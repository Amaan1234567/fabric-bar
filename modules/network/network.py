from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.eventbox import EventBox
from fabric.widgets.revealer import Revealer
from fabric.widgets.button import Button
from fabric.widgets.entry import Entry
from gi.repository import GLib, Gdk, Gio
import NetworkManager as NM
import subprocess
from custom_widgets.popwindow import PopupWindow


class NetworkWidget(Box):
    """
    A Fabric widget displaying network type & strength using JetBrainsMono Nerd Font glyphs.
    Polls ActiveConnections via NetworkManager for both Wi-Fi and Ethernet.
    """
    def __init__(self, window, interval=1, **kwargs):
        super().__init__(**kwargs)
        self.interval = interval
        self.window = window
        self.networks = []
        self._scanning = False
        
        # Glyph label
        self.content = EventBox(
            on_enter_notify_event=self.on_hover,
            on_button_release_event=self.on_left_click
        )
        self.icon = Label(name='network-icon', label='󰤯', justification="center")
        self.content.add(self.icon)
        self.add(self.content)
        
        # Refresh periodically
        GLib.timeout_add_seconds(self.interval, self._refresh)
        
        try:
            self.current_tooltip = self._get_active_connection_info()[2]
            self.icon.set_tooltip_text(self.current_tooltip)
        except:
            self.current_tooltip = "Network"
            self.icon.set_tooltip_text(self.current_tooltip)
            
        self.connect("enter-notify-event", self.on_hover)
        self.connect(
            "state-flags-changed",
            lambda btn, *_: (
                btn.set_cursor("pointer")
                if btn.get_state_flags() & 2  # type: ignore
                else btn.set_cursor("default"),
            ),
        )

        self.networks_box = Box(
            name="wifi-networks-box",
            orientation="vertical",
            spacing=4,
        )
        
        # Revealer for slide animation
        self.networks_revealer = Revealer(
            name="wifi-networks-revealer",
            transition_type="slide-down",
            transition_duration=200,
            child_revealed=True,  # Always revealed inside popup
        )
        self.networks_revealer.add(self.networks_box)
        
        # Popup window
        self.networks_popup = PopupWindow(
            parent=self.window,
            pointing_to=self,
            title = "fabric-networks-popup",
            name="networks-overlay-window",
            layer="top",
            type="popup",
            anchor="top right",
            visible=False,
            child=self.networks_revealer,
            v_expand=False,
            h_expand=False,
            keyboard_mode="on_demand"
        )

        try:
            self.networks_popup.set_accept_focus(True)
            self.networks_popup.set_can_focus(True)
        except:
            pass

        self._update_networks_list()

        self._auto_hide_timer = None
        self._is_hovering = False
        
        self.networks_popup.connect("enter-notify-event", self._on_popup_enter)
        self.networks_popup.connect("leave-notify-event", self._on_popup_leave)

        # Start async network scanning
        self._start_async_network_scanning()

    def _start_async_network_scanning(self):
        """Start periodic async network scanning"""
        def scan_networks():
            if not self._scanning:
                self._scan_networks_async()
            return True  # Continue periodic calls
        
        # Initial scan and then every 8 seconds
        scan_networks()
        GLib.timeout_add_seconds(8, scan_networks)

    def _scan_networks_async(self):
        """Scan networks asynchronously using GLib subprocess"""
        if self._scanning:
            return
            
        self._scanning = True
        
        try:
            # Create subprocess launcher
            launcher = Gio.SubprocessLauncher.new(
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE
            )
            
            # Launch nmcli command
            proc = launcher.spawnv([
                "nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL,SECURITY", 
                "dev", "wifi", "list"
            ])
            
            # Read output asynchronously - FIX: proper callback signature
            proc.communicate_utf8_async(None, None, self._on_scan_complete)
            
        except Exception as e:
            print(f"Failed to start async scan: {e}")
            self._scanning = False

    def _on_scan_complete(self, proc, result):
        """Handle async scan completion - FIXED callback"""
        self._scanning = False
        
        try:
            # FIX: Proper way to get results from async subprocess
            success, stdout, stderr = proc.communicate_utf8_finish(result)
            
            if not success or proc.get_exit_status() != 0:
                print(f"Scan failed: {stderr if stderr else 'Unknown error'}")
                return
            
            # Parse networks
            networks = []
            if stdout and stdout.strip():
                for line in stdout.strip().split('\n'):
                    if not line:
                        continue
                        
                    parts = line.split(':')
                    if len(parts) >= 4:
                        ssid = parts[1]
                        if not ssid or ssid == '--':
                            continue
                        
                        try:
                            networks.append({
                                'ssid': ssid,
                                'signal': int(parts[2]) if parts[2].isdigit() else 0,
                                'security': parts[1],
                                'in_use': parts == 'yes'
                            })
                        except (ValueError, IndexError):
                            continue
            
            # Update networks on main thread
            old_count = len(self.networks)
            self.networks = networks
            new_count = len(self.networks)
            
            #print(f"Networks updated: {old_count} -> {new_count}")
            
        except Exception as e:
            print(f"Failed to parse scan results: {e}")

    def _get_saved_connections_async(self, callback):
        """Get saved connections asynchronously"""
        try:
            launcher = Gio.SubprocessLauncher.new(
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE
            )
            
            proc = launcher.spawnv([
                "nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"
            ])
            
            def on_connections_complete(proc, result):
                try:
                    # FIX: Proper async result handling
                    success, stdout, stderr = proc.communicate_utf8_finish(result)
                    
                    if not success or proc.get_exit_status() != 0:
                        print(f"Get connections failed: {stderr if stderr else 'Unknown error'}")
                        callback([])
                        return
                    
                    saved_ssids = []
                    if stdout:
                        for line in stdout.strip().split('\n'):
                            if not line:
                                continue
                            parts = line.split(':')
                            if len(parts) >= 2 and parts[1] == '802-11-wireless':
                                saved_ssids.append(parts)
                    
                    callback(saved_ssids)
                    
                except Exception as e:
                    print(f"Failed to parse connections: {e}")
                    callback([])
            
            proc.communicate_utf8_async(None, None, on_connections_complete)
            
        except Exception as e:
            print(f"Failed to get connections async: {e}")
            callback([])

    def _on_popup_enter(self, widget, event):
        """Called when mouse enters the popup"""
        self._is_hovering = True
        self._cancel_auto_hide_timer()

    def _on_popup_leave(self, widget, event):
        """Called when mouse leaves the popup"""
        self._is_hovering = False
        self._start_auto_hide_timer()

    def _start_auto_hide_timer(self):
        """Start the auto-hide timer (1.5 seconds)"""
        self._cancel_auto_hide_timer()
        self._auto_hide_timer = GLib.timeout_add(1500, self._auto_hide_popup)

    def _cancel_auto_hide_timer(self):
        """Cancel the auto-hide timer if it exists"""
        if self._auto_hide_timer:
            GLib.source_remove(self._auto_hide_timer)
            self._auto_hide_timer = None

    def _auto_hide_popup(self):
        """Hide the popup automatically (called by timer)"""
        if not self._is_hovering and self.networks_popup.get_visible():
            self.networks_revealer.set_reveal_child(False)
            GLib.timeout_add(250, self.networks_popup.set_visible, False)
        
        self._auto_hide_timer = None
        return False  # Don't repeat timer

    def on_left_click(self, _, event):
        """Handle click events"""
        if event.button == Gdk.BUTTON_PRIMARY:
            # Left click - original behavior
            #subprocess.run("~/Scripts/network_select_rofi.sh", shell=True)
            self._toggle_networks_popup()
        # elif event.button == Gdk.BUTTON_SECONDARY:
        #     # Right click - toggle networks popup
            

    def _toggle_networks_popup(self):
        """Toggle the networks popup"""
        #print(f"Toggle popup called, networks count: {len(self.networks)}")
        
        if self.networks_popup.get_visible():
            #print("Hiding popup")
            self.networks_revealer.set_reveal_child(False)
            GLib.timeout_add(250, self.networks_popup.set_visible, False)
        else:
            #print("Showing popup")
            # Trigger fresh scan when opening popup
            if not self._scanning:
                self._scan_networks_async()
            
            # Update networks list before showing
            self._update_networks_list_async()
            self._on_popup_enter(None, None)
            self.networks_popup.set_visible(True)
            self.networks_revealer.set_reveal_child(True)
            
            # Try to make popup focusable
            def make_popup_focusable():
                try:
                    self.networks_popup.set_can_focus(True)
                    self.networks_popup.grab_focus()
                except:
                    pass
                return False
            
            GLib.timeout_add(1000, make_popup_focusable)

    def _update_networks_list_async(self):
        """Update networks list asynchronously"""
        def on_connections_received(saved_connections):
            self._populate_networks_ui(saved_connections)
        
        self._get_saved_connections_async(on_connections_received)

    def _is_wifi_on(self):
        """Check if WiFi is enabled"""
        try:
            result = subprocess.run([
                "nmcli", "radio", "wifi"
            ], capture_output=True, text=True, check=False)
            return "enabled" in result.stdout
        except:
            return False

    def _populate_networks_ui(self, saved_connections):
        """Populate networks UI (called on main thread)"""
        #print(f"Updating networks list, {len(self.networks)} networks available")
        #print(saved_connections)
        # Clear existing network buttons
        for child in self.networks_box.children:
            self.networks_box.remove(child)
        
        if not self._is_wifi_on():
            print("Wifi is Off or not available")
            no_networks = Label(
                name="wifi-no-networks",
                label="Wifi is Off"
            )
            self.networks_box.add(no_networks)
            return

        if not self.networks:
            print("No networks found, showing message")
            no_networks = Label(
                name="wifi-no-networks",
                label="🔄 Scanning for networks..."
            )
            self.networks_box.add(no_networks)
            return
        
        #print(f"Found {len(saved_connections)} saved connections")
        
        # Sort by signal strength
        self.networks.sort(key=lambda x: x.get('signal', 0), reverse=True)
        
        # Add network buttons (limit to 8)
        for network in self.networks[:8]:
            try:
                ssid = network.get('ssid', '')
                signal = network.get('signal', 0)
                is_secure = bool(network.get('security', ''))
                connected = network.get('in_use', False)
                is_saved = ssid in [i[0] for i in saved_connections]
                
                #print(f"Processing network: {ssid}, secure: {is_secure}, connected: {connected}, saved: {is_saved}")
                
                # Skip connected networks
                if connected:
                    continue
                
                # Create network container
                network_container = Box(
                    name="wifi-network-container",
                    orientation="vertical",
                    spacing=2,
                )
                
                # Create network button
                lock_icon = "" if is_secure else ""
                label = f"{lock_icon} {ssid} ({signal}%)"
                
                network_button = Button(
                    name="wifi-network-available",
                    label=label,
                    h_align="start",
                    on_clicked=lambda btn, s=ssid, sec=is_secure, saved=is_saved: 
                              self._handle_network_click(s, sec, saved, btn)
                )
                network_button.connect(
                    "state-flags-changed",
                    lambda btn, *_: (
                        btn.set_cursor("pointer")
                        if btn.get_state_flags() & 2  # type: ignore
                        else btn.set_cursor("default"),
                    ),
                )
                
                network_container.add(network_button)
                
                # Add password entry if network is secured and not saved
                #print(ssid,is_saved)
                if is_secure and not is_saved:
                    password_box = Box(
                        name="wifi-password-box",
                        orientation="horizontal",
                        spacing=4,
                        h_align="start"
                    )
                    
                    password_entry = Entry(
                        name="wifi-password-entry",
                        placeholder_text="Password",
                        password=True,
                        h_expand=True,
                    )
                    password_entry.get_style_context().add_class("wifi-password-entry")
                    password_entry.connect("activate", lambda entry, s=ssid: self._connect_with_password(s, entry))
                    
                    cancel_btn = Button(
                        name="wifi-password-cancel",
                        label="✕",
                        on_clicked=lambda btn, container=network_container: self._hide_password_entry(container)
                    )
                    
                    password_box.children = [password_entry, cancel_btn]
                    
                    password_revealer = Revealer(
                        name="wifi-password-revealer",
                        transition_type="slide-down",
                        transition_duration=200,
                        child_revealed=False,
                    )
                    password_revealer.add(password_box)
                    
                    network_container.add(password_revealer)
                    
                    # Store revealer reference on the button for later access
                    network_button.password_revealer = password_revealer
                    network_button.password_entry = password_entry
                
                self.networks_box.add(network_container)
                #print(f"Added network button for: {ssid}")
                
            except Exception as e:
                print(f"Error adding network {network}: {e}")
                continue

    def _update_networks_list(self):
        """Update networks list (synchronous fallback)"""
        # Show loading state immediately
        for child in self.networks_box.children:
            self.networks_box.remove(child)
        
        loading = Label(
            name="wifi-loading",
            label="🔄 Loading networks..."
        )
        self.networks_box.add(loading)

    def _handle_network_click(self, ssid, is_secure, is_saved, button):
        """Handle network button click"""
        #print(f"Network clicked: {ssid}, secure: {is_secure}, saved: {is_saved}")
        
        if not is_secure:
            # Open network - connect directly
            self._connect_to_network(ssid, None)
        elif is_saved:
            # Saved network - try to connect
            self._connect_to_network(ssid, None)
        else:
            # Secured network not saved - show password entry
            if hasattr(button, 'password_revealer'):
                # Hide all other password entries first
                self._hide_all_password_entries()
                # Show this network's password entry
                button.password_revealer.set_reveal_child(True)
                
                def focus_entry():
                    try:
                        entry = button.password_entry
                        
                        # Force the popup window to accept keyboard input
                        popup_window = entry.get_toplevel()
                        if popup_window and hasattr(popup_window, 'set_accept_focus'):
                            popup_window.set_accept_focus(True)
                            popup_window.set_focus_on_map(True)
                        
                        # Make sure the popup can receive keyboard events
                        if hasattr(self.networks_popup, 'set_accept_focus'):
                            self.networks_popup.set_accept_focus(True)
                        
                        # Set entry properties
                        entry.set_can_focus(True)
                        entry.set_sensitive(True)
                        entry.set_editable(True)
                        
                        # Try to grab focus on the actual GTK window
                        gtk_window = entry.get_toplevel()
                        if gtk_window:
                            gtk_window.present()
                            gtk_window.grab_focus()
                        
                        # Now try to focus the entry
                        entry.grab_focus()
                        
                        # Alternative: try to select all text to force focus
                        try:
                            entry.select_region(0, -1)
                            entry.set_position(-1)
                        except:
                            pass
                        
                        #print(f"Focused password entry for {ssid}")
                        
                    except Exception as e:
                        print(f"Failed to focus entry: {e}")
                    return False
                
                # Longer delay to ensure everything is ready
                GLib.timeout_add(700, focus_entry)


    def _hide_all_password_entries(self):
        """Hide all password entry revealers"""
        for container in self.networks_box.children:
            if hasattr(container, 'children'):
                for child in container.children:
                    if isinstance(child, Button) and hasattr(child, 'password_revealer'):
                        child.password_revealer.set_reveal_child(False)

    def _hide_password_entry(self, container):
        """Hide password entry for a specific container"""
        for child in container.children:
            if isinstance(child, Button) and hasattr(child, 'password_revealer'):
                child.password_revealer.set_reveal_child(False)

    def _connect_with_password(self, ssid, entry):
        """Connect to network using password from entry"""
        password = entry.get_text()
        if password:
            self._connect_to_network(ssid, password)

    def _connect_to_network(self, ssid, password):
        """Connect to a network with optional password"""
        #print(f"Connecting to {ssid} with {'password' if password else 'no password'}")
        try:
            cmd = ["nmcli", "dev", "wifi", "connect", ssid]
            if password:
                cmd.extend(["password", password])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                print(f"Connected to {ssid}")
                # Hide popup on successful connection
                self.networks_popup.set_visible(False)
                GLib.timeout_add(2000, self._refresh)
            else:
                print(f"Failed to connect to {ssid}: {result.stderr}")
                
        except Exception as e:
            print(f"Connection error: {e}")

    def on_hover(self):
        try:
            self._refresh()
            self.icon.set_tooltip_text(self.current_tooltip)
        except:
            pass

    def _refresh(self):
        try:
            status, strength, tooltip = self._get_active_connection_info()
            self.current_tooltip = tooltip or "Network"
            glyph = self._map_glyph(status, strength)
            self.icon.set_label(glyph)
        except Exception as e:
            print(f"Refresh error: {e}")
        return True

    def _get_active_connection_info(self):
        """Get active connection info with minimal D-Bus calls"""
        try:
            for ac in NM.NetworkManager.ActiveConnections:
                try:
                    devices = ac.Devices
                    if not devices:
                        continue
                    dev = devices[0]
                    
                    # Try to get device type safely
                    try:
                        if hasattr(dev.DeviceType, 'variant_level'):
                            dtype = int(dev.DeviceType)
                        else:
                            dtype = int(dev.DeviceType)
                    except:
                        continue
                    
                    # Get IP safely
                    ip_addr = 'Unknown'
                    try:
                        ip4_config = dev.Ip4Config
                        if ip4_config and hasattr(ip4_config, 'AddressData') and ip4_config.AddressData:
                            ip_addr = str(ip4_config.AddressData[0]['address'])
                    except:
                        pass

                    if dtype == 2:  # WIFI
                        try:
                            ap = dev.SpecificDevice().ActiveAccessPoint
                            strength = int(getattr(ap, 'Strength', 0))
                            ssid = str(ap.Ssid) if ap and ap.Ssid else 'Unknown'
                            tooltip = f"Wi-Fi: {ssid}\nIP: {ip_addr}\nStrength: {strength}%"
                            return 'wifi', strength, tooltip
                        except:
                            return 'wifi', 0, f"Wi-Fi\nIP: {ip_addr}"

                    elif dtype == 1:  # ETHERNET
                        try:
                            iface = str(getattr(dev, 'Interface', '')) or ''
                            mode = 'tether' if 'usb' in iface.lower() else 'ethernet'
                            tooltip = f"{mode.title()}\nIP: {ip_addr}"
                            return mode, None, tooltip
                        except:
                            return 'ethernet', None, f"Ethernet\nIP: {ip_addr}"

                except Exception as e:
                    continue

        except Exception as e:
            pass

        return 'none', None, "No Connection"

    def _map_glyph(self, status: str, strength: int | None) -> str:
        """
        Maps connection status and signal strength to JetBrainsMono Nerd Font glyphs.
        """
        WIFI = {
            'empty': '󰤯', 'low': '󰤟', 'medium': '󰤢', 'high': '󰤥', 'full': '󰤨'
        }
        ETH = '󰈀'
        USB = ''
        OFF = '󰤭'

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
