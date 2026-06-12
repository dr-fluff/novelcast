FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

RUN pip install --no-cache-dir uv

# Copy project metadata FIRST
COPY pyproject.toml uv.lock ./

# IMPORTANT: copy source BEFORE sync (fixes your error)
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./

# Now dependency install + project build
RUN uv pip install --system .

# runtime files
COPY .env ./
RUN mkdir -p data logs config

EXPOSE 8001

CMD ["python", "-m", "novelcast.main"]