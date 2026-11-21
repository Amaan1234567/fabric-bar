"""holds the system service and all its managers"""

from __future__ import annotations

import shutil
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

import dbus
import psutil
from dbus.mainloop.glib import DBusGMainLoop
from fabric.core.service import Service, Signal
from gi.repository import GLib  # type: ignore
from loguru import logger

from utils.notifications import NotificationHelper

UPOWER_SERVICE = "org.freedesktop.UPower"
UPOWER_PATH = "/org/freedesktop/UPower"
UPOWER_DEVICE_IFACE = "org.freedesktop.UPower.Device"

UDISKS2_SERVICE = "org.freedesktop.UDisks2"
UDISKS2_PATH = "/org/freedesktop/UDisks2"
UDISKS2_FS_IFACE = "org.freedesktop.UDisks2.Filesystem"
UDISKS2_BLOCK_IFACE = "org.freedesktop.UDisks2.Block"
DBUS_PROPS_IFACE = "org.freedesktop.DBus.Properties"
DBUS_OBJ_MANAGER_IFACE = "org.freedesktop.DBus.ObjectManager"

BYTES_PER_GB = 1073741824
MIN_MOUNTABLE_BYTES = 2 * 1024**3  # Ignore < 2 GB (EFI / Windows recovery)
IGNORED_FS_TYPES = {
    "swap",
    "vfat",
    "iso9660",
    "squashfs",
}
IGNORED_LABELS = {
    "system reserved",
    "recovery",
    "winre tools",
    "efi",
    "esp",
}


def _run_on_main_thread(fn: Any, *args: Any) -> None:
    """Schedule a callable on the GLib main loop safely."""

    def _cb() -> bool:
        try:
            fn(*args)
        except Exception as exc:
            logger.error(f"Main-thread callback error: {exc}")
        return False

    GLib.idle_add(_cb, priority=GLib.PRIORITY_DEFAULT)


def format_mount_error(err: Exception) -> str:
    """Turn a D-Bus / UDisks2 error into a concise, readable reason string."""
    raw = str(err).strip()
    if ": " in raw:
        raw = raw.split(": ", 1)[1].strip()
    return raw.splitlines()[0].strip() if raw else "Unknown error"


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
            object_path=str(object_path),
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
# D-Bus Subsystem Managers (UPower & UDisks2)
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
            _run_on_main_thread(self.on_device_added, dev)

    def _on_device_added(self, path: Any) -> None:
        self._register_device(str(path), emit_added=True)

    def _on_device_removed(self, path: Any) -> None:
        self.devices.pop(str(path), None)

    def _on_properties_changed(
        self, interface: str, changed: dict, invalidated: list, path: str | None = None
    ) -> None:
        if interface != UPOWER_DEVICE_IFACE or path not in self.devices:
            return
        dev = self.devices[str(path)]
        dev.apply_properties(dict(changed))
        if invalidated:
            dev.refresh()
        if self.on_battery_update:
            _run_on_main_thread(self.on_battery_update, dev)

    @property
    def is_plugged_in(self) -> bool:
        """checks if laptop is plugged in"""
        return any(
            dev.type == UPowerDeviceType.LINE_POWER and dev.online
            for dev in self.devices.values()
        )

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
    object_path: str
    device_node: str
    mount_points: list[str] = field(default_factory=list)
    filesystem_type: str = ""
    label: str = ""
    size_bytes: int = 0

    @property
    def display_name(self) -> str:
        return self.label or self.device_node or self.object_path


class StorageManager:
    """Manages org.freedesktop.UDisks2 block/filesystem objects, usage, and mounts."""

    def __init__(
        self,
        bus: dbus.Bus,
        notifier: NotificationHelper | None = None,
        on_disk_inserted: Any = None,
        on_disk_mounted: Callable[[DiskMountInfo, str], None] | None = None,
        min_size_bytes: int = MIN_MOUNTABLE_BYTES,
        ignored_fs_types: set[str] | None = None,
        ignored_labels: set[str] | None = None,
        ignored_devices: set[str] | None = None,
    ) -> None:
        self.bus = bus
        self.notifier = notifier
        self.on_disk_inserted = on_disk_inserted
        self.on_disk_mounted = on_disk_mounted
        self.min_size_bytes = min_size_bytes
        self.ignored_fs_types = {
            s.lower()
            for s in (
                ignored_fs_types if ignored_fs_types is not None else IGNORED_FS_TYPES
            )
        }
        self.ignored_labels = {
            s.lower()
            for s in (
                ignored_labels if ignored_labels is not None else IGNORED_LABELS
            )
        }
        self.ignored_devices = set(ignored_devices or ())
        self._recent_notified: dict[str, float] = {}
        self._known_disks: dict[str, DiskMountInfo] = {}

        self.manager_proxy = self.bus.get_object(UDISKS2_SERVICE, UDISKS2_PATH)
        self.obj_manager = dbus.Interface(self.manager_proxy, DBUS_OBJ_MANAGER_IFACE)
        self.obj_manager.connect_to_signal("InterfacesAdded", self._on_interfaces_added)

    @staticmethod
    def _decode_byte_array(raw: Any) -> str:
        if not raw:
            return ""
        data = bytes(int(b) for b in raw).rstrip(b"\x00")
        return data.decode("utf-8", errors="replace")

    def _build_disk_info_from_ifaces(
        self, object_path: str, ifaces: dict[str, Any]
    ) -> DiskMountInfo | None:
        if UDISKS2_FS_IFACE not in ifaces:
            return None

        block_props = ifaces.get(UDISKS2_BLOCK_IFACE, {})
        fs_props = ifaces[UDISKS2_FS_IFACE]
        mounts = [
            m
            for m in (
                self._decode_byte_array(mp) for mp in fs_props.get("MountPoints", [])
            )
            if m
        ]

        return DiskMountInfo(
            object_path=str(object_path),
            device_node=self._decode_byte_array(
                block_props.get("PreferredDevice") or block_props.get("Device")
            ),
            mount_points=mounts,
            filesystem_type=str(block_props.get("IdType", "")),
            label=str(block_props.get("IdLabel", "")),
            size_bytes=int(block_props.get("Size", 0)),
        )

    def get_disk_info(self, object_path: str) -> DiskMountInfo | None:
        try:
            managed = self.obj_manager.GetManagedObjects()
        except Exception as exc:
            logger.error(f"Failed to query UDisks2 objects: {exc}")
            return None
        ifaces = managed.get(object_path)
        if not ifaces:
            return None
        info = self._build_disk_info_from_ifaces(str(object_path), ifaces)
        if info:
            self._known_disks[info.object_path] = info
        return info

    def list_filesystems(self) -> list[DiskMountInfo]:
        try:
            managed = self.obj_manager.GetManagedObjects()
        except Exception as exc:
            logger.error(f"Failed to enumerate UDisks2 filesystems: {exc}")
            return []

        results: list[DiskMountInfo] = []
        for path, ifaces in managed.items():
            info = self._build_disk_info_from_ifaces(str(path), ifaces)
            if info:
                self._known_disks[info.object_path] = info
                results.append(info)
        return results

    def should_ignore(self, disk: DiskMountInfo) -> bool:
        if (
            disk.device_node in self.ignored_devices
            or disk.object_path in self.ignored_devices
        ):
            return True
        if disk.filesystem_type.lower() in self.ignored_fs_types:
            return True
        if disk.label.strip().lower() in self.ignored_labels:
            return True
        if self.min_size_bytes > 0 and 0 < disk.size_bytes < self.min_size_bytes:
            return True
        return False

    def list_unmounted_filesystems(self) -> list[DiskMountInfo]:
        """Return mountable unmounted UDisks2 filesystems after filtering system/tiny partitions."""
        return [
            fs
            for fs in self.list_filesystems()
            if not fs.mount_points and not self.should_ignore(fs)
        ]

    def get_usage(self, path: str) -> shutil.usage:  # type: ignore
        return shutil.disk_usage(path)

    def list_partitions(self, all_partitions: bool = False) -> list[Any]:
        return psutil.disk_partitions(all=all_partitions)

    def notify_mount_error(
        self, disk_or_path: DiskMountInfo | str, err: Exception
    ) -> None:
        if isinstance(disk_or_path, DiskMountInfo):
            name = disk_or_path.display_name
            obj_path = disk_or_path.object_path
        else:
            cached = self._known_disks.get(disk_or_path)
            name = cached.display_name if cached else disk_or_path
            obj_path = disk_or_path

        reason = format_mount_error(err)
        logger.error(f"Failed to mount {obj_path}: {err}")
        if self.notifier:
            self.notifier.send(
                summary=f"Failed to mount {name}",
                body=reason,
                icon="dialog-error",
                urgency=2,
                expire_timeout=8000,
            )

    def notify_unmounted_disk(self, disk_info: DiskMountInfo) -> None:
        if not self.notifier:
            return

        size_gb = disk_info.size_bytes / BYTES_PER_GB if disk_info.size_bytes else 0.0
        fs_part = f"{disk_info.filesystem_type} · " if disk_info.filesystem_type else ""
        size_part = f"{size_gb:.1f} GB" if size_gb > 0 else "Storage device"
        body = f"Detected {fs_part}{size_part} ({disk_info.device_node})"

        self.notifier.send(
            summary=disk_info.display_name,
            body=body,
            icon="drive-harddisk",
            actions={"mount": lambda d=disk_info: self.mount(d.object_path)},
            urgency=1,
            expire_timeout=10000,
        )

    def mount(
        self,
        object_path: str,
        options: dict[str, Any] | None = None,
        on_success: Callable[[str], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
        notify_on_error: bool = True,
    ) -> None:
        disk_info = self._known_disks.get(object_path)
        proxy = self.bus.get_object(UDISKS2_SERVICE, object_path)
        fs_iface = dbus.Interface(proxy, UDISKS2_FS_IFACE)
        mount_opts = dbus.Dictionary(options or {}, signature="sv")

        def _reply(mount_path: Any) -> None:
            resolved_path = str(mount_path)
            logger.info(f"Mounted {object_path} -> {resolved_path}")
            if self.on_disk_mounted:
                _run_on_main_thread(
                    self.on_disk_mounted,
                    disk_info
                    or DiskMountInfo(object_path=object_path, device_node=object_path),
                    resolved_path,
                )
            if on_success:
                _run_on_main_thread(on_success, resolved_path)

        def _err(err: Exception) -> None:
            if notify_on_error:
                _run_on_main_thread(
                    self.notify_mount_error, disk_info or object_path, err
                )
            if on_error:
                _run_on_main_thread(on_error, err)

        fs_iface.Mount(mount_opts, reply_handler=_reply, error_handler=_err)

    def unmount(
        self,
        object_path: str,
        options: dict[str, Any] | None = None,
        on_success: Callable[[], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        proxy = self.bus.get_object(UDISKS2_SERVICE, object_path)
        fs_iface = dbus.Interface(proxy, UDISKS2_FS_IFACE)
        unmount_opts = dbus.Dictionary(options or {}, signature="sv")

        def _reply() -> None:
            if on_success:
                _run_on_main_thread(on_success)

        def _err(err: Exception) -> None:
            if on_error:
                _run_on_main_thread(on_error, err)
            else:
                logger.error(f"Failed to unmount {object_path}: {err}")

        fs_iface.Unmount(unmount_opts, reply_handler=_reply, error_handler=_err)

    def _accept_inserted_disk(self, info: DiskMountInfo) -> None:
        self._known_disks[info.object_path] = info
        if self.should_ignore(info):
            return
        if not info.mount_points:
            self.notify_unmounted_disk(info)
        if self.on_disk_inserted:
            _run_on_main_thread(self.on_disk_inserted, info)

    def _on_interfaces_added(self, path: Any, interfaces: dict) -> None:
        if UDISKS2_FS_IFACE not in interfaces:
            return

        obj_path = str(path)
        now = time.monotonic()
        if now - self._recent_notified.get(obj_path, 0.0) < 3.0:
            return
        self._recent_notified[obj_path] = now

        info = self._build_disk_info_from_ifaces(obj_path, dict(interfaces))
        if info is not None:
            self._accept_inserted_disk(info)
            return

        def _on_managed_objects(managed: dict) -> None:
            ifaces = managed.get(obj_path)
            if not ifaces:
                return
            resolved = self._build_disk_info_from_ifaces(obj_path, dict(ifaces))
            if resolved:
                self._accept_inserted_disk(resolved)

        def _on_error(err: Exception) -> None:
            logger.error(f"Async GetManagedObjects failed for {obj_path}: {err}")

        try:
            self.obj_manager.GetManagedObjects(
                reply_handler=_on_managed_objects,
                error_handler=_on_error,
            )
        except Exception as exc:
            logger.error(f"Failed to dispatch async GetManagedObjects: {exc}")


# ---------------------------------------------------------------------------
# System Polling Managers (CPU, Thermals, Memory, GPU, Network)
# ---------------------------------------------------------------------------


class CpuManager:
    """Polls CPU usage, frequency, and per-core usage."""

    def __init__(self, on_update: Callable[[dict[str, Any]], None]) -> None:
        self.on_update = on_update
        self.latest: dict[str, Any] = {
            "usage": 0.0,
            "freq": None,
            "per_core": [],
        }
        self._poll()
        GLib.timeout_add(1000, self._poll)

    def _poll(self) -> bool:
        try:
            usage = float(psutil.cpu_percent())
        except Exception:
            usage = 0.0

        try:
            cur_freq = psutil.cpu_freq()
        except Exception:
            cur_freq = None

        try:
            per_core = list(psutil.cpu_percent(percpu=True))
        except Exception:
            per_core = []

        self.latest = {
            "usage": usage,
            "freq": cur_freq,
            "per_core": per_core,
        }
        self.on_update(self.latest)
        return True


class ThermalsManager:
    """Polls temperatures from all sensors and fan speeds when available."""

    CPU_DRIVERS = (
        "k10temp",
        "coretemp",
        "cpu_thermal",
        "soc_thermal",
        "zenpower",
    )

    def __init__(self, on_update: Callable[[dict[str, Any]], None]) -> None:
        self.on_update = on_update
        self.latest: dict[str, Any] = {
            "sensors": {},
            "cpu_temp": None,
            "fans": {},
            "fan_speed": None,
        }
        self._poll()
        GLib.timeout_add(1000, self._poll)

    def _poll(self) -> bool:
        sensors_map: dict[str, list[dict[str, Any]]] = {}
        cpu_temp = None

        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for driver, entries in temps.items():
                    driver_key = str(driver)
                    parsed_entries: list[dict[str, Any]] = []
                    for idx, entry in enumerate(entries or []):
                        current_val = getattr(entry, "current", None)
                        if current_val is None:
                            continue
                        label = str(getattr(entry, "label", "") or f"Sensor {idx + 1}")
                        parsed_entries.append(
                            {
                                "label": label,
                                "current": float(current_val),
                                "high": getattr(entry, "high", None),
                                "critical": getattr(entry, "critical", None),
                                "raw": entry,
                            }
                        )
                    if parsed_entries:
                        sensors_map[driver_key] = parsed_entries

                for driver in self.CPU_DRIVERS:
                    if sensors_map.get(driver):
                        cpu_temp = sensors_map[driver][0]["raw"]
                        break

                if cpu_temp is None and sensors_map:
                    first_driver = next(iter(sensors_map))
                    cpu_temp = sensors_map[first_driver][0]["raw"]
        except Exception as exc:
            logger.debug(f"Failed to read temperature sensors: {exc}")

        fans_map: dict[str, list[dict[str, Any]]] = {}
        fan_speed = None

        try:
            fans = psutil.sensors_fans()
            if fans:
                for driver, entries in fans.items():
                    driver_key = str(driver)
                    parsed_fans: list[dict[str, Any]] = []
                    for idx, entry in enumerate(entries or []):
                        current_rpm = getattr(entry, "current", None)
                        if current_rpm is None:
                            continue
                        label = str(getattr(entry, "label", "") or f"Fan {idx + 1}")
                        parsed_fans.append(
                            {
                                "label": label,
                                "current": float(current_rpm),
                                "raw": entry,
                            }
                        )
                    if parsed_fans:
                        fans_map[driver_key] = parsed_fans

                if fans_map:
                    first_fan_driver = next(iter(fans_map))
                    fan_speed = fans_map[first_fan_driver][0]["raw"]
        except Exception as exc:
            logger.debug(f"Failed to read fan sensors: {exc}")

        self.latest = {
            "sensors": sensors_map,
            "cpu_temp": cpu_temp,
            "fans": fans_map,
            "fan_speed": fan_speed,
        }
        self.on_update(self.latest)
        return True


class MemoryManager:
    """Polls RAM and swap memory statistics."""

    def __init__(self, on_update: Callable[[dict[str, Any]], None]) -> None:
        self.on_update = on_update
        self.latest: dict[str, Any] = {
            "usage": 0.0,
            "ram": None,
            "swap": None,
        }
        self._poll()
        GLib.timeout_add(1000, self._poll)

    def _poll(self) -> bool:
        try:
            ram = psutil.virtual_memory()
            swap = psutil.swap_memory()
            self.latest = {
                "usage": float(ram.percent),
                "ram": ram,
                "swap": swap,
            }
            self.on_update(self.latest)
        except Exception as exc:
            logger.error(f"Failed to poll memory: {exc}")
        return True


class GpuManager:
    """Polls NVIDIA GPU metrics in a background thread."""

    MAX_DEVICES = 3

    def __init__(self, on_update: Callable[[list[dict[str, Any]]], None]) -> None:
        self.on_update = on_update
        self.latest: list[dict[str, Any]] = []
        self._running = False
        self._trigger_poll()
        GLib.timeout_add(1000, self._trigger_poll)

    def _trigger_poll(self) -> bool:
        if not self._running:
            self._running = True
            threading.Thread(target=self._fetch_gpu_data, daemon=True).start()
        return True

    def _fetch_gpu_data(self) -> None:
        cmd = [
            "nvidia-smi",
            (
                "--query-gpu=name,utilization.gpu,memory.used,memory.total,"
                "temperature.gpu,clocks.gr,clocks.mem,power.draw"
            ),
            "--format=csv,noheader,nounits",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split("\n")
            devices_data: list[dict[str, Any]] = []
            for index, line in enumerate(lines):
                if index >= self.MAX_DEVICES:
                    break
                parts = [p.strip() for p in line.split(",")]
                if len(parts) == 8:
                    used_mib = float(parts[2])
                    total_mib = float(parts[3])
                    devices_data.append(
                        {
                            "name": parts[0],
                            "gpu_util": float(parts[1]),
                            "used_gb": used_mib / 1024,
                            "vram_percent": (used_mib / total_mib) * 100
                            if total_mib
                            else 0.0,
                            "temp": parts[4],
                            "gpu_clock": parts[5],
                            "mem_clock": parts[6],
                            "power": parts[7],
                            "index": index,
                        }
                    )
            if devices_data:
                _run_on_main_thread(self._commit, devices_data)
        except Exception:
            pass
        finally:
            self._running = False

    def _commit(self, devices_data: list[dict[str, Any]]) -> None:
        self.latest = devices_data
        self.on_update(self.latest)


class NetworkManager:
    """Polls network download/upload speeds and optional per-process connections."""

    POLL_TIME = 1

    def __init__(self, on_update: Callable[[dict[str, Any]], None]) -> None:
        self.on_update = on_update
        self.collect_processes = False
        self.latest: dict[str, Any] = {
            "dl_kbs": 0.0,
            "ul_kbs": 0.0,
            "dl_bytes": 0,
            "ul_bytes": 0,
            "top_processes": [],
        }
        threading.Thread(target=self._poll_loop, daemon=True).start()

    def _build_top_processes(
        self, total_dl_bytes: int, total_ul_bytes: int
    ) -> list[dict[str, Any]]:
        conn_map: dict[int, int] = {}
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.pid and conn.status == "ESTABLISHED":
                    conn_map[conn.pid] = conn_map.get(conn.pid, 0) + 1
        except (psutil.AccessDenied, PermissionError):
            pass

        if not conn_map:
            return []

        entries: list[dict[str, Any]] = []
        total_conns = 0
        for pid, count in conn_map.items():
            try:
                name = psutil.Process(pid).name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            entries.append({"name": name, "weight": count})
            total_conns += count

        if total_conns == 0:
            return []

        entries.sort(key=lambda e: e["weight"], reverse=True)
        top = []
        for entry in entries[:5]:
            share = entry["weight"] / total_conns
            top.append(
                {
                    "name": entry["name"],
                    "count": entry["weight"],
                    "dl_est": total_dl_bytes * share,
                    "ul_est": total_ul_bytes * share,
                }
            )
        return top

    def _poll_loop(self) -> None:
        initial_poll = True
        while True:
            initial = psutil.net_io_counters()
            if initial_poll:
                time.sleep(0.1)
                initial_poll = False
            else:
                time.sleep(self.POLL_TIME)
            final = psutil.net_io_counters()

            dl_bytes = final.bytes_recv - initial.bytes_recv
            ul_bytes = final.bytes_sent - initial.bytes_sent
            dl_kbs = (dl_bytes / 1024) * self.POLL_TIME
            ul_kbs = (ul_bytes / 1024) * self.POLL_TIME

            top_procs = (
                self._build_top_processes(dl_bytes, ul_bytes)
                if self.collect_processes
                else []
            )

            payload = {
                "dl_kbs": dl_kbs,
                "ul_kbs": ul_kbs,
                "dl_bytes": dl_bytes,
                "ul_bytes": ul_bytes,
                "top_processes": top_procs,
            }
            _run_on_main_thread(self._commit, payload)

    def _commit(self, payload: dict[str, Any]) -> None:
        self.latest = payload
        self.on_update(self.latest)


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
    def cpu_updated(self):
        """when cpu metrics update"""

    @Signal
    def thermals_updated(self):
        """when thermal or fan sensors update"""

    @Signal
    def memory_tick(self):
        """when memory poll triggers"""

    @Signal
    def memory_updated(self):
        """when memory metrics update"""

    @Signal
    def gpu_updated(self):
        """when gpu metrics update"""

    @Signal
    def network_updated(self):
        """when network metrics update"""

    @Signal
    def sensors_tick(self):
        """when sensors poll triggers"""

    @Signal
    def disk_inserted(self):
        """when a new storage filesystem is detected"""

    @Signal
    def disk_mounted(self):
        """when a storage filesystem is mounted"""

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
        self.notifier = NotificationHelper(app_name="SystemService")
        self._last_inserted_disk: DiskMountInfo | None = None
        self._last_mounted_disk: tuple[DiskMountInfo, str] | None = None

        self.power = PowerManager(
            self.bus,
            on_battery_update=self._handle_battery_update,
            on_device_added=self._handle_device_inserted,
        )
        self.storage = StorageManager(
            self.bus,
            notifier=self.notifier,
            on_disk_inserted=self._handle_disk_inserted,
            on_disk_mounted=self._handle_disk_mounted,
        )
        self.cpu = CpuManager(on_update=self._handle_cpu_update)
        self.thermals = ThermalsManager(on_update=self._handle_thermals_update)
        self.memory = MemoryManager(on_update=self._handle_memory_update)
        self.gpu = GpuManager(on_update=self._handle_gpu_update)
        self.network = NetworkManager(on_update=self._handle_network_update)

        self._initialized = True

    def _handle_battery_update(self, device: UPowerDevice) -> None:
        self.battery_info_update.emit()

    def _handle_device_inserted(self, device: Any) -> None:
        self.new_device_inserted.emit()

    def _handle_storage_inserted(self, object_path: str) -> None:
        self.new_device_inserted.emit()

    def _handle_disk_inserted(self, disk_info: DiskMountInfo) -> None:
        self._last_inserted_disk = disk_info
        self.disk_inserted.emit()

    def _handle_disk_mounted(self, disk_info: DiskMountInfo, mount_path: str) -> None:
        self._last_mounted_disk = (disk_info, mount_path)
        self.disk_mounted.emit()

    def _handle_cpu_update(self, _data: dict[str, Any]) -> None:
        self.cpu_tick.emit()
        self.cpu_updated.emit()

    def _handle_thermals_update(self, _data: dict[str, Any]) -> None:
        self.sensors_tick.emit()
        self.thermals_updated.emit()

    def _handle_memory_update(self, _data: dict[str, Any]) -> None:
        self.memory_tick.emit()
        self.memory_updated.emit()

    def _handle_gpu_update(self, _data: list[dict[str, Any]]) -> None:
        self.gpu_updated.emit()

    def _handle_network_update(self, _data: dict[str, Any]) -> None:
        self.network_updated.emit()