#Command and message handlers for the expense tracker bot
import logging
import json
from telegram import Update
from telegram.ext import ContextTypes
from initial_parser import generate
from asset_nlp import process_asset_input

from constants import TIME_RANGES
from db import add_transaction, get_transactions_summary, get_transactions_details
from gemini_parser import parse_expense_message, extract_transaction
from chart_generator import generate_pie_chart
from utils import safe_reply, clean_json_response

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Sends a welcome message when the /start command is issued
    user_id = update.effective_user.id if update.effective_user else "Unknown"
    logger.info(f"Received /start command from user {user_id}")

    await safe_reply(update,
                     "👋 Welcome to your Finance Tracker!\n\n"
                     "SPENDING AND INVESTMENT TRACKING WITH AI:\n"
                     "Send messages like 'Bought coffee for 5€', 'Saved $10 by not buying pizza' or 'purchased 3 stopgame shares for 10 bucks each'.\n\n"
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
                     "if the bot is down or has some problems plese let me know at @JavohirXR or khatamov37@gmail.com"
                     "Thanks"
                     )

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Sends a summary of transactions
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

############################################

async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Process incoming messages as either expenses or assets

    message_text = update.message.text
    user_id = update.effective_user.id if update.effective_user else "Unknown"
    logger.info(f"Processing message from user {user_id}: {message_text}")

    statement1 = generate(message_text)

    if '1' in statement1:
        # Try processing as an asset first
        asset_success = await handle_potential_asset_message(update, context)
        if asset_success:
            return

        if not asset_success:
            await update.message.reply_text("I couldn't understand your message. "
                                            "Please try rephrasing or provide more details.")
            return

        for transaction in asset_success:
            add_transaction(transaction)
    else:
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
            await thinking_message.edit_text(
                "Sorry, I couldn't understand that. The response from the parser was invalid.")
        except Exception as e:
            logger.error(f"An error occurred in process_message: {e}", exc_info=True)
            await thinking_message.edit_text("An unexpected error occurred while processing your message.")

############################

async def handle_potential_asset_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages that might be about assets."""
    message_text = update.message.text

    await update.message.reply_text("Processing your investment information...")

    success, response = await process_asset_input(message_text)
    await update.message.reply_text(response)

    return success