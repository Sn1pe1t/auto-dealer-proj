import sqlite3

def init_db(conn):
    """Создает структуру таблиц, если они отсутствуют."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            model TEXT NOT NULL,
            year INTEGER NOT NULL,
            color TEXT,
            vin TEXT UNIQUE,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            power INTEGER NOT NULL DEFAULT 0,
            engine_volume REAL,
            id_category INTEGER,
            id_steering INTEGER,
            id_fuel_type INTEGER,
            id_transmission INTEGER,
            id_drive INTEGER,
            id_condition INTEGER,
            mileage INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_customer INTEGER,
            id_employee INTEGER,
            sale_date INTEGER,
            total_amount REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sale_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_sale INTEGER,
            id_car INTEGER,
            quantity INTEGER,
            price_at_sale REAL,
            in_stock_at_sale INTEGER DEFAULT 1
        )
    """)
    cur.execute("CREATE TABLE IF NOT EXISTS car_categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS employees (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, surname TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, first_name TEXT, last_name TEXT)")
    conn.commit()

def get_car_info(conn, car_id):
    """Возвращает подробную информацию об автомобиле."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM cars WHERE id = ?", (car_id,))
    row = cur.fetchone()
    if not row:
        return None
    # Преобразуем Row в словарь для удобства
    return dict(row)

def finalize_sale(conn, cart_items, id_employee, id_customer):
    """Оформляет продажу."""
    cur = conn.cursor()
    try:
        conn.execute("BEGIN TRANSACTION")
        total_amount = sum(item['quantity'] * item['price_at_sale'] for item in cart_items)
        
        cur.execute(
            "INSERT INTO sales (sale_date, id_customer, id_employee, total_amount) VALUES (strftime('%s','now'), ?, ?, ?)",
            (id_customer, id_employee, total_amount)
        )
        sale_id = cur.lastrowid

        for item in cart_items:
            cur.execute(
                "INSERT INTO sale_details (id_sale, id_car, quantity, price_at_sale) VALUES (?, ?, ?, ?)",
                (sale_id, item['car_id'], item['quantity'], item['price_at_sale'])
            )
            cur.execute("UPDATE cars SET quantity = quantity - ? WHERE id = ?", (item['quantity'], item['car_id']))
        
        conn.commit()
        return True, sale_id
    except Exception as e:
        conn.rollback()
        return False, str(e)