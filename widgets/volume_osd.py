from typing import Any
import fabric
from loguru import logger
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.revealer import Revealer
from custom_widgets.animated_scale import AnimatedScale
from fabric.audio.service import Audio
from fabric.utils import cooldown
from gi.repository import GLib


_ICONS = {
        "muted": "󰖁",
        "low": "󰖀",
        "medium": "󰕾",
        "high": "󰓃",
        "headphones": "󰋎",
        "bluetooth": "󰂯",
    }

class VolumeOSD(Window):
    def __init__(self, **kwargs):
        super().__init__(
            layer="overlay",
            name="volume-osd-window",
            anchor="bottom",
            margin="100 0 0 0",
            pass_through=True,
            exclusivity="none",
            all_visible=False,
            **kwargs
        )

        self.audio = Audio()
        self.audio.connect("notify::speaker", self._on_speaker_changed)

        self.icon = Label(name="osd-icon", label=_ICONS["medium"])
        self.scale = AnimatedScale(
            orientation="h",
            name="volume-osd-scale",
            min_value=0,
            max_value=100,
            value=0,
            h_expand=True,
            v_expand=True,
            has_origin=True,
            increments=[1, 5],
        )


        self.box = Box(
            orientation="h",
            spacing=10,
            children=[self.icon, self.scale],
            name="volume-osd-box",
        )

        self.add(self.box)
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
        self.show()

        spk = self.audio.speaker
        if not spk:
            return

        vol: int = round(spk.volume)
        desc: str = (spk.description or "").lower()
        muted: bool = spk.muted

        logger.debug(f"current speaker obj: {spk}")
        logger.debug(f"speaker desc: {desc}")
        logger.info(f"speaker-muted: {muted}")
        logger.debug(f"audio-scale value:{self.scale.value}")

        
        self.scale.animate_value(vol)
        #self.scale.set_value(vol)

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
        GLib.timeout_add_seconds(4, self.hide)

        
