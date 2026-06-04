from flask import Flask, render_template, jsonify, request, session
import sqlite3
import os
import csv
from datetime import datetime
from collections import defaultdict
from functools import wraps
import hashlib
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # или задайте постоянную строку
DB_NAME = 'autodealer.db'
SCHEMA_FILE = 'schema.sql'
INIT_DATA_FILE = 'init_data.csv'

# ------------------------------------------------------------
# Декораторы
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

def owner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'owner':
            return jsonify({'error': 'Forbidden'}), 403
        return f(*args, **kwargs)
    return decorated_function

def senior_manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        role = session.get('role')
        if role not in ('senior_manager', 'owner'):
            return jsonify({'error': 'Forbidden'}), 403
        return f(*args, **kwargs)
    return decorated_function

def manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        role = session.get('role')
        if role not in ('manager', 'senior_manager', 'owner'):
            return jsonify({'error': 'Forbidden'}), 403
        return f(*args, **kwargs)
    return decorated_function

# ------------------------------------------------------------
# Инициализация БД
def init_db():
    if not os.path.exists(SCHEMA_FILE):
        raise Exception(f"Файл схемы {SCHEMA_FILE} не найден!")
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = OFF")
    with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    if os.path.exists(INIT_DATA_FILE):
        load_initial_data(conn, INIT_DATA_FILE)
    else:
        print(f"Предупреждение: {INIT_DATA_FILE} не найден")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()

def load_initial_data(conn, csv_file):
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
            if len(values) > len(columns):
                values = values[:len(columns)]
            elif len(values) < len(columns):
                values.extend([''] * (len(columns) - len(values)))
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

def get_db():
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# ------------------------------------------------------------
# API маршруты
@app.route('/api/filters')
def get_filters():
    conn = get_db()
    categories = conn.execute("SELECT id, name FROM car_categories").fetchall()
    steering = conn.execute("SELECT name FROM steering_types").fetchall()
    fuel = conn.execute("SELECT name FROM fuel_types").fetchall()
    transmission = conn.execute("SELECT name FROM transmissions").fetchall()
    drive = conn.execute("SELECT name FROM drives").fetchall()
    condition = conn.execute("SELECT name FROM conditions").fetchall()
    conn.close()
    return jsonify({
        'categories': [dict(c) for c in categories],
        'steering': [s['name'] for s in steering],
        'fuel': [f['name'] for f in fuel],
        'transmission': [t['name'] for t in transmission],
        'drive': [d['name'] for d in drive],
        'condition': [c['name'] for c in condition]
    })

@app.route('/api/cars')
def get_cars():
    conn = get_db()
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
    params = []
    category_id = request.args.get('category_id')
    if category_id and category_id != 'all':
        query += " AND c.id_category = ?"
        params.append(category_id)
    in_stock_only = request.args.get('in_stock_only')
    if in_stock_only == 'true':
        query += " AND c.quantity > 0"
    steering = request.args.get('steering')
    if steering and steering != 'all':
        query += " AND st.name = ?"
        params.append(steering)
    power_from = request.args.get('power_from')
    if power_from and power_from != '':
        try:
            query += " AND c.power >= ?"
            params.append(int(power_from))
        except: pass
    power_to = request.args.get('power_to')
    if power_to and power_to != '':
        try:
            query += " AND c.power <= ?"
            params.append(int(power_to))
        except: pass
    fuel = request.args.get('fuel')
    if fuel and fuel != 'all':
        query += " AND ft.name = ?"
        params.append(fuel)
    trans = request.args.get('transmission')
    if trans and trans != 'all':
        query += " AND tr.name = ?"
        params.append(trans)
    drive = request.args.get('drive')
    if drive and drive != 'all':
        query += " AND d.name = ?"
        params.append(drive)
    cond = request.args.get('condition')
    if cond and cond != 'all':
        query += " AND cond.name = ?"
        params.append(cond)
    query += " ORDER BY c.quantity DESC, c.brand"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/customers')
@login_required
def get_customers():
    if session['role'] == 'user':
        conn = get_db()
        row = conn.execute("SELECT id, first_name, last_name, phone FROM customers WHERE id = ?", (session['customer_id'],)).fetchone()
        conn.close()
        return jsonify([dict(row)] if row else [])
    else:
        conn = get_db()
        rows = conn.execute("SELECT id, first_name, last_name, phone FROM customers ORDER BY last_name").fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

@app.route('/api/employees')
@login_required
def get_employees():
    conn = get_db()
    rows = conn.execute("SELECT id, name, surname FROM employees").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/sales')
@login_required
def get_sales():
    conn = get_db()
    if session['role'] in ('manager', 'senior_manager', 'owner'):
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
        """, (session['customer_id'],)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/sale_details/<int:sale_id>')
@login_required
def get_sale_details(sale_id):
    conn = get_db()
    if session['role'] not in ('manager', 'senior_manager', 'owner'):
        owner = conn.execute("SELECT id_customer FROM sales WHERE id = ?", (sale_id,)).fetchone()
        if not owner or owner['id_customer'] != session['customer_id']:
            conn.close()
            return jsonify({'error': 'Forbidden'}), 403
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
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/car/<int:car_id>')
@login_required
def get_car(car_id):
    conn = get_db()
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
    conn.close()
    if row:
        return jsonify(dict(row))
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/finalize_sale', methods=['POST'])
@login_required
def finalize_sale():
    data = request.get_json()
    cart_items = data.get('cart', [])
    id_employee = data.get('id_employee')
    id_customer = data.get('id_customer')  # может отсутствовать

    if not cart_items:
        return jsonify({'success': False, 'error': 'Корзина пуста'}), 400

    if not id_employee:
        return jsonify({'success': False, 'error': 'Не выбран менеджер'}), 400

    # Определяем клиента
    if id_customer is None:
        # Для обычного пользователя берём из сессии
        id_customer = session.get('customer_id')
        if not id_customer:
            return jsonify({'success': False, 'error': 'У вас нет привязанного клиента'}), 400

    # Остальная логика оформления заказа (без изменений)
    conn = get_db()
    cur = conn.cursor()
    try:
        totals = defaultdict(int)
        for item in cart_items:
            totals[item['id']] += item['quantity']

        sale_items = []
        for car_id, total_qty in totals.items():
            stock, price = cur.execute("SELECT quantity, price FROM cars WHERE id = ?", (car_id,)).fetchone()
            deduct_qty = min(total_qty, stock)
            preorder_qty = total_qty - deduct_qty
            if deduct_qty > 0:
                sale_items.append((car_id, deduct_qty, price, 1))
            if preorder_qty > 0:
                sale_items.append((car_id, preorder_qty, price, 0))

        total_amount = sum(qty * price for (_, qty, price, _) in sale_items)

        cur.execute(
            "INSERT INTO sales (sale_date, id_customer, id_employee, total_amount) VALUES (?, ?, ?, ?)",
            (datetime.now().timestamp(), id_customer, id_employee, total_amount)
        )
        sale_id = cur.lastrowid

        for car_id, qty, price, in_stock_flag in sale_items:
            cur.execute(
                "INSERT INTO sale_details (id_sale, id_car, quantity, price_at_sale, in_stock_at_sale) VALUES (?, ?, ?, ?, ?)",
                (sale_id, car_id, qty, price, in_stock_flag)
            )
            if in_stock_flag:
                cur.execute("UPDATE cars SET quantity = quantity - ? WHERE id = ?", (qty, car_id))

        conn.commit()
        return jsonify({'success': True, 'sale_id': sale_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/report')
@login_required
@manager_required
def report():
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'date required'}), 400
    conn = get_db()
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
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/top_sales')
@login_required
def top_sales():
    conn = get_db()
    rows = conn.execute('''
        SELECT c.brand, c.model,
               SUM(sd.quantity) AS total_qty,
               SUM(sd.quantity * sd.price_at_sale) AS total_revenue
        FROM sale_details sd
        JOIN cars c ON sd.id_car = c.id
        GROUP BY c.id
        ORDER BY total_qty DESC
        LIMIT 10
    ''').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/sales_today')
@login_required
@manager_required
def sales_today():
    conn = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    row = conn.execute('''
        SELECT COUNT(*) as count, COALESCE(SUM(total_amount), 0) as total
        FROM sales
        WHERE DATE(sale_date, 'unixepoch') = ?
    ''', (today,)).fetchone()
    conn.close()
    return jsonify({'count': row['count'], 'total': row['total']})

@app.route('/api/upload_cars', methods=['POST'])
@login_required
@manager_required
def upload_cars():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Файл не загружен'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Пустое имя файла'}), 400
    stream = file.stream.read().decode('utf-8').splitlines()
    reader = csv.DictReader(stream)
    conn = get_db()
    cur = conn.cursor()
    try:
        for row in reader:
            brand = row.get('brand', '').strip()
            model = row.get('model', '').strip()
            if not brand or not model:
                continue
            try:
                year = int(row['year'])
                color = row.get('color', '').strip()
                vin = row.get('vin', '').strip()
                price = float(row['price'])
                qty = int(row['quantity'])
                cat_name = row.get('category', '').strip()
                steering_text = row.get('steering', 'left').strip().lower()
                power = int(row['power'])
                engine_volume = float(row['engine_volume']) if row.get('engine_volume') else None
                fuel_text = row.get('fuel_type', '').strip().lower()
                trans_text = row.get('transmission', '').strip().lower()
                drive_text = row.get('drive', '').strip().lower()
                cond_text = row.get('condition', 'new').strip().lower()
                mileage = int(row['mileage']) if row.get('mileage') and row['mileage'].strip() else None
            except (KeyError, ValueError):
                continue
            cat_row = cur.execute("SELECT id FROM car_categories WHERE name = ?", (cat_name,)).fetchone()
            if cat_row:
                cat_id = cat_row[0]
            else:
                cur.execute("INSERT INTO car_categories (name) VALUES (?)", (cat_name,))
                cat_id = cur.lastrowid
            def get_ref_id(table, name):
                if not name:
                    return None
                r = cur.execute(f"SELECT id FROM {table} WHERE name = ?", (name,)).fetchone()
                if r:
                    return r[0]
                cur.execute(f"INSERT INTO {table} (name) VALUES (?)", (name,))
                return cur.lastrowid
            id_steering = get_ref_id('steering_types', steering_text)
            id_fuel = get_ref_id('fuel_types', fuel_text) if fuel_text else None
            id_trans = get_ref_id('transmissions', trans_text) if trans_text else None
            id_drive = get_ref_id('drives', drive_text) if drive_text else None
            id_cond = get_ref_id('conditions', cond_text)
            exist = cur.execute("SELECT id, quantity FROM cars WHERE vin = ?", (vin,)).fetchone()
            if exist:
                cur.execute("""
                    UPDATE cars SET price=?, quantity=quantity+?, id_category=?, id_steering=?,
                    power=?, engine_volume=?, id_fuel_type=?, id_transmission=?, id_drive=?,
                    id_condition=?, mileage=? WHERE id=?
                """, (price, qty, cat_id, id_steering, power, engine_volume,
                      id_fuel, id_trans, id_drive, id_cond, mileage, exist[0]))
            else:
                cur.execute("""
                    INSERT INTO cars (brand, model, year, color, vin, price, quantity, id_category,
                    id_steering, power, engine_volume, id_fuel_type, id_transmission, id_drive, id_condition, mileage)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (brand, model, year, color, vin, price, qty, cat_id,
                      id_steering, power, engine_volume, id_fuel, id_trans, id_drive, id_cond, mileage))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/users')
@login_required
@senior_manager_required
def get_users():
    conn = get_db()
    rows = conn.execute("""
        SELECT u.id, u.username, u.role
        FROM users u
        ORDER BY u.id
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/set_role/<int:user_id>', methods=['POST'])
@login_required
def set_role(user_id):
    data = request.get_json()
    new_role = data.get('role')
    if new_role not in ('user', 'manager', 'senior_manager'):
        return jsonify({'success': False, 'error': 'Недопустимая роль'}), 400

    current_user_role = session['role']
    conn = get_db()
    cur = conn.cursor()
    try:
        target = cur.execute("SELECT id, username, role, customer_id, employee_id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not target:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404

        # Права доступа
        if current_user_role == 'owner':
            pass
        elif current_user_role == 'senior_manager':
            if target['role'] in ('owner', 'senior_manager'):
                return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403
            if new_role not in ('user', 'manager'):
                return jsonify({'success': False, 'error': 'Старший менеджер может назначать только обычных менеджеров'}), 403
        else:
            return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403

        if target['role'] == new_role:
            return jsonify({'success': True})

        if new_role in ('manager', 'senior_manager'):
            job_id = 1 if new_role == 'manager' else 2

            if target['employee_id']:
                # Обновляем существующего сотрудника
                cur.execute("UPDATE employees SET id_job_title = ? WHERE id = ?", (job_id, target['employee_id']))
                cur.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
            else:
                # Создаём нового сотрудника (customer_id не трогаем, оставляем NULL)
                name = target['username']
                surname = ''
                # Если есть customer_id, можем взять имя оттуда, но не обязательно
                if target['customer_id']:
                    cust = cur.execute("SELECT first_name, last_name FROM customers WHERE id = ?", (target['customer_id'],)).fetchone()
                    if cust:
                        name = cust['first_name']
                        surname = cust['last_name']
                cur.execute("INSERT INTO employees (name, surname, id_job_title) VALUES (?, ?, ?)", (name, surname, job_id))
                new_emp_id = cur.lastrowid
                # При повышении НЕ меняем customer_id, оставляем как есть (NULL для менеджеров)
                cur.execute("UPDATE users SET role = ?, employee_id = ? WHERE id = ?", (new_role, new_emp_id, user_id))

        elif new_role == 'user':
            cur.execute("UPDATE users SET role = ?, employee_id = NULL WHERE id = ?", (new_role, user_id))

        conn.commit()
        return jsonify({'success': True})

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    conn = get_db()
    user_id = session['user_id']
    user = conn.execute("SELECT username, role, customer_id, employee_id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    profile = {
        'username': user['username'],
        'role': user['role'],
        'first_name': '',
        'last_name': '',
        'phone': '',
        'email': ''
    }
    if user['role'] == 'user' and user['customer_id']:
        cust = conn.execute("SELECT first_name, last_name, phone, email FROM customers WHERE id = ?", (user['customer_id'],)).fetchone()
        if cust:
            profile['first_name'] = cust['first_name']
            profile['last_name'] = cust['last_name']
            profile['phone'] = cust['phone'] or ''
            profile['email'] = cust['email'] or ''
    elif user['role'] in ('manager', 'senior_manager', 'owner') and user['employee_id']:
        emp = conn.execute("SELECT name, surname FROM employees WHERE id = ?", (user['employee_id'],)).fetchone()
        if emp:
            profile['first_name'] = emp['name']
            profile['last_name'] = emp['surname']
    conn.close()
    return jsonify(profile)

@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    data = request.json
    username = data.get('username', '').strip()
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()
    if not username or not first_name or not last_name:
        return jsonify({'success': False, 'error': 'Логин, имя и фамилия обязательны'}), 400
    conn = get_db()
    user_id = session['user_id']
    cur = conn.cursor()
    current = cur.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
    if current['username'] != username:
        existing = cur.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            conn.close()
            return jsonify({'success': False, 'error': 'Пользователь с таким логином уже существует'}), 400
        cur.execute("UPDATE users SET username = ? WHERE id = ?", (username, user_id))
        session['username'] = username
    user = cur.execute("SELECT role, customer_id, employee_id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'success': False, 'error': 'User not found'}), 404
    try:
        if user['role'] == 'user' and user['customer_id']:
            cur.execute("UPDATE customers SET first_name=?, last_name=?, phone=?, email=? WHERE id=?",
                        (first_name, last_name, phone, email, user['customer_id']))
        elif user['role'] in ('manager', 'senior_manager', 'owner') and user['employee_id']:
            cur.execute("UPDATE employees SET name=?, surname=? WHERE id=?",
                        (first_name, last_name, user['employee_id']))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/change_password', methods=['POST'])
@login_required
def change_password():
    data = request.json
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    if not old_password or not new_password:
        return jsonify({'success': False, 'error': 'Введите старый и новый пароль'}), 400
    if len(new_password) < 4:
        return jsonify({'success': False, 'error': 'Новый пароль должен содержать не менее 4 символов'}), 400
    conn = get_db()
    user_id = session['user_id']
    user = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'success': False, 'error': 'User not found'}), 404
    old_hash = hashlib.sha256(old_password.encode()).hexdigest()
    if user['password_hash'] != old_hash:
        conn.close()
        return jsonify({'success': False, 'error': 'Неверный старый пароль'}), 401
    new_hash = hashlib.sha256(new_password.encode()).hexdigest()
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    phone = data.get('phone', '')
    email = data.get('email', '')
    if not username or not password or not first_name or not last_name:
        return jsonify({'success': False, 'error': 'Заполните все обязательные поля'}), 400
    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        conn.close()
        return jsonify({'success': False, 'error': 'Пользователь уже существует'}), 400
    cur = conn.cursor()
    cur.execute("INSERT INTO customers (first_name, last_name, phone, email) VALUES (?, ?, ?, ?)",
                (first_name, last_name, phone, email))
    customer_id = cur.lastrowid
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    cur.execute("INSERT INTO users (username, password_hash, role, customer_id) VALUES (?, ?, 'user', ?)",
                (username, password_hash, customer_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'success': False, 'error': 'Введите логин и пароль'}), 400
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if not user:
        return jsonify({'success': False, 'error': 'Неверный логин или пароль'}), 401
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if user['password_hash'] != password_hash:
        return jsonify({'success': False, 'error': 'Неверный логин или пароль'}), 401
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user['role']
    session['customer_id'] = user['customer_id']
    session['employee_id'] = user['employee_id']
    return jsonify({'success': True, 'role': user['role'], 'username': user['username']})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/current_user')
def current_user():
    if 'user_id' in session:
        return jsonify({'authenticated': True, 'role': session['role'], 'username': session['username']})
    else:
        return jsonify({'authenticated': False})

# ------------------------------------------------------------
# Главная страница
@app.route('/')
def index():
    return render_template('index.html')

# ------------------------------------------------------------
if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)