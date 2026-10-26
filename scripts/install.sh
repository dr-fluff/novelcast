#!/usr/bin/env bash

# Install NovelCast from a checked-out Git repository and register it as a
# per-user background service. Application data remains in this checkout.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
RUNNER="$REPO_DIR/scripts/run-service.sh"
OS="$(uname -s)"

fail() {
    printf 'Error: %s\n' "$*" >&2
    exit 1
}

command -v git >/dev/null || fail "Git is required. Install Git, then run ./install again."
command -v python3 >/dev/null || fail "Python 3.11 or later is required."
git -C "$REPO_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "Run this from a Git clone."

install_uv() {
    if command -v uv >/dev/null; then
        command -v uv
        return
    fi

    local_uv="$REPO_DIR/.tools/bin/uv"
    if [ -x "$local_uv" ]; then
        printf '%s\n' "$local_uv"
        return
    fi

    command -v curl >/dev/null || fail "curl is required to install uv."
    echo "Installing uv locally in .tools/bin..." >&2
    mkdir -p "$REPO_DIR/.tools/bin"
    curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$REPO_DIR/.tools/bin" sh
    [ -x "$local_uv" ] || fail "uv installation failed."
    printf '%s\n' "$local_uv"
}

UV_BIN="$(install_uv)"

create_env_file() {
    [ -f "$REPO_DIR/.env" ] && return

    echo "Creating .env with production defaults..."
    umask 077
    secret="$($UV_BIN run --no-project python -c 'import secrets; print(secrets.token_urlsafe(32))')"
    cat > "$REPO_DIR/.env" <<EOF
ENV=production
RELOAD=false
HOST=127.0.0.1
PORT=8000
SECRET_KEY=$secret
LOG_LEVEL=info
EOF
}

install_service() {
    case "$OS" in
        Darwin)
            local label="com.novelcast.app"
            local plist="$HOME/Library/LaunchAgents/$label.plist"
            mkdir -p "$HOME/Library/LaunchAgents"
            cat > "$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key><array><string>$RUNNER</string></array>
  <key>WorkingDirectory</key><string>$REPO_DIR</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$REPO_DIR/logs/service.out.log</string>
  <key>StandardErrorPath</key><string>$REPO_DIR/logs/service.err.log</string>
</dict></plist>
EOF
            launchctl bootout "gui/$(id -u)" "$plist" >/dev/null 2>&1 || true
            launchctl bootstrap "gui/$(id -u)" "$plist"
            ;;
        Linux)
            local service_dir="$HOME/.config/systemd/user"
            local service="$service_dir/novelcast.service"
            mkdir -p "$service_dir"
            cat > "$service" <<EOF
[Unit]
Description=NovelCast
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$REPO_DIR
ExecStart=$RUNNER
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
            systemctl --user daemon-reload
            systemctl --user enable --now novelcast.service
            ;;
        *) fail "Unsupported operating system: $OS. macOS and Linux are supported." ;;
    esac
}

echo "==> Installing NovelCast from $REPO_DIR"
mkdir -p "$REPO_DIR/data" "$REPO_DIR/config" "$REPO_DIR/logs"
create_env_file

echo "==> Installing locked production dependencies"
"$UV_BIN" sync --frozen --no-dev

echo "==> Applying database migrations"
"$UV_BIN" run --no-sync alembic upgrade head

echo "==> Registering background service"
install_service

echo
echo "NovelCast is running at the address configured in .env (default: http://127.0.0.1:8000)"
echo "Update later with: ./update"
echo "Service controls: ./scripts/service.sh start|status|restart|stop"
