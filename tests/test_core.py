import pytest
import os
import csv
import tempfile
from datetime import datetime
from autodealer_app import load_initial_data, get_car_info, finalize_sale, get_report

# ==================== ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ====================
def _seed_base_data(cur):
    """Заполняет БД базовыми справочниками, сотрудником и клиентом для тестов продаж."""
    cur.execute("INSERT INTO job_titles (id, name) VALUES (1, 'Manager')")
    cur.execute("INSERT INTO employees (id, name, surname, id_job_title) VALUES (1, 'Иван', 'Иванов', 1)")
    cur.execute("INSERT INTO customers (id, first_name, last_name) VALUES (1, 'Петр', 'Петров')")
    cur.execute("INSERT INTO car_categories (id, name) VALUES (1, 'Sedan')")
    cur.execute("INSERT INTO steering_types (id, name) VALUES (1, 'left')")
    cur.execute("INSERT INTO fuel_types (id, name) VALUES (1, 'petrol')")
    cur.execute("INSERT INTO transmissions (id, name) VALUES (1, 'manual')")
    cur.execute("INSERT INTO drives (id, name) VALUES (1, 'front')")
    cur.execute("INSERT INTO conditions (id, name) VALUES (1, 'new')")

# ==================== 1. ТЕСТЫ ИМПОРТА CSV (Анализ данных) ====================

def test_load_initial_data_success(memory_db):
    """Проверка успешной загрузки правильного CSV."""
    fd, path = tempfile.mkstemp(suffix=".csv")
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            # Заполняем ВСЕ справочники, чтобы не ругались FOREIGN KEY
            writer.writerow(["car_categories", "1", "Sedan"])
            writer.writerow(["steering_types", "1", "left"])
            writer.writerow(["fuel_types", "1", "petrol"])
            writer.writerow(["transmissions", "1", "manual"])
            writer.writerow(["drives", "1", "front"])
            writer.writerow(["conditions", "1", "new"])
            # Передаем полную валидную строку машины (18 полей)
            writer.writerow(["cars", "1", "Toyota", "Camry", "2023", "Black", "VIN123", "3000000", "5", "1", "1", "150", "2.0", "1", "1", "1", "1", "0"])
        
        load_initial_data(memory_db, path)
        cur = memory_db.cursor()
        car = cur.execute("SELECT brand, quantity FROM cars WHERE id = 1").fetchone()
        
        assert car is not None
        assert car[0] == "Toyota"
        assert car[1] == 5
    finally:
        os.remove(path)

def test_load_initial_data_dirty_csv(memory_db):
    """Негативный тест: Попытка загрузить CSV со сломанными типами данных (текст вместо числа)."""
    fd, path = tempfile.mkstemp(suffix=".csv")
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["car_categories", "1", "Sedan"])
            # В поле quantity передаем текст "МНОГО", что вызовет ошибку SQLite
            writer.writerow(["cars", "1", "Lada", "Vesta", "2023", "White", "VIN999", "1000000", "МНОГО", "1", "", "", "", "", "", "", "", ""])
        
        load_initial_data(memory_db, path)
        
        cur = memory_db.cursor()
        car = cur.execute("SELECT * FROM cars WHERE vin = 'VIN999'").fetchone()
        assert car is None
    finally:
        os.remove(path)

# ==================== 2. ТЕСТЫ ИНФОРМАЦИИ ОБ АВТО ====================

def test_get_car_info_exists(memory_db):
    """Проверка получения информации о существующей машине."""
    cur = memory_db.cursor()
    _seed_base_data(cur)
    cur.execute("""
        INSERT INTO cars (id, brand, model, year, color, vin, price, quantity, id_category, id_steering, power) 
        VALUES (1, 'BMW', 'X5', 2022, 'White', 'VIN_BMW', 5000000, 2, 1, 1, 249)
    """)
    memory_db.commit()

    info = get_car_info(memory_db, 1)
    assert info is not None
    assert info["description"] == "BMW X5"
    assert info["stock"] == 2

def test_get_car_info_not_found(memory_db):
    """Негативный тест: запрос информации о машине, которой нет в базе."""
    info = get_car_info(memory_db, 999)
    assert info is None

# ==================== 3. ТЕСТЫ БИЗНЕС-ЛОГИКИ ПРОДАЖ ====================

def test_finalize_sale_in_stock(memory_db):
    """Сценарий: Обычная продажа (всё есть на складе)."""
    cur = memory_db.cursor()
    _seed_base_data(cur)
    cur.execute("""
        INSERT INTO cars (id, brand, model, year, color, vin, price, quantity, id_category, id_steering, power) 
        VALUES (1, 'Kia', 'Rio', 2021, 'Red', 'VIN_KIA', 1000000, 5, 1, 1, 100)
    """)
    memory_db.commit()

    cart = [{'car_id': 1, 'quantity': 2, 'price_at_sale': 1000000}]
    success, sale_id = finalize_sale(memory_db, cart, id_employee=1, id_customer=1)
    
    assert success is True
    stock = cur.execute("SELECT quantity FROM cars WHERE id = 1").fetchone()[0]
    assert stock == 3

def test_finalize_sale_boundary_zero(memory_db):
    """Граничный тест: покупка подчистую (ровно столько, сколько есть на складе)."""
    cur = memory_db.cursor()
    _seed_base_data(cur)
    cur.execute("""
        INSERT INTO cars (id, brand, model, year, color, vin, price, quantity, id_category, id_steering, power) 
        VALUES (1, 'Ford', 'Focus', 2020, 'Black', 'VIN_FORD', 1500000, 3, 1, 1, 125)
    """)
    memory_db.commit()

    cart = [{'car_id': 1, 'quantity': 3, 'price_at_sale': 1500000}]
    success, sale_id = finalize_sale(memory_db, cart, id_employee=1, id_customer=1)
    
    assert success is True
    stock = cur.execute("SELECT quantity FROM cars WHERE id = 1").fetchone()[0]
    assert stock == 0

    details = cur.execute("SELECT quantity, in_stock_at_sale FROM sale_details WHERE id_sale = ?", (sale_id,)).fetchall()
    assert len(details) == 1
    assert details[0] == (3, 1)

def test_finalize_sale_preorder(memory_db):
    """Сценарий: Часть из наличия, часть уходит в предзаказ."""
    cur = memory_db.cursor()
    _seed_base_data(cur)
    cur.execute("""
        INSERT INTO cars (id, brand, model, year, color, vin, price, quantity, id_category, id_steering, power) 
        VALUES (1, 'Mazda', '6', 2021, 'Blue', 'VIN_MAZDA', 2000000, 2, 1, 1, 150)
    """)
    memory_db.commit()

    cart = [{'car_id': 1, 'quantity': 5, 'price_at_sale': 2000000}]
    success, sale_id = finalize_sale(memory_db, cart, id_employee=1, id_customer=1)
    
    assert success is True
    stock = cur.execute("SELECT quantity FROM cars WHERE id = 1").fetchone()[0]
    assert stock == 0

    details = cur.execute("SELECT quantity, in_stock_at_sale FROM sale_details WHERE id_sale = ? ORDER BY in_stock_at_sale DESC", (sale_id,)).fetchall()
    assert len(details) == 2
    assert details[0] == (2, 1)
    assert details[1] == (3, 0)

def test_finalize_sale_invalid_car(memory_db):
    """Негативный тест: Попытка купить несуществующий автомобиль."""
    cur = memory_db.cursor()
    _seed_base_data(cur)
    memory_db.commit()

    cart = [{'car_id': 999, 'quantity': 1, 'price_at_sale': 1000000}]
    success, error_msg = finalize_sale(memory_db, cart, id_employee=1, id_customer=1)
    
    assert success is False
    assert "cannot unpack non-iterable NoneType object" in error_msg

def test_finalize_sale_rollback_on_error(memory_db):
    """Негативный тест: Откат транзакции при частичной ошибке в корзине."""
    cur = memory_db.cursor()
    _seed_base_data(cur)
    cur.execute("""
        INSERT INTO cars (id, brand, model, year, color, vin, price, quantity, id_category, id_steering, power) 
        VALUES (1, 'Audi', 'A4', 2022, 'Gray', 'VIN_AUDI', 3000000, 5, 1, 1, 150)
    """)
    memory_db.commit()

    cart = [
        {'car_id': 1, 'quantity': 2, 'price_at_sale': 3000000},
        {'car_id': 999, 'quantity': 1, 'price_at_sale': 1000000}
    ]
    
    success, _ = finalize_sale(memory_db, cart, id_employee=1, id_customer=1)
    
    assert success is False
    stock = cur.execute("SELECT quantity FROM cars WHERE id = 1").fetchone()[0]
    assert stock == 5

# ==================== 4. ТЕСТЫ ФИНАНСОВЫХ ОТЧЕТОВ ====================

def test_get_report_by_date(memory_db):
    """Проверка фильтрации финансового отчета строго по выбранной дате."""
    cur = memory_db.cursor()
    _seed_base_data(cur)
    cur.execute("""
        INSERT INTO cars (id, brand, model, year, color, vin, price, quantity, id_category, id_steering, power) 
        VALUES (1, 'Honda', 'Civic', 2021, 'White', 'VIN_HONDA', 2000000, 10, 1, 1, 140)
    """)
    
    date1 = int(datetime(2026, 6, 1, 12, 0).timestamp())
    date2 = int(datetime(2026, 6, 2, 15, 0).timestamp())

    cur.execute("INSERT INTO sales (id, sale_date, id_customer, id_employee, total_amount) VALUES (1, ?, 1, 1, 2000000)", (date1,))
    cur.execute("INSERT INTO sale_details (id_sale, id_car, quantity, price_at_sale, in_stock_at_sale) VALUES (1, 1, 1, 2000000, 1)")
    
    cur.execute("INSERT INTO sales (id, sale_date, id_customer, id_employee, total_amount) VALUES (2, ?, 1, 1, 4000000)", (date1,))
    cur.execute("INSERT INTO sale_details (id_sale, id_car, quantity, price_at_sale, in_stock_at_sale) VALUES (2, 1, 2, 2000000, 1)")

    cur.execute("INSERT INTO sales (id, sale_date, id_customer, id_employee, total_amount) VALUES (3, ?, 1, 1, 2000000)", (date2,))
    cur.execute("INSERT INTO sale_details (id_sale, id_car, quantity, price_at_sale, in_stock_at_sale) VALUES (3, 1, 1, 2000000, 1)")
    
    memory_db.commit()

    report = get_report(memory_db, '2026-06-01')
    
    assert len(report) == 1
    car_name, total_qty, total_revenue = report[0]
    
    assert car_name == "Honda Civic"
    assert total_qty == 3
    assert total_revenue == 6000000