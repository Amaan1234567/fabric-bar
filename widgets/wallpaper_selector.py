import os
from screeninfo import get_monitors
from gi.repository import Gdk
from PIL import Image
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.eventbox import EventBox
from fabric.utils.helpers import exec_shell_command_async
from helpers.helper_functions import truncate

scale_map = {
    1920: 1280,
    2560: 1080,
    3840: 2560,
}

class wallpaperButton(Button):
    def __init__(self,wallpaper_folder,child,wallpaper_name,parent, **kwargs):
        super().__init__(name="wallpaper-button",
                child=child,
                on_clicked=self._change_wallpaper,**kwargs)
        
        self.wallpaper_folder = wallpaper_folder
        self.wallpaper_name = wallpaper_name
        self.parent = parent

    def _change_wallpaper(self,*args):
        print(f"changing wallpaper: {self.wallpaper_name}")
        exec_shell_command_async(f"bash -c 'scripts/switch_wallpaper.sh {self.wallpaper_folder+self.wallpaper_name}'")
        self.parent.toggle_window()    
class WallpaperSelector(Window):
    """wallpaper selector widget"""

    def __init__(self, **kwargs):
        monitor = get_monitors()[0]
        self.screen_width = monitor.width
        self.screen_height = monitor.height
        self.preview_target_width = int(scale_map[self.screen_width] * 0.2)
        self.preview_target_height = int(scale_map[self.screen_width] * (9 / 16))

        super().__init__(
            name="wallpaper-selector-window",
            title="wallpaper-selector",
            layer="overlay",
            anchor="center",
            exclusivity="auto",
            keyboard_mode="on-demand",
            visible=False,
            type="popup",
            **kwargs,
        )

        self.content = Box(
            name="main-wallpaper-container",
            h_expand=True,
            v_expand=True,
            size=[self.preview_target_width * 5, self.preview_target_height + 55],
        )
        self.wallpaper_folder = f"{os.environ.get('HOME')}/Pictures/backgrounds/"
        self.cache_folder = f"{os.environ.get('HOME')}/.cache/wallpapers_cache/"
        self.wallpapers = os.listdir(self.wallpaper_folder)
        self.cache = os.listdir(self.cache_folder)
        self._process_new_wallpapers()
        self.scrolling_container = ScrolledWindow(
            name="wallpaper-scroll-container",
            # max_content_size=[
            #     self.preview_target_width * 5,
            #     self.preview_target_height,
            # ],
        )
        self.event_box = EventBox(child=self.scrolling_container)
        self.event_box.connect("key-release-event", self._handle_key_press)

        self.buttons_box = Box(name="wallpapers-container", orientation="h", spacing=20)
        self._create_buttons()

        self.scrolling_container.children = [self.buttons_box]

        self.content.add(self.event_box)
        self.children = [self.content]
        self.is_hidden = True

    def _handle_key_press(self, _, key: Gdk.EventKey):
        if key.keyval == Gdk.KEY_Escape:  # type: ignore
            self.toggle_window()

    def _process_new_wallpapers(self):
        for wallpaper in self.wallpapers:
            if wallpaper not in self.cache:
                self._process_wallpaper(wallpaper)

    def _process_wallpaper(self, wallpaper: str):
        scaled_wallpaper = Image.open(self.wallpaper_folder + wallpaper).resize(
            (
                scale_map[self.screen_width],
                int(scale_map[self.screen_width] * (9 / 16)),
            ),
            Image.Resampling.BILINEAR,
        )
        left = scaled_wallpaper.size[0] // 2 - int(scaled_wallpaper.size[0] * 0.1)
        right = scaled_wallpaper.size[0] // 2 + int(scaled_wallpaper.size[0] * 0.1)
        bottom = scaled_wallpaper.size[1]
        top = 0
        cropped_image = scaled_wallpaper.crop((left, top, right, bottom))
        cropped_image.save(self.cache_folder + wallpaper)

    def _create_buttons(self):
        # print(os.listdir(self.cache_folder))
        images = sorted(filter(lambda name: ".gif" not in name, os.listdir(self.cache_folder)))

        for image_file_name in images:
            print(image_file_name)
            image = Box(
                name="wallpaper-thumnail",
                # size=[self.preview_target_width, self.preview_target_height],
                h_expand=True,
                v_expand=True,
            )
            image.set_style(
                f"""border-radius: 10px;
                padding:0px;
                background-image: url('file://{self.cache_folder + image_file_name}');""",
                compile=False,
            )
            label = Label(label=truncate(image_file_name), name="wallpaper-label")
            box = Box(
                name="wallpaper-container",
                orientation="v",
                children=[image, label],
                spacing=5,
                h_align="center",
                v_align="center",
            )
            button = wallpaperButton(
                wallpaper_folder=self.wallpaper_folder,
                wallpaper_name=image_file_name,
                child=box,
                parent=self
            )
            self.buttons_box.add(button)

    def toggle_window(self):
        """function to toggle window"""
        if self.is_hidden:
            self.show_all()
            self.grab_focus()
        else:
            self.hide()
        self.is_hidden = not self.is_hidden
