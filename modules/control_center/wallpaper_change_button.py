from fabric.widgets.button import Button
from fabric.widgets.image import Image
from fabric.widgets.svg import Svg
from fabric.utils import cooldown
import subprocess
import os
import re

from gi.repository import GLib

class WallpaperChangeButton(Button):
    def __init__(self):
        # Let Fabric handle SVG scaling automatically
        self.icon = Svg(
            name="wallpaper-icon",
            svg_file="assets/wallpaper-svgrepo-com.svg",
            size=30,  # This will scale the SVG properly
            h_align="center",
            v_align="center",
            style = " * {stroke-width: 2px;}"
        )
        super().__init__(
            name="wallpaper-change-button", 
            child=self.icon,
            on_clicked=self._change_wallpaper,
        )

        self.set_hexpand(True)
        self.set_vexpand(False)
        self.set_tooltip_text("set random wallpaper")
        
        # Add hover cursor
        self.connect(
            "state-flags-changed",
            lambda btn, *_: (
                btn.set_cursor("pointer")
                if btn.get_state_flags() & 2  # type: ignore
                else btn.set_cursor("default"),
            ),
        )

        self.background=""

        GLib.timeout_add(1000,self._refresh)
    
    def _refresh(self):
        self._get_background_from_css()
        self._update_svg_color()
    
    def _get_background_from_css(self):
        """Get background value from colors.css file"""
        css_file_path = "colors.css"
        default_color = "#F3E3BC"  # Fallback background value
        
        if not os.path.exists(css_file_path):
            return default_color
        
        try:
            with open(css_file_path, 'r') as file:
                css_content = file.read()
            
            # Look for @define-color background #HEXCODE;
            background_pattern = r'@define-color\s+background\s+([^;]+);'
            match = re.search(background_pattern, css_content)
            
            if match:
                color_value = match.group(1).strip()
                #print(f"Found background: {color_value}")
                return color_value
            else:
                print("background not found in CSS, using default")
                return default_color
                
        except Exception as e:
            print(f"Error reading colors.css: {e}")
            return default_color

    def _update_svg_color(self):
        """Update SVG color to background"""
        try:
            # Apply background to the SVG
            #print(self.background)
            #print("color: "+self.background + ";")
            self.icon.set_style(style="stroke: "+self.background + ";")
            #print(f"Updated SVG color to: {self.background}")
        except Exception as e:
            print(f"Error updating SVG color: {e}")


    @cooldown(1)
    def _change_wallpaper(self, button):
        """Launch ROG Control Center"""
        try:
            subprocess.Popen([
                "bash", "-c", "~/Scripts/wallpaper_change.sh & disown"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            #print("ROG Control Center launched")
        except Exception as e:
            print(f"Failed to launch ROG Control Center: {e}")
