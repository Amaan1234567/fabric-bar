"""holds the network service"""

from ast import Dict
import os
import signal
from typing import Any, Callable, List, AnyStr, Literal
from loguru import logger
from gi.repository import NM, Gio  # type: ignore
from fabric.core.service import Property, Service, Signal
from fabric.utils.helpers import bulk_connect, exec_shell_command_async


class WifiService(Service):
    """service to handle wifi device"""

    @Signal
    def scanning(self) -> None:
        """signal to indicate AP scan is going on"""

    @Signal
    def scan_complete(self) -> None:
        """signal to indicate AP scan is complete"""

    @Signal
    def network_change(self) -> None:
        """signal to indicate a change in network"""

    @Signal
    def enabled(self) -> None:
        """signal to show wifi enabled"""

    @Signal
    def disabled(self) -> None:
        """signal to show wifi disabled"""

    @Signal
    def changed(self):
        """signal to show any other change of state in service"""

    def __init__(self, client, device, **kwargs):
        self._client: NM.Client = client
        self._device: NM.DeviceWifi = device
        self._access_point: NM.AccessPoint | None = None
        self._access_point_strength: int = -1
        super().__init__(**kwargs)

        if self._device:
            bulk_connect(
                self._device,
                {
                    # Signal inherited from NM.Device
                    "state-changed": self._on_state_changed,
                    # GObject property notification signals
                    "notify::scanning": self._on_scanning_changed,
                    "notify::active-access-point": self._on_active_ap_changed,
                    # Signals specific to NM.DeviceWifi
                    "access-point-added": self._on_ap_list_changed,
                    "access-point-removed": self._on_ap_list_changed,
                },
            )
            # Set initial state
            self._on_active_ap_changed(self._device)

    def _on_state_changed(
        self,
        device: NM.Device,
        new_state: NM.DeviceState,
        old_state: NM.DeviceState,
        reason: NM.DeviceStateReason,
    ):
        """Handler for the 'state-changed' signal."""

        if (
            new_state == NM.DeviceState.ACTIVATED
            or new_state == NM.DeviceState.DISCONNECTED
        ):
            self.emit("enabled")
        elif new_state == NM.DeviceState.UNAVAILABLE:
            self.emit("disabled")

        self.emit("changed")

    def _on_scanning_changed(self, device: NM.DeviceWifi):
        """Handler for the 'notify::scanning' signal."""
        if device.props.scanning:
            logger.debug("Wifi scan started...")
            self.emit("scanning")
        else:
            logger.debug("Wifi scan finished.")
            self.emit("scan-complete")

    def _on_active_ap_changed(self, device: NM.DeviceWifi):
        """Handler for the 'notify::active-access-point' signal."""
        self._access_point = device.get_active_access_point()

        if self._access_point:
            ssid = self.ssid
            logger.debug(f"Active AP changed to: {ssid}")
            self._access_point.connect("notify::strength", self._on_ap_strength_changed)
            self._access_point_strength = self._access_point.get_strength()
        else:
            logger.debug("Active AP changed to: None (Disconnected)")

        self.emit("network-change")

    def _on_ap_strength_changed(self, ap: NM.AccessPoint):
        logger.debug(f"obtained strength {ap.get_strength()} for AP {self.ssid}")
        self._access_point_strength = ap.get_strength()

    def _on_ap_list_changed(self, device: NM.DeviceWifi, ap: NM.AccessPoint):
        """Handler for 'access-point-added' and 'access-point-removed'."""
        logger.debug("Access point list updated.")

        self.emit("scan-complete")

    @Property(bool, "read-write", default_value=False)
    def wireless_enabled(self):  # type: ignore
        """property to read if wifi enabled or disabled"""
        return bool(self._client.wireless_get_enabled())

    @wireless_enabled.setter
    def wireless_enabled(self, value: bool):
        self._client.wireless_set_enabled(value)
        if value:
            self.emit("enabled")
        else:
            self.emit("disabled")

    @Property(str, "readable")
    def ssid(self):
        """ssid property"""
        if self._access_point is not None:
            return NM.utils_ssid_to_utf8(self._access_point.get_ssid().get_data())  # type: ignore
        else:
            return "N/A"

    @Property(NM.AccessPoint, "readable")
    def active_ap(self):
        """active AP"""
        return self._access_point

    @Property(int, "readable")
    def strength(self):
        """signal strength of AP"""
        return self._access_point_strength if self._access_point else -1

    @Property(str, "readable")
    def ip(self):
        """ip address of current connection"""
        if active_connection := self._device.get_active_connection():
            if ipconfig := active_connection.get_ip4_config():
                return ipconfig.get_addresses()[0].get_address()
            else:
                return "N/A"
        else:
            return "N/A"

    @Property(int, "readable")
    def frequency(self):
        """freq of AP in MHz"""
        if self._access_point:
            return self._access_point.get_frequency()
        else:
            return -1

    def trigger_scan(self):
        """trigger a network scan async"""
        if self._device:
            self.emit("scanning")  # Emit signal that scanning has started
            self._device.request_scan_async(
                None,
                lambda device, result: [
                    device.request_scan_finish(result),
                    self.emit("scan-complete"),  # Emit signal that scanning has stopped
                ],
            )

    def get_ap_security(self, ap: NM.AccessPoint):
        """get security protocol used by AP"""
        flags = ap.get_flags()
        wpa_flags = ap.get_wpa_flags()
        rsn_flags = ap.get_rsn_flags()
        sec_str = ""
        if (
            (flags & getattr(NM, "80211ApFlags").PRIVACY)
            and (wpa_flags == 0)
            and (rsn_flags == 0)
        ):
            sec_str += " WEP"
        if wpa_flags != 0:
            sec_str += " WPA1"
        if rsn_flags != 0:
            sec_str += " WPA2"
        if (wpa_flags & getattr(NM, "80211ApSecurityFlags").KEY_MGMT_802_1X) or (
            rsn_flags & getattr(NM, "80211ApSecurityFlags").KEY_MGMT_802_1X
        ):
            sec_str += " 802.1X"

        # If there is no security use "--"
        if sec_str == "":
            sec_str = "unsecured"
        return sec_str.lstrip()

    def list_all_network(self) -> List[Any]:
        """list all networks available"""
        access_points: List[NM.AccessPoint] = self._device.get_access_points()

        unique_access_points: Dict = {}  # type: ignore
        logger.debug(f"Access points: {access_points}")
        for ap in access_points:
            ssid = NM.utils_ssid_to_utf8(ap.get_ssid().get_data() if ap.get_ssid() is not None else [0])  # type: ignore
            if ssid in unique_access_points:
                if ap.get_strength() < unique_access_points[ssid]["strength"]:  # type: ignore
                    continue

            unique_access_points[ssid] = {  # type: ignore
                "strength": ap.get_strength(),
                "freq": ap.get_frequency(),
                "security": self.get_ap_security(ap),
                "AP": ap,
                "ssid": ssid,
                "bssid": ap.get_bssid(),
            }
        sorted_networks = sorted(unique_access_points.values(), key=lambda e: e["strength"], reverse=True)  # type: ignore
        return list(map(lambda data: data, sorted_networks))

    def connect_to_ssid(
        self, ssid, password: str = "", callback: Callable[[str], bool] | None = None
    ):
        """connect to given ssid"""
        exec_shell_command_async(["nmcli", "con", "up", ssid], callback)
        exec_shell_command_async(
            [
                "nmcli",
                "device",
                "wifi",
                "connect",
                ssid,
                "password",
                password,
            ],
            callback,
        )

    def disconnect_active_connection(self):
        """disconnect from current AP"""
        self.emit("network_change")
        self._device.disconnect_async()


class EthernetService(Service):
    """A service to manage ethernet devices"""

    @Signal
    def changed(self) -> None: ...

    """signal to indicate state change"""

    @Signal
    def enabled(self) -> bool: ...

    """signal to indicate if enabled or disabled"""

    @Property(str, "readable")
    def internet(self) -> str:
        active_connection = self._client.get_active_connections()[0]
        if not active_connection:
            return "disconnected"

        return {
            NM.ActiveConnectionState.ACTIVATED: "activated",
            NM.ActiveConnectionState.ACTIVATING: "activating",
            NM.ActiveConnectionState.DEACTIVATING: "deactivating",
            NM.ActiveConnectionState.DEACTIVATED: "deactivated",
        }.get(
            active_connection.get_state(),
            "disconnected",
        )

    @Property(str, "readable")
    def icon_name(self) -> str:
        network = self.internet
        if network == "activated":
            return "network-wired-symbolic"

        elif network == "activating":
            return "network-wired-acquiring-symbolic"

        elif self._device.get_connectivity != NM.ConnectivityState.FULL:
            return "network-wired-no-route-symbolic"

        return "network-wired-disconnected-symbolic"

    @Property(str, "readable")
    def ip(self):
        """ip address of current connection"""

        if active_connection := self._client.get_active_connections()[0]:
            if ip_config := active_connection.get_ip4_config():
                return ip_config.get_addresses()[0].get_address()
            else:
                return "IP not available"
        else:
            return "No connection"

    @Property(str, "readable")
    def interface_type(self):
        """name of ethernet interface type"""
        return self._device.get_iface()

    def __init__(self, client: NM.Client, device: NM.DeviceEthernet, **kwargs) -> None:
        super().__init__(**kwargs)
        self._client: NM.Client = client
        self._device: NM.DeviceEthernet = device

        for names in (
            "active-connection",
            "icon-name",
            "internet",
            "speed",
            "state",
        ):
            self._device.connect(f"notify::{names}", lambda *_: self.notifier(names))

        self._device.connect("notify::speed", lambda *_: print(_))

    def notifier(self, names):
        self.notify(names)
        self.emit("changed")


class NetworkService(Service):
    """Service to handle network devices"""

    # makes it so that only one instance of service is created
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @Signal
    def device_ready(self) -> None:
        """signal for indicating device is ready"""

    def __init__(self, **kwargs):
        self._client: NM.Client | None = None
        self.wifi_device: WifiService | None = None
        self.ethernet_device: EthernetService | None = None
        super().__init__(**kwargs)
        NM.Client.new_async(
            cancellable=None,
            callback=self._init_network_client,
            **kwargs,
        )

    def _init_network_client(self, client: NM.Client, task: Gio.Task, **kwargs):
        self._client = client
        wifi_device: NM.DeviceWifi | None = self._get_device(NM.DeviceType.WIFI)  # type: ignore
        ethernet_device: NM.DeviceEthernet | None = self._get_device(
            NM.DeviceType.ETHERNET
        )

        if wifi_device:
            self.wifi_device = WifiService(self._client, wifi_device)
            self.emit("device-ready")

        if ethernet_device:
            self.ethernet_device = EthernetService(
                client=self._client, device=ethernet_device
            )
            self.emit("device-ready")

        self.notify("primary-device")

    def _get_device(self, device_type) -> Any:
        devices: list[NM.Device] = self._client.get_devices()  # type: ignore
        return next(
            (x for x in devices if x.get_device_type() == device_type),
            None,
        )

    def _get_primary_device(self) -> str:
        if not self._client:
            return "N/A"

        if self._client.get_primary_connection() is None:
            return "wifi"
        return (
            "wifi"
            if "wireless"
            in str(self._client.get_primary_connection().get_connection_type())
            else (str(self._client.get_primary_connection().get_connection_type()))
        )

    @Property(str, "readable")
    def primary_device(self) -> str:
        """returns primary_network device"""
        return self._get_primary_device()
