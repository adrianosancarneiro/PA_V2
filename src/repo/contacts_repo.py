"""Repository helpers for contact lookups."""
from __future__ import annotations

from typing import List, Tuple

from ..db import get_conn


def search_contacts(q: str, limit: int = 10) -> List[Tuple[int, str, str]]:
    """Search contacts by display name or email.

    Parameters
    ----------
    q:
        Search query string. A case-insensitive ``LIKE`` match is performed
        against both the display name and email fields.
    limit:
        Maximum number of rows to return.
    """
    q_like = f"%{q.lower()}%"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, display_name, email
              FROM contacts
             WHERE lower(email) LIKE %s OR lower(display_name) LIKE %s
             ORDER BY frequency_score DESC, last_seen_at DESC NULLS LAST
             LIMIT %s
            """,
            (q_like, q_like, limit),
        )
        return cur.fetchall()
