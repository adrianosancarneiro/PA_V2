"""
Telegram compose email handlers for PA_V2
Handles the multi-step email composition flow through Telegram interface
"""
import os
import sys
import pathlib
from typing import Dict, List

# Add src to path for imports
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

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

def _get_user_data(context: CallbackContext) -> dict:
    """Get user data dictionary"""
    return context.user_data

def _ensure_compose_state(context: CallbackContext) -> dict:
    """Ensure compose state is initialized"""
    ud = _get_user_data(context)
    ud.setdefault(ComposeState.TO, [])
    ud.setdefault(ComposeState.CC, [])
    ud.setdefault(ComposeState.BCC, [])
    return ud

def start_compose(update: Update, context: CallbackContext):
    """Start the compose flow - choose provider"""
    ud = _ensure_compose_state(context)
    ud[ComposeState.FLOW] = "provider"
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Gmail", callback_data="cmp:prov:gmail"),
        InlineKeyboardButton("Outlook", callback_data="cmp:prov:outlook"),
    ]])
    
    update.effective_chat.send_message(
        "📧 **Compose Email**\n\nChoose provider:", 
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

def handle_compose_callback(update: Update, context: CallbackContext):
    """Handle compose-related callback queries"""
    query = update.callback_query
    data = query.data
    ud = _ensure_compose_state(context)
    
    if data.startswith("cmp:prov:"):
        # Provider selection
        provider = data.split(":")[-1]
        ud[ComposeState.PROVIDER] = provider
        query.answer(f"{provider.title()} selected")
        ud[ComposeState.FLOW] = "recipients"
        
        update.effective_chat.send_message(
            "👥 **Add Recipients**\n\n"
            "• Type an email address\n"
            "• Or type: `find john` to search contacts\n"
            "• When done, send: `done`",
            parse_mode="Markdown"
        )
        return
    
    if data.startswith("cmp:addto:"):
        # Add contact to recipients
        email = data.split(":", 2)[-1]
        if email not in ud[ComposeState.TO]:
            ud[ComposeState.TO].append(email)
        query.answer(f"Added: {email}")
        
        update.effective_chat.send_message(
            f"✅ Added: {email}\n\nType more recipients or `done` to continue."
        )
        return
    
    if data == "cmp:approve":
        # Approve and send email
        _send_email_now(update, context)
        return
    
    if data == "cmp:regen":
        # Regenerate draft
        brief = ud.get(ComposeState.BRIEF, '')
        draft = f"Hi,\n\n{_brief_to_body(brief)}\n\nBest,\n"
        ud[ComposeState.DRAFT] = draft
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve & Send", callback_data="cmp:approve"),
            InlineKeyboardButton("🔄 Regenerate", callback_data="cmp:regen"),
        ]])
        
        query.message.reply_text(
            f"📝 **Regenerated Draft:**\n\n{draft}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        query.answer()
        return

def handle_compose_message(update: Update, context: CallbackContext):
    """Handle text messages during compose flow"""
    ud = _ensure_compose_state(context)
    
    if not ud.get(ComposeState.FLOW):
        return  # Not in compose flow
    
    text = (update.message.text or "").strip()
    
    if ud[ComposeState.FLOW] == "recipients":
        if text.lower().startswith("find "):
            # Search for contacts
            query = text[5:].strip()
            contacts = search_contacts(query, limit=8) or []
            
            if not contacts:
                update.message.reply_text("❌ No contacts found.")
                return
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{name} <{email}>", callback_data=f"cmp:addto:{email}")]
                for (_id, name, email) in contacts
            ])
            
            update.message.reply_text("👥 **Select Contact:**", reply_markup=keyboard, parse_mode="Markdown")
            return
        
        if text.lower() == "done":
            # Move to subject
            recipients = ud[ComposeState.TO]
            if not recipients:
                update.message.reply_text("❌ Please add at least one recipient first.")
                return
            
            ud[ComposeState.FLOW] = "subject"
            update.message.reply_text(
                f"✅ **Recipients:** {', '.join(recipients)}\n\n"
                f"📄 **Subject?**",
                parse_mode="Markdown"
            )
            return
        
        if "@" in text and "." in text:
            # Add email address
            if text not in ud[ComposeState.TO]:
                ud[ComposeState.TO].append(text)
            update.message.reply_text(f"✅ Added: {text}\n\nType more or `done` to continue.")
            return
        
        update.message.reply_text(
            "❌ Invalid input. Type:\n"
            "• `find <name>` to search contacts\n"
            "• A valid email address\n"
            "• `done` when finished"
        )
        return
    
    if ud[ComposeState.FLOW] == "subject":
        # Set subject, move to brief
        ud[ComposeState.SUBJECT] = text
        ud[ComposeState.FLOW] = "brief"
        
        update.message.reply_text(
            f"✅ **Subject:** {text}\n\n"
            f"💭 **What should we say?**\n"
            f"Send a short brief or bullet points:",
            parse_mode="Markdown"
        )
        return
    
    if ud[ComposeState.FLOW] == "brief":
        # Generate draft
        ud[ComposeState.BRIEF] = text
        draft = f"Hi,\n\n{_brief_to_body(text)}\n\nBest,\n"
        ud[ComposeState.DRAFT] = draft
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve & Send", callback_data="cmp:approve"),
            InlineKeyboardButton("🔄 Regenerate", callback_data="cmp:regen"),
        ]])
        
        update.message.reply_text(
            f"📝 **Draft Preview:**\n\n{draft}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        ud[ComposeState.FLOW] = "approve"
        return

def _brief_to_body(brief: str) -> str:
    """Convert brief to email body"""
    return brief.replace("- ", "• ").strip()

def _send_email_now(update: Update, context: CallbackContext):
    """Send the composed email"""
    query = update.callback_query
    ud = _get_user_data(context)
    
    provider = ud.get(ComposeState.PROVIDER)
    to_emails = ud.get(ComposeState.TO, [])
    subject = ud.get(ComposeState.SUBJECT)
    body = ud.get(ComposeState.DRAFT)
    
    if not all([provider, to_emails, subject, body]):
        query.answer("❌ Missing required fields")
        return
    
    try:
        repo = EmailRepo()
        
        if provider == "gmail":
            from_addr = os.getenv("GMAIL_FROM", "me@example.com")
            # Note: gmail_service needs to be available in context
            sent = gmail_send_message(
                context.bot_data.get("gmail_service"), 
                from_addr, to_emails, [], [], subject, body, None
            )
            msg_id = sent.get("id")
            thread_id = sent.get("threadId")
        else:  # outlook
            from_addr = os.getenv("OUTLOOK_FROM", "me@example.com")
            # Note: graph_session needs to be available in context
            outlook_send_mail(
                context.bot_data.get("graph_session"),
                from_addr, to_emails, [], [], subject, body, None
            )
            msg_id = "graph:sent"
            thread_id = None
        
        # Record in outbound table
        try:
            outbound_id = repo.create_outbound_draft(
                provider, from_addr, to_emails, [], [], subject, body, None, None
            )
            repo.mark_outbound_sent(outbound_id, msg_id, thread_id)
        except Exception as e:
            print(f"Warning: Failed to record outbound email: {e}")
        
        query.message.reply_text("✅ **Email sent successfully!**", parse_mode="Markdown")
        query.answer()
        
        # Clear compose state
        for key in [ComposeState.FLOW, ComposeState.PROVIDER, ComposeState.TO, 
                   ComposeState.CC, ComposeState.BCC, ComposeState.SUBJECT, 
                   ComposeState.BRIEF, ComposeState.DRAFT]:
            ud.pop(key, None)
        
    except Exception as e:
        query.answer(f"❌ Send failed: {str(e)}")
        query.message.reply_text(f"❌ **Send failed:** {str(e)}", parse_mode="Markdown")
