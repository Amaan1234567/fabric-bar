"""holds the battery module that shows the current battery percentage
and also extra details in tooltip"""

import subprocess
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from gi.repository import GLib  # type: ignore
from loguru import logger
import psutil


class BatteryWidget(Box):
    """Battery widget that changes color based on battery percentage from green to red,
    and tells extra info in tooltips like time to charge, battery health etc
    """

    def __init__(self, interval=1, **kwargs):
        super().__init__(**kwargs)

        self.glyph_label = Label(name="battery-glyph", label="󰠠")
        self.percent_label = Label(name="battery-percent", label="100%")

        self.add(self.glyph_label)
        self.add(self.percent_label)

        self.battery_health = "Unknown"
        self.interval = interval

        self._on_upower_data(
            subprocess.getoutput(
                "upower -i /org/freedesktop/UPower/devices/battery_BAT0"
            )
        )
        self._refresh()
        GLib.timeout_add_seconds(self.interval, self._refresh)

    def _refresh(self):
        battery = psutil.sensors_battery()
        if not battery:
            self.glyph_label.set_label("󰂑")
            self.percent_label.set_label("")
            self.glyph_label.set_tooltip_text("No Battery Detected")
            return True

        self.percent = battery.percent
        self.charging = battery.power_plugged

        logger.debug(f"battery_obj obtained from psutil: {battery}")

        self.time_left = self._format_time(battery.secsleft)

        status = (
            "fully-charged"
            if self.charging and self.percent >= 99
            else "charging" if self.charging else "discharging"
        )

        glyph = self._map_glyph(self.percent, self.charging)
        percent_color = self._get_color_for_percent(self.percent)
        logger.debug(f"color interpolated based on battery %: {percent_color}")

        self.glyph_label.set_markup(
            f'<span foreground="{percent_color}">{glyph}</span>'
        )

        self.percent_label.set_markup(
            f'<span foreground="{percent_color}">{self.percent:.0f}%</span>'
        )

        tooltip = self._make_tooltip(
            status, self.percent, self.time_left, self.battery_health
        )
        self.glyph_label.set_tooltip_markup(tooltip)
        self.percent_label.set_tooltip_markup(tooltip)
        return True

    def _on_upower_data(self, output: str):
        line = output.strip()
        self._full_now = None
        self._full_design = None
        if "energy-full:" in line:
            try:
                val_str = line.split("energy-full:", 1)[1].strip().split()[0]
                self._full_now = float(val_str)
            except ValueError as e:
                logger.error("⚠️ could not parse energy-full:", e)

        if "energy-full-design:" in line:
            try:
                val_str = line.split("energy-full-design:", 1)[1].strip().split()[0]
                self._full_design = float(val_str)
            except ValueError as e:
                logger.error("⚠️ could not parse energy-full-design:", e)

        logger.debug(
            f"full_current_cap: {self._full_now}\nfull_design_cap: {self._full_design}"
        )

        if self._full_now is not None and self._full_design is not None:
            health_pct = (self._full_now / self._full_design) * 100
            self.battery_health = f"{health_pct:.1f}%"
        else:
            self.battery_health = "Unknown"

    def _map_glyph(self, percent: float, charging: bool) -> str:
        if charging:
            return "󰠠"

        glyphs = ["", "", "", "", ""]
        index = int(percent // 20)
        index = min(index, 4)
        return glyphs[index]

    def _get_color_for_percent(self, percent: float) -> str:
        """Return a pastel gradient color from red to green based on percent."""

        percent = max(0, min(percent, 100)) / 100.0

        # Pastel red (low %) to pastel green (high %)
        red_start, green_start, blue_start = (252, 56, 56)  # pastel red
        red_end, green_end, blue_end = (99, 252, 23)  # pastel green

        # Linear interpolation
        r = int(red_start + (red_end - red_start) * percent)
        g = int(green_start + (green_end - green_start) * percent)
        b = int(blue_start + (blue_end - blue_start) * percent)

        return f"#{r:02x}{g:02x}{b:02x}"

    def _format_time(self, secs: int) -> str:
        """returns the time if available in proper format"""

        if secs == psutil.POWER_TIME_UNKNOWN:
            logger.warning("psutil not able to get Power time :(")
            return "Unknown"
        if secs == psutil.POWER_TIME_UNLIMITED:
            return " "
        hours = secs // 3600
        minutes = (secs % 3600) // 60
        return f"{hours}h {minutes}m"

    def _make_tooltip(self, state: str, percent: float, time: str, health: str) -> str:
        """creates the pango markup tooltip based on battery state and returns as str"""
        percent_str = f"{percent:.0f}%"

        if state == "charging":
            color = "#a6e3a1"
            return (
                f'<b><span foreground="{color}">Charging</span></b>\n'
                f"<b>Level:</b> {percent_str}\n"
                f"<b>Time to Full:</b> <tt>{time}</tt>\n"
                f'<b>Health:</b> <span foreground="#89dceb">{health}</span>'
            )

        if state == "discharging":
            color = "#f9e2af"
            return (
                f'<b><span foreground="{color}">On Battery</span></b>\n'
                f"<b>Level:</b> {percent_str}\n"
                f"<b>Time Left:</b> <tt>{time}</tt>\n"
                f'<b>Health:</b> <span foreground="#f38ba8">{health}</span>'
            )

        if state == "fully-charged":
            color = "#94e2d5"
            return (
                f'<b><span foreground="{color}">Fully Charged</span></b>\n'
                f"<b>Level:</b> {percent_str}\n"
                f'<b>Health:</b> <span foreground="#89b4fa">{health}</span>'
            )

        return (
            f"<b>Status:</b> {state.capitalize()}\n"
            f"<b>Level:</b> {percent_str}\n"
            f'<b>Health:</b> <span foreground="#f2cdcd">{health}</span>'
        )
