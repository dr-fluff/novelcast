run:
	PYTHONPATH=src python -m novelcast.main
dev:
	PYTHONPATH=src python -m novelcast.main

lint:
	ruff src

format:
	black src

test:
	pytest

db:
	python -m novelcast.db.migrate