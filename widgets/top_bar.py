"""holds the main bar widget"""

import tomllib

from fabric.widgets.box import Box
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.wayland import WaylandWindow as Window
from loguru import logger

from modules.active_window_name.active_window import WindowName
from modules.audio.audio import AudioWidget
from modules.background_op_progress.background_op_progress import BackgroundOpProgress
from modules.battery.battery import BatteryWidget
from modules.bluetooth.bluetooth import BluetoothWidget
from modules.cava.cava import CavaWidget
from modules.clock.clock import Clock
from modules.control_center_button.control_center_button import ControlCenterButton
from modules.cpu.cpu import Cpu
from modules.disk.disk import DiskWidget
from modules.gpu.gpu import GpuWidget
from modules.logout_button.logout_button import LogoutButton
from modules.memory.memory import Memory
from modules.mpris.mpris import Mpris
from modules.network.network import NetworkWidget
from modules.network_speed.network_speed import NetworkSpeed
from modules.system_tray.system_tray import barSystemTray as SystemTray
from modules.workspaces.workspaces import CustomWorkspaces
from widgets.system_controls import SystemControls


class TopBar(Window):
    """top bar of UI"""

    def __init__(self, app_data, monitor=0, **kwargs):
        super().__init__(
            layer="top",
            name="bar-window",
            anchor="left top right",
            pass_through=False,
            exclusivity="auto",
            all_visible=False,
            monitor=monitor,
            **kwargs,
        )
        self.app_data = app_data

        self.config = tomllib.loads(open(f"config.toml", "rb").read().decode("utf-8"))
        print(self.config)
        if self.config["layout"]["type"] == "dynamic":
            self.setup_dynamic_layout()
        elif self.config["layout"]["type"] == "single":
            self.setup_single_layout()
        elif self.config["layout"]["type"] == "left-center-right":
            self.setup_left_center_right_layout()

        # self.add(self.content)

    def get_widget_registry(self, name):
        """Returns a dictionary mapping string keys from the layout toml to widget factories."""
        widget_registry = {
            "cpu": Cpu,
            "mem": Memory,
            "gpu": GpuWidget,
            "network-speed": NetworkSpeed,
            "disk-usage": DiskWidget,
            "mpris": Mpris,
            "window-title": WindowName,  # type: ignore
            "hyprland-workspaces": CustomWorkspaces,  # type: ignore
            "clock": Clock,
            "system-tray": SystemTray,
            "system-controls": SystemControls,
            "battery": BatteryWidget,
            "control-center": ControlCenterButton,
            "powermenu": LogoutButton,
            "audio": AudioWidget,
            "bluetooth": BluetoothWidget,
            "cava": CavaWidget,  # type: ignore
            "network": NetworkWidget,
            "background_op": BackgroundOpProgress,
            "spacer": Box,
            "h-padding": Box,
            "v-padding": Box,
        }

        return (
            widget_registry[name](
                app_data=self.app_data, window=self, monitor=self.monitor, h_expand=True
            )
            if name in widget_registry
            else Exception(f"Widget '{name}' not found in widget registry.")
        )

    def setup_dynamic_layout(self):
        """Sets up the bar layout with dynamic widgets based on the configuration."""
        self.content = Box(
            name="bar",
            orientation="h",
            h_expand=True,
            v_align="center",
        )
        cur_box = Box(orientation="h", spacing=10)
        for widget_name in self.config["layout"]["dynamic_widgets"]:
            if widget_name == "spacer":
                self.content.add(cur_box)
                self.content.add(self.get_widget_registry(widget_name))
                logger.info(f"Adding widget: {widget_name} to dynamic layout")
                cur_box = Box(orientation="h", spacing=10)
            else:
                logger.info(f"Adding widget: {widget_name} to dynamic layout")
                cur_box.add(self.get_widget_registry(widget_name))
        self.content.add(cur_box)
        self.add(self.content)

    def setup_left_center_right_layout(self):
        """Sets up the bar layout with left, center, and right sections."""
        left_box = Box(
            orientation="h",
            spacing=10,
        )

        right_box = Box(
            orientation="h",
            spacing=10,
        )

        center_box = Box(
            orientation="h",
            spacing=10,
        )

        box = Box()
        for side in ["left_widgets", "center_widgets", "right_widgets"]:
            if side == "left_widgets":
                box = left_box
            elif side == "center_widgets":
                box = center_box
            elif side == "right_widgets":
                box = right_box

            for widget_name in self.config["layout"][side]:
                logger.info(f"Adding widget: {widget_name} to {side}")
                box.add(self.widget_registry[widget_name])
            logger.info(f"Finished adding widgets to {side}")
            logger.info(f"Current state of {side}: {box.children}")

        self.content = CenterBox(
            name="bar",
            orientation="h",
            start_children=left_box,
            center_children=center_box,
            end_children=right_box,
            v_align="center",
        )
        self.add(self.content)
