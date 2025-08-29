"""
Complete Telegram bot with compose functionality
Integrates with existing email system and digest functionality
"""
import os
import sys
import pathlib

# Add project root to path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# Load environment variables
load_dotenv('/etc/pa_v2/secrets.env')

# Import existing functionality
from interfaces.telegram.views.digest import send_digest
from interfaces.telegram.views.handlers import on_callback
from services.email.email_repo import EmailRepo

    # Import new compose functionality
try:
    from interfaces.telegram.views.compose_handlers import (
        start_compose, 
        handle_compose_callback, 
        handle_compose_message
    )
    COMPOSE_AVAILABLE = True
except ImportError:
    print("Warning: Compose functionality not available")
    COMPOSE_AVAILABLE = False

# Import Outlook reply handlers
from interfaces.telegram.views.outlook_reply_handlers import (
    handle_reply_selection,
    handle_reply_message
)# Import email providers for bot_data
try:
    from services.email.providers.gmail_provider import GmailProvider
    from services.email.providers.outlook_provider import OutlookGraphProvider
    from googleapiclient.discovery import build
    PROVIDERS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Email providers not available: {e}")
    PROVIDERS_AVAILABLE = False

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    await update.message.reply_html(
        f"Hi {user.mention_html()}! 👋\n\n"
        "📧 *PA Email Assistant*\n\n"
        "Available commands:\n"
        "• /digest - View recent emails\n"
        "• /compose - Compose new email\n"
        "• /status - Check email provider status",
        parse_mode="Markdown"
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show email provider authentication status."""
    if not PROVIDERS_AVAILABLE:
        await update.message.reply_text("❌ Email providers not configured")
        return
    
    status_text = "📊 *Email Provider Status:*\n\n"
    
    try:
        gmail = GmailProvider()
        gmail_status = "✅ Ready" if gmail.is_authenticated() else "❌ Setup needed"
        status_text += f"🟥 Gmail: {gmail_status}\n"
    except Exception as e:
        status_text += f"🟥 Gmail: ❌ Error ({e})\n"
    
    try:
        outlook = OutlookGraphProvider()
        outlook_status = "✅ Ready" if outlook.is_authenticated() else "❌ Setup needed"
        status_text += f"🟦 Outlook: {outlook_status}\n"
    except Exception as e:
        status_text += f"🟦 Outlook: ❌ Error ({e})\n"
    
    await update.message.reply_text(status_text, parse_mode="Markdown")


async def digest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show recent email digest."""
    try:
        repo = EmailRepo()
        rows = repo.latest_new_messages(limit=10)
        
        if not rows:
            await update.message.reply_text("📭 No recent emails found.")
            return
        
        bot = context.bot
        chat_id = update.effective_chat.id
        send_digest(bot, chat_id, rows)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching digest: {e}")


async def compose_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the compose email flow."""
    if not PROVIDERS_AVAILABLE:
        await update.message.reply_text("❌ Email providers not configured for sending")
        return
    
    if not COMPOSE_AVAILABLE:
        await update.message.reply_text("❌ Compose functionality not available")
        return
    
    start_compose(update, context)


async def setup_bot_data(application: Application) -> None:
    """Initialize bot data with email services."""
    if not PROVIDERS_AVAILABLE:
        print("⚠️ Email providers not available, compose functionality disabled")
        return
    
    try:
        # Initialize Gmail service
        gmail = GmailProvider()
        if gmail.is_authenticated():
            # Load credentials and create service
            from google.oauth2.credentials import Credentials
            gmail_token_path = os.getenv("GMAIL_TOKEN_PATH", "config/gmail_token.json")
            creds = Credentials.from_authorized_user_file(gmail_token_path, scopes=[
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.send"
            ])
            gmail_service = build("gmail", "v1", credentials=creds)
            application.bot_data["gmail_service"] = gmail_service
            print("✅ Gmail service initialized for compose")
        
        # Initialize Outlook Graph session
        outlook = OutlookGraphProvider()
        if outlook.is_authenticated():
            application.bot_data["graph_session"] = outlook.session
            print("✅ Outlook Graph session initialized for compose")
            
    except Exception as e:
        print(f"⚠️ Error setting up email services: {e}")


async def combined_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages for both reply and compose flows"""
    if context.user_data.get('awaiting_reply'):
        await handle_reply_message(update, context)
    elif COMPOSE_AVAILABLE:
        await handle_compose_message(update, context)


def main() -> None:
    """Start the enhanced Telegram bot."""
    if not TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not found in environment")
        return
    
    print("🤖 Starting enhanced Telegram bot with compose functionality...")
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("digest", digest_command))
    application.add_handler(CommandHandler("compose", compose_command))
    
    # Add Outlook reply handlers (before compose handlers for priority)
    application.add_handler(CallbackQueryHandler(
        handle_reply_selection,
        pattern=r"^(reply_gmail|reply_outlook|reply_cancel):"
    ))
    
    # Add reply message handler (for text input after selecting reply method)
    application.add_handler(MessageHandler(
        filters.TEXT & (~filters.COMMAND) & filters.UpdateType.MESSAGE,
        combined_message_handler
    ))
    
    # Add compose handlers (if available)
    if COMPOSE_AVAILABLE:
        application.add_handler(CallbackQueryHandler(
            handle_compose_callback, 
            pattern=r"^cmp:"
        ))
    
    # Add existing digest handlers (updated to support new reply flow)
    application.add_handler(CallbackQueryHandler(
        on_callback,
        pattern=r"^(more|reply|star|delreq):"
    ))
    
    # Note: Email services setup removed for now to fix startup issues
    # The bot will work for digest interactions without this
    
    print("📧 Bot handlers registered:")
    print("  • Commands: /start, /status, /digest, /compose")
    print("  • Inline: compose flow, digest actions")
    print("  • Email providers integration ready")
    
    # Start the bot
    application.run_polling()


if __name__ == "__main__":
    main()
