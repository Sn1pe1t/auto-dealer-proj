import pytest
import sqlite3
import os

@pytest.fixture
def memory_db():
    """Создает изолированную БД в памяти и накатывает схему для каждого теста."""
    conn = sqlite3.connect(':memory:')
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Ищем schema.sql в корне проекта
    schema_path = os.path.join(os.path.dirname(__file__), '..', 'schema.sql')
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
        
    yield conn  # Передаем подключение в тест
    
    conn.close()  # Закрываем и уничтожаем БД после теста