"""has the CPU widget"""

import psutil


from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay
from gi.repository import GLib # type: ignore
from custom_widgets.animated_circular_progress_bar import AnimatedCircularProgressBar


class Cpu(Box):
    """CPU widget, shows current usage %"""

    def __init__(self) -> None:
        # 1px spacing, horizontal orientation
        super().__init__(orientation="h", name="cpu")

        # Create and pack the SVG icon
        self.icon = Label(
            label="",
            name="cpu-label",
            size=20,
            h_align="center",
            v_align="center",
        )

        self.progress_bar = AnimatedCircularProgressBar(
            name="cpu-progress-bar",
            value=0,
            line_style="round",
            line_width=4,
            size=35,
            start_angle=140,
            end_angle=395,
            invert=True,
            min_value=0.0,
            max_value=100.0,
        )
        self.overlay = Overlay(
            child=self.progress_bar, overlays=self.icon, name="cpu-overlay"
        )
        self.add(self.overlay)

        self.update_label()
        # Set up a Fabricator service to poll CPU% every 500ms
        GLib.timeout_add_seconds(1, self.update_label)

    def get_cpu_usage(self):
        """Return the latest CPU utilization percentage."""
        return psutil.cpu_percent()

    def update_label(
        self,
    ) -> bool:
        """Called by Fabricator whenever get_cpu_usage returns a new value."""
        # Update progress bar
        value = self.get_cpu_usage()
        if abs(self.progress_bar.value - value) > 3:
            self.progress_bar.animate_value(value)
        self.progress_bar.set_value(value)

        return True
