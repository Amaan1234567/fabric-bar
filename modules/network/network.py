"""holds the network widget shown in bar"""

from loguru import logger
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.eventbox import EventBox
from fabric.widgets.revealer import Revealer
from fabric.widgets.button import Button
from fabric.widgets.entry import Entry
from fabric.utils.helpers import exec_shell_command_async
from gi.repository import GLib, Gdk #type: ignore


from custom_widgets.popwindow import PopupWindow
from services.networkservice import NetworkService, WifiService, EthernetService


class NetworkWidget(Box):
    """
    A Fabric widget displaying network type & strength using JetBrainsMono Nerd Font glyphs.
    Polls ActiveConnections via NetworkManager for both Wi-Fi and Ethernet.
    """

    def __init__(self, window, interval=1, **kwargs):
        super().__init__(**kwargs)

        self.interval = interval
        self.window = window
        self.networks = []
        self._scanning = False
        self.wifi_on = False
        self.ethernet_on = False
        self.connected_ssid = ""
        self.saved_connections = []
        self._service = NetworkService()
        self._ethernet_device: EthernetService | None = None
        self._wifi_device: WifiService | None = None
        self._service.connect("device_ready", self._init_device)
        self.current_tooltip = ""

        # Glyph label
        self.content = EventBox(
            on_enter_notify_event=self._on_hover,
            on_button_release_event=self.on_left_click,
        )
        self.icon = Label(name="network-icon", label="󰤯", justification="center")
        self.content.add(self.icon)
        self.add(self.content)

        self.connect("enter-notify-event", self._on_hover)
        self.connect(
            "state-flags-changed",
            lambda btn, *_: (
                (
                    btn.set_cursor("pointer")
                    if btn.get_state_flags() & 2  # type: ignore
                    else btn.set_cursor("default")
                ),
            ),
        )

        self.networks_box = Box(
            name="wifi-networks-box",
            orientation="vertical",
            spacing=4,
        )

        # Revealer for slide animation
        self.networks_revealer = Revealer(
            name="wifi-networks-revealer",
            transition_type="slide-down",
            transition_duration=200,
            child_revealed=True,  # Always revealed inside popup
        )
        self.networks_revealer.add(self.networks_box)

        # Popup window
        self.networks_popup = PopupWindow(
            parent=self.window,
            pointing_to=self,
            title="fabric-networks-popup",
            name="networks-overlay-window",
            layer="top",
            type="popup",
            anchor="top right",
            visible=False,
            child=self.networks_revealer,
            v_expand=False,
            h_expand=False,
            keyboard_mode="on_demand",
        )

        self._auto_hide_timer = None
        self._is_hovering = False

        self.networks_popup.connect("enter-notify-event", self._on_popup_enter)
        self.networks_popup.connect("leave-notify-event", self._on_popup_leave)

    def _init_device(self):
        logger.debug("device ready initialising")
        self._ethernet_device = self._service.ethernet_device
        self._wifi_device = self._service.wifi_device
        if self._wifi_device is not None:
            self._wifi_device.connect("scanning", self._scanning_handler)
            self._wifi_device.connect("scan_complete", self._scan_complete_handler)
            self._wifi_device.connect("network_change", self._refresh)
            self._wifi_device.connect("enabled", self._wifi_enabled)
            self._wifi_device.connect("disabled", self._wifi_disabled)
            self.wifi_on = self._wifi_device.wireless_enabled
        if self._ethernet_device is not None:
            self._ethernet_device.connect("enabled", self._ethernet_enabled)
            self._ethernet_device.connect("changed", self._refresh)
        self._refresh()

    def _ethernet_enabled(self, is_enabled: bool):
        self.ethernet_on = is_enabled
        self._refresh()

    def _wifi_enabled(self):
        self.wifi_on = True
        self._refresh()

    def _wifi_disabled(self):
        self.wifi_on = False
        self._refresh()

    def _scanning_handler(self):
        self._scanning = True

    def _scan_complete_handler(self):
        self._scanning = False

    def _on_popup_enter(self, _, __):
        """Called when mouse enters the popup"""
        self._is_hovering = True
        self._cancel_auto_hide_timer()

    def _on_popup_leave(self, _, __):
        """Called when mouse leaves the popup"""
        self._is_hovering = False
        self._start_auto_hide_timer()

    def _start_auto_hide_timer(self):
        """Start the auto-hide timer (1.5 seconds)"""
        self._cancel_auto_hide_timer()
        self._auto_hide_timer = GLib.timeout_add(1500, self._auto_hide_popup)

    def _cancel_auto_hide_timer(self):
        """Cancel the auto-hide timer if it exists"""
        if self._auto_hide_timer:
            GLib.source_remove(self._auto_hide_timer)
            self._auto_hide_timer = None

    def _auto_hide_popup(self):
        """Hide the popup automatically (called by timer)"""
        if not self._is_hovering and self.networks_popup.get_visible():
            self.networks_revealer.set_reveal_child(False)
            GLib.timeout_add(250, self.networks_popup.set_visible, False)

        self._auto_hide_timer = None
        return False  # Don't repeat timer

    def on_left_click(self, _, event):
        """Handle click events"""
        if event.button == Gdk.BUTTON_PRIMARY:  # type: ignore
            self._toggle_networks_popup()

    def _toggle_networks_popup(self):
        """Toggle the networks popup"""
        if not self.wifi_on:
            return

        if self.networks_popup.get_visible():

            self.networks_revealer.set_reveal_child(False)
            GLib.timeout_add(250, self.networks_popup.set_visible, False)
        else:
            if self._wifi_device is not None:
                self._wifi_device.trigger_scan()
                self._get_saved_connections_async()

            self._on_popup_enter(None, None)
            if self._scanning:
                GLib.timeout_add(250, self._populate_networks_ui)
                GLib.timeout_add(250, self.networks_popup.set_visible, True)
                GLib.timeout_add(250, self.networks_revealer.set_reveal_child, True)

    def _populate_networks_ui(self):
        """Populate networks UI (called on main thread)"""
        if self._wifi_device is None:
            logger.exception("Wifi not available")
            return
        self.networks = self._wifi_device.list_all_network()
        logger.debug(f"Updating networks list, {len(self.networks)} networks available")
        logger.debug(self.networks)

        for child in self.networks_box.children:
            self.networks_box.remove(child)

        if not self._wifi_device.wireless_enabled:
            logger.debug("Wifi is Off or not available")
            no_networks = Label(name="wifi-no-networks", label="Wifi is Off")
            self.networks_box.add(no_networks)
            return

        if len(self.networks) == 0 or self._scanning:
            logger.debug("No networks found, showing message")
            no_networks = Label(
                name="wifi-no-networks", label="🔄 Scanning for networks..."
            )
            self.networks_box.add(no_networks)
            return

        # Add network buttons (limit to 8)
        network_containers = self._create_network_containers()
        self.networks_box.children = network_containers

    def _on_connections_complete(self, result):
        try:
            stdout = result

            saved_ssids = []
            if stdout:
                for line in stdout.strip().split("\n"):
                    if not line:
                        continue
                    parts = line.split(":")
                    if len(parts) >= 2 and parts[1] == "802-11-wireless":
                        saved_ssids.append(parts[0])
            self.saved_connections.extend(saved_ssids)

        except Exception as e:
            logger.exception(f"Failed to parse connections: {e}")

    def _on_connections_received(self):
        self._populate_networks_ui()

    def _get_saved_connections_async(self):
        """Get saved connections asynchronously"""
        try:
            self.saved_connections = []
            exec_shell_command_async(
                ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"],
                self._on_connections_complete,
            )
        except Exception as e:
            logger.exception(f"Failed to get connections async: {e}")
            self._on_connections_received()

    def _create_network_containers(self):
        network_containers = []
        for network in self.networks[:8]:
            try:
                ssid, signal, is_secure = self._get_network_details(network)

                logger.debug(f"Processing network: {ssid}, secure: {is_secure}")
                if ssid == "":
                    continue
                is_saved = ssid in self.saved_connections
                # Create network container
                network_container, network_button = self._create_network_container(
                    ssid, signal, is_secure, is_saved
                )
                # Add password entry if network is secured and not saved
                # print(ssid,is_saved)
                logger.debug(self.saved_connections)
                if not is_saved:
                    self._add_password_entry_box(
                        ssid, is_secure, network_container, network_button
                    )

                network_containers.append(network_container)
                # print(f"Added network button for: {ssid}")

            except Exception as e:
                logger.exception(f"Error adding network {network}: {e}")
                continue
        return network_containers

    def _get_network_details(self, network):
        ssid = network.get("ssid", "")
        signal = network.get("strength", 0)
        is_secure = bool(network.get("security", ""))
        return ssid, signal, is_secure

    def _add_password_entry_box(self, *args):
        ssid, is_secure, network_container, network_button = args

        if is_secure:
            password_box = Box(
                name="wifi-password-box",
                orientation="horizontal",
                spacing=4,
                h_align="start",
            )

            password_entry = Entry(
                name="wifi-password-entry",
                placeholder_text="Password",
                password=True,
                h_expand=True,
            )
            password_entry.get_style_context().add_class("wifi-password-entry")
            password_entry.connect(
                "activate",
                lambda entry, s=ssid: self._connect_to_network(
                    s, password_entry.get_text()
                ),
            )

            cancel_btn = Button(
                name="wifi-password-cancel",
                label="✕",
                on_clicked=lambda btn, container=network_container: self._hide_password_entry(
                    container
                ),
            )

            password_box.children = [password_entry, cancel_btn]

            password_revealer = Revealer(
                name="wifi-password-revealer",
                transition_type="slide-down",
                transition_duration=200,
                child_revealed=False,
            )
            password_revealer.add(password_box)

            network_container.add(password_revealer)

            # Store revealer reference on the button for later access
            network_button.password_revealer = password_revealer
            network_button.password_entry = password_entry

    def _create_network_container(self, ssid, signal, is_secure, is_saved):
        network_container = Box(
            name="wifi-network-container",
            orientation="vertical",
            spacing=2,
        )

        # Create network button
        lock_icon = "" if is_secure else ""
        label = f"{lock_icon} {ssid} ({signal}%)"

        network_button = Button(
            name="wifi-network-available",
            label=label,
            h_align="start",
            on_clicked=lambda btn, s=ssid, sec=is_secure, saved=is_saved:
            self._handle_network_click(
                s, sec, saved, btn
            ),
        )
        network_button.connect(
            "state-flags-changed",
            lambda btn, *_: (
                (
                    btn.set_cursor("pointer")
                    if btn.get_state_flags() & 2  # type: ignore
                    else btn.set_cursor("default")
                ),
            ),
        )

        network_container.add(network_button)
        return network_container, network_button

    def _handle_network_click(self, ssid, is_secure, is_saved, button):
        """Handle network button click"""
        # print(f"Network clicked: {ssid}, secure: {is_secure}, saved: {is_saved}")

        if not is_secure:
            # Open network - connect directly
            self._connect_to_network(ssid, None)
        else:
            if is_saved:
                self._connect_to_network(ssid, None)
                logger.debug(f"attempting to connect to {ssid}")
            if hasattr(button, "password_revealer"):
                # Hide all other password entries first
                self._hide_all_password_entries()
                # Show this network's password entry
                button.password_revealer.set_reveal_child(True)

    def _hide_all_password_entries(self):
        """Hide all password entry revealers"""
        for container in self.networks_box.children:
            if hasattr(container, "children"):
                for child in container.children:
                    if isinstance(child, Button) and hasattr(
                        child, "password_revealer"
                    ):
                        child.password_revealer.set_reveal_child(False)

    def _hide_password_entry(self, container):
        """Hide password entry for a specific container"""
        for child in container.children:
            if isinstance(child, Button) and hasattr(child, "password_revealer"):
                child.password_revealer.set_reveal_child(False)

    def _connection_attempt_callback(self, output) -> bool:
        if "successfully" in output:
            exec_shell_command_async(f"notify-send \"Network Updated\" \"Successfully connected to {self._wifi_device.ssid}\"")
            GLib.idle_add(self.networks_popup.set_visible, False)
            return True
        return False

    def _connect_to_network(self, ssid, password):
        """Connect to a network with optional password"""
        # print(f"Connecting to {ssid} with {'password' if password else 'no password'}")
        if self._wifi_device is not None:
            self._wifi_device.connect_to_ssid(
                ssid=ssid, password=password, callback=self._connection_attempt_callback
            )

    def _on_hover(self):
        self._refresh()
        self.icon.set_tooltip_text(self.current_tooltip)

    def _refresh(self):

        status, strength, tooltip = self._get_active_connection_info()
        self.current_tooltip = tooltip or "Network"
        glyph = self._map_glyph(status, strength)
        self.icon.set_label(glyph)

    def _get_active_connection_info(self):
        """Get active connection info with minimal D-Bus calls"""
        tooltip = ""
        status = ""
        strength = None
        if self._wifi_device is not None:
            status = "wifi"
            strength = None
            ip = self._wifi_device.ip
            if self._wifi_device.wireless_enabled:
                strength = self._wifi_device.strength
                tooltip += (
                    f"Wi-Fi: {self._wifi_device.ssid}\nIP: {ip}\nStrength: {strength}%"
                )
                return status, strength, tooltip
            else:
                status = "off"
                tooltip += "Wifi disabled\n"
                strength = 0
        if self._ethernet_device is not None:
            status = "ethernet"
            interface = self._ethernet_device.interface_type
            ip = self._ethernet_device.ip
            if interface == "usb":
                status = "tether"
            tooltip += f"Ethernet:\nInterface: {interface}\nIP: {ip}"

        if status == "":
            return "none", None, "No Network devices found"
        else:
            return status, strength, tooltip

    def _map_glyph(self, status: str, strength: int | None) -> str:
        """
        Maps connection status and signal strength to JetBrainsMono Nerd Font glyphs.
        """
        wifi = {"empty": "󰤯", "low": "󰤟", "medium": "󰤢", "high": "󰤥", "full": "󰤨"}
        eth = "󰈀"
        usb = ""
        off = "󰤭"
        logger.debug(f"status: {status}")
        logger.debug(f"strength: {strength}")
        if status == "wifi" and strength is not None and self.wifi_on:
            if strength < 25:
                lvl = "empty"
            elif strength < 50:
                lvl = "low"
            elif strength < 75:
                lvl = "medium"
            elif strength < 95:
                lvl = "high"
            else:
                lvl = "full"
            glyph = wifi.get(lvl, off)
            return glyph
        if status == "ethernet":
            return eth
        if status == "tether":
            return usb
        return off
