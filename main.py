"""Main entry point for the expense tracker bot."""
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from constants import BOT_TOKEN
from db import init_db
from handlers import (
    start_command, chart_command, process_message
)
from conversations import (
    piechart_conv_handler, barchart_conv_handler,
    summary_conv_handler, details_conv_handler
)

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Start the bot."""
    init_db()

    application = Application.builder().token(BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("chart", chart_command))  # Keep legacy chart command

    # Register conversation handlers
    application.add_handler(piechart_conv_handler)
    application.add_handler(barchart_conv_handler)
    application.add_handler(summary_conv_handler)  # New interactive summary
    application.add_handler(details_conv_handler)  # New interactive details

    # Register message handler for expense tracking
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))

    logger.info("Bot is starting... Now open to all users.")
    application.run_polling()

if __name__ == "__main__":
    main()