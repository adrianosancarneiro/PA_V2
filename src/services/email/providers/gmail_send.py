import base64
from email.message import EmailMessage
from typing import List, Optional, Dict


def gmail_send_message(
    service,
    from_addr: str,
    to: List[str],
    cc: List[str],
    bcc: List[str],
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
) -> Dict:
    """Send an email using the Gmail API.

    Parameters
    ----------
    service:
        Authenticated Gmail service instance.
    from_addr:
        Sender email address.
    to, cc, bcc:
        Recipient lists. Empty lists are ignored.
    subject:
        Email subject line.
    body_text:
        Plain text body of the message.
    body_html:
        Optional HTML body. When provided a multipart/alternative message is
        created with the text version first followed by the HTML part.

    Returns
    -------
    dict
        The Gmail API response containing at least an ``id`` and ``threadId``.
    """

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    if bcc:
        msg["Bcc"] = ", ".join(bcc)
    msg["Subject"] = subject

    if body_html:
        msg.set_content(body_text or "")
        msg.add_alternative(body_html, subtype="html")
    else:
        msg.set_content(body_text or "")

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return sent
