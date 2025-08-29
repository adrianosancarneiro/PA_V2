#!/usr/bin/env python3
"""Test script to manually send Telegram notification for latest email"""

import os
import sys
sys.path.insert(0, 'src')

from dotenv import load_dotenv
load_dotenv('/etc/pa_v2/secrets.env')

# Import webhook's send function
from webhooks.svc import send_telegram_digest
from services.email.email_repo import EmailRepo

def test_notification():
    """Send notification for the latest email in the database"""
    repo = EmailRepo()
    
    # Get latest emails
    emails = repo.get_recent_emails(limit=5)
    
    if not emails:
        print("No emails found in database")
        return
    
    # Show available emails
    print(f"Found {len(emails)} recent emails:")
    for email in emails:
        thread_id = email.get('thread_id', 'N/A')
        subject = email.get('subject', 'No subject')
        print(f"  ID: {email['id']}, Thread: {thread_id}, Subject: {subject}")
    
    # Send notification for test emails
    test_emails = [e for e in emails if 'test' in e.get('subject', '').lower()]
    
    if test_emails:
        print(f"\nFound {len(test_emails)} test emails. Sending notifications...")
        for email in test_emails:
            print(f"Sending notification for '{email.get('subject', 'No subject')}' (ID: {email['id']})...")
            try:
                send_telegram_digest(email['id'])
                print("✅ Notification sent successfully!")
            except Exception as e:
                print(f"❌ Error sending notification: {e}")
                import traceback
                traceback.print_exc()
    else:
        # Send for latest if no test emails
        latest = emails[0]
        print(f"\nNo test emails found. Sending notification for latest email ID {latest['id']}...")
        try:
            send_telegram_digest(latest['id'])
            print("✅ Notification sent successfully!")
        except Exception as e:
            print(f"❌ Error sending notification: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_notification()
