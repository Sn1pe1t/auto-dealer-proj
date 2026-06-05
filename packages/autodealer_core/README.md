# autodealer-core

Core business logic for a car dealership management system.

## Features

- `calculate_sale_items` – split order into in‑stock and preorder parts.
- `total_amount` – compute total price.
- `aggregate_report` – group sales by car model and sort by revenue.
- `top_sales` – get top N cars by quantity sold.

## Installation

pip install autodealer-core

## Usage

from autodealer_core import calculate_sale_items, total_amount

cart_totals = {1: 5, 2: 2}
stock_map = {1: (3, 100), 2: (10, 200)}
items = calculate_sale_items(cart_totals, stock_map)
total = total_amount(items)
print(total)  # 900