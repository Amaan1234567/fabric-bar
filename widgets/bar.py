#!/usr/bin/env python3
import subprocess
import fabric

from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.label import Label
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.separator import Separator


from modules.clock.clock import Clock
from modules.cpu.cpu import Cpu
from modules.memory.memory import Memory
from modules.workspaces.workspaces import CustomWorkspaces
from modules.active_window_name.active_window import WindowName
from modules.cava.cava import CavaWidget
from modules.mpris.mpris import Mpris
from modules.notification_button.notification_button import NotificationButton
from modules.battery.battery import BatteryWidget
from modules.audio.audio import AudioWidget
from modules.network.network import NetworkWidget
from modules.bluetooth.bluetooth import BluetoothWidget
from modules.system_tray.system_tray import barSystemTray


class StatusBar(Window):
    def __init__(self, **kwargs):
        super().__init__(
            layer="top",
            name="bar-window",
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
        self.right_module = NotificationButton()
        left_box = Box(
            orientation="h",
            spacing=20,
            children=[
                self.cpu,
                self.memory,
                self.workspaces,
                self.active_window,
            ],
        )

        self.mpris = Mpris(window=self)
        self.volume = AudioWidget()
        self.battery = BatteryWidget()
        self.network = NetworkWidget(self, interval=1)
        self.bluetooth = BluetoothWidget(interval=1)
        # self.system_tray = barSystemTray()
        center_box = Box(
            orientation="h",
            spacing=60,
            h_align="center",
            children=[
                self.mpris,
                self.cava,
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
            ],
        )

        right_box = Box(
            orientation="h",
            spacing=10,
            children=[self.battery, self.right_module, self.logout_btn],
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
