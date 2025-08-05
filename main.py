#Main entry point for the finance tracker bot.
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters

import if_investment
from asset_handlers import add_asset_text_command
from asset_conversations import asset_text_conv_handler

from constants import BOT_TOKEN
from db import init_db
from handlers import (
    start_command, chart_command, process_message
)
from conversations import (
    piechart_command, barchart_command,  # Add these imports
    piechart_conv_handler, barchart_conv_handler,
    summary_conv_handler, details_conv_handler
)

# Import asset-related modules
from db_assets import init_asset_tables
from asset_handlers import (
    asset_worth_command, asset_piechart_command
)
from asset_conversations import (
    asset_barchart_command,  # Add this import
    asset_barchart_conv_handler, add_asset_conv_handler
)
# Comment out scheduler if you haven't installed apscheduler
# from scheduler import setup_scheduler

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    #Start the bot.
    # Initialize databases
    init_db()
    init_asset_tables()

    # Comment out scheduler if you haven't installed apscheduler
    # scheduler = setup_scheduler()

    application = Application.builder().token(BOT_TOKEN).build()

    # Register expense-related commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("chart", chart_command))  # Legacy command
    application.add_handler(asset_text_conv_handler)

    # Use the conversation handlers directly instead of adding separate command handlers
    # application.add_handler(CommandHandler("spending_piechart", piechart_command))
    # application.add_handler(CommandHandler("spending_barchart", barchart_command))

    # Register asset-related commands
    application.add_handler(CommandHandler("asset_worth", asset_worth_command))
    application.add_handler(CommandHandler("asset_piechart", asset_piechart_command))
    # application.add_handler(CommandHandler("asset_barchart", asset_barchart_command))

    # Register expense conversation handlers
    application.add_handler(piechart_conv_handler)
    application.add_handler(barchart_conv_handler)
    application.add_handler(summary_conv_handler)
    application.add_handler(details_conv_handler)

    # Register asset conversation handlers
    application.add_handler(asset_barchart_conv_handler)
    application.add_handler(add_asset_conv_handler)

    # Register message handler for expense tracking
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))

    logger.info("Bot is starting... Now open to all users.")
    application.run_polling()

if __name__ == "__main__":
    main()