# AutoDealer Core

Библиотека для управления системой автосалона. Содержит бизнес-логику и работу с базой данных.

## Установка

### Вариант 1: Установка из локального пути (разработка)

```bash
pip install -e .
```

### Вариант 2: Установка из PyPI (когда будет опубликована)

```bash
pip install autodealer-core
```

### Вариант 3: Через requirements.txt

```bash
pip install -r requirements.txt
```

## Использование

### 1. Инициализация БД

```python
from autodealer_core import init_db

# Инициализировать БД с схемой и начальными данными
conn = init_db(
    db_path='autodealer.db',
    schema_path='path/to/schema.sql',
    init_data_path='path/to/init_data.csv'
)
```

### 2. Получить информацию об автомобиле

```python
from autodealer_core import get_car_info

info = get_car_info(conn, car_id=1)
print(info['description'], info['price'])
```

### 3. Оформить продажу

```python
from autodealer_core import finalize_sale

cart_items = [
    {'car_id': 1, 'quantity': 2, 'price_at_sale': 500000},
    {'car_id': 2, 'quantity': 1, 'price_at_sale': 750000},
]

success, result = finalize_sale(conn, cart_items, employee_id=1, customer_id=5)
if success:
    print(f"Продажа #{result} успешно оформлена")
else:
    print(f"Ошибка: {result}")
```

### 4. Получить отчет по продажам

```python
from autodealer_core import get_report

report = get_report(conn, '2026-06-04')
for car_name, qty, revenue in report:
    print(f"{car_name}: {qty} шт. → {revenue:,.2f} руб.")
```

### 5. Получить список продаж

```python
from autodealer_core import get_sales_list, get_sale_details

sales = get_sales_list(conn, limit=50)
for sale_id, date, customer, employee, amount, status in sales:
    print(f"Заказ #{sale_id}: {customer} ({employee}) - {amount:,.2f} руб.")
    
    # Детали продажи
    details = get_sale_details(conn, sale_id)
    for brand, model, year, engine, fuel, trans, drive, qty, price, subtotal, car_id, in_stock in details:
        print(f"  {brand} {model} ({year}): {qty} шт. → {subtotal:,.2f} руб.")
```

## Структура

```
autodealer_core/
├── __init__.py           # Экспортирует функции для импорта
├── database.py           # Инициализация и загрузка БД
├── models.py             # Бизнес-логика (CRUD операции)
└── schema.sql            # SQL схема базы данных
```

## API

### database.py

- `init_db(db_path, schema_path, init_data_path)` — Инициализировать БД
- `load_initial_data(conn, csv_file)` — Загрузить начальные данные из CSV

### models.py

- `get_car_info(conn, car_id)` — Получить информацию об автомобиле
- `finalize_sale(conn, cart_items, id_employee, id_customer)` — Оформить продажу
- `get_report(conn, date_str)` — Получить отчет по продажам на дату
- `get_sales_list(conn, limit=50)` — Получить список продаж
- `get_sale_details(conn, sale_id)` — Получить детали продажи

## Примеры использования в приложении

Смотрите `db-proj-car-dealership/autodealer_app.py` для полного примера использования с GUI на Tkinter.

## Версионирование

Текущая версия: **0.1.0**

## Лицензия

MIT

## Разработка

Для внесения изменений:

1. Создайте ветку: `git checkout -b feature/my-feature`
2. Внесите изменения и добавьте тесты
3. Запустите: `make lint`
4. Создайте Pull Request

## Публикация на PyPI

```bash
# Установить инструменты сборки
pip install build twine

# Собрать пакет
python -m build

# Загрузить на PyPI
twine upload dist/*
```
