#!/usr/bin/env python3
"""Demo script showing how the Internet Message-ID functionality works.

This demonstrates:
1. How Gmail headers are extracted from a message
2. How the email is stored with internet_message_id and references_ids  
3. How to use the Outlook reply service (simulation)
"""

import sys
import pathlib
from datetime import datetime, timezone

# Add project root to path  
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "src"))

from dotenv import load_dotenv
load_dotenv('/etc/pa_v2/secrets.env')

from services.email.email_repo import EmailRepo
from webhooks.svc import to_normalized_gmail


def demo_gmail_header_extraction():
    """Demo how Gmail headers are extracted and stored."""
    print("🔍 Demo: Gmail Header Extraction and Storage\n")
    
    # Simulate a Gmail message payload (similar to what comes from Gmail API)
    simulated_gmail_message = {
        "id": "demo123456789",
        "threadId": "demo_thread_123",
        "snippet": "This is a demo BYU email that was redirected to Gmail...",
        "payload": {
            "headers": [
                {"name": "Message-ID", "value": "<demo-byu-message-12345@mail.byu.edu>"},
                {"name": "References", "value": "<original@mail.byu.edu> <reply1@mail.byu.edu>"},
                {"name": "From", "value": "John Doe <john.doe@byu.edu>"},
                {"name": "To", "value": "adrianosancarneiro@hotmail.com"},
                {"name": "Subject", "value": "Important BYU Message"},
                {"name": "Date", "value": "Thu, 28 Aug 2025 10:00:00 -0600"},
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {
                        "data": "VGhpcyBpcyBhIGRlbW8gQllVIGVtYWlsIHRoYXQgd2FzIHJlZGlyZWN0ZWQgdG8gR21haWwuCgpCZXN0IHJlZ2FyZHMsCkpvaG4gRG9l"  # base64 for demo text
                    }
                }
            ]
        }
    }
    
    print("📧 Simulated Gmail message (BYU email redirected to Gmail):")
    print(f"   Gmail Message ID: {simulated_gmail_message['id']}")
    print(f"   Gmail Thread ID: {simulated_gmail_message['threadId']}")
    
    # Show original headers  
    headers = simulated_gmail_message["payload"]["headers"]
    for h in headers:
        print(f"   {h['name']}: {h['value']}")
    
    print(f"\n🔄 Processing with webhook service...")
    
    # Use the webhook service to normalize the message
    normalized = to_normalized_gmail(simulated_gmail_message)
    
    print(f"✅ Extracted headers:")
    print(f"   Internet Message-ID: {normalized.get('internet_message_id')}")
    print(f"   References: {normalized.get('references_ids')}")
    
    # Store in database
    repo = EmailRepo()
    email_id = repo.upsert_email(
        provider=normalized["provider"],
        provider_message_id=normalized["id"],
        provider_thread_id=normalized["thread_id"],
        from_display=normalized.get("from_name"),
        from_email=normalized.get("from_email"),
        to_emails=normalized.get("to_emails", []),
        cc_emails=normalized.get("cc_emails", []),
        bcc_emails=normalized.get("bcc_emails", []),
        subject=normalized.get("subject"),
        snippet=normalized.get("snippet"),
        body_plain=normalized.get("body_text"),
        body_html=normalized.get("body_html"),
        received_at=normalized.get("received_at"),
        tags=["BYU_ASC59"],  # This would be added by Gmail label detection
        internet_message_id=normalized.get("internet_message_id"),
        references_ids=normalized.get("references_ids", [])
    )
    
    print(f"💾 Stored in database with ID: {email_id}")
    
    # Verify storage
    detail = repo.get_email_detail(email_id)
    print(f"\n📋 Verification - retrieved from database:")
    print(f"   Email ID: {detail['id']}")
    print(f"   Subject: {detail['subject']}")
    print(f"   From: {detail['from_email']}")
    print(f"   Internet Message-ID: {detail['internet_message_id']}")
    print(f"   References: {detail['references_ids']}")
    print(f"   Tags: {detail['tags']}")
    
    return email_id


def demo_outlook_reply_service(email_id):
    """Demo how the Outlook reply service would work."""
    print(f"\n🔄 Demo: Outlook Reply Service\n")
    
    print(f"📧 User wants to reply to email ID {email_id} via Outlook...")
    
    # This is what the Telegram bot would call
    from services.outlook.reply_service import reply_via_outlook_for_email_id
    
    # Simulate what would happen (without actually calling Graph API)
    repo = EmailRepo()
    detail = repo.get_email_detail(email_id)
    
    print(f"🔍 Looking up email details:")
    print(f"   From: {detail['from_email']}")
    print(f"   Subject: {detail['subject']}")
    print(f"   Internet Message-ID: {detail['internet_message_id']}")
    
    if detail['internet_message_id']:
        print(f"\n✅ Found Internet Message-ID: {detail['internet_message_id']}")
        print(f"📞 Would call Microsoft Graph:")
        print(f"   GET /me/messages?$filter=internetMessageId eq '{detail['internet_message_id']}'")
        print(f"   → Find corresponding Outlook message")
        print(f"   → Create reply draft")
        print(f"   → Update draft with reply content")
        print(f"   → Send reply via Outlook")
        print(f"   → ✅ Outlook threading preserved!")
        
        # This is what the actual call would look like:
        # (commented out since we don't have a Graph session set up)
        """
        result = reply_via_outlook_for_email_id(
            graph_session,  # your authenticated Graph session
            email_id,
            "Thank you for your email. I'll get back to you soon.",
            extra_cc=["colleague@byu.edu"]
        )
        print(f"Result: {result}")
        """
        
    else:
        print(f"❌ No Internet Message-ID found - would fallback to new email")


def cleanup_demo_data(email_id):
    """Clean up the demo data."""
    print(f"\n🧹 Cleaning up demo data...")
    
    from core.database import get_conn
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM email_messages WHERE id = %s", (email_id,))
        conn.commit()
    
    print(f"✅ Removed demo email {email_id}")


def main():
    """Run the demo."""
    print("🎬 Internet Message-ID Implementation Demo")
    print("=" * 50)
    
    try:
        # Demo 1: Gmail header extraction and storage
        email_id = demo_gmail_header_extraction()
        
        # Demo 2: Outlook reply service
        demo_outlook_reply_service(email_id)
        
        print(f"\n📝 Summary:")
        print(f"   ✅ BYU emails redirected to Gmail preserve original headers")
        print(f"   ✅ Internet Message-ID and References stored in database")
        print(f"   ✅ Outlook reply service can find original message for threading")
        print(f"   ✅ No background Outlook polling needed!")
        
        # Clean up
        cleanup_demo_data(email_id)
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
