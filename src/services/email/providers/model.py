"""Data model for normalized email structures.

The :class:`NormalizedEmail` dataclass defines the canonical shape used by
our application to represent email messages fetched from different
providers. By ensuring that both Gmail and Outlook mappers emit this same
structure we can treat emails uniformly throughout the codebase.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class NormalizedEmail:
    """Provider-agnostic representation of an email message."""

    id: str
    """Provider-specific message identifier."""

    thread_id: str
    """Provider-specific thread/conversation identifier."""

    from_name: Optional[str]
    """Display name of the sender if available."""

    from_email: Optional[str]
    """Email address of the sender."""

    to_emails: List[str]
    """List of primary recipient email addresses."""

    cc_emails: List[str]
    """List of CC recipient email addresses."""

    bcc_emails: List[str]
    """List of BCC recipient email addresses."""

    subject: Optional[str]
    """Email subject line."""

    snippet: Optional[str]
    """Short preview snippet or summary of the email body."""

    body_text: Optional[str]
    """Plain text body of the email, if available."""

    body_html: Optional[str]
    """HTML body of the email, if available."""

    received_at: Optional[datetime]
    """Timestamp when the email was received."""

    provider: str
    """Name of the provider that supplied this message (e.g. ``"gmail"``)."""

    internet_message_id: Optional[str] = None
    """Original Internet Message-ID header for cross-provider threading."""

    references_ids: List[str] = None
    """List of message IDs from References header for threading."""

    def __post_init__(self):
        """Initialize default values for optional fields."""
        if self.references_ids is None:
            self.references_ids = []
