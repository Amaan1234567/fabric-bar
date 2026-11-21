"""GPU widget with hover-activated graph popup."""

from collections import deque

from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label
from gi.repository import GLib

from custom_widgets.animated_scale import AnimatedScale
from modules.gpu.gpu_popup import GpuPopup
from services.system_service import SystemService
from utils.popup_manager import popup_manager


class GpuWidget(Box):
    """GPU stats widget — scales in the bar, graph popup on hover."""

    HISTORY_LENGTH = 30

    def __init__(self, window, **kwargs):
        super().__init__(name="gpu-stats", orientation="h", spacing=5)

        self.service = SystemService()

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

        # ── service subscription ────────────────────────────────
        self.service.gpu_updated.connect(self._on_gpu_updated)
        self.service.thermals_updated.connect(self._on_thermals_updated)
        if self.service.gpu.latest:
            self._on_gpu_updated()

    # ── Hover / show / hide ─────────────────────────────────────

    def _hover_trigger(self, *_):
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

    # ── Data & Service Updates ──────────────────────────────────

    def _on_gpu_updated(self, *_) -> None:
        devices_data = self.service.gpu.latest
        if not devices_data:
            return

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

    def _on_thermals_updated(self, *_) -> None:
        if self.popup.get_visible():
            self.popup.update(
                self._core_history,
                self._vram_history,
                self._build_stats_markup(),
            )

    def _build_stats_markup(self) -> str:
        if not self._latest_data:
            return "<b>GPU</b>"

        fan_reading = self.service.thermals.latest.get("fan_speed")
        fan_rpm = (
            getattr(fan_reading, "current", None)
            if fan_reading is not None
            else None
        )

        blocks = []
        for dev in self._latest_data:
            lines = [
                f"<u><b>{dev['name']} (GPU {dev['index']})</b></u>",
                f"Usage: {dev['gpu_util']:.0f}%",
                f"Memory: {dev['used_gb']:.2f} GB",
                f"Temperature: {dev['temp']}\u00b0C",
                f"Graphics Clock: {dev['gpu_clock']} MHz",
                f"Memory Clock: {dev['mem_clock']} MHz",
                f"Power Draw: {dev['power']} W",
            ]
            if fan_rpm is not None:
                lines.append(f"Fan Speed: {fan_rpm:.0f} RPM")
            blocks.append("\n".join(lines))

        return "\n\n".join(blocks).strip()