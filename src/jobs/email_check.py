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

# Import from your existing email system
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from email_system.integration import get_latest_emails
from repo.email_repo import EmailRepo
from providers.gmail import gmail_fetch_latest
from providers.outlook import outlook_fetch_latest

# Import telegram digest functionality
try:
    from telegram import Bot
    from telegram.digest import send_digest
    TELEGRAM_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Telegram not available: {e}")
    TELEGRAM_AVAILABLE = False

# Import providers safely (they may have missing dependencies)
try:
    from email_system.providers.gmail_provider import GmailProvider
except ImportError as e:
    print(f"Warning: Gmail provider unavailable: {e}")
    GmailProvider = None

try:
    from email_system.providers.outlook_provider import OutlookGraphProvider
except ImportError as e:
    print(f"Warning: Outlook provider unavailable: {e}")
    OutlookGraphProvider = None

# --- Config & state ---
CONFIG_DIR = pathlib.Path(os.getenv("CONFIG_DIR", "/home/mentorius/AI_Services/PA_V2/config")).resolve()
# Set CONFIG_DIR in environment for consistent provider initialization
os.environ["CONFIG_DIR"] = str(CONFIG_DIR)
STATE_FILE = CONFIG_DIR / "email_check_state.json"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0")) if os.getenv("TELEGRAM_CHAT_ID") else 0
LLAMA_BASE_URL = os.getenv("LLAMA_BASE_URL", "http://192.168.0.83:8080").rstrip("/")

# Providers we'll check every run
PROVIDERS = ("gmail", "outlook")  # must match your provider names

# How many messages to pull per run per provider (keep small, we filter by state)
FETCH_COUNT = 10


def load_state() -> Dict[str, Any]:
    """Load the last check state from file"""
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {p: {"last_date_utc": None, "last_ids": []} for p in PROVIDERS}


def save_state(state: Dict[str, Any]) -> None:
    """Save the current check state to file"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


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


def check_provider(provider: str, last_date_utc: dt.datetime | None, last_ids: List[str]) -> Tuple[List[Dict[str, Any]], dt.datetime, List[str]]:
    """
    Pull recent emails, filter to > last_date_utc and not in last_ids.
    Returns (new_items, new_last_date, new_last_ids)
    """
    print(f"🔍 Checking {provider} for new emails...")
    
    # Get emails using your existing API
    result = get_latest_emails(provider, FETCH_COUNT)
    
    if not result.get("success"):
        raise Exception(f"Failed to get emails: {result.get('message', 'Unknown error')}")
    
    emails = result.get("emails", [])
    print(f"📧 Retrieved {len(emails)} emails from {provider}")
    
    # Sort oldest->newest for consistent processing
    emails_sorted = sorted(emails, key=lambda x: parse_email_date(x.get("date") or x.get("received") or x.get("received_date")))
    new_items = []
    newest_dt = last_date_utc or dt.datetime.fromtimestamp(0, tz=dt.timezone.utc)
    newest_ids: List[str] = list(last_ids or [])

    for e in emails_sorted:
        msg_dt = parse_email_date(e.get("date") or e.get("received") or e.get("received_date"))
        msg_id, _ = email_keyparts(e)
        is_newer = (last_date_utc is None) or (msg_dt > last_date_utc)
        not_seen = msg_id and (msg_id not in last_ids)

        if is_newer or not_seen:
            new_items.append(e)
            print(f"📨 Found new email: {e.get('subject', 'No Subject')}")
        
        # update newest trackers
        if msg_dt > newest_dt:
            newest_dt = msg_dt
        if msg_id and msg_id not in newest_ids:
            newest_ids.append(msg_id)

    # Keep last_ids bounded
    newest_ids = newest_ids[-100:]
    return new_items, newest_dt, newest_ids


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
    
    state = load_state()
    any_new = False

    # Initialize email repository
    repo = EmailRepo()

    for provider in PROVIDERS:
        if not auth_status.get(provider, False):
            print(f"⏭️ Skipping {provider} - not authenticated")
            continue
            
        prov_state = state.get(provider, {"last_date_utc": None, "last_ids": []})
        last_date = parse_email_date(prov_state.get("last_date_utc")) if prov_state.get("last_date_utc") else None
        last_ids = prov_state.get("last_ids") or []

        try:
            new_items, newest_dt, newest_ids = check_provider(provider, last_date, last_ids)
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
                    provider=provider,
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
                    received_at=parse_email_date(e.get("date") or e.get("received") or e.get("received_date")),
                    tags=[]
                )
                print(f"💾 Stored email in database with ID: {email_id}")
            except Exception as ex:
                print(f"⚠️ Failed to store email in database: {ex}")
                # Continue processing even if DB storage fails

        # update state
        if new_items:
            state[provider] = {
                "last_date_utc": newest_dt.isoformat(),
                "last_ids": newest_ids,
            }
            any_new = True
            print(f"📊 Updated state for {provider}: {len(new_items)} new emails")

    if any_new:
        save_state(state)
        print("💾 Saved updated state")
        
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
