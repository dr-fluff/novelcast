#!/usr/bin/env bash

# Update code and dependencies without touching ignored local data/configuration.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
UV_BIN="${UV_BIN:-/root/.local/bin/uv}"
RELEASE_TAG="${1:-}"
GITHUB_REPOSITORY="${2:-}"

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
if [ -n "$RELEASE_TAG" ]; then
    [[ "$RELEASE_TAG" =~ ^v?[0-9]+([.][0-9]+)*$ ]] || {
        echo "Invalid release tag: $RELEASE_TAG" >&2
        exit 2
    }
    [[ "$GITHUB_REPOSITORY" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || {
        echo "Invalid GitHub repository: $GITHUB_REPOSITORY" >&2
        exit 2
    }

    git fetch --tags "https://github.com/${GITHUB_REPOSITORY}.git"
    git rev-parse --verify "refs/tags/${RELEASE_TAG}^{commit}" >/dev/null || {
        echo "Release tag $RELEASE_TAG was not found on GitHub." >&2
        exit 1
    }
    git checkout --detach "refs/tags/${RELEASE_TAG}"
else
    git fetch --tags origin
    git pull --ff-only
fi

echo "==> Installing locked production dependencies"
"$UV_BIN" sync --frozen --no-dev

echo "==> Applying database migrations"
"$UV_BIN" run --no-sync alembic upgrade head

echo "==> Restarting NovelCast"
"$REPO_DIR/scripts/service.sh" restart

echo "NovelCast has been updated and restarted."
