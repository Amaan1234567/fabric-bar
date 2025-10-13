"""
This module defines the CustomImage widget, which extends the Image widget
from the fabric library to add rounded corners to the image.
"""

from typing import cast
import math
import cairo
from fabric.widgets.image import Image
from gi.repository import Gtk


class CustomImage(Image):
    """
    A custom image widget with rounded corners.
    """

    def do_render_rectangle(
        self, cr: cairo.Context, width: int, height: int, radius: int = 0
    ) -> None:
        """
        Renders a rounded rectangle path on the given cairo context.

        Args:
            cr (cairo.Context): The cairo context to draw on.
            width (int): The width of the rectangle.
            height (int): The height of the rectangle.
            radius (int): The radius of the rounded corners. Defaults to 0.
        """
        cr.move_to(radius, 0)
        cr.line_to(width - radius, 0)
        cr.arc(width - radius, radius, radius, -(math.pi / 2), 0)
        cr.line_to(width, height - radius)
        cr.arc(width - radius, height - radius, radius, 0, (math.pi / 2))
        cr.line_to(radius, height)
        cr.arc(radius, height - radius, radius, (math.pi / 2), math.pi)
        cr.line_to(0, radius)
        cr.arc(radius, radius, radius, math.pi, (3 * (math.pi / 2)))
        cr.close_path()

    def do_draw(self, cr: cairo.Context) -> None:
        """
        Draws the image with rounded corners on the given cairo context.

        Args:
            cr (cairo.Context): The cairo context to draw on.
        """
        context = self.get_style_context()
        width, height = self.get_allocated_width(), self.get_allocated_height()
        cr.save()

        self.do_render_rectangle(
            cr,
            width,
            height,
            cast(int, context.get_property("border-radius", Gtk.StateFlags.NORMAL)),  # type: ignore
        )
        cr.clip()
        Image.do_draw(self, cr)  # pylint: disable=no-member

        cr.restore()
