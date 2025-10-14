"""holds the main bar widget"""
import subprocess

from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.separator import Separator


from modules.clock.clock import Clock
from modules.cpu.cpu import Cpu
from modules.memory.memory import Memory
from modules.workspaces.workspaces import CustomWorkspaces
from modules.active_window_name.active_window import WindowName
from modules.cava.cava import CavaWidget
from modules.mpris.mpris import Mpris
from modules.control_center_button.control_center_button import ControlCenterButton
from modules.battery.battery import BatteryWidget
from modules.audio.audio import AudioWidget
from modules.network.network import NetworkWidget
from modules.bluetooth.bluetooth import BluetoothWidget

class TopBar(Window):
    """top bar of UI"""
    def __init__(self, **kwargs):
        super().__init__(
            layer="top",
            name="bar-window",
            anchor="left top right",
            pass_through=False,
            exclusivity="auto",
            all_visible=False,
            **kwargs
        )

        self.cpu = Cpu()
        self.workspaces = CustomWorkspaces()
        self.memory = Memory()
        self.clock = Clock()
        self.logout_btn = Button(
            label="⏻",
            # CORRECTED: Use `dispatch` for commands.
            on_clicked=lambda *a: subprocess.run(
                ["wlogout", "--protocol", "layer-shell"]
            ),
            name="logout",
        )
        self.seperator = Separator(
            orientation="h", h_expand=True, h_align="fill", style_classes="sep"
        )
        self.active_window = WindowName()
        self.cava = CavaWidget()
        self.right_module = ControlCenterButton()
        left_box = Box(
            orientation="h",
            spacing=20,
            children=[
                self.cpu,
                self.memory,
            ],
        )

        self.mpris = Mpris(window=self)
        self.volume = AudioWidget()
        self.battery = BatteryWidget()
        self.network = NetworkWidget(self, interval=1)
        self.bluetooth = BluetoothWidget(interval=1)
        center_box = Box(
            orientation="h",
            spacing=30,
            h_align="center",
            children=[
                self.mpris,
                self.cava,
                self.active_window,
                self.workspaces,
            ],
        )

        right_box = Box(
            orientation="h",
            spacing=20,
            children=[
                self.clock,
                Box(
                    name="system-controls",
                    orientation="h",
                    spacing=10,
                    children=[
                        self.volume,
                        self.network,
                        self.bluetooth,
                    ],
                ),
                self.battery, 
                self.right_module, 
                self.logout_btn],
        )

        self.content = CenterBox(
            name="bar",
            orientation="h",
            start_children=left_box,
            center_children=center_box,
            end_children=right_box,
            v_align="center",
        )

        self.add(self.content)
