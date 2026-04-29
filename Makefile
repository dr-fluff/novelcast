.PHONY: install dev backend frontend predev lint format test clean ports db

VENV ?= .venv
PYTHON := $(VENV)/bin/python
UV := $(VENV)/bin/uv
NPX := npx
NPM := npm

install:
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install uv
	$(UV) sync
	$(NPM) install

predev:
	$(NPX) kill-port 8001 3000

dev: predev
	$(NPX) concurrently -k -n BACKEND,FRONTEND -c auto "$(UV) run python -m novelcast.main" "$(NPX) browser-sync start --config bs-config.js"

backend:
	$(UV) run python -m novelcast.main

frontend:
	$(NPX) browser-sync start --config bs-config.js

ports:
	$(NPX) kill-port 8001 3000

lint:
	$(UV) run ruff src

format:
	$(UV) run black src

test:
	$(UV) run pytest

db:
	$(UV) run python -m novelcast.db.migrate

clean:
	find . -type d -name "__pycache__" -exec rm -r {} + || true
	find . -type d -name ".pytest_cache" -exec rm -r {} + || true
