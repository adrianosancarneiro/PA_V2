#!/usr/bin/env python3
"""Test script to manually trigger digest notification for recent email."""
import sys
import os
sys.path.insert(0, '/home/mentorius/AI_Services/PA_V2/src')

from dotenv import load_dotenv
load_dotenv('/etc/pa_v2/secrets.env')

from services.email.email_repo import EmailRepo
from bots.telegram_bot_enhanced import Bot
from interfaces.telegram.views.digest import build_digest, send_digest

def test_digest_notification():
    """Test the digest notification for the most recent email."""
    try:
        # Get the most recent email
        email_repo = EmailRepo()
        recent_emails = email_repo.list_emails(limit=1)
        
        if not recent_emails:
            print("❌ No emails found to test with")
            return
            
        email = recent_emails[0]
        email_id = email['id']
        print(f"🔍 Testing digest for email: {email.get('subject', 'No Subject')} (ID: {email_id})")
        
        # Initialize bot
        bot = Bot()
        
        # Build and send digest
        digest_content = build_digest([email])
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if chat_id:
            send_digest(bot, chat_id, digest_content, [email])
            print(f"✅ Digest notification sent successfully to chat {chat_id}")
        else:
            print("❌ TELEGRAM_CHAT_ID not configured")
            
    except Exception as e:
        print(f"❌ Error testing digest: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_digest_notification()
