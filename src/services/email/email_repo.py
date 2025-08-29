"""Repository for email storage, retrieval, and management."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Sequence

import sys
import os
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from core.database import get_conn


class EmailRepo:
    """Repository for email-related database operations"""

    def _subjects_are_related(self, subject1: str, subject2: str) -> bool:
        """Check if two subjects are related (same thread)"""
        if not subject1 or not subject2:
            return False
        
        # Remove common prefixes
        def clean_subject(s):
            s = s.strip()
            for prefix in ['Re:', 'RE:', 'Fwd:', 'FWD:', 'Fw:']:
                if s.startswith(prefix):
                    s = s[len(prefix):].strip()
            return s.lower()
        
        clean1 = clean_subject(subject1)
        clean2 = clean_subject(subject2)
        
        # Consider subjects related if they're the same after cleaning
        # or if one contains the other (allowing for slight variations)
        if clean1 == clean2:
            return True
        if clean1 in clean2 or clean2 in clean1:
            return True
        
        return False

    def upsert_thread(self, provider: str, provider_thread_id: str, subject_last: Optional[str]) -> int:
        """Insert or update an email thread and return its internal ID."""
        with get_conn() as conn, conn.cursor() as cur:
            # First, check if a thread with this provider_thread_id exists
            cur.execute("""
                SELECT id, subject_last FROM email_threads 
                WHERE provider = %s AND provider_thread_id = %s
            """, (provider, provider_thread_id))
            
            existing = cur.fetchone()
            if existing:
                thread_id, existing_subject = existing
                # Only update if subjects are similar or related
                if existing_subject and subject_last:
                    # Check if this is truly the same thread or a thread ID reuse
                    # If subjects are completely different, create a new thread with modified ID
                    if not self._subjects_are_related(existing_subject, subject_last):
                        # Create a new unique thread ID to avoid conflicts
                        import time
                        new_thread_id = f"{provider_thread_id}_{int(time.time())}"
                        cur.execute("""
                            INSERT INTO email_threads (provider, provider_thread_id, subject_last)
                            VALUES (%s, %s, %s)
                            RETURNING id;
                        """, (provider, new_thread_id, subject_last))
                        return cur.fetchone()[0]
                
                # Update existing thread with new subject if needed
                if subject_last and subject_last != existing_subject:
                    cur.execute("""
                        UPDATE email_threads SET subject_last = %s, updated_at = NOW()
                        WHERE id = %s
                    """, (subject_last, thread_id))
                return thread_id
            else:
                # Insert new thread
                cur.execute("""
                    INSERT INTO email_threads (provider, provider_thread_id, subject_last)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                """, (provider, provider_thread_id, subject_last))
                return cur.fetchone()[0]

    def upsert_email(self, provider: str, provider_message_id: str, provider_thread_id: str,
                     from_display: Optional[str], from_email: Optional[str],
                     to_emails: Sequence[str], cc_emails: Sequence[str], bcc_emails: Sequence[str],
                     subject: Optional[str], snippet: Optional[str],
                     body_plain: Optional[str], body_html: Optional[str],
                     received_at: Optional[datetime], tags: Sequence[str] = (),
                     internet_message_id: Optional[str] = None,
                     references_ids: Optional[Sequence[str]] = None) -> int:
        """Insert or update an inbound email message and return its internal ID."""
        thread_id = self.upsert_thread(provider, provider_thread_id, subject)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO email_messages (
                  provider, provider_message_id, thread_id,
                  from_display, from_email, to_emails, cc_emails, bcc_emails,
                  subject, snippet, body_plain, body_html,
                  received_at, tags, internet_message_id, references_ids
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (provider, provider_message_id) DO NOTHING
                RETURNING id;
            """, (provider, provider_message_id, thread_id,
                  from_display, from_email, list(to_emails), list(cc_emails), list(bcc_emails),
                  subject, snippet, body_plain, body_html,
                  received_at, list(tags), internet_message_id, list(references_ids or [])))
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
        """Remove old emails for a provider, keeping the most recent 'keep' count."""
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                DELETE FROM email_messages 
                WHERE provider = %s AND id NOT IN (
                    SELECT id FROM email_messages 
                    WHERE provider = %s 
                    ORDER BY received_at DESC, id DESC 
                    LIMIT %s
                )
            """, (provider, provider, keep))
            return cur.rowcount

    def get_recent_emails(self, provider: Optional[str] = None, limit: int = 50) -> List[dict]:
        """Get recent emails, optionally filtered by provider."""
        with get_conn() as conn, conn.cursor() as cur:
            if provider:
                cur.execute("""
                    SELECT id, provider, from_display, from_email, subject, received_at, snippet 
                    FROM email_messages 
                    WHERE provider = %s 
                    ORDER BY received_at DESC, id DESC 
                    LIMIT %s
                """, (provider, limit))
            else:
                cur.execute("""
                    SELECT id, provider, from_display, from_email, subject, received_at, snippet 
                    FROM email_messages 
                    ORDER BY received_at DESC, id DESC 
                    LIMIT %s
                """, (limit,))
            
            rows = cur.fetchall()
            return [
                {
                    "id": row[0],
                    "provider": row[1],
                    "from_display": row[2],
                    "from_email": row[3], 
                    "subject": row[4],
                    "received_at": row[5],
                    "snippet": row[6]
                }
                for row in rows
            ]

    # New methods for telegram digest functionality
    def mark_important(self, email_id: int) -> None:
        """Mark an email as important."""
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                UPDATE email_messages 
                SET tags = ARRAY_APPEND(tags, 'important')
                WHERE id = %s AND NOT ('important' = ANY(tags))
            """, (email_id,))

    # ---- Notification helpers ----
    def mark_notified(self, email_id: int) -> None:
        """Mark an email as notified in tags to avoid duplicate Telegram sends."""
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE email_messages
                   SET tags = ARRAY_APPEND(tags, 'notified'),
                       last_accessed_at = NOW()
                 WHERE id = %s AND NOT ('notified' = ANY(tags))
                """,
                (email_id,),
            )

    def list_recent_unnotified(self, since_hours: int = 24, limit: int = 50) -> List[dict]:
        """Return recent inbound emails missing the 'notified' tag."""
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT em.id, em.provider, em.from_display, em.from_email,
                       em.subject, em.snippet, em.received_at
                  FROM email_messages em
                 WHERE em.direction = 'inbound'
                   AND em.received_at >= NOW() - (%s || ' hours')::INTERVAL
                   AND (em.tags IS NULL OR NOT ('notified' = ANY(em.tags)))
                 ORDER BY em.received_at ASC
                 LIMIT %s
                """,
                (since_hours, limit),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "provider": r[1],
                    "from_display": r[2],
                    "from_email": r[3],
                    "subject": r[4],
                    "snippet": r[5],
                    "received_at": r[6],
                }
                for r in rows
            ]

    def touch(self, email_id: int) -> None:
        """Update last_accessed_at timestamp for an email."""
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                UPDATE email_messages 
                SET last_accessed_at = NOW()
                WHERE id = %s
            """, (email_id,))

    def get_email_detail(self, email_id: int) -> Optional[dict]:
        """Get detailed email information by ID."""
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT provider, provider_message_id, thread_id, 
                       from_display, from_email, to_emails, cc_emails, bcc_emails,
                       subject, snippet, body_plain, body_html, received_at, tags,
                       internet_message_id, references_ids
                FROM email_messages 
                WHERE id = %s
            """, (email_id,))
            row = cur.fetchone()
            if not row:
                return None
            
            return {
                "id": email_id,
                "provider": row[0],
                "provider_message_id": row[1],
                "thread_id": row[2],
                "from_display": row[3],
                "from_email": row[4],
                "to_emails": row[5],
                "cc_emails": row[6],
                "bcc_emails": row[7],
                "subject": row[8],
                "snippet": row[9],
                "body_plain": row[10],
                "body_html": row[11],
                "received_at": row[12],
                "tags": row[13],
                "internet_message_id": row[14],
                "references_ids": row[15]
            }

    def add_draft(self, email_id: int, draft_text: str) -> int:
        """Add a draft reply to an email thread."""
        with get_conn() as conn, conn.cursor() as cur:
            # Get thread info from original email
            cur.execute("""
                SELECT provider, thread_id, from_email, subject
                FROM email_messages 
                WHERE id = %s
            """, (email_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Email {email_id} not found")
            
            provider, thread_id, reply_to_email, original_subject = row
            subject = f"Re: {original_subject}" if not original_subject.startswith("Re:") else original_subject
            
            # Insert draft reply
            cur.execute("""
                INSERT INTO email_drafts (
                    provider, thread_id, reply_to_email_id, subject, body_plain, status
                ) VALUES (%s, %s, %s, %s, %s, 'draft')
                RETURNING id
            """, (provider, thread_id, email_id, subject, draft_text))
            return cur.fetchone()[0]

    def latest_new_messages(self, limit: int = 20) -> List[dict]:
        """Get latest new messages for digest."""
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT em.id, em.provider, em.from_display, em.from_email, 
                       em.subject, em.snippet, em.received_at,
                       et.provider_thread_id
                FROM email_messages em
                JOIN email_threads et ON em.thread_id = et.id
                WHERE em.direction = 'inbound'
                  AND em.received_at >= NOW() - INTERVAL '24 hours'
                ORDER BY em.received_at DESC
                LIMIT %s
            """, (limit,))
            
            rows = cur.fetchall()
            return [
                {
                    "id": row[0],
                    "provider": row[1],
                    "from_display": row[2],
                    "from_email": row[3],
                    "subject": row[4],
                    "snippet": row[5],
                    "received_at": row[6],
                    "provider_thread_id": row[7]
                }
                for row in rows
            ]

    def mark_thread_deleted(self, provider: str, provider_thread_id: str) -> None:
        """Mark a thread as deleted."""
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                UPDATE email_threads 
                SET deleted_at = NOW()
                WHERE provider = %s AND provider_thread_id = %s
            """, (provider, provider_thread_id))

    def restore_thread_deleted(self, provider: str, provider_thread_id: str) -> None:
        """Restore a deleted thread."""
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                UPDATE email_threads 
                SET deleted_at = NULL
                WHERE provider = %s AND provider_thread_id = %s
            """, (provider, provider_thread_id))

    def get_email_row(self, email_id: int) -> Optional[dict]:
        """Get email row data for digest display."""
        return self.get_email_detail(email_id)

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

    def get_latest_email_by_provider(self, provider: str):
        """Get the most recent email for a provider."""
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT provider_message_id, received_at 
                FROM email_messages 
                WHERE provider = %s 
                ORDER BY received_at DESC, id DESC 
                LIMIT 1
            """, (provider,))
            row = cur.fetchone()
            if row:
                from types import SimpleNamespace
                return SimpleNamespace(
                    provider_message_id=row[0],
                    received_at=row[1]
                )
            return None

    def get_recent_emails_by_provider(self, provider: str, limit: int = 100):
        """Get recent emails for a provider."""
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT provider_message_id 
                FROM email_messages 
                WHERE provider = %s 
                ORDER BY received_at DESC, id DESC 
                LIMIT %s
            """, (provider, limit))
            rows = cur.fetchall()
            from types import SimpleNamespace
            return [SimpleNamespace(provider_message_id=row[0]) for row in rows]


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
    repo.mark_outbound_sent(email_id, provider_message_id, provider_thread_id)
