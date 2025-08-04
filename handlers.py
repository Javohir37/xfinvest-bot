"""Command and message handlers for the expense tracker bot"""
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


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message when the /start command is issued."""
    user_id = update.effective_user.id if update.effective_user else "Unknown"
    logger.info(f"Received /start command from user {user_id}")

    await safe_reply(update,
                     "👋 Welcome to your Finance Tracker!\n\n"
                     "SPENDING TRACKING:\n"
                     "Send messages like 'Bought coffee for 5€' or 'Saved $10 by not buying pizza'.\n\n"
                     "SPENDING COMMANDS:\n"
                     "/summary - Interactive spending summary\n"
                     "/details - Interactive transaction details\n"
                     "/spending_piechart - Compare actual vs. potential spending\n"
                     "/spending_barchart - Spending over time\n\n"
                     "INVESTMENT TRACKING:\n"
                     "/add_asset - Add a new investment\n"
                     "/asset_worth - View current asset values\n"
                     "/asset_piechart - Asset distribution chart\n"
                     "/asset_barchart - Net worth history chart"
                     )

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a summary of transactions."""
    user_id = update.effective_user.id if update.effective_user else "Unknown"
    time_range_str = ' '.join(context.args) if context.args else 'today'
    logger.info(f"Received /summary command for range '{time_range_str}' from user {user_id}")
    summary = get_transactions_summary(time_range_str)

    title = TIME_RANGES.get(time_range_str, time_range_str.replace("_", " ").title())
    response = [f"🧾 *Summary ({title})*\n"]

    total_expenses = sum(summary['expenses_by_category'].values())
    response.append(f"💸 *Expenses: ${total_expenses:,.2f}*")
    if summary['expenses_by_category']:
        for category, amount in sorted(summary['expenses_by_category'].items(), key=lambda item: item[1], reverse=True):
            response.append(f"  - {category}: ${amount:,.2f}")

    response.append(f"\n🧘 *Resisted: ${summary['total_resisted']:,.2f}*")
    await safe_reply(update, "\n".join(response), parse_mode='Markdown')

async def details_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a detailed list of transactions."""
    user_id = update.effective_user.id if update.effective_user else "Unknown"
    time_range_str = ' '.join(context.args) if context.args else 'today'
    logger.info(f"Received /details command for range '{time_range_str}' from user {user_id}")
    details = get_transactions_details(time_range_str)

    title = TIME_RANGES.get(time_range_str, time_range_str.replace("_", " ").title())
    response = [f"🧾 *Detailed View ({title})*\n"]

    if details['expenses_by_category']:
        for category, items in sorted(details['expenses_by_category'].items()):
            response.append(f"*{category}*")
            for item in items:
                response.append(f"  - ${item['amount_usd']:,.2f} — _{item['source_text']}_")
    else:
        response.append("_No expenses recorded for this period._")

    if details['resisted']:
        response.append("\n*Resisted*")
        for item in details['resisted']:
            response.append(f"  - ${item['amount_usd']:,.2f} — _{item['source_text']}_")

    await safe_reply(update, "\n".join(response), parse_mode='Markdown')

async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates and sends a pie chart of transactions."""
    user_id = update.effective_user.id if update.effective_user else "Unknown"
    time_range_str = ' '.join(context.args) if context.args else 'today'
    logger.info(f"Received /chart command for range '{time_range_str}' from user {user_id}")

    # Send processing message
    thinking_message = None
    if update.message:
        thinking_message = await update.message.reply_text("Generating chart...")

    summary = get_transactions_summary(time_range_str)
    title = TIME_RANGES.get(time_range_str, time_range_str.replace("_", " ").title())
    chart_buffer = generate_pie_chart(summary, title)

    if chart_buffer:
        # Send the chart
        if update.message:
            await update.message.reply_photo(photo=chart_buffer)
            # Delete the thinking message if it exists
            if thinking_message:
                try:
                    await thinking_message.delete()
                except Exception:
                    pass
        elif update.callback_query:
            await update.callback_query.answer()
            # For callbacks, we can't easily send photos in the same chat, so just notify
            await update.callback_query.edit_message_text("Chart generated! Check the latest messages.")
            await update.effective_chat.send_photo(photo=chart_buffer)
    else:
        await safe_reply(update, "No data to display in a chart for this period.")


# Replace your existing process_message function with this version
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

    # Your existing expense response formatting code here


async def handle_potential_asset_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages that might be about assets."""
    message_text = update.message.text

    await update.message.reply_text("Processing your investment information...")

    success, response = await process_asset_input(message_text)
    await update.message.reply_text(response)

    return success