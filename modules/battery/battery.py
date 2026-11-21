"""Holds the battery module that shows the current battery percentage
and also extra details in tooltip.
"""

from fabric.widgets.box import Box
from fabric.widgets.label import Label
from loguru import logger

from services.system_service import SystemService, UPowerDevice, UPowerDeviceState


class BatteryWidget(Box):
    """Battery widget that changes color based on battery percentage from green to red,
    and tells extra info in tooltips like time to charge, battery health etc.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.service = SystemService()
        self.glyph_label = Label(name="battery-glyph", label="󰠠")
        self.percent_label = Label(name="battery-percent", label="100%")

        self.add(self.glyph_label)
        self.add(self.percent_label)

        # Subscribe to SystemService battery updates (adjust signal name/args to your Service API)
        self.service.battery_info_update.connect(self._on_battery_info_update)

        self._refresh()

    def _on_battery_info_update(self, *_) -> None:
        self._refresh()

    def _refresh(self) -> bool:
        device: UPowerDevice | None = getattr(
            self.service.power, "primary_battery", None
        )
        if device is None:
            self.glyph_label.set_label("󰂑")
            self.percent_label.set_label("")
            self.glyph_label.set_tooltip_text("No Battery Detected")
            self.percent_label.set_tooltip_text("No Battery Detected")
            return True

        logger.debug(f"UPower battery device: {device}")

        self.percent = device.percentage
        self.battery_health = self._compute_health(device)
        plugged_in = self.service.power.is_plugged_in
        self.charging = plugged_in or device.state in (
            UPowerDeviceState.CHARGING,
            UPowerDeviceState.PENDING_CHARGE,
            UPowerDeviceState.FULLY_CHARGED,
        )
        if device.state == UPowerDeviceState.FULLY_CHARGED or (
            self.charging and self.percent > 99
        ):
            status = "fully-charged"
            secs = 0
        elif self.charging:
            status = "charging"
            secs = device.time_to_full
        elif device.state == UPowerDeviceState.DISCHARGING:
            status = "discharging"
            secs = device.time_to_empty
        else:
            status = device.state.name.lower().replace("_", "-")
            secs = (
                device.time_to_empty
                if device.time_to_empty > 0
                else device.time_to_full
            )

        self.time_left = self._format_time(secs, status)

        glyph = self._map_glyph(self.percent, self.charging)
        percent_color = self._get_color_for_percent(self.percent)
        logger.debug(f"color interpolated based on battery %: {percent_color}")

        self.glyph_label.set_markup(
            f'<span foreground="{percent_color}">{glyph}</span>'
        )
        self.percent_label.set_markup(
            f'<span foreground="{percent_color}">{self.percent:.0f}%</span>'
        )
        voltage_line = f"<tt>{device.voltage:.2f} V</tt>" if device.voltage > 0 else ""
        tooltip = self._make_tooltip(
            status, self.percent, self.time_left, self.battery_health, voltage_line
        )
        self.glyph_label.set_tooltip_markup(tooltip)
        self.percent_label.set_tooltip_markup(tooltip)
        return True

    def _compute_health(self, device: UPowerDevice) -> str:
        if device.energy_full > 0 and device.energy_full_design > 0:
            health_pct = (device.energy_full / device.energy_full_design) * 100
            logger.debug(
                f"full_current_cap: {device.energy_full} Wh | "
                f"full_design_cap: {device.energy_full_design} Wh"
            )
            return f"{health_pct:.1f}%"
        if device.capacity > 0:
            return f"{device.capacity:.1f}%"
        return "Unknown"

    def _map_glyph(self, percent: float, charging: bool) -> str:
        if charging:
            return "󰠠"

        glyphs = ["", "", "", "", ""]
        index = min(int(percent // 20), 4)
        return glyphs[index]

    def _get_color_for_percent(self, percent: float) -> str:
        """Return a pastel gradient color from red to green based on percent."""
        percent = max(0, min(percent, 100)) / 100.0

        # Pastel red (low %) to pastel green (high %)
        red_start, green_start, blue_start = (252, 56, 56)
        red_end, green_end, blue_end = (99, 252, 23)

        r = int(red_start + (red_end - red_start) * percent)
        g = int(green_start + (green_end - green_start) * percent)
        b = int(blue_start + (blue_end - blue_start) * percent)

        return f"#{r:02x}{g:02x}{b:02x}"

    def _format_time(self, secs: int, status: str) -> str:
        """Returns remaining/charge time in a readable format."""
        if status == "fully-charged":
            return " "
        if secs <= 0:
            logger.warning("UPower reported no time estimate (0s)")
            return "Unknown"
        hours = secs // 3600
        minutes = (secs % 3600) // 60
        return f"{hours}h {minutes}m"

    def _make_tooltip(
        self, state: str, percent: float, time: str, health: str, voltage: str
    ) -> str:
        """Creates the pango markup tooltip based on battery state and returns as str."""
        percent_str = f"{percent:.0f}%"

        if state == "charging":
            color = "#a6e3a1"
            return (
                f'<b><span foreground="{color}">Charging</span></b>\n'
                f"<b>Level:</b> {percent_str}\n"
                f"<b>Time to Full:</b> <tt>{time}</tt>\n"
                f'<b>Health:</b> <span foreground="#89dceb">{health}</span>\n'
                f'<b>Voltage:</b> <span foreground="#06B6D4">{voltage}</span>'
            )

        if state == "discharging":
            color = "#f9e2af"
            return (
                f'<b><span foreground="{color}">On Battery</span></b>\n'
                f"<b>Level:</b> {percent_str}\n"
                f"<b>Time Left:</b> <tt>{time}</tt>\n"
                f'<b>Health:</b> <span foreground="#f38ba8">{health}</span>\n'
                f'<b>Voltage:</b> <span foreground="#06B6D4">{voltage}</span>'
            )

        if state == "fully-charged":
            color = "#94e2d5"
            return (
                f'<b><span foreground="{color}">Fully Charged</span></b>\n'
                f"<b>Level:</b> {percent_str}\n"
                f'<b>Health:</b> <span foreground="#89b4fa">{health}</span>\n'
                f'<b>Voltage:</b> <span foreground="#06B6D4">{voltage}</span>'
            )

        return (
            f"<b>Status:</b> {state.capitalize()}\n"
            f"<b>Level:</b> {percent_str}\n"
            f'<b>Health:</b> <span foreground="#f2cdcd">{health}</span>'
        )
