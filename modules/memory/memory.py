"""Memory widget with circular progress bar and hover-activated graph popup."""

from collections import deque

import psutil
from gi.repository import GLib  # type: ignore

from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay
from utils.popup_manager import popup_manager
from custom_widgets.animated_circular_progress_bar import AnimatedCircularProgressBar
from modules.memory.memory_popup import MemoryPopup

CONVERSION_CONST = 1073741824  # 1 Gigabyte = 1073741824 bytes


class Memory(Box):
    """Memory widget — icon + circular bar in the bar, graph popup on hover."""

    HISTORY_LENGTH = 10

    def __init__(self, window, **kwargs):
        super().__init__(orientation="h", name="memory")

        # ── icon + circular progress ────────────────────────────
        self.icon = Label("", name="memory-label")
        self.progress_bar = AnimatedCircularProgressBar(
            name="memory-progress-bar",
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
            name="memory-overlay",
        )

        # ── event box for hover events ──────────────────────────
        self.content_event_box = EventBox()
        self.content_event_box.add(self.overlay)
        self.add(self.content_event_box)

        # ── state ───────────────────────────────────────────────
        self._history: deque = deque(
            [0.0] * self.HISTORY_LENGTH, maxlen=self.HISTORY_LENGTH
        )

        self._hide_timeout_id = None
        self._show_delay_id = None

        # ── popup ───────────────────────────────────────────────
        self.popup = MemoryPopup(
            parent=window,
            pointing_to=self,
            exclusivity="none",
        )

        self.content_event_box.connect("enter-notify-event", self._hover_trigger)
        self.content_event_box.connect("leave-notify-event", self._on_hover_leave)
        self.popup.connect("enter-notify-event", self._on_popup_enter)
        self.popup.connect("leave-notify-event", self._on_popup_leave)

        self.popup.do_reposition("x")

        # ── polling ─────────────────────────────────────────────
        self._tick()
        GLib.timeout_add(500, self._tick)

    # ────────────────────────────────────────────────────────────
    #  Hover / show / hide
    # ────────────────────────────────────────────────────────────

    def _hover_trigger(self, *_):
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
        GLib.timeout_add(500, self.popup.set_visible, False)
        popup_manager.request_hide(self.popup, self)
        self._hide_timeout_id = None
        return False

    # ────────────────────────────────────────────────────────────
    #  Data
    # ────────────────────────────────────────────────────────────

    def get_memory_usage(self) -> float:
        return psutil.virtual_memory().percent

    def _build_stats_markup(self) -> str:
        ram = psutil.virtual_memory()
        swap = psutil.swap_memory()

        ram_color = (
            "#A3DC9A"
            if ram.percent <= 50
            else "#FCF67E" if ram.percent <= 80 else "#FF5454"
        )
        swap_color = (
            "#A3DC9A"
            if swap.percent <= 50
            else "#FCF67E" if swap.percent <= 80 else "#FF5454"
        )

        return "\n".join(
            [
                "<b>Memory</b>",
                (
                    f'RAM: <span foreground="{ram_color}">'
                    f"{ram.used / CONVERSION_CONST:.2f} / "
                    f"{ram.total / CONVERSION_CONST:.2f} GB"
                    f" ({ram.percent}%)</span>"
                ),
                (
                    f'SWAP: <span foreground="{swap_color}">'
                    f"{swap.used / CONVERSION_CONST:.2f} / "
                    f"{swap.total / CONVERSION_CONST:.2f} GB"
                    f" ({swap.percent}%)</span>"
                ),
                f"Available: {ram.available / CONVERSION_CONST:.2f} GB",
            ]
        )

    # ────────────────────────────────────────────────────────────
    #  Polling (every 500ms)
    # ────────────────────────────────────────────────────────────

    def _tick(self) -> bool:
        value = self.get_memory_usage()
        self._history.append(value)

        if abs(self.progress_bar.value - value) > 3:
            self.progress_bar.animate_value(value)
        self.progress_bar.set_value(value)

        if self.popup.get_visible():
            self.popup.update(self._history, self._build_stats_markup())

        return True
