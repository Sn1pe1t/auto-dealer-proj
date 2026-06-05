# Автосалон CRM

Веб-приложение для управления заказами в автосалоне.
Поддерживает ролевую модель: клиент, менеджер, старший менеджер, владелец.
Клиенты могут оформлять заказы (с предзаказом при недостатке на складе), просматривать свою историю и топ продаж.
Менеджеры и владельцы имеют доступ к отчётам, управлению персоналом, загрузке автомобилей из CSV и просмотру всех заказов.

## Основные возможности

Каталог автомобилей с фильтрацией (категория, руль, мощность, топливо, КПП, привод, состояние, только в наличии)

Корзина и оформление заказа (часть заказа сразу со склада, остальное – предзаказ)

Аутентификация и регистрация пользователей

Роли: user, manager, senior_manager, owner

История заказов с детализацией

Отчёты по дате и топ-10 продаж

Управление пользователями (назначение ролей)

Профиль пользователя (изменение личных данных и пароля)

## Технологии

Backend: Python 3.11, Flask, SQLite

Frontend: HTML, CSS, JavaScript (fetch API)

Тестирование: pytest, pytest-cov

Автоматизация: Makefile

Контейнеризация: Docker, Docker Compose

Документация: MkDocs (собирается из Markdown + Mermaid)

## Структура проекта

```
.
├── autodealer/ # Основное Flask-приложение
│ ├── init.py # Фабрика приложения
│ ├── auth.py # Декораторы аутентификации
│ ├── db_queries.py # Все SQL-запросы
│ ├── routes.py # Blueprint с маршрутами API
│ └── templates/ # HTML-шаблоны (index.html)
├── docs/ # Документация (спецификация, архитектура)
├── tests/ # Модульные и интеграционные тесты
├── run.py # Точка входа для запуска сервера
├── schema.sql # Схема базы данных
├── init_data.csv # Начальные данные (справочники, тестовые пользователи, автомобили)
├── requirements.txt # Зависимости (Flask, autodealer-core)
├── requirements-dev.txt # Зависимости для разработки (pytest, mkdocs, flake8 и др.)
├── Makefile # Автоматизация команд
├── Dockerfile # Образ приложения
├── docker-compose.yaml # Локальный запуск через Compose
└── README.md # Этот файл

```

## Быстрый старт (локально)

Клонировать репозиторий
`git clone https://github.com/Sn1pe1t/auto-dealer-proj.git`
`cd auto-dealer-proj`

Создать виртуальное окружение
`python -m venv venv`
`source venv/bin/activate # Linux/Mac`
`venv\Scripts\activate # Windows`

Установить зависимости
`make install`
или вручную:
`pip install -r requirements.txt`
(Библиотека autodealer-core устанавливается из PyPI)

Запустить приложение
`make run`
Сервер будет доступен по адресу: http://127.0.0.1:5000

## Запуск в Docker (рекомендуемый способ)

Убедитесь, что Docker Desktop запущен.

`make docker-up`

Приложение поднимется в контейнере, порт 5000 будет проброшен. База данных сохраняется в томе, данные не теряются при перезапуске.

## Тестирование

`make test # все тесты + отчёт о покрытии`
`make test-core # только модульные тесты autodealer-core`
`make test-api # только API тесты`

Покрытие можно посмотреть в htmlcov/index.html.

## Документация

Документация собирается с помощью MkDocs. Установите дополнительные зависимости:

`pip install -r requirements-dev.txt`

Затем:

`make docs`

Сгенерированный сайт появится в папке site/.
Документация включает:

Спецификацию предметной области (docs/specification.md)

Архитектурное описание с диаграммами C4 и sequence (docs/architecture.md)

## Тестовые учётные записи

Роль	Логин	Пароль
Владелец	owner	owner
Старший менеджер	john	john
Менеджер	manager	manager
Клиент	ivan	ivan
Клиент	maria	maria
## Доступные команды Make

Команда	Действие
make install	Установить зависимости (requirements.txt)
make run	Запустить приложение (локально)
make test	Запустить все тесты с отчётом о покрытии
make test-core	Только модульные тесты
make test-api	Только API тесты
make clean	Удалить кэш, временные файлы, отчёты
make init-db	Удалить autodealer.db (сброс данных)
make lint	Проверить код flake8 (если установлен)
make docs	Собрать документацию MkDocs
make docker-up	Поднять контейнеры (docker-compose)
make docker-down	Остановить и удалить контейнеры
make docker-build	Только собрать образ
## Переиспользуемая библиотека

Доменная логика (расчёт заказа, агрегация отчётов) вынесена в отдельный пакет autodealer-core, опубликованный на PyPI:

https://pypi.org/project/autodealer-core/

Установка из PyPI:

`pip install autodealer-core`

Использование:

```
from autodealer_core import calculate_sale_items, aggregate_report, top_sales
```

## Вклад в проект

Если вы хотите предложить улучшения, создайте issue, затем ветку и Pull Request.
Убедитесь, что тесты проходят, а документация обновлена.

## Лицензия

MIT

## Контакты

Автор: Sn1pe1t
Email: enderman303040@gmail.com
GitHub: Sn1pe1t/auto-dealer-proj