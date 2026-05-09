#!/bin/bash

# Path setup
BASE_DIR="/home/amaan/Documents/fabric-bar"
source "$BASE_DIR/venv/bin/activate"
cd "$BASE_DIR"

# 1. Kill any existing instances to avoid conflicts
pkill -f "hypr-fabric-bar-main"
pkill -f "hypr-fabric-bar-side"

# 2. Launch Main Shell (Fixed to Monitor 0)
setsid python3 start_shell.py > /dev/null 2>&1 &
sleep 1

# 3. Detect all other monitors and launch side-monitors for each
# This gets all IDs from hyprctl, removes '0', and loops
OTHER_MONITORS=$(hyprctl monitors -j | jq -r '.[] | select(.id != 0) | .id')

for id in $OTHER_MONITORS; do
    echo "Launching side-monitors on Monitor ID: $id"
    setsid python3 side-monitors.py --monitor-id "$id" > /dev/null 2>&1 &
done

disown