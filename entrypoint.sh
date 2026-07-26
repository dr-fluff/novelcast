#!/bin/sh
set -e

echo "Running database migrations..."
uv run alembic upgrade head

echo "Starting NovelCast..."
exec uv run python -m novelcast.main