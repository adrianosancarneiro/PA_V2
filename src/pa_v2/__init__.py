"""
PA_V2 - Personal Assistant Version 2
Main source package for the Personal Assistant application.
"""

__version__ = "0.1.0"

from .email_system import EmailProviderRegistry, send_email, get_latest_emails

__all__ = ['EmailProviderRegistry', 'send_email', 'get_latest_emails']
