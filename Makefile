PYTHON ?= python3

.PHONY: test lint check typecheck build

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

lint:
	$(PYTHON) -m ruff check src tests

typecheck:
	python3 scripts/quality_gate.py pyright

check: test lint

build:
	$(PYTHON) scripts/build.py
