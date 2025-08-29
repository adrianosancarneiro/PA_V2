#!/usr/bin/env python3
"""
Test script for the updated OutlookGraphProvider
Demonstrates both email sending and reading capabilities
"""

import sys
import os
import pathlib
# Add the src directory to the path for imports
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from services.email.providers.outlook_provider import OutlookGraphProvider

def test_outlook_provider():
    """Test the OutlookGraphProvider functionality"""
    
    print("="*60)
    print("Testing BYU Outlook Graph Provider")
    print("="*60)
    
    try:
        # Initialize the provider
        provider = OutlookGraphProvider()
        print(f"✓ Provider initialized: {provider.get_name()}")
        print(f"✓ Tenant: {provider.tenant}")
        print(f"✓ User: {provider.user_email}")
        
        # Test getting latest emails
        print("\n" + "="*40)
        print("Testing: Get Latest Emails")
        print("="*40)
        
        result = provider.get_latest_emails(count=5)
        if result['success']:
            print(f"✓ {result['message']}")
            print(f"\nEmails retrieved:")
            for i, email in enumerate(result['emails'], 1):
                print(f"\n{i}. Subject: {email['subject']}")
                print(f"   From: {email['from_name']} <{email['from']}>")
                print(f"   Date: {email['received_date']}")
                print(f"   Read: {'Yes' if email['is_read'] else 'No'}")
                print(f"   Preview: {email['body_preview'][:100]}...")
        else:
            print(f"✗ {result['message']}")
        
        # Test sending email
        print("\n" + "="*40)
        print("Testing: Send Email")
        print("="*40)
        
        test_email = input("Enter email address to send test email to (or press Enter to skip): ").strip()
        
        if test_email:
            result = provider.send_email(
                to_addr=test_email,
                subject="Test from Updated BYU Outlook Provider",
                body="This is a test email from the updated BYU Outlook provider using Microsoft Graph API.",
                html_body="""
                <h2>Test Email</h2>
                <p>This is a test email from the updated <strong>BYU Outlook provider</strong> using Microsoft Graph API.</p>
                <ul>
                    <li>✅ Email reading capability</li>
                    <li>✅ Email sending capability</li>
                    <li>✅ Environment variable configuration</li>
                </ul>
                <p><em>Sent from Python via Microsoft Graph API</em></p>
                """
            )
            
            if result['success']:
                print(f"✓ {result['message']}")
            else:
                print(f"✗ {result['message']}")
        else:
            print("Skipping email sending test")
        
        print("\n" + "="*60)
        print("Test completed!")
        print("="*60)
        
    except Exception as e:
        print(f"✗ Error during testing: {e}")

if __name__ == "__main__":
    test_outlook_provider()
