"""
Gmail email provider plugin for the email integration system.
"""
import os
import base64
import json
import pathlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.message import EmailMessage
from email import encoders
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Configuration
SCOPES = ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.readonly"]
# Get paths relative to project root using pathlib for cleaner navigation
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[4]  # Go up 4 levels: providers -> email -> services -> src -> project_root
CREDENTIALS_FILE = PROJECT_ROOT / "config" / "client_secret_147697913284-lrl04fga24gpkk6ltv6ai3d4eps602lb.apps.googleusercontent.com.json"
TOKEN_FILE = PROJECT_ROOT / "config" / "gmail_token.json"

class GmailProvider:
    """Gmail email provider using Google API with OAuth2"""
    
    def get_name(self):
        return "gmail"
    
    def get_credentials(self, interactive=True):
        """Get OAuth credentials for Gmail API
        
        Args:
            interactive (bool): Whether to allow interactive authentication
        """
        creds = None
        if os.path.exists(TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
                print("🔄 Found cached Gmail credentials")
            except Exception as e:
                print(f"⚠️ Error loading cached credentials: {e}")
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    print("🔄 Refreshing expired Gmail token...")
                    creds.refresh(Request())
                    print("✅ Gmail token refreshed successfully!")
                except Exception as e:
                    print(f"⚠️ Token refresh failed: {e}")
                    creds = None
            
            if not creds and not interactive:
                print("❌ No valid Gmail credentials and interactive mode disabled")
                return None
                
            if not creds and interactive:
                print("\n" + "="*60)
                print("GMAIL AUTHENTICATION REQUIRED")
                print("="*60)
                print("💡 This is a one-time setup. Credentials will be cached for future use.")
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
                print("💾 Gmail credentials cached for future use")
            
            if creds:
                try:
                    with open(TOKEN_FILE, "w") as f:
                        f.write(creds.to_json())
                    print("✅ Gmail credentials saved successfully!")
                except Exception as e:
                    print(f"⚠️ Could not save credentials: {e}")
        else:
            print("✅ Using cached Gmail credentials")
            
        return creds
    
    def is_authenticated(self):
        """Check if we have valid cached credentials"""
        try:
            creds = self.get_credentials(interactive=False)
            return creds is not None and creds.valid
        except:
            return False
    
    def setup_authentication(self):
        """Setup authentication interactively (run this once)"""
        try:
            creds = self.get_credentials(interactive=True)
            if creds and creds.valid:
                return {
                    "success": True,
                    "message": "Gmail: Authentication setup completed successfully!",
                    "provider": "gmail"
                }
            else:
                return {
                    "success": False,
                    "message": "Gmail: Authentication setup failed",
                    "provider": "gmail"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Gmail setup error: {str(e)}",
                "provider": "gmail"
            }
    
    def send_email(self, to_addr, subject, body, html_body=None, interactive=False, **kwargs):
        """Send email using Gmail API
        
        Args:
            to_addr (str): Recipient email address
            subject (str): Email subject
            body (str): Plain text email body
            html_body (str, optional): HTML email body
            **kwargs: Additional arguments for future extensions
            
        Returns:
            dict: Result with success status and message
        """
        try:
            # Create API service
            creds = self.get_credentials(interactive=interactive)
            if not creds:
                return {
                    "success": False,
                    "message": "Gmail: Authentication required. Please run setup first.",
                    "provider": "gmail",
                    "requires_auth": True
                }
                
            service = build("gmail", "v1", credentials=creds)
            
            # Prepare email message
            msg = EmailMessage()
            msg["To"] = to_addr
            msg["From"] = "me"   # 'me' lets the API use the authenticated user
            msg["Subject"] = subject
            
            # Set plain text content
            msg.set_content(body)
            
            # Add HTML version if provided
            if html_body:
                msg.add_alternative(html_body, subtype="html")
            
            # Convert to base64 encoded string
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
            
            # Send email
            sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
            
            message_id = sent.get("id", "unknown")
            return {
                "success": True,
                "message": f"Gmail: Email sent successfully. Message ID: {message_id}",
                "provider": "gmail",
                "message_id": message_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Gmail: Failed to send email: {str(e)}",
                "provider": "gmail",
                "error": str(e)
            }
    
    def get_latest_emails(self, count=10, interactive=False):
        """Get latest emails from Gmail inbox
        
        Args:
            count (int): Number of emails to retrieve (default: 10)
            interactive (bool): Whether to allow interactive authentication
            
        Returns:
            dict: Result with success status, message, and emails list
        """
        try:
            # Create API service
            creds = self.get_credentials(interactive=interactive)
            if not creds:
                return {
                    "success": False,
                    "message": "Gmail: Authentication required. Please run setup first.",
                    "provider": "gmail",
                    "requires_auth": True
                }
                
            service = build("gmail", "v1", credentials=creds)
            
            # Get list of messages
            results = service.users().messages().list(
                userId="me", 
                labelIds=["INBOX"],
                maxResults=count
            ).execute()
            
            messages = results.get("messages", [])
            emails = []
            
            for message in messages:
                # Get full message details
                msg = service.users().messages().get(
                    userId="me", 
                    id=message["id"],
                    format="full"
                ).execute()
                
                # Extract email information
                payload = msg.get("payload", {})
                headers = payload.get("headers", [])
                
                # Get header information
                subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
                from_addr = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
                date = next((h["value"] for h in headers if h["name"] == "Date"), "Unknown")
                
                # Parse from address to get name and email
                import re
                from_match = re.match(r'"?([^"]*)"?\s*<(.+)>|(.+)', from_addr)
                if from_match:
                    if from_match.group(2):  # Format: "Name" <email@domain.com>
                        from_name = from_match.group(1).strip()
                        from_email = from_match.group(2).strip()
                    else:  # Format: email@domain.com
                        from_name = from_match.group(3).strip()
                        from_email = from_match.group(3).strip()
                else:
                    from_name = from_addr
                    from_email = from_addr
                
                # Get snippet (preview)
                snippet = msg.get("snippet", "")
                
                # Check if read
                label_ids = msg.get("labelIds", [])
                is_read = "UNREAD" not in label_ids
                
                # Check for attachments
                has_attachments = any(
                    part.get("filename") 
                    for part in payload.get("parts", [payload])
                    if part.get("filename")
                )
                
                email_info = {
                    "subject": subject,
                    "from": from_email,
                    "from_name": from_name,
                    "received_date": date,
                    "body_preview": snippet,
                    "is_read": is_read,
                    "has_attachments": has_attachments,
                    "message_id": message["id"]
                }
                emails.append(email_info)
            
            return {
                "success": True,
                "message": f"Gmail: Retrieved {len(emails)} emails successfully",
                "emails": emails,
                "provider": "gmail"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Gmail: Failed to get emails: {str(e)}",
                "provider": "gmail",
                "error": str(e)
            }
