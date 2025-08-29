"""Outlook Graph API delta query functions."""
from typing import Tuple, List, Dict, Any, Optional


def outlook_delta_list(session, delta_link: Optional[str]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Query Outlook messages using delta links for incremental sync.
    
    Args:
        session: Authenticated requests session for Microsoft Graph API
        delta_link: Previous delta link for incremental sync, or None for initial sync
    
    Returns:
        Tuple of (message_list, next_delta_link)
    """
    if delta_link:
        url = delta_link
        print(f"🔄 Continuing Outlook delta from: {delta_link[:100]}...")
    else:
        url = ("/me/mailFolders/Inbox/messages/delta"
               "?$select=id,conversationId,from,subject,bodyPreview,receivedDateTime,body,"
               "toRecipients,ccRecipients,bccRecipients&$top=50")
        print("🆕 Starting initial Outlook delta query")
    
    items = []
    page_count = 0
    
    while url:
        page_count += 1
        print(f"📄 Fetching Outlook delta page {page_count}...")
        
        try:
            response = session.get(url, headers={"Prefer": "odata.maxpagesize=50"})
            response.raise_for_status()
            data = response.json()
            
            # Add items from this page
            page_items = data.get("value", [])
            items.extend(page_items)
            print(f"📨 Got {len(page_items)} items from page {page_count}")
            
            # Check for next page or delta link
            url = data.get("@odata.nextLink")
            delta = data.get("@odata.deltaLink")
            
            if delta:
                print(f"🎯 Found delta link, total items: {len(items)}")
                return items, delta
                
        except Exception as e:
            print(f"❌ Error fetching Outlook delta page {page_count}: {e}")
            raise
    
    print(f"✅ Completed Outlook delta query: {len(items)} total items")
    return items, None


def parse_outlook_recipients(recipients_data: List[Dict[str, Any]]) -> List[str]:
    """Parse Outlook recipients array into email addresses."""
    emails = []
    for recipient in recipients_data or []:
        email_addr = recipient.get("emailAddress", {}).get("address", "")
        if email_addr:
            emails.append(email_addr)
    return emails


def to_normalized_outlook(outlook_msg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Outlook Graph message to normalized format.
    
    Args:
        outlook_msg: Raw message dict from Microsoft Graph API
        
    Returns:
        Normalized message dict
    """
    # Parse sender
    from_data = outlook_msg.get("from", {}).get("emailAddress", {})
    from_name = from_data.get("name", "")
    from_email = from_data.get("address", "")
    
    # Parse recipients
    to_emails = parse_outlook_recipients(outlook_msg.get("toRecipients", []))
    cc_emails = parse_outlook_recipients(outlook_msg.get("ccRecipients", []))
    bcc_emails = parse_outlook_recipients(outlook_msg.get("bccRecipients", []))
    
    # Parse body
    body_data = outlook_msg.get("body", {})
    body_content = body_data.get("content", "")
    body_type = body_data.get("contentType", "text")
    
    body_text = body_content if body_type == "text" else ""
    body_html = body_content if body_type == "html" else ""
    
    # Parse date
    received_at = None
    received_str = outlook_msg.get("receivedDateTime")
    if received_str:
        try:
            from datetime import datetime
            received_at = datetime.fromisoformat(received_str.replace("Z", "+00:00"))
        except:
            pass
    
    return {
        "id": outlook_msg["id"],
        "thread_id": outlook_msg.get("conversationId"),
        "provider": "outlook",
        "from_name": from_name,
        "from_email": from_email,
        "to_emails": to_emails,
        "cc_emails": cc_emails,
        "bcc_emails": bcc_emails,
        "subject": outlook_msg.get("subject", ""),
        "snippet": outlook_msg.get("bodyPreview", ""),
        "body_text": body_text,
        "body_html": body_html,
        "received_at": received_at,
    }
