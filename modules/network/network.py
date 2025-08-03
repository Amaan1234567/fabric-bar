from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.eventbox import EventBox
from gi.repository import GLib, Gdk
import NetworkManager as NM
import subprocess

class NetworkWidget(Box):
    """
    A Fabric widget displaying network type & strength using JetBrainsMono Nerd Font glyphs.
    Polls ActiveConnections via NetworkManager for both Wi-Fi and Ethernet.
    """
    def __init__(self, interval=5, **kwargs):
        super().__init__(**kwargs)
        self.interval = interval
        # Glyph label
        self.content = EventBox(on_enter_notify_event=self.on_hover,on_button_release_event=self.on_left_click)
        self.icon = Label(name='network-icon', label='󰤯', justification="center")
        self.content.add(self.icon)
        self.add(self.content)
        # Refresh periodically
        GLib.timeout_add_seconds(self.interval, self._refresh)
        self.current_tooltip = self._get_active_connection_info()[2]
        self.icon.set_tooltip_text(self.current_tooltip)
        self.connect("state-flags-changed",self.on_hover)
        self.connect(
            "state-flags-changed",
            lambda btn, *_: (
                btn.set_cursor("pointer")
                if btn.get_state_flags() & 2  # type: ignore
                else btn.set_cursor("default"),
            ),
        )

    def on_left_click(self, _ ,event):
        #print(event)
        if(event.button == Gdk.BUTTON_PRIMARY):
            subprocess.run("~/Scripts/network_select_rofi.sh",shell=True)

    def on_hover(self):
        self._refresh()
        self.icon.set_tooltip_text(self.current_tooltip)

    def _refresh(self):
        status, strength ,tooltip= self._get_active_connection_info()
        self.current_tooltip = tooltip
        glyph = self._map_glyph(status, strength)
        self.icon.set_label(glyph)
        return True
    

    def _get_active_connection_info(self):
        """
        Inspects ActiveConnections to determine current connection:
          - 'wifi' with signal strength
          - 'ethernet'
          - 'tether'
          - falls back to 'none'
        """
        try:
            for ac in NM.NetworkManager.ActiveConnections:
                try:
                    devices = ac.Devices
                    if not devices:
                        continue
                    dev = devices[0]
                    dtype = dev.DeviceType
                    ip4_config = dev.Ip4Config
                    ip_addr = ip4_config.AddressData[0]['address'] if ip4_config and ip4_config.AddressData else 'Unknown'

                    if dtype == 2:  # WIFI
                        ap = dev.SpecificDevice().ActiveAccessPoint
                        strength = getattr(ap, 'Strength', 0)
                        ssid = ap.Ssid if ap and ap.Ssid else 'Unknown'
                        tooltip = f"Wi-Fi: {ssid}\nIP: {ip_addr}\nStrength: {strength}%"
                        return 'wifi', strength, tooltip

                    elif dtype == 1:  # ETHERNET
                        iface = getattr(dev, 'Interface', '') or ''
                        mode = 'tether' if 'usb' in iface.lower() else 'ethernet'
                        tooltip = f"{mode.title()}\nIP: {ip_addr}"
                        return mode, None, tooltip

                except Exception as e:
                    print(f"exception {e}")
                    continue

        except Exception as e:
            print(f"outer exception {e}")
            pass

        return 'none', None, None

    def _map_glyph(self, status: str, strength: int | None) -> str:
        """
        Maps connection status and signal strength to JetBrainsMono Nerd Font glyphs.
        """
        WIFI = {
            'empty': '󰤯', 'low': '󰤟', 'medium': '󰤢', 'high': '󰤥', 'full': '󰤨'
        }
        ETH = '󰈀'
        USB = ''
        OFF = ''

        if status == 'wifi' and strength is not None:
            if strength < 25:
                lvl = 'empty'
            elif strength < 50:
                lvl = 'low'
            elif strength < 75:
                lvl = 'medium'
            elif strength < 95:
                lvl = 'high'
            else:
                lvl = 'full'
            glyph = WIFI.get(lvl, OFF)
            return glyph
        if status == 'ethernet':
            return ETH
        if status == 'tether':
            return USB
        return OFF