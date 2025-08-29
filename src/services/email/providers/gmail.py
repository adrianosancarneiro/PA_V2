"""Gmail provider utilities returning normalized email structures."""
from __future__ import annotations

from base64 import urlsafe_b64decode
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional

from .model import NormalizedEmail


def _header(headers: List[dict], name: str) -> Optional[str]:
    """Return the value of a header from Gmail's header list."""
    name_lower = name.lower()
    for h in headers or []:
        if h.get("name", "").lower() == name_lower:
            return h.get("value")
    return None


def _split_emails(s: Optional[str]) -> List[str]:
    """Split a comma-delimited string of emails into a list."""
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def _split_refs(refs: Optional[str]) -> List[str]:
    """Split References header into list of message IDs."""
    if not refs:
        return []
    # References can be a space-separated list of message-ids
    return [x.strip() for x in refs.split() if x.strip()]


def _extract_bodies(payload: dict) -> tuple[Optional[str], Optional[str]]:
    """Traverse Gmail's MIME structure and return plain and HTML bodies."""
    text: Optional[str] = None
    html: Optional[str] = None

    def walk(part: dict) -> None:
        nonlocal text, html
        mime = part.get("mimeType")
        data = part.get("body", {}).get("data")
        if data:
            decoded = urlsafe_b64decode(data + "==").decode(errors="ignore")
            if mime == "text/plain" and text is None:
                text = decoded
            elif mime == "text/html" and html is None:
                html = decoded
        for sub in part.get("parts", []) or []:
            walk(sub)

    walk(payload)
    return text, html


def gmail_fetch_latest(service, user_id: str = "me", limit: int = 20) -> List[NormalizedEmail]:
    """Fetch the latest messages from Gmail and normalize them.

    Parameters
    ----------
    service:
        Authenticated Gmail API service instance.
    user_id:
        Gmail user identifier. Defaults to ``"me"`` which uses the
        authenticated user.
    limit:
        Maximum number of messages to retrieve.
    """
    result = service.users().messages().list(userId=user_id, maxResults=limit).execute()
    msgs = result.get("messages", [])
    out: List[NormalizedEmail] = []

    for m in msgs:
        full = (
            service.users()
            .messages()
            .get(userId=user_id, id=m["id"], format="full")
            .execute()
        )
        payload = full.get("payload", {})
        headers = payload.get("headers", [])
        thread_id = full.get("threadId")

        subject = _header(headers, "Subject")
        from_raw = _header(headers, "From") or ""
        from_name = None
        from_email = None
        if "<" in from_raw:
            from_name = from_raw.split("<")[0].strip().strip('"')
            from_email = from_raw.split("<")[-1].rstrip(">").strip()
        else:
            from_email = from_raw or None
        to_emails = _split_emails(_header(headers, "To"))
        cc_emails = _split_emails(_header(headers, "Cc"))
        bcc_emails = _split_emails(_header(headers, "Bcc"))

        # Extract original message headers for cross-provider threading
        internet_id = _header(headers, "Message-ID")
        references = _header(headers, "References")
        references_ids = _split_refs(references)

        snippet = full.get("snippet")
        body_text, body_html = _extract_bodies(payload)

        received_at = None
        if full.get("internalDate"):
            received_at = datetime.fromtimestamp(
                int(full["internalDate"]) / 1000, tz=timezone.utc
            )
        else:
            dh = _header(headers, "Date")
            if dh:
                try:
                    received_at = parsedate_to_datetime(dh)
                except Exception:
                    received_at = None

        out.append(
            NormalizedEmail(
                id=full["id"],
                thread_id=thread_id,
                from_name=from_name,
                from_email=from_email,
                to_emails=to_emails,
                cc_emails=cc_emails,
                bcc_emails=bcc_emails,
                subject=subject,
                snippet=snippet,
                body_text=body_text,
                body_html=body_html,
                received_at=received_at,
                provider="gmail",
                internet_message_id=internet_id,
                references_ids=references_ids,
            )
        )

    return out
