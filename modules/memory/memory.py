"""holds the memory widget"""

import psutil
from gi.repository import GLib  # type: ignore

from fabric.widgets.box import Box
from fabric.widgets.label import Label
from custom_widgets.animated_circular_progress_bar import AnimatedCircularProgressBar

CONVERSION_CONST = 1073741824  # 1 Gigabyte = 1073741824 bytes


class Memory(Box):
    """memory widget, displays current memory usage"""

    def __init__(self) -> None:
        # 1px spacing, horizontal orientation
        super().__init__(orientation="h", spacing=1, name="memory")

        # Create and pack the label
        self.icon = Label("", name="memory-label")
        self.progress_bar = AnimatedCircularProgressBar(
            name="memory-progress-bar",
            child=self.icon,
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
        self.add(self.progress_bar)

        # Set up a Fabricator service to poll memory% every 500ms
        # Fabricator is a service, not a widget
        self.update_label()
        GLib.timeout_add_seconds(1, self.update_label)

    def get_memory_usage(self):
        """Return the latest memory utilization percentage."""
        return psutil.virtual_memory().percent

    def _get_details(self):
        return (psutil.virtual_memory(), psutil.swap_memory())

    def _set_tooltip(self):
        ram, swap = self._get_details()
        available_ram = f"<b>RAM usage: <span>{ram.used/CONVERSION_CONST:.2f} GB\
/{ram.total/CONVERSION_CONST:.2f} GB</span></b>\n"
        available_swap = f"<b>SWAP usage: <span>{swap.used/CONVERSION_CONST:.2f} GB\
/{swap.total/CONVERSION_CONST:.2f} GB</span></b>"
        markup = "<u>Memory Stats</u>\n" + available_ram + available_swap

        self.set_tooltip_markup(markup=markup)

    def update_label(
        self,
    ) -> bool:
        """Called by Fabricator whenever `get_memory_usage` returns a new value."""
        value = self.get_memory_usage()
        if abs(self.progress_bar.value - value) > 3:
            self.progress_bar.animate_value(value)
        self.progress_bar.set_value(value)
        self._set_tooltip()

        return True
