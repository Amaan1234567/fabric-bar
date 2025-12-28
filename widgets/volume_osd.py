from typing import Any

from loguru import logger
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from custom_widgets.popup_window import PopupWindow
from fabric.widgets.revealer import Revealer
from fabric.widgets.scale import ScaleMark
from custom_widgets.animated_scale import AnimatedScale
from fabric.audio.service import Audio
from fabric.utils import remove_handler
from gi.repository import GLib


_ICONS = {
    "muted": "󰖁",
    "low": "󰖀",
    "medium": "󰕾",
    "high": "󰓃",
    "headphones": "󰋎",
    "bluetooth": "󰂯",
}


class VolumeOSD(PopupWindow):
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            layer="top",
            title="volume_osd",
            name="volume-osd-window",
            anchor="bottom",
            margin="0 0 0 100",
            type="popup",
            pass_through=True,
            exclusivity="none",
            all_visible=False,
            **kwargs,
        )
        self.is_closing = False
        self.last_revealer_handler = None
        self.last_window_handler = None
        self.audio = Audio()
        self.audio.connect("notify::speaker", self._on_speaker_changed)

        self.icon = Label(name="osd-icon", label=_ICONS["medium"])
        self.scale = AnimatedScale(
            orientation="h",
            name="volume-osd-scale",
            marks=(ScaleMark(value=i) for i in range(1, 100, 10)),
            min_value=0,
            max_value=100,
            inverted=False,
            value=0,
            h_expand=True,
            v_expand=True,
            has_origin=True,
        )

        self.box = Box(
            orientation="h",
            spacing=10,
            children=[self.icon, self.scale],
            name="volume-osd-box",
        )

        self.revealer = Revealer(
            child=self.box,
            name="volume-osd-revealer",
            transition_type="slide-up",
            transition_duration=200,
        )

        self.add(self.revealer)
        self.audio.connect("notify::speaker", self._on_speaker_changed)
        self.hide()

        # Connect to volume change signal

    def _on_speaker_changed(self, *_: Any):
        """When the default sink changes, listen for its volume/mute changes."""
        speaker = self.audio.speaker
        if not speaker:
            return

        speaker.connect("changed", self._update_ui)
        self._update_ui()

    def _update_ui(self, *_: Any):
        """Refresh progress, icon, label, and tooltip."""
        self.show_popup()
        spk = self.audio.speaker
        if not spk:
            return

        vol: int = round(spk.volume)
        desc: str = (spk.description or "").lower()
        muted: bool = spk.muted

        logger.debug(f"current speaker obj: {spk}")
        logger.debug(f"speaker desc: {desc}")
        logger.info(f"speaker-muted: {muted}")
        logger.debug(f"speaker-volume: {vol}")
        logger.debug(f"audio-scale value:{self.scale.value}")

        self.scale.animate_value(vol)
        # GLib.timeout_add(10,self.scale.set_value,vol)

        if muted or vol == 0:
            icon = _ICONS["muted"]
        elif "headset" in spk.icon_name or "headphones" in desc:
            icon = _ICONS["headphones"]
        elif "bluetooth" in desc:
            icon = _ICONS["bluetooth"]
        else:
            if vol < 30:
                icon = _ICONS["low"]
            elif vol < 70:
                icon = _ICONS["medium"]
            else:
                icon = _ICONS["high"]

        self.icon.set_text(icon)
        self.hide_popup()

    def hide_popup(self):
        self.is_closing = True
        self.last_revealer_handler = GLib.timeout_add(
            3000, self.revealer.set_reveal_child, False
        )
        self.last_window_handler = GLib.timeout_add(3250, self.hide)

    def show_popup(self):
        if self.is_closing:
            if self.last_revealer_handler:
                remove_handler(self.last_revealer_handler)
            if self.last_window_handler:
                remove_handler(self.last_window_handler)
            self.is_closing = False
        self.show()
        self.revealer.set_reveal_child(True)
