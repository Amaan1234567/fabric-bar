"""Disk space widget with usage label and hover-activated popup."""

import shutil
import psutil
from gi.repository import GLib  # type: ignore

from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label

from utils.popup_manager import popup_manager
from .disk_popup import DiskPopup

CONVERSION_CONST = 1073741824
MONITORED_PATHS = ["/"]


class DiskWidget(Box):

    def __init__(self, window, **kwargs):
        super().__init__(orientation="h", name="disk")

        self.icon = Label(label="󰋊", name="disk-label")
        self.usage_label = Label(name="disk-usage-label", label="0%")

        self.content_box = Box(
            orientation="h",
            spacing=4,
            children=[self.icon, self.usage_label],
        )

        self.content_event_box = EventBox()
        self.content_event_box.add(self.content_box)
        self.add(self.content_event_box)

        self._hide_timeout_id = None
        self._show_delay_id = None

        # ── popup ───────────────────────────────────────────────
        self.popup = DiskPopup(
            parent=window,
            pointing_to=self,
            exclusivity="none",
        )

        self.content_event_box.connect("enter-notify-event", self._hover_trigger)
        self.content_event_box.connect("leave-notify-event", self._on_hover_leave)
        self.popup.connect("enter-notify-event", self._on_popup_enter)
        self.popup.connect("leave-notify-event", self._on_popup_leave)
        self.popup.do_reposition("x")

        self.update_label()
        GLib.timeout_add(10000, self.update_label)

    # ── Hover / show / hide ─────────────────────────────────────

    def _hover_trigger(self, *_):
        self._cancel_hide_timeout()
        self._show_delay_id = GLib.timeout_add(300, self._on_hover_enter)

    def _on_hover_enter(self, *_):
        self._cancel_hide_timeout()
        self._show_delay_id = None

        self.popup.update(self._build_stats_markup())
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
        GLib.timeout_add(250, self.popup.set_visible, False)
        popup_manager.request_hide(self.popup, self)
        self._hide_timeout_id = None
        return False

    # ── Data ────────────────────────────────────────────────────

    def _build_stats_markup(self):
        """Build aligned columns: mount | used/total | free | pct"""
        lines = []

        # find longest mount name for alignment
        all_mounts = list(MONITORED_PATHS)
        for part in psutil.disk_partitions(all=False):
            if part.mountpoint not in all_mounts:
                all_mounts.append(part.mountpoint)

        max_mount_len = max(len(m) for m in all_mounts) if all_mounts else 1

        # header
        lines.append(
            f"<tt><b>{'Mount':<{max_mount_len}}  {'Used':>10}  {'Free':>8}  {'%':>5}</b></tt>"
        )

        # monitored paths first
        for path in MONITORED_PATHS:
            lines.append(self._format_partition(path, shutil.disk_usage(path), max_mount_len))

        # other partitions
        for part in psutil.disk_partitions(all=False):
            if part.mountpoint in MONITORED_PATHS:
                continue
            try:
                usage = shutil.disk_usage(part.mountpoint)
                lines.append(self._format_partition(part.mountpoint, usage, max_mount_len))
            except PermissionError:
                pass

        return "\n".join(lines)

    def _format_partition(self, mount, usage, max_mount_len):
        used_gb = usage.used / CONVERSION_CONST
        total_gb = usage.total / CONVERSION_CONST
        free_gb = usage.free / CONVERSION_CONST
        pct = (usage.used / usage.total) * 100

        color = "#A3DC9A" if pct < 70 else "#FCF67E" if pct < 90 else "#FF5454"

        return (
            f"<tt>{mount:<{max_mount_len}}  "
            f"{used_gb:>5.1f}/{total_gb:<4.1f} GB  "
            f"{free_gb:>5.1f} GB  "
            f'<span foreground="{color}">{pct:>4.1f}%</span></tt>'
        )

    def update_label(self) -> bool:
        usage = shutil.disk_usage(MONITORED_PATHS[0])
        pct = (usage.used / usage.total) * 100
        self.usage_label.set_label(f"{pct:.0f}%")

        if self.popup.get_visible():
            self.popup.update(self._build_stats_markup())

        return True
