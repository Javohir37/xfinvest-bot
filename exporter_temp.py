import sqlite3
import random
from datetime import datetime, timedelta

# Connect to database
conn = sqlite3.connect('expenses.db')
cursor = conn.cursor()



# Categories and common expenses for each
categories = {
    'Food': [
        ('Lunch at work', 8, 15),
        ('Dinner out', 15, 40),
        ('Coffee shop', 3, 8),
        ('Grocery shopping', 30, 120),
        ('Food delivery', 20, 45),
        ('Snacks', 2, 10),
        ('Breakfast', 5, 15)
    ],
    'Transport': [
        ('Uber ride', 10, 30),
        ('Bus fare', 1.5, 3),
        ('Gas for car', 20, 60),
        ('Parking fee', 5, 20),
        ('Train ticket', 15, 50),
        ('Car maintenance', 50, 300),
        ('Subway pass', 25, 40)
    ],
    'Housing': [
        ('Rent', 1200, 2200),
        ('Home repairs', 50, 300),
        ('Furniture', 100, 800),
        ('Home decor', 20, 150),
        ('Cleaning service', 50, 120),
        ('Household items', 10, 80),
        ('Mortgage payment', 1000, 2500)
    ],
    'Entertainment': [
        ('Movie tickets', 10, 20),
        ('Streaming subscription', 8, 18),
        ('Concert tickets', 40, 150),
        ('Video game', 30, 70),
        ('Bar/Drinks', 15, 60),
        ('Sports event', 30, 100),
        ('Music/Book purchase', 10, 30)
    ],
    'Healthcare': [
        ('Doctor visit', 20, 100),
        ('Prescription', 10, 60),
        ('Health insurance', 100, 500),
        ('Gym membership', 30, 80),
        ('Vitamins/Supplements', 15, 50),
        ('Therapy session', 80, 200),
        ('Dental care', 50, 300)
    ],
    'Shopping': [
        ('Clothing', 30, 150),
        ('Electronics', 50, 600),
        ('Shoes', 40, 120),
        ('Accessories', 15, 80),
        ('Gifts', 20, 100),
        ('Personal care products', 10, 50),
        ('Books', 12, 35)
    ],
    'Utilities': [
        ('Electricity bill', 50, 150),
        ('Water bill', 30, 90),
        ('Internet/Cable', 50, 120),
        ('Phone bill', 40, 100),
        ('Heating/Gas', 40, 120),
        ('Trash service', 20, 60),
        ('Streaming services', 10, 40)
    ],
    'Other': [
        ('Donation', 10, 100),
        ('Pet supplies', 20, 80),
        ('Education expense', 50, 300),
        ('Office supplies', 15, 60),
        ('Software subscription', 10, 50),
        ('Tax payment', 100, 1000),
        ('Miscellaneous', 5, 30)
    ]
}

# Resisted spending ideas
resisted_items = [
    ('Didn\'t buy that coffee today', 'Food', 4, 6),
    ('Skipped takeout food', 'Food', 15, 30),
    ('Made lunch at home instead of eating out', 'Food', 8, 15),
    ('Walked instead of taking an Uber', 'Transport', 8, 25),
    ('Didn\'t order that unnecessary Amazon item', 'Shopping', 20, 100),
    ('Passed on buying new headphones', 'Shopping', 80, 300),
    ('Resisted buying new clothes', 'Shopping', 40, 120),
    ('Skipped movie theater', 'Entertainment', 15, 30),
    ('Didn\'t go to that expensive concert', 'Entertainment', 60, 200),
    ('Used free gym instead of personal trainer', 'Healthcare', 50, 100),
    ('Found free alternative to paid app', 'Other', 5, 15),
    ('Used existing supplies instead of buying new ones', 'Other', 10, 50),
    ('Decided against upgrading phone', 'Shopping', 500, 1200),
    ('Made coffee at home instead of Starbucks', 'Food', 3, 6),
    ('Took public transport instead of taxi', 'Transport', 15, 40)
]

# Generate 3 months of data plus the current month
start_date = datetime(2025, 5, 1)
end_date = datetime(2025, 8, 4)  # Today's date

# Function to generate a transaction with random values
def generate_transaction(date_str, transaction_type='expense'):
    if transaction_type == 'expense':
        # 80% chance of expense, 20% chance of resisted
        category = random.choice(list(categories.keys()))
        item_options = categories[category]
        item, min_amount, max_amount = random.choice(item_options)
        amount = round(random.uniform(min_amount, max_amount), 2)
        created_at = f"{date_str} {random.randint(6, 22)}:{random.randint(0, 59)}:{random.randint(0, 59)}"
        return (transaction_type, category, amount, date_str, item, created_at)
    else:
        # Generate a resisted spending entry
        item, category, min_amount, max_amount = random.choice(resisted_items)
        amount = round(random.uniform(min_amount, max_amount), 2)
        created_at = f"{date_str} {random.randint(6, 22)}:{random.randint(0, 59)}:{random.randint(0, 59)}"
        return ('resisted', category, amount, date_str, item, created_at)

# Generate transactions
transactions = []
current_date = start_date
while current_date <= end_date:
    date_str = current_date.strftime('%Y-%m-%d')
    
    # For monthly bills and rent - add them on the 1st of the month
    if current_date.day == 1:
        # Rent
        rent_amount = round(random.uniform(1500, 2000), 2)
        rent_created = f"{date_str} 10:{random.randint(0, 59)}:{random.randint(0, 59)}"
        transactions.append(('expense', 'Housing', rent_amount, date_str, f'Rent payment for {current_date.strftime("%B")}', rent_created))
        
        # Utilities
        for util_type in ['Electricity bill', 'Internet/Cable', 'Phone bill']:
            category = 'Utilities'
            util_amount = round(random.uniform(50, 120), 2)
            util_created = f"{date_str} {random.randint(10, 17)}:{random.randint(0, 59)}:{random.randint(0, 59)}"
            transactions.append(('expense', category, util_amount, date_str, util_type, util_created))
    
    # Generate 3 regular transactions per day
    # Usually 2 expenses and 1 resisted (with some randomness)
    if random.random() < 0.8:  # 80% chance of 2 expenses and 1 resisted
        transactions.append(generate_transaction(date_str, 'expense'))
        transactions.append(generate_transaction(date_str, 'expense'))
        transactions.append(generate_transaction(date_str, 'resisted'))
    else:  # 20% chance of 3 expenses
        transactions.append(generate_transaction(date_str, 'expense'))
        transactions.append(generate_transaction(date_str, 'expense'))
        transactions.append(generate_transaction(date_str, 'expense'))
    
    # Weekend specific expenses
    if current_date.weekday() >= 5:  # Saturday or Sunday
        # Add entertainment expenses on weekends
        movie_amount = round(random.uniform(25, 80), 2)
        movie_created = f"{date_str} {random.randint(17, 22)}:{random.randint(0, 59)}:{random.randint(0, 59)}"
        transactions.append(('expense', 'Entertainment', movie_amount, date_str, 'Weekend entertainment', movie_created))
        
        # Large grocery runs often happen on weekends
        if random.random() < 0.5:  # 50% chance
            grocery_amount = round(random.uniform(80, 200), 2)
            grocery_created = f"{date_str} {random.randint(10, 16)}:{random.randint(0, 59)}:{random.randint(0, 59)}"
            transactions.append(('expense', 'Food', grocery_amount, date_str, 'Weekly grocery shopping', grocery_created))
    
    current_date += timedelta(days=1)

# Insert transactions into database
cursor.executemany(
    "INSERT INTO transactions (type, category, amount_usd, date, source_text, created_at) VALUES (?, ?, ?, ?, ?, ?)",
    transactions
)

# Commit changes and close connection
conn.commit()

# Verify import
cursor.execute("SELECT COUNT(*) FROM transactions")
count = cursor.fetchone()[0]

# Get some stats
cursor.execute("SELECT SUM(amount_usd) FROM transactions WHERE type = 'expense'")
total_expenses = cursor.fetchone()[0]
cursor.execute("SELECT SUM(amount_usd) FROM transactions WHERE type = 'resisted'")
total_resisted = cursor.fetchone()[0]

conn.close()

print(f"✅ Successfully imported {count} transactions into expenses.db!")
print(f"📊 Total expenses: ${total_expenses:.2f}")
print(f"🧘 Total resisted spending: ${total_resisted:.2f}")
print(f"🗓️ Date range: May 1, 2025 - August 4, 2025")