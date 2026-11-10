.PHONY: install dev backend frontend anubis predev lint format test benchmark clean ports db doctor docker-build docker-up docker-down docker-logs docker-rebuild

VENV ?= .venv

UV := uv
NPX := npx
NPM := npm
ANUBIS_PORT ?= 8192
ANUBIS_URL := http://127.0.0.1:$(ANUBIS_PORT)/v1


install:
	@./scripts/install.sh


dev: predev
	$(UV) run playwright install chromium
	@mkdir -p .tools
	$(NPX) concurrently -k \
		-n BACKEND,FRONTEND,ANUBIS \
		-c auto \
		"NOVELCAST_ANUBIS_SHIM_URL=$(ANUBIS_URL) $(UV) run python -m novelcast.main" \
		"$(NPX) browser-sync start --config bs-config.js" \
		"SHIM_USER_DATA_DIR=.tools/anubis-profile $(UV) run uvicorn anubis_shim:app --host 127.0.0.1 --port $(ANUBIS_PORT)"


backend:
	$(UV) run python -m novelcast.main


frontend:
	$(NPX) browser-sync start --config bs-config.js

anubis:
	$(UV) run playwright install chromium
	@mkdir -p .tools
	SHIM_USER_DATA_DIR=.tools/anubis-profile $(UV) run uvicorn anubis_shim:app --host 127.0.0.1 --port $(ANUBIS_PORT)


predev:
	$(NPX) kill-port 8001 3000 $(ANUBIS_PORT) || true


ports:
	$(NPX) kill-port 8001 3000 $(ANUBIS_PORT) || true


lint:
	$(UV) run ruff check .


format:
	$(NPM) run format


test:
	$(UV) run pytest tests

benchmark:
	$(UV) run python scripts/benchmark_pages.py $(ARGS)


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

git-pull:
	git pull --ff-only

deploy: git-pull docker-rebuild