"""Service functions for processing Gmail webhook data."""
import os
import sys
import pathlib
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
# Add src to path for sibling imports
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from services.email.email_repo import EmailRepo
from repo.push_repo import PushRepo
from providers.gmail_helpers import build_service, gmail_history_list, gmail_fetch_message_by_id

# Load environment configuration
GMAIL_TOKEN_PATH = os.getenv("GMAIL_TOKEN_PATH", "config/gmail_token.json")

repo = EmailRepo()
push = PushRepo()


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
    
    return {
        "id": gmail_msg["id"],
        "thread_id": gmail_msg.get("threadId"),
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
        
        # Get starting history ID (last processed or current)
        start_hid = push.get_gmail_last_history_id() or incoming_hid
        
        if start_hid >= incoming_hid:
            print(f"📋 History ID {incoming_hid} already processed (last: {start_hid})")
            return
        
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
                    
                except Exception as e:
                    print(f"❌ Error processing message {msg_id}: {e}")
        
        # Update last processed history ID
        push.set_gmail_last_history_id(incoming_hid)
        
        print(f"🎉 Gmail webhook processing complete: {new_emails_count} new emails")
        
    except Exception as e:
        print(f"❌ Error in gmail_process_history: {e}")
        push.set_push_state("gmail", "degraded")
        raise
