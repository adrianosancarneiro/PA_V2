#!/usr/bin/env python3
"""
Test script for EmailRepo functionality
Tests database storage, retrieval, and retention cleanup
"""
import sys
import os
from datetime import datetime, timezone

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    from repo.email_repo import EmailRepo
    print("✅ EmailRepo imported successfully")
except ImportError as e:
    print(f"❌ Failed to import EmailRepo: {e}")
    print("Make sure DATABASE_URL is set and PostgreSQL is running")
    sys.exit(1)


def test_email_storage():
    """Test email storage and retrieval functionality."""
    print("\n🧪 Testing email storage...")
    
    repo = EmailRepo()
    
    # Test data
    test_emails = [
        {
            "provider": "gmail",
            "provider_message_id": "test123",
            "provider_thread_id": "threadX",
            "from_display": "Alice Smith",
            "from_email": "alice@example.com",
            "to_emails": ["bob@example.com"],
            "cc_emails": [],
            "bcc_emails": [],
            "subject": "Test Email 1",
            "snippet": "This is a test email",
            "body_plain": "Hello Bob, this is a test message.",
            "body_html": None,
            "received_at": datetime.now(timezone.utc),
            "tags": ["test"]
        },
        {
            "provider": "outlook",
            "provider_message_id": "test456",
            "provider_thread_id": "threadY",
            "from_display": "Charlie Brown",
            "from_email": "charlie@example.com",
            "to_emails": ["dave@example.com"],
            "cc_emails": ["eve@example.com"],
            "bcc_emails": [],
            "subject": "Test Email 2",
            "snippet": "Another test email",
            "body_plain": "Hi Dave, this is another test.",
            "body_html": "<p>Hi Dave, this is another <b>test</b>.</p>",
            "received_at": datetime.now(timezone.utc),
            "tags": ["test", "important"]
        }
    ]
    
    stored_ids = []
    for email_data in test_emails:
        try:
            email_id = repo.upsert_email(**email_data)
            stored_ids.append(email_id)
            print(f"✅ Stored email '{email_data['subject']}' with ID: {email_id}")
        except Exception as e:
            print(f"❌ Failed to store email '{email_data['subject']}': {e}")
            return False
    
    # Test duplicate insertion (should not create new records)
    try:
        duplicate_id = repo.upsert_email(**test_emails[0])
        if duplicate_id == stored_ids[0]:
            print("✅ Duplicate email correctly ignored")
        else:
            print(f"⚠️ Duplicate created new ID: {duplicate_id}")
    except Exception as e:
        print(f"❌ Duplicate test failed: {e}")
    
    # Test retrieval
    try:
        recent_emails = repo.get_recent_emails(limit=10)
        print(f"✅ Retrieved {len(recent_emails)} recent emails")
        for email in recent_emails[:2]:  # Show first 2
            print(f"   - {email['subject']} from {email['from_email']}")
    except Exception as e:
        print(f"❌ Failed to retrieve emails: {e}")
        return False
    
    return True


def test_retention_cleanup():
    """Test retention cleanup functionality."""
    print("\n🧹 Testing retention cleanup...")
    
    repo = EmailRepo()
    
    try:
        # Test cleanup (should be safe with small numbers)
        deleted_gmail = repo.retention_cleanup("gmail", keep=1000)
        deleted_outlook = repo.retention_cleanup("outlook", keep=1000)
        
        print(f"✅ Gmail retention cleanup: {deleted_gmail} emails deleted")
        print(f"✅ Outlook retention cleanup: {deleted_outlook} emails deleted")
        
        return True
    except Exception as e:
        print(f"❌ Retention cleanup failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🔍 PA_V2 EmailRepo Test Suite")
    print("=" * 40)
    
    # Test email storage
    storage_success = test_email_storage()
    
    # Test retention cleanup
    cleanup_success = test_retention_cleanup()
    
    # Summary
    print("\n📊 Test Results:")
    print(f"   Email Storage: {'✅ PASS' if storage_success else '❌ FAIL'}")
    print(f"   Retention Cleanup: {'✅ PASS' if cleanup_success else '❌ FAIL'}")
    
    if storage_success and cleanup_success:
        print("\n🎉 All tests passed! EmailRepo is working correctly.")
        return 0
    else:
        print("\n💥 Some tests failed. Check error messages above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
