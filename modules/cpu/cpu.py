"""CPU widget with circular progress bar and hover-activated graph popup."""

from collections import deque

import psutil

from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay
from gi.repository import GLib  # type: ignore

from custom_widgets.animated_circular_progress_bar import AnimatedCircularProgressBar
from modules.cpu.cpu_popup import CpuPopup


class Cpu(Box):
    """CPU widget — icon + circular bar in the bar, graph popup on hover."""

    HISTORY_LENGTH = 10  # 60 seconds at 1 s polling

    def __init__(self, window, **kwargs):
        super().__init__(orientation="h", name="cpu")

        # ── icon + circular progress (unchanged layout) ─────────────
        self.icon = Label(
            label="",
            name="cpu-label",
            size=20,
            h_align="center",
            v_align="center",
        )

        self.progress_bar = AnimatedCircularProgressBar(
            name="cpu-progress-bar",
            value=0,
            line_style="round",
            line_width=4,
            size=35,
            start_angle=140,
            end_angle=395,
            invert=True,
            min_value=0.0,
            max_value=100.0,
        )

        self.overlay = Overlay(
            child=self.progress_bar,
            overlays=self.icon,
            name="cpu-overlay",
        )

        # ── event box for reliable hover events (same pattern as Mpris) ──
        self.content_event_box = EventBox()
        self.content_event_box.add(self.overlay)
        self.add(self.content_event_box)

        # ── state ───────────────────────────────────────────────────
        self._history: deque = deque(maxlen=self.HISTORY_LENGTH)
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
        # hover on popup itself (pointer moved from bar into popup)
        self.popup.connect("enter-notify-event", self._on_popup_enter)
        self.popup.connect("leave-notify-event", self._on_popup_leave)

        self.popup.do_reposition("x")

        # ── polling ─────────────────────────────────────────────────
        self._tick()
        GLib.timeout_add(500, self._tick)

    # ────────────────────────────────────────────────────────────────
    #  Hover / show / hide  (mirrors the Mpris pattern)
    # ────────────────────────────────────────────────────────────────

    def _hover_trigger(self, *_):
        """Enter on the bar — start a short delay before showing."""
        self._show_delay_id = GLib.timeout_add(300, self._on_hover_enter)

    def _on_hover_enter(self, *_):
        self._cancel_hide_timeout()
        self._show_delay_id = None

        self.popup.update(self._history, self._build_stats_markup())
        self.popup.set_visible(True)
        self.popup.overlay_revealer.set_reveal_child(True)
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
        GLib.timeout_add(500, self.popup.set_visible, False)
        self._hide_timeout_id = None
        return False

    # ────────────────────────────────────────────────────────────────
    #  Data
    # ────────────────────────────────────────────────────────────────

    def get_cpu_usage(self) -> float:
        """Get the current total CPU usage percentage."""
        return psutil.cpu_percent()

    def _get_details(self):
        try:
            return (
                psutil.cpu_freq(),
                psutil.cpu_percent(percpu=True),
                psutil.sensors_temperatures()["coretemp"][0],
                psutil.sensors_fans()["asus"][0],
            )
        except (KeyError, IndexError):
            return None

    def _build_stats_markup(self) -> str:
        details = self._get_details()
        if details is None:
            return "<b>CPU</b>"

        cur_freq, per_core_usage, cpu_temp, cpu_fan_speed = details
        bar_chars = "▁▂▃▄▅▆▇█"

        cores = "".join(
            bar_chars[min(int((c / 100) * (len(bar_chars) - 1)), len(bar_chars) - 1)]
            for c in per_core_usage
        )

        freq_color = (
            "#A3DC9A"
            if cur_freq.current <= 1000
            else "#FCF67E"
            if cur_freq.current < 3500
            else "#FF5454"
        )
        temp_color = (
            "#A3DC9A"
            if cpu_temp.current <= 45
            else "#FCF67E"
            if cpu_temp.current <= 75
            else "#FF5454"
        )

        return "\n".join(
            [
                "<b>CPU</b>",
                (
                    f'Freq: <span foreground="{freq_color}">'
                    f"{cur_freq.current / 1000:.2f} GHz</span>"
                ),
                f"<tt>Core: {cores}</tt>",
                (
                    f'Temp: <span foreground="{temp_color}">'
                    f"{cpu_temp.current}\u00b0C</span>"
                ),
                f"Fan: {cpu_fan_speed.current} RPM",
            ]
        )

    # ────────────────────────────────────────────────────────────────
    #  Polling (every 1 s)
    # ────────────────────────────────────────────────────────────────

    def _tick(self) -> bool:
        value = self.get_cpu_usage()
        self._history.append(value)

        # circular progress — only animate on jumps > 3 %
        if abs(self.progress_bar.value - value) > 3:
            self.progress_bar.animate_value(value)
        self.progress_bar.set_value(value)

        # live-update popup while open
        if self.popup.get_visible():
            self.popup.update(self._history, self._build_stats_markup())

        return True
