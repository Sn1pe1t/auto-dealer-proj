from autodealer_core import aggregate_report, top_sales

def test_aggregate_report():
    details = [
        {'car_name': 'Toyota Camry', 'quantity': 2, 'revenue': 5000},
        {'car_name': 'BMW X5', 'quantity': 1, 'revenue': 3000},
        {'car_name': 'Toyota Camry', 'quantity': 1, 'revenue': 2500},
    ]
    report = aggregate_report(details)
    assert report[0] == ('Toyota Camry', 3, 7500)
    assert report[1] == ('BMW X5', 1, 3000)

def test_aggregate_report_empty():
    assert aggregate_report([]) == []

def test_top_sales():
    details = [
        {'car_name': 'A', 'quantity': 5, 'revenue': 100},
        {'car_name': 'B', 'quantity': 10, 'revenue': 200},
        {'car_name': 'C', 'quantity': 1, 'revenue': 50},
    ]
    top = top_sales(details, limit=2)
    assert top[0] == ('B', 10, 200)
    assert top[1] == ('A', 5, 100)

def test_top_sales_limit_greater_than_items():
    details = [{'car_name': 'A', 'quantity': 1, 'revenue': 10}]
    top = top_sales(details, limit=5)
    assert len(top) == 1