"""
Module that holds the Side Corner Class which displays the corner widgets of the ui
"""
from fabric.widgets.box import Box
from fabric.widgets.shapes import Corner


class SideCorner(Box):
    """A container for a corner shape."""

    def __init__(self, corner, size):
        super().__init__(
            name="corner-container",
            children=Corner(
                name="corner",
                orientation=corner,
                size=size,
            ),
        )
