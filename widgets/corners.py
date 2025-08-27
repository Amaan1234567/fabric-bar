from typing import Iterable
from fabric.widgets.box import Box
from fabric.widgets.wayland import WaylandWindow as Window

from custom_widgets.side_corner import SideCorner


class ScreenCorners(Window):
    """A window that displays all four corners."""

    def __init__(self,**kwargs):
        

        size = [40,40]
        super().__init__(
            name="corners",
            layer="top",
            anchor="top bottom left right",
            exclusivity="none",
            pass_through=True,
            visible=False,
            all_visible=False,
            **kwargs,
        )

        self.all_corners = Box(
            name="all-corners",
            orientation="v",
            h_expand=True,
            v_expand=True,
            h_align="fill",
            v_align="fill",
            children=[
                Box(
                    name="top-corners",
                    orientation="h",
                    h_align="fill",
                    children=[
                        SideCorner("top-left", size),
                        Box(h_expand=True),
                        SideCorner("top-right", size),
                    ],
                ),
                Box(v_expand=True,name="middle-area"),
                Box(
                    name="bottom-corners",
                    orientation="h",
                    h_align="fill",
                    children=[
                        SideCorner("bottom-left", size),
                        Box(h_expand=True),
                        SideCorner("bottom-right", size),
                    ],
                ),
            ],
        )

        self.add(self.all_corners)

        self.show_all()