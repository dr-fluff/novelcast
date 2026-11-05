#!/usr/bin/env bash
# Safely update NovelCast with a database backup and rollback.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
UV_BIN="${UV_BIN:-/root/.local/bin/uv}"
SERVICE_HELPER="$REPO_DIR/scripts/service.sh"

# This is the database actually used by the production service.
PRODUCTION_DB="/root/novelcast/db/novelcast.db"

RELEASE_TAG="${1:-}"
GITHUB_REPOSITORY="${2:-}"

ORIGINAL_COMMIT=""
BACKUP_DIR=""
BACKUP_DB=""
BACKUP_CREATED=0

# Resolve uv.
if [ ! -x "$UV_BIN" ]; then
    UV_BIN="$(command -v uv || true)"
fi

[ -n "$UV_BIN" ] && [ -x "$UV_BIN" ] || {
    echo "ERROR: uv is not installed." >&2
    exit 1
}

command -v sqlite3 >/dev/null || {
    echo "ERROR: sqlite3 is not installed." >&2
    exit 1
}

[ -x "$SERVICE_HELPER" ] || {
    echo "ERROR: Service helper is missing or not executable." >&2
    eit 1
}

cd "$REPO_DIR"

ORIGINAL_COMMIT="$(git rev-parse HEAD)"

# Permit the local updater modification, but refuse other tracked changes.
# Untracked backups/ and docker/ directories are deliberately preserved.
git diff --quiet -- . ':(exclude)scripts/update.sh' &&
git diff --cached --quiet || {
    echo "ERROR: Other tracked files have local changes." >&2
    echo "Commit or stash those changes before updating." >&2
    exit 1
}

# Verify the actual production database.
[ -f "$PRODUCTION_DB" ] || {
    echo "ERROR: Production database not found: $PRODUCTION_DB" >&2
    exit 1
}

DB_CHECK="$(sqlite3 "$PRODUCTION_DB" "PRAGMA quick_check;")" || {
    echo "ERROR: Could not check production database." >&2
    exit 1
}

[ "$DB_CHECK" = "ok" ] || {
    echo "ERROR: Database integrity check failed: $DB_CHECK" >&2
    exit 1
}

echo "==> Production database: $PRODUCTION_DB"
echo "==> Current commit: $ORIGINAL_COMMIT"

# Fetch and apply code updates.
echo "==> Fetching updates"

if [ -n "$RELEASE_TAG" ]; then
    [[ "$RELEASE_TAG" =~ ^v?[0-9]+([.][0-9]+)*$ ]] || {
        echo "ERROR: Invalid release tag: $RELEASE_TAG" >&2
        exit 2
    }

    [[ "$GITHUB_REPOSITORY" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || {
        echo "ERROR: Invalid GitHub repository." >&2
        exit 2
    }

    git fetch --tags "https://github.com/${GITHUB_REPOSITORY}.git"

    git rev-parse --verify "refs/tags/${RELEASE_TAG}^{commit}" >/dev/null || {
        echo "ERROR: Release tag not found: $RELEASE_TAG" >&2
        exit 1
    }

    git checkout --detach "refs/tags/${RELEASE_TAG}"
else
    git fetch --tags origin
    git pull --ff-only
fi

NEW_COMMIT="$(git rev-parse HEAD)"
echo "==> Target commit: $NEW_COMMIT"

# Create a unique backup directory.
BACKUP_DIR="$REPO_DIR/backups/pre-update-$(date +%Y%m%d-%H%M%S)"
BACKUP_DB="$BACKUP_DIR/novelcast.db"

mkdir -p "$BACKUP_DIR"

# Roll back database, code and dependencies if an update step fails.
rollback() {
    echo
    echo "=================================================="
    echo "UPDATE FAILED — attempting rollback"
    echo "=================================================="

    if [ "$BACKUP_CREATED" -eq 1 ]; then
        echo "==> Restoring database backup"

        if rm -f "$PRODUCTION_DB-wal" "$PRODUCTION_DB-shm" &&
           cp -p "$BACKUP_DB" "$PRODUCTION_DB"; then
            echo "Database restored."
        else
            echo "CRITICAL: Database restoration failed!" >&2
        fi
    fi

    if [ "$NEW_COMMIT" != "$ORIGINAL_COMMIT" ]; then
        echo "==> Restoring original code"

        # Preserve the locally modified updater across git reset.
        if cp -p "$REPO_DIR/scripts/update.sh" \
            "$BACKUP_DIR/update.sh.local"; then

            if git reset --hard "$ORIGINAL_COMMIT"; then
                cp -p "$BACKUP_DIR/update.sh.local" \
                    "$REPO_DIR/scripts/update.sh"

                echo "==> Restoring original dependencies"
                if "$UV_BIN" sync --frozen --no-dev; then
                    echo "Original dependencies restored."
                else
                    echo "WARNING: Dependency rollback failed." >&2
                fi
            else
                echo "WARNING: Git rollback failed." >&2
            fi
        else
            echo "WARNING: Could not preserve local updater." >&2
        fi
    fi

    echo "==> Starting NovelCast"
    if "$SERVICE_HELPER" start; then
        echo "Service start requested."
    else
        echo "WARNING: Could not start NovelCast." >&2
    fi

    echo "Rollback attempt finished. Inspect the logs and backup."
}

# Stop the service before touching the database.
echo "==> Stopping NovelCast"

if ! "$SERVICE_HELPER" stop; then
    echo "ERROR: Could not stop NovelCast." >&2
    rollback
    exit 1
fi

# A stopped service means SQLite has no active application writer.
echo "==> Creating consistent SQLite backup"

if ! sqlite3 "$PRODUCTION_DB" ".backup '$BACKUP_DB'"; then
    echo "ERROR: Database backup failed." >&2
    rollback
    exit 1
fi

BACKUP_CHECK="$(sqlite3 "$BACKUP_DB" "PRAGMA quick_check;")" || {
    echo "ERROR: Could not verify database backup." >&2
    rollback
    exit 1
}

if [ "$BACKUP_CHECK" != "ok" ]; then
    echo "ERROR: Database backup failed integrity check." >&2
    rollback
    exit 1
fi

BACKUP_CREATED=1
echo "==> Verified backup: $BACKUP_DB"

# Install dependencies for the new code.
echo "==> Installing locked production dependencies"

if ! "$UV_BIN" sync --frozen --no-dev; then
    echo "ERROR: Dependency installation failed." >&2
    rollback
    exit 1
fi

# Apply migrations to the real production database.
echo "==> Applying database migrations"

if ! (
    cd "$REPO_DIR"
    DATABASE_URL="sqlite:////root/novelcast/db/novelcast.db" \
        "$UV_BIN" run --no-sync alembic upgrade head
); then
    echo "ERROR: Database migration failed." >&2
    rollback
    exit 1
fi

# Verify the resulting database.
DB_CHECK="$(sqlite3 "$PRODUCTION_DB" "PRAGMA quick_check;")" || {
    echo "ERROR: Post-migration database check failed." >&2
    rollback
    exit 1
}

if [ "$DB_CHECK" != "ok" ]; then
    echo "ERROR: Post-migration integrity check failed." >&2
    rollback
    exit 1
fi

echo "==> Database integrity verified"

# Start the updated service.
echo "==> Starting NovelCast"

if ! "$SERVICE_HELPER" start; then
    echo "ERROR: Could not start updated service." >&2
    rollback
    exit 1
fi

echo
echo "NovelCast update completed successfully."
echo "Database backup: $BACKUP_DB"
echo "Previous commit: $ORIGINAL_COMMIT"
echo "Updated commit:  $NEW_COMMIT"x
