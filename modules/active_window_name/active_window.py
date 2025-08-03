import fabric
from fabric.hyprland.widgets import ActiveWindow
from fabric.utils import FormattedString, truncate
from fabric.widgets.box import Box
import re
from loguru import logger
from utils.variables import WINDOW_TITLE_MAP


class WindowName(Box):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)

        self.window_name = ActiveWindow(name="active-window",formatter=FormattedString(
                "{ get_title(win_title, win_class) }",
                get_title=self.get_title,
            ),)
        self.children = self.window_name
    
    def get_title(self, win_title: str, win_class: str):
        trunc = True
        trunc_size = 10
        custom_map = []
        icon_enabled = True

        win_title = truncate(win_title, trunc_size) if trunc else win_title
        merged_titles = WINDOW_TITLE_MAP + (
            custom_map if isinstance(custom_map, list) else []
        )
        for pattern, icon, name in merged_titles:
            try:
                if re.search(pattern, win_class.lower()):
                    #print(f"\n{icon} {name}" if icon_enabled else name)
                    return f"{icon} {name}" if icon_enabled else name
            except re.error as e:
                logger.warning(f"[window_title] Invalid regex '{pattern}': {e}")

        fallback = win_class.lower()
        fallback = truncate(fallback, trunc_size) if trunc else fallback
        return f"󰣆 {fallback}"