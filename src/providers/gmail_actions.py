"""Gmail thread actions for PA_V2"""

def gmail_trash_thread(service, thread_id: str):
    """Move a Gmail thread to trash"""
    service.users().threads().trash(userId="me", id=thread_id).execute()

def gmail_untrash_thread(service, thread_id: str):
    """Restore a Gmail thread from trash"""
    service.users().threads().untrash(userId="me", id=thread_id).execute()
