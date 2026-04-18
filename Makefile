setup:
	uv sync
	npm install

format:
	npm run format

run:
	uv run novelcast

dev:
	uv run novelcast

prod:
	uv run novelcast