#!/usr/bin/env python3
"""
Test script to verify that secrets can be loaded from /etc/pa_v2/secrets.env
"""
import os
from dotenv import load_dotenv

def test_secrets_loading():
    print("Testing secrets loading from /etc/pa_v2/secrets.env...")
    
    # Load from the system-wide secrets file
    load_dotenv('/etc/pa_v2/secrets.env')
    
    # Test key environment variables
    test_vars = [
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID',
        'BYU_CLIENT_ID',
        'BYU_TENANT',
        'BYU_USER',
        'POSTGRES_DATABASE',
        'POSTGRES_HOST',
        'POSTGRES_PORT',
        'POSTGRES_USER'
    ]
    
    print("\n=== Environment Variables Test ===")
    success_count = 0
    
    for var in test_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values for display
            if 'TOKEN' in var or 'PASSWORD' in var:
                display_value = f"{value[:8]}..." if len(value) > 8 else "***"
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
            success_count += 1
        else:
            print(f"❌ {var}: NOT FOUND")
    
    print(f"\n=== Results ===")
    print(f"Successfully loaded: {success_count}/{len(test_vars)} variables")
    
    if success_count == len(test_vars):
        print("🎉 All secrets loaded successfully from /etc/pa_v2/secrets.env!")
        return True
    else:
        print("⚠️  Some secrets are missing. Check the /etc/pa_v2/secrets.env file.")
        return False

def test_email_provider_auth():
    """Test if email providers can authenticate using the new secrets"""
    print("\n=== Email Provider Authentication Test ===")
    
    try:
        # Test Gmail provider authentication
        from services.email.providers.gmail_provider import GmailProvider
        gmail = GmailProvider()
        gmail_auth = gmail.is_authenticated()
        
        # Test Outlook provider authentication  
        from services.email.providers.outlook_provider import OutlookGraphProvider
        outlook = OutlookGraphProvider()
        outlook_auth = outlook.is_authenticated()
        
        print(f"Gmail authentication: {'✅ Working' if gmail_auth else '❌ Failed'}")
        print(f"Outlook authentication: {'✅ Working' if outlook_auth else '❌ Failed'}")
        
        return {'gmail': gmail_auth, 'outlook': outlook_auth}
        
    except Exception as e:
        print(f"❌ Error testing email authentication: {e}")
        return {}

def test_telegram_bot():
    """Test if Telegram bot can be initialized with the new secrets"""
    print("\n=== Telegram Bot Test ===")
    
    try:
        # Test Telegram bot configuration
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if token and len(token) > 10 and chat_id:
            print("✅ Telegram configuration loaded successfully")
            return True
        else:
            print("❌ Telegram configuration not loaded or incomplete")
            return False
    except Exception as e:
        print(f"❌ Error testing Telegram configuration: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING NEW SECRETS CONFIGURATION")
    print("=" * 60)
    
    # Test 1: Basic secrets loading
    secrets_ok = test_secrets_loading()
    
    # Test 2: Email provider authentication
    if secrets_ok:
        auth_status = test_email_provider_auth()
    
    # Test 3: Telegram bot initialization
    if secrets_ok:
        telegram_ok = test_telegram_bot()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if secrets_ok:
        print("✅ System secrets file is working correctly!")
        print("✅ You can safely delete the old .env file.")
    else:
        print("❌ Issues found with system secrets file.")
        print("❌ Do NOT delete the old .env file yet.")
    
    print("=" * 60)
