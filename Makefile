.PHONY: help run init clean test lint format install-dev install-lib publish

help:
	@echo "=== Auto-Dealer Project Commands ==="
	@echo ""
	@echo "Приложение:"
	@echo "  make run         - Запустить GUI приложение"
	@echo "  make init        - Инициализировать БД и загрузить данные"
	@echo "  make clean       - Удалить БД и кэш Python"
	@echo ""
	@echo "Библиотека (autodealer_core):"
	@echo "  make install-lib - Установить библиотеку локально (для разработки)"
	@echo "  make publish     - Собрать и опубликовать на PyPI"
	@echo ""
	@echo "Разработка:"
	@echo "  make install-dev - Установить dev зависимости"
	@echo "  make lint        - Проверить код на ошибки (pylint)"
	@echo "  make format      - Форматировать код (black)"
	@echo "  make backup      - Создать резервную копию БД"
	@echo "  make restart     - Перезагрузить всё (clean + init + run)"
	@echo ""

# ==================== Приложение ====================

# Запуск приложения
run: install-lib
	cd db-proj-car-dealership && python autodealer_app.py

# Инициализация БД
init: install-lib
	cd db-proj-car-dealership && python -c "from autodealer_core import init_db; import os; schema = os.path.join('..', 'autodealer_core', 'schema.sql'); init_db('autodealer.db', schema, 'init_data.csv')"
	@echo "✓ БД инициализирована"

# Очистка (удалить БД и __pycache__)
clean:
	cd db-proj-car-dealership && del /f autodealer.db 2>nul || true
	cd db-proj-car-dealership && rmdir /s /q __pycache__ 2>nul || true
	rmdir /s /q autodealer_core\__pycache__ 2>nul || true
	rmdir /s /q __pycache__ 2>nul || true
	@echo "✓ Файлы очищены"

# ==================== Библиотека ====================

# Установить библиотеку локально (для разработки)
install-lib:
	pip install -e .

# Собрать пакет для PyPI
build-lib:
	pip install build
	python -m build
	@echo "✓ Пакет собран в dist/"

# Опубликовать на PyPI
publish: build-lib
	pip install twine
	twine upload dist/*
	@echo "✓ Опубликовано на PyPI"

# ==================== Разработка ====================

# Установка dev зависимостей
install-dev:
	pip install pylint black

# Проверка кода (требует pylint)
lint:
	cd db-proj-car-dealership && python -m pylint autodealer_app.py || true
	python -m pylint autodealer_core/ || true

# Форматирование кода (требует black)
format:
	cd db-proj-car-dealership && python -m black autodealer_app.py
	python -m black autodealer_core/
	@echo "✓ Код отформатирован"

# Резервная копия БД
backup:
	@powershell -Command "copy db-proj-car-dealership\autodealer.db db-proj-car-dealership\autodealer_backup_$$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').db"
	@echo "✓ Резервная копия создана"

# Перестартовать (очистить и запустить)
restart: clean init run

.DEFAULT_GOAL := help
