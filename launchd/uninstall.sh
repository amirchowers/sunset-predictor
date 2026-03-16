#!/bin/bash
# Remove sunset predictor launchd jobs.
# Usage: bash launchd/uninstall.sh

LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

for name in com.sunset.morning.plist com.sunset.noon.plist com.sunset.afternoon.plist com.sunset.capture.plist; do
    dest="$LAUNCH_AGENTS/$name"
    if [ -f "$dest" ]; then
        launchctl bootout "gui/$(id -u)/$name" 2>/dev/null || true
        rm "$dest"
        echo "Removed: $name"
    else
        echo "Not found: $name (skipped)"
    fi
done

echo ""
echo "All sunset jobs uninstalled."
