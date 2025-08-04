import sqlite3
import os
from datetime import date, timedelta, datetime


def get_db_connection():
    """Establishes a connection to the database."""
    conn = sqlite3.connect('expenses.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Initializes the database schema. This function is self-contained and
    is called only once when the bot starts.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS transactions
                   (
                       id          INTEGER PRIMARY KEY AUTOINCREMENT,
                       type        TEXT CHECK (type IN ('expense', 'resisted')) NOT NULL,
                       category    TEXT                                         NOT NULL,
                       amount_usd  REAL                                         NOT NULL,
                       date        TEXT                                         NOT NULL,
                       source_text TEXT                                         NOT NULL,
                       created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                   );
                   ''')
    conn.commit()
    conn.close()


def add_transaction(transaction_data, source_text):
    """Adds a parsed transaction to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO transactions (type, category, amount_usd, date, source_text) VALUES (?, ?, ?, ?, ?)",
        (transaction_data['type'], transaction_data['category'], transaction_data['amount_usd'],
         transaction_data['date'], source_text)
    )
    conn.commit()
    conn.close()


def parse_date_range(time_range_str):
    """Converts a string like 'this_week' into a start and end date."""
    today = date.today()

    # Map of predefined ranges
    range_mappings = {
        'today': (today, today),
        'this_week': (today - timedelta(days=today.weekday()), today),
        'this_month': (today.replace(day=1), today),
        '3months': (today - timedelta(days=90), today),
    }

    # Handle last_month specially
    if time_range_str == 'last_month':
        first_day_current_month = today.replace(day=1)
        last_day_last_month = first_day_current_month - timedelta(days=1)
        first_day_last_month = last_day_last_month.replace(day=1)
        return first_day_last_month, last_day_last_month

    # Handle predefined ranges
    if time_range_str in range_mappings:
        return range_mappings[time_range_str]

    # Handle custom date ranges like "from 2023-01-01 to 2023-01-31"
    if 'from' in time_range_str and 'to' in time_range_str:
        try:
            parts = time_range_str.split(' ')
            start_date_str = parts[parts.index('from') + 1]
            end_date_str = parts[parts.index('to') + 1]
            return date.fromisoformat(start_date_str), date.fromisoformat(end_date_str)
        except (ValueError, IndexError):
            return today, today  # Fallback

    return today, today  # Default fallback


def get_transactions_summary(time_range_str):
    """Queries the database for a summary of transactions."""
    start_date, end_date = parse_date_range(time_range_str)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Expenses
    cursor.execute(
        "SELECT category, SUM(amount_usd) as total FROM transactions WHERE type = 'expense' AND date BETWEEN ? AND ? GROUP BY category",
        (start_date.isoformat(), end_date.isoformat()))
    expenses_by_category = {row['category']: row['total'] for row in cursor.fetchall()}

    # Total Resisted
    cursor.execute("SELECT SUM(amount_usd) as total FROM transactions WHERE type = 'resisted' AND date BETWEEN ? AND ?",
                   (start_date.isoformat(), end_date.isoformat()))
    total_resisted_row = cursor.fetchone()
    total_resisted = total_resisted_row['total'] if total_resisted_row and total_resisted_row[
        'total'] is not None else 0

    conn.close()

    return {
        'expenses_by_category': expenses_by_category,
        'total_resisted': total_resisted
    }


def get_transactions_details(time_range_str):
    """Queries the database for a detailed list of transactions."""
    start_date, end_date = parse_date_range(time_range_str)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Expenses
    cursor.execute(
        "SELECT category, amount_usd, source_text FROM transactions WHERE type = 'expense' AND date BETWEEN ? AND ? ORDER BY category, created_at",
        (start_date.isoformat(), end_date.isoformat()))
    expenses = cursor.fetchall()

    # Resisted
    cursor.execute(
        "SELECT amount_usd, source_text FROM transactions WHERE type = 'resisted' AND date BETWEEN ? AND ? ORDER BY created_at",
        (start_date.isoformat(), end_date.isoformat()))
    resisted = cursor.fetchall()

    conn.close()

    expenses_by_category = {}
    for expense in expenses:
        category = expense['category']
        if category not in expenses_by_category:
            expenses_by_category[category] = []
        expenses_by_category[category].append(expense)

    return {
        'expenses_by_category': expenses_by_category,
        'resisted': resisted
    }


def get_transactions_time_series(time_range_str, interval='day'):
    """
    Gets transactions grouped by time for charts.

    Args:
        time_range_str: Time range specification
        interval: 'day', 'week', or 'month' for grouping

    Returns:
        Dictionary with dates, expenses, and resisted amounts
    """
    start_date, end_date = parse_date_range(time_range_str)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Format the date based on the interval
    if interval == 'day':
        date_format = '%Y-%m-%d'
        group_by = "date"
    elif interval == 'week':
        date_format = '%Y-%W'  # Year-Week number
        group_by = "strftime('%Y-%W', date)"
    else:  # month
        date_format = '%Y-%m'
        group_by = "strftime('%Y-%m', date)"

    # Get expenses by date
    cursor.execute(f"""
        SELECT {group_by} as period, SUM(amount_usd) as total 
        FROM transactions 
        WHERE type = 'expense' AND date BETWEEN ? AND ?
        GROUP BY period
        ORDER BY period
    """, (start_date.isoformat(), end_date.isoformat()))

    expenses_by_date = {}
    for row in cursor.fetchall():
        expenses_by_date[row['period']] = row['total']

    # Get resisted by date
    cursor.execute(f"""
        SELECT {group_by} as period, SUM(amount_usd) as total 
        FROM transactions 
        WHERE type = 'resisted' AND date BETWEEN ? AND ?
        GROUP BY period
        ORDER BY period
    """, (start_date.isoformat(), end_date.isoformat()))

    resisted_by_date = {}
    for row in cursor.fetchall():
        resisted_by_date[row['period']] = row['total']

    # Combine into a single dataset
    all_periods = sorted(set(list(expenses_by_date.keys()) + list(resisted_by_date.keys())))

    # For nice display, convert period format if needed
    if interval == 'week':
        # Convert YYYY-WW to dates representing the Monday of that week
        formatted_dates = []
        for period in all_periods:
            year, week = period.split('-')
            # Create a date for the first day of that week
            d = datetime.strptime(f'{year}-{week}-1', '%Y-%W-%w')
            formatted_dates.append(d.strftime('%Y-%m-%d'))
        dates = formatted_dates
    elif interval == 'month':
        # Add day to make a valid date
        dates = [f"{period}-01" for period in all_periods]
    else:
        dates = all_periods

    # Get values with 0 for missing dates
    expenses = [expenses_by_date.get(period, 0) for period in all_periods]
    resisted = [resisted_by_date.get(period, 0) for period in all_periods]

    conn.close()

    return {
        'dates': dates,
        'expenses': expenses,
        'resisted': resisted
    }


def get_transactions_summary_grouped(time_range_str, interval='day'):
    """Queries the database for a summary of transactions grouped by time intervals."""
    start_date, end_date = parse_date_range(time_range_str)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Format the date based on the interval
    if interval == 'day':
        date_format = '%Y-%m-%d'
        group_by = "date"
        label_format = '%b %d'  # Aug 04
    elif interval == 'week':
        date_format = '%Y-%W'  # Year-Week number
        group_by = "strftime('%Y-%W', date)"
        label_format = 'Week of %b %d'  # Week of Aug 01
    else:  # month
        date_format = '%Y-%m'
        group_by = "strftime('%Y-%m', date)"
        label_format = '%b %Y'  # Aug 2025

    # Expenses by time period and category
    cursor.execute(f"""
        SELECT {group_by} as period, category, SUM(amount_usd) as total 
        FROM transactions 
        WHERE type = 'expense' AND date BETWEEN ? AND ?
        GROUP BY period, category
        ORDER BY period, category
    """, (start_date.isoformat(), end_date.isoformat()))

    expenses_by_period = {}
    for row in cursor.fetchall():
        period = row['period']
        if period not in expenses_by_period:
            expenses_by_period[period] = {}
        expenses_by_period[period][row['category']] = row['total']

    # Total resisted by time period
    cursor.execute(f"""
        SELECT {group_by} as period, SUM(amount_usd) as total 
        FROM transactions 
        WHERE type = 'resisted' AND date BETWEEN ? AND ?
        GROUP BY period
        ORDER BY period
    """, (start_date.isoformat(), end_date.isoformat()))

    resisted_by_period = {}
    for row in cursor.fetchall():
        resisted_by_period[row['period']] = row['total']

    conn.close()

    # Format periods for display based on interval
    formatted_periods = {}
    for period in list(expenses_by_period.keys()) + list(resisted_by_period.keys()):
        if period not in formatted_periods:
            if interval == 'day':
                # Just use the date directly
                formatted_periods[period] = datetime.strptime(period, '%Y-%m-%d').strftime(label_format)
            elif interval == 'week':
                # Convert YYYY-WW to date representing Monday of that week
                year, week = period.split('-')
                d = datetime.strptime(f'{year}-{week}-1', '%Y-%W-%w')
                formatted_periods[period] = d.strftime(label_format)
            else:  # month
                # Add day to make a valid date
                d = datetime.strptime(f"{period}-01", '%Y-%m-%d')
                formatted_periods[period] = d.strftime(label_format)

    return {
        'expenses_by_period': expenses_by_period,
        'resisted_by_period': resisted_by_period,
        'formatted_periods': formatted_periods
    }


def get_transactions_details_grouped(time_range_str, interval='day'):
    """Queries the database for a detailed list of transactions grouped by time intervals."""
    start_date, end_date = parse_date_range(time_range_str)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Format the date based on the interval
    if interval == 'day':
        date_format = '%Y-%m-%d'
        group_by = "date"
        label_format = '%b %d'  # Aug 04
    elif interval == 'week':
        date_format = '%Y-%W'  # Year-Week number
        group_by = "strftime('%Y-%W', date)"
        label_format = 'Week of %b %d'  # Week of Aug 01
    else:  # month
        date_format = '%Y-%m'
        group_by = "strftime('%Y-%m', date)"
        label_format = '%b %Y'  # Aug 2025

    # Get all transactions for the period
    cursor.execute(
        f"SELECT {group_by} as period, type, category, amount_usd, date, source_text "
        f"FROM transactions WHERE date BETWEEN ? AND ? "
        f"ORDER BY period, type, category",
        (start_date.isoformat(), end_date.isoformat())
    )

    rows = cursor.fetchall()
    conn.close()

    # Group by period
    transactions_by_period = {}
    for row in rows:
        period = row['period']
        if period not in transactions_by_period:
            transactions_by_period[period] = {'expenses': [], 'resisted': []}

        if row['type'] == 'expense':
            transactions_by_period[period]['expenses'].append(dict(row))
        else:
            transactions_by_period[period]['resisted'].append(dict(row))

    # Format periods for display
    formatted_periods = {}
    for period in transactions_by_period.keys():
        if interval == 'day':
            # Just use the date directly
            formatted_periods[period] = datetime.strptime(period, '%Y-%m-%d').strftime(label_format)
        elif interval == 'week':
            # Convert YYYY-WW to date representing Monday of that week
            year, week = period.split('-')
            d = datetime.strptime(f'{year}-{week}-1', '%Y-%W-%w')
            formatted_periods[period] = d.strftime(label_format)
        else:  # month
            # Add day to make a valid date
            d = datetime.strptime(f"{period}-01", '%Y-%m-%d')
            formatted_periods[period] = d.strftime(label_format)

    return {
        'transactions_by_period': transactions_by_period,
        'formatted_periods': formatted_periods
    }