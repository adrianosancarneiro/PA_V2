#!/usr/bin/env python3
"""
Test script for the email integration system.
This script demonstrates how to use the email integration system
and verifies that provider plugins are loaded correctly.
"""

import sys
import os
# Add the src directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from email_system.integration import send_email, EmailProviderRegistry

def main():
    # List all available providers
    providers = EmailProviderRegistry.get_all_providers()
    
    print("=" * 60)
    print(f"Email Integration System - Available Providers: {len(providers)}")
    print("=" * 60)
    
    for provider in providers:
        print(f"- {provider}")
    
    print("\n")
    
    # Test with dummy provider (if available)
    if "dummy" in providers:
        print("Testing dummy provider...")
        result = send_email(
            provider="dummy",
            to="test@example.com",
            subject="Test Email",
            body="This is a test email from the email integration system.",
            html_body="<p>This is a <b>test email</b> from the email integration system.</p>"
        )
        
        print(f"Result: {'SUCCESS' if result['success'] else 'FAILURE'}")
        print(f"Message: {result['message']}")
        print("\n")
    
    # Interactive test
    do_test = input("Would you like to test sending a real email? (y/n): ").lower().strip() == 'y'
    
    if do_test:
        provider = input(f"Select provider ({', '.join(providers)}): ").strip()
        to = input("Recipient email address: ").strip()
        subject = input("Subject: ").strip()
        body = input("Body: ").strip()
        
        result = send_email(provider, to, subject, body)
        
        print(f"\nResult: {'SUCCESS' if result['success'] else 'FAILURE'}")
        print(f"Message: {result['message']}")
    
    print("\nTest complete.")

if __name__ == "__main__":
    main()
