#!/usr/bin/env python3
"""
Debug script to analyze and fix email thread detection issues
This script helps identify why threads are being incorrectly grouped
"""

import os
import sys
from datetime import datetime
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import logging

# Add project paths
sys.path.append('src')
from dotenv import load_dotenv
load_dotenv('/etc/pa_v2/secrets.env')

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Use the existing database connection from your setup
from core.database import get_conn

def get_db_connection():
    """Create and return a database connection using existing setup"""
    return get_conn()

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
        logger.error(f"Could not initialize Gmail service: {e}")
        return None

def analyze_threads():
    """Analyze current thread situation in the database"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        print("\n" + "="*80)
        print("THREAD ANALYSIS REPORT")
        print("="*80)
        
        # 1. Get thread statistics (adjusted for your schema)
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
        print(f"  Total Gmail Threads: {stats['total_threads']}")
        print(f"  Threads WITH provider_thread_id: {stats['threads_with_provider_id']}")
        print(f"  Threads WITHOUT provider_thread_id: {stats['threads_without_provider_id']}")
        
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
            provider_id_display = f"'{thread['provider_thread_id']}'" if thread['provider_thread_id'] else "MISSING/EMPTY"
            print(f"  Thread ID: {thread['id']}")
            print(f"    Subject: {thread['subject_last']}")
            print(f"    Provider Thread ID: {provider_id_display}")
            print(f"    Message Count: {thread['message_count']}")
            print(f"    Date Range: {thread['first_message']} to {thread['last_message']}")
            print()
        
        # 3. Check for messages with mismatched subjects in same thread
        cursor.execute("""
            SELECT 
                em.id,
                em.thread_id,
                em.subject,
                em.from_email,
                em.received_at,
                et.subject_last as thread_subject,
                et.provider_thread_id
            FROM email_messages em
            JOIN email_threads et ON em.thread_id = et.id
            WHERE et.provider = 'gmail'
            AND em.subject != et.subject_last 
            AND em.subject NOT LIKE 'Re:%' || et.subject_last || '%'
            AND em.subject NOT LIKE 'RE:%' || et.subject_last || '%'
            ORDER BY em.received_at DESC
            LIMIT 15
        """)
        
        mismatched = cursor.fetchall()
        if mismatched:
            print(f"\nMessages with Mismatched Subjects (potential wrong thread assignment):")
            print("-" * 80)
            for msg in mismatched:
                print(f"  Message ID: {msg['id']} (Thread {msg['thread_id']})")
                print(f"    Message Subject: {msg['subject']}")
                print(f"    Thread Subject: {msg['thread_subject']}")
                print(f"    Provider Thread ID: {msg['provider_thread_id'] or 'MISSING'}")
                print(f"    From: {msg['from_email']}")
                print(f"    Date: {msg['received_at']}")
                print()

def fetch_gmail_threads():
    """Fetch thread information directly from Gmail API"""
    service = get_gmail_service()
    if not service:
        print("Cannot connect to Gmail API")
        return
    
    print("\n" + "="*80)
    print("GMAIL API THREAD INFORMATION")
    print("="*80)
    
    try:
        # Get recent messages
        results = service.users().messages().list(
            userId='me',
            maxResults=20,
            q='newer_than:2d'
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            print('No recent messages found.')
            return
        
        thread_map = {}
        
        for msg in messages:
            # Get full message details
            message = service.users().messages().get(
                userId='me',
                id=msg['id']
            ).execute()
            
            thread_id = message.get('threadId')
            msg_id = message.get('id')
            
            # Extract headers
            headers = message['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            from_email = next((h['value'] for h in headers if h['name'] == 'From'), '')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            if thread_id not in thread_map:
                thread_map[thread_id] = {
                    'thread_id': thread_id,
                    'messages': [],
                    'subjects': set(),
                    'from_emails': set()
                }
            
            thread_map[thread_id]['messages'].append({
                'id': msg_id,
                'subject': subject,
                'from': from_email,
                'date': date
            })
            thread_map[thread_id]['subjects'].add(subject)
            thread_map[thread_id]['from_emails'].add(from_email)
        
        print(f"\nFound {len(thread_map)} unique Gmail threads:")
        print("-" * 80)
        
        for thread_id, thread_data in thread_map.items():
            print(f"\nGmail Thread ID: {thread_id}")
            print(f"  Message Count: {len(thread_data['messages'])}")
            print(f"  Subjects: {list(thread_data['subjects'])}")
            print(f"  From: {list(thread_data['from_emails'])}")
            if len(thread_data['messages']) <= 3:
                print(f"  Messages:")
                for msg in thread_data['messages']:
                    print(f"    - {msg['date']}: {msg['subject']}")
            else:
                print(f"  First/Last Messages:")
                print(f"    - {thread_data['messages'][0]['date']}: {thread_data['messages'][0]['subject']}")
                print(f"    - {thread_data['messages'][-1]['date']}: {thread_data['messages'][-1]['subject']}")
        
    except Exception as e:
        print(f"Error fetching Gmail threads: {e}")

def fix_thread_associations():
    """Fix incorrect thread associations in the database"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        print("\n" + "="*80)
        print("FIXING THREAD ASSOCIATIONS")
        print("="*80)
        
        service = get_gmail_service()
        if not service:
            print("Cannot connect to Gmail API - manual fix only")
            return
            
        # Get all messages that might be incorrectly grouped
        cursor.execute("""
            SELECT DISTINCT
                em.id as message_id,
                em.provider_message_id,
                em.thread_id,
                em.subject,
                em.from_email,
                et.provider_thread_id
            FROM email_messages em
            JOIN email_threads et ON em.thread_id = et.id
            WHERE et.provider = 'gmail'
            AND em.provider_message_id IS NOT NULL
            ORDER BY em.id DESC
            LIMIT 50
        """)
        
        messages = cursor.fetchall()
        
        fixes_made = 0
        threads_created = 0
        
        for msg in messages:
            if not msg['provider_message_id']:
                continue
                
            try:
                # Get the actual Gmail thread ID
                gmail_msg = service.users().messages().get(
                    userId='me',
                    id=msg['provider_message_id']
                ).execute()
                
                actual_thread_id = gmail_msg.get('threadId')
                
                if actual_thread_id:
                    # Check if this matches the current thread
                    if msg['provider_thread_id'] != actual_thread_id:
                        print(f"\nMismatch found for message {msg['message_id']}:")
                        print(f"  Current thread provider_id: '{msg['provider_thread_id']}'")
                        print(f"  Actual Gmail thread ID: '{actual_thread_id}'")
                        print(f"  Subject: {msg['subject']}")
                        
                        # Check if correct thread exists
                        cursor.execute("""
                            SELECT id FROM email_threads 
                            WHERE provider_thread_id = %s AND provider = 'gmail'
                        """, (actual_thread_id,))
                        
                        correct_thread = cursor.fetchone()
                        
                        if correct_thread:
                            # Move message to correct thread
                            cursor.execute("""
                                UPDATE email_messages 
                                SET thread_id = %s
                                WHERE id = %s
                            """, (correct_thread['id'], msg['message_id']))
                            
                            print(f"  ✓ Moved to correct thread {correct_thread['id']}")
                            fixes_made += 1
                        else:
                            # Create new thread with correct provider_thread_id
                            cursor.execute("""
                                INSERT INTO email_threads (
                                    provider, provider_thread_id, subject_last,
                                    updated_at
                                ) VALUES (%s, %s, %s, NOW())
                                RETURNING id
                            """, (
                                'gmail', actual_thread_id, msg['subject']
                            ))
                            
                            new_thread = cursor.fetchone()
                            
                            # Move message to new thread
                            cursor.execute("""
                                UPDATE email_messages 
                                SET thread_id = %s
                                WHERE id = %s
                            """, (new_thread['id'], msg['message_id']))
                            
                            print(f"  ✓ Created new thread {new_thread['id']} and moved message")
                            threads_created += 1
                            fixes_made += 1
                            
            except Exception as e:
                print(f"Error processing message {msg['message_id']}: {e}")
                continue
        
        if fixes_made > 0:
            conn.commit()
            print(f"\n✓ Fixed {fixes_made} messages")
            print(f"✓ Created {threads_created} new threads")
        else:
            print("\n✓ No fixes needed")

def reset_thread_9():
    """Special function to fix the specific issue with thread ID 9"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        print("\n" + "="*80)
        print("FIXING THREAD ID 9 ISSUE")
        print("="*80)
        
        # Get all messages in thread 9
        cursor.execute("""
            SELECT 
                id,
                subject,
                from_email,
                provider_message_id,
                received_at
            FROM email_messages
            WHERE thread_id = 9
            ORDER BY received_at
        """)
        
        messages = cursor.fetchall()
        
        print(f"Found {len(messages)} messages in thread 9")
        
        service = get_gmail_service()
        
        if service:
            # Group messages by their actual Gmail thread IDs
            thread_groups = {}
            
            for msg in messages:
                if msg['provider_message_id']:
                    try:
                        gmail_msg = service.users().messages().get(
                            userId='me',
                            id=msg['provider_message_id']
                        ).execute()
                        
                        thread_id = gmail_msg.get('threadId')
                        
                        if thread_id not in thread_groups:
                            thread_groups[thread_id] = []
                        
                        thread_groups[thread_id].append(msg)
                        
                    except Exception as e:
                        print(f"Error fetching Gmail message {msg['provider_message_id']}: {e}")
            
            print(f"\nFound {len(thread_groups)} distinct Gmail threads in thread 9")
            
            # Ask user for confirmation
            response = input(f"\nSplit these {len(messages)} messages into {len(thread_groups)} proper threads? (y/n): ")
            if response.lower() != 'y':
                print("❌ Fix cancelled")
                return
            
            # Create new threads for each Gmail thread (except update thread 9 for the first one)
            first_thread = True
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
                    
                    print(f"✓ Updated thread 9 with Gmail thread ID: {gmail_thread_id}")
                    print(f"  Subject: {msgs[-1]['subject']}")
                    print(f"  {len(msgs)} messages remain in thread 9")
                    first_thread = False
                else:
                    # Create new thread
                    cursor.execute("""
                        INSERT INTO email_threads (
                            provider, provider_thread_id, subject_last,
                            updated_at
                        ) VALUES (%s, %s, %s, NOW())
                        RETURNING id
                    """, (
                        'gmail', gmail_thread_id, msgs[-1]['subject']
                    ))
                    
                    new_thread = cursor.fetchone()
                    
                    # Move messages to new thread
                    msg_ids = [m['id'] for m in msgs]
                    cursor.execute("""
                        UPDATE email_messages
                        SET thread_id = %s
                        WHERE id = ANY(%s)
                    """, (new_thread['id'], msg_ids))
                    
                    print(f"✓ Created thread {new_thread['id']} for Gmail thread {gmail_thread_id}")
                    print(f"  Subject: {msgs[-1]['subject']}")
                    print(f"  Moved {len(msgs)} messages to new thread")
        
        else:
            print("\nGmail API not available - using subject-based grouping...")
            
            # Manual fix based on subject lines
            subject_groups = {}
            for msg in messages:
                # Clean subject
                subject = msg['subject']
                for prefix in ['Re:', 'RE:', 'Fwd:', 'FW:']:
                    if subject.startswith(prefix):
                        subject = subject[len(prefix):].strip()
                
                if subject not in subject_groups:
                    subject_groups[subject] = []
                subject_groups[subject].append(msg)
            
            print(f"Found {len(subject_groups)} distinct subjects")
            
            # Ask user for confirmation
            response = input(f"\nSplit messages into {len(subject_groups)} threads by subject? (y/n): ")
            if response.lower() != 'y':
                print("❌ Fix cancelled")
                return
            
            first_group = True
            for subject, msgs in subject_groups.items():
                if first_group:
                    # Keep first group in thread 9
                    cursor.execute("""
                        UPDATE email_threads
                        SET subject_last = %s,
                            updated_at = NOW()
                        WHERE id = 9
                    """, (msgs[-1]['subject'],))
                    print(f"✓ Updated thread 9 subject to: {msgs[-1]['subject']}")
                    first_group = False
                else:
                    # Create new thread
                    cursor.execute("""
                        INSERT INTO email_threads (
                            provider, subject_last, updated_at
                        ) VALUES (%s, %s, NOW())
                        RETURNING id
                    """, (
                        'gmail', msgs[-1]['subject']
                    ))
                    
                    new_thread = cursor.fetchone()
                    
                    # Move messages
                    msg_ids = [m['id'] for m in msgs]
                    cursor.execute("""
                        UPDATE email_messages
                        SET thread_id = %s
                        WHERE id = ANY(%s)
                    """, (new_thread['id'], msg_ids))
                    
                    print(f"✓ Created thread {new_thread['id']} for subject: {subject}")
                    print(f"  Moved {len(msgs)} messages")
        
        conn.commit()
        print("\n✅ Thread 9 fix completed")

def main():
    """Main function to run all diagnostics and fixes"""
    print("\n" + "="*80)
    print("EMAIL THREAD DETECTION DIAGNOSTIC & FIX TOOL")
    print("="*80)
    
    while True:
        print("\nOptions:")
        print("1. Analyze current threads")
        print("2. Fetch Gmail thread information")
        print("3. Fix thread associations (auto)")
        print("4. Fix thread ID 9 specifically")
        print("5. Run all diagnostics")
        print("6. Exit")
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == '1':
            analyze_threads()
        elif choice == '2':
            fetch_gmail_threads()
        elif choice == '3':
            fix_thread_associations()
        elif choice == '4':
            reset_thread_9()
        elif choice == '5':
            analyze_threads()
            fetch_gmail_threads()
            fix_thread_associations()
        elif choice == '6':
            break
        else:
            print("Invalid option")

if __name__ == "__main__":
    main()
