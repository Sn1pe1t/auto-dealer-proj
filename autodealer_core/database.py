"""
Модуль для инициализации и управления базой данных автосалона.
"""
import sqlite3
import csv
import os


def init_db(db_path='autodealer.db', schema_path='schema.sql', init_data_path='init_data.csv'):
    """
    Инициализирует базу данных: создает таблицы и загружает начальные данные.
    
    Args:
        db_path: Путь к файлу БД (по умолчанию 'autodealer.db')
        schema_path: Путь к файлу с SQL схемой (по умолчанию 'schema.sql')
        init_data_path: Путь к CSV файлу с начальными данными (по умолчанию 'init_data.csv')
    
    Returns:
        sqlite3.Connection: Подключение к БД
    
    Raises:
        FileNotFoundError: Если schema_path или init_data_path не найдены
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Файл схемы не найден: {schema_path}")
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    
    # Удаляем старый триггер, если он остался от предыдущих версий
    conn.execute("DROP TRIGGER IF EXISTS deduct_quantity")
    
    # Загружаем начальные данные только если таблица cars пуста
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM cars")
    if cur.fetchone()[0] == 0:
        if os.path.exists(init_data_path):
            load_initial_data(conn, init_data_path)
    
    return conn


def load_initial_data(conn, csv_file):
    """
    Загружает начальные данные из CSV файла в БД.
    
    Args:
        conn: Подключение к БД
        csv_file: Путь к CSV файлу
    """
    table_columns = {
        'steering_types': ['id', 'name'],
        'fuel_types': ['id', 'name'],
        'transmissions': ['id', 'name'],
        'drives': ['id', 'name'],
        'conditions': ['id', 'name'],
        'job_titles': ['id', 'name'],
        'employees': ['id', 'name', 'surname', 'id_job_title'],
        'customers': ['id', 'first_name', 'last_name', 'phone', 'email'],
        'car_categories': ['id', 'name'],
        'cars': ['id', 'brand', 'model', 'year', 'color', 'vin', 'price', 'quantity', 'id_category',
                 'id_steering', 'power', 'engine_volume', 'id_fuel_type', 'id_transmission', 'id_drive', 'id_condition', 'mileage']
    }
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].startswith('#'):
                continue
            table = row[0].strip()
            values = row[1:]
            if table not in table_columns:
                continue
            cols = table_columns[table]
            
            # Для cars: преобразуем пустой mileage в None
            if table == 'cars' and len(values) >= len(cols):
                if values[-1] == '' or values[-1] is None:
                    values[-1] = None
                else:
                    try:
                        values[-1] = int(values[-1])
                    except:
                        values[-1] = None
            
            if len(values) != len(cols):
                print(f"Пропущена строка для {table}: ожидалось {len(cols)} значений, получено {len(values)}")
                continue
            
            placeholders = ','.join(['?' for _ in cols])
            sql = f"INSERT OR IGNORE INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
            try:
                conn.execute(sql, values)
            except Exception as e:
                print(f"Ошибка вставки в {table}: {e} (строка: {row})")
    
    conn.commit()
