"""holds the wallpaper change button"""
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.utils import cooldown, exec_shell_command_async

class WallpaperChangeButton(Button):
    """widget that triggers wallpaper change"""
    def __init__(self):
        # Let Fabric handle SVG scaling automatically
        self.icon = Label(
            name="wallpaper-icon",
            label = "",  # This will scale the SVG properly
            h_align="center",
            v_align="center",
        )
        super().__init__(
            name="wallpaper-change-button",
            child=self.icon,
            on_clicked=self._change_wallpaper,
        )

        self.set_hexpand(True)
        self.set_vexpand(False)
        self.set_tooltip_text("set random wallpaper")

        # Add hover cursor
        self.connect(
            "state-flags-changed",
            lambda btn, *_: (
                (
                    btn.set_cursor("pointer")
                    if btn.get_state_flags() & 2  # type: ignore
                    else btn.set_cursor("default")
                ),
            ),
        )


    @cooldown(1)
    def _change_wallpaper(self, _):
        """Launch ROG Control Center"""
        exec_shell_command_async("bash -c \"~/Scripts/wallpaper_change.sh\"")
