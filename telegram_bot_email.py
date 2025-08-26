"""
Bot-friendly email functions for Telegram integration.
These functions are designed to work without user interaction.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from email_integration import get_latest_emails, send_email
from email_plugins.gmail_provider import GmailProvider
from email_plugins.outlook_provider import OutlookGraphProvider

def check_email_auth_status():
    """Check authentication status for both providers"""
    status = {}
    
    try:
        gmail = GmailProvider()
        status['gmail'] = gmail.is_authenticated()
    except Exception as e:
        status['gmail'] = False
        status['gmail_error'] = str(e)
    
    try:
        outlook = OutlookGraphProvider()
        status['outlook'] = outlook.is_authenticated()
    except Exception as e:
        status['outlook'] = False
        status['outlook_error'] = str(e)
    
    return status

def bot_get_emails(provider="gmail", count=10):
    """
    Get emails for bot use (non-interactive)
    
    Args:
        provider (str): "gmail" or "outlook"
        count (int): Number of emails to retrieve
        
    Returns:
        dict: Result with emails or error info
    """
    result = get_latest_emails(provider, count)
    
    # If authentication is required, add helpful info
    if not result.get('success') and 'requires_auth' in result:
        result['setup_needed'] = True
        result['setup_command'] = f"Run: python setup_email_auth.py"
    
    return result

def bot_send_email(provider="gmail", to_addr="", subject="", body="", html_body=None):
    """
    Send email for bot use (non-interactive)
    
    Args:
        provider (str): "gmail" or "outlook"
        to_addr (str): Recipient email
        subject (str): Email subject
        body (str): Email body
        html_body (str): HTML email body (optional)
        
    Returns:
        dict: Result with success info or error
    """
    result = send_email(provider, to_addr, subject, body, html_body)
    
    # If authentication is required, add helpful info
    if not result.get('success') and 'requires_auth' in result:
        result['setup_needed'] = True
        result['setup_command'] = f"Run: python setup_email_auth.py"
    
    return result

def get_available_providers():
    """Get list of available and authenticated providers"""
    from email_integration import EmailProviderRegistry
    
    all_providers = EmailProviderRegistry.get_all_providers()
    auth_status = check_email_auth_status()
    
    providers_info = {}
    for provider in all_providers:
        if provider in ['gmail', 'outlook']:  # Skip dummy provider
            providers_info[provider] = {
                'available': True,
                'authenticated': auth_status.get(provider, False),
                'error': auth_status.get(f'{provider}_error', None)
            }
    
    return providers_info

# Example usage for your Telegram bot:
if __name__ == "__main__":
    # Check what's available
    print("📧 EMAIL PROVIDERS STATUS:")
    providers = get_available_providers()
    for name, info in providers.items():
        auth_status = "✅ Ready" if info['authenticated'] else "❌ Setup needed"
        print(f"  {name}: {auth_status}")
    
    # Example: Get Gmail emails (non-interactive)
    print("\n📥 TESTING EMAIL RETRIEVAL:")
    result = bot_get_emails("gmail", 3)
    if result['success']:
        print(f"✅ Retrieved {len(result.get('emails', []))} emails")
        for i, email in enumerate(result.get('emails', [])[:2], 1):
            print(f"  {i}. {email['subject']} - {email['from']}")
    else:
        print(f"❌ {result['message']}")
        if result.get('setup_needed'):
            print(f"💡 {result['setup_command']}")
