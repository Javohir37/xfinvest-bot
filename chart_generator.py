import matplotlib.pyplot as plt
import io
from datetime import datetime, timedelta
import numpy as np


def generate_pie_chart(summary_data, title):
    """Generate a pie chart from transaction summary data."""
    expenses = summary_data.get('expenses_by_category', {})

    # If there's no expense data, don't generate a chart
    if not expenses:
        return None

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(10, 6))

    # Create the pie chart
    labels = list(expenses.keys())
    values = list(expenses.values())

    # Add resisted spending as a separate category if it exists
    total_resisted = summary_data.get('total_resisted', 0)
    if total_resisted > 0:
        labels.append('Resisted')
        values.append(total_resisted)

    # Plot with some nice styling
    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        autopct='%1.1f%%',
        startangle=90,
        shadow=True,
    )

    # Style the text
    for text in texts:
        text.set_fontsize(12)
    for autotext in autotexts:
        autotext.set_fontsize(10)
        autotext.set_color('white')

    # Equal aspect ratio ensures the pie chart is circular
    ax.axis('equal')

    plt.title(f'Spending Breakdown - {title}', fontsize=14)

    # Save to a buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)

    # Close the figure to free up memory
    plt.close(fig)

    return buffer


def generate_dual_pie_chart(summary_data, title):
    """Generate two pie charts: actual spending and hypothetical with resisted included."""
    expenses = summary_data.get('expenses_by_category', {})
    resisted = summary_data.get('total_resisted', 0)

    # If there's no data, don't generate a chart
    if not expenses and resisted == 0:
        return None

    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

    # First pie chart: Actual spending
    if expenses:
        labels1 = list(expenses.keys())
        values1 = list(expenses.values())

        wedges1, texts1, autotexts1 = ax1.pie(
            values1,
            labels=labels1,
            autopct='%1.1f%%',
            startangle=90,
            shadow=True,
        )

        # Style the text for first chart
        for text in texts1:
            text.set_fontsize(10)
        for autotext in autotexts1:
            autotext.set_fontsize(8)
            autotext.set_color('white')
    else:
        ax1.text(0.5, 0.5, "No expenses", ha='center', va='center', fontsize=14)

    ax1.set_title('Actual Spending', fontsize=14)
    ax1.axis('equal')

    # Second pie chart: Hypothetical including resisted
    if expenses or resisted > 0:
        labels2 = list(expenses.keys())
        values2 = list(expenses.values())

        # Add resisted as a category
        if resisted > 0:
            labels2.append('Resisted (Not Spent)')
            values2.append(resisted)

        wedges2, texts2, autotexts2 = ax2.pie(
            values2,
            labels=labels2,
            autopct='%1.1f%%',
            startangle=90,
            shadow=True,
        )

        # Style the text for second chart
        for text in texts2:
            text.set_fontsize(10)
        for autotext in autotexts2:
            autotext.set_fontsize(8)
            autotext.set_color('white')
    else:
        ax2.text(0.5, 0.5, "No data", ha='center', va='center', fontsize=14)

    ax2.set_title('Hypothetical (If Resisted Was Spent)', fontsize=14)
    ax2.axis('equal')

    plt.suptitle(f'Spending Analysis - {title}', fontsize=16)
    plt.tight_layout()

    # Save to a buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)

    # Close the figure to free up memory
    plt.close(fig)

    return buffer


def generate_bar_chart(time_data, title, interval='day'):
    """
    Generate a bar chart showing expenses and resisted spending over time.

    Args:
        time_data: Dictionary with dates, expenses, and resisted amounts
        title: Chart title
        interval: Grouping interval ('day', 'week', or 'month')

    Returns:
        BytesIO buffer with the chart image
    """
    if not time_data or not time_data.get('dates'):
        return None

    dates = time_data.get('dates', [])
    expenses = time_data.get('expenses', [])
    resisted = time_data.get('resisted', [])

    # Ensure we have data to display
    if len(dates) == 0:
        return None

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 7))

    # Set width of bars
    width = 0.35

    # Set positions of bars on x-axis
    x_pos = np.arange(len(dates))

    # Create bars
    expense_bars = ax.bar(x_pos - width / 2, expenses, width, label='Spent', color='#FF6B6B')
    resisted_bars = ax.bar(x_pos + width / 2, resisted, width, label='Resisted', color='#4ECDC4')

    # Format x-ticks with date labels
    date_labels = []
    for date_str in dates:
        try:
            if interval == 'day':
                # Just show month and day
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                date_labels.append(dt.strftime('%b %d'))
            elif interval == 'week':
                # Show as week starting date
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                date_labels.append(f'Week of {dt.strftime("%b %d")}')
            elif interval == 'month':
                # Show month and year
                if len(date_str) >= 7:  # Ensure we have YYYY-MM
                    year_month = date_str[:7]  # Get YYYY-MM part
                    dt = datetime.strptime(year_month, '%Y-%m')
                    date_labels.append(dt.strftime('%b %Y'))
                else:
                    date_labels.append(date_str)
        except ValueError:
            # Fallback if parsing fails
            date_labels.append(date_str)

    plt.xticks(x_pos, date_labels, rotation=45)

    # Add labels and legend
    ax.set_xlabel('Time Period')
    ax.set_ylabel('Amount (USD)')
    ax.set_title(f'Spending Over Time - {title}', fontsize=14)
    ax.legend()

    # Add values on top of bars
    for i, v in enumerate(expenses):
        if v > 0:
            ax.text(i - width / 2, v + 0.5, f'${v:.1f}', ha='center', fontsize=8)

    for i, v in enumerate(resisted):
        if v > 0:
            ax.text(i + width / 2, v + 0.5, f'${v:.1f}', ha='center', fontsize=8)

    plt.tight_layout()

    # Save to a buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)

    # Close the figure to free up memory
    plt.close(fig)

    return buffer