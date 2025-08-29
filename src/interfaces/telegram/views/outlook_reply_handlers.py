"""
Enhanced email reply handlers with Outlook reply support
Integrates with Internet Message-ID implementation
"""
import sys
import pathlib
from typing import Optional

# Add project root to path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
from services.email.email_repo import EmailRepo
from services.outlook.reply_service import reply_via_outlook_for_email_id


def create_reply_options_markup(email_id: int, has_internet_message_id: bool = False) -> InlineKeyboardMarkup:
    """Create reply options keyboard based on email capabilities."""
    buttons = []
    
    # Always offer Gmail reply (default)
    buttons.append([InlineKeyboardButton("📧 Reply via Gmail", callback_data=f"reply_gmail:{email_id}")])
    
    # Offer Outlook reply if we have Internet Message-ID (BYU emails)
    if has_internet_message_id:
        buttons.append([InlineKeyboardButton("🏢 Reply via Outlook (BYU)", callback_data=f"reply_outlook:{email_id}")])
    
    # Cancel option
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data=f"reply_cancel:{email_id}")])
    
    return InlineKeyboardMarkup(buttons)


async def handle_reply_selection(update: Update, context: CallbackContext) -> None:
    """Handle reply method selection (Gmail vs Outlook)."""
    query = update.callback_query
    if not query or not query.data:
        return
    
    try:
        action, email_id_str = query.data.split(":", 1)
        email_id = int(email_id_str)
    except Exception:
        await query.answer("Invalid callback data")
        return
    
    repo = EmailRepo()
    detail = repo.get_email_detail(email_id)
    
    if not detail:
        await query.answer("Email not found")
        return
    
    if action == "reply_gmail":
        await handle_gmail_reply(update, context, email_id, detail)
    elif action == "reply_outlook":
        await handle_outlook_reply(update, context, email_id, detail)
    elif action == "reply_cancel":
        await query.answer("Reply cancelled")
        try:
            await query.message.delete()
        except:
            pass  # Message might already be deleted
    else:
        await query.answer("Unknown action")


async def handle_gmail_reply(update: Update, context: CallbackContext, email_id: int, detail: dict) -> None:
    """Handle reply via Gmail (existing functionality)."""
    query = update.callback_query
    
    # Start text input mode for Gmail reply
    context.user_data['awaiting_reply'] = {
        'email_id': email_id,
        'method': 'gmail',
        'detail': detail
    }
    
    subject = detail.get("subject", "No Subject")
    from_email = detail.get("from_email", "Unknown")
    
    await query.message.edit_text(
        f"📧 **Reply via Gmail**\n\n"
        f"To: {from_email}\n"
        f"Re: {subject}\n\n"
        f"💬 Please type your reply message:",
        parse_mode="Markdown"
    )
    
    await query.answer("Type your Gmail reply")


async def handle_outlook_reply(update: Update, context: CallbackContext, email_id: int, detail: dict) -> None:
    """Handle reply via Outlook using Internet Message-ID."""
    query = update.callback_query
    
    # Check if we have Graph session
    graph_session = context.bot_data.get('graph_session')
    if not graph_session:
        await query.answer("❌ Outlook not configured")
        await query.message.edit_text(
            "❌ **Outlook Reply Unavailable**\n\n"
            "Microsoft Graph session not configured. Please contact admin.",
            parse_mode="Markdown"
        )
        return
    
    # Check if email has Internet Message-ID
    internet_message_id = detail.get('internet_message_id')
    if not internet_message_id:
        await query.answer("❌ No BYU message found")
        await query.message.edit_text(
            "❌ **Outlook Reply Unavailable**\n\n"
            "This email doesn't have the original BYU message information needed for Outlook threading.\n\n"
            "This usually means:\n"
            "• Email is not from BYU system\n"
            "• Email was received before Internet Message-ID support\n\n"
            "💡 Use Gmail reply instead.",
            parse_mode="Markdown"
        )
        return
    
    # Start text input mode for Outlook reply
    context.user_data['awaiting_reply'] = {
        'email_id': email_id,
        'method': 'outlook',
        'detail': detail,
        'internet_message_id': internet_message_id
    }
    
    subject = detail.get("subject", "No Subject")
    from_email = detail.get("from_email", "Unknown")
    
    await query.message.edit_text(
        f"🏢 **Reply via Outlook (BYU)**\n\n"
        f"To: {from_email}\n"
        f"Re: {subject}\n\n"
        f"📧 Original Message-ID: `{internet_message_id}`\n\n"
        f"💬 Please type your reply message:",
        parse_mode="Markdown"
    )
    
    await query.answer("Type your Outlook reply")


async def handle_reply_message(update: Update, context: CallbackContext) -> None:
    """Handle the actual reply message text from user."""
    reply_context = context.user_data.get('awaiting_reply')
    if not reply_context:
        return  # Not in reply mode
    
    reply_text = update.message.text
    if not reply_text or not reply_text.strip():
        await update.message.reply_text("❌ Please provide a non-empty reply message.")
        return
    
    email_id = reply_context['email_id']
    method = reply_context['method']
    detail = reply_context['detail']
    
    # Clear the reply context
    del context.user_data['awaiting_reply']
    
    if method == 'gmail':
        await send_gmail_reply(update, context, email_id, detail, reply_text)
    elif method == 'outlook':
        await send_outlook_reply(update, context, email_id, detail, reply_text)


async def send_gmail_reply(update: Update, context: CallbackContext, email_id: int, detail: dict, reply_text: str) -> None:
    """Send reply via Gmail."""
    # This would integrate with existing Gmail sending functionality
    # For now, just create a draft
    repo = EmailRepo()
    
    try:
        draft_id = repo.add_draft(email_id, reply_text)
        
        subject = detail.get("subject", "No Subject")
        from_email = detail.get("from_email", "Unknown")
        
        await update.message.reply_text(
            f"✅ **Gmail Reply Draft Created**\n\n"
            f"📧 Draft ID: {draft_id}\n"
            f"To: {from_email}\n"
            f"Re: {subject}\n\n"
            f"💡 Draft saved for manual sending via Gmail interface.",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to create Gmail draft: {e}")


async def send_outlook_reply(update: Update, context: CallbackContext, email_id: int, detail: dict, reply_text: str) -> None:
    """Send reply via Outlook using Internet Message-ID."""
    graph_session = context.bot_data.get('graph_session')
    if not graph_session:
        await update.message.reply_text("❌ Outlook Graph session not available")
        return
    
    from_email = detail.get("from_email", "Unknown")
    subject = detail.get("subject", "No Subject")
    
    # Show sending status
    status_msg = await update.message.reply_text(
        f"🔄 **Sending Outlook Reply...**\n\n"
        f"To: {from_email}\n"
        f"Re: {subject}\n\n"
        f"Please wait...",
        parse_mode="Markdown"
    )
    
    try:
        # Use the Outlook reply service
        result = reply_via_outlook_for_email_id(
            graph_session,
            email_id,
            reply_text,
            extra_cc=[],  # Could add CC options in future
            extra_bcc=[]  # Could add BCC options in future
        )
        
        if result == "sent":
            await status_msg.edit_text(
                f"✅ **Outlook Reply Sent Successfully!**\n\n"
                f"To: {from_email}\n"
                f"Re: {subject}\n\n"
                f"🏢 Sent via BYU Outlook with proper threading\n"
                f"📧 Check your Outlook Sent Items for confirmation",
                parse_mode="Markdown"
            )
            
            # Touch the email to mark it as replied
            repo = EmailRepo()
            repo.touch(email_id)
            
        else:
            # Handle various error conditions with user-friendly messages
            error_messages = {
                "no_internet_message_id": "❌ Missing original message information",
                "not_found": "❌ Original BYU message not found in Outlook",
                "draft_create_failed": "❌ Failed to create reply draft in Outlook", 
                "update_failed": "❌ Failed to update reply content",
                "send_failed": "❌ Failed to send reply via Outlook"
            }
            
            error_msg = error_messages.get(result, f"❌ Unknown error: {result}")
            
            await status_msg.edit_text(
                f"**Outlook Reply Failed**\n\n"
                f"To: {from_email}\n"
                f"Re: {subject}\n\n"
                f"{error_msg}\n\n"
                f"💡 Try using Gmail reply instead, or compose a new email.",
                parse_mode="Markdown"
            )
    
    except Exception as e:
        await status_msg.edit_text(
            f"❌ **Outlook Reply Error**\n\n"
            f"To: {from_email}\n"
            f"Re: {subject}\n\n"
            f"Error: {str(e)}\n\n"
            f"💡 Try using Gmail reply instead.",
            parse_mode="Markdown"
        )


def enhance_reply_button_handler(original_handler):
    """Decorator to enhance existing reply button with provider selection."""
    
    async def enhanced_handler(update: Update, context: CallbackContext) -> None:
        """Enhanced reply handler that offers provider choice."""
        query = update.callback_query
        if not query or not query.data:
            return await original_handler(update, context)
        
        # Check if this is a reply action
        if not query.data.startswith("reply:"):
            return await original_handler(update, context)
        
        try:
            _, email_id_str = query.data.split(":", 1)
            email_id = int(email_id_str)
        except Exception:
            return await original_handler(update, context)
        
        # Get email details to check for Internet Message-ID
        repo = EmailRepo()
        detail = repo.get_email_detail(email_id)
        
        if not detail:
            await query.answer("Email not found")
            return
        
        has_internet_message_id = bool(detail.get('internet_message_id'))
        subject = detail.get("subject", "No Subject")
        from_email = detail.get("from_email", "Unknown")
        
        # Show provider selection
        markup = create_reply_options_markup(email_id, has_internet_message_id)
        
        provider_info = ""
        if has_internet_message_id:
            provider_info = "🏢 **BYU Email Detected** - Outlook reply available for proper threading\n\n"
        
        await query.message.edit_text(
            f"**Choose Reply Method**\n\n"
            f"{provider_info}"
            f"To: {from_email}\n"
            f"Re: {subject}\n\n"
            f"How would you like to reply?",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
        await query.answer("Choose reply method")
    
    return enhanced_handler
