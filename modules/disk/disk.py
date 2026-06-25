"""Disk space widget with usage label and hover-activated popup."""

import shutil
import psutil
from gi.repository import GLib  # type: ignore

from tabulate import tabulate
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
        # self.popup.do_reposition("x")

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

        rows = []

        for path in MONITORED_PATHS:
            rows.append(self._format_row(path, shutil.disk_usage(path)))

        for part in psutil.disk_partitions(all=False):
            if part.mountpoint in MONITORED_PATHS:
                continue
            try:
                rows.append(
                    self._format_row(
                        part.mountpoint, shutil.disk_usage(part.mountpoint)
                    )
                )
            except PermissionError:
                pass

        if not rows:
            return ""

        table = tabulate(
            rows,
            headers=["Mount", "Used/Total", "Free", "%"],
            tablefmt="plain",
            stralign="left",
            numalign="left",
        )
        return f"<tt>{table}</tt>"

    def _format_row(self, mount, usage):
        used_gb = usage.used / CONVERSION_CONST
        total_gb = usage.total / CONVERSION_CONST
        free_gb = usage.free / CONVERSION_CONST
        pct = (usage.used / usage.total) * 100

        color = "#A3DC9A" if pct < 70 else "#FCF67E" if pct < 90 else "#FF5454"
        pct_str = f'<span foreground="{color}">{pct:.1f}%</span>'

        return [mount, f"{used_gb:.1f}/{total_gb:.1f} GB", f"{free_gb:.1f} GB", pct_str]

    def update_label(self) -> bool:
        usage = shutil.disk_usage(MONITORED_PATHS[0])
        pct = (usage.used / usage.total) * 100
        self.usage_label.set_label(f"{pct:.0f}%")

        if self.popup.get_visible():
            self.popup.update(self._build_stats_markup())

        return True
