# Команды для управления проектом

.PHONY: help install run test clean init-db lint

help:
	@echo "Доступные команды:"
	@echo "  make install   - установить зависимости и локальный пакет autodealer_core"
	@echo "  make run       - запустить веб-приложение"
	@echo "  make test      - запустить тесты (pytest) с покрытием"
	@echo "  make clean     - удалить кэш и временные файлы"
	@echo "  make init-db   - удалить существующую БД и пересоздать (осторожно!)"
	@echo "  make lint      - проверить код flake8 (если установлен)"

# Установка зависимостей
install:
	pip install -r requirements.txt
	pip install -e .

# Запуск веб-приложения
run:
	python app.py

# Запуск тестов с покрытием
test:
	pytest tests/ -v --cov=autodealer_core --cov=app --cov=. --cov-report=term-missing --cov-report=html

# Очистка кэша pytest и временных файлов
clean:
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Пересоздание базы данных (удаляет текущую БД)
init-db:
	rm -f autodealer.db
	@echo "База данных autodealer.db удалена. При следующем запуске будет создана новая из schema.sql и init_data.csv."

# Линтер (требуется flake8)
lint:
	flake8 app/ packages/autodealer_core/ tests/ --max-line-length=120 --ignore=E501,W503