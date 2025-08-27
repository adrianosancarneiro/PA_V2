
"""
Outlook email provider plugin for the email integration system.
Uses Microsoft Graph API with OAuth2 Device Code flow for BYU email integration.
"""
import os
import json
import pathlib
import msal
import requests
from typing import Dict, Any, Optional, List

# Try to load environment variables with fallback
try:
    from dotenv import load_dotenv
    # Load environment variables from system secrets file
    load_dotenv('/etc/pa_v2/secrets.env')
except ImportError:
    print("Warning: python-dotenv not available. Using system environment variables only.")
    # dotenv is not available, will use os.getenv directly

class OutlookGraphProvider:
    """Outlook email provider using Microsoft Graph API for BYU integration"""
    
    def __init__(self):
        # Load configuration from environment variables
        self.tenant = os.getenv('BYU_TENANT', 'byu.edu')
        self.client_id = os.getenv('BYU_CLIENT_ID')
        self.user_email = os.getenv('BYU_USER')

        if not self.client_id:
            raise ValueError("BYU_CLIENT_ID not found in environment variables")

        self.scopes = [
            "https://graph.microsoft.com/Mail.ReadWrite",
            "https://graph.microsoft.com/Mail.Send",
        ]

        # Store token cache in config directory (same as Gmail)
        # Always use absolute path to the project config directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        config_dir = pathlib.Path(
            os.getenv("CONFIG_DIR", os.path.join(project_root, "config"))
        ).resolve()
        config_dir.mkdir(parents=True, exist_ok=True)
        self.token_cache_file = str(config_dir / "byu_outlook_token_cache.json")
        print(f"📂 Using Outlook token cache file: {self.token_cache_file}")

        # Initialize MSAL-related placeholders
        self._app = None
        self._cache = None
        self._save_cache_fn = None
    
    def get_name(self):
        return "outlook"
    
    def _get_msal_app(self):
        """Initialize MSAL application with persistent token cache"""
        # Create cache if not already done
        if self._cache is None:
            self._cache = msal.SerializableTokenCache()

        # Load existing cache from disk (this is safe to call repeatedly)
        if os.path.exists(self.token_cache_file):
            try:
                with open(self.token_cache_file, 'r') as f:
                    data = f.read()
                    if data:
                        self._cache.deserialize(data)
                        # Print debug info on token cache
                        print(f"🔍 Loaded token cache from {self.token_cache_file} (size: {len(data)} bytes)")
            except Exception as e:
                print(f"⚠️ Warning: Could not load token cache: {e}")
        else:
            print(f"⚠️ No token cache file found at {self.token_cache_file}")

        if self._app is None:
            self._app = msal.PublicClientApplication(
                self.client_id,
                authority=f"https://login.microsoftonline.com/{self.tenant}",
                token_cache=self._cache
            )
            
            # Save cache when it changes
            def save_cache():
                if not self._cache:
                    return
                # MSAL SerializableTokenCache.has_state_changed can be a property or a method depending on version
                try:
                    changed_attr = getattr(self._cache, 'has_state_changed', None)
                    changed = False
                    if callable(changed_attr):
                        changed = bool(changed_attr())
                    elif isinstance(changed_attr, bool):
                        changed = changed_attr
                    else:
                        # Fallback: assume changed and write once
                        changed = True
                except Exception:
                    changed = True

                if changed:
                    try:
                        with open(self.token_cache_file, 'w') as f:
                            data = self._cache.serialize()
                            f.write(data)
                            print(f"💾 Saved token cache to {self.token_cache_file} (size: {len(data)} bytes)")
                    except Exception as e:
                        print(f"Warning: Could not save token cache: {e}")
            
            # Note: add_remove_callback not available in all MSAL versions
            # We'll manually save the cache after token operations
            self._save_cache_fn = save_cache
            
        return self._app
    
    def _get_access_token(self, interactive=True):
        """Get access token using device code flow or cached token
        
        Args:
            interactive (bool): Whether to allow interactive authentication
            
        Returns:
            str: Access token or None if authentication fails
        """
        app = self._get_msal_app()
        
        # Try to get token silently first (from cache)
        accounts = app.get_accounts()
        if accounts:
            print("🔄 Attempting to use cached token...")
            result = app.acquire_token_silent(self.scopes, account=accounts[0])
            if result and "access_token" in result:
                print("✅ Using cached token successfully!")
                # Save cache in case token was refreshed
                if hasattr(self, '_save_cache_fn'):
                    self._save_cache_fn()
                return result["access_token"]
            else:
                print("⚠️ Cached token expired or invalid")
        
        # If not interactive mode (for Telegram bot), return None
        if not interactive:
            print("❌ No valid cached token available and interactive mode disabled")
            return None
        
        # If silent acquisition fails, use device code flow
        print("\n" + "="*60)
        print("BYU OUTLOOK AUTHENTICATION REQUIRED")
        print("="*60)
        print("💡 This is a one-time setup. Tokens will be cached for future use.")
        
        try:
            flow = app.initiate_device_flow(scopes=self.scopes)
            if "user_code" not in flow:
                error_msg = flow.get("error_description", "Device flow could not be created")
                raise ValueError(f"Device flow error: {error_msg}")
            
            print(f"📱 Go to: {flow['verification_uri']}")
            print(f"🔑 Enter code: {flow['user_code']}")
            print("\n🏫 You'll be redirected to BYU login page")
            print("🔐 Complete authentication with your BYU credentials")
            print("📁 Token will be saved for future automatic use")
            print("⏳ Waiting for authentication...")
            
            # Wait for user to complete authentication
            result = app.acquire_token_by_device_flow(flow)
            
            if "access_token" in result:
                print("✅ BYU authentication successful!")
                print("💾 Token cached for future use")
                # Manually save the cache since auto-callback isn't available
                if hasattr(self, '_save_cache_fn'):
                    self._save_cache_fn()
                return result["access_token"]
            else:
                error_msg = result.get("error_description", result.get("error", "Unknown error"))
                raise Exception(f"Authentication failed: {error_msg}")
                
        except Exception as e:
            raise Exception(
                f"BYU Microsoft authentication failed: {str(e)}\n\n"
                "⚠️  This might be because:\n"
                "1. The BYU client ID doesn't have the right permissions\n"
                "2. You need to contact BYU OIT for proper app registration\n"
                "3. Your BYU account doesn't have access to this application\n\n"
                "💡 Contact BYU OIT for assistance with Azure app registration."
            )
    
    def setup_authentication(self) -> Dict[str, Any]:
        """Setup authentication interactively (run this once)"""
        try:
            access_token = self._get_access_token(interactive=True)
            if access_token:
                return {
                    "success": True,
                    "message": "BYU Outlook: Authentication setup completed successfully!",
                    "provider": "outlook"
                }
            else:
                return {
                    "success": False,
                    "message": "BYU Outlook: Authentication setup failed",
                    "provider": "outlook"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"BYU Outlook setup error: {str(e)}",
                "provider": "outlook"
            }
    
    def is_authenticated(self):
        """Check if we have valid cached credentials"""
        try:
            # First explicitly check if token cache file exists
            if not os.path.exists(self.token_cache_file):
                print(f"❌ Token cache file not found at {self.token_cache_file}")
                return False
                
            token = self._get_access_token(interactive=False)
            return token is not None
        except Exception as e:
            print(f"❌ Authentication check failed: {e}")
            return False
    
    def get_latest_emails(self, count: int = 10, interactive: bool = False) -> Dict[str, Any]:
        """Get the latest emails from the inbox"""
        try:
            access_token = self._get_access_token(interactive=interactive)
            if not access_token:
                return {
                    "success": False,
                    "message": "BYU Outlook: Authentication required. Please run setup first.",
                    "provider": "outlook",
                    "requires_auth": True
                }
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Get user's messages with more details (include ids for dedup)
            url = (
                "https://graph.microsoft.com/v1.0/me/messages"
                f"?$top={count}"
                "&$select=id,subject,from,receivedDateTime,bodyPreview,isRead,hasAttachments,internetMessageId"
                "&$orderby=receivedDateTime desc"
            )
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                messages_data = response.json()
                emails = []

                for msg in messages_data.get('value', []):
                    email_info = {
                        'id': msg.get('id'),
                        'internet_message_id': msg.get('internetMessageId'),
                        'subject': msg.get('subject', 'No subject'),
                        'from': msg.get('from', {}).get('emailAddress', {}).get('address', 'Unknown'),
                        'from_name': msg.get('from', {}).get('emailAddress', {}).get('name', 'Unknown'),
                        'received_date': msg.get('receivedDateTime', ''),
                        # Standard alias used by the email_check job
                        'date': msg.get('receivedDateTime', ''),
                        'body_preview': msg.get('bodyPreview', ''),
                        'is_read': msg.get('isRead', False),
                        'has_attachments': msg.get('hasAttachments', False)
                    }
                    emails.append(email_info)

                return {
                    "success": True,
                    "message": f"Retrieved {len(emails)} emails successfully",
                    "emails": emails,
                    "provider": "outlook"
                }
            else:
                if response.status_code == 401:
                    return {
                        "success": False,
                        "message": "Unauthorized (401). Token may be expired. Please re-authenticate.",
                        "provider": "outlook",
                        "requires_auth": True
                    }
                return {
                    "success": False,
                    "message": f"Failed to get emails: {response.status_code} - {response.text}",
                    "provider": "outlook"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error getting emails: {str(e)}",
                "provider": "outlook"
            }
    
    def send_email(self, to_addr: str, subject: str, body: str, html_body: Optional[str] = None, interactive: bool = False, **kwargs) -> Dict[str, Any]:
        """Send email using Microsoft Graph API"""
        try:
            access_token = self._get_access_token(interactive=interactive)
            if not access_token:
                return {
                    "success": False,
                    "message": "BYU Outlook: Authentication required. Please run setup first.",
                    "provider": "outlook",
                    "requires_auth": True
                }
            
            # Prepare email content
            email_content = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML" if html_body else "Text",
                        "content": html_body if html_body else body
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": to_addr
                            }
                        }
                    ]
                }
            }
            
            # Add CC and BCC if provided
            if 'cc' in kwargs and kwargs['cc']:
                email_content["message"]["ccRecipients"] = [
                    {"emailAddress": {"address": cc}} for cc in kwargs['cc']
                ]
            
            if 'bcc' in kwargs and kwargs['bcc']:
                email_content["message"]["bccRecipients"] = [
                    {"emailAddress": {"address": bcc}} for bcc in kwargs['bcc']
                ]
            
            # Send email via Microsoft Graph API
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                "https://graph.microsoft.com/v1.0/me/sendMail",
                headers=headers,
                json=email_content
            )
            
            if response.status_code == 202:  # Accepted
                return {
                    "success": True,
                    "message": f"BYU Outlook: Email sent successfully to {to_addr}",
                    "provider": "outlook"
                }
            else:
                error_details = response.text
                return {
                    "success": False,
                    "message": f"BYU Outlook API error (HTTP {response.status_code}): {error_details}",
                    "provider": "outlook"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"BYU Outlook error: {str(e)}",
                "provider": "outlook"
            }
# Automatic registration will handle this via load_provider_plugins()
