from fabric.notifications.service import Notifications
from fabric.widgets.wayland import WaylandWindow
from fabric.widgets.revealer import Revealer

class NotificationPopup(WaylandWindow):
    def __init__(self,**kwargs):
        super().__init__(self,**kwargs)
