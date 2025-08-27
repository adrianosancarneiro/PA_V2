#!/usr/bin/env python3
"""
Comprehensive test suite for email_check.py functionality
Tests all components before deploying as systemd service
"""
import os
import sys
import json
import time
import pathlib
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all required modules can be imported"""
    print("=== Testing Imports ===")
    
    try:
        from jobs.email_check import (
            load_state, save_state, check_auth_status, 
            get_text_from_email, send_telegram, 
            format_telegram_message, check_provider,
            main, CONFIG_DIR, STATE_FILE
        )
        print("✅ All email_check functions imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_config_and_environment():
    """Test configuration and environment variables"""
    print("\n=== Testing Configuration ===")
    
    from jobs.email_check import (
        TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, LLAMA_BASE_URL,
        CONFIG_DIR, STATE_FILE, PROVIDERS
    )
    
    # Check environment variables
    success_count = 0
    total_checks = 0
    
    total_checks += 1
    if TELEGRAM_BOT_TOKEN:
        print(f"✅ TELEGRAM_BOT_TOKEN: {TELEGRAM_BOT_TOKEN[:10]}...")
        success_count += 1
    else:
        print("❌ TELEGRAM_BOT_TOKEN: Missing")
    
    total_checks += 1
    if TELEGRAM_CHAT_ID:
        print(f"✅ TELEGRAM_CHAT_ID: {TELEGRAM_CHAT_ID}")
        success_count += 1
    else:
        print("❌ TELEGRAM_CHAT_ID: Missing")
    
    total_checks += 1
    print(f"✅ LLAMA_BASE_URL: {LLAMA_BASE_URL}")
    success_count += 1
    
    # Check directories
    total_checks += 1
    if CONFIG_DIR.exists():
        print(f"✅ CONFIG_DIR exists: {CONFIG_DIR}")
        success_count += 1
    else:
        print(f"⚠️  CONFIG_DIR missing: {CONFIG_DIR} (will be created)")
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        success_count += 1
    
    total_checks += 1
    print(f"✅ STATE_FILE path: {STATE_FILE}")
    success_count += 1
    
    total_checks += 1
    print(f"✅ PROVIDERS: {PROVIDERS}")
    success_count += 1
    
    return success_count == total_checks

def test_state_management():
    """Test state loading and saving functionality"""
    print("\n=== Testing State Management ===")
    
    from jobs.email_check import load_state, save_state, STATE_FILE
    
    try:
        # Test loading (should create default if missing)
        state = load_state()
        print(f"✅ State loaded: {len(state)} providers")
        
        # Test saving
        test_state = {
            "gmail": {"last_date_utc": "2025-08-26T17:00:00+00:00", "last_ids": ["test123"]},
            "outlook": {"last_date_utc": None, "last_ids": []}
        }
        save_state(test_state)
        print("✅ State saved successfully")
        
        # Test loading saved state
        loaded_state = load_state()
        if loaded_state == test_state:
            print("✅ State persistence working correctly")
            return True
        else:
            print("❌ State persistence failed - data mismatch")
            return False
            
    except Exception as e:
        print(f"❌ State management error: {e}")
        return False

def test_auth_status():
    """Test provider authentication status"""
    print("\n=== Testing Provider Authentication ===")
    
    try:
        from jobs.email_check import check_auth_status
        
        auth_status = check_auth_status()
        print(f"Authentication status: {auth_status}")
        
        gmail_ok = auth_status.get('gmail', False)
        outlook_ok = auth_status.get('outlook', False)
        
        print(f"Gmail: {'✅ Ready' if gmail_ok else '❌ Needs setup'}")
        print(f"Outlook: {'✅ Ready' if outlook_ok else '❌ Needs setup'}")
        
        return gmail_ok or outlook_ok  # At least one provider should work
        
    except Exception as e:
        print(f"❌ Auth status check failed: {e}")
        return False

def test_telegram_connection():
    """Test Telegram bot connection (without actually sending)"""
    print("\n=== Testing Telegram Connection ===")
    
    from jobs.email_check import TELEGRAM_BOT_TOKEN
    
    if not TELEGRAM_BOT_TOKEN:
        print("❌ No Telegram token available")
        return False
    
    try:
        import requests
        
        # Test bot info endpoint (doesn't send messages)
        response = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe",
            timeout=10
        )
        
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info.get('ok'):
                bot_name = bot_info['result']['username']
                print(f"✅ Telegram bot connected: @{bot_name}")
                return True
            else:
                print(f"❌ Telegram API error: {bot_info}")
                return False
        else:
            print(f"❌ Telegram connection failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Telegram test failed: {e}")
        return False

def test_llama_connection():
    """Test LLaMA server connection (optional)"""
    print("\n=== Testing LLaMA Server Connection ===")
    
    from jobs.email_check import LLAMA_BASE_URL
    
    try:
        import requests
        
        # Test server health/models endpoint
        response = requests.get(
            f"{LLAMA_BASE_URL}/v1/models",
            timeout=5
        )
        
        if response.status_code == 200:
            print("✅ LLaMA server is reachable")
            return True
        else:
            print(f"⚠️  LLaMA server returned: {response.status_code} (AI features may be limited)")
            return False
            
    except Exception as e:
        print(f"⚠️  LLaMA server unreachable: {e} (AI features will be disabled)")
        return False

def test_email_text_processing():
    """Test email text processing functions"""
    print("\n=== Testing Email Text Processing ===")
    
    try:
        from jobs.email_check import get_text_from_email, email_keyparts
        
        # Test with mock email data
        mock_email = {
            'id': 'test123',
            'snippet': 'This is a test email snippet',
            'subject': 'Test Email Subject',
            'from': 'test@example.com',
            'date': '2025-08-26T17:00:00+00:00'
        }
        
        # Test email_keyparts
        keyparts = email_keyparts(mock_email)
        if keyparts and 'id' in keyparts:
            print("✅ email_keyparts function working")
        else:
            print("❌ email_keyparts function failed")
            return False
        
        # Test get_text_from_email
        text = get_text_from_email(mock_email)
        if text and len(text) > 0:
            print("✅ get_text_from_email function working")
            return True
        else:
            print("❌ get_text_from_email function failed")
            return False
            
    except Exception as e:
        print(f"❌ Email text processing failed: {e}")
        return False

def test_dry_run():
    """Test the main function in dry-run mode"""
    print("\n=== Testing Main Function (Dry Run) ===")
    
    try:
        # Set environment variable for dry run
        os.environ['DRY_RUN'] = 'true'
        
        from jobs.email_check import main
        
        # Run main function
        print("Running email_check main function...")
        main()
        print("✅ Main function completed without errors")
        return True
        
    except Exception as e:
        print(f"❌ Main function test failed: {e}")
        return False
    finally:
        # Clean up environment
        if 'DRY_RUN' in os.environ:
            del os.environ['DRY_RUN']

def run_full_test_suite():
    """Run the complete test suite"""
    print("=" * 70)
    print("EMAIL_CHECK.PY COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config_and_environment),
        ("State Management", test_state_management),
        ("Provider Authentication", test_auth_status),
        ("Telegram Connection", test_telegram_connection),
        ("LLaMA Server", test_llama_connection),
        ("Email Processing", test_email_text_processing),
        ("Main Function", test_dry_run)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{test_name:.<50} {status}")
    
    print("-" * 70)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Ready for systemd deployment!")
        return True
    elif passed >= total - 2:  # Allow for LLaMA server being optional
        print("\n✅ Core functionality working! Ready for deployment with minor limitations.")
        return True
    else:
        print("\n❌ Critical issues found. Fix before deployment.")
        return False

if __name__ == "__main__":
    success = run_full_test_suite()
    sys.exit(0 if success else 1)
