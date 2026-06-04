.PHONY: test

test:
	python -m pytest tests/ -v --cov=autodealer_app --cov-report=term-missing