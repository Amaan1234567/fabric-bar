"""has the CPU widget"""

import psutil


from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay
from gi.repository import GLib  # type: ignore
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

    def _get_details(self):
        return (
            psutil.cpu_freq(),
            psutil.cpu_percent(percpu=True),
            psutil.sensors_temperatures()["coretemp"][0],
            psutil.sensors_fans()['asus'][0]
        )

    def _set_tooltip(self):
        cur_freq, per_core_usage, cpu_temp, cpu_fan_speed = self._get_details()
        bar_length = "▁▂▃▄▅▆▇█"

        usage_txt = "<tt>Core usage: <span>"
        for core in per_core_usage:
            usage_txt += bar_length[int((core / 100) * 8) - 1]
        usage_txt += "</span></tt>\n"
        if cur_freq.current <= 1000:
            color = "#A3DC9A"
        elif cur_freq.current > 1000 and cur_freq.current < 3500:
            color = "#FCF67E"
        else:
            color = "#FF5454"

        cpu_freq = f'Frequency: <span foreground="{color}">\
            {cur_freq.current/1000 :.2f} GHz</span>\n'
        temp_color = ""

        if cpu_temp.current <= 45:
            temp_color = "#A3DC9A"
        elif cpu_temp.current > 45 and cpu_temp.current <= 75:
            temp_color = "#FCF67E"
        else:
            temp_color = "#FF5454"

        temp_txt = f'Temp: <span foreground="{temp_color}">{cpu_temp.current}°C</span>\n'

        fan_speed_txt = f"CPU Fan Speed: {cpu_fan_speed.current}"
        markup = "<u><b>CPU Stats</b></u>\n" + cpu_freq + usage_txt + temp_txt + fan_speed_txt

        self.set_tooltip_markup(markup=markup)

    def update_label(
        self,
    ) -> bool:
        """Called by Fabricator whenever get_cpu_usage returns a new value."""
        # Update progress bar
        value = self.get_cpu_usage()
        if abs(self.progress_bar.value - value) > 3:
            self.progress_bar.animate_value(value)
        self.progress_bar.set_value(value)
        self._set_tooltip()
        return True
