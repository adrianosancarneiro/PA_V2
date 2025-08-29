"""Gmail send message functionality."""
from typing import List, Optional, Dict, Any
import base64
import email.mime.text
import email.mime.multipart
from googleapiclient.discovery import build


def gmail_send_message(
    service_or_creds,
    from_addr: str,
    to_emails: List[str],
    cc_emails: List[str],
    bcc_emails: List[str],
    subject: str,
    body_text: Optional[str],
    body_html: Optional[str]
) -> Dict[str, Any]:
    """
    Send an email via Gmail API.
    
    Args:
        service_or_creds: Gmail API service object or credentials
        from_addr: Sender email address
        to_emails: List of recipient email addresses
        cc_emails: List of CC email addresses
        bcc_emails: List of BCC email addresses
        subject: Email subject
        body_text: Plain text body
        body_html: HTML body
        
    Returns:
        Dict with sent message info including 'id' and 'threadId'
    """
    # Handle service vs credentials
    if hasattr(service_or_creds, 'users'):
        service = service_or_creds
    else:
        service = build("gmail", "v1", credentials=service_or_creds)
    
    # Create message
    if body_html and body_text:
        message = email.mime.multipart.MIMEMultipart('alternative')
        message.attach(email.mime.text.MIMEText(body_text, 'plain'))
        message.attach(email.mime.text.MIMEText(body_html, 'html'))
    elif body_html:
        message = email.mime.text.MIMEText(body_html, 'html')
    else:
        message = email.mime.text.MIMEText(body_text or "", 'plain')
    
    # Set headers
    message['To'] = ', '.join(to_emails)
    if cc_emails:
        message['Cc'] = ', '.join(cc_emails)
    if bcc_emails:
        message['Bcc'] = ', '.join(bcc_emails)
    message['Subject'] = subject
    message['From'] = from_addr
    
    # Encode message
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    
    # Send via API
    send_message = {'raw': raw_message}
    result = service.users().messages().send(userId='me', body=send_message).execute()
    
    print(f"✅ Gmail message sent: {result.get('id')}")
    return result


def gmail_create_draft(
    service_or_creds,
    from_addr: str,
    to_emails: List[str],
    cc_emails: List[str],
    bcc_emails: List[str],
    subject: str,
    body_text: Optional[str],
    body_html: Optional[str]
) -> Dict[str, Any]:
    """Create a Gmail draft."""
    # Handle service vs credentials
    if hasattr(service_or_creds, 'users'):
        service = service_or_creds
    else:
        service = build("gmail", "v1", credentials=service_or_creds)
    
    # Create message (same as send)
    if body_html and body_text:
        message = email.mime.multipart.MIMEMultipart('alternative')
        message.attach(email.mime.text.MIMEText(body_text, 'plain'))
        message.attach(email.mime.text.MIMEText(body_html, 'html'))
    elif body_html:
        message = email.mime.text.MIMEText(body_html, 'html')
    else:
        message = email.mime.text.MIMEText(body_text or "", 'plain')
    
    # Set headers
    message['To'] = ', '.join(to_emails)
    if cc_emails:
        message['Cc'] = ', '.join(cc_emails)
    if bcc_emails:
        message['Bcc'] = ', '.join(bcc_emails)
    message['Subject'] = subject
    message['From'] = from_addr
    
    # Encode message
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    
    # Create draft via API
    draft_message = {'message': {'raw': raw_message}}
    result = service.users().drafts().create(userId='me', body=draft_message).execute()
    
    print(f"📝 Gmail draft created: {result.get('id')}")
    return result
