import io
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime


def generate_asset_pie_chart(assets_data):
    #Generates a pie chart showing asset distribution with current prices.
    plt.figure(figsize=(10, 7))

    # Prepare data
    asset_names = []
    asset_values = []
    asset_colors = {
        'stock': '#FF9999',
        'crypto': '#66B2FF',
        'real_estate': '#99FF99',
        'cash': '#FFCC99',
        'other': '#CCCCFF'
    }
    colors = []

    for asset in assets_data:
        # Include current price in the label
        name = f"{asset['name']} (${asset['current_price']:,.2f})"
        if asset['ticker']:
            name += f" [{asset['ticker']}]"
        asset_names.append(name)
        asset_values.append(asset['total_value'])
        colors.append(asset_colors.get(asset['type'], '#CCCCCC'))

    # Create pie chart
    plt.pie(asset_values, labels=asset_names, autopct='%1.1f%%', startangle=90, colors=colors)
    plt.title('Asset Distribution')
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle

    # Save to buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    buffer.seek(0)
    plt.close()

    return buffer

def generate_net_worth_bar_chart(net_worth_data, title, interval):
    #Generates a bar chart showing net worth over time.
    plt.figure(figsize=(12, 7))

    # Prepare data
    dates = net_worth_data['dates']
    net_worth = net_worth_data['net_worth']
    assets = net_worth_data['assets']
    expenses = net_worth_data['expenses']

    # Format x-axis labels based on interval
    if interval == 'day':
        x_labels = [datetime.strptime(d, '%Y-%m-%d').strftime('%b %d') for d in dates]
    elif interval == 'week':
        x_labels = [f"Week of {datetime.strptime(d, '%Y-%m-%d').strftime('%b %d')}" for d in dates]
    else:  # month
        x_labels = [datetime.strptime(f"{d}", '%Y-%m-%d').strftime('%b %Y') for d in dates]

    # Create bar chart showing net worth
    x = np.arange(len(dates))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 7))
    ax.bar(x, net_worth, width, label='Net Worth', color='#4CAF50')

    # Add value labels
    for i, v in enumerate(net_worth):
        ax.text(i, v + 0.1, f"${v:,.0f}", ha='center', fontsize=8)

    # Add labels, title and legend
    ax.set_xlabel('Date')
    ax.set_ylabel('Value (USD)')
    ax.set_title(f'Net Worth Over Time ({title})')
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, rotation=45, ha='right')
    ax.legend()

    plt.tight_layout()

    # Save to buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    buffer.seek(0)
    plt.close()

    return buffer