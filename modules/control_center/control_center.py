"""contains the control center widget"""

from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.box import Box
from fabric.widgets.revealer import Revealer
from fabric.utils import cooldown
from custom_widgets.popup_window import PopupWindow
from experimental.hacktk import HackedRevealer
from modules.control_center.bluetooth_toggle import BluetoothToggle
from modules.control_center.wifi_toggle_button import WifiToggle
from modules.control_center.rog_control_center_toggle import ROGButton
from modules.control_center.wallpaper_change_button import WallpaperChangeButton
from modules.control_center.mic_toggle_button import MicToggle
from modules.control_center.performance_toggle import PerformanceToggle
from modules.control_center.brightness_slider import BrightnessSlider
from modules.control_center.notifications_panel import NotificationsPanel
from modules.control_center.gamemode_toggle import GamemodeToggleButton


class ControlCenter(PopupWindow):
    """control center widget"""

    def __init__(self, app_data,parent,**kwargs):
        super().__init__(
            layer="top",
            title="control_center",
            anchor="top bottom right",
            exclusivity="none",
            visible=True,
            type="popup",
            margin="30px 0px 40px 0px",
            parent=parent,
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
                GamemodeToggleButton()
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
        self.revealer = HackedRevealer(
            bezier_curve=(0.3, -0.06, 0, 1.02),
            duration=.350,
            child=self.control_center_content,
            child_revealed=False,
            # transition_duration=200,
            transition_type="slide-left",
            # sizde=[1, -1],
        )
        self.add(self.revealer)
        # self.show()

    @cooldown(0.35)
    def toggle_control_center(self):
        """toggles control center"""
        # self.set_visible(not self.get_visible())

        if self.revealer.get_reveal_child():
            # GLib.timeout_add(300, self.set_visible, not self.get_visible())
            self.revealer.set_reveal_child(False)
            # self.set_visible(False)
        else:
            self.revealer.set_reveal_child(True)
            # self.set_visible(True)
