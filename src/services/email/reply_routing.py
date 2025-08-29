"""
Enhanced reply routing for hybrid Gmail/BYU architecture.
Detects BYU emails and routes replies through proper provider.
"""
import os
from typing import Dict, Optional

def detect_reply_provider(email_detail: Dict) -> str:
    """
    Determine which provider to use for replying based on email metadata.
    
    Args:
        email_detail: Email detail dict from repo.get_email_detail()
        
    Returns:
        Provider name: "outlook" for BYU emails, "gmail" for others
    """
    tags = email_detail.get("tags", [])
    
    # Rule 1: If email has BYU_ASC59 tag, it's a forwarded BYU email
    if "BYU_ASC59" in tags:
        return "outlook"  # Use BYU Outlook for replies
    
    # Rule 2: Check if original sender is from BYU domain  
    from_email = email_detail.get("from_email", "").lower()
    if "@byu.edu" in from_email:
        return "outlook"  # Use BYU Outlook for BYU domain emails
    
    # Rule 3: Check if recipient was BYU email (forwarded)
    to_emails = email_detail.get("to_emails", [])
    byu_user = os.getenv("BYU_USER", "asc59@byu.edu").lower()
    for to_email in to_emails:
        if to_email.lower() == byu_user:
            return "outlook"  # This was sent to BYU account
    
    # Default: Use Gmail for personal emails
    return "gmail"


def get_reply_from_address(provider: str) -> str:
    """Get the appropriate 'from' address for the provider."""
    if provider == "outlook":
        return os.getenv("BYU_USER", "asc59@byu.edu")
    else:
        return os.getenv("PERSONAL_TO_EMAIL", "adrianosancarneiro@gmail.com")


def prepare_reply_context(email_detail: Dict) -> Dict:
    """
    Prepare context for replying to an email with proper routing.
    
    Returns:
        Dict with provider, from_address, to_address, subject, etc.
    """
    provider = detect_reply_provider(email_detail)
    from_address = get_reply_from_address(provider)
    
    # Extract reply-to information
    original_from = email_detail.get("from_email", "")
    original_subject = email_detail.get("subject", "")
    
    # Format reply subject
    if not original_subject.lower().startswith("re:"):
        reply_subject = f"Re: {original_subject}"
    else:
        reply_subject = original_subject
    
    return {
        "provider": provider,
        "from_address": from_address,
        "to_address": original_from,
        "subject": reply_subject,
        "original_email_id": email_detail.get("id"),
        "thread_id": email_detail.get("thread_id"),
        "routing_reason": f"Detected as {provider} email"
    }


# Example usage in telegram handlers:
def enhanced_reply_handler(email_id: int, repo):
    """Enhanced reply handler with proper provider routing."""
    
    # Get email details
    detail = repo.get_email_detail(email_id)
    if not detail:
        return {"error": "Email not found"}
    
    # Prepare reply context with smart routing
    reply_context = prepare_reply_context(detail)
    
    print(f"📧 Reply routing: {reply_context['routing_reason']}")
    print(f"   Provider: {reply_context['provider']}")
    print(f"   From: {reply_context['from_address']}")
    print(f"   To: {reply_context['to_address']}")
    
    return reply_context
