"""
LLM Client for email summarization and conversational AI using llama.cpp server
Now with intelligent tool-based system where LLM decides what actions to take
"""
import os
import requests
import json
from typing import Optional, List, Dict
import datetime
import re
from pathlib import Path

class LLMClient:
    def __init__(self):
        self.base_url = os.getenv('LLM_BASE_URL', 'http://192.168.0.83:8085')
        self.timeout = int(os.getenv('LLM_TIMEOUT', '30'))
        
        # Persistent conversation memory setup
        self.memory_dir = Path(os.getenv('LLM_MEMORY_DIR', '/home/mentorius/AI_Services/PA_V2/data/llm_memory'))
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Files for persistent memory
        self.conversation_file = self.memory_dir / "conversation.jsonl"
        self.long_term_memory_file = self.memory_dir / "long_term_memory.json"
        
        # Context window settings
        self.max_context_tokens = int(os.getenv('LLM_MAX_CONTEXT', '32768'))
        self.reserve_tokens = int(os.getenv('LLM_RESERVE_TOKENS', '1536'))
        
    def summarize_email(self, subject: str, body: str, max_lines: int = 2) -> str:
        """Summarize email content to specified number of lines using llama.cpp"""
        try:
            clean_body = self._clean_email_body(body)
            prompt = f"Summarize this email in {max_lines} lines: Subject: {subject} Content: {clean_body[:500]}"
            
            response = requests.post(
                f"{self.base_url}/completion",
                json={"prompt": prompt, "max_tokens": 100, "temperature": 0.3},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                summary = result.get('content', '').strip()
                if summary:
                    return summary
            
        except Exception as e:
            print(f"⚠️ LLM error: {e}")
        
        return self._naive_summarize(subject, body, max_lines)
    
    def chat(self, user_message: str, user_id: str = "default", include_context: bool = True) -> str:
        """Have a conversation with the LLM, giving it access to email tools and database queries."""
        try:
            # Add user message to persistent conversation
            self._append_message("user", user_message, user_id)
            
            # Build conversation with memory and available tools
            conversation_messages = self._build_conversation_with_memory_and_tools(user_id, include_context)
            
            # Send to LLM with tool descriptions
            response = self._send_chat_request_with_tools(conversation_messages, user_message)
            
            if response:
                # Store assistant response
                self._append_message("assistant", response, user_id)
                return response
            
            return "I'm sorry, I couldn't process your request right now."
            
        except Exception as e:
            print(f"⚠️ LLM chat error: {e}")
            return "I'm having trouble connecting right now. Please try again."
    
    def _append_message(self, role: str, content: str, user_id: str = "default"):
        """Append a message to the persistent conversation log"""
        message = {
            "timestamp": datetime.datetime.now().isoformat(),
            "user_id": user_id,
            "role": role,
            "content": content
        }
        
        with self.conversation_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(message, ensure_ascii=False) + "\n")
    
    def _load_conversation_history(self, user_id: str = "default", max_items: int = 1000) -> List[Dict]:
        """Load conversation history for a specific user"""
        messages = []
        if self.conversation_file.exists():
            with self.conversation_file.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        msg = json.loads(line.strip())
                        if msg.get("user_id") == user_id:
                            messages.append(msg)
                    except json.JSONDecodeError:
                        continue
        return messages[-max_items:]
    
    def _load_long_term_memory(self, user_id: str = "default") -> Dict:
        """Load long-term memory for a user"""
        if self.long_term_memory_file.exists():
            try:
                with self.long_term_memory_file.open("r", encoding="utf-8") as f:
                    all_memory = json.load(f)
                    return all_memory.get(user_id, {"summary": "", "facts": [], "email_context": {}})
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return {"summary": "", "facts": [], "email_context": {}}
    
    def _save_long_term_memory(self, user_id: str, summary: str, facts: List[str], email_context: Dict = None):
        """Save long-term memory for a user"""
        all_memory = {}
        if self.long_term_memory_file.exists():
            try:
                with self.long_term_memory_file.open("r", encoding="utf-8") as f:
                    all_memory = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        all_memory[user_id] = {
            "summary": summary,
            "facts": facts,
            "email_context": email_context or {},
            "last_updated": datetime.datetime.now().isoformat()
        }
        
        with self.long_term_memory_file.open("w", encoding="utf-8") as f:
            json.dump(all_memory, f, ensure_ascii=False, indent=2)
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars ≈ 1 token for most models)"""
        return len(text) // 4
    
    def _build_conversation_with_memory_and_tools(self, user_id: str, include_email_context: bool = True) -> List[Dict]:
        """Build conversation messages with memory management and available tools"""
        
        # Load conversation history and long-term memory
        history = self._load_conversation_history(user_id, max_items=500)
        long_term = self._load_long_term_memory(user_id)
        
        # Build system message with memory, email context, and available tools
        system_content = """You are a helpful AI assistant for email management and general conversation. You have access to several tools to help users:

AVAILABLE TOOLS:
1. search_local_emails(from_email, subject_contains, body_contains, days_back, provider, unread_only) - Search emails in local database
2. search_provider_emails(provider, query, days_back) - Search directly in Gmail/Outlook using their APIs  
3. get_email_details(email_id) - Get full details of a specific email
4. query_database(query_type, parameters) - Get email statistics and analytics
5. general_conversation() - For non-email related conversations

EMAIL SEARCH OPTIONS:
- Local Database Search: Fast, works on already synced emails, supports complex filtering
- Provider Direct Search: Real-time search directly in Gmail/Outlook, may find newer emails

DATABASE QUERIES AVAILABLE:
- email_count_by_timeframe: Count emails in time periods
- unread_count_by_provider: Count unread emails per provider  
- top_senders: Most frequent email senders
- emails_by_provider: Email distribution across providers
- recent_emails_summary: Recent email overview
- search_emails_advanced: Advanced email search with filters
- daily_email_stats: Daily email statistics
- important_emails_count: Count of important/starred emails

INSTRUCTIONS:
- When users ask about emails, decide which tool is most appropriate
- For specific searches, use search_local_emails first (faster), then search_provider_emails if needed
- For statistics/analytics, use query_database
- For general conversation, just respond normally
- Always explain what you're doing and why you chose that approach"""
        
        # Add long-term memory
        if long_term.get("summary"):
            system_content += f"\n\nConversation Summary: {long_term['summary']}"
        
        if long_term.get("facts"):
            system_content += "\n\nKey Facts I Remember:\n- " + "\n- ".join(long_term["facts"])
        
        # Add email context if requested
        if include_email_context:
            email_context = self._build_email_context()
            if email_context:
                system_content += f"\n\nRecent Email Context:\n{email_context}"
        
        # Start with system message
        messages = [{"role": "system", "content": system_content}]
        
        # Add conversation history, managing tokens
        budget = self.max_context_tokens - self.reserve_tokens
        current_tokens = self._estimate_tokens(system_content)
        
        # Add messages from most recent backwards until we hit budget
        recent_messages = []
        for msg in reversed(history):
            msg_content = f"{msg['role']}: {msg['content']}"
            msg_tokens = self._estimate_tokens(msg_content)
            
            if current_tokens + msg_tokens > budget:
                break
                
            recent_messages.append({"role": msg["role"], "content": msg["content"]})
            current_tokens += msg_tokens
        
        # Add messages in correct order
        messages.extend(reversed(recent_messages))
        
        # If we dropped a lot of history, trigger summarization
        if len(recent_messages) < len(history) // 3 and len(history) > 20:
            self._maybe_update_summary(user_id, history)
        
        return messages
    
    def _send_chat_request_with_tools(self, messages: List[Dict], user_message: str) -> Optional[str]:
        """Send chat request to llama.cpp server and handle tool usage"""
        try:
            # Format messages for the completion endpoint
            prompt = ""
            for msg in messages:
                if msg["role"] == "system":
                    prompt += f"System: {msg['content']}\n\n"
                elif msg["role"] == "user":
                    prompt += f"User: {msg['content']}\n"
                elif msg["role"] == "assistant":
                    prompt += f"Assistant: {msg['content']}\n"
            
            prompt += "Assistant:"
            
            response = requests.post(
                f"{self.base_url}/completion",
                json={
                    "prompt": prompt,
                    "max_tokens": 500,
                    "temperature": 0.7,
                    "stop": ["User:", "Human:", "System:"],
                    "stream": False
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('content', '').strip()
                
                # Check if the LLM wants to use a tool
                tool_usage = self._detect_and_execute_tools(answer, user_message)
                if tool_usage:
                    return tool_usage
                
                return answer
                
        except Exception as e:
            print(f"⚠️ Error sending chat request: {e}")
        
        return None
    
    def _detect_and_execute_tools(self, llm_response: str, user_message: str) -> Optional[str]:
        """Detect if LLM wants to use tools and execute them"""
        
        # Look for tool usage patterns in LLM response
        tool_patterns = {
            'search_local_emails': r'search_local_emails\(([^)]+)\)',
            'search_provider_emails': r'search_provider_emails\(([^)]+)\)',
            'get_email_details': r'get_email_details\(([^)]+)\)',
            'query_database': r'query_database\(([^)]+)\)'
        }
        
        for tool_name, pattern in tool_patterns.items():
            match = re.search(pattern, llm_response, re.IGNORECASE)
            if match:
                params_str = match.group(1)
                return self._execute_tool(tool_name, params_str, user_message)
        
        # If no explicit tool usage, check if we should suggest tools based on content
        if any(keyword in llm_response.lower() for keyword in ['search', 'find', 'email', 'database', 'query']):
            # LLM mentioned email/search concepts - try to infer what they want
            return self._smart_tool_inference(llm_response, user_message)
        
        return None
    
    def _execute_tool(self, tool_name: str, params_str: str, user_message: str) -> str:
        """Execute a specific tool with parameters"""
        try:
            if tool_name == 'search_local_emails':
                return self._tool_search_local_emails(user_message)
            elif tool_name == 'search_provider_emails':
                return self._tool_search_provider_emails(user_message)
            elif tool_name == 'get_email_details':
                # Extract email ID from params or user message
                id_match = re.search(r'\d+', params_str + user_message)
                if id_match:
                    return self._get_email_details(int(id_match.group()))
                return "Please specify an email ID number."
            elif tool_name == 'query_database':
                return self._tool_query_database(user_message)
                
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"
        
        return f"Tool {tool_name} not implemented yet."
    
    def _smart_tool_inference(self, llm_response: str, user_message: str) -> Optional[str]:
        """Intelligently infer what tool the user wants based on their message"""
        user_lower = user_message.lower()
        
        # Database query patterns
        if any(word in user_lower for word in ['how many', 'count', 'statistics', 'stats', 'total', 'summary']):
            return self._tool_query_database(user_message)
        
        # Email search patterns - improved to catch more variations
        search_triggers = [
            'find', 'search', 'show', 'get', 'from', 'about',
            'last email', 'latest email', 'recent email', 'new email',
            'email from', 'message from', 'mail from'
        ]
        
        if any(trigger in user_lower for trigger in search_triggers):
            # Check for email ID pattern first
            id_match = re.search(r'(?:email|message|id)\s*(?:#|id|number)?\s*(\d+)', user_lower)
            if id_match:
                return self._get_email_details(int(id_match.group(1)))
            
            # Check if it's asking for "last" or "latest" email - modify search for recent results
            if any(word in user_lower for word in ['last', 'latest', 'recent', 'new']):
                return self._tool_search_recent_emails(user_message)
            
            # Default to local search first (faster)
            return self._tool_search_local_emails(user_message)
        
        return None
    
    def _tool_search_local_emails(self, user_message: str) -> str:
        """Tool: Search emails in local database"""
        try:
            # Import here to avoid circular imports
            import sys
            import pathlib
            sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
            from services.email.email_search_service import EmailSearchService
            
            search_service = EmailSearchService()
            
            # Parse the user's search intent
            search_params = search_service.parse_search_intent(user_message)
            
            if not search_params:
                return "I need more specific search criteria. Please tell me who sent the email, what it's about, or when it was sent."
            
            # Perform the search
            results = search_service.search_emails(search_params)
            
            if results['total_found'] == 0:
                # Create a user-friendly "no results" message for Telegram
                response = "🔍 **No emails found**\n\n"
                
                if search_params.get('from_email'):
                    response += f"Looking for emails from: **{search_params['from_email']}**\n"
                if search_params.get('subject_contains'):
                    response += f"Subject containing: **{search_params['subject_contains']}**\n"
                if search_params.get('days_back'):
                    response += f"Time range: **Last {search_params['days_back']} days**\n"
                if search_params.get('provider') != 'both':
                    response += f"Provider: **{search_params['provider'].upper()}**\n"
                
                response += "\n💡 **Try:**\n"
                response += "• Check the email address spelling\n"
                response += "• Try broader keywords\n"
                response += "• Extend time range: 'from last month'\n"
                response += "• Search both Gmail and Outlook accounts\n"
                
                return response
            
            # Format results for display - make it Telegram-friendly
            formatted_results = search_service.format_search_results_for_llm(results)
            
            # Add a concise summary line
            response = f"� **Found {results['total_found']} email{'s' if results['total_found'] != 1 else ''}**\n\n"
            response += formatted_results
            response += f"\n\n💡 Ask for **'email details ID'** to see full content"
            
            return response
            
        except Exception as e:
            print(f"⚠️ Local email search error: {e}")
            return f"❌ Error searching local emails: {str(e)}"
    
    def _tool_search_recent_emails(self, user_message: str) -> str:
        """Tool: Search for recent emails with special handling for 'last' and 'latest' queries"""
        try:
            # Import here to avoid circular imports
            import sys
            import pathlib
            sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
            from services.email.email_search_service import EmailSearchService
            
            search_service = EmailSearchService()
            
            # Parse the user's search intent
            search_params = search_service.parse_search_intent(user_message)
            
            # For "last" queries, we want the most recent result only
            search_params['limit'] = 1
            search_params['days_back'] = 30  # Look in last 30 days
            
            if not search_params.get('from_email') and not search_params.get('subject_contains'):
                return "I need more details. Please specify who sent the email or what it's about.\n\nExample: 'last email from john@company.com'"
            
            # Perform the search
            results = search_service.search_emails(search_params)
            
            if results['total_found'] == 0:
                # Create a user-friendly "no results" message for Telegram
                response = "🔍 **No recent emails found**\n\n"
                
                if search_params.get('from_email'):
                    response += f"Looking for emails from: **{search_params['from_email']}**\n"
                
                response += "\n💡 **Try:**\n"
                response += "• Check the email address spelling\n"
                response += "• Make sure the email is in your synchronized accounts\n"
                response += "• Try searching for a longer time period\n"
                
                return response
            
            # Get the single most recent email
            email = results['emails'][0]
            
            # Format as a single email result
            response = "📧 **Most Recent Email**\n\n"
            response += f"**From:** {email.get('from_display', email.get('from_email', 'Unknown'))}\n"
            response += f"**Subject:** {email.get('subject', 'No Subject')}\n"
            response += f"**Date:** {email.get('date_received', 'Unknown')}\n"
            response += f"**Provider:** {email.get('provider', 'Unknown').upper()}\n\n"
            
            # Add snippet if available
            snippet = email.get('snippet', '')
            if snippet:
                response += f"**Preview:** {snippet[:150]}{'...' if len(snippet) > 150 else ''}\n\n"
            
            response += f"💡 Ask for **'email details {email.get('id')}'** to see full content"
            
            return response
            
        except Exception as e:
            print(f"⚠️ Recent email search error: {e}")
            return f"❌ Error searching recent emails: {str(e)}"
    
    def _tool_search_provider_emails(self, user_message: str) -> str:
        """Tool: Search directly in Gmail/Outlook using their APIs"""
        try:
            # Import here to avoid circular imports
            import sys
            import pathlib
            sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
            from services.email.email_search_service import EmailSearchService
            
            search_service = EmailSearchService()
            
            # Parse the user's search intent
            search_params = search_service.parse_search_intent(user_message)
            
            if not search_params:
                return "I need more specific search criteria for provider search. Please specify the provider (Gmail/Outlook) and search terms."
            
            # Determine provider
            provider = search_params.get('provider', 'both')
            if provider == 'both':
                return "For provider direct search, please specify either Gmail or Outlook. Example: 'search Gmail for emails from John'"
            
            # TODO: Implement direct provider search
            # This would use Gmail/Outlook APIs to search in real-time
            return f"🚧 Direct {provider.upper()} search not yet implemented.\n\n**Searched for:** {search_params}\n\n**Alternative:** Try local database search first with search_local_emails()"
            
        except Exception as e:
            print(f"⚠️ Provider email search error: {e}")
            return f"❌ Error searching provider emails: {str(e)}"
    
    def _tool_query_database(self, user_message: str) -> str:
        """Tool: Query database for email statistics and analytics"""
        try:
            # Import here to avoid circular imports
            import sys
            import pathlib
            sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
            from services.database.database_query_service import DatabaseQueryService
            
            query_service = DatabaseQueryService()
            
            # Parse the user request and execute query
            query_name, parameters = query_service.natural_language_to_query(user_message)
            
            if query_name:
                results = query_service.execute_query(query_name, parameters)
                formatted_result = query_service.format_results_for_llm(results)
                result = formatted_result
            else:
                result = None
            
            if result:
                return f"📊 **Database Query Results:**\n\n{result}\n\n💡 You can ask for more specific statistics or different time ranges!"
            else:
                return "❌ Could not understand your database query. Try asking about:\n- Email counts\n- Top senders\n- Unread emails\n- Daily statistics\n- Provider breakdown"
            
        except Exception as e:
            print(f"⚠️ Database query error: {e}")
            return f"❌ Error querying database: {str(e)}"
    
    def _get_email_details(self, email_id: int) -> str:
        """Get full details of a specific email by ID"""
        try:
            # Import here to avoid circular imports
            import sys
            import pathlib
            sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
            from services.email.email_search_service import EmailSearchService
            
            search_service = EmailSearchService()
            email = search_service.get_email_detail(email_id)
            
            if not email:
                return f"❌ Email with ID {email_id} not found. Please check the ID and try again."
            
            # Format email details - Telegram-friendly
            response = f"📧 **Email Details**\n\n"
            response += f"**From:** {email.get('from_display', email.get('from_email', 'Unknown'))}\n"
            response += f"**Subject:** {email.get('subject', 'No Subject')}\n"
            
            to_emails = email.get('to_emails', [])
            if to_emails:
                response += f"**To:** {', '.join(to_emails[:3])}{'...' if len(to_emails) > 3 else ''}\n"
            
            if email.get('cc_emails'):
                cc_emails = email.get('cc_emails')
                response += f"**CC:** {', '.join(cc_emails[:2])}{'...' if len(cc_emails) > 2 else ''}\n"
            
            response += f"**Date:** {email.get('date_received', 'Unknown')}\n"
            response += f"**Provider:** {email.get('provider', 'Unknown').upper()}\n"
            
            # Add status tags
            tags = email.get('tags', [])
            if tags:
                status_tags = []
                if 'unread' not in tags:
                    status_tags.append("✅ READ")
                else:
                    status_tags.append("📧 UNREAD")
                if 'important' in tags:
                    status_tags.append("⭐ IMPORTANT")
                if 'starred' in tags:
                    status_tags.append("⭐ STARRED")
                if status_tags:
                    response += f"**Status:** {' | '.join(status_tags)}\n"
            
            response += "\n**Content:**\n"
            body = email.get('body_text', email.get('snippet', 'No content available'))
            if body:
                # Format content properly for Telegram
                clean_body = body.strip()
                if len(clean_body) > 800:
                    response += clean_body[:800] + "\n\n... *[Content truncated - email is longer]*"
                else:
                    response += clean_body
            else:
                response += "*No content available*"
            
            response += "\n\n💡 You can ask me to search for more emails or help with other tasks!"
            
            return response
            
        except Exception as e:
            print(f"⚠️ Error getting email details: {e}")
            return f"❌ Error retrieving email {email_id}: {str(e)}"
    
    def _maybe_update_summary(self, user_id: str, history: List[Dict]):
        """Update summary when conversation gets long"""
        try:
            # Get recent chunk to summarize
            recent_chunk = history[-100:]  # Last 100 messages
            
            # Build a simple summary request
            conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_chunk])
            
            summary_prompt = f"""Summarize this conversation in 2-3 sentences, focusing on:
1. Key topics discussed
2. Important facts or preferences mentioned  
3. Any ongoing tasks or search contexts

Conversation:
{conversation_text}

Summary:"""
            
            response = requests.post(
                f"{self.base_url}/completion",
                json={
                    "prompt": summary_prompt,
                    "max_tokens": 200,
                    "temperature": 0.3,
                    "stop": ["User:", "Human:"],
                    "stream": False
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                new_summary = result.get('content', '').strip()
                
                # Update long-term memory
                long_term = self._load_long_term_memory(user_id)
                facts = long_term.get('facts', [])
                
                # Extract any new facts (simple keyword extraction)
                self._extract_facts_from_conversation(recent_chunk, facts)
                
                self._save_long_term_memory(user_id, new_summary, facts, long_term.get('email_context', {}))
                print(f"📝 Updated conversation summary for user {user_id}")
                
        except Exception as e:
            print(f"⚠️ Error updating summary: {e}")
    
    def _extract_facts_from_conversation(self, messages: List[Dict], existing_facts: List[str]):
        """Extract key facts from conversation (simple implementation)"""
        fact_patterns = [
            r"my name is ([^.]+)",
            r"i work at ([^.]+)",
            r"my email is ([^.]+)",
            r"remember that ([^.]+)",
            r"i prefer ([^.]+)",
            r"i use ([^.]+) for ([^.]+)"
        ]
        
        for msg in messages:
            if msg['role'] == 'user':
                content = msg['content'].lower()
                for pattern in fact_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        fact = match.group(1).strip()
                        if len(fact) > 3 and fact not in existing_facts:
                            existing_facts.append(fact)
                            if len(existing_facts) > 20:  # Keep only recent facts
                                existing_facts.pop(0)
    
    def _build_email_context(self) -> str:
        """Build context from recent emails for conversation"""
        try:
            # Import here to avoid circular imports
            import sys
            import pathlib
            sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
            from services.email.email_repo import EmailRepo
            
            repo = EmailRepo()
            emails = repo.get_recent_emails(limit=5)
            
            context_lines = []
            for email in emails[:5]:  # Limit to 5 most recent
                subject = email.get('subject', 'No Subject')[:50]
                snippet = email.get('snippet', '')[:100]
                from_email = email.get('from_email', 'Unknown')
                context_lines.append(f"From {from_email}: {subject} - {snippet}")
            
            return "\n".join(context_lines) if context_lines else "No recent emails"
            
        except Exception as e:
            print(f"⚠️ Error building email context: {e}")
            return "Email context unavailable"
    
    def _clean_email_body(self, body: str) -> str:
        """Clean email body for better processing"""
        if not body:
            return ""
        
        lines = body.split('\n')
        clean_lines = []
        
        for line in lines:
            line = line.strip()
            if (line and 
                not line.startswith('>') and
                not line.startswith('On ') and
                not line.startswith('From:') and
                len(line) > 10):
                clean_lines.append(line)
        
        return ' '.join(clean_lines)
    
    def _naive_summarize(self, subject: str, body: str, max_lines: int = 2) -> str:
        """Fallback summarization without LLM"""
        clean_body = self._clean_email_body(body)
        
        if not clean_body:
            return f"Email: {subject}"
        
        sentences = [s.strip() for s in clean_body.replace('.', '.\n').split('\n') if s.strip()]
        
        if not sentences:
            return f"Email: {subject}"
        
        summary_parts = []
        for sentence in sentences[:max_lines]:
            if len(sentence) > 80:
                sentence = sentence[:80] + "..."
            summary_parts.append(sentence)
        
        return '\n'.join(summary_parts)
