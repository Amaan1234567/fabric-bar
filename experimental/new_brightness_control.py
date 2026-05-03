# import screen_brightness_control as sbc

# # Get current brightness of all monitors
# print(sbc.get_brightness())
# # print(sbc.)

# # Set brightness to 50% on the first monitor using ddcutil specifically
# sbc.set_brightness(100, display=0, method='ddcutil')


import time
import subprocess
import re

# To make this fast, find your bus number first with 'ddcutil detect'
MONITOR_BUS = "10" 

def get_brightness():
    # Calling specific bus is ~20x faster than general detection
    cmd = ["ddcutil", "-b", MONITOR_BUS, "getvcp", "10", "--terse"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    # Parsing terse output: VCP 10 C <current_value> <max_value>
    match = re.search(r"VCP 10 C (\d+)", result.stdout)
    return int(match.group(1)) if match else None

last_val = get_brightness()

while True:
    current_val = get_brightness()
    if current_val is not None and current_val != last_val:
        print(f"OSD TRIGGER: Brightness is now {current_val}%")
        # INSERT YOUR OSD CALL HERE (e.g., notify-send or custom GUI)
        last_val = current_val
    time.sleep(0.01) # Poll every second
