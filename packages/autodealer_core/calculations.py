from typing import Dict, List, Tuple

def calculate_sale_items(
    cart_totals: Dict[int, int],          # car_id -> requested quantity
    stock_map: Dict[int, Tuple[int, float]]  # car_id -> (stock, price)
) -> List[Tuple[int, int, float, int]]:
    """
    Разбивает заказ на части: из наличия и предзаказ.
    Возвращает список (car_id, quantity, price_at_sale, in_stock_flag)
    """
    sale_items = []
    for car_id, requested in cart_totals.items():
        stock, price = stock_map[car_id]
        deduct = min(requested, stock)
        preorder = requested - deduct
        if deduct > 0:
            sale_items.append((car_id, deduct, price, 1))
        if preorder > 0:
            sale_items.append((car_id, preorder, price, 0))
    return sale_items

def total_amount(sale_items: List[Tuple[int, int, float, int]]) -> float:
    """Вычисляет общую сумму заказа по элементам sale_items."""
    return sum(qty * price for (_, qty, price, _) in sale_items)