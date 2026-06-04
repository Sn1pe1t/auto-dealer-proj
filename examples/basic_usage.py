"""
Пример использования библиотеки autodealer_core.
"""
import os
from autodealer_core import (
    init_db,
    get_car_info,
    finalize_sale,
    get_report,
    get_sales_list,
    get_sale_details
)

# Инициализировать БД
db_path = 'test_autodealer.db'
schema_path = '../autodealer_core/schema.sql'
init_data_path = '../db-proj-car-dealership/init_data.csv'

print("Инициализация БД...")
conn = init_db(db_path, schema_path, init_data_path)

# Получить информацию об автомобиле
print("\n--- Информация об автомобиле ---")
car_info = get_car_info(conn, car_id=1)
if car_info:
    print(f"Описание: {car_info['description']}")
    print(f"Цена: {car_info['price']:,.2f} руб.")
    print(f"В наличии: {car_info['stock']} шт.")
    print(f"Мощность: {car_info['power']} л.с.")
    print(f"Топливо: {car_info['fuel_type']}")

# Получить список продаж
print("\n--- Список продаж ---")
sales = get_sales_list(conn, limit=5)
for sale_id, date, customer, employee, amount, status in sales:
    status_str = "Готов к выдаче" if status == 1 else "Предзаказ" if status == 0 else "—"
    print(f"Заказ #{sale_id} | {date} | {customer} | {amount:,.2f} руб. | {status_str}")

# Получить детали продажи
if sales:
    print(f"\n--- Детали заказа #{sales[0][0]} ---")
    details = get_sale_details(conn, sales[0][0])
    for brand, model, year, engine, fuel, trans, drive, qty, price, subtotal, car_id, in_stock in details:
        print(f"{brand} {model} ({year)} × {qty} = {subtotal:,.2f} руб.")

# Получить отчет
print("\n--- Отчет по продажам ---")
from datetime import datetime
today = datetime.now().strftime("%Y-%m-%d")
report = get_report(conn, today)
if report:
    print(f"Отчет за {today}:")
    for car, qty, revenue in report:
        print(f"  {car}: {qty} шт. → {revenue:,.2f} руб.")
else:
    print(f"За {today} нет продаж")

# Закрыть подключение
conn.close()
print("\n✓ Готово!")
