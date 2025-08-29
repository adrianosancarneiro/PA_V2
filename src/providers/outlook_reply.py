"""On-demand Outlook reply functionality using Microsoft Graph API.

This module provides functionality to:
1. Find Outlook messages by Internet Message-ID 
2. Create reply drafts for proper threading
3. Update draft content and recipients
4. Send the reply

This allows replying via Outlook to emails that were originally received 
via Gmail (e.g., BYU emails redirected to Gmail) while maintaining proper
conversation threading in Outlook.
"""

import requests
from typing import List, Optional, Dict, Any


def _addr_obj(email: str) -> Dict[str, Any]:
    """Convert email address to Graph API recipient object."""
    return {"emailAddress": {"address": email}}


def find_message_by_internet_id(session: requests.Session, internet_message_id: str) -> Optional[Dict[str, Any]]:
    """
    Search the user's mailbox for a message with the exact internetMessageId.
    
    Args:
        session: Pre-authenticated Graph session (base URL should be https://graph.microsoft.com/v1.0)
        internet_message_id: The Message-ID header value (including angle brackets if present)
        
    Returns:
        The message object if found, None otherwise
    """
    # IMPORTANT: internetMessageId must be quoted exactly with angle brackets if present
    # Example filter: internetMessageId eq '<abcdefg@mail.byu.edu>'
    filter_expr = f"internetMessageId eq '{internet_message_id}'"
    url = f"/me/messages?$select=id,subject,internetMessageId&$filter={requests.utils.quote(filter_expr, safe='=$\'?&')}"
    
    try:
        r = session.get(url, timeout=15)
        r.raise_for_status()
        items = r.json().get("value", [])
        return items[0] if items else None
    except Exception as e:
        print(f"❌ Error searching for message by internetMessageId '{internet_message_id}': {e}")
        return None


def create_reply_draft(session: requests.Session, message_id: str) -> Optional[Dict[str, Any]]:
    """
    Create a reply draft (so we can edit recipients and body).
    
    Args:
        session: Pre-authenticated Graph session
        message_id: The Outlook message ID to reply to
        
    Returns:
        The new draft message object containing 'id', or None if failed
    """
    try:
        r = session.post(f"/me/messages/{message_id}/createReply", timeout=15)
        # Some tenants return 201 with message; some 202 with no body — handle both:
        if r.status_code in (200, 201):
            msg = r.json()
            return msg  # contains 'id'
        elif r.status_code == 202:
            # Draft created but no body returned - this is normal for some Graph setups
            # We'd need to find the newest draft, but for now return a placeholder
            print("⚠️ Draft created but no body returned (202)")
            return None
        else:
            r.raise_for_status()
            return None
    except Exception as e:
        print(f"❌ Error creating reply draft for message '{message_id}': {e}")
        return None


def update_draft(session: requests.Session, draft_id: str,
                 body_text: str,
                 to: List[str], cc: List[str], bcc: List[str]) -> bool:
    """
    Update the draft's body and recipients. Use Text for simplicity.
    
    Args:
        session: Pre-authenticated Graph session
        draft_id: The draft message ID to update
        body_text: The reply body content (plain text)
        to: List of TO recipient email addresses
        cc: List of CC recipient email addresses  
        bcc: List of BCC recipient email addresses
        
    Returns:
        True if successful, False otherwise
    """
    payload = {
        "subject": None,  # keep Outlook's default "Re: ..."
        "body": {
            "contentType": "Text",
            "content": body_text or ""
        },
        "toRecipients":  [_addr_obj(x) for x in to]  if to  else [],
        "ccRecipients":  [_addr_obj(x) for x in cc]  if cc  else [],
        "bccRecipients": [_addr_obj(x) for x in bcc] if bcc else [],
    }
    
    try:
        r = session.patch(f"/me/messages/{draft_id}", json=payload, timeout=15)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ Error updating draft '{draft_id}': {e}")
        return False


def send_draft(session: requests.Session, draft_id: str) -> bool:
    """
    Send the draft message.
    
    Args:
        session: Pre-authenticated Graph session
        draft_id: The draft message ID to send
        
    Returns:
        True if successful, False otherwise
    """
    try:
        r = session.post(f"/me/messages/{draft_id}/send", timeout=15)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ Error sending draft '{draft_id}': {e}")
        return False


def reply_via_outlook_session(session: requests.Session,
                              internet_message_id: str,
                              reply_body_text: str,
                              to: List[str], cc: List[str], bcc: List[str]) -> str:
    """
    High-level convenience: find original by internetMessageId, create reply draft,
    update with your body/recipients, and send.
    
    Args:
        session: Pre-authenticated Graph session
        internet_message_id: The Message-ID header from the original email
        reply_body_text: The content of the reply
        to: List of TO recipients
        cc: List of CC recipients 
        bcc: List of BCC recipients
        
    Returns:
        Status string: "sent", "not_found", "draft_create_failed", "update_failed", "send_failed"
    """
    print(f"🔍 Searching for Outlook message with internetMessageId: {internet_message_id}")
    
    found = find_message_by_internet_id(session, internet_message_id)
    if not found:
        print(f"❌ No Outlook message found with internetMessageId: {internet_message_id}")
        return "not_found"

    orig_id = found["id"]
    print(f"✅ Found Outlook message: {found.get('subject', 'No Subject')} (ID: {orig_id})")
    
    draft = create_reply_draft(session, orig_id)
    if not draft or "id" not in draft:
        print(f"❌ Failed to create reply draft for message: {orig_id}")
        return "draft_create_failed"

    draft_id = draft["id"]
    print(f"📝 Created reply draft: {draft_id}")
    
    if not update_draft(session, draft_id, reply_body_text, to, cc, bcc):
        print(f"❌ Failed to update draft: {draft_id}")
        return "update_failed"
    
    print(f"✏️ Updated draft with reply content")
    
    if not send_draft(session, draft_id):
        print(f"❌ Failed to send draft: {draft_id}")
        return "send_failed"
    
    print(f"📤 Successfully sent reply via Outlook")
    return "sent"
