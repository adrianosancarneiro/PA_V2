"""Repository helpers for outbound email drafting and sending."""
from __future__ import annotations

from typing import List, Optional

from ..db import get_conn


def create_outbound_draft(
    provider: str,
    from_email: str,
    to: List[str],
    cc: List[str],
    bcc: List[str],
    subject: str,
    draft_text: str,
    body_html: Optional[str],
    thread_id: Optional[str] = None,
) -> int:
    """Insert a draft outbound message and return its internal id."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO email_messages (
                provider, direction, provider_message_id, thread_id, from_email,
                to_emails, cc_emails, bcc_emails, subject, body_plain, body_html,
                status
            ) VALUES (%s,'outbound', NULL, %s, %s,
                      %s, %s, %s, %s, %s, %s, 'draft')
            RETURNING id
            """,
            (
                provider,
                thread_id,
                from_email,
                to,
                cc,
                bcc,
                subject,
                draft_text,
                body_html,
            ),
        )
        return cur.fetchone()[0]


def mark_outbound_sent(
    email_id: int,
    provider_message_id: str,
    provider_thread_id: Optional[str] = None,
) -> None:
    """Mark a draft message as sent and update provider identifiers."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE email_messages
               SET status='sent',
                   provider_message_id=%s,
                   last_action='send',
                   last_accessed_at=NOW()
             WHERE id=%s
            """,
            (provider_message_id, email_id),
        )
        if provider_thread_id:
            cur.execute(
                """
                INSERT INTO email_threads (provider, provider_thread_id)
                VALUES ((SELECT provider FROM email_messages WHERE id=%s), %s)
                ON CONFLICT DO NOTHING
                """,
                (email_id, provider_thread_id),
            )
