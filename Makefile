.PHONY: run test lint
run:
	python -m src.main

test:
	python -m pytest tests/ -v

lint:
	flake8 src/ tests/
