import pytest
import os
import csv
import tempfile
from autodealer_app import load_initial_data, get_car_info, finalize_sale

# --- Тест 1: Загрузка данных из CSV ---
def test_load_initial_data(memory_db):
    fd, path = tempfile.mkstemp(suffix=".csv")
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            # Нам нужно сначала загрузить справочники, иначе cars выдаст ошибку FOREIGN KEY
            writer.writerow(["car_categories", "1", "Sedan"])
            writer.writerow(["steering_types", "1", "left"])
            writer.writerow(["fuel_types", "1", "petrol"])
            writer.writerow(["transmissions", "1", "manual"])
            writer.writerow(["drives", "1", "front"])
            writer.writerow(["conditions", "1", "new"])
            # Теперь добавляем машину, ссылающуюся на id=1 во всех внешних ключах
            writer.writerow(["cars", "1", "Toyota", "Camry", "2023", "Black", "VIN123", "3000000", "5", "1", "1", "150", "2.0", "1", "1", "1", "1", "0"])
        
        load_initial_data(memory_db, path)
        
        cur = memory_db.cursor()
        cur.execute("SELECT brand, model, quantity FROM cars WHERE id = 1")
        car = cur.fetchone()
        
        assert car is not None
        assert car[0] == "Toyota"
        assert car[1] == "Camry"
        assert car[2] == 5
    finally:
        os.remove(path)


# --- Тест 2: Получение информации об автомобиле ---
def test_get_car_info(memory_db):
    cur = memory_db.cursor()
    # Заполняем абсолютно все связанные справочники для таблицы cars
    cur.execute("INSERT INTO car_categories (id, name) VALUES (1, 'SUV')")
    cur.execute("INSERT INTO steering_types (id, name) VALUES (1, 'left')")
    cur.execute("INSERT INTO fuel_types (id, name) VALUES (1, 'petrol')")
    cur.execute("INSERT INTO transmissions (id, name) VALUES (1, 'manual')")
    cur.execute("INSERT INTO drives (id, name) VALUES (1, 'front')")
    cur.execute("INSERT INTO conditions (id, name) VALUES (1, 'new')")
    
    # Вставляем машину строго по полям из вашей schema.sql (без несуществующего in_stock)
    cur.execute("""
        INSERT INTO cars (id, brand, model, year, color, vin, price, quantity, id_category, id_steering, power, engine_volume, id_fuel_type, id_transmission, id_drive, id_condition, mileage) 
        VALUES (1, 'BMW', 'X5', 2022, 'White', 'VIN_BMW_TEST', 5000000, 2, 1, 1, 249, 3.0, 1, 1, 1, 1, 0)
    """)
    memory_db.commit()

    info = get_car_info(memory_db, 1)

    assert info is not None
    assert info["description"] == "BMW X5"
    assert info["year"] == 2022
    assert info["price"] == 5000000
    assert info["stock"] == 2


# --- Тест 3: Обычная продажа (товар в наличии) ---
def test_finalize_sale_in_stock(memory_db):
    cur = memory_db.cursor()
    # Подготовка инфраструктуры со связями
    cur.execute("INSERT INTO job_titles (id, name) VALUES (1, 'Manager')")
    cur.execute("INSERT INTO employees (id, name, surname, id_job_title) VALUES (1, 'Иван', 'Иванов', 1)")
    cur.execute("INSERT INTO customers (id, first_name, last_name) VALUES (1, 'Петр', 'Петров')")
    
    # Справочники для машины
    cur.execute("INSERT INTO car_categories (id, name) VALUES (1, 'Sedan')")
    cur.execute("INSERT INTO steering_types (id, name) VALUES (1, 'left')")
    cur.execute("INSERT INTO fuel_types (id, name) VALUES (1, 'petrol')")
    cur.execute("INSERT INTO transmissions (id, name) VALUES (1, 'manual')")
    cur.execute("INSERT INTO drives (id, name) VALUES (1, 'front')")
    cur.execute("INSERT INTO conditions (id, name) VALUES (1, 'new')")
    
    cur.execute("""
        INSERT INTO cars (id, brand, model, year, color, vin, price, quantity, id_category, id_steering, power, engine_volume, id_fuel_type, id_transmission, id_drive, id_condition, mileage) 
        VALUES (1, 'Kia', 'Rio', 2021, 'Red', 'VIN_KIA_TEST', 1000000, 5, 1, 1, 100, 1.4, 1, 1, 1, 1, 0)
    """)
    memory_db.commit()

    cart = [{'car_id': 1, 'quantity': 2, 'price_at_sale': 1000000}]
    
    success, sale_id = finalize_sale(memory_db, cart, id_employee=1, id_customer=1)
    
    assert success is True
    assert isinstance(sale_id, int)

    # Проверяем остаток на складе (было 5, купили 2 -> осталось 3)
    stock = cur.execute("SELECT quantity FROM cars WHERE id = 1").fetchone()[0]
    assert stock == 3

    # Проверяем детали продажи
    details = cur.execute("SELECT quantity, in_stock_at_sale FROM sale_details WHERE id_sale = ?", (sale_id,)).fetchall()
    assert len(details) == 1
    assert details[0][0] == 2
    assert details[0][1] == 1


# --- Тест 4: Смешанная продажа (частично предзаказ) ---
def test_finalize_sale_preorder(memory_db):
    cur = memory_db.cursor()
    cur.execute("INSERT INTO job_titles (id, name) VALUES (1, 'Manager')")
    cur.execute("INSERT INTO employees (id, name, surname, id_job_title) VALUES (1, 'Иван', 'Иванов', 1)")
    cur.execute("INSERT INTO customers (id, first_name, last_name) VALUES (1, 'Петр', 'Петров')")
    
    cur.execute("INSERT INTO car_categories (id, name) VALUES (1, 'Sedan')")
    cur.execute("INSERT INTO steering_types (id, name) VALUES (1, 'left')")
    cur.execute("INSERT INTO fuel_types (id, name) VALUES (1, 'petrol')")
    cur.execute("INSERT INTO transmissions (id, name) VALUES (1, 'manual')")
    cur.execute("INSERT INTO drives (id, name) VALUES (1, 'front')")
    cur.execute("INSERT INTO conditions (id, name) VALUES (1, 'new')")
    
    cur.execute("""
        INSERT INTO cars (id, brand, model, year, color, vin, price, quantity, id_category, id_steering, power, engine_volume, id_fuel_type, id_transmission, id_drive, id_condition, mileage) 
        VALUES (1, 'Mazda', '6', 2021, 'Blue', 'VIN_MAZDA_TEST', 2000000, 2, 1, 1, 150, 2.0, 1, 1, 1, 1, 0)
    """)
    memory_db.commit()

    # Покупаем 5 штук при наличии 2
    cart = [{'car_id': 1, 'quantity': 5, 'price_at_sale': 2000000}]
    
    success, sale_id = finalize_sale(memory_db, cart, id_employee=1, id_customer=1)
    
    assert success is True

    # На складе должно остаться 0
    stock = cur.execute("SELECT quantity FROM cars WHERE id = 1").fetchone()[0]
    assert stock == 0

    # Проверяем разбиение на "из наличия" и "предзаказ"
    details = cur.execute("SELECT quantity, in_stock_at_sale FROM sale_details WHERE id_sale = ? ORDER BY in_stock_at_sale DESC", (sale_id,)).fetchall()
    
    assert len(details) == 2
    assert details[0] == (2, 1)  # 2 штуки из наличия
    assert details[1] == (3, 0)  # 3 штуки в предзаказ