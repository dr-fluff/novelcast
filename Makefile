run:
	PYTHONPATH=src python -m novelcast.main

dev:
	PYTHONPATH=src python -m novelcast.main

dev-sync:
	PYTHONPATH=src python -m novelcast.main & \
	browser-sync start --proxy "localhost:8001" --files "src/**/*.html, src/**/*.css"

lint:
	ruff src

format:
	black src

test:
	pytest

db:
	python -m novelcast.db.migrate