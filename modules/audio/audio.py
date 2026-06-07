"""Audio widget with per-application volume mixer popup."""

from typing import Any
from loguru import logger
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.eventbox import EventBox
from fabric.audio.service import Audio
from fabric.utils import cooldown
from gi.repository import GLib  # type: ignore

from utils.popup_manager import popup_manager
from custom_widgets.animated_scale import AnimatedScale
from modules.audio.audio_popup import AudioPopup


class AudioWidget(Box):
    """Master volume in the bar; per-app mixer popup on hover."""

    _ICONS = {
        "muted": "󰖁",
        "low": "󰖀",
        "medium": "󰕾",
        "high": "󰓃",
        "headphones": "󰋎",
        "bluetooth": "󰂯",
    }

    def __init__(self, window, **kwargs: Any):
        super().__init__(name="audio-container", **kwargs)

        # ── bar widgets ────────────────────────────────────────
        self.scale = AnimatedScale(
            name="audio-scale",
            orientation="horizontal",
            min_value=0,
            max_value=100,
            value=0,
            h_expand=True,
            v_expand=True,
            increments=[1, 5],
        )
        self.scale.connect("change-value", self._on_scale_change)

        self.icon = Label(name="audio-icon", label=self._ICONS["medium"])

        # wrap in EventBox for hover (same pattern as Cpu)
        self.content_event_box = EventBox()
        inner = Box(orientation="h", name="audio-inner", spacing=5)
        inner.add(self.icon)
        inner.add(self.scale)
        self.content_event_box.add(inner)
        self.add(self.content_event_box)

        # ── audio service ──────────────────────────────────────
        self.audio = Audio()
        self.audio.connect("notify::speaker", self._on_speaker_changed)

        # ── popup state ────────────────────────────────────────
        self._hide_timeout_id = None
        self._show_delay_id = None

        self.popup = AudioPopup(
            parent=window,
            pointing_to=self,
            audio_service=self.audio,
            exclusivity="none",
        )

        self.content_event_box.connect("enter-notify-event", self._hover_trigger)
        self.content_event_box.connect("leave-notify-event", self._on_hover_leave)
        self.popup.connect("enter-notify-event", self._on_popup_enter)
        self.popup.connect("leave-notify-event", self._on_popup_leave)
        self.popup.do_reposition("x")

        # ── tick ───────────────────────────────────────────────
        GLib.timeout_add(1000, self._tick)

    # ── speaker handling (unchanged) ─────────────────────────────

    def _on_speaker_changed(self, *_: Any):
        speaker = self.audio.speaker
        if not speaker:
            return
        speaker.connect("notify::volume", self._update_ui)
        self._update_ui()

    def _update_ui(self, *_: Any):
        spk = self.audio.speaker
        if not spk:
            return

        vol = round(spk.volume)
        desc = (spk.description or "").lower()
        muted = spk.muted

        self.scale.animate_value(vol)

        if muted or vol == 0:
            icon = self._ICONS["muted"]
        elif "headset" in spk.icon_name or "headphones" in desc:
            icon = self._ICONS["headphones"]
        elif "bluetooth" in desc:
            icon = self._ICONS["bluetooth"]
        elif vol < 30:
            icon = self._ICONS["low"]
        elif vol < 70:
            icon = self._ICONS["medium"]
        else:
            icon = self._ICONS["high"]
        self.icon.set_text(icon)

    @cooldown(0.1)
    def _on_scale_change(self, _, __, value: float):
        self.audio.speaker.volume = value

    # ── hover flow (mirrors Cpu exactly) ─────────────────────────

    def _hover_trigger(self, *_):
        self._show_delay_id = GLib.timeout_add(300, self._on_hover_enter)

    def _on_hover_enter(self, *_):
        self._cancel_hide_timeout()
        self._show_delay_id = None
        self.popup.refresh()  # ← populate BEFORE showing
        popup_manager.request_show(self.popup, self)
        return False

    def _on_hover_leave(self, *_):
        self._schedule_hide()
        if self._show_delay_id:
            GLib.source_remove(self._show_delay_id)
            self._show_delay_id = None

    def _on_popup_enter(self, *_):
        self._cancel_hide_timeout()

    def _on_popup_leave(self, *_):
        self._schedule_hide()

    def _schedule_hide(self):
        self._cancel_hide_timeout()
        self._hide_timeout_id = GLib.timeout_add(1000, self._hide_popup)

    def _cancel_hide_timeout(self):
        if self._hide_timeout_id:
            GLib.source_remove(self._hide_timeout_id)
            self._hide_timeout_id = None

    def _hide_popup(self):
        self.popup.overlay_revealer.set_reveal_child(False)
        GLib.timeout_add(250, self.popup.set_visible, False)
        popup_manager.request_hide(self.popup, self)
        self._hide_timeout_id = None
        return False

    # ── tick ──────────────────────────────────────────────────────

    def _tick(self) -> bool:
        if self.popup.get_visible():
            self.popup.refresh()
        return True
