from collections import defaultdict
from typing import List, Dict, Union, Tuple

def aggregate_report(
    sales_details: List[Dict[str, Union[str, int, float]]]
) -> List[Tuple[str, int, float]]:
    """
    Агрегирует продажи по автомобилям.
    Ожидает список словарей с ключами: 'car_name', 'quantity', 'revenue'.
    Возвращает [(car_name, total_qty, total_revenue), ...] отсортированный по revenue DESC.
    """
    groups = defaultdict(lambda: {'qty': 0, 'revenue': 0.0})
    for d in sales_details:
        name = d['car_name']
        groups[name]['qty'] += d['quantity']
        groups[name]['revenue'] += d['revenue']
    result = [(name, data['qty'], data['revenue']) for name, data in groups.items()]
    result.sort(key=lambda x: x[2], reverse=True)
    return result

def top_sales(
    sales_details: List[Dict[str, Union[str, int, float]]],
    limit: int = 10
) -> List[Tuple[str, int, float]]:
    """
    Возвращает топ-10 автомобилей по количеству продаж.
    """
    groups = defaultdict(lambda: {'qty': 0, 'revenue': 0.0})
    for d in sales_details:
        name = d['car_name']
        groups[name]['qty'] += d['quantity']
        groups[name]['revenue'] += d['revenue']
    result = [(name, data['qty'], data['revenue']) for name, data in groups.items()]
    result.sort(key=lambda x: x[1], reverse=True)
    return result[:limit]