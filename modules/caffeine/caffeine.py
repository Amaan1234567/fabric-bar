"""holds the caffeine widget"""

from fabric.widgets.button import Button
from fabric.utils.helpers import exec_shell_command, exec_shell_command_async, cooldown


class Caffeine(Button):
    """Caffeine widget, when toggled disables hypridle"""

    def __init__(self, **kwargs):
        super().__init__(
            name="caffeine-button", label="󰾪", on_clicked=self._toggle, **kwargs
        )
        print(not exec_shell_command("pgrep -x hypridle").strip().isdigit())
        self.is_enabled = not exec_shell_command("pgrep -x hypridle").strip().isdigit()  # type: ignore
        self.set_hexpand(True)
        self.set_vexpand(False)
        # self.ctx = self.get_style_context()
        # self.ctx.add_class("caffeine-off")
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
        self._set_ui()

    def _set_ui(self):
        if self.is_enabled:
            self.set_label("󰅶")
        else:
            self.set_label("󰾪")

    @cooldown(0.3)
    def _toggle(self):
        if self.is_enabled:
            self.is_enabled = False
            self.set_label("󰾪")
            exec_shell_command_async("hypridle & disown")
            self.set_tooltip_text("sleep(hypridle) enabled")
        else:
            self.is_enabled = True
            self.set_label("󰅶")
            exec_shell_command_async("pkill hypridle")
            self.set_tooltip_text("sleep(hypridle) disabled")
