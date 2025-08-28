from typing import List, Optional, Dict
import requests


def outlook_send_mail(
    session: requests.Session,
    from_addr: str,
    to: List[str],
    cc: List[str],
    bcc: List[str],
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
) -> Dict:
    """Send a message using the Microsoft Graph API.

    Parameters
    ----------
    session:
        Authenticated ``requests.Session`` object configured for the Graph API.
    from_addr:
        Address of the sender.
    to, cc, bcc:
        Recipient email lists. Empty lists are allowed.
    subject:
        Subject line of the email.
    body_text:
        Plain text body.
    body_html:
        Optional HTML body. When provided the message will be sent as HTML.

    Returns
    -------
    dict
        A dictionary with an ``ok`` flag. Consumers may extend this with more
        information if needed.
    """

    body = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "HTML" if body_html else "Text",
                "content": body_html if body_html else (body_text or ""),
            },
            "toRecipients": [{"emailAddress": {"address": a}} for a in to],
            "ccRecipients": [{"emailAddress": {"address": a}} for a in cc] if cc else [],
            "bccRecipients": [{"emailAddress": {"address": a}} for a in bcc] if bcc else [],
        },
        "saveToSentItems": True,
    }
    r = session.post("/me/sendMail", json=body, timeout=15)
    r.raise_for_status()
    return {"ok": True}
