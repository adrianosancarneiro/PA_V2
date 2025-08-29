"""Service for replying to emails via Outlook using stored Internet Message-IDs.

This service bridges the gap between emails stored from Gmail (including
BYU emails redirected to Gmail) and replying via Outlook. It uses the
stored internet_message_id from the Gmail copy to find the corresponding
Outlook message and create a properly threaded reply.
"""

import sys
import pathlib
from typing import List, Optional

# Add project root to path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from services.email.email_repo import EmailRepo
from providers.outlook_reply import reply_via_outlook_session


def reply_via_outlook_for_email_id(graph_session,
                                   email_id: int,
                                   reply_body_text: str,
                                   extra_to: Optional[List[str]] = None,
                                   extra_cc: Optional[List[str]] = None,
                                   extra_bcc: Optional[List[str]] = None) -> str:
    """
    Use the stored internet_message_id from the Gmail copy to reply in Outlook.
    
    Args:
        graph_session: Authenticated requests.Session for Microsoft Graph API
        email_id: The database ID of the email to reply to
        reply_body_text: The content of the reply message
        extra_to: Additional TO recipients beyond the original sender
        extra_cc: Additional CC recipients beyond the original CC list
        extra_bcc: Additional BCC recipients
        
    Returns:
        Status string indicating the result:
        - "sent": Reply sent successfully
        - "no_internet_message_id": The email doesn't have an internet_message_id
        - "not_found": No corresponding Outlook message found
        - "draft_create_failed": Failed to create reply draft
        - "update_failed": Failed to update draft content
        - "send_failed": Failed to send the draft
    """
    print(f"🔄 Processing Outlook reply for email ID: {email_id}")
    
    repo = EmailRepo()
    detail = repo.get_email_detail(email_id)
    if not detail:
        print(f"❌ Email {email_id} not found in database")
        return "email_not_found"
    
    imid = detail.get("internet_message_id")
    if not imid:
        print(f"❌ Email {email_id} has no internet_message_id stored")
        return "no_internet_message_id"

    print(f"📧 Email details:")
    print(f"   From: {detail.get('from_email')}")
    print(f"   Subject: {detail.get('subject')}")
    print(f"   Internet Message-ID: {imid}")

    # Build recipients - reply to sender and include original recipients
    from_email = detail.get("from_email")
    to_emails = []
    if from_email:
        to_emails.append(from_email)
    
    # Add extra recipients if provided
    if extra_to:
        to_emails.extend(extra_to)
    
    cc_emails = list(detail.get("cc_emails") or [])
    if extra_cc:
        cc_emails.extend(extra_cc)
    
    bcc_emails = list(detail.get("bcc_emails") or [])
    if extra_bcc:
        bcc_emails.extend(extra_bcc)

    # Remove duplicates while preserving order
    to_emails = list(dict.fromkeys(to_emails))
    cc_emails = list(dict.fromkeys(cc_emails))
    bcc_emails = list(dict.fromkeys(bcc_emails))

    print(f"📮 Reply recipients:")
    print(f"   TO: {to_emails}")
    print(f"   CC: {cc_emails}")
    print(f"   BCC: {bcc_emails}")

    return reply_via_outlook_session(
        graph_session,
        imid,
        reply_body_text,
        to_emails,
        cc_emails,
        bcc_emails
    )


def fallback_compose_new_outlook_reply(graph_session,
                                       email_id: int,
                                       reply_body_text: str,
                                       extra_to: Optional[List[str]] = None,
                                       extra_cc: Optional[List[str]] = None,
                                       extra_bcc: Optional[List[str]] = None) -> str:
    """
    Fallback function to compose a new email via Outlook when the original
    message cannot be found by Internet Message-ID.
    
    This creates a new email with "Re: [Subject]" to the original sender,
    which will reach them but may not thread perfectly in Outlook.
    
    Args:
        graph_session: Authenticated requests.Session for Microsoft Graph API
        email_id: The database ID of the email to reply to
        reply_body_text: The content of the reply message
        extra_to: Additional TO recipients
        extra_cc: Additional CC recipients
        extra_bcc: Additional BCC recipients
        
    Returns:
        Status string: "sent" if successful, error message otherwise
    """
    print(f"📝 Creating new Outlook email as fallback for email ID: {email_id}")
    
    repo = EmailRepo()
    detail = repo.get_email_detail(email_id)
    if not detail:
        return "email_not_found"
    
    from_email = detail.get("from_email")
    original_subject = detail.get("subject", "")
    
    if not from_email:
        return "no_sender_email"
    
    # Create "Re: " subject if not already present
    subject = original_subject
    if subject and not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    elif not subject:
        subject = "Re: (No Subject)"
    
    # Build recipients
    to_emails = [from_email]
    if extra_to:
        to_emails.extend(extra_to)
    
    cc_emails = list(extra_cc or [])
    bcc_emails = list(extra_bcc or [])
    
    # Remove duplicates
    to_emails = list(dict.fromkeys(to_emails))
    cc_emails = list(dict.fromkeys(cc_emails))
    bcc_emails = list(dict.fromkeys(bcc_emails))
    
    # Compose new message via Graph API
    payload = {
        "subject": subject,
        "body": {
            "contentType": "Text",
            "content": reply_body_text
        },
        "toRecipients": [{"emailAddress": {"address": email}} for email in to_emails],
        "ccRecipients": [{"emailAddress": {"address": email}} for email in cc_emails] if cc_emails else [],
        "bccRecipients": [{"emailAddress": {"address": email}} for email in bcc_emails] if bcc_emails else [],
    }
    
    try:
        print(f"📤 Sending new Outlook email:")
        print(f"   TO: {to_emails}")
        print(f"   Subject: {subject}")
        
        r = graph_session.post("/me/sendMail", json={"message": payload}, timeout=15)
        r.raise_for_status()
        
        print(f"✅ Successfully sent new Outlook email")
        return "sent"
        
    except Exception as e:
        print(f"❌ Error sending new Outlook email: {e}")
        return f"send_failed: {e}"
