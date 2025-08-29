"""
Telegram command handlers for PA_V2
Handles /commands like /digest, /compose, etc.
"""
import sys
import pathlib
from telegram import Update
from telegram.ext import CallbackContext

# Add src to path for imports
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from services.email.email_repo import EmailRepo
from .digest import build_digest
from .compose_handlers import start_compose, handle_compose_message

repo = EmailRepo()

def handle_start(update: Update, context: CallbackContext):
    """Handle /start command"""
    update.message.reply_text(
        "🤖 **PA_V2 Email Assistant**\n\n"
        "Available commands:\n"
        "• /digest - View recent emails\n"
        "• /compose - Compose new email\n"
        "• /status - System status",
        parse_mode="Markdown"
    )

def handle_digest(update: Update, context: CallbackContext):
    """Handle /digest command"""
    try:
        emails = repo.get_recent_emails(limit=10)
        if not emails:
            update.message.reply_text("📭 No recent emails found.")
            return
        
        # Convert to the format expected by build_digest
        rows = [
            (email["id"], email["provider"], email.get("from_display", ""), 
             email.get("from_email", ""), email.get("subject", ""), 
             email.get("snippet", ""), email["received_at"], 
             email.get("provider_thread_id", ""))
            for email in emails
        ]
        
        text, markup, _ = build_digest(rows)
        update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")
        
    except Exception as e:
        update.message.reply_text(f"❌ Failed to generate digest: {e}")

def handle_compose(update: Update, context: CallbackContext):
    """Handle /compose command"""
    start_compose(update, context)

def handle_status(update: Update, context: CallbackContext):
    """Handle /status command"""
    try:
        recent_count = len(repo.get_recent_emails(limit=10))
        update.message.reply_text(
            f"📊 **System Status**\n\n"
            f"• Database: ✅ Connected\n"
            f"• Recent emails: {recent_count}\n"
            f"• Services: ✅ Running",
            parse_mode="Markdown"
        )
    except Exception as e:
        update.message.reply_text(f"❌ Status check failed: {e}")

def handle_message(update: Update, context: CallbackContext):
    """Handle text messages (for compose flow)"""
    handle_compose_message(update, context)
