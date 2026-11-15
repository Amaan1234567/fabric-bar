"""A wallpaper selector widget that allows users to preview and
apply different wallpapers for their desktop background.
"""

import os
from threading import Thread

from fabric.utils.helpers import cooldown, exec_shell_command_async, monitor_file
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.wayland import WaylandWindow as Window
from gi.repository import Gdk, GLib  # type: ignore
from loguru import logger
from PIL import Image
from screeninfo import get_monitors

from services.background_op_service import BackgroundOpService

scale_map = {
    1920: 1280,
    2560: 1080,
    3840: 2560,
}


class WallpaperButton(Button):
    """button widget for wallpapers."""

    def __init__(self, wallpaper_folder, child, wallpaper_name, **kwargs):
        super().__init__(
            name="wallpaper-button",
            child=child,
            on_clicked=self._change_wallpaper,
            **kwargs,
        )

        self.wallpaper_folder = wallpaper_folder
        self.wallpaper_name = wallpaper_name

    def _change_wallpaper(self):
        logger.info(f"changing wallpaper: {self.wallpaper_name}")
        exec_shell_command_async(
            f"bash -c 'scripts/switch_wallpaper.sh {self.wallpaper_folder + self.wallpaper_name}'"
        )


class WallpaperSelector(Window):
    """wallpaper selector widget."""

    def __init__(self, **kwargs):
        monitor = get_monitors()[0]
        self.screen_width = monitor.width
        self.screen_height = monitor.height
        self.preview_target_width = int(scale_map[self.screen_width] * 0.2)
        self.preview_target_height = int(scale_map[self.screen_width] * (9 / 16))
        super().__init__(
            name="wallpaper-selector-window",
            title="wallpaper-selector",
            layer="top",
            anchor="center",
            exclusivity="auto",
            keyboard_mode="on-demand",
            visible=False,
            type="top-level",
            **kwargs,
        )

        # To this (let CSS control min-width/height, or use set_size_request safely):
        self.content = Box(
            name="main-wallpaper-container",
            h_expand=True,
            v_expand=True,
        )
        self.content.set_size_request(
            self.preview_target_width * 5 + 130, 
            self.preview_target_height + 55
        )
        self.wallpaper_folder = f"{os.environ.get('HOME')}/Pictures/backgrounds/"
        self.cache_folder = f"{os.environ.get('HOME')}/.cache/wallpapers_cache/"
        os.makedirs(self.cache_folder, exist_ok=True)
        
        self.cache_available = len(os.listdir(self.cache_folder)) != 0
        self.wallpapers = os.listdir(self.wallpaper_folder)
        self.cache = os.listdir(self.cache_folder)

        self.wallpaper_folder_monitor = monitor_file(
            self.wallpaper_folder,
            self._process_wallpaper_handler,
            flags="watch-moves",
            initial_call=True,
        )

        self.scrolling_container = ScrolledWindow(
            name="wallpaper-scroll-container", h_expand=True
        )
        self.scrolling_container.set_can_focus(False)

        self.event_box = EventBox(child=self.scrolling_container, h_expand=True)
        self.event_box.set_can_focus(False)
        self.connect("key-press-event", self._handle_key_press)

        self.buttons_box = Box(
            name="wallpapers-container", orientation="h", spacing=20, h_expand=True
        )

        # REMOVED the bad background thread spawning _create_buttons() here!
        # _process_new_wallpaper_handler (via monitor_file initial_call=True) 
        # will handle checking/processing and call _create_buttons safely on main thread.

        self.scrolling_container.children = [self.buttons_box]

        self.content.add(self.event_box)
        self.children = [self.content]
        self.is_hidden = True

    @cooldown(1)
    def _process_wallpaper_handler(self):
        Thread(target=self._process_new_wallpapers, daemon=True).start()

    def _handle_key_press(self, _, key: Gdk.EventKey):
        if key.keyval == Gdk.KEY_Escape:  # type: ignore
            self.toggle_window()
            return True
        elif key.keyval == Gdk.KEY_Right:  # type: ignore
            self._navigate_buttons(1)
            return True
        elif key.keyval == Gdk.KEY_Left:  # type: ignore
            self._navigate_buttons(-1)
            return True
        return False

    def _navigate_buttons(self, direction: int):
        """Custom keyboard navigation for buttons box."""
        buttons = self.buttons_box.children
        if not buttons:
            return

        current_idx = -1
        for i, btn in enumerate(buttons):
            if btn.has_focus():
                current_idx = i
                break

        if current_idx == -1:
            target_idx = 0
        else:
            target_idx = max(0, min(len(buttons) - 1, current_idx + direction))

        buttons[target_idx].grab_focus()

    def _process_new_wallpapers(self):
        self.wallpapers = os.listdir(self.wallpaper_folder)
        self.cache = os.listdir(self.cache_folder)
        logger.info("detected change in wallpaper folder, checking for new wallpapers")
        
        unprocessed_wallpapers = [
            wallpaper for wallpaper in self.wallpapers if wallpaper not in self.cache
        ]
        
        if len(unprocessed_wallpapers) > 0:
            service = BackgroundOpService()
            background_op = service.set_background_op(
                "wallpaper_cache_build", "building wallpaper cache", 0
            )
            total_work = len(unprocessed_wallpapers)
            for i, wallpaper in enumerate(unprocessed_wallpapers):
                self._process_wallpaper(wallpaper)
                GLib.idle_add(background_op.set_progress, ((i + 1) / total_work) * 100)
                GLib.idle_add(background_op.set_display_text, f"processing {wallpaper}")
                logger.debug(f"wallpaper_cache_progress: {((i + 1) / total_work) * 100}")

        self.cache_available = True
        # Always trigger button creation on the main thread via GLib.idle_add
        GLib.idle_add(self._create_buttons)
        return True

    def _process_wallpaper(self, wallpaper: str):
        scaled_wallpaper = Image.open(self.wallpaper_folder + wallpaper).resize(
            (
                scale_map[self.screen_width],
                int(scale_map[self.screen_width] * (9 / 16)),
            ),
            Image.Resampling.BILINEAR,
        )
        left = scaled_wallpaper.size[0] // 2 - int(scaled_wallpaper.size[0] * 0.2)
        right = scaled_wallpaper.size[0] // 2 + int(scaled_wallpaper.size[0] * 0.2)
        bottom = scaled_wallpaper.size[1]
        top = 0
        cropped_image = scaled_wallpaper.crop((left, top, right, bottom))
        cropped_image.save(self.cache_folder + wallpaper)

    def _create_buttons(self):
        """Runs strictly on the main thread when scheduled by GLib.idle_add."""
        # Clear existing children safely
        for child in list(self.buttons_box.children):
            self.buttons_box.remove(child)
            child.destroy()

        images = sorted(
            filter(lambda name: ".gif" not in name, os.listdir(self.cache_folder))
        )

        if not images:
            temp_label = Label(
                name="loading-label",
                label="No wallpapers found...",
                h_align="center",
                v_align="center",
                h_expand=True,
                v_expand=True,
            )
            self.buttons_box.add(temp_label)
            return

        for image_file_name in images:
            image = Box(
                name="wallpaper-thumnail",
                h_expand=True,
                v_expand=True,
            )
            image.set_style(
                f"""border-radius: 12px;
                padding:0px;
                margin:0px;
                background-image: url('file://{self.cache_folder + image_file_name}');""",
                compile=False,
            )
            box = Box(
                name="wallpaper-container",
                orientation="v",
                children=[image],
                h_expand=True,
                v_expand=True,
                h_align="center",
                v_align="center",
            )
            button = WallpaperButton(
                wallpaper_folder=self.wallpaper_folder,
                wallpaper_name=image_file_name,
                child=box,
            )
            button.connect("clicked", lambda _: self.toggle_window())
            self.buttons_box.add(button)

        if not self.is_hidden and self.buttons_box.children:
            self.buttons_box.children[0].grab_focus()

    def toggle_window(self):
        """Function to toggle window."""
        if self.is_hidden:
            self.show()
            GLib.idle_add(self._activate_focus)
        else:
            self.hide()
        self.is_hidden = not self.is_hidden

    def _activate_focus(self):
        for child in self.buttons_box.children:
            if isinstance(child, WallpaperButton):
                child.grab_focus()
                break
        return GLib.SOURCE_REMOVE