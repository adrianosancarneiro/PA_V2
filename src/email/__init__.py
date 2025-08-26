"""
Email module for PA_V2
Provides email integration capabilities with multiple providers.
"""

from .integration import EmailProviderRegistry, send_email, get_latest_emails

__all__ = ['EmailProviderRegistry', 'send_email', 'get_latest_emails']
