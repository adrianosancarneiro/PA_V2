"""
Email search service that provides intelligent email retrieval capabilities
for the LLM to use in conversations with users.
"""
import os
import sys
import pathlib
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import re

# Add project root to path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from services.email.email_repo import EmailRepo
from services.email.providers.gmail_provider import GmailProvider
from services.email.providers.outlook_provider import OutlookGraphProvider


class EmailSearchService:
    """Service for intelligent email search and retrieval"""
    
    def __init__(self):
        self.repo = EmailRepo()
        self.gmail = None
        self.outlook = None
        
        try:
            self.gmail = GmailProvider()
            if not self.gmail.is_authenticated():
                self.gmail = None
        except:
            self.gmail = None
            
        try:
            self.outlook = OutlookGraphProvider()
            if not self.outlook.is_authenticated():
                self.outlook = None
        except:
            self.outlook = None
    
    def search_emails(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search emails based on various parameters
        
        Args:
            query_params: Dictionary containing search parameters like:
                - from_email: Email address of sender
                - subject_contains: Text that should be in subject
                - body_contains: Text that should be in body  
                - days_back: How many days back to search (default 30)
                - provider: 'gmail' or 'outlook' (default: both)
                - limit: Maximum number of results (default 10)
                - unread_only: Only unread emails (default False)
                - important_only: Only important emails (default False)
        
        Returns:
            Dictionary with search results and metadata
        """
        results = {
            'emails': [],
            'total_found': 0,
            'search_params': query_params,
            'providers_searched': [],
            'errors': []
        }
        
        # Extract search parameters with defaults
        from_email = query_params.get('from_email', '').lower()
        subject_contains = query_params.get('subject_contains', '')
        body_contains = query_params.get('body_contains', '')
        days_back = query_params.get('days_back', 30)
        provider = query_params.get('provider', 'both')
        limit = query_params.get('limit', 10)
        unread_only = query_params.get('unread_only', False)
        important_only = query_params.get('important_only', False)
        
        # Calculate date threshold
        since_date = datetime.now() - timedelta(days=days_back)
        
        try:
            # Search in local database first
            emails = self._search_local_database(
                from_email=from_email,
                subject_contains=subject_contains,
                body_contains=body_contains,
                since_date=since_date,
                limit=limit * 2,  # Get more from DB to filter
                unread_only=unread_only,
                important_only=important_only
            )
            
            # Filter and format results
            filtered_emails = []
            for email in emails:
                if len(filtered_emails) >= limit:
                    break
                    
                # Apply provider filter
                if provider != 'both' and email.get('provider') != provider:
                    continue
                    
                filtered_emails.append(self._format_email_for_display(email))
            
            results['emails'] = filtered_emails
            results['total_found'] = len(filtered_emails)
            results['providers_searched'] = ['database']
            
        except Exception as e:
            results['errors'].append(f"Database search error: {str(e)}")
        
        return results
    
    def _search_local_database(self, from_email: str, subject_contains: str, 
                              body_contains: str, since_date: datetime,
                              limit: int, unread_only: bool, important_only: bool) -> List[Dict]:
        """Search emails in local database"""
        
        # Build WHERE clause dynamically
        where_conditions = []
        params = []
        
        # Base query
        query = """
            SELECT em.*, et.subject_last as thread_subject
            FROM email_messages em
            LEFT JOIN email_threads et ON em.thread_id = et.id
            WHERE em.direction = 'inbound'
        """
        
        # Add date filter
        if since_date:
            where_conditions.append("em.date_received >= %s")
            params.append(since_date)
        
        # Add sender filter - search both email and display name
        if from_email:
            if '@' in from_email:
                # Exact email search
                where_conditions.append("LOWER(em.from_email) LIKE %s")
                params.append(f"%{from_email}%")
            else:
                # Name search - check both display name and email
                where_conditions.append("(LOWER(em.from_display) LIKE %s OR LOWER(em.from_email) LIKE %s)")
                name_pattern = f"%{from_email}%"
                params.extend([name_pattern, name_pattern])
        
        # Add subject filter
        if subject_contains:
            where_conditions.append("(LOWER(em.subject) LIKE %s OR LOWER(et.subject_last) LIKE %s)")
            params.extend([f"%{subject_contains.lower()}%", f"%{subject_contains.lower()}%"])
        
        # Add body filter
        if body_contains:
            where_conditions.append("LOWER(em.snippet) LIKE %s")
            params.append(f"%{body_contains.lower()}%")
        
        # Add unread filter
        if unread_only:
            where_conditions.append("NOT ('read' = ANY(em.tags))")
        
        # Add important filter
        if important_only:
            where_conditions.append("'important' = ANY(em.tags)")
        
        # Combine conditions
        if where_conditions:
            query += " AND " + " AND ".join(where_conditions)
        
        # Add ordering and limit
        query += " ORDER BY em.date_received DESC LIMIT %s"
        params.append(limit)
        
        # Execute query
        from core.database import get_conn
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(query, params)
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
    
    def _format_email_for_display(self, email: Dict) -> Dict:
        """Format email data for display in chat"""
        return {
            'id': email.get('id'),
            'provider': email.get('provider'),
            'from_display': email.get('from_display', email.get('from_email')),
            'from_email': email.get('from_email'),
            'subject': email.get('subject') or email.get('thread_subject', 'No Subject'),
            'snippet': (email.get('snippet') or '')[:200] + ('...' if len(email.get('snippet', '')) > 200 else ''),
            'date_received': email.get('date_received').strftime('%Y-%m-%d %H:%M') if email.get('date_received') else 'Unknown',
            'is_unread': not any(tag == 'read' for tag in (email.get('tags') or [])),
            'is_important': any(tag == 'important' for tag in (email.get('tags') or []))
        }
    
    def get_email_detail(self, email_id: int) -> Optional[Dict]:
        """Get full details of a specific email"""
        return self.repo.get_email_detail(email_id)
    
    def parse_search_intent(self, user_message: str) -> Dict[str, Any]:
        """
        Parse user message to extract search intent and parameters
        
        Args:
            user_message: Natural language message from user
            
        Returns:
            Dictionary with extracted search parameters
        """
        message_lower = user_message.lower()
        params = {}
        
        # Look for sender information - improved to capture full names and email addresses
        from_patterns = [
            r'from\s+([^\s]+@[^\s,!?]+)',  # Email addresses - fixed to allow dots in domain
            r'sender\s+([^\s]+@[^\s,!?]+)',
            r'emails?\s+from\s+([^,\.!?]+?)(?:\s+(?:from|about|containing|yesterday|today|this|last|ago|gmail|outlook)|\s*$)',  # Names until next keyword
            r'messages?\s+from\s+([^,\.!?]+?)(?:\s+(?:from|about|containing|yesterday|today|this|last|ago|gmail|outlook)|\s*$)',
            r'find.*from\s+([^,\.!?]+?)(?:\s+(?:from|about|containing|yesterday|today|this|last|ago|gmail|outlook)|\s*$)',
            r'search.*from\s+([^,\.!?]+?)(?:\s+(?:from|about|containing|yesterday|today|this|last|ago|gmail|outlook)|\s*$)'
        ]
        
        for pattern in from_patterns:
            match = re.search(pattern, message_lower)
            if match:
                sender = match.group(1).strip()
                # Clean up the sender name/email
                if '@' in sender:
                    params['from_email'] = sender
                else:
                    # For names, we'll search in both display name and email
                    params['from_email'] = sender
                break
        
        # Look for subject keywords
        subject_patterns = [
            r'subject\s+["\']([^"\']+)["\']',
            r'subject\s+containing\s+["\']([^"\']+)["\']',
            r'subject\s+with\s+["\']([^"\']+)["\']',
            r'about\s+["\']([^"\']+)["\']',
            r'regarding\s+["\']([^"\']+)["\']',
            r'emails?\s+about\s+([^,\.!?]+?)(?:\s+(?:from|containing|yesterday|today|this|last|ago|gmail|outlook)|\s*$)',
            r'messages?\s+about\s+([^,\.!?]+?)(?:\s+(?:from|containing|yesterday|today|this|last|ago|gmail|outlook)|\s*$)'
        ]
        
        for pattern in subject_patterns:
            match = re.search(pattern, message_lower)
            if match:
                params['subject_contains'] = match.group(1).strip()
                break
        
        # Look for content keywords
        content_patterns = [
            r'containing\s+["\']([^"\']+)["\']',
            r'mentioning\s+["\']([^"\']+)["\']',
            r'with\s+text\s+["\']([^"\']+)["\']',
            r'emails?\s+containing\s+([^,\.!?]+?)(?:\s+(?:from|about|yesterday|today|this|last|ago|gmail|outlook)|\s*$)'
        ]
        
        for pattern in content_patterns:
            match = re.search(pattern, message_lower)
            if match:
                params['body_contains'] = match.group(1).strip()
                break
        
        # Look for time constraints
        if 'today' in message_lower:
            params['days_back'] = 1
        elif 'yesterday' in message_lower:
            params['days_back'] = 2
        elif 'this week' in message_lower or 'past week' in message_lower:
            params['days_back'] = 7
        elif 'this month' in message_lower or 'past month' in message_lower:
            params['days_back'] = 30
        elif 'last month' in message_lower:
            params['days_back'] = 60
        else:
            # Default to last 30 days if no time specified
            params['days_back'] = 30
        
        # Look for specific days
        days_match = re.search(r'(\d+)\s+days?\s+ago', message_lower)
        if days_match:
            params['days_back'] = int(days_match.group(1))
        
        # Look for provider preference
        if 'only gmail' in message_lower or 'just gmail' in message_lower:
            params['provider'] = 'gmail'
        elif 'only outlook' in message_lower or 'just outlook' in message_lower:
            params['provider'] = 'outlook'
        else:
            # Default to both providers
            params['provider'] = 'both'
        
        # Look for unread/important flags
        if 'unread' in message_lower:
            params['unread_only'] = True
        if 'important' in message_lower:
            params['important_only'] = True
        
        # Look for number of results
        limit_match = re.search(r'(\d+)\s+emails?', message_lower)
        if limit_match:
            params['limit'] = min(int(limit_match.group(1)), 20)  # Cap at 20
        else:
            params['limit'] = 10  # Default limit
        
        return params
    
    def format_search_results_for_llm(self, results: Dict[str, Any]) -> str:
        """Format search results for LLM to understand and present to user"""
        
        if results['total_found'] == 0:
            return ("No emails found matching your criteria. "
                   "You might want to try:\n"
                   "- Expanding the time range\n"
                   "- Using different keywords\n"
                   "- Checking spelling\n"
                   "- Being more specific about sender or subject")
        
        # Use the same format as the digest
        output_lines = []
        
        # Provider icons
        PROVIDER_ICON = {
            "gmail": "✉️🟥",
            "outlook": "✉️🟦",
        }
        
        for i, email in enumerate(results['emails'], 1):
            # Build status badges
            badges = ""
            if email['is_unread']:
                badges += "📧 "
            if email['is_important']:
                badges += "⭐ "
            
            # Get provider icon
            provider_icon = PROVIDER_ICON.get(email['provider'], "✉️")
            
            # Format sender
            sender = email['from_display'] or email['from_email'] or "(unknown)"
            
            # Format subject
            subject = email['subject'] or "(no subject)"
            
            # Format snippet (truncate if too long)
            snippet = email['snippet'] or ""
            if len(snippet) > 140:
                snippet = snippet[:137] + "…"
            
            # Build the email line in digest format
            email_line = f"{badges}{provider_icon} *{sender}*\n_{subject}_\n{snippet}"
            
            # Add email ID at the end for reference
            email_line += f"\n`ID: {email['id']}`"
            
            output_lines.append(email_line)
        
        output = "\n\n".join(output_lines)
        
        if results['total_found'] == results.get('limit', 10):
            output += "\n\n💡 This shows the maximum number of results. Use 'more specific' terms to narrow down or ask for 'more emails' to increase the limit."
        
        return output
