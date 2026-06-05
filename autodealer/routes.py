# app/routes.py
from flask import Blueprint, render_template, jsonify, request, session
from datetime import datetime
from collections import defaultdict
import hashlib

from autodealer.auth import login_required, owner_required, senior_manager_required, manager_required
from autodealer.db_queries import (
    get_db, get_filters_data, get_cars_with_filters, get_customers_by_role,
    get_employees, get_sales_by_role, get_sale_details_by_id, get_car_info_by_id,
    get_car_stock_and_price, update_car_quantity, insert_sale, insert_sale_detail,
    get_report_data, get_top_sales_data, get_sales_today_data,
    get_users_list, get_user_by_id, update_user_role, create_employee,
    update_employee_job_title, get_customer_by_id, get_employee_by_id,
    get_user_by_username, create_customer, create_user
)
from autodealer_core import calculate_sale_items, total_amount, aggregate_report, top_sales

api = Blueprint('api', __name__)

# ------------------------------------------------------------
# Главная страница
@api.route('/')
def index():
    return render_template('index.html')

# ------------------------------------------------------------
# Фильтры и автомобили
@api.route('/api/filters')
def get_filters():
    conn = get_db()
    data = get_filters_data(conn)
    conn.close()
    return jsonify(data)

@api.route('/api/cars')
def get_cars():
    conn = get_db()
    cars = get_cars_with_filters(conn, request.args.to_dict())
    conn.close()
    return jsonify(cars)

@api.route('/api/customers')
@login_required
def get_customers():
    conn = get_db()
    customers = get_customers_by_role(conn, session['role'], session.get('customer_id'))
    conn.close()
    return jsonify(customers)

@api.route('/api/employees')
@login_required
def get_employees_route():
    conn = get_db()
    employees = get_employees(conn)
    conn.close()
    return jsonify(employees)

@api.route('/api/sales')
@login_required
def get_sales_route():
    conn = get_db()
    sales = get_sales_by_role(conn, session['role'], session.get('customer_id'))
    conn.close()
    return jsonify(sales)

@api.route('/api/sale_details/<int:sale_id>')
@login_required
def get_sale_details_route(sale_id):
    conn = get_db()
    details = get_sale_details_by_id(conn, sale_id, session['role'], session.get('customer_id'))
    conn.close()
    if details is None:
        return jsonify({'error': 'Forbidden'}), 403
    return jsonify(details)

@api.route('/api/car/<int:car_id>')
@login_required
def get_car_route(car_id):
    conn = get_db()
    car = get_car_info_by_id(conn, car_id)
    conn.close()
    if not car:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(car)

@api.route('/api/finalize_sale', methods=['POST'])
@login_required
def finalize_sale_route():
    data = request.get_json()
    cart_items = data.get('cart', [])
    id_employee = data.get('id_employee')
    id_customer = data.get('id_customer')

    if not cart_items:
        return jsonify({'success': False, 'error': 'Корзина пуста'}), 400
    if not id_employee:
        return jsonify({'success': False, 'error': 'Не выбран менеджер'}), 400
    if id_customer is None:
        id_customer = session.get('customer_id')
        if not id_customer:
            return jsonify({'success': False, 'error': 'У вас нет привязанного клиента'}), 400

    conn = get_db()
    try:
        cart_totals = defaultdict(int)
        for item in cart_items:
            cart_totals[item['id']] += item['quantity']

        stock_map = {}
        for car_id in cart_totals:
            stock, price = get_car_stock_and_price(conn, car_id)
            stock_map[car_id] = (stock, price)

        sale_items = calculate_sale_items(cart_totals, stock_map)
        total = total_amount(sale_items)

        sale_id = insert_sale(conn, datetime.now().timestamp(), id_customer, id_employee, total)

        for car_id, qty, price, in_stock_flag in sale_items:
            insert_sale_detail(conn, sale_id, car_id, qty, price, in_stock_flag)
            if in_stock_flag:
                update_car_quantity(conn, car_id, qty)

        conn.commit()
        return jsonify({'success': True, 'sale_id': sale_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

@api.route('/api/report')
@login_required
@manager_required
def report_route():
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'date required'}), 400
    conn = get_db()
    rows = get_report_data(conn, date_str)
    conn.close()
    report_data = aggregate_report(rows)
    return jsonify([{'car': car, 'qty': qty, 'revenue': revenue} for car, qty, revenue in report_data])

@api.route('/api/top_sales')
@login_required
def top_sales_route():
    conn = get_db()
    rows = get_top_sales_data(conn, 10)
    conn.close()
    result = []
    for r in rows:
        brand_model = f"{r['brand']} {r['model']}".strip()
        if brand_model:   # пропускаем пустые названия
            result.append({
                'brand_model': brand_model,
                'total_qty': r['total_qty'],
                'total_revenue': r['total_revenue']
            })
    return jsonify(result)

@api.route('/api/sales_today')
@login_required
@manager_required
def sales_today_route():
    conn = get_db()
    data = get_sales_today_data(conn)
    conn.close()
    return jsonify(data)

@api.route('/api/upload_cars', methods=['POST'])
@login_required
@manager_required
def upload_cars_route():
    import csv
    file = request.files['file']
    if 'file' not in request.files or file.filename == '':
        return jsonify({'success': False, 'error': 'Файл не загружен'}), 400
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

@api.route('/api/users')
@login_required
@senior_manager_required
def get_users_route():
    conn = get_db()
    users = get_users_list(conn)
    conn.close()
    return jsonify(users)

@api.route('/api/set_role/<int:user_id>', methods=['POST'])
@login_required
def set_role_route(user_id):
    data = request.get_json()
    new_role = data.get('role')
    if new_role not in ('user', 'manager', 'senior_manager'):
        return jsonify({'success': False, 'error': 'Недопустимая роль'}), 400

    conn = get_db()
    try:
        target = get_user_by_id(conn, user_id)
        if not target:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404

        current_role = session['role']
        if current_role == 'owner':
            pass
        elif current_role == 'senior_manager':
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
                update_employee_job_title(conn, target['employee_id'], job_id)
                update_user_role(conn, user_id, new_role)
            else:
                name = target['username']
                surname = ''
                if target['customer_id']:
                    cust = get_customer_by_id(conn, target['customer_id'])
                    if cust:
                        name = cust['first_name']
                        surname = cust['last_name']
                emp_id = create_employee(conn, name, surname, job_id)
                update_user_role(conn, user_id, new_role, emp_id)
        elif new_role == 'user':
            update_user_role(conn, user_id, 'user')

        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

@api.route('/api/profile', methods=['GET'])
@login_required
def get_profile_route():
    conn = get_db()
    user_id = session['user_id']
    user = get_user_by_id(conn, user_id)
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
        cust = get_customer_by_id(conn, user['customer_id'])
        if cust:
            profile['first_name'] = cust['first_name']
            profile['last_name'] = cust['last_name']
            profile['phone'] = cust['phone'] or ''
            profile['email'] = cust['email'] or ''
    elif user['role'] in ('manager', 'senior_manager', 'owner') and user['employee_id']:
        emp = get_employee_by_id(conn, user['employee_id'])
        if emp:
            profile['first_name'] = emp['name']
            profile['last_name'] = emp['surname']
    conn.close()
    return jsonify(profile)

@api.route('/api/profile', methods=['PUT'])
@login_required
def update_profile_route():
    data = request.json
    username = data.get('username', '').strip()
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()
    if not username or not first_name or not last_name:
        return jsonify({'success': False, 'error': 'Логин, имя и фамилия обязательны'}), 400
    conn = get_db()
    try:
        user_id = session['user_id']
        cur = conn.cursor()
        current = cur.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
        if current['username'] != username:
            existing = cur.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            if existing:
                return jsonify({'success': False, 'error': 'Пользователь с таким логином уже существует'}), 400
            cur.execute("UPDATE users SET username = ? WHERE id = ?", (username, user_id))
            session['username'] = username
        user = get_user_by_id(conn, user_id)
        if user['role'] == 'user' and user['customer_id']:
            cur.execute("UPDATE customers SET first_name=?, last_name=?, phone=?, email=? WHERE id=?",
                        (first_name, last_name, phone, email, user['customer_id']))
        elif user['role'] in ('manager', 'senior_manager', 'owner') and user['employee_id']:
            cur.execute("UPDATE employees SET name=?, surname=? WHERE id=?",
                        (first_name, last_name, user['employee_id']))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

@api.route('/api/change_password', methods=['POST'])
@login_required
def change_password_route():
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

@api.route('/api/register', methods=['POST'])
def register_route():
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
    customer_id = create_customer(conn, first_name, last_name, phone, email)
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    create_user(conn, username, password_hash, 'user', customer_id=customer_id)
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@api.route('/api/login', methods=['POST'])
def login_route():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'success': False, 'error': 'Введите логин и пароль'}), 400
    conn = get_db()
    user = get_user_by_username(conn, username)
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

@api.route('/api/logout', methods=['POST'])
def logout_route():
    session.clear()
    return jsonify({'success': True})

@api.route('/api/current_user')
def current_user_route():
    if 'user_id' in session:
        return jsonify({'authenticated': True, 'role': session['role'], 'username': session['username']})
    else:
        return jsonify({'authenticated': False})