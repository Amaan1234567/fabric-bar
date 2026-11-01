"""Service to manage brightness for both internal and external displays."""

import os
import subprocess
import threading
import time
from gi.repository import GLib #type: ignore
from fabric.core.service import Service, Signal
from fabric import Fabricator


class BrightnessService(Service):
    """Service to manage brightness for both internal and external displays."""
    _instance = None

    @Signal
    def changed(self, device_type: str, hardware_id: str, value: int) -> None:
        """Emitted when brightness changes. device_type is 'internal' or 'external'.
        hardware_id is the identifier for the specific device.
        value is the new brightness level (0-100).
        """

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, **kwargs):
        if hasattr(self, "_initialized"):
            return
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
        try:
            return os.listdir("/sys/class/backlight")[0]
        except:  # noqa: E722
            return "intel_backlight"

    def _get_sysfs_value(self, *args) -> int:
        try:
            with open(f"{self._internal_path}/max_brightness", "r") as f:
                max_v = int(f.read())
            with open(f"{self._internal_path}/actual_brightness", "r") as f:
                act_v = int(f.read())
            return round((act_v / max_v) * 100)
        except:  # noqa: E722
            return 0

    def _on_internal_poll(self, _, value):
        # We removed the 'is_adjusting' check here
        if value != self._internal_val:
            self._internal_val = value
            self.emit("changed", "internal", "internal", value)

    def _external_poll_loop(self):
        while True:
            try:
                # Use context manager and avoid capture_output/check=True
                with subprocess.Popen(
                    ["ddcutil", "getvcp", "10", "--bus", self.external_bus, "--terse"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL, # Discard stderr to prevent unneeded I/O wrappers
                    text=True
                ) as proc:
                    stdout, _ = proc.communicate()
                    
                    if proc.returncode == 0:
                        parts = stdout.split()
                        if len(parts) >= 4:
                            val = int(parts[3])
                            if val != self._external_values.get(self.external_bus):
                                self._external_values[self.external_bus] = val
                                GLib.idle_add(self.emit, "changed", "external", "1", val)
            except Exception:
                pass

            time.sleep(1)

    def set_brightness(self, device_type: str, hardware_id: str, value: int):
        """Set brightness for a given device and emit the change immediately."""
        if device_type == "internal":
            self._internal_val = value
            # Native GTK async fire-and-forget (No zombie processes)
            GLib.spawn_command_line_async(f"brightnessctl set {value}% -q")
        else:
            self._external_values[self.external_bus] = value
            # Native GTK background execution - replaces your threading.Thread completely
            GLib.spawn_command_line_async(f"ddcutil setvcp 10 {value} --bus {self.external_bus} --sleep-multiplier .1")

        self.emit("changed", device_type, hardware_id, value)
