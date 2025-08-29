"""Telegram compose email functionality."""
import os
import sys
import pathlib
from typing import Dict, List

# Add project root to path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from services.email.contacts_repo import search_contacts
from services.email.email_repo import EmailRepo
from providers.gmail_send import gmail_send_message
from providers.outlook_send import outlook_send_mail

# State keys for compose flow
class ComposeState:
    FLOW = "cmp_flow"
    PROVIDER = "cmp_provider"
    TO = "cmp_to"
    CC = "cmp_cc"
    BCC = "cmp_bcc"
    SUBJECT = "cmp_subject"
    BRIEF = "cmp_brief"
    DRAFT = "cmp_draft"
    OUTBOUND_ID = "cmp_outbound_id"

K = ComposeState()


def _get_user_data(context: CallbackContext) -> Dict:
    """Get user data from context."""
    return context.user_data


def _ensure_lists(context: CallbackContext) -> Dict:
    """Ensure TO, CC, BCC lists exist in user data."""
    ud = _get_user_data(context)
    ud.setdefault(K.TO, [])
    ud.setdefault(K.CC, [])
    ud.setdefault(K.BCC, [])
    return ud


def start_compose(update: Update, context: CallbackContext):
    """Start the compose email flow."""
    ud = _ensure_lists(context)
    
    # Clear any previous compose state
    for key in [K.FLOW, K.PROVIDER, K.SUBJECT, K.BRIEF, K.DRAFT, K.OUTBOUND_ID]:
        ud.pop(key, None)
    ud[K.TO] = []
    ud[K.CC] = []
    ud[K.BCC] = []
    
    # Start with provider selection
    ud[K.FLOW] = "provider"
    
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("📧 Gmail", callback_data="cmp:prov:gmail"),
        InlineKeyboardButton("📨 Outlook", callback_data="cmp:prov:outlook"),
    ]])
    
    update.effective_chat.send_message(
        "📝 *Compose Email*\n\nChoose your email provider:",
        reply_markup=kb,
        parse_mode="Markdown"
    )


def on_compose_callback(update: Update, context: CallbackContext):
    """Handle inline keyboard callbacks for compose flow."""
    query = update.callback_query
    data = query.data
    ud = _ensure_lists(context)
    
    if data.startswith("cmp:prov:"):
        # Provider selection
        provider = data.split(":")[-1]
        ud[K.PROVIDER] = provider
        query.answer(f"{provider.title()} selected")
        
        ud[K.FLOW] = "recipients"
        update.effective_chat.send_message(
            f"📧 *Composing with {provider.title()}*\n\n"
            "👥 *Add Recipients:*\n"
            "• Type an email address directly\n"
            "• Or type: `find john` to search contacts\n"
            "• When done, send: `done`",
            parse_mode="Markdown"
        )
        return
    
    if data.startswith("cmp:addto:"):
        # Add recipient from contact search
        email = data.split(":", 2)[2]
        if email not in ud[K.TO]:
            ud[K.TO].append(email)
        
        query.answer(f"Added: {email}")
        query.message.reply_text(
            f"✅ Added: {email}\n\n"
            f"Recipients: {', '.join(ud[K.TO]) if ud[K.TO] else '(none)'}\n\n"
            "Add more recipients or send `done`"
        )
        return
    
    if data == "cmp:approve":
        # Approve and send the email
        _send_now(update, context)
        return
    
    if data == "cmp:regen":
        # Regenerate the draft
        brief = ud.get(K.BRIEF, "")
        draft = _brief_to_body(brief)
        ud[K.DRAFT] = draft
        
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve & Send", callback_data="cmp:approve"),
            InlineKeyboardButton("🔄 Regenerate", callback_data="cmp:regen"),
        ]])
        
        query.message.reply_text(
            f"📝 *Updated Draft:*\n\n{draft}",
            reply_markup=kb,
            parse_mode="Markdown"
        )
        query.answer("Draft regenerated")
        return


def on_compose_message(update: Update, context: CallbackContext):
    """Handle text messages during compose flow."""
    ud = _ensure_lists(context)
    
    if not ud.get(K.FLOW):
        return  # Not in compose flow
    
    text = (update.message.text or "").strip()
    flow_state = ud[K.FLOW]
    
    if flow_state == "recipients":
        if text.lower().startswith("find "):
            # Search contacts
            query_term = text[5:].strip()
            if not query_term:
                update.message.reply_text("Please provide a search term after 'find'")
                return
            
            try:
                contacts = search_contacts(query_term, limit=8)
                if not contacts:
                    update.message.reply_text(f"🔍 No contacts found for '{query_term}'")
                    return
                
                # Create inline keyboard with contact options
                buttons = []
                for (contact_id, name, email) in contacts:
                    display_name = f"{name} <{email}>" if name and name != email else email
                    buttons.append([InlineKeyboardButton(
                        display_name[:60],  # Truncate for display
                        callback_data=f"cmp:addto:{email}"
                    )])
                
                kb = InlineKeyboardMarkup(buttons)
                update.message.reply_text(
                    f"🔍 Found {len(contacts)} contacts for '{query_term}':",
                    reply_markup=kb
                )
                return
                
            except Exception as e:
                print(f"Error searching contacts: {e}")
                update.message.reply_text(f"❌ Error searching contacts: {e}")
                return
        
        elif text.lower() == "done":
            # Finished adding recipients
            if not ud[K.TO]:
                update.message.reply_text("⚠️ Please add at least one recipient first.")
                return
            
            ud[K.FLOW] = "subject"
            update.message.reply_text(
                f"📝 *Recipients:* {', '.join(ud[K.TO])}\n\n"
                "📋 What's the subject?",
                parse_mode="Markdown"
            )
            return
        
        elif "@" in text and "." in text:
            # Direct email address
            email = text.strip()
            if email not in ud[K.TO]:
                ud[K.TO].append(email)
            
            update.message.reply_text(
                f"✅ Added: {email}\n\n"
                f"Recipients: {', '.join(ud[K.TO])}\n\n"
                "Add more recipients or send `done`"
            )
            return
        
        else:
            update.message.reply_text(
                "📧 Please:\n"
                "• Type an email address\n"
                "• Type `find <name>` to search contacts\n"
                "• Type `done` when finished"
            )
            return
    
    elif flow_state == "subject":
        # Subject input
        ud[K.SUBJECT] = text
        ud[K.FLOW] = "brief"
        
        update.message.reply_text(
            f"📋 *Subject:* {text}\n\n"
            "✍️ What should the email say? Send a brief description or bullet points:",
            parse_mode="Markdown"
        )
        return
    
    elif flow_state == "brief":
        # Brief input - generate draft
        ud[K.BRIEF] = text
        draft = _brief_to_body(text)
        ud[K.DRAFT] = draft
        ud[K.FLOW] = "approve"
        
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve & Send", callback_data="cmp:approve"),
            InlineKeyboardButton("🔄 Regenerate", callback_data="cmp:regen"),
        ]])
        
        update.message.reply_text(
            f"📝 *Draft Email:*\n\n{draft}",
            reply_markup=kb,
            parse_mode="Markdown"
        )
        return


def _brief_to_body(brief: str) -> str:
    """Convert brief description to email body."""
    # Simple formatting for now - could be enhanced with LLM in the future
    lines = brief.strip().split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('- '):
            formatted_lines.append(f"• {line[2:]}")
        elif line.startswith('* '):
            formatted_lines.append(f"• {line[2:]}")
        else:
            formatted_lines.append(line)
    
    body = '\n'.join(formatted_lines)
    
    # Add greeting and closing
    return f"Hi,\n\n{body}\n\nBest regards"


def _send_now(update: Update, context: CallbackContext):
    """Send the composed email."""
    query = update.callback_query
    ud = _get_user_data(context)
    
    # Validate required fields
    provider = ud.get(K.PROVIDER)
    to_emails = ud.get(K.TO, [])
    subject = ud.get(K.SUBJECT)
    body = ud.get(K.DRAFT)
    
    if not all([provider, to_emails, subject, body]):
        query.answer("❌ Missing required fields")
        return
    
    try:
        repo = EmailRepo()
        
        # Get sender email from environment
        if provider == "gmail":
            from_addr = os.getenv("GMAIL_FROM", "me@example.com")
        else:
            from_addr = os.getenv("OUTLOOK_FROM", "me@example.com")
        
        # Create outbound record
        outbound_id = repo.create_outbound_draft(
            provider, from_addr, to_emails, [], [], subject, body, None, None
        )
        
        # Send the email
        if provider == "gmail":
            # Get Gmail service from bot data (set up in main bot)
            gmail_service = context.bot_data.get("gmail_service")
            if not gmail_service:
                raise Exception("Gmail service not available")
            
            sent_result = gmail_send_message(
                gmail_service, from_addr, to_emails, [], [], subject, body, None
            )
            msg_id = sent_result.get("id")
            thread_id = sent_result.get("threadId")
            
        else:  # outlook
            # Get Graph session from bot data
            graph_session = context.bot_data.get("graph_session")
            if not graph_session:
                raise Exception("Outlook Graph session not available")
            
            outlook_send_mail(
                graph_session, from_addr, to_emails, [], [], subject, body, None
            )
            msg_id = f"outlook_sent_{outbound_id}"
            thread_id = None
        
        # Mark as sent
        repo.mark_outbound_sent(outbound_id, msg_id, thread_id)
        
        # Clear compose state
        for key in [K.FLOW, K.PROVIDER, K.TO, K.CC, K.BCC, K.SUBJECT, K.BRIEF, K.DRAFT, K.OUTBOUND_ID]:
            ud.pop(key, None)
        
        query.message.reply_text(
            f"✅ *Email Sent!*\n\n"
            f"📧 Provider: {provider.title()}\n"
            f"👥 To: {', '.join(to_emails)}\n"
            f"📋 Subject: {subject}",
            parse_mode="Markdown"
        )
        query.answer("Email sent successfully!")
        
    except Exception as e:
        print(f"Error sending email: {e}")
        query.message.reply_text(f"❌ Failed to send email: {e}")
        query.answer("Send failed")
