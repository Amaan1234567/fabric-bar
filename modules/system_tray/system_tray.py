from fabric.system_tray.widgets import SystemTray
from fabric.widgets.box import Box


class barSystemTray(Box):
    def __init__(self, name="system-tray", **kwargs):
        super().__init__(**kwargs)
        self.tray = SystemTray(spacing=10)
        self.add(self.tray)
