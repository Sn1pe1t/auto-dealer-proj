# Архитектурное описание

## 1. Контекстная диаграмма (C4 level 1)
```mermaid
graph TD
    User[Пользователь] -->|HTTP| App[Автосалон CRM]
    Reviewer[Рецензент - Проверяющий] -->|Git clone / make| App
    App -->|SQL| DB[(SQLite DB)]
    App -->|CSV import| CSV[init_data.csv]
    User -->|CLI| PyPI[pip install autodealer-core]
    Admin[Администратор] -->|Docker commands| Docker[Docker Engine]
    Docker -->|контейнер| App
    CI[CI/CD GitHub Actions] -->|запуск тестов| App
    CI -->|сборка документации| DocsSite[Сайт документации]
    Developer[Разработчик] -->|publish| PyPIRegistry[PyPI registry]
```

Система представляет собой веб-приложение, которое взаимодействует с базой данных SQLite и может загружать начальные данные из CSV. Пользователи обращаются через браузер. Библиотека `autodealer-core` может использоваться отдельно (например, в CLI). Администратор управляет развёртыванием через Docker.

## 2. Диаграмма контейнеров (C4 level 2)

```mermaid
graph TD
    Browser[Браузер] -->|HTTP/HTTPS| Flask[Flask-приложение]
    Flask -->|SQLite3| DB[(SQLite DB)]
    Flask -->|чтение| CSV[init_data.csv]
    Flask -->|вызовы| Core[Библиотека autodealer-core]
    Core -->|чистые функции| Logic[Доменная логика: расчёт заказа, отчёты]
    Flask -->|рендеринг| Templates[Шаблоны HTML/CSS/JS]
    Browser -->|загрузка| Templates
    Flask -->|сессии| Session[Сессии Flask]
    Core -->|не зависит от БД| Pure[Чистые функции]
```

Flask-приложение – содержит маршруты API, аутентификацию, работу с БД.

SQLite DB – хранит данные о пользователях, автомобилях, заказах.

Библиотека autodealer-core – независимый пакет, опубликованный на PyPI. Содержит чистое доменное поведение.

CSV-файл – используется для инициализации справочников и тестовых данных.

## 3. Use case диаграмма (основные сценарии)

```mermaid
graph LR
    subgraph Клиент
        A1[Просмотр каталога]
        A2[Фильтрация авто]
        A3[Управление корзиной]
        A4[Оформление заказа]
        A5[Просмотр своих заказов]
        A6[Просмотр топа продаж]
        A7[Редактирование профиля]
        A8[Смена пароля]
    end

    subgraph Менеджер
        B1[Всё из клиента]
        B2[Оформление заказа на любого]
        B3[Просмотр всех заказов]
        B4[Формирование отчёта по дате]
        B5[Загрузка автомобилей из CSV]
    end

    subgraph Старший менеджер
        C1[Всё из менеджера]
        C2[Назначение менеджеров]
        C3[Снятие менеджеров]
    end

    subgraph Владелец
        D1[Всё из старшего менеджера]
        D2[Назначение старших менеджеров]
        D3[Снятие старших менеджеров]
        D4[Полный доступ к данным]
    end

    Client[Клиент] --> A1 & A2 & A3 & A4 & A5 & A6 & A7 & A8
    Manager[Менеджер] --> B1 & B2 & B3 & B4 & B5
    Senior[Старший менеджер] --> C1 & C2 & C3
    Owner[Владелец] --> D1 & D2 & D3 & D4

    Manager -.->|расширяет| Client
    Senior -.->|расширяет| Manager
    Owner -.->|расширяет| Senior
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

## 5. Принятые архитектурные решения

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

## 6. Используемые инструменты разработки

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