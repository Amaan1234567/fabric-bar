from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from custom_widgets.animated_scale import AnimatedScale
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

    def __init__(self,step_size=5,show_tooltip=True,**kwargs):
        # We only need to listen for nothing here; events go on the progress bar
        super().__init__(name="audio-container",spacing=5,show_label=False, **kwargs)
        
        # 1) Create the AnimatedCircularProgressBar
        self.scale = AnimatedScale(
            name="audio-scale",
            orientation="horizontal",
            min=0,
            max=100,
            value=float(subprocess.getoutput("wpctl status | grep '\\*' | head -1 | sed -E 's/.*\\[vol: ([0-9.]+)\\].*/\\1/'").strip()),
            draw_value=False,
            h_expand=True,
            v_expand=True,
            has_origin = True,
            increments=(0.1, 0.05),
        )
        self.scale.connect("change-value",self.on_scroll)


        self.icon = Label(name="audio-icon", label=self._ICONS["medium"])



        self.add(self.icon)
        self.add(self.scale)
        # 5) Audio service & config
        self.audio = Audio()
        self.step = step_size
        self.show_tooltip = show_tooltip

        # 6) Connect the audio signals
        self.audio.connect("notify::speaker", self._on_speaker_changed)

        # 7) Hook scroll & hover on the progress widget
        # self.connect("scroll_event",       self.on_scroll)
        # self.scale.connect("scroll_event",       self.on_scroll)
        self.connect("state-flags-changed", self._on_hover)

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

    @cooldown(0.2)
    def _update_ui(self, *args):
        """Refresh progress, icon, label, and tooltip."""

        spk = self.audio.speaker
        if not spk:
            return

        vol = round(spk.volume)
        muted = spk.muted
        #print(muted)
        desc = (spk.description or "").lower()
        
        #print(self.scale.value)
        self.scale.animate_value(vol/100)
        self.scale.set_value(vol / 100)


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
            self.set_tooltip_markup(tip)

    def on_scroll(self, _ ,__,value):
        """Scroll on the ring to change volume."""

        self.scale.animate_value(value)
        self.scale.set_value(value)
        self.audio.speaker.volume = value * 100

    def _on_hover(self, widget, event):
        """Show tooltip immediately on hover, if enabled."""
        if self.show_tooltip:
            # re-set tooltip to update any values
            self._update_ui()
            self.scale.show_tooltip()  # ensure it pops up now (GTK handles rest)
