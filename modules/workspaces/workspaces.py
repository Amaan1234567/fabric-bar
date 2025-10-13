"""contains the workspaces widget"""

from fabric.core.widgets import WorkspaceButton
from fabric.hyprland.widgets import HyprlandWorkspaces as Workspaces


class CustomWorkspaces(Workspaces):
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
