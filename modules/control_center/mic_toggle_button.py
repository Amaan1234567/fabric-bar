import subprocess
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
from fabric.widgets.button import Button
from fabric.widgets.label import Label


class MicToggle(Button):
    """
    A single large button that toggles microphone mute.
    Shows microphone icon with Nerd Font icon.
    Background changes based on state via CSS classes.
    """

    def __init__(self):
        # Create the icon label
        self.icon_label = Label(name="mic-icon", label="󰍬")  # Nerd Font microphone icon

        super().__init__(
            name="mic-toggle",
            child=self.icon_label,
            on_clicked=self._toggle,
        )
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
        # Poll every 6s to keep in sync
        GLib.timeout_add_seconds(6, self._refresh)
        self.set_tooltip_text("toggle mic")

    @staticmethod
    def _mic_is_muted() -> bool:
        """Returns True if microphone is muted"""
        try:
            # Try pactl first (PulseAudio)
            result = subprocess.run(
                ["pactl", "get-source-mute", "@DEFAULT_SOURCE@"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                return "yes" in result.stdout.lower()

            # Fallback to amixer (ALSA)
            result = subprocess.run(
                ["amixer", "get", "Capture"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                # Check if [off] is in the output (indicates muted)
                return "[off]" in result.stdout.lower()

            return False  # Default to not muted if can't determine

        except Exception:
            return False

    def _refresh(self) -> bool:
        """Update CSS class and icon based on mic state"""
        muted = self._mic_is_muted()

        ctx = self.get_style_context()
        if muted:
            # Microphone is muted
            self.icon_label.set_label("󰍭")  # Muted mic icon
            ctx.add_class("mic-muted")
            ctx.remove_class("mic-active")
        else:
            # Microphone is active
            self.icon_label.set_label("󰍬")  # Active mic icon
            ctx.add_class("mic-active")
            ctx.remove_class("mic-muted")

        return True  # keep timeout alive

    def _toggle(self, _button):
        """Toggle microphone mute"""
        try:
            # Try pactl first (PulseAudio)
            result = subprocess.run(
                ["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "toggle"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )

            if result.returncode != 0:
                # Fallback to amixer (ALSA)
                subprocess.run(
                    ["amixer", "set", "Capture", "toggle"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )

        except Exception:
            pass

        # Refresh after short delay
        GLib.timeout_add(800, self._refresh)
