import os
from google import genai
from google.genai import types
from constants import EXPENSE_CATEGORIES
from datetime import datetime

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