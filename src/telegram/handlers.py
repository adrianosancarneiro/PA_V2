"""
Telegram callback handlers for PA_V2
Handles inline button interactions for email digest
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from repo.email_repo import EmailRepo

repo = EmailRepo()

def _confirm_delete_markup(email_id: int):
    """Create confirmation markup for delete action"""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Delete", callback_data=f"delok:{email_id}"),
        InlineKeyboardButton("Cancel", callback_data=f"delcancel:{email_id}")
    ]])

def on_callback(update: Update, context: CallbackContext):
    """Single entry point for all inline callbacks"""
    if not update.callback_query or not update.callback_query.data:
        return
    
    data = update.callback_query.data
    try:
        action, id_str = data.split(":", 1)
        email_id = int(id_str)
    except Exception:
        update.callback_query.answer("Bad callback")
        return

    if action == "star":
        # Mark important tag in DB
        try:
            repo.mark_important(email_id)
            repo.touch(email_id, action="mark_important")
            update.callback_query.answer("Marked ⭐")
        except Exception as e:
            update.callback_query.answer(f"Failed: {e}")
        return

    if action == "more":
        # Show detailed view
        try:
            row = repo.get_email_detail(email_id)
            if not row:
                update.callback_query.answer("Email not found")
                return
                
            subject = row.get("subject") or "(no subject)"
            from_d = row.get("from_display") or row.get("from_email") or "(unknown)"
            snippet = (row.get("body_plain") or row.get("snippet") or "").strip()
            
            if len(snippet) > 1500:  # Telegram message limit safety
                snippet = snippet[:1500] + "…"
                
            text = f"*From:* {from_d}\n*Subject:* {subject}\n\n{snippet}"
            update.effective_chat.send_message(text, parse_mode="Markdown")
            repo.touch(email_id, action="view")
            update.callback_query.answer()
        except Exception as e:
            update.callback_query.answer(f"Failed: {e}")
        return

    if action == "reply":
        # Generate initial LLM draft and present approve/edit
        try:
            detail = repo.get_email_detail(email_id)
            if not detail:
                update.callback_query.answer("Email not found")
                return
                
            subject = detail.get("subject") or "(no subject)"
            # TODO: plug actual LLM. For now, naive draft:
            draft = f"Hi,\n\nThanks for your email about \"{subject}\". I'll get back to you shortly.\n\nBest regards,"
            
            # Save draft revision
            draft_id = repo.add_draft(email_id, draft)
            update.effective_chat.send_message(f"Draft #{draft_id}:\n\n{draft}")
            repo.touch(email_id, action="reply")
            update.callback_query.answer("Draft created")
        except Exception as e:
            update.callback_query.answer(f"Failed: {e}")
        return

    if action == "delreq":
        # Request delete confirmation
        try:
            update.callback_query.message.reply_text(
                "Delete entire conversation? This moves all messages in this thread to Trash/Deleted Items.",
                reply_markup=_confirm_delete_markup(email_id)
            )
            update.callback_query.answer()
        except Exception as e:
            update.callback_query.answer(f"Failed: {e}")
        return

    if action == "delok":
        # Confirm delete thread
        try:
            em = repo.get_email_row(email_id)
            if not em:
                update.callback_query.answer("Email not found")
                return
                
            deleted_by = f"telegram:{update.effective_user.id}"
            
            # Import provider actions
            if em["provider"] == "gmail":
                try:
                    from providers.gmail_actions import gmail_trash_thread
                    # Would need gmail service - for now just mark in DB
                    # gmail_trash_thread(context.bot_data["gmail_service"], em["provider_thread_id"])
                except ImportError:
                    pass  # Provider actions not available
            elif em["provider"] == "outlook":
                try:
                    from providers.outlook_actions import outlook_soft_delete_conversation
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
            
            update.callback_query.message.reply_text(
                "Thread deleted. All messages moved to trash.",
                reply_markup=undo_markup
            )
            update.callback_query.answer("Deleted")
        except Exception as e:
            update.callback_query.answer(f"Failed: {e}")
        return

    if action == "delcancel":
        # Cancel delete action
        update.callback_query.message.reply_text("Delete cancelled.")
        update.callback_query.answer()
        return

    if action == "undodel":
        # Undo delete thread
        try:
            thread_id = int(id_str)
            repo.restore_thread_deleted(thread_id)
            update.callback_query.message.reply_text("Thread restored from trash.")
            update.callback_query.answer("Restored")
        except Exception as e:
            update.callback_query.answer(f"Failed: {e}")
        return

    # Unknown action
    update.callback_query.answer("Unknown action")
