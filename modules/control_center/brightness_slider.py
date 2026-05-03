from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay
from gi.repository import GLib
from custom_widgets.animated_scale import AnimatedScale
from services.brightnessservice import BrightnessService
from fabric.utils import cooldown # Assuming you have a cooldown decorator

class BrightnessSlider(Box):
    def __init__(self, *, step: int = 5, name="brightness-container"):
        super().__init__(
            orientation="vertical",
            name=name,
            v_expand=True,
            h_expand=True,
        )
        self.service = BrightnessService()
        self._is_tracking = False
        self._reset_timeout = None
        
        # Hardcoded to internal for now as requested
        self.target_type = "internal"
        self.target_id = "internal"

        self.scale = AnimatedScale(
            name="brightness-scale",
            orientation="horizontal",
            min_value=5,
            max_value=100,
            # Direct access to the internal value
            value=self.service._internal_val, 
            draw_value=False,
            h_expand=True,
            v_expand=True,
            has_origin=True,
            increments=(step, step),
        )

        self.label = Label(
            label="󰃠",
            name="brightness-label",
            v_align="center",
            h_align="start",
            size=[30, 30],
        )

        self.scale.connect("change-value", self._on_scale_moved)
        self.add(Overlay(child=self.scale, overlays=self.label))
        
        # Connect to the new 4-argument signal
        self.service.connect("changed", self._on_service_changed)
        self._update_style(self.service._internal_val)

    def _on_service_changed(self, service, dev_type, dev_id, value):
        # Filter: only update if the internal screen changed and we aren't dragging
        if dev_type == self.target_type and not self._is_tracking:
            self.scale.animate_value(value)
            self._update_style(value)

    @cooldown(0.1)
    def _on_scale_moved(self, _, __, value):
        self._is_tracking = True
        
        # Use the new explicit method
        self.service.set_brightness(self.target_type, self.target_id, int(value))
        self.scale.animate_value(value) # Immediate feedback
        self._update_style(value)
        
        if self._reset_timeout:
            GLib.source_remove(self._reset_timeout)
        self._reset_timeout = GLib.timeout_add(1000, self._reset_tracking)

    def _reset_tracking(self):
        self._is_tracking = False
        self._reset_timeout = None
        return False

    def _update_style(self, value):
        if value < 15:
            self.label.add_style_class("brightness-icon-low")
        else:
            self.label.remove_style_class("brightness-icon-low")