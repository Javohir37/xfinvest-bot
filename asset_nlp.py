"""Process asset information from natural language using Gemini."""
import logging
import asyncio
import json
import re
from datetime import datetime

from google import genai
from google.genai import types
from db_assets import add_asset

logger = logging.getLogger(__name__)

async def process_asset_input(user_text):
    """Process user input about assets using Gemini."""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: gemini_process_asset(user_text))
    return result

def gemini_process_asset(user_text):
    """
    Process asset text with Gemini and return structured data.
    Uses the exact Gemini implementation from the user.
    """
    full_response = ""

    client = genai.Client(
        api_key="AIzaSyBxgWtRszQJYalspo_0CGFSCS6B96zVxq0",
    )

    model = "gemini-2.5-flash"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=f"""
You're a financial assistant. Extract asset information from this text:
"{user_text}"

Extract:
1. Asset type (stock, crypto, real_estate, cash, other)
2. Asset name (e.g. Tesla, Bitcoin)
3. Quantity (how many shares/coins/units)
4. Purchase price per unit in USD
5. Purchase date (assume today: {datetime.now().strftime('%Y-%m-%d')} if not mentioned)
6. Any notes or additional information

Respond ONLY with a JSON object:
{{
  "type": "stock|crypto|real_estate|cash|other",
  "name": "name of the asset",
  "quantity": numeric_quantity,
  "purchase_price": numeric_price_in_usd,
  "purchase_date": "YYYY-MM-DD",
  "notes": "any additional info",
  "is_complete": true|false,
  "missing_info": ["field1", "field2"],
  "feedback": "message about missing info"
}}

Set is_complete to false if any required field (type, name, quantity, price) is missing.
                """),
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

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        full_response += chunk.text

    # Parse the JSON response
    try:
        # Try to extract JSON from the response
        json_match = re.search(r'\{[\s\S]*\}', full_response)
        if not json_match:
            return False, "I couldn't process your asset information. Please try again."

        parsed_data = json.loads(json_match.group(0))

        # Check if we have complete data
        is_complete = parsed_data.get('is_complete', False)

        if is_complete:
            # Add asset to database
            asset_data = {
                'type': parsed_data.get('type'),
                'name': parsed_data.get('name'),
                'ticker': None,  # No ticker as per requirements
                'quantity': parsed_data.get('quantity'),
                'purchase_price': parsed_data.get('purchase_price'),
                'purchase_date': parsed_data.get('purchase_date'),
                'notes': parsed_data.get('notes')
            }

            asset_id = add_asset(asset_data)
            total_value = asset_data['quantity'] * asset_data['purchase_price']

            return True, f"✅ Added new {asset_data['type']} asset: {asset_data['name']}\n\n" + \
                   f"Quantity: {asset_data['quantity']}\n" + \
                   f"Purchase Price: ${asset_data['purchase_price']:,.2f}\n" + \
                   f"Total Value: ${total_value:,.2f}\n" + \
                   f"Purchase Date: {asset_data['purchase_date']}"
        else:
            # Return feedback about missing information
            missing = parsed_data.get('missing_info', [])
            feedback = parsed_data.get('feedback', f"Please provide more information: {', '.join(missing)}")
            return False, feedback

    except Exception as e:
        logger.error(f"Error processing asset data: {e}", exc_info=True)
        return False, "I encountered an error processing your asset information. Please try again."