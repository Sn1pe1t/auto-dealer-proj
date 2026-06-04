from flask import Flask, render_template, request, redirect, flash, jsonify
import sqlite3
from autodealer.core import finalize_sale, init_db, get_car_info

app = Flask(__name__)
app.secret_key = 'auto_dealer_secret_key'

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db()
    init_db(conn)
    # Загружаем данные для фильтров
    cars = conn.execute("SELECT id, brand, model, year, price, quantity FROM cars").fetchall()
    categories = conn.execute("SELECT * FROM car_categories").fetchall()
    employees = conn.execute("SELECT id, name, surname FROM employees").fetchall()
    customers = conn.execute("SELECT id, first_name, last_name FROM customers").fetchall()
    conn.close()
    return render_template('index.html', cars=cars, categories=categories, 
                           employees=employees, customers=customers)

@app.route('/sell', methods=['POST'])
def sell():
    conn = get_db()
    try:
        # В реальном приложении здесь будет логика обработки JSON корзины
        # Сейчас для примера берем данные из формы
        car_id = int(request.form.get('car_id'))
        qty = int(request.form.get('quantity'))
        emp_id = int(request.form.get('employee_id'))
        cust_id = int(request.form.get('customer_id'))
        
        car_info = get_car_info(conn, car_id)
        cart = [{'car_id': car_id, 'quantity': qty, 'price_at_sale': car_info['price']}]
        
        success, result = finalize_sale(conn, cart, emp_id, cust_id)
        if success:
            flash(f"Заказ №{result} успешно оформлен!", "success")
        else:
            flash(f"Ошибка: {result}", "danger")
    finally:
        conn.close()
    return redirect('/')