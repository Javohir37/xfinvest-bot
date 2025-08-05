#Command handlers for investment tracking functionality.
import logging
from telegram import Update
from telegram.ext import ContextTypes

from db_assets import get_assets
from asset_charts import generate_asset_pie_chart
from asset_pricing import get_current_asset_prices
from utils import safe_reply

logger = logging.getLogger(__name__)

async def asset_worth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Show current asset values with real-time pricing.
    user_id = update.effective_user.id if update.effective_user else "Unknown"
    logger.info(f"Received /asset_worth command from user {user_id}")

    await update.message.reply_text("Fetching your asset data and current market prices...")

    # Get all assets with their stored values
    assets = get_assets()

    if not assets:
        await update.message.reply_text(
            "You don't have any assets recorded. Use /add_asset to add your first investment."
        )
        return

    # Get real-time prices from Gemini
    updated_assets = await get_current_asset_prices(assets)

    # Group assets by type
    assets_by_type = {}
    total_value = 0

    for asset in updated_assets:
        asset_type = asset['type']
        if asset_type not in assets_by_type:
            assets_by_type[asset_type] = []
        assets_by_type[asset_type].append(asset)
        total_value += asset['total_value']

    # Build response
    response = ["📊 *Current Asset Portfolio*\n"]

    for asset_type, assets_list in assets_by_type.items():
        type_total = sum(a['total_value'] for a in assets_list)
        response.append(f"*{asset_type.title()} Assets: ${type_total:,.2f}*")

        for asset in assets_list:
            ticker_text = f" [{asset['ticker']}]" if asset['ticker'] else ""

            # Calculate gain/loss from purchase
            gain_loss = asset['current_price'] - asset['purchase_price']
            gain_loss_pct = (gain_loss / asset['purchase_price']) * 100 if asset['purchase_price'] > 0 else 0
            gain_loss_symbol = "📈" if gain_loss >= 0 else "📉"

            # Show price change if available
            price_change_text = ""
            if asset.get('price_changed'):
                change = asset.get('price_change', 0)
                pct = asset.get('price_change_pct', 0)
                change_symbol = "📈" if change >= 0 else "📉"
                price_change_text = f" | {change_symbol} {pct:+.2f}% today"

            response.append(
                f"  - {asset['name']}{ticker_text}: "
                f"${asset['total_value']:,.2f} "
                f"({asset['quantity']} x ${asset['current_price']:,.2f}) "
                f"{gain_loss_symbol} {gain_loss_pct:+.1f}% total{price_change_text}"
            )

    response.append(f"\n💰 *Total Portfolio Value: ${total_value:,.2f}*")
    response.append(f"\n_Prices updated automatically using AI market data_")

    await update.message.reply_text("\n".join(response), parse_mode='Markdown')

async def asset_piechart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Show asset distribution as pie chart with real-time pricing.
    user_id = update.effective_user.id if update.effective_user else "Unknown"
    logger.info(f"Received /asset_piechart command from user {user_id}")

    await update.message.reply_text("Getting current market prices and generating asset chart...")

    # Get all assets with their stored values
    assets = get_assets()

    if not assets:
        await update.message.reply_text(
            "You don't have any assets recorded. Use /add_asset to add your first investment."
        )
        return

    # Get real-time prices from Gemini
    updated_assets = await get_current_asset_prices(assets)

    # Generate pie chart with updated values
    chart_buffer = generate_asset_pie_chart(updated_assets)

    # Calculate total value
    total_value = sum(asset['total_value'] for asset in updated_assets)

    # Send the chart
    await update.message.reply_photo(
        photo=chart_buffer,
        caption=f"📊 Asset Distribution (Total Value: ${total_value:,.2f})\n\n_Prices updated automatically using AI market data_"
    )

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