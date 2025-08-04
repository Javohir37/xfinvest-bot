import os
from google import genai
from google.genai import types
from constants import EXPENSE_CATEGORIES
from datetime import datetime

import re
import json
import logging

def parse_expense_message(message_text):
    """
    Send a prompt to Gemini to extract structured spending data from user input.
    Returns: JSON string from Gemini (the main bot will parse it).
    """
    today = datetime.now().strftime('%Y-%m-%d')
    categories_str = ", ".join(EXPENSE_CATEGORIES)

    prompt = f"""
Parse this user message about an expense or resisted spending.

User message: "{message_text}"

Extract:
- type: "expense" if money was spent, "resisted" if not spent
- amount_usd: amount in USD (convert if needed)
- category: one of [{categories_str}]
- date: YYYY-MM-DD (default to today: {today})

If info is missing, respond with:
{{
  "error": "not-enough-data",
  "explanation": "..."
}}

Otherwise, respond with only this JSON (no commentary):
{{
  "type": ...,
  "amount_usd": ...,
  "category": ...,
  "date": ...
}}
"""
    try:
        client = genai.Client(
                api_key="AIzaSyBxgWtRszQJYalspo_0CGFSCS6B96zVxq0",
        )

        model = "gemini-2.5-flash"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                ],
            ),
        ]
        tools = [
            types.Tool(googleSearch=types.GoogleSearch()),
        ]
        generate_content_config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_budget=0,
            ),
            tools=tools,
            system_instruction=[
                types.Part.from_text(text="You are an API backend for an expense tracker. Only output a single valid JSON object as specified. Never explain your answer, never include commentary."),
            ],
        )

        response = ""
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if hasattr(chunk, "text") and chunk.text:
                response += chunk.text
        return response.strip()
    except Exception as e:
        return f'''{{"error": "api-error", "explanation": "Gemini error: {str(e)}"}}'''


# Add this function to your gemini_parser.py file
async def extract_transaction(message_text):
    """Extract transaction information from message text using Gemini."""
    client = genai.Client(
        api_key="AIzaSyBxgWtRszQJYalspo_0CGFSCS6B96zVxq0",
    )

    model = "gemini-2.5-flash"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=f"""
Extract expense transaction information from this text: "{message_text}"

Extract:
1. Amount spent in USD (just the number)
2. Category (e.g., food, transport, entertainment)
3. Description of purchase
4. Date (use today's date if not specified: {datetime.now().strftime('%Y-%m-%d')})

Respond ONLY with a JSON array of transactions:
[{{
  "amount": numeric_amount,
  "category": "category_name",
  "description": "description of purchase",
  "date": "YYYY-MM-DD"
}}]

If no valid transaction can be extracted, return an empty array [].
                """),
            ],
        ),
    ]
    tools = [
        types.Tool(googleSearch=types.GoogleSearch(
        )),
    ]
    generate_content_config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_budget=0,
        ),
        media_resolution="MEDIA_RESOLUTION_MEDIUM",
        tools=tools,
    )

    # Collect response
    full_response = ""
    for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
    ):
        full_response += chunk.text

    # Parse the JSON response
    try:
        json_match = re.search(r'\[[\s\S]*\]', full_response)
        if not json_match:
            return []

        transactions = json.loads(json_match.group(0))
        return transactions
    except Exception as e:
        logger.error(f"Error extracting transaction: {e}")
        return []