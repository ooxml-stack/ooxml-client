PYTHON ?= python3

.PHONY: test lint check build

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

lint:
	$(PYTHON) -m ruff check src tests

check: test lint

build:
	$(PYTHON) scripts/build.py
