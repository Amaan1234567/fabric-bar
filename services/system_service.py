"""holds the system service and all its managers"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from fabric.core.service import Service, Signal

UPOWER_SERVICE = "org.freedesktop.UPower"
UPOWER_PATH = "/org/freedesktop/UPower"
UPOWER_DEVICE_IFACE = "org.freedesktop.UPower.Device"

UDISKS2_SERVICE = "org.freedesktop.UDisks2"
UDISKS2_PATH = "/org/freedesktop/UDisks2"
UDISKS2_FS_IFACE = "org.freedesktop.UDisks2.Filesystem"
UDISKS2_BLOCK_IFACE = "org.freedesktop.UDisks2.Block"
DBUS_PROPS_IFACE = "org.freedesktop.DBus.Properties"
DBUS_OBJ_MANAGER_IFACE = "org.freedesktop.DBus.ObjectManager"


# ---------------------------------------------------------------------------
# UPower Enums & Device Model
# ---------------------------------------------------------------------------


class UPowerDeviceType(IntEnum):
    """enum to store UPower Device type"""

    UNKNOWN = 0
    LINE_POWER = 1
    BATTERY = 2
    UPS = 3
    MONITOR = 4
    MOUSE = 5
    KEYBOARD = 6
    PDA = 7
    PHONE = 8
    MEDIA_PLAYER = 9
    TABLET = 10
    COMPUTER = 11
    GAMING_INPUT = 12
    PEN = 13
    TOUCHPAD = 14
    MODEM = 15
    NETWORK = 16
    HEADSET = 17
    SPEAKERS = 18
    HEADPHONES = 19
    VIDEO = 20
    OTHER_AUDIO = 21
    REMOTE_CONTROL = 22
    PRINTER = 23
    SCANNER = 24
    CAMERA = 25
    WEARABLE = 26
    TOY = 27
    BLUETOOTH_GENERIC = 28

    @property
    def label(self) -> str:
        """str form of enum"""
        return self.name.replace("_", " ").title()


class UPowerDeviceState(IntEnum):
    """enum to store UPower Device State"""

    UNKNOWN = 0
    CHARGING = 1
    DISCHARGING = 2
    EMPTY = 3
    FULLY_CHARGED = 4
    PENDING_CHARGE = 5
    PENDING_DISCHARGE = 6


def _parse_enum(enum_cls: type[IntEnum], raw: Any, default: IntEnum) -> IntEnum:
    if raw is None:
        return default
    try:
        return enum_cls(int(raw))
    except (ValueError, TypeError):
        return default


@dataclass
class UPowerDevice:
    """dataclass for UPowerDevice"""

    object_path: str
    props_iface: Any
    device_iface: Any | None = None

    type: UPowerDeviceType = UPowerDeviceType.UNKNOWN
    state: UPowerDeviceState = UPowerDeviceState.UNKNOWN
    native_path: str = ""
    model: str = ""
    vendor: str = ""
    power_supply: bool = False
    is_present: bool = False
    online: bool = False
    percentage: float = 0.0
    energy: float = 0.0
    energy_full: float = 0.0
    energy_full_design: float = 0.0
    energy_rate: float = 0.0
    capacity: float = 0.0
    time_to_empty: int = 0
    time_to_full: int = 0
    voltage: float = 0.0

    def __post_init__(self) -> None:
        self.refresh()

    @classmethod
    def from_bus(cls, bus: dbus.Bus, object_path: str) -> UPowerDevice:
        """gets UPowerDevice object from dbus"""
        proxy = bus.get_object(UPOWER_SERVICE, object_path)
        return cls(
            object_path=object_path,
            props_iface=dbus.Interface(proxy, DBUS_PROPS_IFACE),
            device_iface=dbus.Interface(proxy, UPOWER_DEVICE_IFACE),
        )

    def refresh(self) -> None:
        """refreshes the properties for Device"""
        self.apply_properties(dict(self.props_iface.GetAll(UPOWER_DEVICE_IFACE)))

    def apply_properties(self, props: dict[str, Any]) -> None:
        """sets all properties in the class"""
        if "Type" in props:
            self.type = _parse_enum(
                UPowerDeviceType, props["Type"], UPowerDeviceType.UNKNOWN
            )  # type: ignore[assignment]
        if "State" in props:
            self.state = _parse_enum(
                UPowerDeviceState, props["State"], UPowerDeviceState.UNKNOWN
            )  # type: ignore[assignment]
        self.native_path = str(props.get("NativePath", self.native_path))
        self.model = str(props.get("Model", self.model))
        self.vendor = str(props.get("Vendor", self.vendor))
        self.power_supply = bool(props.get("PowerSupply", self.power_supply))
        self.is_present = bool(props.get("IsPresent", self.is_present))
        self.online = bool(props.get("Online", self.online))
        self.percentage = float(props.get("Percentage", self.percentage))
        self.energy = float(props.get("Energy", self.energy))
        self.energy_full = float(props.get("EnergyFull", self.energy_full))
        self.energy_full_design = float(
            props.get("EnergyFullDesign", self.energy_full_design)
        )
        self.energy_rate = float(props.get("EnergyRate", self.energy_rate))
        self.capacity = float(props.get("Capacity", self.capacity))
        self.time_to_empty = int(props.get("TimeToEmpty", self.time_to_empty))
        self.time_to_full = int(props.get("TimeToFull", self.time_to_full))
        self.voltage = float(props.get("Voltage", self.voltage))


# ---------------------------------------------------------------------------
# D-Bus Subsystem Managers (Extensible Pattern for UPower, UDisks2, etc.)
# ---------------------------------------------------------------------------


class PowerManager:
    """Manages org.freedesktop.UPower devices and property change signals."""

    def __init__(
        self, bus: dbus.Bus, on_battery_update: Any = None, on_device_added: Any = None
    ) -> None:
        self.bus = bus
        self.on_battery_update = on_battery_update
        self.on_device_added = on_device_added
        self.devices: dict[str, UPowerDevice] = {}

        proxy = self.bus.get_object(UPOWER_SERVICE, UPOWER_PATH)
        self.upower_iface = dbus.Interface(proxy, UPOWER_SERVICE)

        for path in self.upower_iface.EnumerateDevices():
            self._register_device(str(path), emit_added=False)

        self.upower_iface.connect_to_signal("DeviceAdded", self._on_device_added)
        self.upower_iface.connect_to_signal("DeviceRemoved", self._on_device_removed)

    def _register_device(self, path: str, emit_added: bool = True) -> None:
        if path in self.devices:
            return
        dev = UPowerDevice.from_bus(self.bus, path)
        self.devices[path] = dev
        self.bus.add_signal_receiver(
            self._on_properties_changed,
            signal_name="PropertiesChanged",
            dbus_interface=DBUS_PROPS_IFACE,
            bus_name=UPOWER_SERVICE,
            path=path,
            path_keyword="path",
        )
        if emit_added and self.on_device_added:
            self.on_device_added(dev)

    def _on_device_added(self, path: Any) -> None:
        self._register_device(str(path), emit_added=True)

    def _on_device_removed(self, path: Any) -> None:
        self.devices.pop(str(path), None)

    def _on_properties_changed(
        self, interface: str, changed: dict, invalidated: list, path: str | None = None
    ) -> None:
        if interface != UPOWER_DEVICE_IFACE or path not in self.devices:
            return
        dev = self.devices[path]
        dev.apply_properties(dict(changed))
        if invalidated:
            dev.refresh()
        if self.on_battery_update:
            self.on_battery_update(dev)

    @property
    def is_plugged_in(self) -> bool:
        """checks if laptop is plugged in"""
        return any(
            dev.type == UPowerDeviceType.LINE_POWER and dev.online
            for dev in self.devices.values()
        )

    # In PowerManager:
    @property
    def primary_battery(self) -> UPowerDevice | None:
        """returns the first battery device found else None"""
        for dev in self.devices.values():
            if (
                dev.type == UPowerDeviceType.BATTERY
                and dev.power_supply
                and dev.is_present
            ):
                return dev
        for dev in self.devices.values():
            if dev.type == UPowerDeviceType.BATTERY and dev.is_present:
                return dev
        return None


@dataclass
class DiskMountInfo:
    """data class for disk mount info"""

    object_path: str
    device_node: str
    mount_points: list[str] = field(default_factory=list)
    filesystem_type: str = ""
    label: str = ""


class StorageManager:
    """Manages org.freedesktop.UDisks2 block/filesystem objects and mount actions."""

    def __init__(self, bus: dbus.Bus, on_device_inserted: Any = None) -> None:
        self.bus = bus
        self.on_device_inserted = on_device_inserted
        self.manager_proxy = self.bus.get_object(UDISKS2_SERVICE, UDISKS2_PATH)
        self.obj_manager = dbus.Interface(self.manager_proxy, DBUS_OBJ_MANAGER_IFACE)

        self.obj_manager.connect_to_signal("InterfacesAdded", self._on_interfaces_added)

    @staticmethod
    def _decode_byte_array(raw: Any) -> str:
        if not raw:
            return ""
        # UDisks2 often encodes device paths/labels as null-terminated byte arrays ('ay')
        data = bytes(int(b) for b in raw).rstrip(b"\x00")
        return data.decode("utf-8", errors="replace")

    def list_filesystems(self) -> list[DiskMountInfo]:
        """lists filesystems"""
        managed = self.obj_manager.GetManagedObjects()
        results: list[DiskMountInfo] = []

        for path, ifaces in managed.items():
            if UDISKS2_FS_IFACE not in ifaces:
                continue
            block_props = ifaces.get(UDISKS2_BLOCK_IFACE, {})
            fs_props = ifaces[UDISKS2_FS_IFACE]
            raw_mounts = fs_props.get("MountPoints", [])
            mounts = [self._decode_byte_array(mp) for mp in raw_mounts]

            results.append(
                DiskMountInfo(
                    object_path=str(path),
                    device_node=self._decode_byte_array(
                        block_props.get("PreferredDevice") or block_props.get("Device")
                    ),
                    mount_points=[m for m in mounts if m],
                    filesystem_type=str(block_props.get("IdType", "")),
                    label=str(block_props.get("IdLabel", "")),
                )
            )
        return results

    def mount(self, object_path: str, options: dict[str, Any] | None = None) -> str:
        """mounts a disk"""
        proxy = self.bus.get_object(UDISKS2_SERVICE, object_path)
        fs_iface = dbus.Interface(proxy, UDISKS2_FS_IFACE)
        mount_opts = dbus.Dictionary(options or {}, signature="sv")
        return str(fs_iface.Mount(mount_opts))

    def unmount(self, object_path: str, options: dict[str, Any] | None = None) -> None:
        """unmounts a disk"""
        proxy = self.bus.get_object(UDISKS2_SERVICE, object_path)
        fs_iface = dbus.Interface(proxy, UDISKS2_FS_IFACE)
        unmount_opts = dbus.Dictionary(options or {}, signature="sv")
        fs_iface.Unmount(unmount_opts)

    def _on_interfaces_added(self, path: Any, interfaces: dict) -> None:
        if UDISKS2_FS_IFACE in interfaces and self.on_device_inserted:
            self.on_device_inserted(str(path))


# ---------------------------------------------------------------------------
# SystemService Integration
# ---------------------------------------------------------------------------


class SystemService(Service):
    """System service for obtaining all information about the system from psutil or dbus."""

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
        if getattr(self, "_initialized", False):
            return
        super().__init__(**kwargs)

        DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()

        self.power = PowerManager(
            self.bus,
            on_battery_update=self._handle_battery_update,
            on_device_added=self._handle_device_inserted,
        )
        self.storage = StorageManager(
            self.bus,
            on_device_inserted=self._handle_storage_inserted,
        )

        self._initialized = True

    def _handle_battery_update(self, device: UPowerDevice) -> None:
        self.battery_info_update.emit()

    def _handle_device_inserted(self, device: Any) -> None:
        self.new_device_inserted.emit()

    def _handle_storage_inserted(self, object_path: str) -> None:
        self.new_device_inserted.emit()
