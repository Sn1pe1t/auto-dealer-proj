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
            power INTEGER NOT NULL DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_customer INTEGER,
            id_employee INTEGER,
            sale_date INTEGER
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
    conn.commit()

def finalize_sale(conn, cart, id_employee, id_customer):
    try:
        conn.execute("BEGIN TRANSACTION")
        cur = conn.cursor()
        cur.execute("INSERT INTO sales (id_customer, id_employee, sale_date) VALUES (?, ?, strftime('%s','now'))", 
                    (id_customer, id_employee))
        sale_id = cur.lastrowid
        for item in cart:
            cur.execute("UPDATE cars SET quantity = quantity - ? WHERE id = ?", (item['quantity'], item['car_id']))
            cur.execute("INSERT INTO sale_details (id_sale, id_car, quantity, price_at_sale) VALUES (?, ?, ?, ?)",
                        (sale_id, item['car_id'], item['quantity'], item['price_at_sale']))
        conn.commit()
        return (True, sale_id)
    except Exception as e:
        conn.rollback()
        return (False, str(e))