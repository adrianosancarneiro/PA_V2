# email_integration.py
"""
Unified email integration module that provides a plugin-based email sending system.
This module makes it easy to add new email providers in the future.
"""

import importlib
import os
import sys
from typing import Dict, List, Optional, Any, Union

# Define provider interface
class EmailProviderInterface:
    @staticmethod
    def get_name() -> str:
        """Return the name of the provider"""
        raise NotImplementedError("Provider must implement get_name()")
    
    @staticmethod
    def send_email(to_addr: str, subject: str, body: str, html_body: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Send an email and return result information"""
        raise NotImplementedError("Provider must implement send_email()")
    
    def get_latest_emails(self, count: int = 10) -> Dict[str, Any]:
        """Get the latest emails from the inbox (optional method)"""
        return {
            "success": False,
            "message": f"Email reading not supported by {self.get_name()} provider",
            "provider": self.get_name()
        }

# Provider registry
class EmailProviderRegistry:
    _providers: Dict[str, EmailProviderInterface] = {}
    
    @classmethod
    def register(cls, provider: EmailProviderInterface) -> None:
        """Register a new email provider"""
        provider_name = provider.get_name()
        cls._providers[provider_name] = provider
        print(f"Registered email provider: {provider_name}")
    
    @classmethod
    def get_provider(cls, name: str) -> Optional[EmailProviderInterface]:
        """Get a provider by name"""
        return cls._providers.get(name.lower())
    
    @classmethod
    def get_all_providers(cls) -> List[str]:
        """Get list of all registered provider names"""
        return list(cls._providers.keys())

# Main email reading function
def get_latest_emails(provider: str, count: int = 10) -> Dict[str, Any]:
    """
    Get latest emails from the specified provider
    
    Args:
        provider (str): The name of the email provider to use
        count (int): Number of emails to retrieve (default: 10)
        
    Returns:
        dict: Result information including success status, message, and emails list
    """
    provider = provider.lower()
    
    # Get the requested provider
    email_provider = EmailProviderRegistry.get_provider(provider)
    
    if not email_provider:
        available_providers = ", ".join(EmailProviderRegistry.get_all_providers())
        return {
            "success": False,
            "message": f"Unknown email provider: {provider}. Available providers: {available_providers}",
            "error": "Unknown provider"
        }
    
    try:
        # Check if provider supports email reading
        if hasattr(email_provider, 'get_latest_emails'):
            return email_provider.get_latest_emails(count)
        else:
            return {
                "success": False,
                "message": f"Provider '{provider}' does not support email reading",
                "provider": provider,
                "error": "Feature not supported"
            }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting emails from {provider}: {str(e)}",
            "provider": provider,
            "error": str(e)
        }

# Main email sending function
def send_email(
    provider: str, 
    to: str, 
    subject: str, 
    body: str, 
    html_body: Optional[str] = None, 
    fallback_providers: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Send an email using the specified provider
    
    Args:
        provider (str): The name of the email provider to use
        to (str): Recipient email address
        subject (str): Email subject
        body (str): Plain text email body
        html_body (str, optional): HTML version of the email body
        fallback_providers (list, optional): List of provider names to try if the main provider fails
        **kwargs: Additional provider-specific arguments
        
    Returns:
        dict: Result information including success status and message
    """
    provider = provider.lower()
    
    # Get the requested provider
    email_provider = EmailProviderRegistry.get_provider(provider)
    
    if not email_provider:
        available_providers = ", ".join(EmailProviderRegistry.get_all_providers())
        return {
            "success": False,
            "message": f"Unknown email provider: {provider}. Available providers: {available_providers}",
            "error": "Unknown provider"
        }
    
    try:
        # Try the main provider
        result = email_provider.send_email(to, subject, body, html_body, **kwargs)
        
        # If it fails and we have fallback providers, try them in order
        if not result["success"] and fallback_providers:
            for fallback_provider in fallback_providers:
                print(f"{provider} failed. Trying fallback provider: {fallback_provider}")
                fallback = EmailProviderRegistry.get_provider(fallback_provider)
                if fallback:
                    fallback_result = fallback.send_email(to, subject, body, html_body, **kwargs)
                    if fallback_result["success"]:
                        return fallback_result
            
        return result
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error sending email with {provider}: {str(e)}",
            "provider": provider,
            "error": str(e)
        }

# Load providers from plugins directory
def load_provider_plugins(plugins_dir: str = "email_plugins") -> None:
    """
    Load email provider plugins from the plugins directory
    
    Args:
        plugins_dir (str): Directory containing provider plugins
    """
    if not os.path.exists(plugins_dir):
        print(f"Warning: Plugins directory '{plugins_dir}' does not exist.")
        return
        
    # Add plugins directory to Python path
    plugins_path = os.path.abspath(plugins_dir)
    if plugins_path not in sys.path:
        sys.path.insert(0, plugins_path)
    
    print(f"Loading email providers from {plugins_dir}...")
    for filename in os.listdir(plugins_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = filename[:-3]  # Remove .py extension
            try:
                module = importlib.import_module(module_name)
                
                # Look for provider classes in the module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    
                    # Check if it's a class and has the required methods
                    if (isinstance(attr, type) and 
                        hasattr(attr, "get_name") and 
                        hasattr(attr, "send_email")):
                        
                        # Create an instance and register the provider
                        try:
                            provider_instance = attr()
                            EmailProviderRegistry.register(provider_instance)
                        except Exception as e:
                            print(f"Error creating instance of {attr_name}: {e}")
                        
            except ImportError as e:
                print(f"Error loading provider plugin {module_name}: {e}")

# Load all provider plugins
load_provider_plugins()

# For backwards compatibility with old code
try:
    import send_gmail
    import send_outlook
    
    print("Maintaining backward compatibility with legacy modules...")
    
    def legacy_gmail_send(to_addr, subject, body):
        """Legacy Gmail send function for backward compatibility"""
        result = send_email("gmail", to_addr, subject, body)
        return result["message"] if result["success"] else result["error"]
    
    def legacy_outlook_send(to_addr, subject, body):
        """Legacy Outlook send function for backward compatibility"""
        result = send_email("outlook", to_addr, subject, body)
        return result["message"] if result["success"] else result["error"]
        
    # Replace legacy functions with wrapper functions
    if hasattr(send_gmail, "send_email"):
        original_gmail_send = send_gmail.send_email
        send_gmail.send_email = lambda to, subject, html, plain=None: legacy_gmail_send(to, subject, plain or "")
        
    if hasattr(send_outlook, "send_email"):
        original_outlook_send = send_outlook.send_email
        send_outlook.send_email = lambda to, subject, body: legacy_outlook_send(to, subject, body)
        
except ImportError:
    print("Legacy modules not found. No backward compatibility needed.")

if __name__ == "__main__":
    # Command-line interface
    import argparse
    
    parser = argparse.ArgumentParser(description="Send and read emails through different providers")
    parser.add_argument("--provider", "-p", 
                        help="Email provider to use")
    parser.add_argument("--to", "-t", 
                        help="Recipient email address (for sending)")
    parser.add_argument("--subject", "-s", 
                        help="Email subject (for sending)")
    parser.add_argument("--body", "-b", 
                        help="Email body text (for sending)")
    parser.add_argument("--html", 
                        help="HTML version of the email body (for sending)")
    parser.add_argument("--get-emails", "-g", action="store_true",
                        help="Get latest emails instead of sending")
    parser.add_argument("--count", "-c", type=int, default=10,
                        help="Number of emails to retrieve (default: 10)")
    parser.add_argument("--list-providers", action="store_true",
                        help="List available email providers")
    parser.add_argument("--test", action="store_true",
                        help="Run interactive test mode for both providers")
    
    args = parser.parse_args()
    
    if args.list_providers:
        providers = EmailProviderRegistry.get_all_providers()
        if providers:
            print("Available email providers:")
            for provider in providers:
                print(f"  - {provider}")
        else:
            print("No email providers available. Check the email_plugins directory.")
        sys.exit(0)
    
    if args.test:
        # Interactive test mode
        providers = EmailProviderRegistry.get_all_providers()
        if not providers:
            print("No email providers available. Check the email_plugins directory.")
            sys.exit(1)
        
        print("="*60)
        print("EMAIL INTEGRATION TEST MODE")
        print("="*60)
        print(f"Available providers: {', '.join(providers)}")
        
        for provider in providers:
            print(f"\n{'='*40}")
            print(f"Testing Provider: {provider.upper()}")
            print(f"{'='*40}")
            
            # Test email reading
            print(f"\n📥 Testing email reading for {provider}...")
            result = get_latest_emails(provider, count=3)
            if result['success']:
                print(f"✅ {result['message']}")
                if 'emails' in result and result['emails']:
                    for i, email in enumerate(result['emails'][:3], 1):
                        print(f"\n{i}. {email.get('subject', 'No Subject')}")
                        print(f"   From: {email.get('from', 'Unknown')}")
                        print(f"   Date: {email.get('received_date', 'Unknown')}")
                        if 'body_preview' in email:
                            preview = email['body_preview'][:100]
                            print(f"   Preview: {preview}...")
            else:
                print(f"❌ {result['message']}")
            
            # Test email sending
            test_email = input(f"\nEnter email address to test sending with {provider} (or press Enter to skip): ").strip()
            if test_email:
                print(f"\n📤 Testing email sending for {provider}...")
                result = send_email(
                    provider=provider,
                    to=test_email,
                    subject=f"Test Email from {provider.title()} Provider",
                    body=f"This is a test email sent using the {provider} provider through the email integration system.",
                    html_body=f"""
                    <h2>Test Email from {provider.title()} Provider</h2>
                    <p>This is a test email sent using the <strong>{provider}</strong> provider through the email integration system.</p>
                    <p><em>Sent via Python email integration</em></p>
                    """
                )
                
                if result['success']:
                    print(f"✅ {result['message']}")
                else:
                    print(f"❌ {result['message']}")
            else:
                print(f"Skipping email sending test for {provider}")
        
        print(f"\n{'='*60}")
        print("TEST COMPLETED")
        print(f"{'='*60}")
        sys.exit(0)
    
    # Email reading mode
    if args.get_emails:
        if not args.provider:
            providers = EmailProviderRegistry.get_all_providers()
            if not providers:
                print("No email providers available. Check the email_plugins directory.")
                sys.exit(1)
            print("Available providers:", ", ".join(providers))
            provider = input("Provider: ").strip() or providers[0]
        else:
            provider = args.provider
            
        result = get_latest_emails(provider, args.count)
        
        if result["success"]:
            print(f"✅ {result['message']}")
            if 'emails' in result and result['emails']:
                print(f"\nLatest {len(result['emails'])} emails:")
                for i, email in enumerate(result['emails'], 1):
                    print(f"\n{i}. Subject: {email.get('subject', 'No Subject')}")
                    print(f"   From: {email.get('from_name', 'Unknown')} <{email.get('from', 'Unknown')}>")
                    print(f"   Date: {email.get('received_date', 'Unknown')}")
                    print(f"   Read: {'Yes' if email.get('is_read', False) else 'No'}")
                    if 'body_preview' in email:
                        preview = email['body_preview'][:150]
                        print(f"   Preview: {preview}...")
        else:
            print(f"❌ {result['message']}")
            sys.exit(1)
        sys.exit(0)
    
    # Email sending mode (existing functionality)
    if not args.provider or not args.to or not args.subject or not args.body:
        providers = EmailProviderRegistry.get_all_providers()
        if not providers:
            print("No email providers available. Check the email_plugins directory.")
            sys.exit(1)
            
        print("Available providers:", ", ".join(providers))
        provider = input("Provider: ").strip() or "gmail"
        to = input("Send to: ").strip()
        subject = input("Subject: ").strip()
        body = input("Body: ").strip()
        html_body = input("HTML body (optional): ").strip() or None
        
        result = send_email(
            provider=provider,
            to=to,
            subject=subject,
            body=body,
            html_body=html_body
        )
    else:
        result = send_email(
            provider=args.provider,
            to=args.to,
            subject=args.subject,
            body=args.body,
            html_body=args.html
        )
    
    if result["success"]:
        print(f"✅ {result['message']}")
        sys.exit(0)
    else:
        print(f"❌ {result['message']}")
        sys.exit(1)
