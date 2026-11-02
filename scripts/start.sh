#!/bin/bash

# Path setup
BASE_DIR="$HOME/fabric-bar"
echo "$BASE_DIR/venv/bin/activate"
source "$BASE_DIR/venv/bin/activate"
cd "$BASE_DIR"
export PATH=$HOME/.cargo/bin:$PATH
# 1. Kill any existing instances to avoid conflicts
pkill -f "hypr-fabric-bar-main"
pkill -f "hypr-fabric-bar-side"

# 1. Dynamically find all monitors EXCEPT the primary one
OTHER_MONITORS=$(hyprctl monitors -j | jq -r --argjson primary "${PRIMARY_MONITOR_ID:-0}" '.[] | select(.id != $primary) | .id')

echo "Other monitors detected: $OTHER_MONITORS"
# 2. Launch Main Shell on the designated Primary Monitor
echo "Launching main shell on Primary Monitor ID: ${PRIMARY_MONITOR_ID:-0}"
setsid python3 start_shell.py --monitor-id "${PRIMARY_MONITOR_ID:-0}" > /dev/null 2>&1 &
disown
# 3. Launch Side Shells only if other monitors exist
if [ -z "$OTHER_MONITORS" ]; then
    echo "No side monitors detected."
else
    echo "Detected side monitors: $OTHER_MONITORS"
    for id in $OTHER_MONITORS; do
        echo "Launching side-monitors on Monitor ID: $id"
        setsid python3 side-monitors.py --monitor-id "$id" > /dev/null 2>&1 &
    done
fi


disown