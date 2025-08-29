#!/usr/bin/env python3
"""Simple test script to send digest notification for the most recent email."""
import sys
import os
sys.path.insert(0, '/home/mentorius/AI_Services/PA_V2/src')

from dotenv import load_dotenv
load_dotenv('/etc/pa_v2/secrets.env')

from services.email.email_repo import EmailRepo

def test_webhook_digest():
    """Test webhook digest by getting most recent email and sending notification."""
    try:
        repo = EmailRepo()
        
        # Get the most recent email
        recent_emails = repo.get_recent_emails(limit=1)
        
        if not recent_emails:
            print("❌ No emails found to test with")
            return
            
        email = recent_emails[0]
        email_id = email['id']
        
        print(f"🔍 Testing digest for email ID {email_id}: {email.get('subject', 'No Subject')}")
        
        # Import and call the webhook digest function
        sys.path.insert(0, '/home/mentorius/AI_Services/PA_V2/src/webhooks')
        from svc import send_telegram_digest
        
        send_telegram_digest(email_id)
        
    except Exception as e:
        print(f"❌ Error testing digest: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_webhook_digest()
