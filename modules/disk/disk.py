"""Disk space widget with usage label, hover-activated popup, and mount notifications."""

from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label
from gi.repository import GLib  # type: ignore
from loguru import logger
from tabulate import tabulate

from modules.disk.disk_popup import DiskPopup
from services.system_service import DiskMountInfo, SystemService
from utils.helper_functions import truncate
from utils.notifications import NotificationHelper
from utils.popup_manager import popup_manager

CONVERSION_CONST = 1073741824
MONITORED_PATHS = ["/"]


class DiskWidget(Box):
    def __init__(self, window, **kwargs):
        super().__init__(orientation="h", name="disk")

        self.service = SystemService()
        self.notifier = NotificationHelper(app_name="SystemService")

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
            on_disk_mounted=self._on_disk_mounted,
            exclusivity="none",
        )

        self.content_event_box.connect("enter-notify-event", self._hover_trigger)
        self.content_event_box.connect("leave-notify-event", self._on_hover_leave)
        self.popup.connect("enter-notify-event", self._on_popup_enter)
        self.popup.connect("leave-notify-event", self._on_popup_leave)

        # Fetch once on startup, then react to service events on demand
        self.service.disk_inserted.connect(self._on_disk_inserted)
        self.update_label()

    # ── Disk insertion & mount notifications ────────────────────

    def _on_disk_inserted(self, *args) -> None:
        disk_info: DiskMountInfo | None = getattr(
            self.service, "_last_inserted_disk", None
        )
        if not disk_info:
            return

        if disk_info.mount_points:
            self.update_label()
            return

        self._send_mount_notification(disk_info)
        if self.popup.get_visible():
            self.popup.refresh_unmounted()

    def _on_disk_mounted(self) -> None:
        self.update_label()
        if self.popup.get_visible():
            self.popup.update(self._build_stats_markup())

    def _send_mount_notification(self, disk_info: DiskMountInfo) -> None:
        title = disk_info.label or disk_info.device_node or "External Storage"
        size_gb = (
            disk_info.size_bytes / CONVERSION_CONST if disk_info.size_bytes else 0.0
        )
        fs_part = f"{disk_info.filesystem_type} · " if disk_info.filesystem_type else ""
        size_part = f"{size_gb:.1f} GB" if size_gb > 0 else "Storage device"
        body = f"Detected {fs_part}{size_part} ({disk_info.device_node})"

        def _mount_disk() -> None:
            def _on_mounted(mount_path: str) -> None:
                logger.info(f"Mounted {disk_info.device_node} -> {mount_path}")
                self._on_disk_mounted()

            def _on_err(err: Exception) -> None:
                logger.error(f"Failed to mount {disk_info.object_path}: {err}")

            self.service.storage.mount(
                disk_info.object_path,
                on_success=_on_mounted,
                on_error=_on_err,
            )

        self.notifier.send(
            summary=title,
            body=body,
            icon="drive-harddisk",
            actions={"mount": _mount_disk},
            urgency=1,
            expire_timeout=10000,
        )

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
        self._hide_timeout_id = GLib.timeout_add(10000000000000, self._hide_popup)

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

    # ── Data ────────────────────────────────────────────────────

    def _build_stats_markup(self):
        rows = []

        for path in MONITORED_PATHS:
            rows.append(self._format_row(path, self.service.storage.get_usage(path)))

        for part in self.service.storage.list_partitions(all_partitions=False):
            if part.mountpoint in MONITORED_PATHS:
                continue
            try:
                rows.append(
                    self._format_row(
                        str(part.mountpoint),
                        self.service.storage.get_usage(part.mountpoint),
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
        print(f"mpunt: {truncate(mount, show_end=True, max_len=20)}")
        return [
            truncate(mount, show_end=True, max_len=20),
            f"{used_gb:.1f}/{total_gb:.1f} GB",
            f"{free_gb:.1f} GB",
            pct_str,
        ]

    def update_label(self) -> bool:
        usage = self.service.storage.get_usage(MONITORED_PATHS[0])
        pct = (usage.used / usage.total) * 100
        self.usage_label.set_label(f"{pct:.0f}%")

        if self.popup.get_visible():
            self.popup.update(self._build_stats_markup())

        return True
