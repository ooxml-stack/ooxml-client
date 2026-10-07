PYTHON ?= python3

.PHONY: test lint check typecheck coverage build

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

lint:
	$(PYTHON) scripts/quality_gate.py ruff
	$(PYTHON) scripts/format_gate.py
	$(PYTHON) scripts/check_action_pins.py
	$(PYTHON) scripts/check_dependency_notices.py
	$(PYTHON) scripts/size_report.py --check
	$(PYTHON) scripts/check_evidence_redaction.py

typecheck:
	$(PYTHON) scripts/quality_gate.py pyright

coverage:
	uv run --frozen --extra dev --with coverage coverage run -m unittest discover -s tests
	uv run --frozen --extra dev --with coverage coverage report

check: test lint

build:
	$(PYTHON) scripts/build.py
