#!/usr/bin/env python3
import subprocess
import fabric

from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.datetime import DateTime
from fabric.widgets.label import Label
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.hyprland import Hyprland, HyprlandEvent
from fabric.widgets.overlay import Overlay



from modules.clock.clock import Clock
from modules.cpu.cpu import Cpu
from modules.memory.memory import Memory
from modules.workspaces.workspaces import CustomWorkspaces
from modules.active_window_name.active_window import WindowName
from modules.cava.cava import CavaWidget
from modules.mpris.mpris import Mpris
from modules.right_module.right_module import NotificationButton
from modules.battery.battery import BatteryWidget
from modules.audio.audio import AudioWidget
from modules.network.network import NetworkWidget
from modules.bluetooth.bluetooth import BluetoothWidget

class StatusBar(Window):
    def __init__(self, **kwargs):
        super().__init__(
            layer="top",
            anchor="left top right",
            exclusivity="auto",
            type="top-level",
            all_visible=True,
            **kwargs
        )

        self.cpu = Cpu()
        self.workspaces = CustomWorkspaces()
        self.memory = Memory()
        self.clock = Clock()
        self.logout_btn = Button(
            label="⏻",
            # CORRECTED: Use `dispatch` for commands.
            on_clicked=lambda *a: subprocess.run(["wlogout","--protocol","layer-shell"]),
            name="logout"
        )

        self.active_window = WindowName()
        self.cava = CavaWidget()
        self.right_module = NotificationButton()
        left_box = Box(orientation="h",spacing=20,children=[
            self.cpu,
            self.memory,
            self.workspaces,
            self.active_window,
            self.cava
        ])

        self.mpris = Mpris(window=self)
        self.volume = AudioWidget()
        self.battery = BatteryWidget()
        self.network = NetworkWidget(interval=1)
        self.bluetooth = BluetoothWidget(interval=1)
        center_box = Box(orientation="h", children=[self.clock])
        right_box = Box(orientation="h", spacing=10, children=[
            self.mpris,
            self.volume,
            self.network,
            self.bluetooth,
            self.right_module,
            self.battery,
            self.logout_btn
        ])

        self.content = CenterBox(name="bar",
            start_children=left_box,
            center_children=center_box,
            end_children=right_box
        )
        
        self.add(self.content)


