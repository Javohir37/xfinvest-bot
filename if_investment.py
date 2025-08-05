import json
import logging
from telegram import Update
from telegram.ext import ContextTypes

from asset_nlp import process_asset_input

from constants import TIME_RANGES
from db import add_transaction, get_transactions_summary, get_transactions_details
from gemini_parser import parse_expense_message
from chart_generator import generate_pie_chart
from utils import safe_reply, clean_json_response

logger = logging.getLogger(__name__)

async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process incoming messages as either expenses or assets."""
    message_text = update.message.text
    user_id = update.effective_user.id if update.effective_user else "Unknown"
    logger.info(f"Processing message from user {user_id}: {message_text}")

    # Check if the message contains common investment keywords
    investment_keywords = ['bought', 'purchased', 'shares', 'stock', 'bitcoin', 'crypto',
                           'investment', 'invested', 'asset']

    if any(keyword in message_text.lower() for keyword in investment_keywords):
        # Try processing as an asset first
        asset_success = await handle_potential_asset_message(update, context)
        if asset_success:
            return

    # If not an asset or asset processing failed, process as an expense
    await update.message.reply_text("Analyzing your expense...")

    transactions = await extract_transaction(message_text)

    if not transactions:
        await update.message.reply_text("I couldn't understand your message. "
                                        "Please try rephrasing or provide more details.")
        return

    for transaction in transactions:
        add_transaction(transaction)