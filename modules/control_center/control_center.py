from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.box import Box
from fabric.widgets.flowbox import FlowBox
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.revealer import Revealer
from fabric.widgets.eventbox import EventBox
from gi.repository import GLib

from .bluetooth_toggle import BluetoothToggle
from .wifi_toggle_button import WifiToggle
from .rog_control_center_toggle import ROGButton
from .wallpaper_change_button import WallpaperChangeButton
from .mic_toggle_button import MicToggle
from .performance_toggle import PerformanceToggle
from .brightness_slider import BrightnessSlider


class ControlCenter(Window):
    def __init__(self, **kwargs):
        super().__init__(layer="top",
                         title="control_center",
            anchor="right top bottom",
            exclusivity="auto",
            visible=False,
            type="top-level",
            margin="0px 0px 0px -1px",
            **kwargs)

        self.small_toggles = Box(orientation='h',h_align="center",spacing=15,children=[WifiToggle(),BluetoothToggle(),ROGButton(),WallpaperChangeButton(),MicToggle()])
        self.med_toggles = Box(orientation='h',h_align="center",spacing=10,children=[PerformanceToggle(),BrightnessSlider()],h_expand=True)
        self.control_center_content = Box(name="control-center",orientation='v',h_align="center",spacing=20)
        self.control_center_content.add(self.small_toggles)
        self.control_center_content.add(self.med_toggles)
        
        

        self.add(self.control_center_content)
        #self.show()

       

    def toggle_control_center(self):
        self.set_visible(not self.get_visible())

# if self.revealer.get_reveal_child():
#     GLib.timeout_add(300,self.set_visible,not self.get_visible())
#     self.revealer.set_reveal_child(False)
# else:
#     self.set_visible(True)
#     self.revealer.set_reveal_child(True)