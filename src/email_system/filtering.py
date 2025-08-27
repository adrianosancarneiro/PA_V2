"""Advanced email filtering utilities."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Optional

from dateutil import parser


def _parse(date_value: Optional[str]) -> Optional[datetime]:
    if not date_value:
        return None
    try:
        return parser.parse(date_value)
    except Exception:
        return None


def filter_emails(
    emails: Iterable[Dict],
    *,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    keyword: Optional[str] = None,
    fields: Optional[List[str]] = None,
    sender: Optional[str] = None,
) -> List[Dict]:
    """Filter ``emails`` according to various criteria.

    Args:
        emails: Iterable of email dictionaries.
        date_from/date_to: ISO formatted date strings or similar parsable
            representations. Emails outside the range are removed.
        keyword: Substring that must appear in one of ``fields``.
        fields: List of keys to search for ``keyword`` (defaults to subject and body).
        sender: Filter by sender email address.
    """
    fields = fields or ["subject", "body_preview"]
    start = _parse(date_from)
    end = _parse(date_to)

    def match(email: Dict) -> bool:
        if start or end:
            email_date = _parse(email.get("received_date"))
            if email_date:
                if start and email_date < start:
                    return False
                if end and email_date > end:
                    return False
        if sender and sender.lower() not in email.get("from", "").lower():
            return False
        if keyword:
            key = keyword.lower()
            for field in fields:
                value = email.get(field, "")
                if key in value.lower():
                    return True
            return False
        return True

    return [e for e in emails if match(e)]
