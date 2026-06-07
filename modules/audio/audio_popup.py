"""Audio mixer popup with per-application volume control and device switcher."""

import subprocess

from loguru import logger
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.eventbox import EventBox
from fabric.widgets.button import Button
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

_DEVICE_ICONS = {
    "bluetooth": "󰂯",
    "headphone": "󰋋",
    "headset": "󰋎",
    "hdmi": "󰡁",
    "usb": "󰏶",
    "speaker": "󰓃",
}


def _icon_for(stream):
    """Best-effort Nerd Font icon from stream name/app id."""
    n = (stream.name or stream.application_id or "").lower()
    for key, icon in _APP_ICONS.items():
        if key in n:
            return icon
    return "󰎆"


def _device_icon_for(stream):
    """Icon for an output device based on its description."""
    desc = (stream.description or stream.icon_name or "").lower()
    for key, icon in _DEVICE_ICONS.items():
        if key in desc:
            return icon
    return "󰓃"


# ────────────────────────────────────────────────────────────────────
#  Device selector row (inside the expandable list)
# ────────────────────────────────────────────────────────────────────


class DeviceRow(EventBox):
    """A single output device in the switcher list."""

    def __init__(self, stream, is_current=False, **kwargs):
        super().__init__(name="audio-device-row", **kwargs)

        box = Box(orientation="h", spacing=8, h_expand=True)

        radio = Label(
            label="󰡖" if is_current else "",
            name="audio-device-current" if is_current else "audio-device-radio",
        )

        icon = Label(
            label=_device_icon_for(stream),
            name="audio-device-item-icon",
            size=14,
        )

        name_label = Label(
            label=stream.description or stream.name or "Unknown Output",
            name="audio-device-current" if is_current else "audio-device-item-name",
            h_align="start",
            h_expand=True,
            size=10,
        )

        box.add(radio)
        box.add(icon)
        box.add(name_label)
        self.add(box)


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
            size=24,
        )

        # name
        self._display_name = (
            stream.name or stream.application_id or stream.description or "App"
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
        """Disconnect all signal handlers from the stream to avoid
        callbacks after the row is removed."""
        try:
            self._stream.disconnect(self._vh)
            self._stream.disconnect(self._mh)
        except Exception:
            pass


# ────────────────────────────────────────────────────────────────────
#  Popup window
# ────────────────────────────────────────────────────────────────────


class AudioPopup(PopupWindow):
    """Hover popup with master volume info, device switcher, and per-app sliders."""

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
        self._device_expanded = False

        # ── content ────────────────────────────────────────────
        content = Box(orientation="v", name="audio-popup-content", spacing=6)

        # ── header: title + master volume ──────────────────────
        title_row = Box(orientation="h", name="audio-popup-header", spacing=8)
        title = Label(
            label="Volume Mixer",
            name="audio-popup-title",
            h_align="start",
            h_expand=True,
        )
        self._master_vol = Label(label="0%", name="audio-master-vol", h_align="end")
        title_row.add(title)
        title_row.add(self._master_vol)

        # ── device selector (clickable) ────────────────────────
        self._device_row = EventBox(name="audio-device-selector")
        device_inner = Box(orientation="h", spacing=6, h_expand=True)
        self._device_icon = Label(
            label="󰓃",
            name="audio-device-icon",
            size=14,
        )
        self._device_name = Label(
            label="",
            name="audio-device-name",
            h_align="start",
            h_expand=True,
            size=10,
        )
        self._device_chevron = Button(
            label="▸",
            name="audio-device-chevron",
        )
        device_inner.add(self._device_icon)
        device_inner.add(self._device_name)
        device_inner.add(self._device_chevron)
        self._device_row.add(device_inner)
        self._device_row.connect("button-press-event", self._toggle_device_list)
        self._device_chevron.connect("clicked", self._toggle_device_list)

        # ── expandable device list ─────────────────────────────
        self._device_list = Box(
            orientation="v",
            name="audio-device-list",
            spacing=2,
            h_expand=True,
        )
        self._device_revealer = HackedRevealer(
            bezier_curve=(0.3, -0.06, 0, 1.02),
            duration=0.300,
            name="audio-device-revealer",
            child=self._device_list,
        )

        divider = Box(name="audio-divider", h_expand=True)

        # ── app list ───────────────────────────────────────────
        self._app_list = Box(orientation="v", name="audio-app-list", spacing=2)

        self._empty_label = Label(
            label="No applications playing audio",
            name="audio-empty-label",
            h_align="center",
        )
        self._app_list.add(self._empty_label)

        # ── assemble ───────────────────────────────────────────
        content.add(title_row)
        content.add(self._device_row)
        content.add(self._device_revealer)
        content.add(divider)
        content.add(self._app_list)

        self.overlay_revealer = HackedRevealer(
            bezier_curve=(0.3, -0.06, 0, 1.02),
            duration=0.450,
            name="audio-revealer",
            child=content,
        )
        self.add(self.overlay_revealer)

    # ────────────────────────────────────────────────────────────
    #  Device switcher
    # ────────────────────────────────────────────────────────────

    def _toggle_device_list(self, *_):
        self._device_expanded = not self._device_expanded
        if self._device_expanded:
            self._rebuild_device_list()
            self._device_revealer.set_reveal_child(True)
            self._device_chevron.set_label("▾")
        else:
            self._device_revealer.set_reveal_child(False)
            self._device_chevron.set_label("▸")

    def _rebuild_device_list(self):
        for child in self._device_list.get_children():
            self._device_list.remove(child)
            child.destroy()

        current_speaker = self._audio.speaker
        current_id = current_speaker.id if current_speaker else None

        for speaker in self._audio.speakers:
            is_current = speaker.id == current_id
            row = DeviceRow(speaker, is_current=is_current)
            row.connect(
                "button-press-event",
                lambda *a, s=speaker: self._select_device(
                    s
                ),  # ← *a absorbs widget+event
            )
            self._device_list.add(row)

    def _select_device(self, stream):
        """Switch the default output sink."""
        # try pactl by numeric id first
        try:
            subprocess.run(
                ["pactl", "set-default-sink", str(stream.id)],
                check=True,
                timeout=2,
            )
            logger.debug(f"Switched sink by id={stream.id}: {stream.description}")
        except Exception as exc:
            logger.warning(f"Sink switch by id failed: {exc}")
            # fallback: find the pactl sink name matching the description
            self._select_device_by_description(stream)

        # collapse the device list
        self._device_expanded = False
        self._device_revealer.set_reveal_child(False)
        self._device_chevron.set_label("▸")

    def _select_device_by_description(self, stream):
        """Fallback: match by description and use the pactl sink name."""
        try:
            result = subprocess.run(
                ["pactl", "list", "sinks"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            target_desc = (stream.description or "").strip()
            sink_name = None

            for line in result.stdout.split("\n"):
                stripped = line.strip()
                if stripped.startswith("Name:"):
                    sink_name = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("Description:"):
                    desc = stripped.split(":", 1)[1].strip()
                    if desc == target_desc and sink_name:
                        subprocess.run(
                            ["pactl", "set-default-sink", sink_name],
                            check=True,
                            timeout=2,
                        )
                        logger.debug(f"Switched sink by name: {sink_name}")
                        return

            logger.warning(f"No pactl sink matched description: '{target_desc}'")
        except Exception as exc:
            logger.warning(f"Sink switch by description failed: {exc}")

    # ────────────────────────────────────────────────────────────
    #  Refresh — called by AudioWidget on tick + before showing
    # ────────────────────────────────────────────────────────────

    def refresh(self):
        """Update device info, master volume, and reconcile app rows."""
        # ── master speaker info ────────────────────────────────
        try:
            spk = self._audio.speaker
            if spk:
                vol = round(spk.volume)
                muted = spk.muted
                self._master_vol.set_text(f"{vol}%{'  (muted)' if muted else ''}")
                self._device_name.set_text(spk.description or spk.name or "Unknown")
                self._device_icon.set_text(_device_icon_for(spk))
            else:
                self._master_vol.set_text("—")
                self._device_name.set_text("No output device")
                self._device_icon.set_text("󰓃")
        except Exception:
            self._master_vol.set_text("—")

        # ── update device list if it's currently open ──────────
        if self._device_expanded:
            self._rebuild_device_list()

        # ── application streams ────────────────────────────────
        try:
            apps = self._audio.applications or []
        except Exception:
            apps = []

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
                    logger.debug(f"audio popup: + '{stream.name}' id={sid}")
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
