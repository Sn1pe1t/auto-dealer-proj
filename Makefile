.PHONY: help run init clean test lint format

help:
	@echo "=== Auto-Dealer Project Commands ==="
	@echo "make run      - Запустить приложение"
	@echo "make init     - Инициализировать БД и загрузить данные"
	@echo "make clean    - Удалить БД и кэш Python"
	@echo "make lint     - Проверить код на ошибки (pylint)"
	@echo "make format   - Форматировать код (black)"
	@echo "make dev      - Установить dev зависимости"
	@echo "make backup   - Создать резервную копию БД"
	@echo ""

# Запуск приложения
run:
	cd db-proj-car-dealership && python autodealer_app.py

# Инициализация БД
init:
	cd db-proj-car-dealership && python -c "from autodealer_app import init_db; init_db()"
	@echo "✓ БД инициализирована"

# Очистка (удалить БД и __pycache__)
clean:
	cd db-proj-car-dealership && del /f autodealer.db 2>nul || true
	cd db-proj-car-dealership && rmdir /s /q __pycache__ 2>nul || true
	@echo "✓ Файлы очищены"

# Проверка кода (требует pylint)
lint:
	cd db-proj-car-dealership && python -m pylint autodealer_app.py || true

# Форматирование кода (требует black)
format:
	cd db-proj-car-dealership && python -m black autodealer_app.py
	@echo "✓ Код отформатирован"

# Установка dev зависимостей
dev:
	pip install pylint black

# Резервная копия БД
backup:
	@powershell -Command "copy db-proj-car-dealership\autodealer.db db-proj-car-dealership\autodealer_backup_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').db"
	@echo "✓ Резервная копия создана"

# Перестартовать (очистить и запустить)
restart: clean init run

.DEFAULT_GOAL := help
