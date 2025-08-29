 #!/usr/bin/env python3
"""
Setup Gmail push notifications watch.
This tells Gmail to start sending push notifications to our webhook.
"""
import sys
import os
import pathlib

# Add src to path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "src"))

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def main():
    print("🚀 Setting up Gmail push notifications...")
    
    # Load existing Gmail credentials
    token_file = "config/gmail_token.json"
    if not os.path.exists(token_file):
        print(f"❌ Error: {token_file} not found. Please run Gmail authentication first.")
        return
    
    try:
        # Create Gmail service
        creds = Credentials.from_authorized_user_file(
            token_file,
            scopes=["https://www.googleapis.com/auth/gmail.readonly"]
        )
        service = build("gmail", "v1", credentials=creds)
        
        # Get all labels to find BYU_ASC59
        print("📋 Getting Gmail labels...")
        labels_result = service.users().labels().list(userId="me").execute()
        labels = labels_result.get("labels", [])
        
        def find_label_id(name):
            if name == "INBOX":
                return "INBOX"
            for label in labels:
                if label["name"] == name:
                    return label["id"]
            return None
        
        # Find the BYU_ASC59 label
        byu_label_id = find_label_id("BYU_ASC59")
        if not byu_label_id:
            print("⚠️  Warning: BYU_ASC59 label not found. Only watching INBOX.")
            label_ids = ["INBOX"]
        else:
            print(f"✅ Found BYU_ASC59 label: {byu_label_id}")
            label_ids = ["INBOX", byu_label_id]
        
        # Start the watch
        print(f"📡 Starting Gmail watch for labels: {label_ids}")
        watch_request = {
            "topicName": "projects/personalassistant-470020/topics/gmail-push-notifications",
            "labelIds": label_ids
        }
        
        result = service.users().watch(userId="me", body=watch_request).execute()
        
        print("🎉 Gmail push notifications started successfully!")
        print(f"📊 Watch details:")
        print(f"   📧 History ID: {result.get('historyId')}")
        print(f"   ⏰ Expiration: {result.get('expiration')}")
        print(f"   🏷️  Labels: {label_ids}")
        print(f"   🎯 Topic: gmail-push-notifications")
        print(f"   🔗 Webhook: https://hooks.adrianocarneiro.com/hooks/gmail")
        
        print("\n✅ Setup complete! Your webhook will now receive Gmail push notifications.")
        print("📧 Try sending yourself an email to test it!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return

if __name__ == "__main__":
    main()
