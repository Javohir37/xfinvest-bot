"""Asset pricing functionality using Google GenAI client with streaming."""
import logging
from datetime import datetime
import json
import re
import asyncio
import io
from typing import Dict, List, Any

from google import genai
from google.genai import types
from db_assets import update_asset_value

logger = logging.getLogger(__name__)

async def get_current_asset_prices(assets: List[Dict]) -> List[Dict]:
    """Get current prices for all assets using Gemini API."""
    updated_assets = []

    for asset in assets:
        updated_asset = await get_current_price(asset)
        updated_assets.append(updated_asset)

    return updated_assets

async def get_current_price(asset: Dict) -> Dict:
    """Get current price for a single asset using Gemini API."""
    asset_id = asset['id']
    asset_name = asset['name']
    asset_ticker = asset['ticker']
    asset_type = asset['type']
    last_price = asset['current_price']

    # Create a copy of the asset dict that we can modify
    updated_asset = dict(asset)

    # Construct the query for price information
    query_text = f"current price of {asset_name}"
    if asset_ticker:
        query_text = f"current price of {asset_ticker} ({asset_name})"

    try:
        # Get response using the streaming approach
        response_text = await get_gemini_stream_response(query_text)

        # Try to extract a price from the response text
        price, source = extract_price_from_response(response_text, asset_name)

        if price is not None:
            today = datetime.now().strftime('%Y-%m-%d')

            # Record the price in the database
            update_asset_value(asset_id, price, today)

            # Update the asset dict
            updated_asset['current_price'] = price
            updated_asset['total_value'] = price * asset['quantity']
            updated_asset['price_source'] = source
            updated_asset['price_updated'] = today
            updated_asset['price_changed'] = (last_price != price)

            # Calculate price change information
            if last_price > 0:
                updated_asset['price_change'] = price - last_price
                updated_asset['price_change_pct'] = (price - last_price) / last_price * 100
            else:
                updated_asset['price_change'] = 0
                updated_asset['price_change_pct'] = 0

            logger.info(f"Updated {asset_name} price to ${price}")
        else:
            logger.warning(f"No reliable price found for {asset_name}")

    except Exception as e:
        logger.error(f"Error updating price for {asset_name}: {e}", exc_info=True)

    return updated_asset

async def get_gemini_stream_response(query: str) -> str:
    """Get streaming response from Gemini using exact user code structure."""
    # Run in executor to avoid blocking
    loop = asyncio.get_event_loop()
    response_text = await loop.run_in_executor(None,
                                              lambda: generate_stream_response(query))
    return response_text

def generate_stream_response(query: str) -> str:
    """Generate streaming response from Gemini using the user's exact code pattern."""
    # Using a string buffer to collect chunks
    buffer = io.StringIO()

    # Following the user's code structure exactly
    client = genai.Client(
        api_key="AIzaSyBxgWtRszQJYalspo_0CGFSCS6B96zVxq0",
    )

    model = "gemini-2.5-flash"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=query),
            ],
        ),
    ]
    tools = [
        types.Tool(googleSearch=types.GoogleSearch(
        )),
    ]
    generate_content_config = types.GenerateContentConfig(
        thinking_config = types.ThinkingConfig(
            thinking_budget=0,
        ),
        media_resolution="MEDIA_RESOLUTION_MEDIUM",
        tools=tools,
    )

    # Collect chunks into our buffer instead of printing
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        buffer.write(chunk.text)

    # Return the full response
    return buffer.getvalue()

def extract_price_from_response(response_text: str, asset_name: str) -> tuple:
    """Extract price and source information from Gemini response."""
    # Try to find a price in the response
    # First look for a clear pattern like $X,XXX.XX or X,XXX.XX USD
    price_patterns = [
        r'\$([0-9,]+\.[0-9]+)',
        r'([0-9,]+\.[0-9]+)\s*USD',
        r'([0-9,]+\.[0-9]+)\s*dollars',
        r'price is ([0-9,]+\.[0-9]+)',
        r'worth ([0-9,]+\.[0-9]+)',
        r'valued at ([0-9,]+\.[0-9]+)',
        r'price: \$?([0-9,]+\.[0-9]+)',
        r'([0-9,]+\.[0-9]+)'  # Last resort - find any number with decimal
    ]

    for pattern in price_patterns:
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
            # Found a price, clean it and convert to float
            price_str = match.group(1).replace(',', '')
            try:
                price = float(price_str)
                # Try to find the source
                source_match = re.search(r'according to ([^\.]+)', response_text, re.IGNORECASE)
                source = source_match.group(1) if source_match else "Market data"
                return price, source
            except ValueError:
                continue

    # If we couldn't find a price using patterns, try to find JSON
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            price = data.get('price')
            source = data.get('source', 'Market data')
            if price is not None:
                return float(price), source
        except:
            pass

    logger.warning(f"Could not extract price for {asset_name} from response: {response_text[:100]}...")
    return None, None