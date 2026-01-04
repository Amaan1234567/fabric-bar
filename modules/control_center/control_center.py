"""contains the control center widget"""

from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.box import Box
from fabric.widgets.revealer import Revealer

from modules.control_center.bluetooth_toggle import BluetoothToggle
from modules.control_center.wifi_toggle_button import WifiToggle
from modules.control_center.rog_control_center_toggle import ROGButton
from modules.control_center.wallpaper_change_button import WallpaperChangeButton
from modules.control_center.mic_toggle_button import MicToggle
from modules.control_center.performance_toggle import PerformanceToggle
from modules.control_center.brightness_slider import BrightnessSlider
from modules.control_center.notifications_panel import NotificationsPanel


class ControlCenter(Window):
    """control center widget"""

    def __init__(self, app_data, **kwargs):
        super().__init__(
            layer="top",
            title="control_center",
            anchor="right top bottom",
            exclusivity="auto",
            visible=True,
            type="top-level",
            margin="0px 0px 0px -1px",
            **kwargs
        )

        self.small_toggles = Box(
            orientation="h",
            h_align="center",
            spacing=15,
            children=[
                WifiToggle(),
                BluetoothToggle(),
                ROGButton(),
                WallpaperChangeButton(),
                MicToggle(),
            ],
        )
        self.small_toggles.set_homogeneous(True)
        self.med_toggles = Box(
            orientation="h",
            h_align="fill",
            spacing=10,
            children=[PerformanceToggle(), BrightnessSlider()],
            h_expand=True,
        )
        self.med_toggles.set_homogeneous(True)
        self.control_center_content = Box(
            name="control-center", orientation="v", h_align="center", spacing=20
        )
        self.control_center_content.add(self.small_toggles)
        self.control_center_content.add(self.med_toggles)
        self.control_center_content.add(NotificationsPanel(app_data=app_data))
        self.revealer = Revealer(
            child=self.control_center_content,
            child_revealed=False,
            transition_duration=100,
            transition_type="slide-left",
            size=[1, -1],
        )
        self.add(self.revealer)
        # self.show()

    def toggle_control_center(self):
        """toggles control center"""
        # self.set_visible(not self.get_visible())

        if self.revealer.get_reveal_child():
            # GLib.timeout_add(300, self.set_visible, not self.get_visible())
            self.revealer.set_reveal_child(False)
        else:
            # self.set_visible(True)
            self.revealer.set_reveal_child(True)
