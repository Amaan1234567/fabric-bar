"""holds screen corners widget"""

from fabric.widgets.box import Box
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.overlay import Overlay
from custom_widgets.side_corner import SideCorner


class ScreenCorners(Window):
    """A window that displays all four corners."""

    def __init__(self, **kwargs):

        size = [40, 40]
        super().__init__(
            name="corners",
            layer="top",
            anchor="top bottom left right",
            exclusivity="auto",
            pass_through=True,
            type="top-level",
            visible=False,
            all_visible=False,
            **kwargs,
        )

        self.all_corners = Box(
            orientation="v",
            children=[
                Box(name="screen-padding-top", size=[-1, 1]),
                Box(
                    name="all-corners",
                    orientation="h",
                    h_expand=True,
                    v_expand=True,
                    h_align="fill",
                    v_align="fill",
                    children=[
                        Box(
                            orientation="h",
                            children=[
                                Box(name="screen-padding-left", size=[1, -1]),
                                Box(
                                    name="left-corners",
                                    orientation="v",
                                    h_align="fill",
                                    children=[
                                        SideCorner("top-left", size),
                                        Box(v_expand=True),
                                        SideCorner("bottom-left", size),
                                    ],
                                ),
                            ],
                        ),
                        Box(h_expand=True, name="middle-area"),
                        Box(
                            orientation="h",
                            children=[
                                Box(
                                    name="right-corners",
                                    orientation="v",
                                    h_align="fill",
                                    children=[
                                        SideCorner("top-right", size),
                                        Box(v_expand=True),
                                        SideCorner("bottom-right", size),
                                    ],
                                ),
                                Box(name="screen-padding-right", size=[1, -1]),
                            ],
                        ),
                    ],
                ),
                Box(name="screen-padding-bottom", size=[-1, 1]),
            ],
        )
        self.overlay = Overlay(child=self.all_corners,overlays=Box(name="corners-overlay",h_expand=True,v_expand=True))
        # self.add(self.all_corners)
        self.add(self.overlay)

        self.show_all()
