.PHONY: help install run test clean init-db lint test-core test-api

help:
	@echo "Доступные команды:"
	@echo "  make install       - установить зависимости и локальный пакет"
	@echo "  make run           - запустить веб-приложение (через run.py)"
	@echo "  make test          - запустить все тесты (pytest) с покрытием"
	@echo "  make test-core     - запустить только модульные тесты (autodealer_core)"
	@echo "  make test-api      - запустить только API тесты"
	@echo "  make clean         - удалить кэш и временные файлы"
	@echo "  make init-db       - удалить существующую БД (осторожно!)"
	@echo "  make lint          - проверить код flake8"

install:
	pip install -r requirements.txt
	pip install -e .

run:
	python run.py

test:
	pytest tests/ -v --cov=autodealer_core --cov=autodealer --cov=. --cov-report=term-missing --cov-report=html

test-core:
	pytest tests/test_calculations.py tests/test_reporting.py -v

test-api:
	pytest tests/test_api.py tests/test_smoke.py -v

clean:
	rm -rf .pytest_cache .coverage htmlcov
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

init-db:
	rm -f autodealer.db
	@echo "База данных удалена. При следующем запуске будет создана новая."

lint:
	flake8 autodealer/ packages/autodealer_core/ tests/ --max-line-length=120 --ignore=E501,W503 || echo "flake8 не установлен, установите: pip install flake8"