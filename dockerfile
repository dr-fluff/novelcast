# --- NovelCast production image ---
# Uses uv for dependency management, excludes dev-only deps (e.g. browser-sync)

FROM python:3.12-slim

# uv installer needs curl/ca-certificates; remove after install to keep image small
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy the full project (setuptools' build backend needs src/ and README.md
# present at sync time, so we can't split this into a deps-only layer first)
COPY . .

# --no-dev skips dev-only dependency groups (browser-sync, test tools, etc.)
# Adjust the group name below if yours differs (e.g. --group prod)
RUN uv sync --frozen --no-dev

# Do NOT copy .env into the image (see .dockerignore) — pass it in at runtime instead

ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Adjust "app.main:app" if your ASGI entry point / factory path differs
CMD ["uv", "run", "python", "-m", "novelcast.main"]
