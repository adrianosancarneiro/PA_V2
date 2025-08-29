"""Gmail push notification lifecycle management."""
import os
import sys
import pathlib
from datetime import datetime, timedelta, timezone

# Add project root to path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from repo.push_repo import PushRepo
from providers.gmail_helpers import build_service, get_label_id
from providers.gmail_admin import gmail_watch_start

# Configuration from environment
GMAIL_TOKEN_PATH = os.getenv("GMAIL_TOKEN_PATH", "config/gmail_token.json")
GCP_TOPIC = os.getenv("GMAIL_PUBSUB_TOPIC", "projects/your-project/topics/gmail-push")
WATCH_LABELS = os.getenv("GMAIL_WATCH_LABELS", "INBOX,BYU_ASC59").split(",")


def _load_creds():
    """Load Gmail OAuth credentials."""
    from google.oauth2.credentials import Credentials
    return Credentials.from_authorized_user_file(GMAIL_TOKEN_PATH, scopes=[
        "https://www.googleapis.com/auth/gmail.readonly"
    ])


def run():
    """Set up or renew Gmail push notifications."""
    print(f"🔧 Setting up Gmail push notifications...")
    print(f"📋 Topic: {GCP_TOPIC}")
    print(f"🏷️ Labels: {WATCH_LABELS}")
    
    try:
        push = PushRepo()
        creds = _load_creds()
        svc = build_service(creds)

        # Resolve label IDs by name
        label_ids = []
        for name in WATCH_LABELS:
            name = name.strip()
            if name == "INBOX":
                label_ids.append("INBOX")
            else:
                try:
                    label_id = get_label_id(svc, name)
                    label_ids.append(label_id)
                    print(f"✅ Found label '{name}' -> ID: {label_id}")
                except RuntimeError as e:
                    print(f"⚠️ {e}")
                    continue

        if not label_ids:
            print("❌ No valid labels found to watch")
            return False

        # Start Gmail watch
        result = gmail_watch_start(creds, topic_name=GCP_TOPIC, label_ids=label_ids)
        
        history_id = result.get("historyId")
        expiration = result.get("expiration")  # Unix timestamp in milliseconds
        
        print(f"🎉 Gmail watch started successfully!")
        print(f"📊 History ID: {history_id}")
        print(f"⏰ Expires: {expiration}")
        
        # Update database state
        if history_id:
            push.set_gmail_last_history_id(int(history_id))
        
        if expiration:
            # Convert milliseconds to datetime
            exp_dt = datetime.fromtimestamp(int(expiration) / 1000, tz=timezone.utc)
            push.update_gmail_watch(exp_dt)
            print(f"📅 Watch expires at: {exp_dt}")
        
        push.set_push_state("gmail", "healthy")
        return True
        
    except Exception as e:
        print(f"❌ Error setting up Gmail push: {e}")
        push.set_push_state("gmail", "down")
        return False


if __name__ == "__main__":
    success = run()
    if success:
        print("✅ Gmail push lifecycle setup complete")
    else:
        print("❌ Gmail push lifecycle setup failed")
        sys.exit(1)
