import subprocess
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
from fabric.widgets.button import Button


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
        # Poll every 5s to keep in sync
        GLib.timeout_add_seconds(5, self._refresh)
        self.set_tooltip_text("Toggle Wifi")

    def _toggle_wifi(self, button):
        """Toggle WiFi on/off"""
        if not self._wifi_is_available():
            return  # Can't toggle if WiFi hardware isn't available
            
        cmd = ["off", "on"][not self._wifi_is_on()]
        try:
            subprocess.run([
                "nmcli", "radio", "wifi", cmd
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass
        
        GLib.timeout_add(1500, self._refresh)

    @staticmethod
    def _wifi_is_available() -> bool:
        """Check if WiFi hardware is available"""
        try:
            result = subprocess.run([
                "nmcli", "radio", "wifi"
            ], capture_output=True, text=True, check=False)
            
            # If command fails, WiFi is not available
            if result.returncode != 0:
                return False
                
            # Check if output contains any valid state (enabled/disabled)
            output = result.stdout.strip().lower()
            return output in ["enabled", "disabled"]
            
        except:
            return False

    @staticmethod
    def _wifi_is_on() -> bool:
        """Check if WiFi is enabled"""
        try:
            result = subprocess.run([
                "nmcli", "radio", "wifi"
            ], capture_output=True, text=True, check=False)
            return "enabled" in result.stdout
        except:
            return False

    def _refresh(self) -> bool:
        """Update WiFi status and icon"""
        ctx = self.get_style_context()
        
        if not self._wifi_is_available():
            # WiFi hardware not available - show slash icon
            self.set_label("󰤭")  # WiFi off/slash icon
            ctx.add_class("wifi-unavailable")
            ctx.remove_class("wifi-on")
            ctx.remove_class("wifi-off")
        else:
            powered = self._wifi_is_on()
            
            if powered:
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
