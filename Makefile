PYTHON ?= py -3
PACKAGE := scribe

.PHONY: run dev lint typecheck test format sync-commands

run:
	$(PYTHON) main.py

dev:
	$(PYTHON) -m pip install -e .[dev]

lint:
	$(PYTHON) -m black bot config.py main.py worker.py scripts tests
	$(PYTHON) -m isort bot config.py main.py worker.py scripts tests

format: lint

typecheck:
	$(PYTHON) -m mypy bot config.py main.py worker.py

test:
	$(PYTHON) -m pytest

sync-commands:
	$(PYTHON) scripts/sync_commands.py
