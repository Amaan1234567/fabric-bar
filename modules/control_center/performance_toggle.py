"""holds performance toggle widget"""

from loguru import logger
from fabric.widgets.button import Button
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.power_profiles.service import PowerProfiles


class PerformanceToggle(Button):
    """widget to toggle performance mode, uses the powerprofiles service"""

    def __init__(self, **kwargs):
        super().__init__(
            name="performance-toggle",
            v_expand=False,
            h_expand=False,
            size=[147, 10],
            **kwargs,
        )
        self.service = PowerProfiles()
        self.service.connect("changed", self._update_active_mode)
        logger.debug(f"profiles: {self.service.profiles}")
        self.status_icon_map = {"power-saver": "󰒲", "balanced": "󰈐", "performance": "󰿗"}
        self.modes = ["power-saver", "balanced", "performance"]
        self.status_idx = 0
        self.current_mode = self.service.active_profile

        self.content = Box(
            orientation="v", spacing=30, h_align="center", v_align="center"
        )
        self.status = Label(
            name="status-label",
            label=self.modes[self.status_idx],
            justification="center",
            h_align="center",
        )

        self.content.add(self.status)

        self.add(self.content)

        self.connect("clicked", self._cycle_mode)
        self._update_active_mode()

    def _update_active_mode(self):
        logger.debug("performance toggle updating")
        logger.debug(f"active profile: {self.service.active_profile}")
        self.current_mode = self.service.active_profile
        for i, mode in enumerate(self.modes):
            if mode == self.current_mode:
                self.status_idx = i
                break
        self.status.set_label(self.current_mode)

    def _cycle_mode(self):
        self.status_idx = (self.status_idx + 1) % 3
        self.current_mode = self.modes[self.status_idx]
        self.service.active_profile = self.current_mode
        self.status.set_label(self.current_mode)
