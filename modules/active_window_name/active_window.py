"""
Module for displaying the active window name in Hyprland.

This module provides a widget that displays the title of the currently active
window, along with an optional icon and a fallback mechanism for unknown
window classes.
"""

import re

from typing import Tuple, List
from fabric.hyprland.widgets import ActiveWindow
from fabric.utils import FormattedString, truncate
from fabric.widgets.box import Box
from loguru import logger
from utils.variables import WINDOW_TITLE_MAP


class WindowName(Box):
    """
    A widget that displays the active window's title, optionally with an icon.
    """

    def __init__(self, **kwargs):
        """
        Initializes the WindowName widget.

        Args:
            **kwargs: Keyword arguments to pass to the parent Box class.
        """
        super().__init__(**kwargs)

        self.window_name = ActiveWindow(
            name="active-window",
            formatter=FormattedString(
                "{ get_title(win_title, win_class) }",
                get_title=self.get_title,
            ),
        )
        self.children = [self.window_name]

    def get_title(self, win_title: str, win_class: str) -> str:
        """
        Gets the title to display for the active window.

        This function attempts to match the window class against a list
        of predefined patterns. If a match is found, it returns an icon
        and a name. Otherwise, it returns a fallback with the window class.

        Args:
            win_title (str): The title of the window.
            win_class (str): The class of the window.

        Returns:
            str: The formatted title to display.
        """
        trunc = True
        trunc_size = 10
        custom_map: List[Tuple[str, str, str]] = []  # Corrected type
        icon_enabled = True

        win_title = truncate(win_title, trunc_size) if trunc else win_title
        merged_titles: List[Tuple[str, str, str] | List[str]] = WINDOW_TITLE_MAP + (
            custom_map if isinstance(custom_map, list) else []
        )
        for pattern, icon, name in merged_titles:
            try:
                if re.search(pattern, win_class.lower()):
                    # print(f"\n{icon} {name}" if icon_enabled else name)
                    return f"{icon} {name}" if icon_enabled else name
            except re.error as e:
                logger.warning(f"[window_title] Invalid regex '{pattern}': {e}")

        fallback = win_class.lower()
        fallback = truncate(fallback, trunc_size) if trunc else fallback
        return f"󰣆 {fallback}"
