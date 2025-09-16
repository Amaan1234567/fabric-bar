"""Hold the Bluetooth widget that displays the bluetooth status
and battery of bluetooth device if supported
"""

import subprocess
from typing import List
from loguru import logger
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.eventbox import EventBox
from fabric.utils import cooldown
from fabric.bluetooth.service import BluetoothClient, BluetoothDevice
from gi.repository import GLib, Gdk  # type: ignore


class BluetoothWidget(Box):
    """Bluetooth widget that displays the status of bluetooth,
    battery of the bluetooth device if supported, and extra info
    on the device in tooltip"""

    def __init__(self, interval=1, **kwargs):
        super().__init__(**kwargs)
        self._tooltip_text = ""
        self.interval = interval
        self._tooltip = "Bluetooth status loading..."

        self.bluetooth_client = BluetoothClient()

        self.content_event_box = EventBox(
            on_enter_notify_event=self._on_hover,
            on_button_release_event=self._on_left_click,
        )
        self.content = Box(orientation="h", spacing=0)
        self.icon = Label(name="bluetooth-icon", label="󰂯")  # Default BT icon
        self.content.set_tooltip_text(self._tooltip)
        self.percentage = Label(name="bluetooth-percentage")
        self.content.add(self.icon)

        self.button = Button(child=self.content)
        self.button.connect(
            "state-flags-changed",
            lambda btn, *_: (
                (
                    btn.set_cursor("pointer")
                    if btn.get_state_flags() & 2  # type: ignore
                    else btn.set_cursor("default")
                ),
            ),
        )
        self.content_event_box.add(self.button)
        self.add(self.content_event_box)

        self.bluetooth_client.connect("changed", self._refresh)

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

        # Initial refresh
        self._refresh()

    @cooldown(1)
    def _on_left_click(self, _, event):
        if event.button == Gdk.BUTTON_PRIMARY:
            subprocess.run(
                "blueman-manager & disown",
                shell=True,
                check=False,
            )

    def _on_hover(self):
        self._refresh()
        self._update_widget_state()
        self.content.set_tooltip_text(self._tooltip_text)

    def _refresh(self):
        self._update_widget_state()
        self.content.set_tooltip_text(self._tooltip_text)
        self._update_icon()
        return True

    def _update_icon(self):
        """Update the Bluetooth icon based on state"""
        try:
            if not self.bluetooth_client.enabled:
                self.icon.set_label("󰂲")
            elif not self.bluetooth_client.powered:
                self.icon.set_label("󰂲")
            elif len(self.bluetooth_client.connected_devices):
                self.icon.set_label("󰂱")
            else:
                self.icon.set_label("󰂯")

        except Exception as error:
            logger.exception(f"Error updating Bluetooth icon: {error}")
            self.icon.set_label("󰂲")

    def _update_widget_state(self):
        """Get Bluetooth status using Fabric's Bluetooth service"""
        try:
            if not self._bluetooth_status_checks():
                return

            # Get connected devices
            connected_devices: List[BluetoothDevice] = (
                self.bluetooth_client.connected_devices
            )
            logger.debug(f"bluetooth connected devices:{connected_devices}")

            if len(connected_devices) != 0:
                self._process_devices(connected_devices)
            else:
                self.percentage.set_label("")

                if len(self.content.children) > 1:
                    self.content.remove(self.percentage)

                self._tooltip_text = "Bluetooth On\nNo devices connected"

        except Exception as e:
            logger.exception(f"Bluetooth status error: {e}")
            self._tooltip_text = f"Bluetooth error: {e}"

    def _process_devices(self, connected_devices):
        device_info = []
        first_device_battery = None

        for device in connected_devices:
            name = device.name or device.alias or device.address or "Unknown"
            battery_level = None

            # Check if device has battery information
            battery_level = self._retrieve_battery_data(device)

            # Format device info
            first_device_battery, line = self._format_battery_data(
                first_device_battery, name, battery_level
            )

            device_info.append(line)

        # Update percentage display
        self._update_label_and_widget(first_device_battery)

        self._tooltip_text = "Bluetooth On\n" + "\n".join(device_info)

    def _update_label_and_widget(self, first_device_battery):
        if first_device_battery is not None:
            self.percentage.set_label(f"{first_device_battery}%")

            if len(self.content.children) == 1:
                self.content.add(self.percentage)
        else:
            self.percentage.set_label("")

            if len(self.content.children) > 1:
                self.content.remove(self.percentage)

    def _bluetooth_status_checks(self) -> bool:
        if not self.bluetooth_client.enabled:
            self.percentage.set_label("")

            if len(self.content.children) > 1:
                self.content.remove(self.percentage)

            self._tooltip_text = "Bluetooth not available"

            return False

        if not self.bluetooth_client.powered:
            self.percentage.set_label("")

            if len(self.content.children) > 1:
                self.content.remove(self.percentage)

            self._tooltip_text = "Bluetooth Off"

            return False

        return True

    def _format_battery_data(self, first_device_battery, name, battery_level):
        line = f"✓ {name}"

        if battery_level is not None:
            line += f" ({battery_level}%)"

            if first_device_battery is None:
                first_device_battery = battery_level
        return first_device_battery, line

    def _retrieve_battery_data(self, device) -> int | str:
        battery_level = "NaN"
        try:
            if (
                hasattr(device, "battery_percentage")
                and device.battery_percentage is not None
            ):
                battery_level = int(device.battery_percentage)
                logger.debug(f"bluetooth device battery level: {battery_level}")

            elif hasattr(device, "battery_level") and device.battery_level is not None:
                battery_level = int(device.battery_level)

        except ValueError as error:
            logger.exception(
                f"encountered following error when trying to retrieve battery information: {error}"
            )

        return battery_level
