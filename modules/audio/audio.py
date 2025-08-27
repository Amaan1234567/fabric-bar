from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from custom_widgets.animated_circular_progress_bar import AnimatedCircularProgressBar
from fabric.widgets.label import Label
from fabric.audio import Audio
from fabric.utils import cooldown
from gi.repository import Gtk , Gdk
import subprocess

class AudioWidget(Box):
    """A widget that displays and controls volume using Fabric's Audio service."""

    # Unicode / Nerd‑Font icons
    _ICONS = {
        "muted":       "󰖁",
        "low":         "󰖀",
        "medium":      "󰕾",
        "high":        "󰓃",
        "headphones":  "󰋎",
        "bluetooth":   "󰂯",
    }

    def __init__(self, step_size=5, show_label=False, show_tooltip=True, **kwargs):
        # We only need to listen for nothing here; events go on the progress bar
        super().__init__(on_scroll_event=self.on_scroll,**kwargs)
        
        self.eventbox = EventBox(events=[],on_scroll_event = self.on_scroll)
        # 1) Create the AnimatedCircularProgressBar
        self.progress = AnimatedCircularProgressBar(
            name="audio-progress-bar",
            value=float(subprocess.getoutput("wpctl status | grep '\\*' | head -1 | sed -E 's/.*\\[vol: ([0-9.]+)\\].*/\\1/'").strip()),
            line_style="round",
            line_width=4,
            size=35,
            start_angle=140,
            end_angle=395,
            invert=True,
        )

        # 2) Create the icon and pack it *inside* the progress bar
        self.icon = Label(name="audio-icon", label=self._ICONS["medium"])
        self.progress.add(self.icon)
        self.progress.show_all()

        # 3) Optional percentage label (outside the ring)
        self.show_label = show_label
        if show_label:
            self.pct = Label(name="audio-pct", label="0%")
            self.add(self.pct)

        # 4) Put the progress bar (with icon inside) into this EventBox
        self.eventbox.add(self.progress)
        self.eventbox.add_events("scroll")
        self.add(self.eventbox)
        # 5) Audio service & config
        self.audio = Audio()
        self.step = step_size
        self.show_tooltip = show_tooltip

        # 6) Connect the audio signals
        self.audio.connect("notify::speaker", self._on_speaker_changed)

        # 7) Hook scroll & hover on the progress widget
        # self.connect("scroll_event",       self.on_scroll)
        # self.progress.connect("scroll_event",       self.on_scroll)
        self.eventbox.connect("scroll_event",self.on_scroll)
        self.icon.connect("state-flags-changed", self._on_hover)

        # 8) Initialize
        self._on_speaker_changed()
        # subprocess.run(r"wpctl set-volume @DEFAULT_AUDIO_SINK@ 1%+ --limit 1.0",shell=True)
        # subprocess.run(r"wpctl set-volume @DEFAULT_AUDIO_SINK@ 1%- --limit 1.0",shell=True)
        
        
    def _on_speaker_changed(self, *args):
        """When the default sink changes, listen for its volume/mute changes."""
        speaker = self.audio.speaker
        if not speaker:
            return

        speaker.connect("notify::volume", self._update_ui)
        speaker.connect("notify::muted",  self._update_ui)
        self._update_ui()

    def _update_ui(self, *args):
        """Refresh progress, icon, label, and tooltip."""

        spk = self.audio.speaker
        if not spk:
            return

        vol = round(spk.volume)
        muted = spk.muted
        desc = (spk.description or "").lower()
        
        #print(desc)
        #print(spk.icon_name)

        # 1) Update the ring fill
        self.progress.animate_value(vol/100)
        self.progress.set_value(vol / 100)

        # 2) Update the % label if enabled
        if self.show_label:
            self.pct.set_text(f"{vol}%")

        # 3) Pick the right icon
        if muted or vol == 0:
            icon = self._ICONS["muted"]
        elif "headset" in spk.icon_name or "headphones" in desc:
            icon = self._ICONS["headphones"]
        elif "bluetooth" in desc:
            icon = self._ICONS["bluetooth"]
        else:
            if vol < 30:
                icon = self._ICONS["low"]
            elif vol < 70:
                icon = self._ICONS["medium"]
            else:
                icon = self._ICONS["high"]

        self.icon.set_text(icon)

        # 4) Tooltip
        if self.show_tooltip:
            tip = (
                f"<b>Device:</b> {self.audio.speaker.description}\n"
                f"<b>Volume:</b> {vol}%\n"
                f"<b>Muted:</b> {'Yes' if muted else 'No'}"
            )
            self.progress.set_tooltip_markup(tip)
    @cooldown(0.1)
    def on_scroll(self, _ ,event):
        """Scroll on the ring to change volume."""

        step = self.step
        if event.direction == Gdk.ScrollDirection.UP:
            self.audio.speaker.volume = min(self.audio.speaker.volume + step, 100)
        elif event.direction == Gdk.ScrollDirection.DOWN:
            self.audio.speaker.volume = max(self.audio.speaker.volume - step, 0)

    def _on_hover(self, widget, event):
        """Show tooltip immediately on hover, if enabled."""
        if self.show_tooltip:
            # re-set tooltip to update any values
            self._update_ui()
            self.progress.show_tooltip()  # ensure it pops up now (GTK handles rest)
