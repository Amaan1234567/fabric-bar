import fabric
from fabric.widgets.box import Box
from fabric.hyprland.widgets import WorkspaceButton, Workspaces

class CustomWorkspaces(Box):
    def __init__(self,**kwargs):
        super().__init__(name="workspaces",**kwargs)

        def create_workspace_label(ws_id: int) -> str:
            return ""

        def setup_button(ws_id: int) -> WorkspaceButton:
            button = WorkspaceButton(
                style_classes="workspace-button",
                id=ws_id,
                label=f"{ws_id}",
            )
            return button

        # Create a HyperlandWorkspace widget to manage workspace buttons
        self.workspace = Workspaces(
            name="workspaces",
            spacing=4,
            # Factory function to create buttons for each workspace
            buttons_factory=setup_button,
        )

        # Add the HyperlandWorkspace widget as a child
        self.children = self.workspace