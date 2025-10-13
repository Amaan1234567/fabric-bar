"""contains the mic toggle widget"""

from loguru import logger

from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.audio.service import Audio


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
        self.audio = Audio()
        self.audio.connect("microphone_changed", self._refresh)
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

        self.set_tooltip_text("toggle mic")

    def _mic_is_muted(self) -> bool:
        """Returns True if microphone is muted"""

        return self.audio.microphone.muted

    def _refresh(self) -> bool:
        """Update CSS class and icon based on mic state"""
        logger.debug("refreshing mic toggle")

        muted = self._mic_is_muted()
        logger.debug(muted)
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
        self.audio.microphone.set_property("muted", not self._mic_is_muted())
