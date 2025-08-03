from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.circularprogressbar import CircularProgressBar
from custom_widgets.animated_circular_progress_bar import AnimatedCircularProgressBar
from fabric import Fabricator
import psutil
from time import sleep

class Cpu(Box):
    def __init__(self) -> None:
        # 1px spacing, horizontal orientation
        super().__init__(orientation="h", spacing=1,name="cpu")

        # Create and pack the label
        self.icon = Label("",name="cpu-label")
        self.progress_bar = AnimatedCircularProgressBar(name="cpu-progress-bar",child=self.icon,
            value=0,
            line_style="round",
                line_width=3,
                size=30,
                start_angle=140,
                end_angle=395,
                invert=True)
        self.add(self.progress_bar)

        # Set up a Fabricator service to poll CPU% every 500ms
        # Fabricator is a service, not a widget
        self.update_service = Fabricator(
            # milliseconds between polls
            default_value=0,            # initial value
            poll_from=lambda svc: self.get_cpu_usage(),
            stream=True,
        ).connect("changed",self.update_label)

    def get_cpu_usage(self):
        """Return the latest CPU utilization percentage."""
        while True:
            yield psutil.cpu_percent()
            sleep(1)

    def update_label(self,_, value) -> bool:
        """Called by Fabricator whenever `get_cpu_usage` returns a new value."""

        self.progress_bar.animate_value(value/100.0)
        #print(f"[Cpu] updated to {value:.1f}%")
        return True
