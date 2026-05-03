from gi.repository import GLib
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.revealer import Revealer
from fabric.utils import remove_handler
from custom_widgets.animated_scale import AnimatedScale
from fabric.widgets.wayland import WaylandWindow as Window # <--- Add this!
from services.brightnessservice import BrightnessService
from utils.monitor import get_monitor_info

class BrightnessOSD(Window):
    def __init__(self, parent, pointing_to, monitor_id=0, **kwargs):
        # Determine if this OSD is internal or external
        self.device_type, self.hardware_id = get_monitor_info(monitor_id)
        
        super().__init__(
            # parent,
            # pointing_to,
            layer="top",
            title="brightness_osd",
            name="brightness-osd-window",
            anchor="bottom right",
            type="popup",
            pass_through=True,
            all_visible=False,
            monitor=monitor_id, # Ensure the window goes to the right screen
            **kwargs,
        )

        self.service = BrightnessService()
        self.icon = Label(name="brightness-osd-icon", label="󰃠")
        self.scale = AnimatedScale(
            name="brightness-osd-scale",
            orientation="v",
            min_value=0,
            max_value=100,
            inverted=True,
            value=0, # Initial value, will be updated by signal
            h_expand=True,
            v_expand=True,
            has_origin=True,
        )
        
        self.revealer = Revealer(
            child=Box(
                name="brightness-osd-box",
                orientation="vertical",
                spacing=10,
                children=[self.scale, self.icon],
            ),
            transition_duration=200,
            transition_type="slide-left",
        )
        
        self.add(self.revealer)
        self.hide_timer = None
        self.window_timer = None
        self._last_val = -1

        self.service.connect("changed", self._on_brightness_changed)
        self.hide()

    def _on_brightness_changed(self, service, dev_type, dev_id, value):
        # Match against our dynamic detection
        # Convert both to strings to avoid "1" vs 1 mismatch
        if dev_type != self.device_type or str(dev_id) != str(self.hardware_id):
            return

        if value == self._last_val: 
            return

        self._last_val = value
        self.scale.animate_value(value)
        self._show_popup()

    def _show_popup(self):
        if self.hide_timer: remove_handler(self.hide_timer)
        if self.window_timer: remove_handler(self.window_timer)
        
        self.show()
        self.revealer.set_reveal_child(True)
        
        self.hide_timer = GLib.timeout_add(2500, self.revealer.set_reveal_child, False)
        self.window_timer = GLib.timeout_add(2750, self.hide)