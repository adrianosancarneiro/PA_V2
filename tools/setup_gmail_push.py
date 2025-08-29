#!/usr/bin/env python3
"""
Setup Gmail Push Notifications
This script registers your webhook with Gmail to receive real-time notifications.
"""

import sys
import os
import pathlib
from dotenv import load_dotenv

# Load system secrets
load_dotenv('/etc/pa_v2/secrets.env')

# Add the src directory to the path for imports
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from services.email.providers.gmail_provider import GmailProvider
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json

def setup_gmail_push_notifications():
    """Setup Gmail push notifications"""
    print("="*60)
    print("SETTING UP GMAIL PUSH NOTIFICATIONS")
    print("="*60)
    
    try:
        # Get Gmail credentials
        gmail = GmailProvider()
        creds = gmail.get_credentials(interactive=False)
        
        if not creds or not creds.valid:
            print("❌ Gmail authentication required. Run: python tools/setup_email_auth.py")
            return False
            
        # Build Gmail service
        service = build('gmail', 'v1', credentials=creds)
        
        # Your Pub/Sub topic from the screenshot
        topic_name = "projects/personalassistant-470020/topics/gmail-push-notifications"
        
        # Configure watch request
        request_body = {
            'labelIds': ['INBOX'],  # Monitor inbox
            'topicName': topic_name
        }
        
        print(f"📡 Registering webhook with topic: {topic_name}")
        print(f"📧 Monitoring labels: {request_body['labelIds']}")
        
        # Make the watch request
        result = service.users().watch(userId='me', body=request_body).execute()
        
        print("✅ Gmail push notifications enabled!")
        print(f"📋 Watch details:")
        print(f"   History ID: {result.get('historyId')}")
        print(f"   Expiration: {result.get('expiration', 'Not specified')}")
        
        # Save the watch info for renewal
        watch_info = {
            'historyId': result.get('historyId'),
            'expiration': result.get('expiration'),
            'topicName': topic_name,
            'labelIds': request_body['labelIds']
        }
        
        watch_file = pathlib.Path("config/gmail_watch.json")
        with open(watch_file, 'w') as f:
            json.dump(watch_info, f, indent=2)
            
        print(f"💾 Watch info saved to: {watch_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Gmail push setup failed: {e}")
        if "Push notifications are not supported" in str(e):
            print("💡 This may be because:")
            print("   1. Your domain is not verified")
            print("   2. Push endpoint is not properly configured")
            print("   3. Gmail API push is not enabled for your project")
        return False

def check_gmail_push_status():
    """Check current Gmail push notification status"""
    print("\n" + "="*60)
    print("CHECKING GMAIL PUSH STATUS")
    print("="*60)
    
    watch_file = pathlib.Path("config/gmail_watch.json")
    if watch_file.exists():
        with open(watch_file, 'r') as f:
            watch_info = json.load(f)
            
        print("📋 Current watch configuration:")
        print(f"   History ID: {watch_info.get('historyId')}")
        print(f"   Topic: {watch_info.get('topicName')}")
        print(f"   Labels: {watch_info.get('labelIds')}")
        
        expiration = watch_info.get('expiration')
        if expiration:
            import datetime
            exp_timestamp = int(expiration) / 1000  # Convert milliseconds to seconds
            exp_date = datetime.datetime.fromtimestamp(exp_timestamp)
            print(f"   Expires: {exp_date}")
            
            # Check if renewal is needed (within 24 hours)
            time_left = exp_date - datetime.datetime.now()
            if time_left.total_seconds() < 86400:  # 24 hours
                print("⚠️  Watch will expire soon - consider renewing")
            else:
                print("✅ Watch is active and current")
        else:
            print("⚠️  No expiration info available")
    else:
        print("❌ No active Gmail push notifications found")
        print("💡 Run setup to enable push notifications")

def main():
    """Main menu for Gmail push notifications"""
    print("Gmail Push Notifications Setup")
    print("==============================")
    print()
    print("1. Setup Gmail push notifications")
    print("2. Check current status")
    print("3. Exit")
    print()
    
    choice = input("Enter your choice (1-3): ").strip()
    
    if choice == "1":
        setup_gmail_push_notifications()
    elif choice == "2":
        check_gmail_push_status()
    elif choice == "3":
        print("Goodbye!")
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()
