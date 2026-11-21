"""Hold the CPU widget"""

import typing
from collections import deque

from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay
from gi.repository import GLib  # type: ignore

from custom_widgets.animated_cirular_scale import AnimatedCircularScale
from modules.cpu.cpu_popup import CpuPopup
from services.system_service import SystemService
from utils.popup_manager import popup_manager


class Cpu(Box):
    """CPU widget — icon + circular bar in the bar, graph popup on hover."""

    HISTORY_LENGTH: typing.ClassVar = 10  # 60 seconds at 1 s polling

    def __init__(self, window, **kwargs):
        super().__init__(orientation="h", name="cpu")

        self.service = SystemService()

        # ── icon + circular progress (unchanged layout) ─────────────
        self.icon = Label(
            label="",
            name="cpu-label",
            size=20,
            h_align="center",
            v_align="center",
        )

        self.progress_bar = AnimatedCircularScale(
            name="cpu-progress-bar",
            value=0,
            line_style="round",
            line_width=4,
            size=35,
            start_angle=105,
            end_angle=465,
            min_value=0.0,
            max_value=100.0,
        )

        self.overlay = Overlay(
            child=self.progress_bar,
            overlays=self.icon,
            name="cpu-overlay",
        )

        # ── event box for reliable hover events ─────────────────────
        self.content_event_box = EventBox()
        self.content_event_box.add(self.overlay)
        self.add(self.content_event_box)

        # ── state ───────────────────────────────────────────────────
        self._history: deque = deque(
            [0.0] * self.HISTORY_LENGTH, maxlen=self.HISTORY_LENGTH
        )

        self._hide_timeout_id = None
        self._show_delay_id = None

        # ── popup ───────────────────────────────────────────────────
        self.popup = CpuPopup(
            parent=window,
            pointing_to=self,
            exclusivity="none",
        )

        # hover on bar
        self.content_event_box.connect("enter-notify-event", self._hover_trigger)
        self.content_event_box.connect("leave-notify-event", self._on_hover_leave)
        # hover on popup itself
        self.popup.connect("enter-notify-event", self._on_popup_enter)
        self.popup.connect("leave-notify-event", self._on_popup_leave)

        # ── service subscription ────────────────────────────────────
        self.service.cpu_updated.connect(self._on_cpu_updated)
        self.service.thermals_updated.connect(self._on_thermals_updated)
        self._on_cpu_updated()

    # ────────────────────────────────────────────────────────────────
    #  Hover / show / hide
    # ────────────────────────────────────────────────────────────────

    def _hover_trigger(self, *_):
        """Enter on the bar — start a short delay before showing."""
        self._show_delay_id = GLib.timeout_add(300, self._on_hover_enter)

    def _on_hover_enter(self, *_):
        self._cancel_hide_timeout()
        self._show_delay_id = None

        self.popup.update(self._history, self._build_stats_markup())
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
        GLib.timeout_add(450, self.popup.set_visible, False)
        popup_manager.request_hide(self.popup, self)
        self._hide_timeout_id = None
        return False

    # ────────────────────────────────────────────────────────────────
    #  Data & Service Updates
    # ────────────────────────────────────────────────────────────────

    def _build_stats_markup(self) -> str:
        cpu_data = self.service.cpu.latest
        thermal_data = self.service.thermals.latest

        cur_freq = cpu_data.get("freq")
        per_core_usage = cpu_data.get("per_core") or []
        cpu_temp = thermal_data.get("cpu_temp")
        cpu_fan_speed = thermal_data.get("fan_speed")
        bar_chars = "▁▂▃▄▅▆▇█"

        lines = ["<b>CPU</b>"]

        # Frequency line
        if cur_freq and getattr(cur_freq, "current", None):
            freq_val = cur_freq.current / 1000
            freq_color = (
                "#A3DC9A"
                if freq_val <= 1.0
                else "#FCF67E"
                if freq_val < 3.5
                else "#FF5454"
            )
            lines.append(
                f'Freq: <span foreground="{freq_color}">{freq_val:.2f} GHz</span>'
            )

        # Core usage line
        if per_core_usage:
            cores = "".join(
                bar_chars[
                    min(int((c / 100) * (len(bar_chars) - 1)), len(bar_chars) - 1)
                ]
                for c in per_core_usage
            )
            lines.append(f"<tt>Core: {cores}</tt>")

        # Temperature line (omitted gracefully if sensor is missing)
        if cpu_temp and getattr(cpu_temp, "current", None) is not None:
            temp_val = cpu_temp.current
            temp_color = (
                "#A3DC9A"
                if temp_val <= 45
                else "#FCF67E"
                if temp_val <= 75
                else "#FF5454"
            )
            lines.append(
                f'Temp: <span foreground="{temp_color}">{temp_val:.1f}\u00b0C</span>'
            )

        # Fan speed line (omitted gracefully on fanless/unsupported systems)
        if cpu_fan_speed and getattr(cpu_fan_speed, "current", None) is not None:
            lines.append(f"Fan: {cpu_fan_speed.current:.0f} RPM")

        return "\n".join(lines)

    def _on_cpu_updated(self, *_) -> None:
        value = float(self.service.cpu.latest.get("usage", 0.0))
        self._history.append(value)

        # circular progress — only animate on jumps > 3 %
        if abs(self.progress_bar.value - value) > 3:
            self.progress_bar.animate_value(value)
        self.progress_bar.set_value(value)

        # live-update popup while open
        if self.popup.get_visible():
            self.popup.update(self._history, self._build_stats_markup())

    def _on_thermals_updated(self, *_) -> None:
        if self.popup.get_visible():
            self.popup.update(self._history, self._build_stats_markup())
