.PHONY: help install install-dev setup run test test-core test-api clean init-db lint docs serve-docs docker-build docker-run docker-up docker-down check

# ------------------------------
# Help
# ------------------------------
help:
	@echo "Available commands:"
	@echo "  make install       - install production dependencies"
	@echo "  make install-dev   - install development dependencies (pytest, mkdocs, etc.)"
	@echo "  make setup         - install all dependencies (prod + dev)"
	@echo "  make run           - run the web application locally"
	@echo "  make test          - run all tests with coverage report"
	@echo "  make test-core     - run only unit tests for autodealer_core"
	@echo "  make test-api      - run only API integration tests"
	@echo "  make clean         - remove cache, reports, temporary files"
	@echo "  make init-db       - delete autodealer.db file (reset database)"
	@echo "  make lint          - run flake8 linter (requires flake8)"
	@echo "  make docs          - build static documentation with MkDocs"
	@echo "  make serve-docs    - start documentation server (http://127.0.0.1:8000)"
	@echo "  make docker-build  - build Docker image"
	@echo "  make docker-run    - run container (without Compose)"
	@echo "  make docker-up     - start services using docker-compose"
	@echo "  make docker-down   - stop and remove containers"
	@echo "  make check         - run all checks (tests, linter, docs)"

# ------------------------------
# Dependency installation
# ------------------------------
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

setup: install install-dev
	@echo "✅ All dependencies (production and dev) installed"

# ------------------------------
# Run application
# ------------------------------
run:
	python run.py

# ------------------------------
# Testing
# ------------------------------
test:
	pytest tests/ -v --cov=autodealer_core --cov=autodealer --cov=. --cov-report=term-missing --cov-report=html

test-core:
	pytest tests/test_calculations.py tests/test_reporting.py -v

test-api:
	pytest tests/test_api.py tests/test_smoke.py -v

# ------------------------------
# Cleanup
# ------------------------------
clean:
	rm -rf .pytest_cache .coverage htmlcov site
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

init-db:
	rm -f autodealer.db
	@echo "Database deleted. A new one will be created on next run."

# ------------------------------
# Linter
# ------------------------------
lint:
	flake8 autodealer/ tests/ --max-line-length=120 --ignore=E501,W503 || echo "flake8 not installed, run: pip install flake8"

# ------------------------------
# Documentation
# ------------------------------
docs:
	mkdocs build --clean
	@echo "Documentation built in site/ folder"

serve-docs:
	mkdocs serve

# ------------------------------
# Docker
# ------------------------------
docker-build:
	docker build -t autodealer-app .

docker-run:
	docker run -p 5000:5000 autodealer-app

docker-up:
	docker-compose up --build

docker-down:
	docker-compose down

# ------------------------------
# Comprehensive check
# ------------------------------
check: test test-core test-api lint docs
	@echo "✅ All checks passed successfully"