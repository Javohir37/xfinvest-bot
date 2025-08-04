"""Utility functions for the expense tracker bot"""
import logging

logger = logging.getLogger(__name__)

async def safe_reply(update, text, parse_mode=None, **kwargs):
    """Safely reply to a message, handling cases where update.message might be None."""
    if update.message:
        return await update.message.reply_text(text, parse_mode=parse_mode, **kwargs)
    elif update.callback_query:
        await update.callback_query.answer()
        return await update.callback_query.edit_message_text(text, parse_mode=parse_mode, **kwargs)
    else:
        logger.error("Cannot reply: update has neither message nor callback_query")
        return None

def clean_json_response(response_str):
    """Clean JSON string from markdown code blocks."""
    cleaned_str = response_str.strip()
    if cleaned_str.startswith("```json"):
        cleaned_str = cleaned_str[7:]  # Remove ```json
    if cleaned_str.endswith("```"):
        cleaned_str = cleaned_str[:-3]  # Remove ```
    return cleaned_str.strip()