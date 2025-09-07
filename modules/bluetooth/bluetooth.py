from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.eventbox import EventBox
from fabric.utils import cooldown
from fabric.bluetooth.service import BluetoothClient, BluetoothDevice

from gi.repository import GLib, Gdk
import subprocess


class BluetoothWidget(Box):
    def __init__(self, interval=1, **kwargs):
        super().__init__(**kwargs)
        self.interval = interval
        self._tooltip = "Bluetooth status loading..."
        
        # Initialize Bluetooth client
        self.bluetooth_client = BluetoothClient()
        
        self.content_event_box = EventBox(
            on_enter_notify_event=self.on_hover,
            on_button_release_event=self.on_left_click
        )
        self.content = Box(orientation='h', spacing=0)
        self.icon = Label(name="bluetooth-icon", label='󰂯')  # Default BT icon
        self.content.set_tooltip_text(self._tooltip)
        self.percentage = Label(name="bluetooth-percentage")
        self.content.add(self.icon)
        
        self.button = Button(child=self.content)
        self.button.connect(
            "state-flags-changed",
            lambda btn, *_: (
                btn.set_cursor("pointer")
                if btn.get_state_flags() & 2  # type: ignore
                else btn.set_cursor("default"),
            ),
        )
        self.content_event_box.add(self.button)
        self.add(self.content_event_box)
        
        # Set up periodic refresh
        GLib.timeout_add_seconds(self.interval, self._refresh)
        
        self.connect(
            "state-flags-changed",
            lambda btn, *_: (
                btn.set_cursor("pointer")
                if btn.get_state_flags() & 2  # type: ignore
                else btn.set_cursor("default"),
            ),
        )
        
        # Initial refresh
        self._refresh()
        GLib.timeout_add_seconds(5,self.refresh_bluetooth_client)

    def refresh_bluetooth_client(self):
        try:
            #self.bluetooth_client = BluetoothClient()
            pass
        except AttributeError as e :
            #print(e)
            pass

    @cooldown(1)
    def on_left_click(self, _, event):
        if event.button == Gdk.BUTTON_PRIMARY:
            subprocess.run("blueman-manager & disown",shell=True)
            
    def on_hover(self):
        self._refresh()
        self.content.set_tooltip_text(self._tooltip)

    def _refresh(self):
        self._tooltip = self._get_bluetooth_status()
        self.content.set_tooltip_text(self._tooltip)
        self._update_icon()
        return True

    def _update_icon(self):
        """Update the Bluetooth icon based on state"""
        try:
            if not self.bluetooth_client.enabled:
                # Bluetooth is disabled
                self.icon.set_label('󰂲')  # Bluetooth off/unavailable icon
            elif not self.bluetooth_client.powered:
                # Bluetooth is enabled but not powered
                self.icon.set_label('󰂲')  # Bluetooth off icon
            elif self.bluetooth_client.connected_devices:
                # Bluetooth is on and has connected devices
                self.icon.set_label('󰂱')  # Bluetooth connected icon
            else:
                # Bluetooth is on but no connected devices
                self.icon.set_label('󰂯')  # Bluetooth on icon
                
        except Exception as e:
            print(f"Error updating Bluetooth icon: {e}")
            self.icon.set_label('󰂲')  # Default to off icon on error

    def _get_bluetooth_status(self):
        """Get Bluetooth status using Fabric's Bluetooth service"""
        try:
            # Check if Bluetooth is enabled
            if not self.bluetooth_client.enabled:
                # Clear percentage label when Bluetooth is disabled
                self.percentage.set_label("")
                if len(self.content.children) > 1:
                    self.content.remove(self.percentage)
                return "Bluetooth not available"
            
            # Check if Bluetooth is powered
            if not self.bluetooth_client.powered:
                # Clear percentage label when Bluetooth is off
                self.percentage.set_label("")
                if len(self.content.children) > 1:
                    self.content.remove(self.percentage)
                return "Bluetooth Off"
            
            # Get connected devices
            connected_devices = self.bluetooth_client.connected_devices
            #print(connected_devices)
            
            if connected_devices:
                device_info = []
                first_device_battery = None
                
                for device in connected_devices:
                    name = device.name or device.alias or device.address or "Unknown"
                    battery_level = None
                    
                    # Check if device has battery information
                    try:
                        if hasattr(device, 'battery_percentage') and device.battery_percentage is not None:
                            battery_level = int(device.battery_percentage)
                            #print(battery_level)
                        elif hasattr(device, 'battery_level') and device.battery_level is not None:
                            battery_level = int(device.battery_level)
                    except (ValueError, TypeError):
                        battery_level = None
                    
                    # Format device info
                    line = f"✓ {name}"
                    if battery_level is not None:
                        line += f" ({battery_level}%)"
                        # Show battery percentage for first connected device
                        if first_device_battery is None:
                            first_device_battery = battery_level
                    
                    device_info.append(line)
                
                # Update percentage display
                if first_device_battery is not None:
                    self.percentage.set_label(f"{first_device_battery}%")
                    if len(self.content.children) == 1:
                        self.content.add(self.percentage)
                else:
                    self.percentage.set_label("")
                    if len(self.content.children) > 1:
                        self.content.remove(self.percentage)
                
                return "Bluetooth On\n" + "\n".join(device_info)
            else:
                # Clear percentage label when no devices connected
                self.percentage.set_label("")
                if len(self.content.children) > 1:
                    self.content.remove(self.percentage)
                return "Bluetooth On\nNo devices connected"
                
        except Exception as e:
            print(f"Bluetooth status error: {e}")
            return f"Bluetooth error: {e}"
