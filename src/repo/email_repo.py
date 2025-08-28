"""Repository for email storage, retrieval, and management."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Sequence

from db import get_conn


class EmailRepo:
    """Repository for managing email threads and messages."""
    
    def upsert_thread(self, provider: str, provider_thread_id: str, subject_last: Optional[str]) -> int:
        """Insert or update an email thread and return its internal ID."""
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO email_threads (provider, provider_thread_id, subject_last)
                VALUES (%s, %s, %s)
                ON CONFLICT (provider, provider_thread_id)
                DO UPDATE SET subject_last = COALESCE(EXCLUDED.subject_last, email_threads.subject_last),
                              updated_at = NOW()
                RETURNING id;
            """, (provider, provider_thread_id, subject_last))
            return cur.fetchone()[0]

    def upsert_email(self, provider: str, provider_message_id: str, provider_thread_id: str,
                     from_display: Optional[str], from_email: Optional[str],
                     to_emails: Sequence[str], cc_emails: Sequence[str], bcc_emails: Sequence[str],
                     subject: Optional[str], snippet: Optional[str],
                     body_plain: Optional[str], body_html: Optional[str],
                     received_at: Optional[datetime], tags: Sequence[str] = ()) -> int:
        """Insert or update an inbound email message and return its internal ID."""
        thread_id = self.upsert_thread(provider, provider_thread_id, subject)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO email_messages (
                  provider, provider_message_id, thread_id,
                  from_display, from_email, to_emails, cc_emails, bcc_emails,
                  subject, snippet, body_plain, body_html,
                  received_at, tags
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (provider, provider_message_id) DO NOTHING
                RETURNING id;
            """, (provider, provider_message_id, thread_id,
                  from_display, from_email, list(to_emails), list(cc_emails), list(bcc_emails),
                  subject, snippet, body_plain, body_html,
                  received_at, list(tags)))
            row = cur.fetchone()
            return row[0] if row else self.get_email_id(provider, provider_message_id)

    def get_email_id(self, provider: str, provider_message_id: str) -> Optional[int]:
        """Get the internal ID for an email by provider and message ID."""
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM email_messages WHERE provider=%s AND provider_message_id=%s",
                        (provider, provider_message_id))
            r = cur.fetchone()
            return r[0] if r else None

    def retention_cleanup(self, provider: str, keep: int = 10000) -> int:
        """Remove old emails keeping only the most recent `keep` messages per provider.
        
        Returns the number of messages deleted.
        """
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                WITH ranked AS (
                  SELECT id, ROW_NUMBER() OVER (ORDER BY received_at DESC NULLS LAST) as rn
                  FROM email_messages WHERE provider=%s AND direction='inbound'
                )
                DELETE FROM email_messages
                 WHERE id IN (SELECT id FROM ranked WHERE rn > %s)
                 RETURNING id;
            """, (provider, keep))
            deleted_rows = cur.fetchall()
            return len(deleted_rows)
    
    def get_recent_emails(self, provider: Optional[str] = None, limit: int = 50) -> List[dict]:
        """Get recent emails, optionally filtered by provider."""
        with get_conn() as conn, conn.cursor() as cur:
            if provider:
                cur.execute("""
                    SELECT provider, provider_message_id, from_display, from_email, 
                           subject, snippet, received_at, imported_at, status
                    FROM email_messages 
                    WHERE provider=%s AND direction='inbound'
                    ORDER BY received_at DESC NULLS LAST 
                    LIMIT %s
                """, (provider, limit))
            else:
                cur.execute("""
                    SELECT provider, provider_message_id, from_display, from_email, 
                           subject, snippet, received_at, imported_at, status
                    FROM email_messages 
                    WHERE direction='inbound'
                    ORDER BY received_at DESC NULLS LAST 
                    LIMIT %s
                """, (limit,))
            
            rows = cur.fetchall()
            return [
                {
                    'provider': row[0],
                    'provider_message_id': row[1], 
                    'from_display': row[2],
                    'from_email': row[3],
                    'subject': row[4],
                    'snippet': row[5],
                    'received_at': row[6],
                    'imported_at': row[7],
                    'status': row[8]
                }
                for row in rows
            ]

    # Legacy outbound email functions for backward compatibility
    def create_outbound_draft(
        self,
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
        self,
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


# Legacy function wrappers for backward compatibility
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
    """Legacy wrapper - use EmailRepo().create_outbound_draft() instead."""
    repo = EmailRepo()
    return repo.create_outbound_draft(
        provider, from_email, to, cc, bcc, subject, draft_text, body_html, thread_id
    )


def mark_outbound_sent(
    email_id: int,
    provider_message_id: str,
    provider_thread_id: Optional[str] = None,
) -> None:
    """Legacy wrapper - use EmailRepo().mark_outbound_sent() instead.""" 
    repo = EmailRepo()
    return repo.mark_outbound_sent(email_id, provider_message_id, provider_thread_id)
