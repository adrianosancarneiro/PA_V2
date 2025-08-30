#!/usr/bin/env python3
"""
LLM Memory Management Tool
Manage conversation memory for the PA_V2 Telegram bot
"""
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.shared.llm_client import LLMClient

def list_users(memory_dir: Path):
    """List all users with conversation history"""
    conversation_file = memory_dir / "conversation.jsonl"
    long_term_file = memory_dir / "long_term_memory.json"
    
    users = set()
    
    # Get users from conversation log
    if conversation_file.exists():
        with conversation_file.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    msg = json.loads(line.strip())
                    users.add(msg.get("user_id", "default"))
                except json.JSONDecodeError:
                    continue
    
    # Get users from long-term memory
    if long_term_file.exists():
        try:
            with long_term_file.open("r", encoding="utf-8") as f:
                memory_data = json.load(f)
                users.update(memory_data.keys())
        except json.JSONDecodeError:
            pass
    
    return sorted(list(users))

def show_user_summary(client: LLMClient, user_id: str):
    """Show summary and stats for a user"""
    history = client._load_conversation_history(user_id, max_items=10000)
    long_term = client._load_long_term_memory(user_id)
    
    print(f"\n📊 Summary for User: {user_id}")
    print("=" * 50)
    
    if history:
        print(f"Total Messages: {len(history)}")
        first_msg = history[0]
        last_msg = history[-1]
        print(f"First Message: {first_msg['timestamp']}")
        print(f"Last Message: {last_msg['timestamp']}")
        
        # Count message types
        user_msgs = sum(1 for msg in history if msg['role'] == 'user')
        assistant_msgs = sum(1 for msg in history if msg['role'] == 'assistant')
        print(f"User Messages: {user_msgs}")
        print(f"Assistant Messages: {assistant_msgs}")
    else:
        print("No conversation history found")
    
    print(f"\n💭 Long-term Memory:")
    if long_term.get('summary'):
        print(f"Summary: {long_term['summary']}")
    else:
        print("No summary yet")
    
    if long_term.get('facts'):
        print(f"\nKey Facts ({len(long_term['facts'])}):")
        for i, fact in enumerate(long_term['facts'], 1):
            print(f"  {i}. {fact}")
    else:
        print("No facts stored yet")
    
    if long_term.get('last_updated'):
        print(f"\nLast Updated: {long_term['last_updated']}")

def clear_user_memory(client: LLMClient, user_id: str, confirm: bool = False):
    """Clear all memory for a user"""
    if not confirm:
        response = input(f"Are you sure you want to clear ALL memory for user '{user_id}'? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            return
    
    # Clear conversation history
    conversation_file = client.conversation_file
    if conversation_file.exists():
        # Read all messages except for this user
        remaining_messages = []
        with conversation_file.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    msg = json.loads(line.strip())
                    if msg.get("user_id") != user_id:
                        remaining_messages.append(line)
                except json.JSONDecodeError:
                    remaining_messages.append(line)  # Keep malformed lines
        
        # Write back without this user's messages
        with conversation_file.open("w", encoding="utf-8") as f:
            f.writelines(remaining_messages)
    
    # Clear long-term memory
    long_term_file = client.long_term_memory_file
    if long_term_file.exists():
        try:
            with long_term_file.open("r", encoding="utf-8") as f:
                all_memory = json.load(f)
            
            if user_id in all_memory:
                del all_memory[user_id]
                
                with long_term_file.open("w", encoding="utf-8") as f:
                    json.dump(all_memory, f, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass
    
    print(f"✅ Cleared all memory for user '{user_id}'")

def export_user_data(client: LLMClient, user_id: str, output_file: str):
    """Export all data for a user"""
    history = client._load_conversation_history(user_id, max_items=10000)
    long_term = client._load_long_term_memory(user_id)
    
    export_data = {
        "user_id": user_id,
        "exported_at": datetime.now().isoformat(),
        "conversation_history": history,
        "long_term_memory": long_term
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Exported data for user '{user_id}' to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Manage LLM conversation memory")
    parser.add_argument("--memory-dir", 
                       default="/home/mentorius/AI_Services/PA_V2/data/llm_memory",
                       help="Path to memory directory")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List users
    subparsers.add_parser("list", help="List all users")
    
    # Show user summary
    summary_parser = subparsers.add_parser("summary", help="Show user summary")
    summary_parser.add_argument("user_id", help="User ID to show summary for")
    
    # Clear user memory
    clear_parser = subparsers.add_parser("clear", help="Clear user memory")
    clear_parser.add_argument("user_id", help="User ID to clear")
    clear_parser.add_argument("--yes", action="store_true", help="Skip confirmation")
    
    # Export user data
    export_parser = subparsers.add_parser("export", help="Export user data")
    export_parser.add_argument("user_id", help="User ID to export")
    export_parser.add_argument("output_file", help="Output file path")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    memory_dir = Path(args.memory_dir)
    if not memory_dir.exists():
        print(f"❌ Memory directory does not exist: {memory_dir}")
        return
    
    # Create client instance for memory operations
    client = LLMClient()
    
    if args.command == "list":
        users = list_users(memory_dir)
        if users:
            print(f"👥 Found {len(users)} users with conversation history:")
            for user in users:
                print(f"  - {user}")
        else:
            print("No users found with conversation history")
    
    elif args.command == "summary":
        show_user_summary(client, args.user_id)
    
    elif args.command == "clear":
        clear_user_memory(client, args.user_id, args.yes)
    
    elif args.command == "export":
        export_user_data(client, args.user_id, args.output_file)

if __name__ == "__main__":
    main()
