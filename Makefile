.PHONY: help install install-dev run test clean init-db lint test-core test-api docs serve-docs docker-build docker-run docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  make install       - install production dependencies"
	@echo "  make install-dev   - install dependencies for development"
	@echo "  make run           - run the application"
	@echo "  make test          - run all tests with coverage report"
	@echo "  make test-core     - run tests for core calculations and reporting logic"
	@echo "  make test-api      - run tests for API endpoints and smoke tests"
	@echo "  make clean         - delete cache files and test reports to start fresh"
	@echo "  make init-db       - delete the existing database file to start fresh (use with caution)"
	@echo "  make lint          - test code style with flake8"
	@echo "  make docs          - build documentation using MkDocs"
	@echo "  make serve-docs    - start local server for documentation preview"
	@echo "  make docker-build  - build the Docker image"
	@echo "  make docker-run    - start a container without docker-compose"
	@echo "  make docker-up     - start docker-compose services"
	@echo "  make docker-down   - stop and remove docker-compose services"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

setup: install install-dev
	@echo "ALL DEPENDENCIES INSTALLED. You can now run the application with 'make run' or run tests with 'make test'."

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
	@echo "Database file 'autodealer.db' has been removed. You can now initialize a new database by running the application or using a setup script."

lint:
	flake8 autodealer/ tests/ --max-line-length=120 --ignore=E501,W503 || echo "flake8 is not installed, please download: pip install flake8"

docs:
	mkdocs build --clean
	@echo "Documentation built in the 'site' folder."

serve-docs:
	mkdocs serve

docker-build:
	docker build -t autodealer-app .

docker-run:
	docker run -p 5000:5000 autodealer-app

docker-up:
	docker-compose up --build

docker-down:
	docker-compose down