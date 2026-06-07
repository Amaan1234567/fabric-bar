"""GPU widget with hover-activated graph popup."""

import subprocess
import threading
from collections import deque

from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label
from gi.repository import GLib

from custom_widgets.animated_scale import AnimatedScale
from utils.popup_manager import popup_manager
from modules.gpu.gpu_popup import GpuPopup

MAX_DEVICES_DISPLAYED = 3


class GpuWidget(Box):
    """GPU stats widget — scales in the bar, graph popup on hover."""

    HISTORY_LENGTH = 30

    def __init__(self, window, **kwargs):
        super().__init__(name="gpu-stats", orientation="h", spacing=5)

        # ── scales + icon (same as original) ────────────────────
        self.icon = Label(label="GPU", name="gpu-icon", h_align="start")

        self.usage_scale = AnimatedScale(
            name="gpu-usage-scale",
            orientation="horizontal",
            min_value=0,
            max_value=100,
            value=0,
            h_expand=True,
            v_expand=True,
        )
        self.memory_usage_scale = AnimatedScale(
            name="gpu-mem-usage-scale",
            orientation="horizontal",
            min_value=0,
            max_value=100,
            value=0,
            h_expand=True,
            v_expand=True,
        )

        self.scales_holder = Box(
            name="gpu-scales-container",
            orientation="v",
            children=[self.usage_scale, self.memory_usage_scale],
            spacing=1,
        )

        self.content_box = Box(
            orientation="h",
            spacing=5,
            children=[self.icon, self.scales_holder],
        )

        self.content_event_box = EventBox()
        self.content_event_box.add(self.content_box)
        self.add(self.content_event_box)

        # ── state ───────────────────────────────────────────────
        self._core_history: deque = deque(
            [0.0] * self.HISTORY_LENGTH, maxlen=self.HISTORY_LENGTH
        )
        self._vram_history: deque = deque(
            [0.0] * self.HISTORY_LENGTH, maxlen=self.HISTORY_LENGTH
        )

        self._latest_data: list = []
        self._hide_timeout_id = None
        self._show_delay_id = None

        # ── popup ───────────────────────────────────────────────
        self.popup = GpuPopup(
            parent=window,
            pointing_to=self,
            exclusivity="none",
        )

        self.content_event_box.connect("enter-notify-event", self._hover_trigger)
        self.content_event_box.connect("leave-notify-event", self._on_hover_leave)

        # scales and icon capture events before the EventBox —
        # connect them to the same handlers
        self.icon.connect("enter-notify-event", self._hover_trigger)
        self.icon.connect("leave-notify-event", self._on_hover_leave)
        self.usage_scale.connect("enter-notify-event", self._hover_trigger)
        self.usage_scale.connect("leave-notify-event", self._on_hover_leave)
        self.memory_usage_scale.connect("enter-notify-event", self._hover_trigger)
        self.memory_usage_scale.connect("leave-notify-event", self._on_hover_leave)

        self.popup.connect("enter-notify-event", self._on_popup_enter)
        self.popup.connect("leave-notify-event", self._on_popup_leave)
        self.popup.do_reposition("x")

        # ── polling (background thread, every 2s) ───────────────
        GLib.timeout_add(500, self._trigger_update)

    # ── Hover / show / hide ─────────────────────────────────────

    def _hover_trigger(self, *_):
        # cancel any pending hide immediately — moving between
        # children within the widget shouldn't close the popup
        self._cancel_hide_timeout()
        self._show_delay_id = GLib.timeout_add(300, self._on_hover_enter)

    def _on_hover_enter(self, *_):
        self._cancel_hide_timeout()
        self._show_delay_id = None
        self.popup.update(
            self._core_history,
            self._vram_history,
            self._build_stats_markup(),
        )
        # only show if not already visible — avoids flicker
        if not self.popup.get_visible():
            popup_manager.request_show(self.popup, self)
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
        GLib.timeout_add(450, self.popup.set_visible, False)
        popup_manager.request_hide(self.popup, self)
        self._hide_timeout_id = None
        return False

    # ── Data fetching ───────────────────────────────────────────

    def _trigger_update(self):
        threading.Thread(target=self._fetch_gpu_data, daemon=True).start()
        return True

    def _fetch_gpu_data(self):
        cmd = [
            "nvidia-smi",
            "--query-gpu=name,utilization.gpu,memory.used,memory.total,"
            "temperature.gpu,clocks.gr,clocks.mem,power.draw",
            "--format=csv,noheader,nounits",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split("\n")
            devices_data = []
            for index, line in enumerate(lines):
                if index >= MAX_DEVICES_DISPLAYED:
                    break
                parts = [p.strip() for p in line.split(",")]
                if len(parts) == 8:
                    used_mib = float(parts[2])
                    total_mib = float(parts[3])
                    devices_data.append(
                        {
                            "name": parts[0],
                            "gpu_util": float(parts[1]),
                            "used_gb": used_mib / 1024,
                            "vram_percent": (used_mib / total_mib) * 100,
                            "temp": parts[4],
                            "gpu_clock": parts[5],
                            "mem_clock": parts[6],
                            "power": parts[7],
                            "index": index,
                        }
                    )
            if devices_data:
                GLib.idle_add(self._apply_ui_updates, devices_data)
        except Exception:
            pass

    def _apply_ui_updates(self, devices_data):
        primary = devices_data[0]
        self._latest_data = devices_data

        # scales
        self.usage_scale.animate_value(primary["gpu_util"])
        self.usage_scale.set_value(primary["gpu_util"])
        self.memory_usage_scale.animate_value(primary["vram_percent"])
        self.memory_usage_scale.set_value(primary["vram_percent"])

        # history for graphs
        self._core_history.append(primary["gpu_util"])
        self._vram_history.append(primary["vram_percent"])

        # live-update popup while open
        if self.popup.get_visible():
            self.popup.update(
                self._core_history,
                self._vram_history,
                self._build_stats_markup(),
            )
        return False

    def _build_stats_markup(self) -> str:
        if not self._latest_data:
            return "<b>GPU</b>"

        markup = ""
        for dev in self._latest_data:
            markup += (
                f"<u><b>{dev['name']} (GPU {dev['index']})</b></u>\n"
                f"Usage: {dev['gpu_util']:.0f}%\n"
                f"Memory: {dev['used_gb']:.2f} GB\n"
                f"Temperature: {dev['temp']}\u00b0C\n"
                f"Graphics Clock: {dev['gpu_clock']} MHz\n"
                f"Memory Clock: {dev['mem_clock']} MHz\n"
                f"Power Draw: {dev['power']} W\n"
            )
            if dev != self._latest_data[-1]:
                markup += "\n"
        return markup.strip()
