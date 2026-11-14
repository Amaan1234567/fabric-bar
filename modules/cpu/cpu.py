"""Hold the CPU widget"""

import typing
from collections import deque

import psutil
from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay
from gi.repository import GLib  # type: ignore

from custom_widgets.animated_cirular_scale import AnimatedCircularScale
from modules.cpu.cpu_popup import CpuPopup
from utils.popup_manager import popup_manager


class Cpu(Box):
    """CPU widget — icon + circular bar in the bar, graph popup on hover."""

    HISTORY_LENGTH: typing.ClassVar = 10  # 60 seconds at 1 s polling
    CPU_DRIVERS: typing.ClassVar = [
        "k10temp",
        "coretemp",
        "cpu_thermal",
        "soc_thermal",
        "zenpower",
    ]

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

        # ── polling ─────────────────────────────────────────────────
        self._tick()
        GLib.timeout_add(1000, self._tick)

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
        GLib.timeout_add(250, self.popup.set_visible, False)
        popup_manager.request_hide(self.popup, self)
        self._hide_timeout_id = None
        return False

    # ────────────────────────────────────────────────────────────────
    #  Data
    # ────────────────────────────────────────────────────────────────

    def get_cpu_usage(self) -> float:
        """Get the current total CPU usage percentage safely."""
        try:
            return psutil.cpu_percent()
        except Exception:
            return 0.0

    def _get_details(self):
        """Safely fetch system metrics with granular fallback handlers."""
        # 1. Frequency
        try:
            cur_freq = psutil.cpu_freq()
        except Exception:
            cur_freq = None

        # 2. Per-core usage
        try:
            per_core_usage = psutil.cpu_percent(percpu=True)
        except Exception:
            per_core_usage = []

        # 3. Temperature with driver fallback lookup
        cpu_temp = None
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for driver in self.CPU_DRIVERS:
                    if temps.get(driver):
                        cpu_temp = temps[driver][0]
                        break
                # Fallback to the first available sensor if none of the known drivers matched
                if not cpu_temp:
                    first_key = next(iter(temps.keys()))
                    if temps[first_key]:
                        cpu_temp = temps[first_key][0]
        except Exception:
            cpu_temp = None

        # 4. Fan speed (handles systems without fans gracefully)
        cpu_fan_speed = None
        try:
            fans = psutil.sensors_fans()
            if fans:
                first_fan_key = next(iter(fans.keys()))
                if fans[first_fan_key]:
                    cpu_fan_speed = fans[first_fan_key][0]
        except Exception:
            cpu_fan_speed = None

        return cur_freq, per_core_usage, cpu_temp, cpu_fan_speed

    def _build_stats_markup(self) -> str:
        cur_freq, per_core_usage, cpu_temp, cpu_fan_speed = self._get_details()
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
        if cpu_temp and getattr(cpu_temp, "current", None):
            temp_val = cpu_temp.current
            temp_color = (
                "#A3DC9A"
                if temp_val <= 45
                else "#FCF67E"
                if temp_val <= 75
                else "#FF5454"
            )
            lines.append(
                f'Temp: <span foreground="{temp_color}">{temp_val}\u00b0C</span>'
            )

        # Fan speed line (omitted gracefully on fanless/unsupported systems)
        if cpu_fan_speed and getattr(cpu_fan_speed, "current", None):
            lines.append(f"Fan: {cpu_fan_speed.current} RPM")

        return "\n".join(lines)

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
