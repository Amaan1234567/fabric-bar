"""holds the widget to toggle wifi"""

from gi.repository import GLib  # type: ignore
from fabric.widgets.button import Button
from fabric.utils.helpers import exec_shell_command_async
from loguru import logger


class WifiToggle(Button):
    """
    Simple WiFi toggle button.
    Shows WiFi with slash if no WiFi card/driver issues.
    Background changes based on state via CSS classes.
    """

    def __init__(self):
        super().__init__(
            name="wifi-toggle",
            label="󰤨",  # Nerd Font WiFi icon
            on_clicked=self._toggle_wifi,
        )
        self.wifi_available = True
        self.wifi_on = True
        self._is_wifi_available()
        self._is_wifi_on()
        self.set_hexpand(True)
        self.set_vexpand(False)

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
        # Poll every 5s to keep in sync
        GLib.timeout_add_seconds(1, self._refresh)
        self.set_tooltip_text("Toggle Wifi")

    def _wifi_on_callback(self, output):
        self.wifi_on = output == "enabled"

    def _is_wifi_on(self):
        exec_shell_command_async(["nmcli", "radio", "wifi"], self._wifi_on_callback)

    def _toggle_wifi(self, _):
        """Toggle WiFi on/off"""
        if not self.wifi_available:
            return  # Can't toggle if WiFi hardware isn't available

        cmd = ["off", "on"][not self.wifi_on]
        exec_shell_command_async(["nmcli", "radio", "wifi", cmd])

    def _wifi_check_callback(self, output):
        logger.debug(f"wifi toggle output: {output}")
        if int(output) > 1:
            self.wifi_available = True
        else:
            self.wifi_available = False

    def _is_wifi_available(self):
        """Check if WiFi hardware is available"""
        exec_shell_command_async(
            ["nmcli", "device", " | ", "grep", "-c", "wifi"], self._wifi_check_callback
        )

    def _refresh(self) -> bool:
        """Update WiFi status and icon"""

        ctx = self.get_style_context()
        self._is_wifi_on()
        self._is_wifi_available()
        if not self.wifi_available:
            # WiFi hardware not available - show slash icon
            self.set_label("󰤭")  # WiFi off/slash icon
            ctx.add_class("wifi-unavailable")
            ctx.remove_class("wifi-on")
            ctx.remove_class("wifi-off")
        else:

            if self.wifi_on:
                self.set_label("󰤨")  # WiFi on icon
                ctx.add_class("wifi-on")
                ctx.remove_class("wifi-off")
                ctx.remove_class("wifi-unavailable")
            else:
                self.set_label("󰤭")  # WiFi off icon
                ctx.add_class("wifi-off")
                ctx.remove_class("wifi-on")
                ctx.remove_class("wifi-unavailable")

        return True  # Keep timeout alive
