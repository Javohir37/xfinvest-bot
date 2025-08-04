"""
Fix for the NLP classification issue in the finance bot
Add this code to your asset_nlp.py file or replace the relevant functions
"""

import re
import spacy
import logging
from datetime import datetime

# Initialize logging
logger = logging.getLogger(__name__)

# Load SpaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except:
    logger.warning("SpaCy model not found. Installing now...")
    import subprocess

    subprocess.call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")

# Define classification patterns
INVESTMENT_PATTERNS = [
    r'\b(?:bought|purchased|acquired|invested in|added)\b.*\b(?:shares?|stocks?|equity|bitcoin|ethereum|crypto|etfs?)\b',
    r'\b(?:stock|share|bond|etf|fund|reit)\b.*\b(?:purchase|buy|acquire)\b',
    r'\binvest(?:ed|ing)?\b.+\$([\d,]+(?:\.\d{1,2})?)',
    r'\b(?:bought|purchased|added)\s+(\d+)\s+(?:shares?|stocks?)',
]

EXPENSE_PATTERNS = [
    r'\b(?:spent|bought|paid|purchased)\b.*\b(?:food|lunch|dinner|breakfast|snack|grocery|restaurant|cafe)\b',
    r'\b(?:food|meal|restaurant|grocery|cafe|dining|takeout)\b.*\b(?:expense|cost|price|bill)\b',
    r'(?:spent|paid|cost)\s+\$?([\d,]+(?:\.\d{1,2})?)\s+(?:for|on)\s+(?:food|lunch|dinner|meal)',
    r'(?:restaurant|cafe|dining|food|grocery)\s+(?:bill|expense|receipt)\s+\$?([\d,]+(?:\.\d{1,2})?)'
]


def classify_user_input(text):
    """
    Classify user input into categories: investment, expense, or other
    Returns: category_name (str), confidence (float)
    """
    text = text.lower().strip()

    # Check for investment patterns
    for pattern in INVESTMENT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return "investment", 0.85

    # Check for expense patterns
    for pattern in EXPENSE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return "expense", 0.85

    # Use SpaCy for more nuanced classification
    doc = nlp(text)

    # Check for money mentions combined with context
    money_mentioned = any(ent.label_ == "MONEY" for ent in doc.ents)

    # Check for investment-related keywords
    investment_keywords = ["invest", "stock", "share", "bond", "portfolio", "asset", "etf", "fund", "reit"]
    expense_keywords = ["spend", "buy", "food", "lunch", "dinner", "restaurant", "grocery", "bill"]

    # Count keyword matches
    investment_score = sum(1 for token in doc if token.lemma_.lower() in investment_keywords)
    expense_score = sum(1 for token in doc if token.lemma_.lower() in expense_keywords)

    # Make classification decision
    if money_mentioned:
        if investment_score > expense_score:
            return "investment", 0.6
        elif expense_score > investment_score:
            return "expense", 0.6

    # Default to "other" if no clear classification
    return "other", 0.5


async def process_asset_input(text):
    """
    Enhanced function to first classify input before processing it as an asset
    Returns: success (bool), message (str)
    """
    # First classify the input
    category, confidence = classify_user_input(text)

    if category == "expense":
        # This should be handled by expense tracking, not asset tracking
        return False, "This appears to be an expense, not an investment. Use /add_expense for food and other expenses."

    elif category == "other":
        # Not clear what this input is
        return False, "I'm not sure if this is an investment. Please use a clearer format like 'Bought 10 shares of Apple at $150 on 2025-07-15'"

    # Continue with existing asset processing logic
    # ... (your existing asset extraction code) ...

    # For testing purposes, just return that it's recognized as an investment
    return True, f"Recognized as investment data. Processing: {text}"


# Add this to your message handler
async def handle_text_input(update, context):
    """Handle text input - route to appropriate processor based on classification"""
    text = update.message.text

    # Skip if it's a command
    if text.startswith('/'):
        return

    # Classify the input
    category, confidence = classify_user_input(text)

    if category == "investment":
        # Process as investment/asset
        success, response = await process_asset_input(text)
        await update.message.reply_text(response)

    elif category == "expense":
        # Suggest using expense command
        await update.message.reply_text(
            "This looks like an expense. Please use /add_expense command for tracking expenses like food."
        )

    else:
        # Generic response for unclassified input
        await update.message.reply_text(
            "I'm not sure what you want to do. You can use commands like /add_asset, /add_expense, or /help."
        )