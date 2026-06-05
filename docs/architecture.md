# Архитектурное описание

## 1. Контекстная диаграмма (C4 level 1)
```mermaid
graph TD
    User[Пользователь] -->|HTTP| App[Автосалон]
    App -->|SQL| DB[(SQLite DB)]
    App -->|CSV import| CSV[init_data.csv]
    User -->|CLI| PyPI[pip install autodealer-core]
    Admin[Администратор] -->|Docker commands| Docker[Docker Engine]
    Docker -->|контейнер| App
```

Система представляет собой веб-приложение, которое взаимодействует с базой данных SQLite и может загружать начальные данные из CSV. Пользователи обращаются через браузер. Библиотека `autodealer-core` может использоваться отдельно (например, в CLI). Администратор управляет развёртыванием через Docker.

## 2. Диаграмма контейнеров (C4 level 2)

```mermaid
graph TD
    Browser[Браузер] -->|HTTP/HTTPS| Flask[Flask-приложение]
    Flask -->|SQLite3| DB[(SQLite DB)]
    Flask -->|CSV| CSV[init_data.csv]
    Flask -->|вызовы| Core[Библиотека autodealer-core]
    Core -->|чистые функции| Logic[Доменная логика: расчёт заказа, отчёты]
    Flask -->|рендеринг| Templates[Шаблоны HTML/CSS/JS]
    Browser -->|загрузка| Templates
```

Flask-приложение – содержит маршруты API, аутентификацию, работу с БД.

SQLite DB – хранит данные о пользователях, автомобилях, заказах.

Библиотека autodealer-core – независимый пакет, опубликованный на PyPI. Содержит чистое доменное поведение.

CSV-файл – используется для инициализации справочников и тестовых данных.

## 3. Use case диаграмма (основные сценарии)

```mermaid
graph TD
    User[Клиент] -->|Каталог, фильтры, корзина, заказ, свои заказы, топ, профиль| S[Автосалон CRM]
    Manager[Менеджер] -->|Всё из клиента + заказ на любого + все заказы + отчёты + загрузка CSV| S
    Senior[Старший менеджер] -->|Всё из менеджера + назначение менеджеров| S
    Owner[Владелец] -->|Всё из старшего + назначение старших + полный доступ| S
```

## 4. Диаграмма последовательности для сценария «Оформление заказа»

```mermaid
sequenceDiagram
    participant Client as Клиент (браузер)
    participant Flask as Flask-приложение
    participant DB as SQLite
    participant Core as autodealer-core

    Client->>Flask: POST /api/login (логин/пароль)
    Flask->>DB: SELECT * FROM users WHERE username=?
    DB-->>Flask: пользователь
    Flask-->>Client: session cookie

    Client->>Flask: GET /api/cars (фильтры)
    Flask->>DB: SELECT ... WHERE ...
    DB-->>Flask: список автомобилей
    Flask-->>Client: JSON

    Client->>Flask: POST /api/finalize_sale (корзина, id_employee)
    Flask->>DB: BEGIN TRANSACTION

    loop для каждого автомобиля в корзине
        Flask->>DB: SELECT quantity, price FROM cars WHERE id=?
        DB-->>Flask: остаток, цена
    end

    Flask->>Core: calculate_sale_items(cart_totals, stock_map)
    Core-->>Flask: список sale_items (in_stock + preorder)

    alt есть позиции in_stock
        Flask->>DB: INSERT INTO sales (заказ)
        loop для каждого sale_item с in_stock_flag=1
            Flask->>DB: INSERT INTO sale_details (из наличия)
            Flask->>DB: UPDATE cars SET quantity = quantity - ?
        end
    end

    alt есть позиции preorder
        loop для каждого sale_item с in_stock_flag=0
            Flask->>DB: INSERT INTO sale_details (предзаказ)
        end
        Note right of Flask: Количество на складе не уменьшается
    end

    Flask->>DB: COMMIT
    Flask-->>Client: {success: true, sale_id: ...}

    opt ошибка (например, отсутствие авто)
        Flask->>DB: ROLLBACK
        Flask-->>Client: {success: false, error: ...}
    end
```

## 5. Модель данных (упрощённая ER-диаграмма)

```mermaid
erDiagram
    users {
        int id PK
        string username
        string password_hash
        string role
        int customer_id FK
        int employee_id FK
    }
    customers {
        int id PK
        string first_name
        string last_name
        string phone
        string email
    }
    employees {
        int id PK
        string name
        string surname
        int id_job_title FK
    }
    job_titles {
        int id PK
        string name
    }
    cars {
        int id PK
        string brand
        string model
        int year
        string vin
        int price
        int quantity
        int id_category FK
        int id_steering FK
        int power
        float engine_volume
        int id_fuel_type FK
        int id_transmission FK
        int id_drive FK
        int id_condition FK
        int mileage
    }
    sales {
        int id PK
        float sale_date
        int id_customer FK
        int id_employee FK
        float total_amount
    }
    sale_details {
        int id PK
        int id_sale FK
        int id_car FK
        int quantity
        float price_at_sale
        int in_stock_at_sale
    }

    users ||--o| customers : "customer_id"
    users ||--o| employees : "employee_id"
    employees ||--|| job_titles : "id_job_title"
    sales ||--|| customers : "id_customer"
    sales ||--|| employees : "id_employee"
    sale_details ||--|| sales : "id_sale"
    sale_details ||--|| cars : "id_car"
```

## 6. Принятые архитектурные решения

| Решение | Обоснование |
|---------|-------------|
| Выделение `autodealer-core` в отдельную библиотеку | Переиспользование доменной логики в CLI, Telegram-боте и других интерфейсах. Публикация на PyPI. |
| Использование SQLite | Простота, не требует отдельного сервера, достаточно для учебного проекта. Данные сохраняются в одном файле. |
| Flask без сложных расширений | Минимализм, легкость, быстрая разработка. |
| Ролевая модель через декораторы | Чёткое разделение прав, легко расширять. |
| Контейнеризация (Docker, Compose) | Воспроизводимость, один запуск для проверяющего. |
| Makefile для автоматизации | Единые команды для всех операций: установка, запуск, тесты, документация. |
| Тестирование pytest + покрытие | Защита от регрессий, документация поведения. |
| MkDocs + Mermaid | Автоматическая сборка документации с диаграммами, хранение исходников в репозитории. |

## 7. Используемые инструменты разработки

| Инструмент | Назначение |
|------------|------------|
| Python 3.11 | Язык программирования |
| Flask | Web-фреймворк |
| SQLite | База данных |
| pytest | Тестирование |
| pytest-cov | Покрытие кода |
| flake8 | Линтер |
| MkDocs + Material | Генератор статической документации |
| Docker, Compose | Контейнеризация |
| Make | Автоматизация команд |
| Git | Контроль версий |