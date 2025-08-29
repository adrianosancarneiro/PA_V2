"""Outlook send message functionality."""
from typing import List, Optional, Dict, Any


def outlook_send_mail(
    session,
    from_addr: str,
    to_emails: List[str],
    cc_emails: List[str],
    bcc_emails: List[str],
    subject: str,
    body_text: Optional[str],
    body_html: Optional[str]
) -> Dict[str, Any]:
    """
    Send an email via Microsoft Graph API.
    
    Args:
        session: Authenticated requests session for Microsoft Graph
        from_addr: Sender email address (used for display only)
        to_emails: List of recipient email addresses
        cc_emails: List of CC email addresses
        bcc_emails: List of BCC email addresses
        subject: Email subject
        body_text: Plain text body
        body_html: HTML body
        
    Returns:
        Dict with sent message info
    """
    # Build recipients
    def build_recipients(email_list):
        return [{"emailAddress": {"address": email}} for email in email_list]
    
    # Determine body content and type
    if body_html:
        body_content = body_html
        content_type = "HTML"
    else:
        body_content = body_text or ""
        content_type = "Text"
    
    # Build message payload
    message = {
        "subject": subject,
        "body": {
            "contentType": content_type,
            "content": body_content
        },
        "toRecipients": build_recipients(to_emails)
    }
    
    if cc_emails:
        message["ccRecipients"] = build_recipients(cc_emails)
    
    if bcc_emails:
        message["bccRecipients"] = build_recipients(bcc_emails)
    
    # Send via Graph API
    response = session.post("/me/sendMail", json={"message": message})
    response.raise_for_status()
    
    print(f"✅ Outlook message sent via Graph API")
    
    # Graph API returns 202 with no content for successful sends
    return {
        "id": "outlook_sent_" + str(hash(subject + str(to_emails))),
        "status": "sent"
    }


def outlook_create_draft(
    session,
    from_addr: str,
    to_emails: List[str],
    cc_emails: List[str],
    bcc_emails: List[str],
    subject: str,
    body_text: Optional[str],
    body_html: Optional[str]
) -> Dict[str, Any]:
    """Create an Outlook draft via Microsoft Graph API."""
    # Build recipients
    def build_recipients(email_list):
        return [{"emailAddress": {"address": email}} for email in email_list]
    
    # Determine body content and type
    if body_html:
        body_content = body_html
        content_type = "HTML"
    else:
        body_content = body_text or ""
        content_type = "Text"
    
    # Build message payload
    message = {
        "subject": subject,
        "body": {
            "contentType": content_type,
            "content": body_content
        },
        "toRecipients": build_recipients(to_emails)
    }
    
    if cc_emails:
        message["ccRecipients"] = build_recipients(cc_emails)
    
    if bcc_emails:
        message["bccRecipients"] = build_recipients(bcc_emails)
    
    # Create draft via Graph API
    response = session.post("/me/messages", json=message)
    response.raise_for_status()
    result = response.json()
    
    print(f"📝 Outlook draft created: {result.get('id')}")
    return result
