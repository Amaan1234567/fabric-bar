"""Disk stats popup showing partition usage and unmounted drives with mount actions."""

from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from loguru import logger

from custom_widgets.HackedStackRevealer import HackedRevealer
from custom_widgets.popup_window import PopupWindow
from services.system_service import DiskMountInfo, SystemService
from utils.helper_functions import truncate

CONVERSION_CONST = 1073741824


class DiskPopup(PopupWindow):
    """disk popup"""

    def __init__(self, parent, pointing_to, on_disk_mounted=None, **kwargs):
        super().__init__(
            parent=parent,
            pointing_to=pointing_to,
            layer="top",
            name="disk-popup-window",
            type="popup",
            margin="15px 0 0 0px",
            anchor="top left",
            title="fabric-disk-popup",
            visible=False,
            v_expand=False,
            h_expand=False,
            **kwargs,
        )

        self.service = SystemService()
        self.on_disk_mounted = on_disk_mounted

        self._content = Box(
            orientation="v",
            name="disk-popup-content",
            spacing=8,
            h_expand=True,
            v_expand=True,
        )

        self.stats_label = Label(
            name="disk-stats-label",
            use_markup=True,
            h_align="start",
        )

        self.unmounted_box = Box(
            orientation="v",
            name="disk-unmounted-box",
            spacing=4,
            h_expand=True,
        )

        self._content.add(self.stats_label)
        self._content.add(self.unmounted_box)

        self.overlay_revealer = HackedRevealer(
            bezier_curve=(0.3, -0.06, 0, 1.02),
            duration=0.450,
            name="disk-revealer",
            child=self._content,
        )

        self.add(self.overlay_revealer)

    def refresh_unmounted(self) -> None:
        """Fetch unmounted UDisks2 filesystems on demand and rebuild mount rows."""
        for child in list(self.unmounted_box.get_children()):
            self.unmounted_box.remove(child)

        unmounted = self.service.storage.list_unmounted_filesystems()
        if not unmounted:
            self.unmounted_box.hide()
            return

        self.unmounted_box.show()
        header = Label(
            label="Unmounted Drives",
            name="disk-unmounted-header",
            h_align="start",
        )
        self.unmounted_box.add(header)

        for disk in unmounted:
            self.unmounted_box.add(self._build_disk_row(disk))

        self.unmounted_box.show_all()

    def _build_disk_row(self, disk: DiskMountInfo) -> Box:
        name = truncate(
            disk.label or disk.device_node or disk.object_path,
            show_end=True,
            max_len=40,
        )
        size_gb = disk.size_bytes / CONVERSION_CONST if disk.size_bytes else 0.0
        size_str = f" ({size_gb:.1f} GB)" if size_gb > 0 else ""
        fs_str = f" [{disk.filesystem_type}]" if disk.filesystem_type else ""

        info_label = Label(
            label=f"{name}{size_str}{fs_str}",
            name="disk-unmounted-label",
            h_align="start",
            h_expand=True,
        )

        mount_btn = Button(
            label="Mount",
            name="disk-mount-button",
        )
        mount_btn.connect("clicked", lambda _btn, d=disk: self._on_mount_clicked(d))

        return Box(
            orientation="h",
            name="disk-unmounted-row",
            spacing=8,
            children=[info_label, mount_btn],
        )

    def _on_mount_clicked(self, disk: DiskMountInfo) -> None:
        def _on_mounted(mount_path: str) -> None:
            logger.info(f"Mounted {disk.device_node} -> {mount_path}")
            self.refresh_unmounted()
            if self.on_disk_mounted:
                self.on_disk_mounted()

        def _on_err(err: Exception) -> None:
            logger.error(f"Failed to mount {disk.object_path}: {err}")

        self.service.storage.mount(
            disk.object_path,
            on_success=_on_mounted,
            on_error=_on_err,
        )

    def update(self, stats_markup):
        """updates info on popup"""
        self.stats_label.set_markup(stats_markup)
        self.refresh_unmounted()
