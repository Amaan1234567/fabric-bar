"""Service to manage brightness for both internal and external displays."""

import os
import re
import subprocess
import threading
import time
import re
from loguru import logger

from fabric import Fabricator
from fabric.core.service import Service, Signal
from gi.repository import GLib  # type: ignore
from loguru import logger

LOWEST_VALUE = 5


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

        self._external_monitors_bus_ids = self._find_external_devices()
        self._external_values = {}
        self._inhibit_polling = False

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

    def _external_device_polling_threads(self):
        threads = []
        for bus_id in self._external_monitors_bus_ids:
            thread = threading.Thread(
                target=self._external_poll_loop, args=(bus_id,), daemon=True
            )
            threads.append(thread)
            thread.start()
        return threads

    def _find_external_devices(self):
        try:
            res = subprocess.run(
                ["ddcutil", "detect", "--ddc-checks-async-min", "4"],
                capture_output=True,
                text=True,
                check=True,
            )
            bus_ids = re.findall(
                r"(?<=Display \d{1}\n   I2C bus:  )/dev/i2c-(\d+)", res.stdout
            )
            print(bus_ids)

            return bus_ids
        except Exception:
            return []

    def _get_sysfs_value(self, *_) -> int:
        try:
            with open(
                f"{self._internal_path}/max_brightness", "r", encoding="utf-8"
            ) as f:
                max_v = int(f.read())
            with open(
                f"{self._internal_path}/actual_brightness", "r", encoding="utf-8"
            ) as f:
                act_v = int(f.read())
            return round((act_v / max_v) * 100)
        except:  # noqa: E722
            return 0

    def _on_internal_poll(self, _, value):

        if value != self._internal_val:
            self._internal_val = value
            self.emit("changed", "internal", "internal", value)

    def _external_poll_loop(self, bus_id=None | str):
        if bus_id is None:
            logger.info("No bus_id provided for external polling loop. Exiting thread.")
            return
        while True:
            try:
                res = subprocess.run(
                    ["ddcutil", "getvcp", "10", "--bus", bus_id, "--terse"],  # type: ignore
                    capture_output=True,
                    text=True,
                    check=True,
                )  # type: ignore
                if res.returncode == 0:
                    parts = res.stdout.split()
                    if len(parts) >= 4:
                        val = int(parts[3])
                        # Only emit if the hardware value actually changed from what we last saw
                        if val != self._external_values.get(bus_id):
                            self._external_values[bus_id] = val
                            GLib.idle_add(self.emit, "changed", "external", "1", val)
            except Exception:
                pass

            time.sleep(1)

    def set_brightness_all(self, value):
        """Set brightness for all devices to the internal value."""
        value = min(max(value, LOWEST_VALUE), 100)

        self.set_brightness("internal", "internal", value)
        for bus_id in self._external_monitors_bus_ids:
            self.set_brightness("external", bus_id, value)

    def set_brightness(self, device_type: str, hardware_id: str, value: int):
        """Set brightness for a given device and emit the change immediately."""
        value = min(max(value, LOWEST_VALUE), 100)
        # 1. Update internal state and emit immediately so the UI is snappy
        if device_type == "internal":
            self._internal_val = value
            subprocess.Popen(["brightnessctl", "set", f"{value}%", "-q"])
            self.emit("changed", device_type, hardware_id, value)
        else:
            self._external_values[hardware_id] = value
            # Run the ddcutil set command in a background thread
            threading.Thread(
                target=lambda: subprocess.run(
                    [
                        "ddcutil",
                        "setvcp",
                        "10",
                        str(round(value)),
                        "--bus",
                        hardware_id,
                        "--sleep-multiplier",
                        ".1",
                    ],
                    check=False,
                ),
                daemon=True,
            ).start()
            self.emit("changed", device_type, "1", value)
