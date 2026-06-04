"""
Модель данных и бизнес-логика для автосалона.
Содержит функции для работы с автомобилями, продажами и отчетами.
"""
from datetime import datetime
from collections import defaultdict


def get_car_info(conn, car_id):
    """
    Получает полную информацию об автомобиле по ID.
    
    Args:
        conn: Подключение к БД
        car_id: ID автомобиля
    
    Returns:
        dict: Словарь с информацией об автомобиле или None, если не найден
    """
    row = conn.execute("""
        SELECT c.brand, c.model, c.year, c.color, c.price, c.quantity,
               st.name, c.power, c.engine_volume,
               ft.name, t.name, d.name, cond.name, c.mileage
        FROM cars c
        LEFT JOIN steering_types st ON c.id_steering = st.id
        LEFT JOIN fuel_types ft ON c.id_fuel_type = ft.id
        LEFT JOIN transmissions t ON c.id_transmission = t.id
        LEFT JOIN drives d ON c.id_drive = d.id
        LEFT JOIN conditions cond ON c.id_condition = cond.id
        WHERE c.id = ?
    """, (car_id,)).fetchone()
    
    if row:
        info = {
            "description": f"{row[0]} {row[1]}",
            "year": row[2],
            "color": row[3],
            "price": row[4],
            "stock": row[5],
            "steering": "Левый" if row[6] == 'left' else "Правый",
            "power": row[7],
            "engine_volume": row[8],
            "fuel_type": row[9] or "",
            "transmission": row[10] or "",
            "drive": row[11] or "",
            "condition": "Новый" if row[12] == 'new' else "С пробегом" if row[12] == 'used' else row[12],
            "mileage": row[13],
            "in_stock": row[5] > 0
        }
        return info
    return None


def finalize_sale(conn, cart_items, id_employee, id_customer):
    """
    Оформляет продажу: создает запись о продаже и списывает остатки.
    
    Args:
        conn: Подключение к БД
        cart_items: Список товаров в корзине (список dict с keys: car_id, quantity, price_at_sale)
        id_employee: ID менеджера
        id_customer: ID клиента
    
    Returns:
        tuple: (успех: bool, результат: ID продажи или сообщение об ошибке)
    """
    cur = conn.cursor()
    try:
        # Группируем позиции по car_id
        totals = defaultdict(int)
        for item in cart_items:
            totals[item['car_id']] += item['quantity']
        
        sale_items = []
        # Проверяем остатки и готовим записи (наличие / предзаказ)
        for car_id, total_qty in totals.items():
            stock, price = cur.execute(
                "SELECT quantity, price FROM cars WHERE id = ?", (car_id,)
            ).fetchone()
            deduct_qty = min(total_qty, stock)
            preorder_qty = total_qty - deduct_qty
            
            if deduct_qty > 0:
                sale_items.append((car_id, deduct_qty, price, 1))   # в наличии
            if preorder_qty > 0:
                sale_items.append((car_id, preorder_qty, price, 0)) # предзаказ
        
        total_amount = sum(qty * price for (_, qty, price, _) in sale_items)
        
        # Создаём продажу
        cur.execute(
            "INSERT INTO sales (sale_date, id_customer, id_employee, total_amount) VALUES (?, ?, ?, ?)",
            (datetime.now().timestamp(), id_customer, id_employee, total_amount)
        )
        sale_id = cur.lastrowid
        
        # Вставляем детали и списываем остатки только для позиций в наличии
        for car_id, qty, price, in_stock_flag in sale_items:
            cur.execute(
                "INSERT INTO sale_details (id_sale, id_car, quantity, price_at_sale, in_stock_at_sale) "
                "VALUES (?, ?, ?, ?, ?)",
                (sale_id, car_id, qty, price, in_stock_flag)
            )
            if in_stock_flag:
                cur.execute(
                    "UPDATE cars SET quantity = quantity - ? WHERE id = ?",
                    (qty, car_id)
                )
        
        conn.commit()
        return True, sale_id
    except Exception as e:
        conn.rollback()
        return False, str(e)


def get_report(conn, date_str):
    """
    Получает отчет по продажам на дату.
    
    Args:
        conn: Подключение к БД
        date_str: Дата в формате "ГГГГ-ММ-ДД"
    
    Returns:
        list: Список кортежей (описание_авто, количество, сумма)
    """
    return conn.execute('''
        SELECT c.brand || ' ' || c.model AS car,
               SUM(sd.quantity) AS qty,
               SUM(sd.quantity * sd.price_at_sale) AS revenue
        FROM sale_details sd
        JOIN cars c ON sd.id_car = c.id
        JOIN sales s ON sd.id_sale = s.id
        WHERE DATE(s.sale_date, 'unixepoch') = ?
        GROUP BY c.id
        ORDER BY revenue DESC
    ''', (date_str,)).fetchall()


def get_sales_list(conn, limit=50):
    """
    Получает список продаж с основной информацией.
    
    Args:
        conn: Подключение к БД
        limit: Максимальное количество записей
    
    Returns:
        list: Список кортежей с информацией о продажах
    """
    return conn.execute('''
        SELECT s.id, 
               datetime(s.sale_date, 'unixepoch', 'localtime') AS date,
               (c.first_name || ' ' || c.last_name) AS customer,
               (e.name || ' ' || e.surname) AS employee,
               s.total_amount,
               (SELECT MIN(sd2.in_stock_at_sale) FROM sale_details sd2 WHERE sd2.id_sale = s.id) AS all_in_stock
        FROM sales s
        JOIN customers c ON s.id_customer = c.id
        JOIN employees e ON s.id_employee = e.id
        ORDER BY s.sale_date DESC
        LIMIT ?
    ''', (limit,)).fetchall()


def get_sale_details(conn, sale_id):
    """
    Получает детальную информацию о конкретной продаже.
    
    Args:
        conn: Подключение к БД
        sale_id: ID продажи
    
    Returns:
        list: Список кортежей с информацией о каждом товаре в продаже
    """
    return conn.execute("""
        SELECT ca.brand, ca.model, ca.year, ca.engine_volume,
               ft.name, t.name, d.name,
               sd.quantity, sd.price_at_sale,
               (sd.quantity * sd.price_at_sale) AS subtotal,
               sd.id_car, sd.in_stock_at_sale
        FROM sale_details sd
        JOIN cars ca ON sd.id_car = ca.id
        LEFT JOIN fuel_types ft ON ca.id_fuel_type = ft.id
        LEFT JOIN transmissions t ON ca.id_transmission = t.id
        LEFT JOIN drives d ON ca.id_drive = d.id
        WHERE sd.id_sale = ?
    """, (sale_id,)).fetchall()
