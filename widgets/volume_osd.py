"""Volume on-screen display (OSD) widget."""

from typing import Any

from fabric.widgets.box import Box
from fabric.widgets.label import Label

from fabric.audio.service import Audio
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.utils import remove_handler
from gi.repository import GLib  # type: ignore

from custom_widgets.animated_scale import AnimatedScale
from custom_widgets.HackedStackRevealer import HackedRevealer as Revealer

_ICONS = {
    "muted": "󰖁",
    "low": "󰖀",
    "medium": "󰕾",
    "high": "󰓃",
    "headphones": "󰋎",
    "bluetooth": "󰂯",
}


class VolumeOSD(Window):
    """Volume on-screen display (OSD) widget."""

    def __init__(self, **kwargs):
        super().__init__(
            layer="top",
            title="volume_osd",
            name="volume-osd-window",
            anchor="top right",
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
            orientation="vertical",
            name="volume-osd-scale",
            min_value=0,
            max_value=100,
            value=50,
            inverted=True,
            h_expand=True,
            v_expand=True,
            has_origin=True,
        )

        self.box = Box(
            orientation="v",
            spacing=10,
            children=[self.scale, self.icon],
            name="volume-osd-box",
        )

        self.revealer = Revealer(
            child=self.box,
            name="volume-osd-revealer",
            transition_type="slide-left",
            bezier_curve=(0.3, -0.06, 0, 1.02),
            duration=0.350,
        )

        self.add(self.revealer)
        self.audio.connect("notify::speaker", self._on_speaker_changed)
        self.hide()

    def _on_speaker_changed(self, *_: Any):
        """When the default sink changes, listen for its volume/mute changes."""
        speaker = self.audio.speaker
        if not speaker:
            return

        speaker.connect("notify::volume", self._update_ui)

    def _update_ui(self, *_: Any):
        """Refresh progress, icon, label, and tooltip."""
        self._show_popup()
        spk = self.audio.speaker
        if not spk:
            return

        vol: int = round(spk.volume)
        desc: str = (spk.description or "").lower()
        muted: bool = spk.muted

        self.scale.animate_value(vol)

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
        self._hide_popup()

    def _hide_popup(self):
        self.is_closing = True
        self.last_revealer_handler = GLib.timeout_add(
            3000, self.revealer.set_reveal_child, False
        )
        self.last_window_handler = GLib.timeout_add(3350, self.hide)

    def _show_popup(self):
        if self.is_closing:
            if self.last_revealer_handler:
                remove_handler(self.last_revealer_handler)
            if self.last_window_handler:
                remove_handler(self.last_window_handler)
            self.is_closing = False
        if self.is_visible():
            return
        self.show()
        self.revealer.set_reveal_child(True)
