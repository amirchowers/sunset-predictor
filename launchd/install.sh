#!/bin/bash
# Install sunset predictor launchd jobs.
# Usage: bash launchd/install.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

mkdir -p "$LAUNCH_AGENTS"

for plist in "$SCRIPT_DIR"/com.sunset.*.plist; do
    name="$(basename "$plist")"
    dest="$LAUNCH_AGENTS/$name"

    # Unload if already loaded
    launchctl bootout "gui/$(id -u)/$name" 2>/dev/null || true

    cp "$plist" "$dest"
    launchctl bootstrap "gui/$(id -u)" "$dest"
    echo "Installed and loaded: $name"
done

echo ""
echo "Done. Four jobs scheduled:"
echo "  08:00 — morning prediction"
echo "  12:00 — noon prediction + Telegram notification"
echo "  14:00 — afternoon prediction (no capture)"
echo "  16:00 — webcam capture (waits dynamically for actual sunset)"
echo ""
echo "Check status: launchctl list | grep com.sunset"
echo "Uninstall:    bash launchd/uninstall.sh"
