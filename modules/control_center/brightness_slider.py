import fabric
from fabric.widgets.box import Box
from fabric.widgets.scale import Scale
from fabric.widgets.label import Label
from fabric.widgets.button import Button
import subprocess
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


class BrightnessSlider(Box):
    def __init__(self):
        super().__init__(
            name="brightness-slider-container",
            orientation="vertical",
            spacing=8,
        )
        
        # Flag to prevent recursive brightness setting
        self._updating_brightness = False
        
        # Header with icon and label
        self.header_box = Box(
            name="brightness-header-box",
            orientation="horizontal",
            spacing=8,
        )
        
        self.brightness_icon = Label(
            name="brightness-icon",
            label="󰃞",  # Default brightness icon
        )
        
        self.brightness_label = Label(
            name="brightness-label",
            label="Brightness",
        )
        
        self.percentage_label = Label(
            name="brightness-percentage-label",
            label="",
        )
        
        self.header_box.children = [
            self.brightness_icon,
            self.brightness_label,
            self.percentage_label,
        ]
        
        # Get current brightness first
        current_brightness = self.get_current_brightness()
        
        # Brightness slider - initialize with current brightness to avoid triggering change
        self.brightness_scale = Scale(
            name="brightness-scale",
            orientation="horizontal",
            min=5,  # Minimum 5% to avoid complete darkness
            max=100,
            value=current_brightness,  # Set to current brightness immediately
            step=5,
            on_value_changed=self.on_brightness_change,
        )
        
        # Quick preset buttons
        self.presets_box = Box(
            name="brightness-presets-box",
            orientation="horizontal",
            spacing=4,
        )
        
        self.preset_25 = Button(
            name="brightness-preset-25",
            label="25%",
            on_clicked=lambda btn: self.set_brightness(25),
        )
        
        self.preset_50 = Button(
            name="brightness-preset-50",
            label="50%",
            on_clicked=lambda btn: self.set_brightness(50),
        )
        
        self.preset_75 = Button(
            name="brightness-preset-75",
            label="75%",
            on_clicked=lambda btn: self.set_brightness(75),
        )
        
        self.preset_100 = Button(
            name="brightness-preset-100",
            label="100%",
            on_clicked=lambda btn: self.set_brightness(100),
        )
        
        self.presets_box.children = [
            self.preset_25,
            self.preset_50,
            self.preset_75,
            self.preset_100,
        ]
        
        self.children = [
            self.header_box,
            self.brightness_scale,
            self.presets_box,
        ]
        
        # Initialize current brightness (update UI only, don't change system brightness)
        self.update_current_brightness_ui_only()
    
    def get_current_brightness(self):
        """Get current screen brightness"""
        try:
            # Try different methods to get brightness
            methods = [
                ["brightnessctl", "-P", "get"],
                ["light", "-G"],
                ["xbacklight", "-get"],
            ]
            
            for method in methods:
                try:
                    result = subprocess.run(
                        method, 
                        capture_output=True, 
                        text=True
                    )
                    
                    if result.returncode == 0:
                        brightness = float(result.stdout.strip())
                        # Ensure brightness is in 0-100 range
                        if method[0] == "light":
                            brightness = max(0, min(100, brightness))
                        return max(5, int(brightness))  # Ensure minimum 5%
                except:
                    continue
            
            return 50  # Default fallback
        except:
            return 50
    
    def set_brightness(self, value):
        """Set screen brightness"""
        # Prevent recursive calls
        if self._updating_brightness:
            return
            
        self._updating_brightness = True
        
        try:
            # Ensure value is within bounds
            value = max(5, min(100, int(value)))
            
            # Try different methods to set brightness
            methods = [
                ["brightnessctl", "set", f"{value}%"],
                ["light", "-S", str(value)],
                ["xbacklight", "-set", str(value)],
            ]
            
            success = False
            for method in methods:
                try:
                    result = subprocess.run(method, capture_output=True)
                    if result.returncode == 0:
                        success = True
                        break
                except:
                    continue
            
            if success:
                # Update UI only after successful brightness change
                self.brightness_scale.value = value
                self.percentage_label.label = f"{value}%"
                self.update_brightness_icon(value)
                
        except Exception as e:
            print(f"Failed to set brightness: {e}")
        finally:
            self._updating_brightness = False
    
    def update_brightness_icon(self, brightness_value):
        """Update brightness icon based on brightness level"""
        # Use different Nerd Font icons for different brightness levels
        if brightness_value >= 80:
            self.brightness_icon.label = "󰃠"  # High brightness
            self.brightness_icon.get_style_context().add_class("brightness-high")
            self.brightness_icon.get_style_context().remove_class("brightness-medium")
            self.brightness_icon.get_style_context().remove_class("brightness-low")
        elif brightness_value >= 40:
            self.brightness_icon.label = "󰃟"  # Medium brightness
            self.brightness_icon.get_style_context().add_class("brightness-medium")
            self.brightness_icon.get_style_context().remove_class("brightness-high")
            self.brightness_icon.get_style_context().remove_class("brightness-low")
        else:
            self.brightness_icon.label = "󰃞"  # Low brightness
            self.brightness_icon.get_style_context().add_class("brightness-low")
            self.brightness_icon.get_style_context().remove_class("brightness-high")
            self.brightness_icon.get_style_context().remove_class("brightness-medium")
    
    def update_current_brightness_ui_only(self):
        """Update UI with current brightness without changing system brightness"""
        current = self.get_current_brightness()
        
        # Set flag to prevent triggering brightness change
        self._updating_brightness = True
        
        try:
            self.brightness_scale.value = current
            self.percentage_label.label = f"{current}%"
            self.update_brightness_icon(current)
        finally:
            self._updating_brightness = False
    
    def on_brightness_change(self, scale):
        """Handle brightness slider change"""
        # Don't process if we're updating programmatically
        if self._updating_brightness:
            return False
            
        brightness = int(scale.value)
        
        # Use a small delay to avoid rapid changes while dragging
        if hasattr(self, '_brightness_timeout'):
            GLib.source_remove(self._brightness_timeout)
        
        self._brightness_timeout = GLib.timeout_add(100, lambda: self.set_brightness(brightness))
        
        # Update UI immediately for responsiveness
        self.percentage_label.label = f"{brightness}%"
        self.update_brightness_icon(brightness)
        
        return False
