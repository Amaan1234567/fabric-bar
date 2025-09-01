from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.circularprogressbar import CircularProgressBar
from custom_widgets.animated_circular_progress_bar import AnimatedCircularProgressBar
from fabric import Fabricator
import psutil
from time import sleep

from gi.repository import GLib

class Memory(Box):
    def __init__(self) -> None:
        # 1px spacing, horizontal orientation
        super().__init__(orientation="h", spacing=1,name="memory")

        # Create and pack the label
        self.icon = Label("",name="memory-label")
        self.progress_bar = AnimatedCircularProgressBar(name="memory-progress-bar",child=self.icon,
            value=0,
            line_style="round",
                line_width=4,
                size=35,
                start_angle=140,
                end_angle=395,
                invert=True)
        self.add(self.progress_bar)

        # Set up a Fabricator service to poll memory% every 500ms
        # Fabricator is a service, not a widget
        self.update_label()
        GLib.timeout_add_seconds(1,self.update_label)

    def get_memory_usage(self):
        """Return the latest memory utilization percentage."""
        return psutil.virtual_memory().percent

    def update_label(self,) -> bool:
        """Called by Fabricator whenever `get_memory_usage` returns a new value."""
        value = self.get_memory_usage()
        self.progress_bar.animate_value(value/100.0)
        #print(f"[memory] updated to {value:.1f}%")
        return True
