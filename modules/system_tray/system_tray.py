from fabric.widgets.box import Box
from fabric.system_tray.widgets import SystemTray


class barSystemTray(Box):
    def __init__(self, name="system-tray", **kwargs):
        super().__init__(**kwargs)
        self.tray = SystemTray()
        self.add(self.tray)
