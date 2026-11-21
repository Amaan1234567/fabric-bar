"""Network speed widget with download/upload labels, graph popup, and top processes."""

from collections import deque

from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label
from gi.repository import GLib  # type:ignore

from modules.network_speed.network_speed_popup import NetworkSpeedPopup
from services.system_service import SystemService
from utils.popup_manager import popup_manager


class NetworkSpeed(Box):
    """Network speed widget — download/upload labels in the bar, graph popup on hover."""

    HISTORY_LENGTH = 30

    def __init__(self, window, **kwargs):
        super().__init__(orientation="h", name="network-speed", spacing=5)

        self.service = SystemService()

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

        # ── service subscription ────────────────────────────────
        self.service.network_updated.connect(self._on_network_updated)

    # ── Hover / show / hide ─────────────────────────────────────

    def _hover_trigger(self, *_):
        self._cancel_hide_timeout()
        self._show_delay_id = GLib.timeout_add(250, self._on_hover_enter)

    def _on_hover_enter(self, *_):
        self._cancel_hide_timeout()
        self._show_delay_id = None

        self.service.network.collect_processes = True
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
        self.service.network.collect_processes = False
        self.popup.overlay_revealer.set_reveal_child(False)
        GLib.timeout_add(450, self.popup.set_visible, False)
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

    # ── Per-process markup formatting ───────────────────────────

    @staticmethod
    def _format_process_markup(top_processes: list[dict]) -> str:
        if not top_processes:
            return ""

        lines = ["<b>Top Network</b>"]
        for entry in top_processes:
            dl_est = entry["dl_est"]
            ul_est = entry["ul_est"]
            count = entry["count"]

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
            conn_label = f"{count} conn{'s' if count != 1 else ''}"
            lines.append(
                f"<tt>↓{dl_str} ↑{ul_str}</tt>  {entry['name']}  <small>({conn_label})</small>"
            )

        return "\n".join(lines)

    # ── Service network update handler ──────────────────────────

    def _on_network_updated(self, *_) -> None:
        payload = self.service.network.latest
        dl_kbs = float(payload.get("dl_kbs", 0.0))
        ul_kbs = float(payload.get("ul_kbs", 0.0))
        top_procs = payload.get("top_processes") or []

        dl_label = (
            f"{dl_kbs:.2f} KB/s" if dl_kbs < 1024 else f"{dl_kbs / 1024:.2f} MB/s"
        )
        ul_label = (
            f"{ul_kbs:.2f} KB/s" if ul_kbs < 1024 else f"{ul_kbs / 1024:.2f} MB/s"
        )

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

        self._top_processes_markup = self._format_process_markup(top_procs)

        if self.popup.get_visible():
            self._push_to_popup()
