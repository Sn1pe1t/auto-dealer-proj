# app/db_queries.py
import sqlite3
import csv
import os
import hashlib
from datetime import datetime

# ------------------------------------------------------------
# Подключение к БД
def get_db(db_name='autodealer.db'):
    conn = sqlite3.connect(db_name, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# ------------------------------------------------------------
# Инициализация БД и загрузка данных
def init_db(conn, schema_file, init_data_file, load_initial_data_func):
    """Выполняет инициализацию БД по схеме и CSV."""
    conn.execute("PRAGMA foreign_keys = OFF")
    with open(schema_file, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    if os.path.exists(init_data_file):
        load_initial_data_func(conn, init_data_file)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()

def load_initial_data(conn, csv_file):
    """Загружает данные из CSV в формате: таблица,значения... (первая колонка — имя таблицы)"""
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].startswith('#'):
                continue
            table = row[0].strip()
            values = row[1:]
            if not values:
                continue
            cur = conn.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cur.fetchall()]
            if not columns:
                continue
            # Приводим количество значений к числу колонок
            if len(values) > len(columns):
                values = values[:len(columns)]
            elif len(values) < len(columns):
                values.extend([''] * (len(columns) - len(values)))
            # Для таблицы users: хешируем пароль
            if table == 'users':
                if len(values) >= 3 and values[2]:
                    values[2] = hashlib.sha256(values[2].encode()).hexdigest()
                for i in [4, 5]:
                    if i < len(values) and values[i] and values[i] != '':
                        values[i] = int(values[i])
                    else:
                        values[i] = None
            placeholders = ','.join(['?' for _ in columns])
            sql = f"INSERT OR IGNORE INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
            try:
                conn.execute(sql, values)
            except Exception as e:
                print(f"Ошибка вставки в {table}: {e} (строка: {row})")
    conn.commit()

# ------------------------------------------------------------
# Фильтры и автомобили
def get_filters_data(conn):
    categories = conn.execute("SELECT id, name FROM car_categories").fetchall()
    steering = conn.execute("SELECT name FROM steering_types").fetchall()
    fuel = conn.execute("SELECT name FROM fuel_types").fetchall()
    transmission = conn.execute("SELECT name FROM transmissions").fetchall()
    drive = conn.execute("SELECT name FROM drives").fetchall()
    condition = conn.execute("SELECT name FROM conditions").fetchall()
    return {
        'categories': [dict(c) for c in categories],
        'steering': [s['name'] for s in steering],
        'fuel': [f['name'] for f in fuel],
        'transmission': [t['name'] for t in transmission],
        'drive': [d['name'] for d in drive],
        'condition': [c['name'] for c in condition],
    }

def get_cars_with_filters(conn, params):
    query = """
        SELECT c.id, c.brand, c.model, c.year, c.color, c.price, c.quantity,
               st.name as steering_name, c.power, c.engine_volume,
               ft.name as fuel_name, tr.name as trans_name, d.name as drive_name,
               cond.name as condition_name, cat.name as category_name
        FROM cars c
        LEFT JOIN steering_types st ON c.id_steering = st.id
        LEFT JOIN fuel_types ft ON c.id_fuel_type = ft.id
        LEFT JOIN transmissions tr ON c.id_transmission = tr.id
        LEFT JOIN drives d ON c.id_drive = d.id
        LEFT JOIN conditions cond ON c.id_condition = cond.id
        LEFT JOIN car_categories cat ON c.id_category = cat.id
        WHERE 1=1
    """
    args = []
    cat_id = params.get('category_id')
    if cat_id and cat_id != 'all':
        query += " AND c.id_category = ?"
        args.append(cat_id)
    if params.get('in_stock_only') == 'true':
        query += " AND c.quantity > 0"
    steering = params.get('steering')
    if steering and steering != 'all':
        query += " AND st.name = ?"
        args.append(steering)
    power_from = params.get('power_from')
    if power_from and power_from != '':
        try:
            query += " AND c.power >= ?"
            args.append(int(power_from))
        except: pass
    power_to = params.get('power_to')
    if power_to and power_to != '':
        try:
            query += " AND c.power <= ?"
            args.append(int(power_to))
        except: pass
    fuel = params.get('fuel')
    if fuel and fuel != 'all':
        query += " AND ft.name = ?"
        args.append(fuel)
    trans = params.get('transmission')
    if trans and trans != 'all':
        query += " AND tr.name = ?"
        args.append(trans)
    drive = params.get('drive')
    if drive and drive != 'all':
        query += " AND d.name = ?"
        args.append(drive)
    cond = params.get('condition')
    if cond and cond != 'all':
        query += " AND cond.name = ?"
        args.append(cond)
    query += " ORDER BY c.quantity DESC, c.brand"
    rows = conn.execute(query, args).fetchall()
    return [dict(r) for r in rows]

def get_car_info_by_id(conn, car_id):
    row = conn.execute("""
        SELECT c.brand, c.model, c.year, c.color, c.price, c.quantity,
               st.name as steering_name, c.power, c.engine_volume,
               ft.name as fuel_name, tr.name as trans_name, d.name as drive_name,
               cond.name as condition_name, c.mileage,
               (c.quantity > 0) as in_stock
        FROM cars c
        LEFT JOIN steering_types st ON c.id_steering = st.id
        LEFT JOIN fuel_types ft ON c.id_fuel_type = ft.id
        LEFT JOIN transmissions tr ON c.id_transmission = tr.id
        LEFT JOIN drives d ON c.id_drive = d.id
        LEFT JOIN conditions cond ON c.id_condition = cond.id
        WHERE c.id = ?
    """, (car_id,)).fetchone()
    return dict(row) if row else None

# ------------------------------------------------------------
# Клиенты и сотрудники
def get_customers_by_role(conn, role, customer_id):
    if role == 'user':
        row = conn.execute("SELECT id, first_name, last_name, phone FROM customers WHERE id = ?", (customer_id,)).fetchone()
        return [dict(row)] if row else []
    else:
        rows = conn.execute("SELECT id, first_name, last_name, phone FROM customers ORDER BY last_name").fetchall()
        return [dict(r) for r in rows]

def get_employees(conn):
    rows = conn.execute("SELECT id, name, surname FROM employees").fetchall()
    return [dict(r) for r in rows]

# ------------------------------------------------------------
# Продажи и детали
def get_sales_by_role(conn, role, customer_id):
    if role in ('manager', 'senior_manager', 'owner'):
        rows = conn.execute("""
            SELECT s.id, datetime(s.sale_date, 'unixepoch', 'localtime') as date,
                   (c.first_name || ' ' || c.last_name) as customer,
                   (e.name || ' ' || e.surname) as employee,
                   s.total_amount,
                   (SELECT MIN(sd2.in_stock_at_sale) FROM sale_details sd2 WHERE sd2.id_sale = s.id) as all_in_stock
            FROM sales s
            JOIN customers c ON s.id_customer = c.id
            JOIN employees e ON s.id_employee = e.id
            ORDER BY s.sale_date DESC
            LIMIT 100
        """).fetchall()
    else:
        rows = conn.execute("""
            SELECT s.id, datetime(s.sale_date, 'unixepoch', 'localtime') as date,
                   (c.first_name || ' ' || c.last_name) as customer,
                   (e.name || ' ' || e.surname) as employee,
                   s.total_amount,
                   (SELECT MIN(sd2.in_stock_at_sale) FROM sale_details sd2 WHERE sd2.id_sale = s.id) as all_in_stock
            FROM sales s
            JOIN customers c ON s.id_customer = c.id
            JOIN employees e ON s.id_employee = e.id
            WHERE s.id_customer = ?
            ORDER BY s.sale_date DESC
            LIMIT 100
        """, (customer_id,)).fetchall()
    return [dict(r) for r in rows]

def get_sale_details_by_id(conn, sale_id, role, customer_id):
    if role not in ('manager', 'senior_manager', 'owner'):
        owner = conn.execute("SELECT id_customer FROM sales WHERE id = ?", (sale_id,)).fetchone()
        if not owner or owner['id_customer'] != customer_id:
            return None
    rows = conn.execute("""
        SELECT ca.brand, ca.model, ca.year, ca.engine_volume,
               ft.name as fuel_name, tr.name as trans_name, d.name as drive_name,
               sd.quantity, sd.price_at_sale,
               (sd.quantity * sd.price_at_sale) as subtotal,
               sd.id_car, sd.in_stock_at_sale
        FROM sale_details sd
        JOIN cars ca ON sd.id_car = ca.id
        LEFT JOIN fuel_types ft ON ca.id_fuel_type = ft.id
        LEFT JOIN transmissions tr ON ca.id_transmission = tr.id
        LEFT JOIN drives d ON ca.id_drive = d.id
        WHERE sd.id_sale = ?
    """, (sale_id,)).fetchall()
    return [dict(r) for r in rows]

def get_car_stock_and_price(conn, car_id):
    return conn.execute("SELECT quantity, price FROM cars WHERE id = ?", (car_id,)).fetchone()

def update_car_quantity(conn, car_id, deduct_qty):
    conn.execute("UPDATE cars SET quantity = quantity - ? WHERE id = ?", (deduct_qty, car_id))

def insert_sale(conn, sale_date, id_customer, id_employee, total_amount):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO sales (sale_date, id_customer, id_employee, total_amount) VALUES (?, ?, ?, ?)",
        (sale_date, id_customer, id_employee, total_amount)
    )
    return cur.lastrowid

def insert_sale_detail(conn, sale_id, car_id, quantity, price_at_sale, in_stock_flag):
    conn.execute(
        "INSERT INTO sale_details (id_sale, id_car, quantity, price_at_sale, in_stock_at_sale) VALUES (?, ?, ?, ?, ?)",
        (sale_id, car_id, quantity, price_at_sale, in_stock_flag)
    )

# ------------------------------------------------------------
# Отчёты
def get_report_data(conn, date_str):
    rows = conn.execute('''
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
    return [{'car_name': r[0], 'quantity': r[1], 'revenue': r[2]} for r in rows]

def get_top_sales_data(conn, limit):
    rows = conn.execute('''
        SELECT c.brand, c.model,
               SUM(sd.quantity) AS total_qty,
               SUM(sd.quantity * sd.price_at_sale) AS total_revenue
        FROM sale_details sd
        JOIN cars c ON sd.id_car = c.id
        GROUP BY c.id
        ORDER BY total_qty DESC
        LIMIT ?
    ''', (limit,)).fetchall()
    return [{'brand': r[0], 'model': r[1], 'total_qty': r[2], 'total_revenue': r[3]} for r in rows]

def get_sales_today_data(conn):
    today = datetime.now().strftime('%Y-%m-%d')
    row = conn.execute('''
        SELECT COUNT(*) as count, COALESCE(SUM(total_amount), 0) as total
        FROM sales
        WHERE DATE(sale_date, 'unixepoch') = ?
    ''', (today,)).fetchone()
    return {'count': row[0], 'total': row[1]}

# ------------------------------------------------------------
# Управление пользователями
def get_users_list(conn):
    rows = conn.execute("SELECT id, username, role FROM users ORDER BY id").fetchall()
    return [dict(r) for r in rows]

def get_user_by_id(conn, user_id):
    return conn.execute("SELECT id, username, role, customer_id, employee_id FROM users WHERE id = ?", (user_id,)).fetchone()

def update_user_role(conn, user_id, new_role, employee_id=None):
    if employee_id is not None:
        conn.execute("UPDATE users SET role = ?, employee_id = ? WHERE id = ?", (new_role, employee_id, user_id))
    else:
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))

def create_employee(conn, name, surname, job_id):
    cur = conn.cursor()
    cur.execute("INSERT INTO employees (name, surname, id_job_title) VALUES (?, ?, ?)", (name, surname, job_id))
    return cur.lastrowid

def update_employee_job_title(conn, emp_id, job_id):
    conn.execute("UPDATE employees SET id_job_title = ? WHERE id = ?", (job_id, emp_id))

def get_customer_by_id(conn, customer_id):
    return conn.execute("SELECT first_name, last_name, phone, email FROM customers WHERE id = ?", (customer_id,)).fetchone()

def get_employee_by_id(conn, emp_id):
    return conn.execute("SELECT name, surname FROM employees WHERE id = ?", (emp_id,)).fetchone()

def get_user_by_username(conn, username):
    return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

def create_customer(conn, first_name, last_name, phone, email):
    cur = conn.cursor()
    cur.execute("INSERT INTO customers (first_name, last_name, phone, email) VALUES (?, ?, ?, ?)",
                (first_name, last_name, phone, email))
    return cur.lastrowid

def create_user(conn, username, password_hash, role, customer_id=None, employee_id=None):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, password_hash, role, customer_id, employee_id) VALUES (?, ?, ?, ?, ?)",
        (username, password_hash, role, customer_id, employee_id)
    )
    return cur.lastrowid