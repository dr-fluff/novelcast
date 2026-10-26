#!/usr/bin/env bash

# Process entry point used by launchd and systemd. Keep production settings
# here so a development-oriented .env cannot accidentally enable auto-reload.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
UV_BIN="${UV_BIN:-$REPO_DIR/.tools/bin/uv}"

if [ ! -x "$UV_BIN" ]; then
    UV_BIN="$(command -v uv || true)"
fi
[ -n "$UV_BIN" ] && [ -x "$UV_BIN" ] || {
    echo "NovelCast cannot start: uv is not installed." >&2
    exit 1
}

cd "$REPO_DIR"
export ENV=production
export RELOAD=false
export PYTHONUNBUFFERED=1

exec "$UV_BIN" run --no-sync python -m novelcast.main
