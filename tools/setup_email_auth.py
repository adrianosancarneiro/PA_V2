#!/usr/bin/env python3
"""
Setup script for email provider authentication.
Run this once to set up cached credentials for both Gmail and Outlook providers.
After running this, your Telegram bot can use emails without interactive authentication.
"""

import sys
import os
# Add the src directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from pa_v2.email.providers.gmail_provider import GmailProvider
from pa_v2.email.providers.outlook_provider import OutlookGraphProvider

def setup_gmail():
    """Setup Gmail authentication"""
    print("="*60)
    print("SETTING UP GMAIL AUTHENTICATION")
    print("="*60)
    
    try:
        gmail = GmailProvider()
        result = gmail.setup_authentication()
        
        if result['success']:
            print(f"✅ {result['message']}")
            return True
        else:
            print(f"❌ {result['message']}")
            return False
    except Exception as e:
        print(f"❌ Gmail setup failed: {e}")
        return False

def setup_outlook():
    """Setup Outlook authentication"""
    print("\n" + "="*60)
    print("SETTING UP BYU OUTLOOK AUTHENTICATION")
    print("="*60)
    
    try:
        outlook = OutlookGraphProvider()
        result = outlook.setup_authentication()
        
        if result['success']:
            print(f"✅ {result['message']}")
            return True
        else:
            print(f"❌ {result['message']}")
            return False
    except Exception as e:
        print(f"❌ Outlook setup failed: {e}")
        return False

def check_authentication_status():
    """Check current authentication status"""
    print("\n" + "="*60)
    print("AUTHENTICATION STATUS CHECK")
    print("="*60)
    
    try:
        gmail = GmailProvider()
        gmail_auth = gmail.is_authenticated()
        print(f"Gmail: {'✅ Authenticated' if gmail_auth else '❌ Not authenticated'}")
    except Exception as e:
        print(f"Gmail: ❌ Error checking status: {e}")
    
    try:
        outlook = OutlookGraphProvider()
        outlook_auth = outlook.is_authenticated()
        print(f"BYU Outlook: {'✅ Authenticated' if outlook_auth else '❌ Not authenticated'}")
    except Exception as e:
        print(f"BYU Outlook: ❌ Error checking status: {e}")

def main():
    print("🤖 EMAIL PROVIDER AUTHENTICATION SETUP")
    print("This script will set up authentication for your Telegram bot")
    print("After completing this setup, your bot can send/receive emails automatically")
    
    # Check current status
    check_authentication_status()
    
    print("\nSelect an option:")
    print("1. Setup Gmail authentication")
    print("2. Setup BYU Outlook authentication") 
    print("3. Setup both providers")
    print("4. Check authentication status only")
    print("5. Exit")
    
    choice = input("\nEnter your choice (1-5): ").strip()
    
    if choice == "1":
        setup_gmail()
    elif choice == "2":
        setup_outlook()
    elif choice == "3":
        print("Setting up both providers...")
        gmail_success = setup_gmail()
        outlook_success = setup_outlook()
        
        if gmail_success and outlook_success:
            print("\n🎉 Both providers set up successfully!")
            print("Your Telegram bot is now ready to use email features!")
        else:
            print("\n⚠️ Some providers failed to set up. Check the errors above.")
    elif choice == "4":
        # Already checked above
        pass
    elif choice == "5":
        print("Goodbye!")
        return
    else:
        print("Invalid choice. Please run the script again.")
        return
    
    # Final status check
    print("\n" + "="*60)
    print("FINAL STATUS")
    print("="*60)
    check_authentication_status()
    
    print("\n💡 Next steps:")
    print("- Your authentication tokens are now cached")
    print("- Your Telegram bot can use email features without user interaction")
    print("- Tokens will auto-refresh when needed")
    print("- If authentication fails in the future, re-run this setup script")

if __name__ == "__main__":
    main()
