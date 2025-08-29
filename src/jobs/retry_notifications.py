#!/usr/bin/env python3
"""
Retry failed notifications for emails that are stored but not notified.
This handles cases where webhook processing succeeded but notification failed.
"""
import sys
import pathlib
from dotenv import load_dotenv

# Load environment secrets
load_dotenv('/etc/pa_v2/secrets.env')

# Add src to path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from services.email.email_repo import EmailRepo
from webhooks.svc import send_telegram_digest

def main():
    """Check for unnotified emails and retry sending notifications."""
    print("🔄 Checking for unnotified emails...")
    
    repo = EmailRepo()
    
    try:
        # Get recent unnotified emails (last 24 hours)
        unnotified = repo.list_recent_unnotified(since_hours=24, limit=50)
        
        if not unnotified:
            print("✅ No unnotified emails found")
            return
        
        print(f"📧 Found {len(unnotified)} unnotified emails")
        
        for email in unnotified:
            email_id = email['id']
            subject = email.get('subject', 'No Subject')
            
            print(f"🔔 Retrying notification for email {email_id}: {subject}")
            
            try:
                send_telegram_digest(email_id)
                repo.mark_notified(email_id)
                print(f"✅ Successfully notified for email {email_id}")
            except Exception as e:
                print(f"❌ Failed to notify email {email_id}: {e}")
                # Continue with other emails even if one fails
        
        print("🎉 Notification retry completed")
        
    except Exception as e:
        print(f"❌ Error in notification retry: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
