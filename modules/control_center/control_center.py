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

from custom_widgets.side_corner import SideCorner
# notify_child_revealed=lambda revealer, _: [
#                 revealer.hide(),
#                 self.set_visible(False),
#             ]
#             if not revealer.fully_revealed
#             else None,
#             notify_content=lambda revealer, _: [
#                 self.set_visible(True),
#             ]
#             if revealer.child_revealed
#             else None,

class ControlCenter(Window):
    def __init__(self, **kwargs):
        super().__init__(layer="top",
                         title="control_center",
            anchor="right top bottom",
            exclusivity="auto",
            visible=True,
            type="top-level",
            margin="0px 0px 0px -1px",
            **kwargs)

        self.small_toggles = Box(orientation='h',h_align="center",spacing=15,children=[WifiToggle(),BluetoothToggle(),ROGButton(),WallpaperChangeButton(),MicToggle()])
        self.med_toggles = Box(orientation='h',h_align="center",spacing=10,children=[PerformanceToggle(),BrightnessSlider()],h_expand=True)
        self.control_center_content = Box(name="control-center",orientation='v',h_align="center",spacing=20)
        self.control_center_content.add(self.small_toggles)
        self.control_center_content.add(self.med_toggles)
        self.all_corners = Box(
            name="all-corners",
            orientation="v",
            h_expand=True,
            v_expand=True,
            h_align="fill",
            v_align="fill",
            children=[
                Box(
                    name="top-corners",
                    orientation="h",
                    h_align="fill",
                    children=[
                        SideCorner("top-right", [40,40]),
                    ],
                ),
                Box(v_expand=True,name="middle-area"),
                Box(
                    name="bottom-corners",
                    orientation="h",
                    h_align="fill",
                    children=[
                        SideCorner("bottom-right", [40,40]),
                    ],
                ),
            ],
        )
        self.content = Box(orientation='h',v_expand=True)
        self.revealer: Revealer = Revealer(
            name="control-center-revealer",
            transition_type='slide-left',
            transition_duration=300,
            child_revealed=False,
            size=(0, -1),
        )
        self.revealer.set_reveal_child(False)
        #self.content.add(self.all_corners)
        self.content.add(self.control_center_content)
        self.revealer.add(self.content)


        self.add(self.revealer)
        self.show()

       

    def toggle_control_center(self):
        is_opening = not self.revealer.get_reveal_child()

        self.revealer.set_reveal_child(is_opening)
        if is_opening:
            # Make window visible immediately when opening
            #self.set_visible(True)
            #self.revealer.set_visible(True)
            self.revealer.set_reveal_child(is_opening)
        else:
            # Delay hiding window until animation finishes (~500ms)
            self.revealer.set_reveal_child(is_opening)
            #GLib.timeout_add(400, self.set_visible, False)  # milliseconds
            #GLib.timeout_add(400, self.revealer.set_visible,False)