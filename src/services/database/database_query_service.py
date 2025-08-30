"""
Database Query Service for LLM
Provides safe database access for the LLM to answer questions about emails and data
"""
import os
import sys
import pathlib
from typing import List, Dict, Any, Optional, Tuple
import json
import re
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from core.database import get_conn


class DatabaseQueryService:
    """Service for safe database queries that the LLM can use"""
    
    def __init__(self):
        # Define safe, pre-approved queries that the LLM can use
        self.safe_queries = {
            'count_emails': {
                'description': 'Count total emails, optionally filtered by provider, date range, or read status',
                'sql': '''
                    SELECT COUNT(*) as total_emails
                    FROM email_messages 
                    WHERE direction = 'inbound'
                    {where_conditions}
                ''',
                'params': ['provider', 'days_back', 'unread_only', 'from_date', 'to_date']
            },
            
            'recent_emails': {
                'description': 'Get recent emails with sender, subject, date info',
                'sql': '''
                    SELECT id, provider, from_display, from_email, subject, snippet, 
                           received_at, tags, direction
                    FROM email_messages 
                    WHERE direction = 'inbound'
                    {where_conditions}
                    ORDER BY received_at DESC 
                    LIMIT {limit}
                ''',
                'params': ['provider', 'days_back', 'unread_only', 'limit', 'from_email', 'subject_contains']
            },
            
            'email_stats_by_provider': {
                'description': 'Get email counts grouped by provider (Gmail, Outlook)',
                'sql': '''
                    SELECT provider, 
                           COUNT(*) as total_emails,
                           COUNT(*) FILTER (WHERE NOT ('read' = ANY(tags))) as unread_count,
                           COUNT(*) FILTER (WHERE 'important' = ANY(tags)) as important_count,
                           MAX(received_at) as latest_email
                    FROM email_messages 
                    WHERE direction = 'inbound'
                    {where_conditions}
                    GROUP BY provider
                    ORDER BY provider
                ''',
                'params': ['days_back']
            },
            
            'email_stats_by_sender': {
                'description': 'Get email counts by top senders',
                'sql': '''
                    SELECT from_email, from_display,
                           COUNT(*) as email_count,
                           MAX(received_at) as latest_email,
                           COUNT(*) FILTER (WHERE NOT ('read' = ANY(tags))) as unread_count
                    FROM email_messages 
                    WHERE direction = 'inbound' AND from_email IS NOT NULL
                    {where_conditions}
                    GROUP BY from_email, from_display
                    ORDER BY email_count DESC
                    LIMIT {limit}
                ''',
                'params': ['days_back', 'limit', 'provider']
            },
            
            'email_by_date': {
                'description': 'Get email counts by date (daily breakdown)',
                'sql': '''
                    SELECT DATE(received_at) as email_date,
                           COUNT(*) as email_count,
                           COUNT(*) FILTER (WHERE NOT ('read' = ANY(tags))) as unread_count,
                           COUNT(DISTINCT from_email) as unique_senders
                    FROM email_messages 
                    WHERE direction = 'inbound' AND received_at IS NOT NULL
                    {where_conditions}
                    GROUP BY DATE(received_at)
                    ORDER BY email_date DESC
                    LIMIT {limit}
                ''',
                'params': ['days_back', 'limit', 'provider']
            },
            
            'search_emails': {
                'description': 'Search emails by sender, subject, or content',
                'sql': '''
                    SELECT id, provider, from_display, from_email, subject, snippet,
                           received_at, tags
                    FROM email_messages 
                    WHERE direction = 'inbound'
                    {where_conditions}
                    ORDER BY received_at DESC
                    LIMIT {limit}
                ''',
                'params': ['from_email', 'subject_contains', 'body_contains', 'days_back', 'limit', 'provider']
            },
            
            'thread_info': {
                'description': 'Get information about email threads',
                'sql': '''
                    SELECT et.id, et.provider, et.provider_thread_id, et.subject_last,
                           COUNT(em.id) as message_count,
                           MAX(em.received_at) as latest_message,
                           MIN(em.received_at) as first_message
                    FROM email_threads et
                    LEFT JOIN email_messages em ON em.thread_id = et.id
                    {where_conditions}
                    GROUP BY et.id, et.provider, et.provider_thread_id, et.subject_last
                    ORDER BY latest_message DESC
                    LIMIT {limit}
                ''',
                'params': ['provider', 'days_back', 'limit']
            },
            
            'unread_summary': {
                'description': 'Get summary of unread emails',
                'sql': '''
                    SELECT provider,
                           COUNT(*) as unread_count,
                           COUNT(DISTINCT from_email) as unique_senders,
                           MAX(received_at) as latest_unread
                    FROM email_messages 
                    WHERE direction = 'inbound' 
                    AND NOT ('read' = ANY(tags))
                    {where_conditions}
                    GROUP BY provider
                    ORDER BY unread_count DESC
                ''',
                'params': ['days_back']
            }
        }
    
    def execute_query(self, query_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a safe, pre-defined query with parameters
        
        Args:
            query_name: Name of the query from safe_queries
            parameters: Dictionary of parameters for the query
            
        Returns:
            Dictionary with results and metadata
        """
        if query_name not in self.safe_queries:
            return {
                'error': f"Query '{query_name}' not found",
                'available_queries': list(self.safe_queries.keys())
            }
        
        query_def = self.safe_queries[query_name]
        parameters = parameters or {}
        
        try:
            # Build the WHERE conditions and parameters
            where_conditions, query_params = self._build_where_conditions(parameters)
            
            # Format the SQL with WHERE conditions
            sql = query_def['sql'].format(
                where_conditions=where_conditions,
                limit=parameters.get('limit', 20)
            )
            
            # Execute the query
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute(sql, query_params)
                
                # Get column names
                columns = [desc[0] for desc in cur.description] if cur.description else []
                
                # Fetch results
                rows = cur.fetchall()
                
                # Convert to list of dictionaries
                results = []
                for row in rows:
                    row_dict = {}
                    for i, value in enumerate(row):
                        # Convert datetime objects to strings for JSON serialization
                        if isinstance(value, datetime):
                            row_dict[columns[i]] = value.isoformat()
                        elif isinstance(value, list):
                            row_dict[columns[i]] = value
                        else:
                            row_dict[columns[i]] = value
                    results.append(row_dict)
                
                return {
                    'query_name': query_name,
                    'description': query_def['description'],
                    'results': results,
                    'total_rows': len(results),
                    'parameters_used': parameters,
                    'sql_executed': sql
                }
                
        except Exception as e:
            return {
                'error': f"Database query failed: {str(e)}",
                'query_name': query_name,
                'parameters': parameters
            }
    
    def _build_where_conditions(self, parameters: Dict[str, Any]) -> Tuple[str, List[Any]]:
        """Build WHERE conditions and parameters for SQL query"""
        conditions = []
        params = []
        
        # Provider filter
        if parameters.get('provider') and parameters['provider'] != 'both':
            conditions.append("provider = %s")
            params.append(parameters['provider'])
        
        # Date range filters
        if parameters.get('days_back'):
            since_date = datetime.now() - timedelta(days=int(parameters['days_back']))
            conditions.append("received_at >= %s")
            params.append(since_date)
        
        if parameters.get('from_date'):
            conditions.append("received_at >= %s")
            params.append(parameters['from_date'])
            
        if parameters.get('to_date'):
            conditions.append("received_at <= %s")
            params.append(parameters['to_date'])
        
        # Sender filter
        if parameters.get('from_email'):
            from_email = parameters['from_email'].lower()
            if '@' in from_email:
                conditions.append("LOWER(from_email) LIKE %s")
                params.append(f"%{from_email}%")
            else:
                conditions.append("(LOWER(from_display) LIKE %s OR LOWER(from_email) LIKE %s)")
                params.extend([f"%{from_email}%", f"%{from_email}%"])
        
        # Subject filter
        if parameters.get('subject_contains'):
            conditions.append("LOWER(subject) LIKE %s")
            params.append(f"%{parameters['subject_contains'].lower()}%")
        
        # Body/content filter
        if parameters.get('body_contains'):
            conditions.append("(LOWER(snippet) LIKE %s OR LOWER(body_plain) LIKE %s)")
            content = parameters['body_contains'].lower()
            params.extend([f"%{content}%", f"%{content}%"])
        
        # Unread filter
        if parameters.get('unread_only'):
            conditions.append("NOT ('read' = ANY(tags))")
        
        # Important filter
        if parameters.get('important_only'):
            conditions.append("'important' = ANY(tags)")
        
        # Build final WHERE clause
        if conditions:
            where_clause = "AND " + " AND ".join(conditions)
        else:
            where_clause = ""
        
        return where_clause, params
    
    def get_available_queries(self) -> Dict[str, str]:
        """Get list of available queries with descriptions"""
        return {name: info['description'] for name, info in self.safe_queries.items()}
    
    def natural_language_to_query(self, user_request: str) -> Tuple[str, Dict[str, Any]]:
        """
        Convert natural language request to query name and parameters
        
        Args:
            user_request: Natural language description of what user wants
            
        Returns:
            Tuple of (query_name, parameters)
        """
        request_lower = user_request.lower()
        
        # Pattern matching for different types of requests
        if any(word in request_lower for word in ['count', 'how many', 'total']):
            if 'provider' in request_lower or 'gmail' in request_lower or 'outlook' in request_lower:
                return 'email_stats_by_provider', self._extract_parameters(user_request)
            else:
                return 'count_emails', self._extract_parameters(user_request)
        
        elif any(word in request_lower for word in ['recent', 'latest', 'new']):
            return 'recent_emails', self._extract_parameters(user_request)
        
        elif any(word in request_lower for word in ['search', 'find', 'look for']):
            return 'search_emails', self._extract_parameters(user_request)
        
        elif any(word in request_lower for word in ['sender', 'from', 'who sent']):
            return 'email_stats_by_sender', self._extract_parameters(user_request)
        
        elif any(word in request_lower for word in ['unread', 'not read']):
            return 'unread_summary', self._extract_parameters(user_request)
        
        elif any(word in request_lower for word in ['thread', 'conversation']):
            return 'thread_info', self._extract_parameters(user_request)
        
        elif any(word in request_lower for word in ['daily', 'by date', 'per day']):
            return 'email_by_date', self._extract_parameters(user_request)
        
        else:
            # Default to recent emails
            return 'recent_emails', self._extract_parameters(user_request)
    
    def _extract_parameters(self, user_request: str) -> Dict[str, Any]:
        """Extract parameters from natural language request"""
        params = {}
        request_lower = user_request.lower()
        
        # Extract provider
        if 'gmail' in request_lower:
            params['provider'] = 'gmail'
        elif 'outlook' in request_lower:
            params['provider'] = 'outlook'
        
        # Extract time constraints
        if 'today' in request_lower:
            params['days_back'] = 1
        elif 'yesterday' in request_lower:
            params['days_back'] = 2
        elif 'this week' in request_lower or 'past week' in request_lower:
            params['days_back'] = 7
        elif 'this month' in request_lower or 'past month' in request_lower:
            params['days_back'] = 30
        
        # Extract specific days
        days_match = re.search(r'(\d+)\s+days?\s+ago', request_lower)
        if days_match:
            params['days_back'] = int(days_match.group(1))
        
        # Extract sender
        from_patterns = [
            r'from\s+([^\s@]+@[^\s,\.!?]+)',
            r'from\s+([^,\.!?]+?)(?:\s+(?:yesterday|today|this|last|ago|gmail|outlook)|\s*$)',
            r'sender\s+([^,\.!?]+?)(?:\s+(?:yesterday|today|this|last|ago|gmail|outlook)|\s*$)'
        ]
        
        for pattern in from_patterns:
            match = re.search(pattern, request_lower)
            if match:
                params['from_email'] = match.group(1).strip()
                break
        
        # Extract subject
        subject_patterns = [
            r'subject\s+["\']([^"\']+)["\']',
            r'about\s+["\']([^"\']+)["\']',
            r'subject\s+containing\s+([^,\.!?]+?)(?:\s+(?:from|yesterday|today)|\s*$)'
        ]
        
        for pattern in subject_patterns:
            match = re.search(pattern, request_lower)
            if match:
                params['subject_contains'] = match.group(1).strip()
                break
        
        # Extract flags
        if 'unread' in request_lower:
            params['unread_only'] = True
        if 'important' in request_lower:
            params['important_only'] = True
        
        # Extract limit
        limit_match = re.search(r'(\d+)\s+(?:emails?|messages?|results?)', request_lower)
        if limit_match:
            params['limit'] = min(int(limit_match.group(1)), 50)  # Cap at 50
        else:
            params['limit'] = 10  # Default
        
        return params
    
    def format_results_for_llm(self, query_result: Dict[str, Any]) -> str:
        """Format query results for LLM to understand and present"""
        
        if 'error' in query_result:
            return f"❌ Database Error: {query_result['error']}"
        
        results = query_result['results']
        query_name = query_result['query_name']
        total_rows = query_result['total_rows']
        
        if total_rows == 0:
            return f"📊 No results found for query: {query_result['description']}"
        
        output = f"📊 **{query_result['description']}**\n"
        output += f"Found {total_rows} result(s):\n\n"
        
        # Format based on query type
        if query_name == 'count_emails':
            result = results[0]
            output += f"Total emails: **{result['total_emails']}**"
        
        elif query_name == 'email_stats_by_provider':
            for result in results:
                provider_icon = "🟥" if result['provider'] == 'gmail' else "🟦"
                output += f"{provider_icon} **{result['provider'].upper()}:**\n"
                output += f"  - Total: {result['total_emails']}\n"
                output += f"  - Unread: {result['unread_count']}\n"
                output += f"  - Important: {result['important_count']}\n"
                if result['latest_email']:
                    output += f"  - Latest: {result['latest_email']}\n"
                output += "\n"
        
        elif query_name in ['recent_emails', 'search_emails']:
            for i, result in enumerate(results, 1):
                provider_icon = "✉️🟥" if result['provider'] == 'gmail' else "✉️🟦"
                
                badges = ""
                if result.get('tags'):
                    if 'read' not in result['tags']:
                        badges += "📧 "
                    if 'important' in result['tags']:
                        badges += "⭐ "
                
                sender = result['from_display'] or result['from_email'] or 'Unknown'
                subject = result['subject'] or '(no subject)'
                snippet = (result['snippet'] or '')[:100]
                if len(result['snippet'] or '') > 100:
                    snippet += "..."
                
                output += f"{badges}{provider_icon} **{sender}**\n"
                output += f"_{subject}_\n"
                output += f"{snippet}\n"
                output += f"`ID: {result['id']} | {result['received_at']}`\n\n"
        
        elif query_name == 'email_stats_by_sender':
            for i, result in enumerate(results, 1):
                sender = result['from_display'] or result['from_email']
                output += f"{i}. **{sender}**\n"
                output += f"   - Total emails: {result['email_count']}\n"
                output += f"   - Unread: {result['unread_count']}\n"
                output += f"   - Latest: {result['latest_email']}\n\n"
        
        elif query_name == 'email_by_date':
            for result in results:
                output += f"📅 **{result['email_date']}**: {result['email_count']} emails"
                if result['unread_count'] > 0:
                    output += f" ({result['unread_count']} unread)"
                output += f" from {result['unique_senders']} senders\n"
        
        elif query_name == 'unread_summary':
            for result in results:
                provider_icon = "🟥" if result['provider'] == 'gmail' else "🟦"
                output += f"{provider_icon} **{result['provider'].upper()}**: {result['unread_count']} unread emails from {result['unique_senders']} senders\n"
        
        else:
            # Generic formatting for other query types
            for i, result in enumerate(results[:10], 1):  # Limit to 10 for readability
                output += f"{i}. "
                for key, value in result.items():
                    if key != 'id':
                        output += f"{key}: {value} | "
                output = output.rstrip(" | ") + "\n"
        
        return output.strip()
