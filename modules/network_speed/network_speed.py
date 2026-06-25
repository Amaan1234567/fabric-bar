"""Network speed widget with download/upload labels, graph popup, and top processes."""

import time
from collections import deque
from threading import Thread

import psutil
from gi.repository import GLib

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
        self.upload_icon = Label(name="upload-icon", label="")
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
        self._popup_visible = False

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
        # self.popup.do_reposition("x")

        Thread(target=self._get_network_speed, daemon=True).start()

    # ── Hover / show / hide ─────────────────────────────────────

    def _hover_trigger(self, *_):
        self._cancel_hide_timeout()
        self._show_delay_id = GLib.timeout_add(300, self._on_hover_enter)

    def _on_hover_enter(self, *_):
        self._cancel_hide_timeout()
        self._show_delay_id = None

        self._popup_visible = True
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
        self._popup_visible = False
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

    # ── Per-process markup via psutil.net_connections ────────────

    def _build_process_markup(self, total_dl_bytes, total_ul_bytes):
        """Build per-process breakdown using psutil.net_connections().

        Single batch call instead of scanning every /proc/<pid>/fd/.
        """
        conn_map = {}
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.pid and conn.status == "ESTABLISHED":
                    conn_map[conn.pid] = conn_map.get(conn.pid, 0) + 1
        except (psutil.AccessDenied, PermissionError):
            pass

        if not conn_map:
            return ""

        entries = []
        total_conns = 0
        for pid, count in conn_map.items():
            try:
                name = psutil.Process(pid).name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            entries.append({"name": name, "weight": count})
            total_conns += count

        if total_conns == 0:
            return ""

        entries.sort(key=lambda e: e["weight"], reverse=True)
        entries = entries[:5]

        lines = ["<b>Top Network</b>"]
        for e in entries:
            share = e["weight"] / total_conns
            dl_est = total_dl_bytes * share
            ul_est = total_ul_bytes * share

            dl_str = (
                f"{dl_est / 1_048_576:.2f} MB/s"
                if dl_est >= 1_048_576
                else f"{dl_est / 1024:.2f} KB/s"
            )
            ul_str = (
                f"{ul_est / 1_048_576:.2f} MB/s"
                if ul_est >= 1_048_576
                else f"{ul_est / 1024:.2f} KB/s"
            )

            conn_label = f"{e['weight']} conn{'s' if e['weight'] != 1 else ''}"
            lines.append(
                f"<tt>↓{dl_str} ↑{ul_str}</tt>  {e['name']}  <small>({conn_label})</small>"
            )

        return "\n".join(lines)

    # ── Network speed polling ───────────────────────────────────

    def _get_network_speed(self):
        initial_poll=True
        while True:
            initial = psutil.net_io_counters()
            if initial_poll:
                time.sleep(0.5)
                initial_poll = False
            else :
                time.sleep(2)
            final = psutil.net_io_counters()

            dl_kbs = (final.bytes_recv - initial.bytes_recv) / 1024
            ul_kbs = (final.bytes_sent - initial.bytes_sent) / 1024

            if dl_kbs < 1024:
                dl_label = f"{dl_kbs:.2f} KB/s"
            else:
                dl_label = f"{dl_kbs / 1024:.2f} MB/s"
            if ul_kbs < 1024:
                ul_label = f"{ul_kbs:.2f} KB/s"
            else:
                ul_label = f"{ul_kbs / 1024:.2f} MB/s"

            # Only scan per-process when popup is actually open
            proc_markup = ""
            if self._popup_visible:
                proc_markup = self._build_process_markup(
                    final.bytes_recv - initial.bytes_recv,
                    final.bytes_sent - initial.bytes_sent,
                )

            GLib.idle_add(
                self._apply_update, dl_kbs, ul_kbs, dl_label, ul_label, proc_markup
            )

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

        self._top_processes_markup = proc_markup

        if self.popup.get_visible():
            self._push_to_popup()
        return False