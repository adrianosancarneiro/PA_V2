"""Re-export provider implementations for compatibility."""

from email_system.providers.dummy_provider import DummyProvider  # noqa: F401
from email_system.providers.gmail_provider import GmailProvider  # noqa: F401
from email_system.providers.outlook_provider import OutlookGraphProvider  # noqa: F401

__all__ = ["DummyProvider", "GmailProvider", "OutlookGraphProvider"]
