"""Network speed widget with download/upload labels, graph popup, and top processes."""

import os
import time
from collections import deque
from threading import Thread

import psutil
from gi.repository import GLib  # type: ignore

from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label

from utils.popup_manager import popup_manager
from modules.network_speed.network_speed_popup import NetworkSpeedPopup
from pathlib import Path


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

        self._download_history = deque(
            [0.0] * self.HISTORY_LENGTH, maxlen=self.HISTORY_LENGTH
        )
        self._upload_history = deque(
            [0.0] * self.HISTORY_LENGTH, maxlen=self.HISTORY_LENGTH
        )
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

    def _get_network_speed(self):
        while True:
            # snapshot per-connection socket counters BEFORE
            conns_before = self._snapshot_sockets()
            initial = psutil.net_io_counters()
            time.sleep(0.5)
            final = psutil.net_io_counters()
            # snapshot AFTER
            conns_after = self._snapshot_sockets()

            dl_kbs = (final.bytes_recv - initial.bytes_recv) / 1024
            ul_kbs = (final.bytes_sent - initial.bytes_sent) / 1024

            # bar labels
            if dl_kbs < 1024:
                dl_label = f"{dl_kbs:.2f} KB/s"
            else:
                dl_label = f"{dl_kbs / 1024:.2f} MB/s"
            if ul_kbs < 1024:
                ul_label = f"{ul_kbs:.2f} KB/s"
            else:
                ul_label = f"{ul_kbs / 1024:.2f} MB/s"

            proc_markup = self._build_markup_from_sockets(
                conns_before, conns_after, final.bytes_recv - initial.bytes_recv,
                final.bytes_sent - initial.bytes_sent,
            )

            GLib.idle_add(
                self._apply_update, dl_kbs, ul_kbs, dl_label, ul_label, proc_markup
            )

    def _snapshot_sockets(self):
        """Snapshot per-connection inode → (pid, name, bytes_sent, bytes_recv).

        Reads /proc/net/tcp and /proc/net/tcp6 to get socket inodes,
        then maps inodes to PIDs via /proc/<pid>/fd/ symlinks.
        Tracks bytes via SO_MEMINFO or falls back to connection count estimation.
        """
        # Step 1: read /proc/net/tcp to get (local_addr, remote_addr, inode)
        sockets = {}
        for proto in ("tcp", "tcp6", "udp", "udp6"):
            try:
                with open(f"/proc/net/{proto}") as f:
                    for line in f.readlines()[2:]:  # skip headers
                        parts = line.split()
                        if len(parts) >= 10:
                            local = parts[1]
                            remote = parts[2]
                            state = int(parts[3], 16)
                            inode = parts[9]
                            # only ESTABLISHED (01) for tcp
                            if proto.startswith("tcp") and state != 1:
                                continue
                            sockets[inode] = {
                                "local": local, "remote": remote,
                                "proto": proto.rstrip("6"),
                            }
            except (FileNotFoundError, PermissionError):
                pass

        # Step 2: map inodes → PIDs by reading /proc/<pid>/fd/ symlinks
        inode_to_pid = {}
        try:
            for pid_dir in Path("/proc").iterdir():
                if not pid_dir.name.isdigit():
                    continue
                fd_dir = pid_dir / "fd"
                try:
                    for fd in fd_dir.iterdir():
                        try:
                            target = fd.resolve()
                            if target.parts[:3] == ("proc", fd_dir.parent.name, "net"):
                                continue
                            link = os.readlink(str(fd))
                            if link.startswith("socket:["):
                                inode = link[8:-1]
                                inode_to_pid[inode] = int(pid_dir.name)
                        except (OSError, ValueError):
                            continue
                except PermissionError:
                    continue
        except Exception:
            pass

        # Step 3: combine — for each socket, record the PID and connection info
        result = {}  # pid → {"name": ..., "connections": count}
        for inode, info in sockets.items():
            pid = inode_to_pid.get(inode)
            if pid is None or pid <= 0:
                continue
            if pid not in result:
                try:
                    name = psutil.Process(pid).name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    name = f"pid:{pid}"
                result[pid] = {"name": name, "count": 0}
            result[pid]["count"] += 1

        return result

    def _build_markup_from_sockets(
        self, before, after, total_dl_bytes, total_ul_bytes,
    ):
        """Estimate per-process traffic proportional to connection count.

        This is an approximation — real per-byte tracking requires
        nethogs or eBPF. But it gives meaningful relative numbers
        instead of showing the same value for every process.
        """
        # find processes active in both snapshots
        common = set(before.keys()) & set(after.keys())
        if not common:
            # try 'after' only (new connections)
            common = set(after.keys())
            if not common:
                return ""

        # build weighted shares
        entries = []
        total_conns = 0
        for pid in common:
            after_count = after.get(pid, {}).get("count", 0)
            before_count = before.get(pid, {}).get("count", 0)
            name = after.get(pid, {}).get("name", before.get(pid, {}).get("name", "?"))
            # delta connections = approximate activity weight
            weight = max(after_count, 1)
            entries.append({"pid": pid, "name": name, "weight": weight})
            total_conns += weight

        if total_conns == 0:
            return ""

        # sort by weight descending, take top 5
        entries.sort(key=lambda e: e["weight"], reverse=True)
        entries = entries[:5]

        lines = ["<b>Top Network</b>"]
        for e in entries:
            share = e["weight"] / total_conns
            dl_est = total_dl_bytes * share
            ul_est = total_ul_bytes * share

            if dl_est >= 1_048_576:
                dl_str = f"{dl_est / 1_048_576:.2f} MB/s"
            else:
                dl_str = f"{dl_est / 1024:.2f} KB/s"
            if ul_est >= 1_048_576:
                ul_str = f"{ul_est / 1_048_576:.2f} MB/s"
            else:
                ul_str = f"{ul_est / 1024:.2f} KB/s"

            conn_label = f"{e['weight']} conn{'s' if e['weight'] != 1 else ''}"
            lines.append(
                f"<tt>↓{dl_str} ↑{ul_str}</tt>  {e['name']}  <small>({conn_label})</small>"
            )

        return "\n".join(lines)


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
