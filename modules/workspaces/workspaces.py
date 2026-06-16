"""contains the workspaces widget"""

from fabric.core.widgets import WorkspaceButton
from fabric.hyprland.widgets import (
    HyprlandWorkspaces as FabricHyprlandWorkspaces,
)


class HyprlandWorkspaces(FabricHyprlandWorkspaces):
    """Hyprland workspaces widget"""

    def do_action_next(self):
        return self.connection.send_command(
            f'batch/dispatch hl.dsp.focus({{ workspace = "{"e" if not self._empty_scroll else ""}+1" }})' # pylint: disable=line-too-long
        )

    def do_action_previous(self):
        return self.connection.send_command(
            f'batch/dispatch hl.dsp.focus({{ workspace = "{"e" if not self._empty_scroll else ""}-1" }})' # pylint: disable=line-too-long
        )

    def do_button_clicked(self, button):
        return self.connection.send_command(
            f'batch/dispatch hl.dsp.focus({{ workspace = "{button.id}" }})'
        )


class CustomWorkspaces(HyprlandWorkspaces):
    """Hyprland workspaces widget"""

    def __init__(self, **kwargs):

        super().__init__(
            name="workspaces",
            spacing=4,
            buttons_factory=self._setup_button,
            **kwargs,
        )

    def _setup_button(self, ws_id: int) -> WorkspaceButton:
        button = WorkspaceButton(
            style_classes="workspace-button",
            id=ws_id,
            label=f"{ws_id}",
        )
        return button
