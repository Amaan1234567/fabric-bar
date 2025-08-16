import subprocess
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
from fabric.widgets.button import Button


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

        # Set initial state
        self._refresh()
        self.connect(
            "state-flags-changed",
            lambda btn, *_: (
                btn.set_cursor("pointer")
                if btn.get_state_flags() & 2  # type: ignore
                else btn.set_cursor("default"),
            ),
        )
        # Poll every 6s to keep in sync
        GLib.timeout_add_seconds(6, self._refresh)

    @staticmethod
    def _bluetooth_is_on() -> bool:
        """Returns True if bluetoothctl reports Powered: yes"""
        try:
            out = subprocess.run(
                ["bluetoothctl", "show"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout
            return "Powered: yes" in out
        except Exception:
            return False

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
            )
        except Exception:
            pass

        # Refresh after short delay
        GLib.timeout_add(800, self._refresh)
