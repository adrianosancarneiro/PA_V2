# email_integration.py
"""
Unified email integration module that provides a plugin-based email sending system.
This module makes it easy to add new email providers in the future.
"""

import importlib
import os
import sys
from typing import Dict, List, Optional, Any, Union

from .filtering import filter_emails

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
def get_latest_emails(provider: str, count: int = 10, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
            result = email_provider.get_latest_emails(count)
            if result.get("success") and filters:
                emails = result.get("emails", [])
                result["emails"] = filter_emails(emails, **filters)
            return result
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
    **kwargs
) -> Dict[str, Any]:
    """
    Send an email using the specified provider
    
    Args:
        provider (str): The name of the email provider to use
        to (str): Recipient email address
        subject (str): Email subject
        body (str): Email body (plain text)
        html_body (Optional[str]): Email body in HTML format
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
            "message": f"Unknown email provider: {provider}. Available providers: {available_providers}"
        }
    
    # Send the email
    try:
        return email_provider.send_email(to, subject, body, html_body, **kwargs)
    except Exception as e:
        return {
            "success": False,
            "message": f"Error sending email via {provider}: {str(e)}"
        }

# Auto-discover and register providers
def _discover_providers():
    """Automatically discover and register email providers"""
    providers_dir = os.path.join(os.path.dirname(__file__), "providers")
    
    if not os.path.exists(providers_dir):
        print(f"Warning: Providers directory not found: {providers_dir}")
        return
    
    # Get all Python files in the providers directory
    for filename in os.listdir(providers_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = filename[:-3]  # Remove .py extension
            
            try:
                # Import the module
                module = importlib.import_module(f'.providers.{module_name}', package=__package__)
                
                # Look for provider classes in the module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    
                    # Check if it's a class that might be a provider
                    if (isinstance(attr, type) and 
                        hasattr(attr, 'get_name') and
                        hasattr(attr, 'send_email') and
                        attr_name.endswith('Provider')):
                        
                        try:
                            # Try to instantiate and register the provider
                            provider_instance = attr()
                            EmailProviderRegistry.register(provider_instance)
                        except Exception as e:
                            print(f"Warning: Could not register provider {attr_name}: {e}")
                            
            except Exception as e:
                print(f"Warning: Could not import provider module {module_name}: {e}")

# Initialize providers when module is imported
_discover_providers()
