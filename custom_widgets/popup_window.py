"""
This module defines the PopupWindow class, a custom Wayland window
designed to function as a popup, often used for menus or tooltips.
It positions itself relative to a parent window and optionally points
to a specific widget.
"""

from typing import Tuple, Union, Optional
from fabric.widgets.wayland import WaylandWindow
from gi.repository import Gtk, GtkLayerShell


class PopupWindow(WaylandWindow):
    """
    A Wayland-based popup window that can be positioned relative to a parent
    window and optionally point to a specific widget.
    """

    def __init__(
        self,
        parent: WaylandWindow,
        pointing_to: Optional[Gtk.Widget] = None,
        margin: Union[Tuple[int, ...], str] = "0px 0px 0px 0px",
        **kwargs,
    ):
        """
        Initializes a new PopupWindow instance.

        Args:
            parent (WaylandWindow): The parent Wayland window. The popup will
                be positioned relative to this window.
            pointing_to (Gtk.Widget, optional): The widget that the popup
                should point to. Defaults to None.
            margin (Union[Tuple[int, ...], str], optional): The margin around
                the popup. Can be a tuple of integers (top, right, bottom, left)
                or a string in the format "top right bottom left".
                Defaults to "0px 0px 0px 0px".
            **kwargs: Additional keyword arguments to pass to the
                WaylandWindow constructor.
        """
        super().__init__(**kwargs)
        self.exclusivity = "none"

        self._parent: WaylandWindow = parent
        self._pointing_widget: Optional[Gtk.Widget] = pointing_to
        self._base_margin = self.extract_margin(margin)
        self.margin: Tuple[int, ...] = tuple(self._base_margin.values())
        self.title: str = "fabric-popup"

        self.connect("notify::visible", self.do_update_handlers)

    def get_coords_for_widget(self, widget: Gtk.Widget) -> Tuple[int, int]:
        """
        Calculates the coordinates of a widget relative to the toplevel
        window.

        Args:
            widget (Gtk.Widget): The widget to get the coordinates of.

        Returns:
            Tuple[int, int]: A tuple containing the x and y coordinates
                of the widget's center, relative to the toplevel window.
        """
        if not ((toplevel := widget.get_toplevel()) and toplevel.is_toplevel()):  # type: ignore
            return 0, 0
        allocation = widget.get_allocation()
        x, y = widget.translate_coordinates(toplevel, allocation.x, allocation.y) or (
            0,
            0,
        )
        return round(x / 2), round(y / 2)

    def set_pointing_to(self, widget: Optional[Gtk.Widget]) -> bool:
        """
        Sets the widget that the popup should point to.

        If a previous pointing widget was set, it disconnects the
        "size-allocate" signal handler from it.

        Args:
            widget (Gtk.Widget, optional): The widget to point to.
                If None, the popup will no longer point to any widget.

        Returns:
            bool: The return value of `do_update_handlers`.
        """
        if self._pointing_widget:
            try:
                self._pointing_widget.disconnect_by_func(self.do_handle_size_allocate)
            except Exception:
                pass
        self._pointing_widget = widget
        return self.do_update_handlers()

    def do_update_handlers(self, *_):
        """
        Updates the signal handlers for size allocation based on the
        visibility of the popup and the presence of a pointing widget.
        """
        if not self._pointing_widget:
            return

        if not self.get_visible():
            try:
                self._pointing_widget.disconnect_by_func(self.do_handle_size_allocate)
                self.disconnect_by_func(self.do_handle_size_allocate)
            except Exception:
                pass
            return

        self._pointing_widget.connect("size-allocate", self.do_handle_size_allocate)
        self.connect("size-allocate", self.do_handle_size_allocate)

        return self.do_handle_size_allocate()

    def do_handle_size_allocate(self, *_):
        """
        Handles the size allocation event, recalculating and repositioning
        the popup.
        """
        return self.do_reposition(self.do_calculate_edges())

    def do_calculate_edges(self) -> str:
        """
        Calculates which axis (x or y) the popup should move on based on
        the parent window's anchor.

        Returns:
            str: "x" if the popup should move horizontally, "y" if it
                should move vertically.
        """
        move_axe = "x"
        parent_anchor = self._parent.anchor

        if len(parent_anchor) != 3:
            return move_axe

        if (
            GtkLayerShell.Edge.LEFT in parent_anchor
            and GtkLayerShell.Edge.RIGHT in parent_anchor
        ):
            # horizontal -> move on x-axies
            move_axe = "x"
            if GtkLayerShell.Edge.TOP in parent_anchor:
                self.anchor = "left top"
            else:
                self.anchor = "left bottom"
        elif (
            GtkLayerShell.Edge.TOP in parent_anchor
            and GtkLayerShell.Edge.BOTTOM in parent_anchor
        ):
            # vertical -> move on y-axies
            move_axe = "y"
            if GtkLayerShell.Edge.RIGHT in parent_anchor:
                self.anchor = "top right"
            else:
                self.anchor = "top left"

        return move_axe

    def do_reposition(self, move_axe: str):
        """
        Repositions the popup based on the parent window's margins,
        the pointing widget's coordinates (if any), and the calculated
        movement axis.

        Args:
            move_axe (str): The axis ("x" or "y") to move the popup on.
        """
        parent_margin = self._parent.margin
        parent_x_margin, parent_y_margin = parent_margin[0], parent_margin[3]

        height = self.get_allocated_height()
        width = self.get_allocated_width()

        if self._pointing_widget:
            coords = self.get_coords_for_widget(self._pointing_widget)
            coords_centered = (
                round(coords[0] + self._pointing_widget.get_allocated_width() / 2),
                round(coords[1] + self._pointing_widget.get_allocated_height() / 2),
            )
        else:
            coords_centered = (
                round(self._parent.get_allocated_width() / 2),
                round(self._parent.get_allocated_height() / 2),
            )

        self.margin = tuple(
            a + b
            for a, b in zip(
                (
                    (
                        0,
                        0,
                        0,
                        round((parent_x_margin + coords_centered[0]) - (width / 2)),
                    )
                    if move_axe == "x"
                    else (
                        round((parent_y_margin + coords_centered[1]) - (height / 2)),
                        0,
                        0,
                        0,
                    )
                ),
                self._base_margin.values(),
            )
        )
