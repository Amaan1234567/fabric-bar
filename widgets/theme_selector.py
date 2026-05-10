import os
from re import search
import shutil
import subprocess
from loguru import logger
from gi.repository import Gdk
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.eventbox import EventBox
from fabric.widgets.entry import Entry
from fabric.utils.helpers import exec_shell_command, cooldown

# Configuration
# Update path to be relative to your project root or use an absolute path
COLORS_CSS_PATH = os.path.expanduser("~/Documents/fabric-bar/styles/colors.css")
BACKUP_CSS_PATH = COLORS_CSS_PATH + ".bak"


def get_themes():
    result = subprocess.run(
        ["wallust", "theme", "--help"], capture_output=True, text=True
    )
    output = result.stdout
    start = output.find("[possible values: ")
    end = output.find("]", start)
    themes_str = output[start + 18 : end]
    return [t.strip() for t in themes_str.split(",")]


class ThemeSelector(Window):
    """"""

    def __init__(self, **kwargs):
        super().__init__(
            name="theme-selector-window",
            title="theme_selector",
            layer="top",
            anchor="center",
            exclusivity="auto",
            keyboard_mode="exclusive",
            visible=False,
            type="top-level",
            **kwargs,
        )

        self.backup_created = False
        self.themes = get_themes()
        logger.info(f"Available themes: {self.themes}")
        self.content = Box(name="main-theme-container", orientation="v", spacing=10)
        self.scrolling = ScrolledWindow(name="themes-scroll")
        self.theme_box = Box(name="themes-container", orientation="v")
        self.search_entry = Entry(placeholder="Search a theme...", name="search-entry")
        self.search_entry.connect("changed", self._on_search_changed)
        self.content.add(self.search_entry)

        for theme in self.themes:
            # We use on_enter_notify_event to trigger a preview while hovering
            btn = Button(label=theme)
            btn.connect(
                "focus-in-event",
                lambda *args, t=theme: self.preview_theme(t),
            )
            btn.connect("clicked", lambda *args, t=theme: self.apply_theme(t))
            self.theme_box.add(btn)

        self.scrolling.add(self.theme_box)
        self.content.add(self.scrolling)

        self.event_box = EventBox(child=self.content)
        self.event_box.connect("key-release-event", self._handle_key_press)

        self.children = [self.event_box]
        self.is_hidden = True

    def _on_search_changed(self, entry):
        search_text = entry.get_text().capitalize()
        for btn in self.theme_box.get_children():
            theme_name = btn.get_label()
            if search_text in theme_name:
                btn.show()
            else:
                btn.hide()

    def show(self):
        super().show()
        # Ensure it has focus after showing
        self.grab_focus()

    def _handle_key_press(self, _, key: Gdk.EventKey):
        if key.keyval == Gdk.KEY_Escape:
            self.revert()
            self.toggle_window()
        elif key.keyval == Gdk.KEY_Return:
            self.confirm()
        return True  # Return True to indicate the event was handled

    def ANSI_to_HEX(self, ansi_color):
        # Remove ANSI escape codes and convert to HEX
        # print("ansi_color:",ansi_color)
        ansi_color_array = (
            ansi_color.replace("\x1b[48;2", "").replace("\x1b[49m", "")
            .replace("m", "")
            .strip()
            .split(";")[1:]
        )
        print("ansi_color_array:", ansi_color_array)
        int_color = 1
        for i, val in enumerate(ansi_color_array):
            int_color *= int(val)
        r, g, b = map(int, ansi_color_array)
        # print("color_code:", color_code)
        return f'#{r:02x}{g:02x}{b:02x}'

    def apply_color_scheme(self, theme):
        theme_schema = f""":vars {{
    --cursor: lighter({theme[12]});
    --background: darker({theme[0]});
    --foreground: lighter({theme[12]});
    --color0:  {theme[0]};
    --color1:  {theme[1]};
    --color2:  {theme[2]};
    --color3:  {theme[3]};
    --color4:  {theme[4]};
    --color5:  {theme[5]};
    --color6:  {theme[6]};
    --color7:  {theme[7]};
    --color8:  {theme[8]};
    --color9:  {theme[9]};
    --color10: {theme[10]};
    --color11: {theme[11]};
    --color12: {theme[12]};
    --color13: {theme[13]};
    --color14: {theme[14]};
    --color15: {theme[15]};
    --backgroundWaybar: alpha({theme[0]},0.65);
}}"""
        with open(COLORS_CSS_PATH, "w") as f:
            f.write(theme_schema)

    @cooldown(0.2)
    def preview_theme(self, theme):
        if not self.backup_created and os.path.exists(COLORS_CSS_PATH):
            shutil.copy2(COLORS_CSS_PATH, BACKUP_CSS_PATH)
            self.backup_created = True

        # Apply theme
        # If preview is True, it runs with --preview, otherwise standard
        cmd = ["wallust", "theme", theme, "--preview"]
        output = subprocess.run(cmd, capture_output=True, text=True)
        print(output.stdout)
        print("obtained theme: ",repr(output.stdout))
        theme = [
            self.ANSI_to_HEX(color) for color in output.stdout.split("    ")[:-1] if color
        ]
        print("theme:", theme)
        self.apply_color_scheme(theme)

    def apply_theme(self, theme):
        exec_shell_command(f"wallust theme {theme}")
        self.toggle_window()

    def revert(self):
        if self.backup_created and os.path.exists(BACKUP_CSS_PATH):
            shutil.move(BACKUP_CSS_PATH, COLORS_CSS_PATH)
            self.backup_created = False

    def confirm(self):
        if self.backup_created and os.path.exists(BACKUP_CSS_PATH):
            os.remove(BACKUP_CSS_PATH)
            self.backup_created = False
        self.toggle_window()

    def toggle_window(self):
        if self.is_hidden:
            self.show()
            self.grab_focus()
        else:
            self.hide()
        self.is_hidden = not self.is_hidden
