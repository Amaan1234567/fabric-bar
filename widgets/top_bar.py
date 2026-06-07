"""holds the main bar widget"""

from fabric.widgets.box import Box
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.wayland import WaylandWindow as Window


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
from modules.gpu.gpu import GpuWidget
from modules.network_speed.network_speed import NetworkSpeed
from modules.system_tray.system_tray import barSystemTray as SystemTray
from modules.logout_button.logout_button import LogoutButton
from modules.disk.disk import DiskWidget


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
        self.cpu = Cpu(window=self)
        self.workspaces = CustomWorkspaces()
        self.memory = Memory(window=self)
        self.gpu = GpuWidget(window=self)
        self.network_speed = NetworkSpeed(window=self)
        self.disk = DiskWidget(window=self)
        self.clock = Clock()
        self.logout_btn = LogoutButton(window=self)
        self.active_window = WindowName()
        self.cava = CavaWidget()
        self.right_module = ControlCenterButton(app_data=app_data)
        left_box = Box(
            orientation="h",
            spacing=10,
            children=[self.cpu, self.memory, self.gpu, self.network_speed, self.disk],
        )

        self.system_tray = SystemTray()
        self.mpris = Mpris(window=self)
        self.volume = AudioWidget(window=self)
        self.battery = BatteryWidget()
        self.network = NetworkWidget(self, interval=1)
        self.bluetooth = BluetoothWidget(interval=1)
        center_box = Box(
            orientation="h",
            spacing=20,
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
                self.system_tray,
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
                self.logout_btn,
            ],
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
