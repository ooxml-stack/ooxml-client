PYTHON ?= python3

.PHONY: test lint check typecheck coverage build

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

lint:
	$(PYTHON) -m ruff check src tests
	python3 scripts/format_gate.py

typecheck:
	python3 scripts/quality_gate.py pyright

coverage:
	uv run --frozen --extra dev --with coverage coverage run -m unittest discover -s tests
	uv run --frozen --extra dev --with coverage coverage report

check: test lint

build:
	$(PYTHON) scripts/build.py
