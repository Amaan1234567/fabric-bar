"""Singleton that ensures only one popup is visible at a time."""

from gi.repository import GLib #type: ignore


class _PopupManager:
    """Tracks the currently-visible popup and hides it when a new one requests focus."""

    def __init__(self):
        self._current_popup = None
        self._current_widget = None  # the bar widget that owns the current popup

    def request_show(self, popup, owner):
        """Called by a widget when it wants to show its popup.

        If a different popup is already visible, hide it first.

        Args:
            popup: The PopupWindow to show.
            owner: The bar widget (Cpu, Memory, etc.) that owns this popup.
        """
        if self._current_popup is popup:
            return  # already showing — nothing to do

        # hide the previous popup immediately
        if self._current_popup is not None and self._current_popup.get_visible():
            self._hide(self._current_popup, self._current_widget)

        popup.set_visible(True)
        popup.overlay_revealer.set_reveal_child(True)
        self._current_popup = popup
        self._current_widget = owner

    def request_hide(self, popup, _):
        """Called when a popup actually hides — clears the reference so
        the next request_show doesn't try to hide an already-hidden popup."""
        if self._current_popup is popup:
            self._current_popup = None
            self._current_widget = None

    @staticmethod
    def _hide(popup, owner):
        popup.overlay_revealer.set_reveal_child(False)
        GLib.timeout_add(250, popup.set_visible, False)
        # also cancel any pending hide timeout on the owner
        if hasattr(owner, "_cancel_hide_timeout"):
            owner._cancel_hide_timeout()


# module-level singleton — every widget imports this same instance
popup_manager = _PopupManager()
