#!/usr/bin/env bash

set -euo pipefail

ACTION="${1:-status}"
case "$(uname -s)" in
    Darwin)
        LABEL="gui/$(id -u)/com.novelcast.app"
        PLIST="$HOME/Library/LaunchAgents/com.novelcast.app.plist"
        case "$ACTION" in
            start) launchctl bootstrap "gui/$(id -u)" "$PLIST" ;;
            restart) launchctl kickstart -k "$LABEL" ;;
            stop) launchctl bootout "$LABEL" ;;
            status) launchctl print "$LABEL" ;;
            *) echo "Usage: $0 {start|status|restart|stop}" >&2; exit 2 ;;
        esac
        ;;
    Linux)
        case "$ACTION" in
            start|restart|stop|status) systemctl --user "$ACTION" novelcast.service ;;
            *) echo "Usage: $0 {start|status|restart|stop}" >&2; exit 2 ;;
        esac
        ;;
    *) echo "Unsupported operating system." >&2; exit 1 ;;
esac
