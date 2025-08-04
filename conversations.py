"""Conversation handlers for interactive bot commands"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)

from constants import TIME_RANGES
from chart_generator import generate_dual_pie_chart, generate_bar_chart
from db import get_transactions_summary, get_transactions_time_series, get_transactions_details

# Define conversation states
SELECT_TIMEFRAME = 0
SELECT_INTERVAL = 1

logger = logging.getLogger(__name__)

# --- Pie Chart Command Flow ---
async def piechart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the pie chart command flow by asking for timeframe."""
    user_id = update.effective_user.id if update.effective_user else "Unknown"
    logger.info(f"Received /piechart command from user {user_id}")

    keyboard = [
        [
            InlineKeyboardButton("Today", callback_data="timeframe_today"),
            InlineKeyboardButton("This Week", callback_data="timeframe_this_week")
        ],
        [
            InlineKeyboardButton("This Month", callback_data="timeframe_this_month"),
            InlineKeyboardButton("Last Month", callback_data="timeframe_last_month")
        ],
        [
            InlineKeyboardButton("Custom Range", callback_data="timeframe_custom")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📊 Please select a time range for your pie chart:",
        reply_markup=reply_markup
    )
    return SELECT_TIMEFRAME

async def piechart_timeframe_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle timeframe selection for pie chart."""
    query = update.callback_query
    await query.answer()

    # Extract the selected timeframe
    selected_timeframe = query.data.replace("timeframe_", "")

    if selected_timeframe == "custom":
        await query.edit_message_text(
            "📅 Please enter a custom date range in format:\n\n"
            "`from YYYY-MM-DD to YYYY-MM-DD`"
        )
        # Set state to expect a custom range input
        context.user_data["chart_type"] = "pie"
        return SELECT_TIMEFRAME

    # Process the built-in timeframe
    await query.edit_message_text("Generating your pie charts...")

    summary = get_transactions_summary(selected_timeframe)
    title = TIME_RANGES.get(selected_timeframe, selected_timeframe.replace("_", " ").title())
    chart_buffer = generate_dual_pie_chart(summary, title)

    if chart_buffer:
        await update.effective_chat.send_photo(
            photo=chart_buffer,
            caption=f"📊 Pie Charts ({title}) - Compare your actual spending with what might have been if you hadn't resisted those purchases!"
        )
        await query.delete_message()
    else:
        await query.edit_message_text(f"No data available for the selected period ({title}).")

    return ConversationHandler.END

# --- Bar Chart Command Flow ---
async def barchart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the bar chart command flow by asking for timeframe."""
    user_id = update.effective_user.id if update.effective_user else "Unknown"
    logger.info(f"Received /barchart command from user {user_id}")

    keyboard = [
        [
            InlineKeyboardButton("This Week", callback_data="timeframe_this_week"),
            InlineKeyboardButton("This Month", callback_data="timeframe_this_month")
        ],
        [
            InlineKeyboardButton("Last Month", callback_data="timeframe_last_month"),
            InlineKeyboardButton("3 Months", callback_data="timeframe_3months")
        ],
        [
            InlineKeyboardButton("Custom Range", callback_data="timeframe_custom")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📊 Please select a time range for your bar chart:",
        reply_markup=reply_markup
    )
    return SELECT_TIMEFRAME

async def barchart_timeframe_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle timeframe selection for bar chart."""
    query = update.callback_query
    await query.answer()

    # Extract the selected timeframe
    selected_timeframe = query.data.replace("timeframe_", "")
    context.user_data["selected_timeframe"] = selected_timeframe

    if selected_timeframe == "custom":
        await query.edit_message_text(
            "📅 Please enter a custom date range in format:\n\n"
            "`from YYYY-MM-DD to YYYY-MM-DD`"
        )
        # Set state to expect a custom range input
        context.user_data["chart_type"] = "bar"
        return SELECT_TIMEFRAME

    # Select appropriate interval options based on the timeframe
    keyboard = []

    if selected_timeframe == "today":
        # For "today," we don't need interval options - go straight to chart
        await query.edit_message_text("Generating your bar chart...")

        time_data = get_transactions_time_series(selected_timeframe, "day")
        title = TIME_RANGES.get(selected_timeframe, selected_timeframe.replace("_", " ").title())
        chart_buffer = generate_bar_chart(time_data, title, "day")

        if chart_buffer:
            await update.effective_chat.send_photo(
                photo=chart_buffer,
                caption=f"📊 Spending Today"
            )
            await query.delete_message()
        else:
            await query.edit_message_text(f"No data available for today.")

        return ConversationHandler.END

    elif selected_timeframe == "this_week":
        # For "this week," only "by day" makes sense
        keyboard = [[InlineKeyboardButton("By Day", callback_data="interval_day")]]

    elif selected_timeframe in ["this_month", "last_month"]:
        # For monthly views, "by day" and "by week" make sense
        keyboard = [
            [
                InlineKeyboardButton("By Day", callback_data="interval_day"),
                InlineKeyboardButton("By Week", callback_data="interval_week")
            ]
        ]

    elif selected_timeframe == "3months":
        # For longer ranges, all options make sense
        keyboard = [
            [
                InlineKeyboardButton("By Day", callback_data="interval_day"),
                InlineKeyboardButton("By Week", callback_data="interval_week"),
                InlineKeyboardButton("By Month", callback_data="interval_month")
            ]
        ]

    # If we've determined keyboard options, show them
    if keyboard:
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📊 How should I group the data?",
            reply_markup=reply_markup
        )
        return SELECT_INTERVAL
    else:
        # Fallback - use daily grouping
        await query.edit_message_text("Generating your bar chart...")

        time_data = get_transactions_time_series(selected_timeframe, "day")
        title = TIME_RANGES.get(selected_timeframe, selected_timeframe.replace("_", " ").title())
        chart_buffer = generate_bar_chart(time_data, title, "day")

        if chart_buffer:
            await update.effective_chat.send_photo(
                photo=chart_buffer,
                caption=f"📊 Spending Over Time ({title}, daily view)"
            )
            await query.delete_message()
        else:
            await query.edit_message_text(f"No data available for the selected period ({title}).")

        return ConversationHandler.END

async def barchart_interval_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle interval selection for bar chart."""
    query = update.callback_query
    await query.answer()

    # Extract the selected interval
    selected_interval = query.data.replace("interval_", "")
    selected_timeframe = context.user_data.get("selected_timeframe")

    await query.edit_message_text("Generating your bar chart...")

    time_data = get_transactions_time_series(selected_timeframe, selected_interval)
    title = TIME_RANGES.get(selected_timeframe, selected_timeframe.replace("_", " ").title())
    chart_buffer = generate_bar_chart(time_data, title, selected_interval)

    if chart_buffer:
        await update.effective_chat.send_photo(
            photo=chart_buffer,
            caption=f"📊 Spending Over Time ({title}, grouped by {selected_interval})"
        )
        await query.delete_message()
    else:
        await query.edit_message_text(f"No data available for the selected period ({title}).")

    return ConversationHandler.END

async def custom_range_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom date range input."""
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

    # Generate appropriate chart based on type
    if chart_type == "pie":
        await update.message.reply_text("Generating your pie charts...")

        summary = get_transactions_summary(custom_range)
        chart_buffer = generate_dual_pie_chart(summary, "Custom Range")

        if chart_buffer:
            await update.message.reply_photo(
                photo=chart_buffer,
                caption=f"📊 Pie Charts ({custom_range}) - Compare your actual spending with what might have been!"
            )
        else:
            await update.message.reply_text(f"No data available for {custom_range}.")

        return ConversationHandler.END

    elif chart_type == "bar":
        # For bar chart, we need to ask about interval
        keyboard = [
            [
                InlineKeyboardButton("By Day", callback_data="interval_day"),
                InlineKeyboardButton("By Week", callback_data="interval_week"),
                InlineKeyboardButton("By Month", callback_data="interval_month")
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

# --- New Summary Command Flow ---
async def summary_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the summary command flow by asking for timeframe."""
    user_id = update.effective_user.id if update.effective_user else "Unknown"
    logger.info(f"Received /summary command from user {user_id}")

    keyboard = [
        [
            InlineKeyboardButton("Today", callback_data="summary_timeframe_today"),
            InlineKeyboardButton("This Week", callback_data="summary_timeframe_this_week")
        ],
        [
            InlineKeyboardButton("This Month", callback_data="summary_timeframe_this_month"),
            InlineKeyboardButton("Last Month", callback_data="summary_timeframe_last_month")
        ],
        [
            InlineKeyboardButton("Custom Range", callback_data="summary_timeframe_custom")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📊 Please select a time range for your spending summary:",
        reply_markup=reply_markup
    )
    return SELECT_TIMEFRAME

async def summary_timeframe_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle timeframe selection for summary."""
    query = update.callback_query
    await query.answer()

    # Extract the selected timeframe
    selected_timeframe = query.data.replace("summary_timeframe_", "")

    if selected_timeframe == "custom":
        await query.edit_message_text(
            "📅 Please enter a custom date range in format:\n\n"
            "`from YYYY-MM-DD to YYYY-MM-DD`"
        )
        # Set state to expect a custom range input
        context.user_data["command_type"] = "summary"
        return SELECT_TIMEFRAME

    # Process the built-in timeframe
    await query.edit_message_text("Generating your summary...")

    summary = get_transactions_summary(selected_timeframe)
    title = TIME_RANGES.get(selected_timeframe, selected_timeframe.replace("_", " ").title())

    response = [f"🧾 *Summary ({title})*\n"]

    total_expenses = sum(summary['expenses_by_category'].values())
    response.append(f"💸 *Expenses: ${total_expenses:,.2f}*")
    if summary['expenses_by_category']:
        for category, amount in sorted(summary['expenses_by_category'].items(), key=lambda item: item[1], reverse=True):
            response.append(f"  - {category}: ${amount:,.2f}")

    response.append(f"\n🧘 *Resisted: ${summary['total_resisted']:,.2f}*")

    await query.edit_message_text("\n".join(response), parse_mode='Markdown')
    return ConversationHandler.END

# --- New Details Command Flow ---
async def details_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the details command flow by asking for timeframe."""
    user_id = update.effective_user.id if update.effective_user else "Unknown"
    logger.info(f"Received /details command from user {user_id}")

    keyboard = [
        [
            InlineKeyboardButton("Today", callback_data="details_timeframe_today"),
            InlineKeyboardButton("This Week", callback_data="details_timeframe_this_week")
        ],
        [
            InlineKeyboardButton("This Month", callback_data="details_timeframe_this_month"),
            InlineKeyboardButton("Last Month", callback_data="details_timeframe_last_month")
        ],
        [
            InlineKeyboardButton("Custom Range", callback_data="details_timeframe_custom")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📋 Please select a time range for your transaction details:",
        reply_markup=reply_markup
    )
    return SELECT_TIMEFRAME

async def details_timeframe_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle timeframe selection for details."""
    query = update.callback_query
    await query.answer()

    # Extract the selected timeframe
    selected_timeframe = query.data.replace("details_timeframe_", "")

    if selected_timeframe == "custom":
        await query.edit_message_text(
            "📅 Please enter a custom date range in format:\n\n"
            "`from YYYY-MM-DD to YYYY-MM-DD`"
        )
        # Set state to expect a custom range input
        context.user_data["command_type"] = "details"
        return SELECT_TIMEFRAME

    # Process the built-in timeframe
    await query.edit_message_text("Fetching your transaction details...")

    details = get_transactions_details(selected_timeframe)
    title = TIME_RANGES.get(selected_timeframe, selected_timeframe.replace("_", " ").title())

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

    message_text = "\n".join(response)

    # Check if message exceeds Telegram's 4096 character limit
    if len(message_text) > 4000:
        # Split into multiple messages
        await query.edit_message_text(
            f"🧾 *Detailed View ({title})*\n\n"
            f"_Your transaction list is very long. Sending it in multiple messages..._",
            parse_mode='Markdown'
        )

        # Send chunks of the message
        chunks = [response[0]]
        current_chunk = []
        current_length = 0

        for line in response[1:]:
            if current_length + len(line) + 1 > 3800:  # Leave some margin
                # Send current chunk
                await update.effective_chat.send_message(
                    "\n".join(current_chunk),
                    parse_mode='Markdown'
                )
                current_chunk = []
                current_length = 0

            current_chunk.append(line)
            current_length += len(line) + 1  # +1 for newline

        # Send any remaining chunk
        if current_chunk:
            await update.effective_chat.send_message(
                "\n".join(current_chunk),
                parse_mode='Markdown'
            )
    else:
        await query.edit_message_text(message_text, parse_mode='Markdown')

    return ConversationHandler.END

# --- Common Custom Range Handler ---
async def command_custom_range_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom date range input for summary and details."""
    message_text = update.message.text
    command_type = context.user_data.get("command_type")

    # Check for valid format
    if not message_text.startswith("from ") or " to " not in message_text:
        await update.message.reply_text(
            "⚠️ Invalid format. Please use format: `from YYYY-MM-DD to YYYY-MM-DD`\n"
            "For example: `from 2025-07-01 to 2025-07-31`"
        )
        return SELECT_TIMEFRAME

    custom_range = message_text  # This should be like "from 2025-07-01 to 2025-07-31"

    # Generate appropriate response based on command type
    if command_type == "summary":
        await update.message.reply_text("Generating your summary...")

        summary = get_transactions_summary(custom_range)

        response = [f"🧾 *Summary ({custom_range})*\n"]

        total_expenses = sum(summary['expenses_by_category'].values())
        response.append(f"💸 *Expenses: ${total_expenses:,.2f}*")
        if summary['expenses_by_category']:
            for category, amount in sorted(summary['expenses_by_category'].items(), key=lambda item: item[1], reverse=True):
                response.append(f"  - {category}: ${amount:,.2f}")

        response.append(f"\n🧘 *Resisted: ${summary['total_resisted']:,.2f}*")

        await update.message.reply_text("\n".join(response), parse_mode='Markdown')

    elif command_type == "details":
        await update.message.reply_text("Fetching your transaction details...")

        details = get_transactions_details(custom_range)

        response = [f"🧾 *Detailed View ({custom_range})*\n"]

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

        message_text = "\n".join(response)

        # Check if message exceeds Telegram's 4096 character limit
        if len(message_text) > 4000:
            # Split into multiple messages
            await update.message.reply_text(
                f"🧾 *Detailed View ({custom_range})*\n\n"
                f"_Your transaction list is very long. Sending it in multiple messages..._",
                parse_mode='Markdown'
            )

            # Send chunks of the message
            chunks = [response[0]]
            current_chunk = []
            current_length = 0

            for line in response[1:]:
                if current_length + len(line) + 1 > 3800:  # Leave some margin
                    # Send current chunk
                    await update.message.reply_text(
                        "\n".join(current_chunk),
                        parse_mode='Markdown'
                    )
                    current_chunk = []
                    current_length = 0

                current_chunk.append(line)
                current_length += len(line) + 1  # +1 for newline

            # Send any remaining chunk
            if current_chunk:
                await update.message.reply_text(
                    "\n".join(current_chunk),
                    parse_mode='Markdown'
                )
        else:
            await update.message.reply_text(message_text, parse_mode='Markdown')

    return ConversationHandler.END

async def cancel_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the chart conversation."""
    await update.message.reply_text("Command canceled.")
    return ConversationHandler.END

# --- Set up all conversation handlers ---
piechart_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("piechart", piechart_command)],
    states={
        SELECT_TIMEFRAME: [
            CallbackQueryHandler(piechart_timeframe_selected, pattern=r"^timeframe_"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, custom_range_input),
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_chart)],
    per_message=False
)

barchart_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("barchart", barchart_command)],
    states={
        SELECT_TIMEFRAME: [
            CallbackQueryHandler(barchart_timeframe_selected, pattern=r"^timeframe_"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, custom_range_input),
        ],
        SELECT_INTERVAL: [
            CallbackQueryHandler(barchart_interval_selected, pattern=r"^interval_"),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_chart)],
    per_message=False
)

summary_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("summary", summary_conversation)],
    states={
        SELECT_TIMEFRAME: [
            CallbackQueryHandler(summary_timeframe_selected, pattern=r"^summary_timeframe_"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, command_custom_range_input),
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_chart)],  # Reusing the same cancel handler
    per_message=False
)

details_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("details", details_conversation)],
    states={
        SELECT_TIMEFRAME: [
            CallbackQueryHandler(details_timeframe_selected, pattern=r"^details_timeframe_"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, command_custom_range_input),
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_chart)],  # Reusing the same cancel handler
    per_message=False
)