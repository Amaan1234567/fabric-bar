"""holds the wallpaper change button"""

from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.utils import cooldown, exec_shell_command_async


class GamemodeToggleButton(Button):
    """widget that triggers wallpaper change"""

    def __init__(self):
        # Let Fabric handle SVG scaling automatically
        self.icon = Label(
            name="gamemode-icon",
            label="󰡈",  # This will scale the SVG properly
            h_align="center",
            v_align="center",
        )
        super().__init__(
            name="gamemode-toggle-button",
            child=self.icon,
            on_clicked=self._toggle_gamemode,
        )
        self.get_style_context().add_class("gamemode-off")
        self.set_hexpand(True)
        self.set_vexpand(False)
        self.set_tooltip_text("set random wallpaper")
        self.is_on = False

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
    def _toggle_gamemode(self, _):
        """Launch ROG Control Center"""
        ctx = self.get_style_context()
        if self.is_on:
            ctx.add_class("gamemode-off")
            ctx.remove_class("gamemode-on")
        else:
            print("adding class")
            ctx.add_class("gamemode-on")
            ctx.remove_class("gamemode-off")
        self.is_on = not self.is_on
        exec_shell_command_async('bash -c "./scripts/gamemode.sh"')
