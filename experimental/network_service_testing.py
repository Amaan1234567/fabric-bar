import os
import signal
import sys
from loguru import logger
from typing import Literal, Any

# --- PyGObject and NetworkManager Imports ---
import gi
gi.require_version("NM", "1.0")
from gi.repository import NM, Gio, GObject, GLib

# --- Fabric Imports ---
# (Assuming you have this 'fabric' framework installed)
try:
    from fabric.core.service import Service, Signal, Property
    from fabric.utils.helpers import bulk_connect
except ImportError:
    logger.error("Fabric library not found.")
    logger.error("Please ensure 'fabric.core.service' is in your PYTHONPATH.")
    # Define dummy classes to allow the script to at least be parsed
    class GObjectMeta(type(GObject.Object)):
        def __init__(cls, name, bases, attrs):
            super().__init__(name, bases, attrs)
            if "__gsignals__" in attrs:
                GObject.signal_new_class(cls, *cls.__gsignals__.items())

    class Service(GObject.Object, metaclass=GObjectMeta):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
    
    class Signal(object):
        def __init__(self, func):
            pass # This is just a decorator placeholder
    
    class Property(object):
        def __init__(self, *args):
            pass # This is just a decorator placeholder

    def bulk_connect(obj, signal_map):
        for sig_name, handler in signal_map.items():
            obj.connect(sig_name, handler)
    logger.warning("Using dummy 'fabric' classes. Real functionality will be missing.")


# -----------------------------------------------------------------
# YOUR SERVICE CODE (with corrections from previous answer)
# -----------------------------------------------------------------

class WifiService(Service):
    """Holds the network service for a Wi-Fi device"""
    
    __gsignals__ = {
        "scanning": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "scan-complete": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "network-change": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "enabled": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "disabled": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }
    
    def __init__(self, client, device, **kwargs):
        self._client: NM.Client = client
        self._device: NM.DeviceWifi = device
        self._access_point: NM.AccessPoint | None = None
        self._access_point_strength: int | None = None
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
            self._on_active_ap_changed(self._device, None)
            self._on_state_changed(self._device, self._device.get_state(), NM.DeviceState.UNKNOWN, NM.DeviceStateReason.NONE)


    def _on_state_changed(self, device: NM.Device, new_state: NM.DeviceState, old_state: NM.DeviceState, reason: NM.DeviceStateReason):
        """Handler for the 'state-changed' signal."""
        logger.debug(f"Wifi state changed: {old_state.value_nick} -> {new_state.value_nick}")
        
        if new_state == NM.DeviceState.ACTIVATED:
            self.emit("enabled")
        elif new_state in (NM.DeviceState.DEACTIVATED, NM.DeviceState.UNAVAILABLE, NM.DeviceState.DISCONNECTED):
            self.emit("disabled")
        
        self.emit("network-change")
        self.emit("changed")

    def _on_scanning_changed(self, device: NM.DeviceWifi, param_spec):
        """Handler for the 'notify::scanning' signal."""
        if device.props.scanning:
            logger.debug("Wifi scan started...")
            self.emit("scanning")
        else:
            logger.debug("Wifi scan finished.")
            self.emit("scan-complete")

    def _on_active_ap_changed(self, device: NM.DeviceWifi, param_spec):
        """Handler for the 'notify::active-access-point' signal."""
        self._access_point = device.get_active_access_point()
        
        if self._access_point:
            ssid_bytes = self._access_point.get_ssid()
            # *** FIXED HERE ***
            ssid = ssid_bytes.get_data().decode('utf-8', errors='replace') if ssid_bytes else "[Hidden]"
            logger.debug(f"Active AP changed to: {ssid}")
        else:
            logger.debug("Active AP changed to: None (Disconnected)")
        
        self.emit("network-change")
        self.emit("changed")

    def _on_ap_list_changed(self, device: NM.DeviceWifi, ap: NM.AccessPoint):
        """Handler for 'access-point-added' and 'access-point-removed'."""
        logger.debug("Access point list updated.")
        self.emit("scan-complete") # AP list updates imply a scan completed

    def request_scan(self):
        """Manually trigger a Wi-Fi scan."""
        if self._device:
            logger.info("Requesting Wi-Fi scan...")
            self._device.request_scan_async(None, None, None) # Simple scan request


class EthernetService(Service):
    """Holds the network service for an Ethernet device"""
    
    __gsignals__ = {
        "network-change": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "enabled": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "disabled": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, client, device, **kwargs):
        self._client: NM.Client = client
        self._device: NM.DeviceEthernet = device
        super().__init__(**kwargs)
        
        if self._device:
            bulk_connect(
                self._device,
                {"state-changed": self._on_state_changed}
            )
            # Set initial state
            self._on_state_changed(self._device, self._device.get_state(), NM.DeviceState.UNKNOWN, NM.DeviceStateReason.NONE)

    def _on_state_changed(self, device: NM.Device, new_state: NM.DeviceState, old_state: NM.DeviceState, reason: NM.DeviceStateReason):
        logger.debug(f"Ethernet state changed: {old_state.value_nick} -> {new_state.value_nick}")
        if new_state == NM.DeviceState.ACTIVATED:
            self.emit("enabled")
        else:
            self.emit("disabled")
        self.emit("network-change")


class NetworkService(Service):
    """Service to handle network devices"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @Signal
    def device_ready(self) -> None:
        """signal for indicating device is ready"""

    def __init__(self, **kwargs):
        if hasattr(self, "_client") and self._client: # Prevent re-initialization
             return
        self._client: NM.Client | None = None
        self.wifi_device: WifiService | None = None
        self.ethernet_device: EthernetService | None = None
        super().__init__(**kwargs)
        NM.Client.new_async(
            cancellable=None,
            callback=self._init_network_client,
        )

    def _init_network_client(self, client_obj: NM.Client, task: Gio.Task, **kwargs):
        try:
            self._client = NM.Client.new_finish(task)
        except Exception as e:
            logger.error(f"Failed to create NM.Client: {e}")
            return
            
        wifi_device: NM.DeviceWifi | None = self._get_device(NM.DeviceType.WIFI)
        ethernet_device: NM.DeviceEthernet | None = self._get_device(
            NM.DeviceType.ETHERNET
        )

        device_found = False
        if wifi_device:
            self.wifi_device = WifiService(client=self._client, device=wifi_device)
            logger.info("WifiService Initialized.")
            device_found = True

        if ethernet_device:
            self.ethernet_device = EthernetService(client=self._client, device=ethernet_device)
            logger.info("EthernetService Initialized.")
            device_found = True
        
        if device_found:
            self.emit("device-ready")
        else:
            logger.warning("No managed Wi-Fi or Ethernet devices found.")

        self.notify("primary-device")

    def _get_device(self, device_type: NM.DeviceType) -> Any:
        devices: list[NM.Device] = self._client.get_devices()
        return next(
            (x for x in devices if x.get_device_type() == device_type and x.get_managed()),
            None,
        )

    def _get_primary_device(self) -> Literal["wifi", "wired"] | None:
        if not self._client:
            return None

        primary_conn = self._client.get_primary_connection()
        if primary_conn is None:
            return None # No active connection

        conn_type = primary_conn.get_connection_type()
        if "wireless" in conn_type:
            return "wifi"
        elif "ethernet" in conn_type:
            return "wired"
        else:
            return None

    @Property(str, "readable")
    def primary_device(self) -> Literal["wifi", "wired"] | None:
        return self._get_primary_device()


# -----------------------------------------------------------------
# TOY TEST SCRIPT
# -----------------------------------------------------------------

def on_device_ready(service: NetworkService, *args):
    print("\n✅ NETWORK SERVICE: Device(s) are ready.")
    print(f"   Primary device is currently: {service.primary_device}")
    
    # --- Connect to Wi-Fi signals ---
    if service.wifi_device:
        print("   Found Wi-Fi device. Connecting to its signals...")
        service.wifi_device.connect("scanning", on_wifi_scanning)
        service.wifi_device.connect("scan-complete", on_wifi_scan_complete, service.wifi_device) # Pass service for AP list
        service.wifi_device.connect("network-change", on_wifi_network_change, service.wifi_device)
        service.wifi_device.connect("enabled", on_wifi_enabled)
        service.wifi_device.connect("disabled", on_wifi_disabled)
        
        # Trigger an initial scan
        service.wifi_device.request_scan()

    # --- Connect to Ethernet signals ---
    if service.ethernet_device:
        print("   Found Ethernet device. Connecting to its signals...")
        service.ethernet_device.connect("enabled", on_eth_enabled)
        service.ethernet_device.connect("disabled", on_eth_disabled)

def on_wifi_scanning(service: WifiService, *args):
    print("📡 WIFI: Scanning for networks...")

def on_wifi_scan_complete(service: WifiService, *args):
    print("📡 WIFI: Scan complete. Available APs:")
    try:
        aps = service._device.get_access_points()
        if not aps:
            print("  (No APs found or list is empty)")
            return
        
        # Sort by strength
        aps.sort(key=lambda ap: ap.get_strength(), reverse=True)
        
        for i, ap in enumerate(aps[:10]): # Print top 10
            ssid_bytes = ap.get_ssid()
            # *** FIXED HERE ***
            ssid = ssid_bytes.get_data().decode('utf-8', errors='replace') if ssid_bytes else "[Hidden]"
            print(f"  - {ssid:<30} ({ap.get_strength()}%)")
        if len(aps) > 10:
            print(f"  ...and {len(aps) - 10} more.")
            
    except Exception as e:
        print(f"  (Could not get APs: {e})")

def on_wifi_network_change(service: WifiService, *args):
    print("\n🔄 WIFI: Network change detected.")
    active_ap = service._access_point
    if active_ap:
        ssid_bytes = active_ap.get_ssid().__str__
        # *** ALSO FIXED HERE (for consistency) ***
        ssid = ssid_bytes.get_data().decode('utf-8', errors='replace') if ssid_bytes else "[Hidden]"
        print(f"  -> Now connected to: {ssid}")
    else:
        print(f"  -> Now disconnected.")

def on_wifi_enabled(service: WifiService, *args):
    print("🟢 WIFI: Enabled (Activated).")

def on_wifi_disabled(service: WifiService, *args):
    print("🔴 WIFI: Disabled (Deactivated/Disconnected).")

def on_eth_enabled(service: EthernetService, *args):
    print("🟢 ETHERNET: Enabled (Plugged in and active).")

def on_eth_disabled(service: EthernetService, *args):
    print("🔴 ETHERNET: Disabled (Unplugged or inactive).")


if __name__ == "__main__":
    # --- Configure logging ---
    logger.remove()
    logger.add(sys.stderr, level="INFO") # Change to "DEBUG" for more verbose output

    print("Starting Network Service Test...")
    print("Press Ctrl+C to exit.")

    # --- Setup MainLoop ---
    loop = GLib.MainLoop()
    
    # --- Instantiate Service ---
    # This automatically starts the _init_network_client async call
    network_service = NetworkService()
    
    # --- Connect to the main service signal ---
    network_service.connect("device-ready", on_device_ready)
    
    # --- Run the loop ---
    try:
        loop.run()
    except KeyboardInterrupt:
        pass
    finally:
        loop.quit()
        print("\nExiting...")