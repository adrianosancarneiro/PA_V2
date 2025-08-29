#!/usr/bin/env python3
"""
Enhanced Telegram Bot for PA_V2 with Compose functionality
Includes digest, compose, and interactive email management
"""
import os
import sys
import pathlib
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Load environment
load_dotenv('/etc/pa_v2/secrets.env')

def create_enhanced_bot():
    """Create the enhanced bot with all handlers"""
    from interfaces.telegram.views.commands import (
        handle_start, handle_digest, handle_compose, handle_status, handle_message
    )
    from interfaces.telegram.views.handlers import on_callback
    
    # Build the application
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("digest", handle_digest))
    app.add_handler(CommandHandler("compose", handle_compose))
    app.add_handler(CommandHandler("status", handle_status))
    
    # Message handler for compose flow
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    # Callback handler for all inline buttons
    app.add_handler(CallbackQueryHandler(on_callback))
    
    return app

if __name__ == "__main__":
    print("🤖 Starting Enhanced PA_V2 Telegram Bot...")
    
    app = create_enhanced_bot()
    
    print("✅ Bot configured with:")
    print("   📧 /digest - Email digest")
    print("   ✍️  /compose - Compose emails") 
    print("   📊 /status - System status")
    print("   ⚡ Interactive buttons")
    print()
    print("🚀 Starting bot...")
    
    try:
        app.run_polling(allowed_updates=["message", "callback_query"])
    except KeyboardInterrupt:
        print("\n👋 Bot stopped.")
    except Exception as e:
        print(f"❌ Bot error: {e}")
        sys.exit(1)
