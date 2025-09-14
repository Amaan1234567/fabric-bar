"""
Module that holds the AudioWidget class which shows the current volume and other details in tooltip
"""

from typing import Any
import subprocess
from loguru import logger
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.audio.service import Audio
from fabric.utils import cooldown
from gi.repository import GLib
from custom_widgets.animated_scale import AnimatedScale


class AudioWidget(Box):
    """A widget that displays and controls volume using Fabric's Audio service."""

    # Unicode / Nerd‑Font icons
    _ICONS = {
        "muted": "󰖁",
        "low": "󰖀",
        "medium": "󰕾",
        "high": "󰓃",
        "headphones": "󰋎",
        "bluetooth": "󰂯",
    }

    def __init__(self, step_size: int = 5, **kwargs: Any):
        super().__init__(name="audio-container", spacing=5, show_label=False, **kwargs)

        self.scale: AnimatedScale = AnimatedScale(
            name="audio-scale",
            orientation="horizontal",
            min_value=0,
            max_value=100,
            value=float(
                subprocess.getoutput(
                    "wpctl status | grep '\\*' | head -1 | sed -E 's/.*\\[vol: ([0-9.]+)\\].*/\\1/'"
                ).strip()
            )
            * 100,
            h_expand=True,
            v_expand=True,
            has_origin=True,
            increments=[1, 5],
        )
        self.scale.connect("change-value", self._on_scroll)

        self.icon = Label(name="audio-icon", label=self._ICONS["medium"])

        self.add(self.icon)
        self.add(self.scale)

        self.audio = Audio()

        self.step = step_size

        self.audio.connect("notify::speaker", self._on_speaker_changed)

        self._on_speaker_changed()
        self.scrolling = False

    # def initial_update(self):
    #     self.scale.value = round(spk.volume)
    def _on_speaker_changed(self, *_: Any):
        """When the default sink changes, listen for its volume/mute changes."""
        speaker = self.audio.speaker
        if not speaker:
            return

        speaker.connect("notify::volume", self._update_ui)
        speaker.connect("notify::is-muted", self._update_ui)
        self._update_ui()
    @cooldown(0.05)
    def _update_ui(self, *_: Any):
        """Refresh progress, icon, label, and tooltip."""

        if self.scrolling:
            return

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

        # if abs(self.scale.value - vol) > 5:
        self.scale.animate_value(vol)
        self.scale.set_value(vol)

        if muted or vol == 0:
            icon = self._ICONS["muted"]
        elif "headset" in spk.icon_name or "headphones" in desc:
            icon = self._ICONS["headphones"]
        elif "bluetooth" in desc:
            icon = self._ICONS["bluetooth"]
        else:
            if vol < 30:
                icon = self._ICONS["low"]
            elif vol < 70:
                icon = self._ICONS["medium"]
            else:
                icon = self._ICONS["high"]

        self.icon.set_text(icon)

        tip = (
            f"<b>Device:</b> {self.audio.speaker.description}\n"
            f"<b>Volume:</b> {vol}%\n"
            f"<b>Muted:</b> {'Yes' if muted else 'No'}"
        )
        self.set_tooltip_markup(tip)

    @cooldown(0.1)
    def _on_scroll(self, _, __, value: float):
        """Scroll on the ring to change volume."""
        self.scrolling = True

        logger.debug(f"audio scale value returned on value change: {value}")
        logger.debug(f"current change in volume: {abs(self.scale.value)}")
        # if abs(self.scale.value - value) > 5:
        self.scale.animate_value(value)
        self.scale.set_value(value)
        self.audio.speaker.volume = value
        self.scrolling = False
        GLib.timeout_add(100,self._update_ui)
