from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.box import Box
from fabric.widgets.image import Image
import asyncio
import subprocess
from gi.repository import GLib
import dbus.mainloop.glib
import NetworkManager as NM


from modules.control_center.control_center import ControlCenter
from modules.bluetooth.bluetooth import BluetoothWidget
from modules.network.network import NetworkWidget
# Ensure D-Bus uses GLib main loop
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)


control_center = ControlCenter()

class NotificationButton(Box):
    def __init__(self,**kwargs):
        super().__init__(**kwargs,name="notification-button")
        #self.parent_conn = parent_conn
        self.content = EventBox(on_button_release_event = self.trigger_control_center)
        self.container_box = Box(orientation='h',spacing=4)
        self.notifcations = Button(label="")
        self.notifcations.connect(
            "state-flags-changed",
            lambda btn, *_: (
                btn.set_cursor("pointer")
                if btn.get_state_flags() & 2  # type: ignore
                else btn.set_cursor("default"),
            ),
        )
        
        self.container_box.add(self.notifcations)
        self.content.add(self.container_box)
        self.add(self.content)

        
        #self.trigger_control_center(None,None) # hacky bug fix

    def trigger_control_center(self,_,__):
        #print("toggling control center")
        control_center.toggle_control_center()


