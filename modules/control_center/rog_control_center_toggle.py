from fabric.widgets.button import Button
from fabric.widgets.image import Image
from fabric.widgets.svg import Svg
from fabric.utils import cooldown
import subprocess


class ROGButton(Button):
    def __init__(self):
        # Let Fabric handle SVG scaling automatically
        rog_icon = Svg(
            name="rog-icon",
            svg_file="assets/rog-icon.svg",
            size=35,  # This will scale the SVG properly
            h_align="center",
            v_align="center",
            style = " * {stroke-width: 2px;}"
        )
        super().__init__(
            name="rog-button", 
            child=rog_icon,
            on_clicked=self._launch_rog_center,
        )

        self.set_hexpand(True)
        self.set_vexpand(False)
        self.set_tooltip_text("Open ROG Control Center")
        
        # Add hover cursor
        self.connect(
            "state-flags-changed",
            lambda btn, *_: (
                btn.set_cursor("pointer")
                if btn.get_state_flags() & 2  # type: ignore
                else btn.set_cursor("default"),
            ),
        )

    @cooldown(1)
    def _launch_rog_center(self, button):
        """Launch ROG Control Center"""
        try:
            subprocess.Popen([
                "bash", "-c", "rog-control-center & disown"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            #print("ROG Control Center launched")
        except Exception as e:
            print(f"Failed to launch ROG Control Center: {e}")
