#!/usr/bin/env python3
"""
Script to get the correct Telegram chat ID for the bot
"""
import os
import requests
from dotenv import load_dotenv

# Load system secrets
load_dotenv('/etc/pa_v2/secrets.env')

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

def get_chat_id():
    """Get recent chat updates to find the correct chat ID"""
    if not TOKEN:
        print("❌ No TELEGRAM_BOT_TOKEN found")
        return
    
    try:
        # Get recent updates
        response = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/getUpdates",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok') and data.get('result'):
                print("📬 Recent chats:")
                for update in data['result']:
                    if 'message' in update:
                        chat = update['message']['chat']
                        print(f"  Chat ID: {chat['id']} - Type: {chat['type']} - Title: {chat.get('title', chat.get('first_name', 'Unknown'))}")
                
                if data['result']:
                    latest_chat_id = data['result'][-1]['message']['chat']['id']
                    print(f"\n✅ Most recent chat ID: {latest_chat_id}")
                    print(f"Add this to /etc/pa_v2/secrets.env:")
                    print(f"TELEGRAM_CHAT_ID={latest_chat_id}")
                else:
                    print("📭 No recent messages found")
                    print("💡 Send a message to your bot first, then run this script again")
            else:
                print(f"❌ Telegram API error: {data}")
        else:
            print(f"❌ Request failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_bot_info():
    """Get bot information"""
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/getMe",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot = data['result']
                print(f"🤖 Bot Info:")
                print(f"  Name: {bot['first_name']}")
                print(f"  Username: @{bot['username']}")
                print(f"  ID: {bot['id']}")
                return True
        
        print("❌ Failed to get bot info")
        return False
        
    except Exception as e:
        print(f"❌ Error getting bot info: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("TELEGRAM BOT CHAT ID FINDER")
    print("=" * 50)
    
    if test_bot_info():
        print("\n" + "=" * 50)
        get_chat_id()
    
    print("\n" + "=" * 50)
    print("📝 Instructions:")
    print("1. If no chat ID found, send a message to your bot first")
    print("2. Then run this script again to get the chat ID")
    print("3. Update TELEGRAM_CHAT_ID in /etc/pa_v2/secrets.env")
    print("=" * 50)
