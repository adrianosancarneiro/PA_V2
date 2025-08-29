import asyncio
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv('/etc/pa_v2/secrets.env')
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# 1. Define the handler function for the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the command /start is issued."""
    # 'update' contains information about the incoming message
    # 'context' is a general-purpose object for the handler
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! 👋",
    )

def main() -> None:
    """Start the bot."""
    # 2. Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    # 3. Register the command handler
    # This tells the bot to run the 'start' function when it receives the /start command.
    application.add_handler(CommandHandler("start", start))

    # 4. Start the bot and listen for updates
    # The bot will keep running until you stop the script (e.g., with Ctrl-C).
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()