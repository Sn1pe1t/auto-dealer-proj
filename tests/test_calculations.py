from autodealer_core import calculate_sale_items, total_amount

def test_calculate_sale_items():
    cart = {1: 5, 2: 2}
    stock = {1: (3, 100), 2: (10, 200)}
    items = calculate_sale_items(cart, stock)
    assert items == [(1, 3, 100, 1), (1, 2, 100, 0), (2, 2, 200, 1)]

def test_calculate_sale_items_empty_cart():
    assert calculate_sale_items({}, {}) == []

def test_total_amount():
    items = [(1, 3, 100, 1), (1, 2, 100, 0), (2, 2, 200, 1)]
    assert total_amount(items) == 3*100 + 2*100 + 2*200 == 900

def test_total_amount_empty():
    assert total_amount([]) == 0