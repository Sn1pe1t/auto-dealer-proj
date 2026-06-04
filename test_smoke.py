import os

def test_infrastructure_files_exist():
    # Проверяем, что критически важные файлы на месте
    assert os.path.exists("schema.sql"), "Файл schema.sql отсутствует!"
    assert os.path.exists("init_data.csv"), "Файл init_data.csv отсутствует!"

def test_schema_is_not_empty():
    # Проверяем, что схема содержит SQL-код
    with open("schema.sql", "r", encoding="utf-8") as f:
        content = f.read()
    assert "CREATE TABLE" in content, "Схема базы данных кажется пустой или некорректной!"
