
from os import name
from loguru import logger
from fabric import Fabricator
from fabric.widgets.revealer import Revealer
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.utils import remove_handler
from gi.repository import GLib
from custom_widgets.animated_scale import AnimatedScale
from custom_widgets.popup_window import PopupWindow as Window

class BrightnessOSD(Window):
    """Brightness on-screen display (OSD) widget."""
    def __init__(self, parent,pointing_to, **kwargs):
        super().__init__(
            parent,
            pointing_to,
            layer="top",
            title="volume_osd",
            name="brightness-osd-window",
            anchor="bottom",
            margin="0 0 0 100",
            type="popup",
            pass_through=True,
            exclusivity="none",
            all_visible=False,
            **kwargs,
        )

        self.icon = Label(name="brightness-osd-icon", label="󰃠")

        self.scale = AnimatedScale(
            name="brightness-osd-scale",
            orientation="v",
            min_value=0,
            max_value=100,
            inverted=True,
            value=0,
            h_expand=True,
            v_expand=True,
            has_origin=True,
        )
        self.content = Box(
            name="brightness-osd-box",
            orientation="vertical",
            spacing=10,
            children=[self.scale,self.icon],
        )

        self.revealer = Revealer(
            child=self.content,
            transition_duration=200,
            transition_type="slide-left",
            name="brightness-osd-revealer",
        )
        self.add(self.revealer)
        self.is_closing = False
        self.last_revealer_handler = None
        self.last_window_handler = None
        self.max_brightness_file = "/sys/class/backlight/intel_backlight/max_brightness"
        self.actual_brightness_file = "/sys/class/backlight/intel_backlight/actual_brightness"

        with open(self.max_brightness_file, "r", encoding="utf8") as max_brightness:
            self.max_brightness = int(max_brightness.read())
        # initialize last-known brightness so we only react to real changes
        self._last_brightness = self._get_brightness()

        Fabricator(poll_from=lambda E: self._get_brightness(), interval=100).connect(
            "changed", self._update_brightness
        )
        self.hide()

    def _get_brightness(self):
        try:
            with open(self.max_brightness_file, "r", encoding="utf8") as fmax:
                max_brightness = int(fmax.read())

            with open(self.actual_brightness_file, "r", encoding="utf8") as fact:
                actual_brightness = int(fact.read())

            percentage = round((actual_brightness / max_brightness) * 100)
            logger.debug(f"current_brightness: {percentage}")
            return percentage
        except (OSError, ValueError, ZeroDivisionError):
            return 0

    def _update_brightness(self, _emitter, value):
        logger.debug(f"Brightness changed: {value}")
        try:
            percentage = int(value)
        except ValueError:
            return

        # only update UI when brightness actually changes
        if percentage == self._last_brightness:
            return

        self._last_brightness = percentage
        self._show_popup()
        self.scale.animate_value(percentage)
        self._hide_popup()

    def _hide_popup(self):
        self.is_closing = True
        self.last_revealer_handler = GLib.timeout_add(
            3000, self.revealer.set_reveal_child, False
        )
        self.last_window_handler = GLib.timeout_add(3250, self.hide)

    def _show_popup(self):
        if self.is_closing:
            if self.last_revealer_handler:
                remove_handler(self.last_revealer_handler)
            if self.last_window_handler:
                remove_handler(self.last_window_handler)
            self.is_closing = False
        self.show()
        self.revealer.set_reveal_child(True)
