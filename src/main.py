#!/usr/bin/env python3
"""
Main entry point for PA_V2 Personal Assistant
This script provides a command-line interface to various PA_V2 functions.
"""

import sys
import os
import argparse
from pathlib import Path

from .email_system.integration import send_email, get_latest_emails, EmailProviderRegistry

def setup_auth():
    """Run email authentication setup"""
    # Add tools directory to path
    project_root = Path(__file__).parent.parent.parent
    tools_path = project_root / "tools"
    sys.path.insert(0, str(tools_path))
    
    import setup_email_auth
    setup_email_auth.main()

def test_email():
    """Run email integration tests"""
    # Add tests directory to path  
    project_root = Path(__file__).parent.parent.parent
    tests_path = project_root / "tests"
    sys.path.insert(0, str(tests_path))
    
    import test_email_integration
    test_email_integration.main()

def send_email_cmd(args):
    """Send an email via command line"""
    result = send_email(
        provider=args.provider,
        to=args.to,
        subject=args.subject,
        body=args.body,
        html_body=args.html_body
    )
    
    if result['success']:
        print(f"✅ Email sent successfully via {args.provider}")
    else:
        print(f"❌ Failed to send email: {result['message']}")

def list_providers():
    """List available email providers"""
    providers = EmailProviderRegistry.get_all_providers()
    print("Available email providers:")
    for provider in providers:
        print(f"  - {provider}")

def main():
    parser = argparse.ArgumentParser(description='PA_V2 Personal Assistant')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Setup auth command
    subparsers.add_parser('setup-auth', help='Setup email authentication')
    
    # Test command
    subparsers.add_parser('test', help='Run email integration tests')
    
    # List providers command
    subparsers.add_parser('list-providers', help='List available email providers')
    
    # Send email command
    email_parser = subparsers.add_parser('send-email', help='Send an email')
    email_parser.add_argument('--provider', required=True, help='Email provider to use')
    email_parser.add_argument('--to', required=True, help='Recipient email address')
    email_parser.add_argument('--subject', required=True, help='Email subject')
    email_parser.add_argument('--body', required=True, help='Email body (plain text)')
    email_parser.add_argument('--html-body', help='Email body (HTML)')
    
    args = parser.parse_args()
    
    if args.command == 'setup-auth':
        setup_auth()
    elif args.command == 'test':
        test_email()
    elif args.command == 'list-providers':
        list_providers()
    elif args.command == 'send-email':
        send_email_cmd(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
