"""holds the system service"""

import dbus
from fabric.core.service import Service, Signal


class SystemService(Service):
    """System service for obtaining all information about they system from psutil or dbus"""

    _instance = None

    @Signal
    def battery_info_update(self):
        """signal to tell battery info updated"""

    @Signal
    def new_device_inserted(self):
        """when new device is inserted"""

    @Signal
    def cpu_tick(self):
        """when cpu poll triggers"""

    @Signal
    def memory_tick(self):
        """when memory poll triggers"""

    @Signal
    def sensors_tick(self):
        """when sensors poll triggers"""

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, **kwargs):
        if hasattr(self, "_initialized"):
            return
        super().__init__(**kwargs)

        self.bus = dbus.SystemBus()
        upower_proxy = self.bus.get_object(
            "org.freedesktop.UPower", "/org/freedesktop/UPower"
        )
        upower = dbus.Interface(upower_proxy, "org.freedesktop.UPower")
        print(upower.EnumerateDevices())
        devices = upower.EnumerateDevices()
        for device in devices:
            device_proxy = self.bus.get_object("org.freedesktop.UPower", device)
            props = dbus.Interface(device_proxy, "org.freedesktop.DBus.Properties")

            device_type = props.Get("org.freedesktop.UPower.Device", "Type")
            percentage = props.Get("org.freedesktop.UPower.Device", "Percentage")
            print(f"Device: {device} | Type: {device_type} | Charge: {percentage}%")
