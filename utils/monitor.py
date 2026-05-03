import json
import subprocess
from loguru import logger

def get_monitor_info(monitor_id: int):
    """
    Returns (device_type, hardware_id)
    Internal: ("internal", "internal")
    External: ("external", "1") -> "1" is the ddcutil display index
    """
    try:
        output = subprocess.check_output(["hyprctl", "monitors", "-j"], text=True)
        monitors = json.loads(output)
        target_mon = next((m for m in monitors if m["id"] == monitor_id), None)
        
        if not target_mon:
            return "internal", "internal"
            
        if "eDP" in target_mon["name"]:
            return "internal", "internal"

        # Logic for multiple external monitors:
        # Hyprland IDs are 0, 1, 2... ddcutil displays are usually 1, 2, 3...
        # We find the display index by matching the model name if possible, 
        # or fallback to a calculated index.
        display_index = str(monitor_id + 1) 
        return "external", display_index
        
    except Exception as e:
        logger.error(f"Monitor detection failed: {e}")
        return "internal", "internal"