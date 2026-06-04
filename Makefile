# Команды для управления проектом

.PHONY: install run test clean

# Установка зависимостей
install:
	pip install -r requirements.txt

# Запуск веб-приложения
run:
	python app.py

# Запуск тестов
test:
	pytest tests/ -v --cov=autodealer --cov-report=term-missing

# Очистка кэша pytest и временных файлов
clean:
	rm -rf .pytest_cache
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +