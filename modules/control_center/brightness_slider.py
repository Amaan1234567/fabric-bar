"""holds module for brightness slider used in control center"""

from loguru import logger

from fabric import Fabricator
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay
from fabric.utils import cooldown, exec_shell_command_async
from custom_widgets.animated_scale import AnimatedScale

# ---------------------------------------------------------------- helpers
MIN_BRIGHT = 5  # avoid a black screen
MIN_BRIGHTNESS_STEP = 3
STEP = 5  # percentage per scroll “tick”


# ------------------------------------------------------------- main widget
class BrightnessSlider(Box):
    """
    Material-You slider with overlay label and scroll support.
    """

    def __init__(self, *, step: int = STEP, name="brightness-container"):
        super().__init__(
            orientation="vertical",
            spacing=0,
            size=[145, 30],
            name=name,
            v_expand=True,
            h_expand=True,
        )
        path = "/sys/class/backlight/intel_backlight/"
        self.actual_brightness_file = f"{path}/actual_brightness"
        self.max_brightness_file = f"{path}/max_brightness"
        self._step = step
        self.scale = AnimatedScale(
            name="brightness-scale",
            orientation="horizontal",
            min_value=MIN_BRIGHT,
            max_value=100,
            value=self._get_brightness(),
            draw_value=False,
            h_expand=True,
            v_expand=True,
            has_origin=True,
            increments=(STEP, STEP),
        )

        self.label = Label(
            label="󰃠",
            name="brightness-label",
            justification="left",
            v_align="center",
            h_align="start",
            h_expand=False,
            v_expand=True,
            size=[30, 30],
        )
        self.scale.connect("change-value", self._on_scroll)
        self.overlay = Overlay(child=self.scale, overlays=self.label)
        self.add(self.overlay)

        self.value_changing = True
        Fabricator(poll_from=lambda E: self._get_brightness(), interval=500).connect(
            "changed", self._refresh
        )

    def _set_brightness_rel(self, delta_pct: int):
        """
        Add or subtract a *relative* percentage (positive or negative).
        """

        exec_shell_command_async(
            " ".join(["brightnessctl", "set", f"{abs(delta_pct)}%"])
        )

    def _get_brightness(self):
        with open(self.max_brightness_file, "r", encoding="utf8") as max_brightness:
            max_brightness = int(max_brightness.read())

            with open(
                self.actual_brightness_file, "r", encoding="utf8"
            ) as actual_brightness:
                actual_brightness = int(actual_brightness.read())
                current_brightness = round((actual_brightness / max_brightness) * 100)

                logger.debug(f"current_brightness: {current_brightness}")
                return current_brightness

    @cooldown(0.1)
    def _on_scroll(self, _, __, value):
        """Mouse wheel sends ±STEP % *relative* increments."""
        self.value_changing = True
        logger.debug("detecting scroll on brightness scale")

        self._set_brightness_rel(value)
        print("brigntness value:", value)
        if abs(self.scale.value - value) > MIN_BRIGHTNESS_STEP:
            self.scale.animate_value(value)
        self.scale.set_value(value)

        self.value_changing = False

    def _refresh(self, _, value):
        if self.value_changing:
            return

        if abs(self.scale.value - value) > MIN_BRIGHTNESS_STEP:
            self.scale.animate_value(value)
        self.scale.set_value(value)
        if value < 15:
            self.label.add_style_class("brightness-icon-low")
        else:
            self.label.remove_style_class("brightness-icon-low")
