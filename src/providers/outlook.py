"""Outlook provider utilities returning normalized email structures."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from .model import NormalizedEmail


def _addr(obj) -> tuple[Optional[str], Optional[str]]:
    """Extract name and address from a Graph API recipient object."""
    if not obj:
        return None, None
    e = obj.get("emailAddress") or {}
    return e.get("name"), e.get("address")


def _collect(recipients: Optional[List[dict]]) -> List[str]:
    """Return a list of email addresses from a recipients list."""
    if not recipients:
        return []
    out: List[str] = []
    for r in recipients:
        _, addr = _addr(r)
        if addr:
            out.append(addr)
    return out


def outlook_fetch_latest(graph, limit: int = 20) -> List[NormalizedEmail]:
    """Fetch the latest messages from Outlook and normalize them.

    Parameters
    ----------
    graph:
        Pre-authenticated Microsoft Graph client or session capable of
        making HTTP requests.
    limit:
        Maximum number of messages to retrieve.
    """
    url = (
        "/me/messages"
        f"?$top={limit}&$orderby=receivedDateTime desc"
        "&$select=id,conversationId,from,subject,bodyPreview,receivedDateTime,body,"
        "toRecipients,ccRecipients,bccRecipients"
    )
    resp = graph.get(url)
    resp.raise_for_status()
    items = resp.json().get("value", [])
    out: List[NormalizedEmail] = []

    for it in items:
        from_name, from_email = _addr(it.get("from"))
        subject = it.get("subject")
        snippet = it.get("bodyPreview")

        body = it.get("body") or {}
        ctype = (body.get("contentType") or "").lower()
        content = body.get("content")
        body_text = content if ctype == "text" else None
        body_html = content if ctype == "html" else None

        to_emails = _collect(it.get("toRecipients"))
        cc_emails = _collect(it.get("ccRecipients"))
        bcc_emails = _collect(it.get("bccRecipients"))

        received_at = None
        r = it.get("receivedDateTime")
        if r:
            try:
                received_at = datetime.fromisoformat(r.replace("Z", "+00:00"))
            except Exception:
                received_at = None

        out.append(
            NormalizedEmail(
                id=it["id"],
                thread_id=it.get("conversationId"),
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
                provider="outlook",
            )
        )

    return out
