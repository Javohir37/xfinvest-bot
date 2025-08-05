import logging
import json
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
    #Processes natural language messages for expenses or resisted spending
    # Ensure we have a message to process
    if not update.message or not update.message.text:
        logger.warning("Received update with no message text")
        return

    message_text = update.message.text
    user_id = update.effective_user.id if update.effective_user else "Unknown"
    logger.info(f"Processing message '{message_text}' from user {user_id}")

    thinking_message = await update.message.reply_text("🧠 Thinking...")

    gemini_response_str = parse_expense_message(message_text)

    try:
        # Clean the response
        cleaned_str = clean_json_response(gemini_response_str)

        data = json.loads(cleaned_str)

        if "error" in data:
            await thinking_message.edit_text(f"😕 Error from parser: {data.get('explanation', 'Unknown error')}")
            return

        add_transaction(data, message_text)

        if data['type'] == 'expense':
            reply = f"✅ Expense recorded: ${data['amount_usd']:,.2f} for {data['category']}."
        else:
            reply = f"✅ Resisted spending recorded: Saved ${data['amount_usd']:,.2f} from {data['category']}."

        await thinking_message.edit_text(reply)

    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from Gemini: {gemini_response_str}")
        await thinking_message.edit_text("Sorry, I couldn't understand that. The response from the parser was invalid.")
    except Exception as e:
        logger.error(f"An error occurred in process_message: {e}", exc_info=True)
        await thinking_message.edit_text("An unexpected error occurred while processing your message.")