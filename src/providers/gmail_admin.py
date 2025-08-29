"""Gmail administration functions for webhook management."""
from typing import List, Dict
from googleapiclient.discovery import build


def gmail_watch_start(creds, topic_name: str, label_ids: List[str]) -> Dict:
    """
    Start Gmail push notifications for specified labels.
    
    Args:
        creds: Gmail API credentials
        topic_name: Google Cloud Pub/Sub topic name (e.g., "projects/my-project/topics/gmail-push")
        label_ids: List of label IDs to watch (e.g., ["INBOX", "Label_123"])
    
    Returns:
        Dict with 'historyId' and 'expiration' fields
    """
    svc = build("gmail", "v1", credentials=creds)
    body = {"topicName": topic_name}
    if label_ids:
        body["labelIds"] = label_ids
    
    return svc.users().watch(userId="me", body=body).execute()


def gmail_stop_watch(creds) -> Dict:
    """Stop Gmail push notifications."""
    svc = build("gmail", "v1", credentials=creds)
    return svc.users().stop(userId="me").execute()


def gmail_get_profile(creds) -> Dict:
    """Get Gmail profile information."""
    svc = build("gmail", "v1", credentials=creds)
    return svc.users().getProfile(userId="me").execute()
