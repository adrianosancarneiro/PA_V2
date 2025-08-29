#!/usr/bin/env python3
"""
Debug script to analyze and fix email thread detection issues
Simplified version that works with existing infrastructure
"""

import os
import sys
import json
from datetime import datetime

# Add project paths
sys.path.append('src')
from dotenv import load_dotenv
load_dotenv('/etc/pa_v2/secrets.env')

from core.database import get_conn
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def get_gmail_service():
    """Initialize and return Gmail API service"""
    try:
        # Use your existing Gmail token setup
        GMAIL_TOKEN_PATH = 'config/gmail_token.json'
        with open(GMAIL_TOKEN_PATH) as f:
            token_data = json.load(f)

        creds = Credentials(
            token=token_data['token'],
            refresh_token=token_data.get('refresh_token'),
            token_uri=token_data.get('token_uri'),
            client_id=token_data.get('client_id'),
            client_secret=token_data.get('client_secret'),
            scopes=token_data.get('scopes')
        )
        
        return build('gmail', 'v1', credentials=creds)
    except Exception as e:
        print(f"❌ Could not initialize Gmail service: {e}")
        return None

def analyze_threads():
    """Analyze current thread situation in the database"""
    with get_conn() as conn:
        cursor = conn.cursor()
        
        print("\n" + "="*80)
        print("THREAD ANALYSIS REPORT")
        print("="*80)
        
        # 1. Get thread statistics
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT id) as total_threads,
                COUNT(DISTINCT CASE WHEN provider_thread_id IS NOT NULL AND provider_thread_id != '' THEN id END) as threads_with_provider_id,
                COUNT(DISTINCT CASE WHEN provider_thread_id IS NULL OR provider_thread_id = '' THEN id END) as threads_without_provider_id
            FROM email_threads
            WHERE provider = 'gmail'
        """)
        
        stats = cursor.fetchone()
        print(f"\nThread Statistics:")
        print(f"  Total Gmail Threads: {stats[0]}")
        print(f"  Threads WITH provider_thread_id: {stats[1]}")
        print(f"  Threads WITHOUT provider_thread_id: {stats[2]}")
        
        # 2. Find the problematic threads
        cursor.execute("""
            SELECT 
                et.id,
                et.subject_last,
                et.provider_thread_id,
                COUNT(em.id) as message_count,
                MIN(em.received_at) as first_message,
                MAX(em.received_at) as last_message
            FROM email_threads et
            LEFT JOIN email_messages em ON et.id = em.thread_id
            WHERE et.provider = 'gmail'
            GROUP BY et.id, et.subject_last, et.provider_thread_id
            HAVING COUNT(em.id) > 1
            ORDER BY COUNT(em.id) DESC
            LIMIT 10
        """)
        
        print(f"\nThreads with Most Messages (potential grouping issues):")
        print("-" * 80)
        
        for thread in cursor.fetchall():
            thread_id, subject_last, provider_thread_id, message_count, first_message, last_message = thread
            provider_id_display = f"'{provider_thread_id}'" if provider_thread_id else "MISSING/EMPTY"
            print(f"  Thread ID: {thread_id}")
            print(f"    Subject: {subject_last}")
            print(f"    Provider Thread ID: {provider_id_display}")
            print(f"    Message Count: {message_count}")
            print(f"    Date Range: {first_message} to {last_message}")
            print()

def analyze_thread_9():
    """Analyze the specific problematic thread 9"""
    with get_conn() as conn:
        cursor = conn.cursor()
        
        print("\n" + "="*50)
        print("THREAD 9 DETAILED ANALYSIS")
        print("="*50)
        
        # Get thread 9 details
        cursor.execute("""
            SELECT id, provider_thread_id, subject_last, updated_at
            FROM email_threads 
            WHERE id = 9
        """)
        
        thread_info = cursor.fetchone()
        if not thread_info:
            print("❌ Thread 9 not found")
            return
            
        thread_id, provider_thread_id, subject_last, updated_at = thread_info
        print(f"Thread 9 Info:")
        print(f"  Provider Thread ID: '{provider_thread_id}'")
        print(f"  Subject: {subject_last}")
        print(f"  Updated: {updated_at}")
        
        # Get all messages in thread 9
        cursor.execute("""
            SELECT id, subject, from_email, received_at, provider_message_id
            FROM email_messages 
            WHERE thread_id = 9
            ORDER BY received_at DESC
            LIMIT 20
        """)
        
        messages = cursor.fetchall()
        print(f"\nRecent messages in Thread 9 ({len(messages)} shown):")
        print("-" * 80)
        
        distinct_subjects = set()
        distinct_senders = set()
        
        for msg in messages:
            msg_id, subject, from_email, received_at, provider_msg_id = msg
            print(f"  {msg_id}: {subject[:60]}")
            print(f"      From: {from_email}")
            print(f"      Date: {received_at}")
            print(f"      Gmail ID: {provider_msg_id}")
            print()
            
            distinct_subjects.add(subject)
            distinct_senders.add(from_email)
        
        print(f"Summary:")
        print(f"  🗂️ {len(distinct_subjects)} distinct subjects")
        print(f"  👥 {len(distinct_senders)} distinct senders")
        print(f"  📧 {len(messages)} total messages shown")

def fix_thread_9_with_gmail():
    """Fix thread 9 using Gmail API to get correct thread IDs"""
    service = get_gmail_service()
    if not service:
        print("❌ Cannot connect to Gmail API")
        return
    
    with get_conn() as conn:
        cursor = conn.cursor()
        
        print("\n" + "="*50)
        print("FIXING THREAD 9 WITH GMAIL API")
        print("="*50)
        
        # Get all messages in thread 9
        cursor.execute("""
            SELECT id, provider_message_id, subject, from_email, received_at
            FROM email_messages 
            WHERE thread_id = 9
            ORDER BY received_at ASC
        """)
        
        messages = cursor.fetchall()
        print(f"Found {len(messages)} messages in thread 9")
        
        # Group messages by their actual Gmail thread IDs
        thread_groups = {}
        failed_messages = []
        
        for msg in messages:
            msg_id, provider_msg_id, subject, from_email, received_at = msg
            
            if not provider_msg_id:
                print(f"⚠️ Message {msg_id} has no Gmail ID, skipping")
                failed_messages.append(msg)
                continue
                
            try:
                # Get the actual Gmail thread ID
                gmail_msg = service.users().messages().get(
                    userId='me',
                    id=provider_msg_id
                ).execute()
                
                actual_thread_id = gmail_msg.get('threadId')
                
                if actual_thread_id:
                    if actual_thread_id not in thread_groups:
                        thread_groups[actual_thread_id] = []
                    
                    thread_groups[actual_thread_id].append({
                        'msg_id': msg_id,
                        'provider_msg_id': provider_msg_id,
                        'subject': subject,
                        'from_email': from_email,
                        'received_at': received_at
                    })
                    
                    print(f"✓ Message {msg_id}: Gmail thread {actual_thread_id}")
                else:
                    print(f"⚠️ Message {msg_id}: No threadId from Gmail")
                    failed_messages.append(msg)
                    
            except Exception as e:
                print(f"❌ Error fetching Gmail message {provider_msg_id}: {e}")
                failed_messages.append(msg)
        
        print(f"\n📊 Results:")
        print(f"  ✅ {len(thread_groups)} distinct Gmail threads found")
        print(f"  ❌ {len(failed_messages)} messages couldn't be processed")
        
        for gmail_thread_id, msgs in thread_groups.items():
            print(f"\n🧵 Gmail Thread {gmail_thread_id}: {len(msgs)} messages")
            for msg in msgs[:3]:  # Show first 3
                print(f"     - {msg['subject'][:50]} from {msg['from_email']}")
            if len(msgs) > 3:
                print(f"     ... and {len(msgs) - 3} more")
        
        # Ask user if they want to proceed with the fix
        if len(thread_groups) <= 1:
            print("\n✅ All messages belong to the same Gmail thread - no fix needed!")
            return
            
        response = input(f"\n❓ Split these {len(messages)} messages into {len(thread_groups)} proper threads? (y/n): ")
        if response.lower() != 'y':
            print("❌ Fix cancelled")
            return
        
        # Perform the fix
        first_thread = True
        total_moved = 0
        
        for gmail_thread_id, msgs in thread_groups.items():
            if first_thread:
                # Update thread 9 with the correct provider_thread_id
                cursor.execute("""
                    UPDATE email_threads
                    SET provider_thread_id = %s,
                        subject_last = %s,
                        updated_at = NOW()
                    WHERE id = 9
                """, (gmail_thread_id, msgs[-1]['subject']))
                
                print(f"✅ Updated thread 9 with Gmail thread ID: {gmail_thread_id}")
                print(f"   Subject: {msgs[-1]['subject']}")
                print(f"   {len(msgs)} messages remain in thread 9")
                first_thread = False
            else:
                # Create new thread
                cursor.execute("""
                    INSERT INTO email_threads (
                        provider, provider_thread_id, subject_last, updated_at
                    ) VALUES (%s, %s, %s, NOW())
                    RETURNING id
                """, ('gmail', gmail_thread_id, msgs[-1]['subject']))
                
                new_thread_id = cursor.fetchone()[0]
                
                # Move messages to new thread
                msg_ids = [msg['msg_id'] for msg in msgs]
                cursor.execute("""
                    UPDATE email_messages
                    SET thread_id = %s
                    WHERE id = ANY(%s)
                """, (new_thread_id, msg_ids))
                
                total_moved += len(msg_ids)
                print(f"✅ Created thread {new_thread_id} for Gmail thread {gmail_thread_id}")
                print(f"   Subject: {msgs[-1]['subject']}")
                print(f"   Moved {len(msgs)} messages to new thread")
        
        conn.commit()
        print(f"\n🎉 Thread 9 fix completed!")
        print(f"   📊 Moved {total_moved} messages to new threads")
        print(f"   🧵 Created {len(thread_groups) - 1} new threads")

def verify_fix():
    """Verify that the fix worked correctly"""
    with get_conn() as conn:
        cursor = conn.cursor()
        
        print("\n" + "="*50)
        print("VERIFICATION REPORT")
        print("="*50)
        
        # Check for threads with empty provider_thread_id
        cursor.execute("""
            SELECT COUNT(*) FROM email_threads 
            WHERE provider = 'gmail' AND (provider_thread_id = '' OR provider_thread_id IS NULL)
        """)
        empty_threads = cursor.fetchone()[0]
        
        # Check total Gmail threads
        cursor.execute("SELECT COUNT(*) FROM email_threads WHERE provider = 'gmail'")
        total_threads = cursor.fetchone()[0]
        
        print(f"📊 Gmail threads: {total_threads} total, {empty_threads} with empty provider_thread_id")
        
        if empty_threads == 0:
            print("✅ All Gmail threads now have proper provider_thread_id!")
        else:
            print(f"⚠️ Still {empty_threads} threads with empty provider_thread_id")
        
        # Show recent thread distribution
        cursor.execute("""
            SELECT et.id, et.provider_thread_id, COUNT(em.id) as msg_count, et.subject_last
            FROM email_threads et
            LEFT JOIN email_messages em ON et.id = em.thread_id
            WHERE et.provider = 'gmail'
            GROUP BY et.id, et.provider_thread_id, et.subject_last
            ORDER BY msg_count DESC
            LIMIT 10
        """)
        
        print(f"\n📧 Top Gmail threads by message count:")
        for row in cursor.fetchall():
            thread_id, provider_thread_id, msg_count, subject = row
            display_id = f'"{provider_thread_id}"' if provider_thread_id else '"" (EMPTY)'
            print(f"   Thread {thread_id}: {display_id} → {msg_count} msgs - {subject[:40] if subject else 'No Subject'}")

def main():
    """Main function to run all diagnostics and fixes"""
    print("\n" + "="*80)
    print("EMAIL THREAD DETECTION DIAGNOSTIC & FIX TOOL")
    print("="*80)
    
    while True:
        print("\nOptions:")
        print("1. Analyze all threads")
        print("2. Analyze thread 9 specifically")
        print("3. Fix thread 9 with Gmail API")
        print("4. Verify fix results")
        print("5. Exit")
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == '1':
            analyze_threads()
        elif choice == '2':
            analyze_thread_9()
        elif choice == '3':
            fix_thread_9_with_gmail()
        elif choice == '4':
            verify_fix()
        elif choice == '5':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid option")

if __name__ == "__main__":
    main()
