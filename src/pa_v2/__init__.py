"""Compatibility package exposing the public API for PA_V2.

This repository originally used a flat ``src/`` layout.  Some tests expect the
package to be importable as ``pa_v2`` so we provide lightweight wrappers that
re-export the existing modules.
"""

from .email_system.integration import send_email, get_latest_emails, EmailProviderRegistry

__all__ = [
    "send_email",
    "get_latest_emails",
    "EmailProviderRegistry",
]
