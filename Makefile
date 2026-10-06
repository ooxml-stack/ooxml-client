PYTHON ?= python3

.PHONY: test lint check typecheck coverage build

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

lint:
	python3 scripts/quality_gate.py ruff
	python3 scripts/format_gate.py
	python3 scripts/check_action_pins.py
	python3 scripts/check_dependency_notices.py
	python3 scripts/size_report.py --check
	python3 scripts/check_evidence_redaction.py

typecheck:
	python3 scripts/quality_gate.py pyright

coverage:
	uv run --frozen --extra dev --with coverage coverage run -m unittest discover -s tests
	uv run --frozen --extra dev --with coverage coverage report

check: test lint

build:
	$(PYTHON) scripts/build.py
