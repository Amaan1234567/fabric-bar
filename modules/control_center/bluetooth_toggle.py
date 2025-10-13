"""hold the bluetooth toggle module"""

import subprocess
from loguru import logger

from fabric.widgets.button import Button
from fabric.bluetooth.service import BluetoothClient


class BluetoothToggle(Button):
    """
    A single large button that toggles Bluetooth power.
    Shows " Bluetooth" label with Nerd Font icon.
    Background changes based on state via CSS classes.
    """

    def __init__(self):
        super().__init__(
            name="bluetooth-toggle",
            label="󰂯",  # Nerd Font Bluetooth icon + "Bluetooth"
            on_clicked=self._toggle,
        )
        self.set_hexpand(True)
        self.set_vexpand(False)

        self.bluetooth_client = BluetoothClient()
        self.bluetooth_client.connect("changed", self._refresh)
        # Set initial state
        self._refresh()
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
        self.set_tooltip_text("Toggle Bluetooth")

    def _bluetooth_is_on(self) -> bool:
        """Returns True if bluetoothctl reports Powered: yes"""
        logger.debug(f"{self.bluetooth_client.state}")
        return self.bluetooth_client.get_property("state") == "on"

    def _refresh(self) -> bool:
        """Update CSS class based on Bluetooth state"""
        powered = self._bluetooth_is_on()

        ctx = self.get_style_context()
        if powered:
            ctx.add_class("bluetooth-on")
            ctx.remove_class("bluetooth-off")
        else:
            ctx.add_class("bluetooth-off")
            ctx.remove_class("bluetooth-on")

        return True  # keep timeout alive

    def _toggle(self, _button):
        """Toggle Bluetooth power"""
        cmd = ["off", "on"][not self._bluetooth_is_on()]
        try:
            subprocess.run(
                ["bluetoothctl", "power", cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
        except TimeoutError as exception:
            logger.exception(f"{exception} encountered")
