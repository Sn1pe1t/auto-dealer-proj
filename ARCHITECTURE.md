# Архитектура проекта после рефакторинга

## Структура

```
auto-dealer-proj/
├── autodealer_core/              ← 📚 БИБЛИОТЕКА (для PyPI)
│   ├── __init__.py               ← Экспорты API
│   ├── database.py               ← Инициализация БД, загрузка данных
│   ├── models.py                 ← Бизнес-логика (6 функций)
│   └── schema.sql                ← SQL схема БД
│
├── db-proj-car-dealership/       ← 🖥️ GUI ПРИЛОЖЕНИЕ
│   ├── autodealer_app.py         ← Переписано для импорта из библиотеки
│   ├── requirements.txt           ← autodealer-core>=0.1.0
│   ├── autodealer.db             ← БД (создается при запуске)
│   ├── init_data.csv             ← Начальные данные
│   └── app_old.py                ← Резервная копия оригинального кода
│
├── examples/                     ← 📖 ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
│   ├── README.md                 ← Документация примеров
│   └── basic_usage.py            ← Пример работы с API
│
├── setup.py                      ← Конфигурация для PyPI
├── MANIFEST.in                   ← Включить schema.sql в пакет
├── README.md                     ← Документация проекта и библиотеки
├── Makefile                      ← Команды для разработки
└── .git/                         ← Git репозиторий
```

## Разделение ответственности

### autodealer_core (библиотека)

**Отвечает за:**
- Инициализацию БД (`init_db`, `load_initial_data`)
- Работу с данными (`get_car_info`, `finalize_sale`, `get_report` и т.д.)
- Бизнес-логику операций
- Схему БД (`schema.sql`)

**Не содержит:**
- GUI код (Tkinter)
- Интерактивные диалоги
- Визуализацию данных

### autodealer_app (приложение)

**Отвечает за:**
- GUI интерфейс (Tkinter)
- Взаимодействие с пользователем
- Визуализация данных
- Обработка пользовательских действий

**Зависит от:**
- `autodealer_core` (импортирует функции)
- `tkinter` (встроено в Python)
- `csv` (встроено в Python)

## API библиотеки (autodealer_core)

### database.py
```python
init_db(db_path, schema_path, init_data_path) → sqlite3.Connection
load_initial_data(conn, csv_file) → None
```

### models.py
```python
get_car_info(conn, car_id) → dict
finalize_sale(conn, cart_items, id_employee, id_customer) → (bool, int|str)
get_report(conn, date_str) → list[tuple]
get_sales_list(conn, limit=50) → list[tuple]
get_sale_details(conn, sale_id) → list[tuple]
```

## Команды (Makefile)

### Приложение
```bash
make run           # Запустить приложение
make init          # Инициализировать БД
make clean         # Очистить БД и кэш
```

### Библиотека
```bash
make install-lib   # Установить для разработки
make build-lib     # Собрать пакет
make publish       # Опубликовать на PyPI
```

### Разработка
```bash
make lint          # Проверить код
make format        # Форматировать код
make backup        # Резервная копия БД
```

## Преимущества рефакторинга

✅ **Переиспользуемость** — логика БД отделена от GUI  
✅ **Публикация** — можно выложить на PyPI  
✅ **Расширяемость** — легко добавить новые интерфейсы (CLI, API, веб и т.д.)  
✅ **Тестируемость** — библиотека тестируется отдельно  
✅ **Документация** — четкое разделение ответственности  

## Использование библиотеки в других проектах

После публикации на PyPI:

```bash
pip install autodealer-core
```

Затем в своем коде:

```python
from autodealer_core import init_db, get_car_info, finalize_sale

conn = init_db('my_db.db', 'path/to/schema.sql', 'path/to/data.csv')
car = get_car_info(conn, car_id=1)
success, sale_id = finalize_sale(conn, items, emp_id, cust_id)
```

## Версионирование

Текущая версия библиотеки: **0.1.0**

Следить за обновлениями в `autodealer_core/__init__.py`

## Дальнейшие шаги

1. Добавить тесты (`tests/` папка)
2. Добавить больше примеров в `examples/`
3. Создать CLI интерфейс с `argparse` или `click`
4. Создать REST API с `Flask` или `FastAPI`
5. Опубликовать на PyPI
6. Добавить CI/CD конвейер (GitHub Actions)
