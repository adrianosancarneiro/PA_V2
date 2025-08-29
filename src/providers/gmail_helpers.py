"""Gmail helper functions for API operations."""
from typing import Dict, Any, List
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


def build_service(creds: Credentials):
    """Build Gmail API service object."""
    return build("gmail", "v1", credentials=creds)


def get_label_id(svc, label_name: str) -> str:
    """
    Get Gmail label ID by name.
    
    Args:
        svc: Gmail API service object
        label_name: Name of the label (e.g., "BYU_ASC59", "INBOX")
    
    Returns:
        Label ID string
        
    Raises:
        RuntimeError: If label is not found
    """
    labels_result = svc.users().labels().list(userId="me").execute()
    labels = labels_result.get("labels", [])
    
    for label in labels:
        if label["name"] == label_name:
            return label["id"]
    
    raise RuntimeError(f"Label not found: {label_name}")


def gmail_fetch_message_by_id(svc, msg_id: str) -> Dict[str, Any]:
    """
    Fetch a complete Gmail message by ID.
    
    Args:
        svc: Gmail API service object
        msg_id: Gmail message ID
        
    Returns:
        Complete message dict with headers, body, etc.
    """
    return svc.users().messages().get(userId="me", id=msg_id, format="full").execute()


def gmail_history_list(svc, start_history_id: int) -> Dict[str, Any]:
    """
    List Gmail history changes since a given history ID.
    
    Args:
        svc: Gmail API service object
        start_history_id: History ID to start from
        
    Returns:
        Dict with 'history' array containing changes
    """
    return svc.users().history().list(
        userId="me", 
        startHistoryId=start_history_id,
        historyTypes=["messageAdded"]
    ).execute()


def get_all_labels(svc) -> List[Dict[str, Any]]:
    """Get all Gmail labels."""
    return svc.users().labels().list(userId="me").execute().get("labels", [])


def gmail_search_messages(svc, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search Gmail messages with a query.
    
    Args:
        svc: Gmail API service object
        query: Gmail search query (e.g., "is:unread", "from:example@gmail.com")
        max_results: Maximum number of results
        
    Returns:
        List of message dicts with basic info
    """
    result = svc.users().messages().list(
        userId="me", 
        q=query, 
        maxResults=max_results
    ).execute()
    
    return result.get("messages", [])
