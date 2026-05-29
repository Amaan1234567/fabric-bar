"""Network speed widget with download/upload labels, graph popup, and top processes."""

import os
import time
from collections import deque
from threading import Thread

import psutil
from loguru import logger
from gi.repository import GLib  # type: ignore

from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label

from utils.popup_manager import popup_manager
from modules.network_speed.network_speed_popup import NetworkSpeedPopup


class NetworkSpeed(Box):
    HISTORY_LENGTH = 30

    def __init__(self, window, **kwargs):
        super().__init__(orientation="h", name="network-speed", spacing=5)

        self.download_icon = Label(name="download-icon", label="")
        self.download_speed = Label(name="download-speed", label="")
        self.upload_icon = Label(name="upload-icon", label="")
        self.upload_speed = Label(name="upload-speed", label="")

        self.content_box = Box(
            orientation="h",
            spacing=5,
            children=[
                self.download_icon,
                self.download_speed,
                self.upload_icon,
                self.upload_speed,
            ],
        )

        self.content_event_box = EventBox()
        self.content_event_box.add(self.content_box)
        self.add(self.content_event_box)

        self._download_history = deque([0.0] * self.HISTORY_LENGTH, maxlen=self.HISTORY_LENGTH)
        self._upload_history = deque([0.0] * self.HISTORY_LENGTH, maxlen=self.HISTORY_LENGTH)
        self._max_download = 1.0
        self._max_upload = 1.0
        self._hide_timeout_id = None
        self._show_delay_id = None
        self._top_processes_markup = ""

        # ── popup ───────────────────────────────────────────────
        self.popup = NetworkSpeedPopup(
            parent=window,
            pointing_to=self,
            exclusivity="none",
        )

        self.content_event_box.connect("enter-notify-event", self._hover_trigger)
        self.content_event_box.connect("leave-notify-event", self._on_hover_leave)
        self.popup.connect("enter-notify-event", self._on_popup_enter)
        self.popup.connect("leave-notify-event", self._on_popup_leave)
        self.popup.do_reposition("x")

        Thread(target=self._get_network_speed, daemon=True).start()

    # ── Hover / show / hide ─────────────────────────────────────

    def _hover_trigger(self, *_):
        self._cancel_hide_timeout()
        self._show_delay_id = GLib.timeout_add(300, self._on_hover_enter)

    def _on_hover_enter(self, *_):
        self._cancel_hide_timeout()
        self._show_delay_id = None

        self._push_to_popup()
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

    # ── Push to popup (graph always in MB/s) ────────────────────

    def _push_to_popup(self):
        dl_mb = [v / 1024 for v in self._download_history]
        ul_mb = [v / 1024 for v in self._upload_history]
        dl_max = max(self._max_download / 1024, 0.1)
        ul_max = max(self._max_upload / 1024, 0.1)
        self.popup.update(dl_mb, ul_mb, dl_max, ul_max, self._top_processes_markup)

    # ── Top network processes via /proc ─────────────────────────

    def _read_proc_net_bytes(self, pid):
        """Read cumulative TX/RX bytes for a process from /proc/<pid>/net/dev."""
        try:
            with open(f"/proc/{pid}/net/dev", "r") as f:
                lines = f.readlines()[2:]  # skip header
            rx_total = 0
            tx_total = 0
            for line in lines:
                parts = line.split()
                if len(parts) >= 10:
                    rx_total += int(parts[1])
                    tx_total += int(parts[9])
            return rx_total, tx_total
        except (FileNotFoundError, PermissionError, ValueError):
            return None, None

    def _snapshot_active_processes(self):
        """Get PIDs with ESTABLISHED connections and their current /proc byte counts."""
        snapshot = {}
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.pid and conn.pid > 0 and conn.status == 'ESTABLISHED':
                    if conn.pid in snapshot:
                        continue
                    try:
                        name = psutil.Process(conn.pid).name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                    rx, tx = self._read_proc_net_bytes(conn.pid)
                    if rx is not None:
                        snapshot[conn.pid] = {"name": name, "rx": rx, "tx": tx}
        except (psutil.AccessDenied, PermissionError):
            pass
        return snapshot

    def _build_processes_markup(self, before, after):
        """Compare two snapshots, show top 5 by total traffic with per-process speeds."""
        common = set(before.keys()) & set(after.keys())
        if not common:
            return ""

        deltas = []
        for pid in common:
            dl = after[pid]["rx"] - before[pid]["rx"]
            ul = after[pid]["tx"] - before[pid]["tx"]
            if dl < 0:
                dl = 0
            if ul < 0:
                ul = 0
            if dl == 0 and ul == 0:
                continue
            deltas.append({"name": after[pid]["name"], "dl": dl, "ul": ul})

        deltas.sort(key=lambda x: x["dl"] + x["ul"], reverse=True)
        deltas = deltas[:5]

        if not deltas:
            return ""

        lines = ["<b>Top Network</b>"]
        for d in deltas:
            dl_str = (f"{d['dl'] / 1_048_576:.1f} MB/s" if d["dl"] >= 1_048_576
                      else f"{d['dl'] / 1024:.0f} KB/s")
            ul_str = (f"{d['ul'] / 1_048_576:.1f} MB/s" if d["ul"] >= 1_048_576
                      else f"{d['ul'] / 1024:.0f} KB/s")
            lines.append(f"<tt>↓{dl_str} ↑{ul_str}</tt>  {d['name']}")

        return "\n".join(lines)

    # ── Data (background thread — runs every second) ────────────

    def _get_network_speed(self):
        while True:
            # snapshot processes BEFORE
            procs_before = self._snapshot_active_processes()
            initial = psutil.net_io_counters()
            time.sleep(1)
            final = psutil.net_io_counters()
            # snapshot processes AFTER
            procs_after = self._snapshot_active_processes()

            dl_kbs = (final.bytes_recv - initial.bytes_recv) / 1024
            ul_kbs = (final.bytes_sent - initial.bytes_sent) / 1024

            # bar labels: smart switching
            if dl_kbs < 1024:
                dl_label = f"{dl_kbs:.2f} KB/s"
            else:
                dl_label = f"{dl_kbs / 1024:.2f} MB/s"
            if ul_kbs < 1024:
                ul_label = f"{ul_kbs:.2f} KB/s"
            else:
                ul_label = f"{ul_kbs / 1024:.2f} MB/s"

            # build per-process markup from the before/after diff
            proc_markup = self._build_processes_markup(procs_before, procs_after)

            GLib.idle_add(self._apply_update, dl_kbs, ul_kbs, dl_label, ul_label, proc_markup)

            logger.debug(f"download speed: {dl_label}")
            logger.debug(f"upload speed: {ul_label}")

    def _apply_update(self, dl_kbs, ul_kbs, dl_label, ul_label, proc_markup):
        self.download_speed.set_label(dl_label)
        self.upload_speed.set_label(ul_label)

        self._download_history.append(dl_kbs)
        self._upload_history.append(ul_kbs)

        if dl_kbs > self._max_download:
            self._max_download = dl_kbs
        else:
            self._max_download = max(self._max_download * 0.995, 1.0)

        if ul_kbs > self._max_upload:
            self._max_upload = ul_kbs
        else:
            self._max_upload = max(self._max_upload * 0.995, 1.0)

        # always store the markup — popup reads it when visible
        self._top_processes_markup = proc_markup

        # always push to popup if visible — this is what updates the process list
        if self.popup.get_visible():
            self._push_to_popup()
        return False
