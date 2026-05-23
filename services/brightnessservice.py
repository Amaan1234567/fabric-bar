import os
import subprocess
import threading
import time
from loguru import logger
from gi.repository import GLib
from fabric.core.service import Service, Signal, Property
from fabric import Fabricator

class BrightnessService(Service):
    _instance = None

    @Signal
    def changed(self, device_type: str, hardware_id: str, value: int) -> None:
        pass

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, **kwargs):
        if hasattr(self, "_initialized"): return
        super().__init__(**kwargs)
        self._initialized = True

        # Internal Backlight Setup
        self._internal_dev = self._find_internal_device()
        self._internal_path = f"/sys/class/backlight/{self._internal_dev}"
        self._internal_val = self._get_sysfs_value()
        
        self._external_values = {} 
        self._inhibit_polling = False

        # Your MSI monitor bus ID
        self.external_bus = "10" 

        # 1. Internal Poller (sysfs)
        self._int_poller = Fabricator(poll_from=self._get_sysfs_value, interval=100)
        self._int_poller.connect("changed", self._on_internal_poll)

        # 2. External Poller Thread (Direct Bus)
        threading.Thread(target=self._external_poll_loop, daemon=True).start()

    def _find_internal_device(self):
        try: return os.listdir("/sys/class/backlight")[0]
        except: return "intel_backlight"

    def _get_sysfs_value(self, *args) -> int:
        try:
            with open(f"{self._internal_path}/max_brightness", "r") as f: max_v = int(f.read())
            with open(f"{self._internal_path}/actual_brightness", "r") as f: act_v = int(f.read())
            return round((act_v / max_v) * 100)
        except: return 0

    def _on_internal_poll(self, _, value):
        # We removed the 'is_adjusting' check here
        if value != self._internal_val:
            self._internal_val = value
            self.emit("changed", "internal", "internal", value)

    def _external_poll_loop(self):
        while True:
            # We only skip if Control Center is animating (inhibit)
            # if self._inhibit_polling:
            #     time.sleep(0.1)
            #     continue

            try:
                res = subprocess.run(
                    ["ddcutil", "getvcp", "10", "--bus", self.external_bus, "--terse"],
                    capture_output=True, text=True # Slightly longer timeout
                )
                if res.returncode == 0:
                    parts = res.stdout.split()
                    if len(parts) >= 4:
                        val = int(parts[3])
                        # Only emit if the hardware value actually changed from what we last saw
                        if val != self._external_values.get(self.external_bus):
                            self._external_values[self.external_bus] = val
                            GLib.idle_add(self.emit, "changed", "external", "1", val)
            except Exception:
                pass
            
            time.sleep(0.01) 

    def set_brightness(self, device_type: str, hardware_id: str, value: int):
        # 1. Update internal state and emit immediately so the UI is snappy
        if device_type == "internal":
            self._internal_val = value
            subprocess.Popen(["brightnessctl", "set", f"{value}%", "-q"])
        else:
            self._external_values[self.external_bus] = value
            # Run the ddcutil set command in a background thread
            threading.Thread(
                target=lambda: subprocess.run([
                    "ddcutil", "setvcp", "10", str(value), 
                    "--bus", self.external_bus, "--sleep-multiplier", ".1"
                ]), 
                daemon=True
            ).start()

        # 2. Force emit the signal so the OSD pops up instantly
        self.emit("changed", device_type, hardware_id, value)