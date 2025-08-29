"""Repository for managing push webhook and delta state."""
from typing import Optional
import sys
import os
import pathlib

# Add project root to path  
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from core.database import get_conn


class PushRepo:
    """Repository for managing Gmail push webhooks and Outlook delta state."""
    
    def _ensure_row(self, provider: str):
        """Ensure a row exists for the given provider."""
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
              INSERT INTO provider_push_state (provider, push_state)
              VALUES (%s, 'down') ON CONFLICT (provider) DO NOTHING
            """, (provider,))

    # ---- Gmail Push Webhooks ----
    def get_gmail_last_history_id(self) -> Optional[int]:
        """Get the last Gmail history ID we processed."""
        self._ensure_row("gmail")
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT gmail_last_history_id FROM provider_push_state WHERE provider='gmail'")
            r = cur.fetchone()
            return r[0] if r else None

    def set_gmail_last_history_id(self, hid: int):
        """Update the last Gmail history ID we processed."""
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
              UPDATE provider_push_state
                 SET gmail_last_history_id=%s, last_pubsub_at=NOW(), push_state='healthy'
               WHERE provider='gmail'
            """, (hid,))

    def update_gmail_watch(self, expires_at):
        """Update Gmail watch expiration time."""
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
              UPDATE provider_push_state SET gmail_watch_expires_at=%s WHERE provider='gmail'
            """, (expires_at,))

    def touch_pubsub(self):
        """Update last pubsub received timestamp."""
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
              UPDATE provider_push_state SET last_pubsub_at=NOW(), push_state='healthy'
               WHERE provider='gmail'
            """)

    # ---- Outlook Delta Link ----
    def get_outlook_delta_link(self) -> Optional[str]:
        """Get the Outlook Graph delta link for incremental sync."""
        self._ensure_row("outlook")
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT graph_delta_link FROM provider_push_state WHERE provider='outlook'")
            r = cur.fetchone()
            return r[0] if r else None

    def set_outlook_delta_link(self, link: str):
        """Update the Outlook Graph delta link."""
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
              UPDATE provider_push_state SET graph_delta_link=%s, last_poll_at=NOW()
               WHERE provider='outlook'
            """, (link,))

    def touch_poll(self, provider: str):
        """Update last poll timestamp for a provider."""
        self._ensure_row(provider)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("UPDATE provider_push_state SET last_poll_at=NOW() WHERE provider=%s", (provider,))

    # ---- General State ----
    def get_push_state(self, provider: str) -> Optional[str]:
        """Get the current push state for a provider."""
        self._ensure_row(provider)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT push_state FROM provider_push_state WHERE provider=%s", (provider,))
            r = cur.fetchone()
            return r[0] if r else None

    def set_push_state(self, provider: str, state: str):
        """Set the push state for a provider."""
        if state not in ['healthy', 'degraded', 'down']:
            raise ValueError(f"Invalid push state: {state}")
        
        self._ensure_row(provider)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
              UPDATE provider_push_state SET push_state=%s, updated_at=NOW() WHERE provider=%s
            """, (state, provider))
