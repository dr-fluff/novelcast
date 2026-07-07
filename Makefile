.PHONY: install dev backend frontend predev lint format test clean ports db doctor docker-build docker-up docker-down docker-logs docker-rebuild

VENV ?= .venv

UV := uv
NPX := npx
NPM := npm


install:
	@./scripts/install.sh


dev: predev
	$(NPX) concurrently -k \
		-n BACKEND,FRONTEND \
		-c auto \
		"$(UV) run python -m novelcast.main" \
		"$(NPX) browser-sync start --config bs-config.js"


backend:
	$(UV) run python -m novelcast.main


frontend:
	$(NPX) browser-sync start --config bs-config.js


predev:
	$(NPX) kill-port 8001 3000 || true


ports:
	$(NPX) kill-port 8001 3000 || true


lint:
	$(UV) run ruff src


format:
	$(UV) run black src


test:
	$(UV) run pytest tests


db:
	$(UV) run python -m novelcast.db.migrate


clean:
	rm -rf .venv
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +


doctor:
	@echo "Python:"
	@python3 --version || true
	@echo "Node:"
	@node --version || true
	@echo "npm:"
	@npm --version || true
	@echo "uv:"
	@uv --version || true


docker-build:
	docker compose build


docker-up:
	docker compose up -d


docker-down:
	docker compose down


docker-logs:
	docker compose logs -f


docker-rebuild:
	docker compose down
	docker compose build --no-cache
	docker compose up -d