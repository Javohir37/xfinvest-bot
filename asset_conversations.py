"""Conversation handlers for investment tracking."""
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)

from constants import TIME_RANGES
from db_assets import add_asset, get_net_worth_history
from asset_charts import generate_net_worth_bar_chart

# Add at the top with other imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler

from db_assets import add_asset
# Import the missing command handler
# Import the process_asset_input function
from asset_nlp import process_asset_input

from telegram.ext import CommandHandler, MessageHandler, filters, ConversationHandler
from asset_nlp import process_asset_input

logger = logging.getLogger(__name__)

# Define conversation states
SELECT_TIMEFRAME = 0
SELECT_INTERVAL = 1
SELECT_GROUPING = 2


# --- Asset Bar Chart Command Flow ---
async def asset_barchart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the asset bar chart flow by asking for timeframe."""
    user_id = update.effective_user.id if update.effective_user else "Unknown"
    logger.info(f"Received /asset_barchart command from user {user_id}")

    keyboard = [
        [
            InlineKeyboardButton("This Week", callback_data="asset_timeframe_this_week"),
            InlineKeyboardButton("This Month", callback_data="asset_timeframe_this_month")
        ],
        [
            InlineKeyboardButton("Last Month", callback_data="asset_timeframe_last_month"),
            InlineKeyboardButton("3 Months", callback_data="asset_timeframe_3months")
        ],
        [
            InlineKeyboardButton("Custom Range", callback_data="asset_timeframe_custom")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📊 Please select a time range for your net worth chart:",
        reply_markup=reply_markup
    )
    return SELECT_TIMEFRAME


async def asset_barchart_timeframe_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle timeframe selection for asset bar chart."""
    query = update.callback_query
    await query.answer()

    # Extract the selected timeframe
    selected_timeframe = query.data.replace("asset_timeframe_", "")
    context.user_data["selected_timeframe"] = selected_timeframe

    if selected_timeframe == "custom":
        await query.edit_message_text(
            "📅 Please enter a custom date range in format:\n\n"
            "`from YYYY-MM-DD to YYYY-MM-DD`"
        )
        # Set state to expect a custom range input
        context.user_data["chart_type"] = "asset_bar"
        return SELECT_TIMEFRAME

    # Select appropriate interval options based on the timeframe
    if selected_timeframe == "this_week":
        # For "this week," only "by day" makes sense
        keyboard = [[InlineKeyboardButton("By Day", callback_data="asset_interval_day")]]
    elif selected_timeframe in ["this_month", "last_month"]:
        # For monthly views, "by day" and "by week" make sense
        keyboard = [
            [
                InlineKeyboardButton("By Day", callback_data="asset_interval_day"),
                InlineKeyboardButton("By Week", callback_data="asset_interval_week")
            ]
        ]
    else:  # 3months
        # For longer ranges, all options make sense
        keyboard = [
            [
                InlineKeyboardButton("By Day", callback_data="asset_interval_day"),
                InlineKeyboardButton("By Week", callback_data="asset_interval_week"),
                InlineKeyboardButton("By Month", callback_data="asset_interval_month")
            ]
        ]

    # Show interval options
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "📊 How should I group the data?",
        reply_markup=reply_markup
    )
    return SELECT_INTERVAL


async def asset_barchart_interval_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle interval selection for asset bar chart."""
    query = update.callback_query
    await query.answer()

    # Extract the selected interval
    selected_interval = query.data.replace("asset_interval_", "")
    selected_timeframe = context.user_data.get("selected_timeframe")

    await query.edit_message_text("Generating your net worth chart...")

    net_worth_data = get_net_worth_history(selected_timeframe, selected_interval)
    title = TIME_RANGES.get(selected_timeframe, selected_timeframe.replace("_", " ").title())

    if not net_worth_data['dates']:
        await query.edit_message_text(
            "No net worth data available for this period. "
            "Make sure you've recorded asset values and expenses."
        )
        return ConversationHandler.END

    chart_buffer = generate_net_worth_bar_chart(net_worth_data, title, selected_interval)

    if chart_buffer:
        await update.effective_chat.send_photo(
            photo=chart_buffer,
            caption=f"📊 Net Worth Over Time ({title}, grouped by {selected_interval})"
        )
        await query.delete_message()
    else:
        await query.edit_message_text(f"No data available for the selected period ({title}).")

    return ConversationHandler.END


async def custom_asset_range_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom date range input for asset charts."""
    message_text = update.message.text
    chart_type = context.user_data.get("chart_type")

    # Check for valid format
    if not message_text.startswith("from ") or " to " not in message_text:
        await update.message.reply_text(
            "⚠️ Invalid format. Please use format: `from YYYY-MM-DD to YYYY-MM-DD`\n"
            "For example: `from 2025-07-01 to 2025-07-31`"
        )
        return SELECT_TIMEFRAME

    custom_range = message_text  # This should be like "from 2025-07-01 to 2025-07-31"

    if chart_type == "asset_bar":
        # For asset bar chart, we need to ask about interval
        keyboard = [
            [
                InlineKeyboardButton("By Day", callback_data="asset_interval_day"),
                InlineKeyboardButton("By Week", callback_data="asset_interval_week"),
                InlineKeyboardButton("By Month", callback_data="asset_interval_month")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Store the custom range
        context.user_data["selected_timeframe"] = custom_range

        await update.message.reply_text(
            "📊 How should I group the data?",
            reply_markup=reply_markup
        )
        return SELECT_INTERVAL

    # Fallback
    return ConversationHandler.END


# --- Add Asset Command Flow ---
async def add_asset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the add asset flow."""
    await update.message.reply_text(
        "📝 Let's add a new investment asset. What type of asset is it?\n\n"
        "Choose from: stock, crypto, real_estate, cash, other"
    )
    context.user_data['asset'] = {}
    return 'ASSET_TYPE'


async def asset_type_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process asset type and ask for name."""
    asset_type = update.message.text.lower()
    if asset_type not in ['stock', 'crypto', 'real_estate', 'cash', 'other']:
        await update.message.reply_text(
            "⚠️ Invalid asset type. Please choose from: stock, crypto, real_estate, cash, other"
        )
        return 'ASSET_TYPE'

    context.user_data['asset']['type'] = asset_type

    await update.message.reply_text(f"What's the name of this {asset_type}?")
    return 'ASSET_NAME'


async def asset_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process asset name and ask for ticker if applicable."""
    asset_name = update.message.text
    context.user_data['asset']['name'] = asset_name

    asset_type = context.user_data['asset']['type']

    if asset_type in ['stock', 'crypto']:
        await update.message.reply_text(
            f"What's the ticker symbol for {asset_name}? (Enter 'none' if not applicable)"
        )
        return 'ASSET_TICKER'
    else:
        context.user_data['asset']['ticker'] = None
        await update.message.reply_text(
            f"How much of this asset do you own? (quantity)"
        )
        return 'ASSET_QUANTITY'


async def asset_ticker_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process asset ticker and ask for quantity."""
    ticker = update.message.text

    if ticker.lower() == 'none':
        ticker = None

    context.user_data['asset']['ticker'] = ticker

    await update.message.reply_text(
        f"How much of this asset do you own? (quantity)"
    )
    return 'ASSET_QUANTITY'


async def asset_quantity_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process asset quantity and ask for purchase price."""
    try:
        quantity = float(update.message.text)
        context.user_data['asset']['quantity'] = quantity

        await update.message.reply_text(
            f"What was the purchase price per unit in USD?"
        )
        return 'ASSET_PRICE'
    except ValueError:
        await update.message.reply_text(
            "⚠️ Please enter a valid number for quantity."
        )
        return 'ASSET_QUANTITY'


async def asset_price_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process asset price and ask for purchase date."""
    try:
        price = float(update.message.text)
        context.user_data['asset']['purchase_price'] = price

        await update.message.reply_text(
            f"When did you purchase this asset? (YYYY-MM-DD format)"
        )
        return 'ASSET_DATE'
    except ValueError:
        await update.message.reply_text(
            "⚠️ Please enter a valid number for price."
        )
        return 'ASSET_PRICE'


async def asset_date_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process asset date and ask for notes."""
    date_text = update.message.text

    try:
        # Validate date format
        purchase_date = datetime.strptime(date_text, '%Y-%m-%d').strftime('%Y-%m-%d')
        context.user_data['asset']['purchase_date'] = purchase_date

        await update.message.reply_text(
            f"Any notes about this asset? (optional, type 'none' to skip)"
        )
        return 'ASSET_NOTES'
    except ValueError:
        await update.message.reply_text(
            "⚠️ Please enter a valid date in YYYY-MM-DD format."
        )
        return 'ASSET_DATE'


async def asset_notes_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process asset notes and finalize asset addition."""
    notes = update.message.text

    if notes.lower() == 'none':
        notes = None

    context.user_data['asset']['notes'] = notes

    # Save the asset
    asset_data = context.user_data['asset']
    asset_id = add_asset(asset_data)

    # Calculate total value
    total_value = asset_data['quantity'] * asset_data['purchase_price']

    # Format response
    ticker_text = f" [{asset_data['ticker']}]" if asset_data['ticker'] else ""

    await update.message.reply_text(
        f"✅ Added new {asset_data['type']} asset: {asset_data['name']}{ticker_text}\n\n"
        f"Quantity: {asset_data['quantity']}\n"
        f"Purchase Price: ${asset_data['purchase_price']:,.2f}\n"
        f"Total Value: ${total_value:,.2f}\n"
        f"Purchase Date: {asset_data['purchase_date']}"
    )

    # Clear user data
    context.user_data.clear()

    return ConversationHandler.END


async def cancel_asset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the asset addition process."""
    await update.message.reply_text("Asset addition canceled.")
    context.user_data.clear()
    return ConversationHandler.END


# --- Set up asset conversation handlers ---
asset_barchart_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("asset_barchart", asset_barchart_command)],
    states={
        SELECT_TIMEFRAME: [
            CallbackQueryHandler(asset_barchart_timeframe_selected, pattern=r"^asset_timeframe_"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, custom_asset_range_input),
        ],
        SELECT_INTERVAL: [
            CallbackQueryHandler(asset_barchart_interval_selected, pattern=r"^asset_interval_"),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_asset)],
    per_message=False
)

add_asset_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("add_asset", add_asset_command)],
    states={
        'ASSET_TYPE': [MessageHandler(filters.TEXT & ~filters.COMMAND, asset_type_received)],
        'ASSET_NAME': [MessageHandler(filters.TEXT & ~filters.COMMAND, asset_name_received)],
        'ASSET_TICKER': [MessageHandler(filters.TEXT & ~filters.COMMAND, asset_ticker_received)],
        'ASSET_QUANTITY': [MessageHandler(filters.TEXT & ~filters.COMMAND, asset_quantity_received)],
        'ASSET_PRICE': [MessageHandler(filters.TEXT & ~filters.COMMAND, asset_price_received)],
        'ASSET_DATE': [MessageHandler(filters.TEXT & ~filters.COMMAND, asset_date_received)],
        'ASSET_NOTES': [MessageHandler(filters.TEXT & ~filters.COMMAND, asset_notes_received)],
    },
    fallbacks=[CommandHandler("cancel", cancel_asset)],
    per_message=False
)


async def asset_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process natural language asset text."""
    if not context.user_data.get('expecting_asset_text'):
        return ConversationHandler.END

    # Clear the flag
    context.user_data.pop('expecting_asset_text')

    message_text = update.message.text

    # Process the asset description
    await update.message.reply_text("Processing your investment information...")
    success, response = await process_asset_input(message_text)

    await update.message.reply_text(response)

    if success:
        return ConversationHandler.END
    else:
        # If we couldn't extract all info, stay in this state for more input
        context.user_data['expecting_asset_text'] = True
        return 'EXPECT_ASSET_TEXT'

async def add_asset_text_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /add_asset_text command for natural language asset addition."""
    user_id = update.effective_user.id if update.effective_user else "Unknown"
    logger.info(f"Received /add_asset_text command from user {user_id}")

    await update.message.reply_text(
        "Please describe your investment in natural language.\n\n"
        "For example:\n"
        "- \"I bought 10 shares of Apple at $180 each yesterday\"\n"
        "- \"Purchased 0.5 Bitcoin for $45,000 on 2025-07-30\"\n"
        "- \"Added 5000 USD to my portfolio as cash\"\n\n"
        "Include the asset name, quantity, price, and date if possible."
    )

    # Set the conversation state
    context.user_data['expecting_asset_text'] = True
    return 'EXPECT_ASSET_TEXT'

# Add this conversation handler
asset_text_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("add_asset_text", add_asset_text_command)],
    states={
        'EXPECT_ASSET_TEXT': [MessageHandler(filters.TEXT & ~filters.COMMAND, asset_text_received)],
    },
    fallbacks=[CommandHandler("cancel", cancel_asset)],
    per_message=True
)


