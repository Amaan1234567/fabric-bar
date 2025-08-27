from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric import Fabricator
from gi.repository import GLib
import psutil
import re
import subprocess

class BatteryWidget(Box):
    def __init__(self, interval=1, **kwargs):
        super().__init__(**kwargs)
        
        self.glyph_label = Label(name="battery-glyph", label="󰠠")
        self.percent_label = Label(name="battery-percent", label="100%")
        
        self.add(self.glyph_label)
        self.add(self.percent_label)

        self.battery_health = "Unknown"
        self.interval = interval

        self._on_upower_data(subprocess.getoutput("upower -i /org/freedesktop/UPower/devices/battery_BAT0"))
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
        #print(battery)
        self.time_left = self._format_time(battery.secsleft)

        status = (
            "fully-charged" if self.charging and self.percent >= 99
            else "charging" if self.charging
            else "discharging"
        )

        glyph = self._map_glyph(self.percent, self.charging)
        percent_color = self._get_color_for_percent(self.percent)
        #print(percent_color)
        self.glyph_label.set_markup(f'<span foreground="{percent_color}">{glyph}</span>')

        self.percent_label.set_markup(f'<span foreground="{percent_color}">{self.percent:.0f}%</span>')

        tooltip = self._make_tooltip(status, self.percent, self.time_left, self.battery_health)
        self.glyph_label.set_tooltip_markup(tooltip)
        self.percent_label.set_tooltip_markup(tooltip)
        return True

    def _on_upower_data(self, output):
        line = output.strip()
        #print("starting: \n",line,"\nending...\n")
        self._full_now = None
        self._full_design = None
        if "energy-full:" in line:
            # split off everything after the colon,
            # strip spaces, then take the first token (the number)
            try:
                val_str = line.split("energy-full:", 1)[1].strip().split()[0]
                self._full_now = float(val_str)
                #print(self._full_now,self._full_design)
            except Exception as e:
                print("⚠️ could not parse energy-full:", e)

        if "energy-full-design:" in line:
            try:
                val_str = line.split("energy-full-design:", 1)[1].strip().split()[0]
                self._full_design = float(val_str)
                #print(self._full_now,self._full_design)
            except Exception as e:
                print("⚠️ could not parse energy-full-design:", e)

        # 2) When we have both values, compute health
        # print(self._full_now,self._full_design)
        if self._full_now is not None and self._full_design is not None:
            health_pct = (self._full_now / self._full_design) * 100
            self.battery_health = f"{health_pct:.1f}%"
        else:
            self.battery_health = "Unknown"

    def _map_glyph(self, percent: float, charging: bool) -> str:
        glyphs = ["", "", "", "", ""]
        index = int(percent // 20)
        index = min(index, 4)
        if charging:
            return "󰠠"
        return glyphs[index]

    def _get_color_for_percent(self, percent: float) -> str:
        """Return a pastel gradient color from red to green based on percent."""
        # Clamp percent between 0 and 100
        percent = max(0, min(percent, 100)) / 100.0

        # Pastel red (low %) to pastel green (high %)
        red_start, green_start, blue_start = (252, 56, 56)  # pastel red
        red_end, green_end, blue_end = (99, 252, 23)        # pastel green

        # Linear interpolation
        r = int(red_start   + (red_end   - red_start)   * percent)
        g = int(green_start + (green_end - green_start) * percent)
        b = int(blue_start  + (blue_end  - blue_start)  * percent)

        return f"#{r:02x}{g:02x}{b:02x}"


    def _format_time(self, secs: int) -> str:
        if secs in (psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN):
            return "Unknown"
        hours = secs // 3600
        minutes = (secs % 3600) // 60
        return f"{hours}h {minutes}m"

    def _make_tooltip(self, state, percent, time, health):
        color = (
            "#a6e3a1" if state == "charging"
            else "#f9e2af" if state == "discharging"
            else "#94e2d5"
        )
        percent_str = f"{percent:.0f}%"

        if state == "charging":
            return f"""
<b><span foreground="{color}">Charging</span></b>
<b>Level:</b> {percent_str}
<b>Time to Full:</b> <tt>{time}</tt>
<b>Health:</b> <span foreground="#89dceb">{health}</span>
""".strip()

        elif state == "discharging":
            return f"""
<b><span foreground="{color}">On Battery</span></b>
<b>Level:</b> {percent_str}
<b>Time Left:</b> <tt>{time}</tt>
<b>Health:</b> <span foreground="#f38ba8">{health}</span>
""".strip()

        elif state == "fully-charged":
            return f"""
<b><span foreground="{color}">Fully Charged</span></b>
<b>Level:</b> {percent_str}
<b>Health:</b> <span foreground="#89b4fa">{health}</span>
""".strip()

        return f"""
<b>Status:</b> {state.capitalize()}
<b>Level:</b> {percent_str}
<b>Health:</b> <span foreground="#f2cdcd">{health}</span>
""".strip()
