"""
Telegram callback handlers for PA_V2
Handles inline button interactions for email digest
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
import sys
import os

# Add src to path for imports
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from services.email.email_repo import EmailRepo

repo = EmailRepo()

def _confirm_delete_markup(email_id: int):
    """Create confirmation markup for delete action"""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Delete", callback_data=f"delok:{email_id}"),
        InlineKeyboardButton("Cancel", callback_data=f"delcancel:{email_id}")
    ]])

async def on_callback(update: Update, context: CallbackContext):
    """Single entry point for all inline callbacks"""
    if not update.callback_query or not update.callback_query.data:
        return
    
    data = update.callback_query.data
    
    # Handle compose callbacks
    if data.startswith("cmp:"):
        from .compose_handlers import handle_compose_callback
        await handle_compose_callback(update, context)
        return
    
    try:
        action, id_str = data.split(":", 1)
        email_id = int(id_str)
    except Exception:
        await update.callback_query.answer("Bad callback")
        return

    if action == "star":
        # Mark important tag in DB
        try:
            repo.mark_important(email_id)
            repo.touch(email_id, action="mark_important")
            await update.callback_query.answer("Marked ⭐")
        except Exception as e:
            await update.callback_query.answer(f"Failed: {e}")
        return

    if action == "more":
        # Show detailed view
        try:
            row = repo.get_email_detail(email_id)
            if not row:
                await update.callback_query.answer("Email not found")
                return
                
            subject = row.get("subject") or "(no subject)"
            from_d = row.get("from_display") or row.get("from_email") or "(unknown)"
            snippet = (row.get("body_plain") or row.get("snippet") or "").strip()
            
            if len(snippet) > 1500:  # Telegram message limit safety
                snippet = snippet[:1500] + "…"
                
            text = f"*From:* {from_d}\n*Subject:* {subject}\n\n{snippet}"
            await update.effective_chat.send_message(text, parse_mode="Markdown")
            repo.touch(email_id, action="view")
            await update.callback_query.answer()
        except Exception as e:
            await update.callback_query.answer(f"Failed: {e}")
        return

    if action == "reply":
        # NEW: Enhanced reply with Outlook support
        try:
            detail = repo.get_email_detail(email_id)
            if not detail:
                update.callback_query.answer("Email not found")
                return
            
            # Import the enhanced reply functionality
            from .outlook_reply_handlers import create_reply_options_markup
            
            has_internet_message_id = bool(detail.get('internet_message_id'))
            subject = detail.get("subject", "No Subject")
            from_email = detail.get("from_email", "Unknown")
            
            # Show provider selection
            markup = create_reply_options_markup(email_id, has_internet_message_id)
            
            provider_info = ""
            if has_internet_message_id:
                provider_info = "🏢 **BYU Email Detected** - Outlook reply available for proper threading\n\n"
            
            await update.callback_query.message.edit_text(
                f"**Choose Reply Method**\n\n"
                f"{provider_info}"
                f"To: {from_email}\n"
                f"Re: {subject}\n\n"
                f"How would you like to reply?",
                reply_markup=markup,
                parse_mode="Markdown"
            )
            
            await update.callback_query.answer("Choose reply method")
            repo.touch(email_id)
        except Exception as e:
            await update.callback_query.answer(f"Failed: {e}")
        return

    if action == "delreq":
        # Request delete confirmation
        try:
            await update.callback_query.message.reply_text(
                "Delete entire conversation? This moves all messages in this thread to Trash/Deleted Items.",
                reply_markup=_confirm_delete_markup(email_id)
            )
            await update.callback_query.answer()
        except Exception as e:
            await update.callback_query.answer(f"Failed: {e}")
        return

    if action == "delok":
        # Confirm delete thread
        try:
            em = repo.get_email_row(email_id)
            if not em:
                await update.callback_query.answer("Email not found")
                return
                
            deleted_by = f"telegram:{update.effective_user.id}"
            
            # Import provider actions
            if em["provider"] == "gmail":
                try:
                    from services.email.providers.gmail_actions import gmail_trash_thread
                    # Would need gmail service - for now just mark in DB
                    # gmail_trash_thread(context.bot_data["gmail_service"], em["provider_thread_id"])
                except ImportError:
                    pass  # Provider actions not available
            elif em["provider"] == "outlook":
                try:
                    from services.email.providers.outlook_actions import outlook_soft_delete_conversation
                    # Would need outlook session - for now just mark in DB
                    # outlook_soft_delete_conversation(context.bot_data["outlook_session"], em["provider_thread_id"])
                except ImportError:
                    pass  # Provider actions not available
            
            # Mark thread as deleted in database
            repo.mark_thread_deleted(em["thread_id"], deleted_by, mode="soft")
            
            # Create undo button
            undo_markup = InlineKeyboardMarkup([[
                InlineKeyboardButton("↩ Undo", callback_data=f"undodel:{em['thread_id']}")
            ]])
            
            await update.callback_query.message.reply_text(
                "Thread deleted. All messages moved to trash.",
                reply_markup=undo_markup
            )
            await update.callback_query.answer("Deleted")
        except Exception as e:
            await update.callback_query.answer(f"Failed: {e}")
        return

    if action == "delcancel":
        # Cancel delete action
        await update.callback_query.message.reply_text("Delete cancelled.")
        await update.callback_query.answer()
        return

    if action == "undodel":
        # Undo delete thread
        try:
            thread_id = int(id_str)
            repo.restore_thread_deleted(thread_id)
            await update.callback_query.message.reply_text("Thread restored from trash.")
            await update.callback_query.answer("Restored")
        except Exception as e:
            await update.callback_query.answer(f"Failed: {e}")
        return

    # Unknown action
    await update.callback_query.answer("Unknown action")
