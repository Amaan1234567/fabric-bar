from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.eventbox import EventBox
from fabric.utils import cooldown

from gi.repository import GLib, Gdk
import dbus.mainloop.glib
import subprocess


class BluetoothWidget(Box):
    def __init__(self, interval=5, **kwargs):
        super().__init__(**kwargs)
        self.interval = interval
        self._tooltip = "Bluetooth status loading..."
        self.content_event_box = EventBox(on_enter_notify_event=self.on_hover,on_button_release_event=self.on_left_click)
        self.content = Box(orientation='h',spacing=0)
        self.icon = Label(name="bluetooth-icon", label='󰂯')
        self.content.set_tooltip_text(self._tooltip)
        self.percentage = Label(name="bluetooth-percentage")
        self.content.add(self.icon)
        self.button = Button(child=self.content)
        self.content_event_box.add(self.button)
        self.add(self.content_event_box)
        GLib.timeout_add_seconds(self.interval, self._refresh)
        self.connect(
            "state-flags-changed",
            lambda btn, *_: (
                btn.set_cursor("pointer")
                if btn.get_state_flags() & 2  # type: ignore
                else btn.set_cursor("default"),
            ),
        )

    @cooldown(1)
    def on_left_click(self,_ ,event):
        if(event.button == Gdk.BUTTON_PRIMARY):
            subprocess.run("blueman-manager",shell=True)
            
    def on_hover(self):
        self._refresh()
        self.content.set_tooltip_text(self._tooltip)

    def _refresh(self):
        self._tooltip = self._get_bluetooth_status()
        self.icon.set_tooltip_text(self._tooltip)
        return True

    def _get_bluetooth_status(self):
        try:
            bus = dbus.SystemBus()
            manager = dbus.Interface(bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
            objects = manager.GetManagedObjects()

            adapters = [path for path, iface in objects.items() if "org.bluez.Adapter1" in iface]
            if not adapters:
                return "Bluetooth not available"

            connected_devices = []

            for path, ifaces in objects.items():
                if "org.bluez.Device1" in ifaces:
                    dev_props = ifaces["org.bluez.Device1"]
                    if dev_props.get("Connected", False):
                        name = dev_props.get("Alias", "Unknown")
                        battery = None

                        if "org.bluez.Battery1" in ifaces:
                            battery_props = ifaces["org.bluez.Battery1"]
                            battery = int(battery_props.get("Percentage"))
                            self.percentage.set_label(f"{battery}%")

                        line = f"✓ {name}"
                        if battery is not None:
                            line += f" ({battery}%)"

                        connected_devices.append(line)

            if connected_devices:
                if(len(self.content.children)==1):
                    self.content.add(self.percentage)
                return "Bluetooth On\n" + "\n".join(connected_devices)
            else:
                self.percentage.set_label("")
                #print(len(self.children))
                if(len(self.content.children)>1):
                    self.content.children.pop()
                return "Bluetooth On\nNo devices connected"

        except Exception as e:
            return f"Bluetooth error: {e}"