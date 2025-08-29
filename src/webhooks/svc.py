"""Service functions for processing Gmail webhook data."""
import os
import sys
import pathlib
import requests
import json
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment secrets
load_dotenv('/etc/pa_v2/secrets.env')

# Add project root to path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
# Add src to path for sibling imports
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from services.email.email_repo import EmailRepo
from repo.push_repo import PushRepo
from providers.gmail_helpers import build_service, gmail_history_list, gmail_fetch_message_by_id

# Import Telegram digest system for proper notifications
try:
    from telegram import Bot
    from interfaces.telegram.views.digest import send_digest
    TELEGRAM_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Telegram digest not available: {e}")
    TELEGRAM_AVAILABLE = False

# Load environment configuration
GMAIL_TOKEN_PATH = os.getenv("GMAIL_TOKEN_PATH", "config/gmail_token.json")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

repo = EmailRepo()
push = PushRepo()


def send_telegram_digest(email_id: int) -> None:
    """Send a proper digest notification for a new email"""
    if not TELEGRAM_AVAILABLE or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram digest not available; skipping notification.")
        return
    
    try:
        # Get the email details for digest format
        email_detail = repo.get_email_detail(email_id)
        if not email_detail:
            print(f"No email found with ID {email_id} for digest")
            return
        
        # Convert to the tuple format expected by send_digest
        # (email_id, provider, from_display, from_email, subject, snippet, received_at)
        digest_row = (
            email_id,
            email_detail['provider'],
            email_detail['from_display'],
            email_detail['from_email'],
            email_detail['subject'],
            email_detail['snippet'],
            email_detail['received_at']
        )
        
        # Build digest using the proper function but send using HTTP API to avoid async issues
        from interfaces.telegram.views.digest import build_digest
        text, markup, mode = build_digest([digest_row])
        
        # Send using HTTP API instead of Bot object to avoid async issues
        import json
        import requests
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        # Convert InlineKeyboardMarkup to dict format for JSON
        keyboard_data = []
        for row in markup.inline_keyboard:
            button_row = []
            for button in row:
                button_row.append({
                    "text": button.text,
                    "callback_data": button.callback_data
                })
            keyboard_data.append(button_row)
        
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": {
                "inline_keyboard": keyboard_data
            }
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Telegram digest sent for email ID: {email_id}")
        else:
            print(f"❌ Telegram API error: {response.status_code} - {response.text}")
            raise Exception(f"HTTP {response.status_code}")
        
    except Exception as e:
        print(f"❌ Failed to send Telegram digest: {e}")
        # Fallback to simple notification
        try:
            send_telegram_simple(email_id)
        except Exception as e2:
            print(f"❌ Fallback notification also failed: {e2}")


def send_telegram_simple(email_id: int) -> None:
    """Fallback simple Telegram notification"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    
    try:
        # Get email details
        email = repo.get_email_detail(email_id)
        if not email:
            return
            
        text = (
            f"📧 *GMAIL* — New email via webhook\n"
            f"From: {email.get('from_email', 'Unknown')}\n"
            f"Subject: {email.get('subject', 'No Subject')}\n"
            f"Date: {email.get('received_at', '')}"
        )
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        }
        requests.post(url, data=payload, timeout=10)
        
    except Exception as e:
        print(f"❌ Simple notification failed: {e}")


def send_telegram(text: str) -> None:
    """Send a message to Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("TELEGRAM_BOT_TOKEN/CHAT_ID missing; skipping Telegram send.")
        return
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text[:4000],  # Telegram max is larger; keep it tidy
            "disable_web_page_preview": True,
            "parse_mode": "Markdown"  # Enable markdown formatting
        }
        r = requests.post(url, data=payload, timeout=15)
        r.raise_for_status()
        print(f"✅ Telegram notification sent: {text[:50]}...")
    except Exception as e:
        print(f"❌ Failed to send Telegram notification: {e}")


def format_telegram_message(nm: Dict[str, Any]) -> str:
    """Format email information for Telegram message"""
    frm = nm.get("from_email") or "(unknown sender)"
    subj = nm.get("subject") or "(no subject)"
    date = nm.get("received_at") or ""
    snippet = nm.get("snippet") or ""
    
    # Escape markdown special characters in email data
    frm = frm.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
    subj = subj.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
    snippet = snippet.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
    
    # Truncate snippet if too long
    if len(snippet) > 200:
        snippet = snippet[:197] + "…"
    
    return (
        f"📧 *GMAIL* — New email via webhook\n"
        f"From: {frm}\n"
        f"Subject: {subj}\n"
        f"Date: {date}\n"
        f"Preview: {snippet}\n\n"
        f"🧵 Thread ID: {nm.get('thread_id')}"
    )


def _load_creds():
    """Load Gmail OAuth credentials."""
    from google.oauth2.credentials import Credentials
    return Credentials.from_authorized_user_file(GMAIL_TOKEN_PATH, scopes=[
        "https://www.googleapis.com/auth/gmail.readonly"
    ])


def to_normalized_gmail(gmail_msg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Gmail message to normalized format.
    
    This is a simplified version - you should use your existing gmail provider logic.
    """
    headers = {}
    payload = gmail_msg.get("payload", {})
    for header in payload.get("headers", []):
        headers[header["name"].lower()] = header["value"]
    
    # Extract original headers for cross-provider threading
    internet_id = None
    references_ids = []
    for header in payload.get("headers", []):
        name = header.get("name", "").lower()
        value = header.get("value", "")
        if name == "message-id":
            internet_id = value
        elif name == "references" and value:
            references_ids = [x.strip() for x in value.split() if x.strip()]
    
    # Extract body text (simplified)
    body_text = ""
    body_html = ""
    
    def extract_body(part):
        nonlocal body_text, body_html
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                import base64
                body_text = base64.urlsafe_b64decode(data + "===").decode("utf-8", errors="ignore")
        elif part.get("mimeType") == "text/html":
            data = part.get("body", {}).get("data", "")
            if data:
                import base64
                body_html = base64.urlsafe_b64decode(data + "===").decode("utf-8", errors="ignore")
        
        for subpart in part.get("parts", []):
            extract_body(subpart)
    
    extract_body(payload)
    
    # Parse date
    from datetime import datetime
    received_at = None
    if "date" in headers:
        try:
            from email.utils import parsedate_to_datetime
            received_at = parsedate_to_datetime(headers["date"])
        except:
            pass
    
    # Extract thread ID with validation and fallback
    thread_id = gmail_msg.get("threadId")
    if not thread_id or thread_id.strip() == "":
        # Fallback: use message ID as thread ID for single-message threads
        thread_id = gmail_msg["id"]
        print(f"⚠️ Warning: No threadId found for message {gmail_msg['id']}, using message ID as fallback")
    
    return {
        "id": gmail_msg["id"],
        "thread_id": thread_id,
        "provider": "gmail",
        "from_name": headers.get("from", "").split("<")[0].strip().strip('"'),
        "from_email": headers.get("from", ""),
        "to_emails": [headers.get("to", "")],
        "cc_emails": [headers.get("cc", "")] if headers.get("cc") else [],
        "bcc_emails": [],
        "subject": headers.get("subject", ""),
        "snippet": gmail_msg.get("snippet", ""),
        "body_text": body_text,
        "body_html": body_html,
        "received_at": received_at,
        "internet_message_id": internet_id,
        "references_ids": references_ids,
    }


async def gmail_process_history(incoming_hid: int):
    """
    Process Gmail history changes from webhook notification.
    
    Args:
        incoming_hid: History ID from the webhook notification
    """
    try:
        print(f"🔄 Processing Gmail history from ID: {incoming_hid}")
        
        creds = _load_creds()
        svc = build_service(creds)
        
    # Get starting history ID (last processed or, on first run, the incoming one)
    start_hid = push.get_gmail_last_history_id() or incoming_hid
    print(f"🔎 History scan from {start_hid} -> incoming {incoming_hid}")
        
        # Get history changes
    history_result = gmail_history_list(svc, start_history_id=start_hid)
        history_items = history_result.get("history", [])
        
        print(f"📨 Found {len(history_items)} history items to process")
        
        # Process each history item
        new_emails_count = 0
        for hist_item in history_items:
            for added in hist_item.get("messagesAdded", []):
                msg_id = added["message"]["id"]
                
                # Check if we already have this message
                existing_id = repo.get_email_id("gmail", msg_id)
                if existing_id:
                    print(f"⏭️ Skipping existing email: {msg_id}")
                    continue
                
                try:
                    # Fetch full message
                    full_msg = gmail_fetch_message_by_id(svc, msg_id)
                    nm = to_normalized_gmail(full_msg)
                    
                    # Debug: Log the extracted threadId
                    print(f"🐛 Debug - Message {msg_id}: threadId='{nm['thread_id']}', subject='{nm.get('subject', 'No Subject')}'")
                    
                    # Validate thread ID is not empty
                    if not nm['thread_id'] or nm['thread_id'].strip() == "":
                        print(f"❌ Error: Empty thread ID for message {msg_id}, skipping...")
                        continue
                    
                    # Store in database
                    email_id = repo.upsert_email(
                        provider=nm["provider"],
                        provider_message_id=nm["id"],
                        provider_thread_id=nm["thread_id"],
                        from_display=nm.get("from_name"),
                        from_email=nm.get("from_email"),
                        to_emails=nm.get("to_emails", []),
                        cc_emails=nm.get("cc_emails", []),
                        bcc_emails=nm.get("bcc_emails", []),
                        subject=nm.get("subject"),
                        snippet=nm.get("snippet"),
                        body_plain=nm.get("body_text"),
                        body_html=nm.get("body_html"),
                        received_at=nm.get("received_at"),
                        tags=[],
                        internet_message_id=nm.get("internet_message_id"),
                        references_ids=nm.get("references_ids", [])
                    )
                    
                    new_emails_count += 1
                    print(f"✅ Processed new email: {nm.get('subject', 'No Subject')} (ID: {email_id})")
                    
                    # Send proper Telegram digest notification for new email
                    try:
                        send_telegram_digest(email_id)
                        # mark as notified to avoid duplicates
                        try:
                            repo.mark_notified(email_id)
                        except Exception as me:
                            print(f"⚠️ Failed to mark email {email_id} notified: {me}")
                    except Exception as e:
                        print(f"⚠️ Failed to send Telegram digest: {e}")
                    
                except Exception as e:
                    print(f"❌ Error processing message {msg_id}: {e}")
        
    # Update last processed history ID
    push.set_gmail_last_history_id(incoming_hid)
        
        print(f"🎉 Gmail webhook processing complete: {new_emails_count} new emails")
        
    except Exception as e:
        print(f"❌ Error in gmail_process_history: {e}")
        push.set_push_state("gmail", "degraded")
        raise
