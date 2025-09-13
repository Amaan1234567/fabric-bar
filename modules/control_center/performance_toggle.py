import fabric
from fabric.widgets.button import Button
from fabric.widgets.box import Box
from fabric.widgets.label import Label
import subprocess


class PerformanceToggle(Button):
    def __init__(self, **kwargs):
        super().__init__(
            name="performance-toggle",
            v_expand=False,
            h_expand=False,
            size=[147, 10],
            **kwargs
        )
        self.status_icon_map = {"Quiet": "󰒲", "Balanced": "󰈐", "Performance": "󰿗"}
        self.modes = ["Quiet", "Balanced", "Performance"]
        self.current_mode = subprocess.getoutput(
            "asusctl profile -p | grep is | awk '{print $4}'"
        )
        self.status_idx = 0

        for i in range(len(self.modes)):
            if self.modes[i].strip() == self.current_mode:
                self.status_idx = i
                break
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

        self.connect("clicked", self.cycle_mode)

    def cycle_mode(self):
        print(self.status_idx)
        self.status_idx = (self.status_idx + 1) % 3
        self.current_mode = self.modes[self.status_idx]

        subprocess.run(
            ["asusctl", "profile", "--profile-set", self.current_mode.strip()]
        )
        self.status.set_label(self.current_mode)
