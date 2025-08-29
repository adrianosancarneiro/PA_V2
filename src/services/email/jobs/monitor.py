# src/jobs/email_check.py
"""
Email checking job for PA_V2 - Monitors Gmail and Outlook for new emails
and sends notifications via Telegram with AI-generated summaries
"""
from __future__ import annotations
import os, json, time, pathlib, datetime as dt
import requests
from typing import Dict, Any, List, Tuple
from dotenv import load_dotenv

# Load system-wide secrets
load_dotenv('/etc/pa_v2/secrets.env')

# Import from the new architecture
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from core.database import get_conn
from services.email.integration import get_latest_emails
from services.email.email_repo import EmailRepo
from services.email.providers.gmail import gmail_fetch_latest
from services.email.providers.outlook import outlook_fetch_latest

# Import push/delta functionality
try:
    from repo.push_repo import PushRepo
    from providers.outlook_delta import outlook_delta_list, to_normalized_outlook
    PUSH_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Push functionality not available: {e}")
    PUSH_AVAILABLE = False

# Import telegram digest functionality
try:
    from telegram import Bot
    from interfaces.telegram.views.digest import send_digest
    TELEGRAM_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Telegram not available: {e}")
    TELEGRAM_AVAILABLE = False

# Import providers safely (they may have missing dependencies)
try:
    from services.email.providers.gmail_provider import GmailProvider
except ImportError as e:
    print(f"Warning: Gmail provider unavailable: {e}")
    GmailProvider = None

try:
    from services.email.providers.outlook_provider import OutlookGraphProvider
except ImportError as e:
    print(f"Warning: Outlook provider unavailable: {e}")
    OutlookGraphProvider = None

# --- Config & state ---
CONFIG_DIR = pathlib.Path(os.getenv("CONFIG_DIR", "/home/mentorius/AI_Services/PA_V2/config")).resolve()
# Set CONFIG_DIR in environment for consistent provider initialization
os.environ["CONFIG_DIR"] = str(CONFIG_DIR)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0")) if os.getenv("TELEGRAM_CHAT_ID") else 0
LLAMA_BASE_URL = os.getenv("LLAMA_BASE_URL", "http://192.168.0.83:8080").rstrip("/")

# Providers we'll check every run
PROVIDERS = ("gmail", "outlook")  # must match your provider names

# How many messages to pull per run per provider (keep small, we filter by state)
FETCH_COUNT = 10


def load_state_from_db(repo: EmailRepo) -> Dict[str, Any]:
    """Load the last check state from database"""
    state = {}
    for provider in PROVIDERS:
        try:
            # Get latest email for this provider
            latest_email = repo.get_latest_email_by_provider(provider)
            if latest_email:
                # Get recent message IDs for deduplication (last 100)
                recent_emails = repo.get_recent_emails_by_provider(provider, limit=100)
                recent_ids = [str(email.provider_message_id) for email in recent_emails if email.provider_message_id]
                
                state[provider] = {
                    "last_date_utc": latest_email.received_at.isoformat(),
                    "last_ids": recent_ids
                }
            else:
                state[provider] = {"last_date_utc": None, "last_ids": []}
        except Exception as e:
            print(f"⚠️ Failed to load state for {provider}: {e}")
            state[provider] = {"last_date_utc": None, "last_ids": []}
    
    return state


def save_state(state: Dict[str, Any]) -> None:
    """Legacy function - state is now tracked in database, no file saving needed"""
    print("📝 State tracking moved to database - no JSON file update needed")


def to_utc(dtobj: dt.datetime) -> dt.datetime:
    """Convert datetime to UTC timezone"""
    if dtobj.tzinfo is None:
        return dtobj.replace(tzinfo=dt.timezone.utc)
    return dtobj.astimezone(dt.timezone.utc)


def parse_email_date(val: Any) -> dt.datetime:
    """
    Try several common shapes: ISO strings, epoch seconds, datetime, RFC2822, etc.
    Fallback to 'now - 365 days' if unknown so we don't miss messages.
    """
    if isinstance(val, dt.datetime):
        return to_utc(val)
    if isinstance(val, (int, float)):
        return to_utc(dt.datetime.utcfromtimestamp(float(val)))
    if isinstance(val, str):
        # try ISO
        try:
            return to_utc(dt.datetime.fromisoformat(val.replace("Z", "+00:00")))
        except Exception:
            pass
        # try RFC2822-ish
        from email.utils import parsedate_to_datetime
        try:
            return to_utc(parsedate_to_datetime(val))
        except Exception:
            pass
    return to_utc(dt.datetime.utcnow() - dt.timedelta(days=365))


def email_keyparts(e: Dict[str, Any]) -> Tuple[str, str]:
    """Return a stable tuple for dedup/state: (provider_id, subject) best-effort."""
    msg_id = str(e.get("id") or e.get("message_id") or e.get("internet_message_id") or "")
    subj = str(e.get("subject") or "")
    return (msg_id, subj)


def get_text_from_email(e: Dict[str, Any]) -> str:
    """Heuristic to get human-readable body/preview."""
    for k in ("body", "text", "snippet", "preview"):
        if e.get(k):
            return str(e[k])
    # fallback compose a minimal view
    return f"From: {e.get('from') or e.get('sender')}\nSubject: {e.get('subject')}\n(No preview available.)"


def llama_summarize_and_draft(email_text: str) -> str:
    """
    Calls local llama.cpp (OpenAI-compatible /v1/chat/completions).
    Returns a formatted string: Summary + Draft.
    """
    prompt = (
        "You are an email assistant. Given the email below, do two things:\n"
        "1) Write a 2–3 sentence summary.\n"
        "2) Write a concise, professional draft reply under 120 words.\n"
        "Format output as:\n"
        "Summary: <...>\n"
        "Draft: <...>\n\n"
        f"Email:\n{email_text}"
    )
    payload = {
        "model": "llama",  # your loaded model alias/name (server-side)
        "messages": [
            {"role": "system", "content": "You are a helpful, concise assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6,
    }
    url = f"{LLAMA_BASE_URL}/v1/chat/completions"
    resp = requests.post(url, json=payload, timeout=90)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def send_telegram(text: str) -> None:
    """Send a message to Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("TELEGRAM_BOT_TOKEN/CHAT_ID missing; skipping Telegram send.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text[:4000],  # Telegram max is larger; keep it tidy
        "disable_web_page_preview": True,
        "parse_mode": "Markdown"  # Enable markdown formatting
    }
    r = requests.post(url, data=payload, timeout=15)
    r.raise_for_status()


def format_telegram_message(provider: str, e: Dict[str, Any], ai: str) -> str:
    """Format email information for Telegram message"""
    frm = e.get("from") or e.get("sender") or "(unknown sender)"
    subj = e.get("subject") or "(no subject)"
    date = e.get("date") or e.get("received") or e.get("received_date") or ""
    
    # Escape markdown special characters in email data
    frm = frm.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
    subj = subj.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
    
    return (
        f"✉️ *{provider.upper()}* — New email\n"
        f"From: {frm}\n"
        f"Subject: {subj}\n"
        f"Date: {date}\n\n"
        f"{ai}"
    )


def check_outlook_delta(repo: EmailRepo, push_repo: PushRepo) -> List[Dict[str, Any]]:
    """
    Check Outlook using Graph delta queries for incremental sync.
    Much more efficient than fetching all recent emails.
    """
    print("🔄 Checking Outlook using delta queries...")
    
    try:
        # Get Outlook Graph session (reuse existing provider logic)
        if not OutlookGraphProvider:
            print("❌ Outlook provider not available")
            return []
            
        outlook = OutlookGraphProvider()
        if not outlook.is_authenticated():
            print("❌ Outlook not authenticated")
            return []
        
        # Get the Graph session from the provider
        session = outlook.session  # Assuming this exists in your provider
        
        # Get previous delta link
        delta_link = push_repo.get_outlook_delta_link()
        
        # Query delta
        changes, next_delta_link = outlook_delta_list(session, delta_link)
        
        # Process changes and filter for new emails
        new_emails = []
        for item in changes:
            # Check if this is a deletion or update we should ignore
            if item.get("@removed"):
                continue
                
            # Convert to normalized format
            normalized = to_normalized_outlook(item)
            
            # Check if already in database
            existing_id = repo.get_email_id("outlook", normalized["id"])
            if existing_id is None:
                new_emails.append(normalized)
                print(f"📨 Found new Outlook email: {normalized.get('subject', 'No Subject')}")
        
        # Update delta link for next time
        if next_delta_link:
            push_repo.set_outlook_delta_link(next_delta_link)
        
        # Update poll timestamp
        push_repo.touch_poll("outlook")
        
        return new_emails
        
    except Exception as e:
        print(f"❌ Error in Outlook delta check: {e}")
        return []


def check_provider(provider: str, repo: EmailRepo) -> List[Dict[str, Any]]:
    """
    Pull recent emails and filter out ones already in database.
    Simple approach: fetch latest emails, check each against database.
    Returns only truly new emails.
    """
    print(f"🔍 Checking {provider} for new emails...")
    
    # Get emails using your existing API
    result = get_latest_emails(provider, FETCH_COUNT)
    
    if not result.get("success"):
        raise Exception(f"Failed to get emails: {result.get('message', 'Unknown error')}")
    
    emails = result.get("emails", [])
    print(f"📧 Retrieved {len(emails)} emails from {provider}")
    
    new_emails = []
    
    for email in emails:
        # Check if this email already exists in database
        provider_message_id = (
            email.get("id") or 
            email.get("internet_message_id") or 
            email.get("message_id") or 
            f"{email.get('subject', '')}_{email.get('from', '')}_{email.get('date', '')}"
        )
        
        if provider_message_id:
            existing_id = repo.get_email_id(provider, provider_message_id)
            if existing_id is None:
                # This email is not in database - it's new
                new_emails.append(email)
                print(f"📨 Found new email: {email.get('subject', 'No Subject')}")
            # else: email already exists in database, skip it
    
    return new_emails


def check_auth_status() -> Dict[str, bool]:
    """Check authentication status for all providers"""
    status = {}
    
    if GmailProvider:
        try:
            gmail = GmailProvider()
            status['gmail'] = gmail.is_authenticated()
        except Exception as e:
            status['gmail'] = False
            print(f"Gmail auth check failed: {e}")
    else:
        status['gmail'] = False
        print("Gmail provider not available (missing dependencies)")
    
    if OutlookGraphProvider:
        try:
            outlook = OutlookGraphProvider()  
            status['outlook'] = outlook.is_authenticated()
        except Exception as e:
            status['outlook'] = False
            print(f"Outlook auth check failed: {e}")
    else:
        status['outlook'] = False
        print("Outlook provider not available (missing dependencies)")
    
    return status

def main() -> None:
    """Main email checking function"""
    print(f"🚀 Starting email check at {dt.datetime.now()}")
    
    # Check authentication status first
    auth_status = check_auth_status()
    print("Authentication Status:")
    for provider, is_auth in auth_status.items():
        print(f"  {provider}: {'✅ Ready' if is_auth else '❌ Setup needed'}")
    
    if not all(auth_status.values()):
        error_msg = "⚠️ Some email providers need authentication. Please run setup."
        print(error_msg)
        try:
            send_telegram(error_msg)
        except Exception as e:
            print(f"Failed to send Telegram notification: {e}")
        return
    
    # Initialize repositories
    repo = EmailRepo()
    push_repo = PushRepo() if PUSH_AVAILABLE else None
    any_new = False
    all_new_emails = []

    for provider in PROVIDERS:
        if not auth_status.get(provider, False):
            print(f"⏭️ Skipping {provider} - not authenticated")
            continue

        try:
            # Use delta for Outlook if available, regular check for Gmail
            if provider == "outlook" and push_repo:
                new_items = check_outlook_delta(repo, push_repo)
            else:
                new_items = check_provider(provider, repo)
                
        except Exception as ex:
            error_msg = f"❌ {provider.upper()} checker error: {ex}"
            print(error_msg)
            try:
                send_telegram(error_msg)
            except Exception as e:
                print(f"Failed to send Telegram error notification: {e}")
            continue

        for e in new_items:
            print(f"📝 Processing new email: {e.get('subject', 'No Subject')}")
            
            # Store email in database using normalized format
            try:
                email_id = repo.upsert_email(
                    provider=e.get("provider", provider),
                    provider_message_id=str(e.get("id") or e.get("message_id") or e.get("internet_message_id") or ""),
                    provider_thread_id=str(e.get("thread_id") or e.get("conversation_id") or ""),
                    from_display=e.get("from_name"),
                    from_email=e.get("from") or e.get("from_email"),
                    to_emails=e.get("to") or e.get("to_emails") or [],
                    cc_emails=e.get("cc") or e.get("cc_emails") or [],
                    bcc_emails=e.get("bcc") or e.get("bcc_emails") or [],
                    subject=e.get("subject"),
                    snippet=e.get("snippet") or e.get("body_preview"),
                    body_plain=e.get("body") or e.get("text") or e.get("body_text"),
                    body_html=e.get("body_html"),
                    received_at=parse_email_date(e.get("date") or e.get("received") or e.get("received_date") or e.get("received_at")),
                    tags=[]
                )
                print(f"💾 Stored email in database with ID: {email_id}")
                all_new_emails.append(e)
            except Exception as ex:
                print(f"⚠️ Failed to store email in database: {ex}")
                # Continue processing even if DB storage fails

        if new_items:
            any_new = True
            print(f"📊 Processed {len(new_items)} new emails from {provider}")
            
            # Update poll timestamp for regular providers
            if push_repo and provider == "gmail":
                push_repo.touch_poll("gmail")

    if any_new:
        print("💾 Processing completed")
        
        # Send digest instead of individual messages
        if TELEGRAM_AVAILABLE and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            try:
                print("📱 Sending Telegram digest...")
                rows = repo.latest_new_messages(limit=20)
                if rows:
                    bot = Bot(TELEGRAM_BOT_TOKEN)
                    send_digest(bot, TELEGRAM_CHAT_ID, rows)
                    print(f"✅ Sent digest with {len(rows)} emails")
                else:
                    print("📭 No new messages for digest")
            except Exception as ex:
                print(f"❌ Digest send failed: {ex}")
    else:
        print("📭 No new emails found")
    
    print(f"✅ Email check completed at {dt.datetime.now()}")


if __name__ == "__main__":
    main()
