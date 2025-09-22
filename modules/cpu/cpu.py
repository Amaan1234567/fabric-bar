from encodings import utf_8
from venv import logger
import psutil
import re
import os

from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.svg import Svg
from fabric.utils import monitor_file,get_relative_path
from gi.repository import GLib
from custom_widgets.animated_circular_progress_bar import AnimatedCircularProgressBar


class Cpu(Box):
    def __init__(self) -> None:
        # 1px spacing, horizontal orientation
        super().__init__(orientation="h", name="cpu")

        # Create and pack the SVG icon
        self.icon = Svg(
            svg_file="assets/cpu-svgrepo-com.svg",
            name="cpu-label",
            size=20,
            h_align="center",
            v_align="center",
        )

        self.progress_bar = AnimatedCircularProgressBar(
            name="cpu-progress-bar",
            child=self.icon,
            value=0,
            line_style="round",
            line_width=4,
            size=35,
            start_angle=140,
            end_angle=395,
            invert=True,
            min_value = 0.0,
            max_value = 100.0
        )
        self.add(self.progress_bar)

        # Get color6 from CSS
        self.color6 = self._get_color6_from_css()

        self.update_label()
        # Set up a Fabricator service to poll CPU% every 500ms
        GLib.timeout_add_seconds(1, self.update_label)
        #monitor_file("../../styles/colors.css",self._update_svg_color,initial_call=True)

    def _get_color6_from_css(self):
        """Get color6 value from colors.css file"""
        css_file_path = get_relative_path("../../styles/colors.css")
        default_color = "#F3E3BC"  # Fallback color6 value

        if not os.path.exists(css_file_path):
            return default_color

        try:
            with open(css_file_path, "r",encoding="utf-8") as file:
                css_content = file.read()

            # Look for @define-color color6 #HEXCODE;
            color6_pattern = r"@define-color\s+color6\s+([^;]+);"
            match = re.search(color6_pattern, css_content)

            if match:
                color_value = match.group(1).strip()
                # print(f"Found color6: {color_value}")
                return color_value
            else:
                print("color6 not found in CSS, using default")
                return default_color

        except Exception as e:
            print(f"Error reading colors.css: {e}")
            return default_color

    def _update_svg_color(self):
        """Update SVG color to color6"""
        try:
            # Apply color6 to the SVG
            # print(self.color6)
            logger.info(f"color retrieved from colors.css for CPU widget: {self.color6};")
             # Update SVG color to color6 every update
            self.color6 = self._get_color6_from_css()
            self.icon.set_style(style="stroke: " + self.color6 + ";")
            # print(f"Updated SVG color to: {self.color6}")
            return True
        except Exception as e:
            print(f"Error updating SVG color: {e}")

    def get_cpu_usage(self):
        """Return the latest CPU utilization percentage."""
        return psutil.cpu_percent()

    def update_label(
        self,
    ) -> bool:
        """Called by Fabricator whenever get_cpu_usage returns a new value."""
        # Update progress bar
        value = self.get_cpu_usage()
        self._update_svg_color()
        if abs(self.progress_bar.value - value) > 2:
            self.progress_bar.animate_value(value)
        self.progress_bar.set_value(value)

        return True
