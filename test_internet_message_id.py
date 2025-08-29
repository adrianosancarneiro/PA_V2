#!/usr/bin/env python3
"""Test script for the Internet Message-ID storage and Outlook reply functionality.

This script tests:
1. Database schema changes (internet_message_id, references_ids columns)
2. Gmail header extraction and storage
3. Outlook reply lookup and functionality (if Graph session available)
"""

import sys
import os
import pathlib
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "src"))

from dotenv import load_dotenv
load_dotenv('/etc/pa_v2/secrets.env')

from services.email.email_repo import EmailRepo
from services.email.providers.model import NormalizedEmail


def test_database_schema():
    """Test that the new database columns exist and work."""
    print("🔍 Testing database schema...")
    
    repo = EmailRepo()
    
    # Create a test email with the new fields
    test_message_id = f"test-{datetime.now().timestamp()}"
    test_internet_id = f"<test-{test_message_id}@test.example.com>"
    test_references = ["<ref1@example.com>", "<ref2@example.com>"]
    
    try:
        email_id = repo.upsert_email(
            provider="gmail",  # Use valid provider enum value
            provider_message_id=test_message_id,
            provider_thread_id=f"thread-{test_message_id}",
            from_display="Test Sender",
            from_email="test@example.com",
            to_emails=["recipient@example.com"],
            cc_emails=["cc@example.com"],
            bcc_emails=[],
            subject="Test Email with Internet Message-ID",
            snippet="This is a test email",
            body_plain="Test body content",
            body_html="<p>Test body content</p>",
            received_at=datetime.now(timezone.utc),
            tags=["test"],
            internet_message_id=test_internet_id,
            references_ids=test_references
        )
        
        print(f"✅ Created test email with ID: {email_id}")
        
        # Retrieve and verify
        detail = repo.get_email_detail(email_id)
        assert detail is not None, "Failed to retrieve test email"
        assert detail["internet_message_id"] == test_internet_id, f"Internet Message-ID mismatch: {detail['internet_message_id']} != {test_internet_id}"
        assert detail["references_ids"] == test_references, f"References mismatch: {detail['references_ids']} != {test_references}"
        
        print("✅ Database schema test passed")
        
        # Clean up test data
        from core.database import get_conn
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM email_messages WHERE id = %s", (email_id,))
            conn.commit()
        print("🧹 Cleaned up test data")
        
        return True
        
    except Exception as e:
        print(f"❌ Database schema test failed: {e}")
        return False


def test_gmail_header_extraction():
    """Test Gmail header extraction functionality."""
    print("\n🔍 Testing Gmail header extraction...")
    
    try:
        from services.email.providers.gmail import _header, _split_refs
        
        # Test header extraction
        test_headers = [
            {"name": "Message-ID", "value": "<test123@mail.byu.edu>"},
            {"name": "References", "value": "<ref1@example.com> <ref2@example.com> <ref3@example.com>"},
            {"name": "Subject", "value": "Test Subject"},
            {"name": "From", "value": "Test User <test@byu.edu>"}
        ]
        
        # Test _header function
        message_id = _header(test_headers, "Message-ID")
        assert message_id == "<test123@mail.byu.edu>", f"Message-ID extraction failed: {message_id}"
        
        references = _header(test_headers, "References")
        refs_list = _split_refs(references)
        expected_refs = ["<ref1@example.com>", "<ref2@example.com>", "<ref3@example.com>"]
        assert refs_list == expected_refs, f"References extraction failed: {refs_list} != {expected_refs}"
        
        print("✅ Gmail header extraction test passed")
        return True
        
    except Exception as e:
        print(f"❌ Gmail header extraction test failed: {e}")
        return False


def test_normalized_email_model():
    """Test the updated NormalizedEmail model."""
    print("\n🔍 Testing NormalizedEmail model...")
    
    try:
        email = NormalizedEmail(
            id="test123",
            thread_id="thread123",
            from_name="Test User",
            from_email="test@example.com",
            to_emails=["recipient@example.com"],
            cc_emails=[],
            bcc_emails=[],
            subject="Test Email",
            snippet="Test snippet",
            body_text="Test body",
            body_html="<p>Test body</p>",
            received_at=datetime.now(timezone.utc),
            provider="gmail",
            internet_message_id="<test123@example.com>",
            references_ids=["<ref1@example.com>", "<ref2@example.com>"]
        )
        
        assert email.internet_message_id == "<test123@example.com>", "Internet Message-ID not set correctly"
        assert email.references_ids == ["<ref1@example.com>", "<ref2@example.com>"], "References not set correctly"
        
        # Test default initialization
        email2 = NormalizedEmail(
            id="test456",
            thread_id="thread456",
            from_name="Test User 2",
            from_email="test2@example.com",
            to_emails=["recipient2@example.com"],
            cc_emails=[],
            bcc_emails=[],
            subject="Test Email 2",
            snippet="Test snippet 2",
            body_text="Test body 2",
            body_html="<p>Test body 2</p>",
            received_at=datetime.now(timezone.utc),
            provider="gmail"
        )
        
        assert email2.internet_message_id is None, "Default internet_message_id should be None"
        assert email2.references_ids == [], "Default references_ids should be empty list"
        
        print("✅ NormalizedEmail model test passed")
        return True
        
    except Exception as e:
        print(f"❌ NormalizedEmail model test failed: {e}")
        return False


def test_outlook_reply_imports():
    """Test that the Outlook reply modules can be imported."""
    print("\n🔍 Testing Outlook reply module imports...")
    
    try:
        from providers.outlook_reply import (
            find_message_by_internet_id,
            create_reply_draft,
            update_draft,
            send_draft,
            reply_via_outlook_session
        )
        
        from services.outlook.reply_service import (
            reply_via_outlook_for_email_id,
            fallback_compose_new_outlook_reply
        )
        
        print("✅ Outlook reply module imports successful")
        return True
        
    except Exception as e:
        print(f"❌ Outlook reply module import failed: {e}")
        return False


def show_recent_emails_with_internet_id():
    """Show recent emails and their internet_message_id values."""
    print("\n📧 Recent emails with Internet Message-ID:")
    
    repo = EmailRepo()
    emails = repo.get_recent_emails(limit=10)
    
    from core.database import get_conn
    with get_conn() as conn, conn.cursor() as cur:
        for email in emails:
            cur.execute("""
                SELECT internet_message_id, references_ids
                FROM email_messages 
                WHERE id = %s
            """, (email["id"],))
            row = cur.fetchone()
            
            if row:
                internet_id, references = row
                print(f"   ID {email['id']}: {email.get('subject', 'No Subject')[:50]}")
                print(f"     From: {email.get('from_email', 'Unknown')}")
                print(f"     Internet Message-ID: {internet_id or 'None'}")
                print(f"     References: {len(references or [])} items")
                print()


def main():
    """Run all tests."""
    print("🧪 Testing Internet Message-ID implementation\n")
    
    tests = [
        test_database_schema,
        test_gmail_header_extraction,
        test_normalized_email_model,
        test_outlook_reply_imports,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print(f"\n📊 Test Results:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed! Internet Message-ID implementation is ready.")
    else:
        print(f"\n⚠️ {failed} test(s) failed. Please check the implementation.")
    
    # Show recent emails regardless of test results
    show_recent_emails_with_internet_id()


if __name__ == "__main__":
    main()
