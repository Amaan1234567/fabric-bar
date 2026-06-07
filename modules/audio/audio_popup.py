"""Audio mixer popup with per-application volume control."""

from loguru import logger
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.eventbox import EventBox
from fabric.utils import cooldown

from custom_widgets.popup_window import PopupWindow
from custom_widgets.animated_scale import AnimatedScale
from custom_widgets.HackedStackRevealer import HackedRevealer


_APP_ICONS = {
    "firefox": "󰈹",
    "brave": "󰈹",
    "chrome": "󰈹",
    "chromium": "󰈹",
    "spotify": "󰓇",
    "discord": "",
    "vlc": "󰕼",
    "mpv": "󰎈",
    "steam": "󰓓",
    "obs": "",
    "telegram": "",
    "signal": "",
    "thunderbird": "󰇮",
}


def _icon_for(stream):
    """Best-effort Nerd Font icon from stream name/app id."""
    n = (stream.name or stream.application_id or "").lower()
    for key, icon in _APP_ICONS.items():
        if key in n:
            return icon
    return "󰎆"


# ────────────────────────────────────────────────────────────────────
#  Single per-app row
# ────────────────────────────────────────────────────────────────────

class AppRow(Box):
    """One row: icon · name · volume scale · vol% · mute toggle."""

    def __init__(self, stream, **kwargs):
        super().__init__(
            orientation="h",
            name="audio-app-row",
            spacing=8,
            **kwargs,
        )
        self._stream = stream
        self._updating = False

        # icon
        self.icon = Label(
            label=_icon_for(stream),
            name="audio-app-icon",
        )

        # name
        self._display_name = (
            stream.name
            or stream.application_id
            or stream.description
            or "App"
        )
        display = self._display_name
        if len(display) > 18:
            display = display[:16] + "…"

        self.name_label = Label(
            label=display,
            name="audio-app-name",
            h_align="start",
            h_expand=True,
            size=11,
        )

        # volume scale
        self.scale = AnimatedScale(
            name="audio-app-scale",
            orientation="horizontal",
            min_value=0,
            max_value=100,
            value=stream.volume,
            h_expand=True,
            increments=[1, 5],
        )
        self.scale.set_size_request(120, 14)
        self.scale.connect("change-value", self._on_user_change)

        # volume percentage
        self.vol_label = Label(
            label=f"{round(stream.volume)}%",
            name="audio-app-vol-label",
            size=10,
        )

        # mute button
        self.mute_btn = EventBox(name="audio-app-mute-btn")
        self.mute_icon = Label(
            label="󰖁" if stream.muted else "󰕾",
            name="audio-app-mute-icon",
            size=12,
        )
        self.mute_btn.add(self.mute_icon)
        self.mute_btn.connect("button-press-event", self._on_mute_toggle)

        # layout
        self.add(self.icon)
        self.add(self.name_label)
        self.add(self.scale)
        self.add(self.vol_label)
        self.add(self.mute_btn)

        # stream signals
        self._vh = stream.connect("notify::volume", self._on_stream_vol)
        self._mh = stream.connect("notify::muted", self._on_stream_muted)

    # ── user interaction ────────────────────────────────────────

    @cooldown(0.2)
    def _on_user_change(self, _widget, _scroll, value):
        if self._updating:
            return
        clamped = max(0, min(100, value))
        self._stream.volume = clamped
        self.vol_label.set_text(f"{round(clamped)}%")

    def _on_mute_toggle(self, *_):
        self._stream.muted = not self._stream.muted

    # ── stream → widget sync ───────────────────────────────────

    def _on_stream_vol(self, stream, _pspec):
        self._updating = True
        vol = max(0, min(100, round(stream.volume)))
        self.scale.animate_value(vol)
        self.vol_label.set_text(f"{vol}%")
        self._updating = False

    def _on_stream_muted(self, stream, _pspec):
        self.mute_icon.set_text("󰖁" if stream.muted else "󰕾")

    # ── cleanup ─────────────────────────────────────────────────

    def disconnect_stream(self):
        try:
            self._stream.disconnect(self._vh)
            self._stream.disconnect(self._mh)
        except Exception:
            pass


# ────────────────────────────────────────────────────────────────────
#  Popup window
# ────────────────────────────────────────────────────────────────────

class AudioPopup(PopupWindow):
    """Hover popup showing per-application volume sliders."""

    def __init__(self, parent, pointing_to, audio_service, **kwargs):
        super().__init__(
            parent=parent,
            pointing_to=pointing_to,
            layer="top",
            name="audio-popup-window",
            type="popup",
            margin="15px 0 0 0",
            anchor="top left",
            title="fabric-audio-popup",
            visible=False,
            v_expand=False,
            h_expand=False,
            **kwargs,
        )

        self._audio = audio_service
        self._rows: dict[int, AppRow] = {}

        # ── content ────────────────────────────────────────────
        content = Box(
            orientation="v",
            name="audio-popup-content",
            spacing=6,
        )

        # header: title + device subtitle
        header = Box(orientation="v", name="audio-popup-header", spacing=2)
        title = Label(
            label="Volume Mixer",
            name="audio-popup-title",
            h_align="start",
        )
        self._subtitle = Label(
            label="",
            name="audio-popup-subtitle",
            h_align="start",
            h_expand=True,
            size=10,
        )
        header.add(title)
        header.add(self._subtitle)

        divider = Box(name="audio-divider", h_expand=True)

        self._app_list = Box(
            orientation="v",
            name="audio-app-list",
            spacing=2,
        )

        self._empty_label = Label(
            label="No applications playing audio",
            name="audio-empty-label",
            h_align="center",
        )
        self._app_list.add(self._empty_label)

        content.add(header)
        content.add(divider)
        content.add(self._app_list)

        self.overlay_revealer = HackedRevealer(
            bezier_curve=(0.3, -0.06, 0, 1.02),
            duration=0.450,
            name="audio-revealer",
            child=content,
        )
        self.add(self.overlay_revealer)

    # ── called by AudioWidget on tick + before showing ──────────

    def refresh(self):
        """Reconcile rows with the current list of application streams."""
        try:
            apps = self._audio.applications or []
        except Exception:
            apps = []

        # update device subtitle
        try:
            spk = self._audio.speaker
            if spk:
                self._subtitle.set_text(spk.description or spk.name or "")
            else:
                self._subtitle.set_text("No output device")
        except Exception:
            self._subtitle.set_text("")

        # add new
        seen_ids = set()
        for stream in apps:
            try:
                sid = stream.id
                seen_ids.add(sid)
                if sid not in self._rows:
                    row = AppRow(stream)
                    self._rows[sid] = row
                    self._app_list.add(row)
                    logger.debug(
                        f"audio popup: + '{stream.name}' id={sid}"
                    )
            except Exception as exc:
                logger.warning(f"audio popup: add failed: {exc}")

        # remove stale
        for sid in [k for k in self._rows if k not in seen_ids]:
            row = self._rows.pop(sid)
            row.disconnect_stream()
            self._app_list.remove(row)
            row.destroy()
            logger.debug(f"audio popup: - id={sid}")

        # empty state
        if self._rows:
            if self._empty_label.get_parent():
                self._app_list.remove(self._empty_label)
        else:
            if not self._empty_label.get_parent():
                self._app_list.add(self._empty_label)
