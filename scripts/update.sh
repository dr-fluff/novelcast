#!/usr/bin/env bash

# Update code and dependencies without touching ignored local data/configuration.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
UV_BIN="${UV_BIN:-$REPO_DIR/.tools/bin/uv}"

if [ ! -x "$UV_BIN" ]; then
    UV_BIN="$(command -v uv || true)"
fi
[ -n "$UV_BIN" ] && [ -x "$UV_BIN" ] || {
    echo "NovelCast cannot update: uv is not installed. Run ./install first." >&2
    exit 1
}

cd "$REPO_DIR"
git diff --quiet && git diff --cached --quiet || {
    echo "Refusing to update because tracked files have local changes." >&2
    echo "Commit or stash them first; data/ and config/ are never changed by updates." >&2
    exit 1
}

echo "==> Fetching updates"
git fetch --tags origin
git pull --ff-only

echo "==> Installing locked production dependencies"
"$UV_BIN" sync --frozen --no-dev

echo "==> Applying database migrations"
"$UV_BIN" run --no-sync alembic upgrade head

echo "==> Restarting NovelCast"
"$REPO_DIR/scripts/service.sh" restart

echo "NovelCast has been updated and restarted."
