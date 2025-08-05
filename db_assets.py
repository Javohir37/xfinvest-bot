#Database functions for asset management.
import sqlite3
from datetime import datetime
from db import get_db_connection, parse_date_range


def init_asset_tables():
    #Initializes the asset-related database tables.
    conn = get_db_connection()
    cursor = conn.cursor()

    # Table for assets
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS assets
                   (
                       id             INTEGER PRIMARY KEY AUTOINCREMENT,
                       type           TEXT CHECK (type IN ('stock', 'crypto', 'real_estate', 'cash', 'other')) NOT NULL,
                       name           TEXT                                                                     NOT NULL,
                       ticker         TEXT,
                       quantity       REAL                                                                     NOT NULL,
                       purchase_price REAL                                                                     NOT NULL,
                       purchase_date  TEXT                                                                     NOT NULL,
                       notes          TEXT,
                       created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                   );
                   ''')

    # Table for tracking daily asset values
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS asset_values
                   (
                       id            INTEGER PRIMARY KEY AUTOINCREMENT,
                       asset_id      INTEGER NOT NULL,
                       current_price REAL    NOT NULL,
                       total_value   REAL    NOT NULL,
                       date          TEXT    NOT NULL,
                       created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                       FOREIGN KEY (asset_id) REFERENCES assets (id)
                   );
                   ''')

    # Table for daily net worth history
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS net_worth_history
                   (
                       id             INTEGER PRIMARY KEY AUTOINCREMENT,
                       date           TEXT NOT NULL UNIQUE,
                       total_assets   REAL NOT NULL,
                       total_expenses REAL NOT NULL,
                       net_worth      REAL NOT NULL,
                       created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                   );
                   ''')

    conn.commit()
    conn.close()


def add_asset(asset_data):
    #Adds a new asset to the portfolio.
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO assets (type, name, ticker, quantity, purchase_price, purchase_date, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (asset_data['type'], asset_data['name'], asset_data.get('ticker'), asset_data['quantity'],
         asset_data['purchase_price'], asset_data['purchase_date'], asset_data.get('notes'))
    )
    asset_id = cursor.lastrowid
    conn.commit()

    # Also record initial value
    record_asset_value(asset_id, asset_data['purchase_price'], asset_data['purchase_price'] * asset_data['quantity'],
                       asset_data['purchase_date'])

    conn.close()
    return asset_id


def update_asset_value(asset_id, current_price, date=None):
    #Updates the current value of an asset
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get asset quantity
    cursor.execute("SELECT quantity FROM assets WHERE id = ?", (asset_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return False

    quantity = row['quantity']
    total_value = quantity * current_price

    # Record the new value
    record_asset_value(asset_id, current_price, total_value, date)
    conn.close()

    return True


def record_asset_value(asset_id, current_price, total_value, date=None):
    #Records the current value of an asset
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO asset_values (asset_id, current_price, total_value, date) VALUES (?, ?, ?, ?)",
        (asset_id, current_price, total_value, date)
    )
    conn.commit()
    conn.close()


def record_net_worth(date=None):
    #Records the net worth for a specific date
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Calculate total assets
    cursor.execute("""
                   SELECT SUM(total_value) as total
                   FROM (SELECT asset_id, MAX(created_at) as latest
                         FROM asset_values
                         WHERE date <= ?
                         GROUP BY asset_id) as latest_entries
                            JOIN asset_values ON asset_values.asset_id = latest_entries.asset_id AND
                                                 asset_values.created_at = latest_entries.latest
                   """, (date,))

    total_assets_row = cursor.fetchone()
    total_assets = total_assets_row['total'] if total_assets_row and total_assets_row['total'] is not None else 0

    # Calculate total expenses (cumulative up to this date)
    cursor.execute(
        "SELECT SUM(amount_usd) as total FROM transactions WHERE type = 'expense' AND date <= ?",
        (date,)
    )
    total_expenses_row = cursor.fetchone()
    total_expenses = total_expenses_row['total'] if total_expenses_row and total_expenses_row[
        'total'] is not None else 0

    # Calculate net worth
    net_worth = total_assets - total_expenses

    # Insert or update the net worth record
    cursor.execute(
        "INSERT OR REPLACE INTO net_worth_history (date, total_assets, total_expenses, net_worth) VALUES (?, ?, ?, ?)",
        (date, total_assets, total_expenses, net_worth)
    )
    conn.commit()
    conn.close()


def get_assets():
    #Gets a list of all assets with their current values.
    conn = get_db_connection()
    cursor = conn.cursor()

    # For each asset, get the latest value
    cursor.execute("""
                   SELECT assets.id,
                          assets.type,
                          assets.name,
                          assets.ticker,
                          assets.quantity,
                          assets.purchase_price,
                          assets.purchase_date,
                          assets.notes,
                          asset_values.current_price,
                          asset_values.total_value
                   FROM assets
                            JOIN (SELECT asset_id, MAX(created_at) as latest_record
                                  FROM asset_values
                                  GROUP BY asset_id) as latest_values ON assets.id = latest_values.asset_id
                            JOIN asset_values ON latest_values.asset_id = asset_values.asset_id
                       AND latest_values.latest_record = asset_values.created_at
                   ORDER BY assets.type, assets.name
                   """)

    assets = cursor.fetchall()
    conn.close()

    return assets


def get_net_worth_history(time_range_str, interval='day'):
    """Gets net worth history for charts."""
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

    # Get net worth by date
    cursor.execute(f"""
        SELECT {group_by} as period, AVG(net_worth) as avg_worth, 
               AVG(total_assets) as avg_assets, AVG(total_expenses) as avg_expenses  
        FROM net_worth_history 
        WHERE date BETWEEN ? AND ?
        GROUP BY period
        ORDER BY period
    """, (start_date.isoformat(), end_date.isoformat()))

    data_by_period = {}
    for row in cursor.fetchall():
        data_by_period[row['period']] = {
            'net_worth': row['avg_worth'],
            'total_assets': row['avg_assets'],
            'total_expenses': row['avg_expenses']
        }

    conn.close()

    # Process dates similar to get_transactions_time_series
    all_periods = sorted(data_by_period.keys())

    # For nice display, convert period format if needed
    if interval == 'week':
        formatted_dates = []
        for period in all_periods:
            year, week = period.split('-')
            d = datetime.strptime(f'{year}-{week}-1', '%Y-%W-%w')
            formatted_dates.append(d.strftime('%Y-%m-%d'))
        dates = formatted_dates
    elif interval == 'month':
        dates = [f"{period}-01" for period in all_periods]
    else:
        dates = all_periods

    # Extract values
    net_worth = [data_by_period.get(period, {}).get('net_worth', 0) for period in all_periods]
    assets = [data_by_period.get(period, {}).get('total_assets', 0) for period in all_periods]
    expenses = [data_by_period.get(period, {}).get('total_expenses', 0) for period in all_periods]

    return {
        'dates': dates,
        'net_worth': net_worth,
        'assets': assets,
        'expenses': expenses
    }