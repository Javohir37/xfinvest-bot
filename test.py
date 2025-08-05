import sqlite3
import random
from datetime import datetime, timedelta
import math

def generate_net_worth_history():
    #Generate mock data for net worth history table
    
    # Connect to the database
    conn = sqlite3.connect('expenses.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Make sure the table exists
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
    
    # Set start date to 2 years ago from today
    end_date = datetime(2025, 8, 4)  # Current date from input
    start_date = datetime(2023, 8, 4)
    
    # Initial values
    base_assets = 50000  # Starting with $50,000 in assets
    base_expenses = 20000  # Starting with $20,000 in expenses
    
    # Get existing dates to avoid duplicates
    cursor.execute("SELECT date FROM net_worth_history")
    existing_dates = set(row[0] for row in cursor.fetchall())
    
    # Generate data for each day
    current_date = start_date
    entries = []
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        
        # Skip if this date already exists in the database
        if date_str in existing_dates:
            current_date += timedelta(days=1)
            continue
            
        # Create realistic trends with:
        # - General upward trend for assets (savings growth)
        # - Weekend vs weekday expense patterns
        # - Monthly patterns (higher expenses at beginning/end of month)
        # - Seasonal patterns (holidays etc.)
        
        # Time factors
        days_passed = (current_date - start_date).days
        month = current_date.month
        day_of_week = current_date.weekday()  # 0-6 where 0 is Monday
        day_of_month = current_date.day
        
        # Asset growth - steady increase with some random fluctuations
        # About 5% annual growth plus fluctuations
        growth_factor = 1 + (0.05 * days_passed / 365)
        daily_fluctuation = random.uniform(-0.005, 0.008)  # -0.5% to +0.8% daily variation
        
        assets = base_assets * growth_factor * (1 + daily_fluctuation)
        
        # Add some seasonal patterns to assets (e.g., bonuses in December/January)
        if month == 12:
            assets *= random.uniform(1.02, 1.05)  # Year-end bonus
        elif month == 1 and day_of_month < 15:
            assets *= random.uniform(1.01, 1.03)  # New Year bonus/tax return
        
        # Expenses vary by:
        # - Weekends have higher expenses
        # - Beginning and end of month have higher expenses (rent, bills)
        # - Holiday seasons have higher expenses
        
        expense_base = base_expenses * (1 + (0.03 * days_passed / 365))  # Slight inflation
        
        # Weekend factor
        weekend_factor = 1.0
        if day_of_week >= 5:  # Weekend (Saturday and Sunday)
            weekend_factor = random.uniform(1.05, 1.15)
            
        # Month beginning/end factor (bills, rent)
        month_factor = 1.0
        if day_of_month <= 5 or day_of_month >= 25:
            month_factor = random.uniform(1.02, 1.08)
            
        # Holiday season factor
        holiday_factor = 1.0
        if (month == 11 and day_of_month >= 20) or (month == 12 and day_of_month <= 31):
            holiday_factor = random.uniform(1.05, 1.20)  # Thanksgiving & Christmas
        elif month == 7 and day_of_month >= 1 and day_of_month <= 15:
            holiday_factor = random.uniform(1.03, 1.10)  # Summer vacation
            
        # Combine all factors with some randomness
        expenses = expense_base * weekend_factor * month_factor * holiday_factor * random.uniform(0.95, 1.05)
        
        # Calculate net worth
        net_worth = assets - expenses
        
        # Add some market fluctuations to create more realistic data
        # We'll use a sine wave with increasing frequency and some noise
        market_fluctuation = math.sin(days_passed / 30) * 2000 + random.uniform(-1000, 1000)
        net_worth += market_fluctuation
        
        # Round to 2 decimal places
        assets = round(assets, 2)
        expenses = round(expenses, 2)
        net_worth = round(net_worth, 2)
        
        entries.append((date_str, assets, expenses, net_worth))
        current_date += timedelta(days=1)
    
    # Insert the data in batches
    cursor.executemany(
        "INSERT OR IGNORE INTO net_worth_history (date, total_assets, total_expenses, net_worth) VALUES (?, ?, ?, ?)",
        entries
    )
    
    conn.commit()
    print(f"Added {len(entries)} new entries to net_worth_history")
    conn.close()

if __name__ == "__main__":
    generate_net_worth_history()