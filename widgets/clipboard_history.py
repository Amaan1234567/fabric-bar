"""widget to show clipboard history"""

import os
import re
import subprocess

from fabric.utils.helpers import exec_shell_command, exec_shell_command_async
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.entry import Entry
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.wayland import WaylandWindow as Window
from gi.repository import Gdk, GdkPixbuf  # type: ignore
from rapidfuzz.process import extract

from custom_widgets.image_rounded import CustomImage
from utils.helper_functions import truncate


class ClipboardButton(Button):
    """custom button class to store search data in button, easier for search query handling"""

    def __init__(self, id, data, image_extension=None):

        self.id = id
        self.data = data
        self.image_extension = image_extension
        if image_extension:
            loader = GdkPixbuf.PixbufLoader()
            loader.write(data)  # type: ignore
            loader.close()
            pixbuf: GdkPixbuf.Pixbuf = loader.get_pixbuf()
            pixbuf = pixbuf.scale_simple(720, 405, GdkPixbuf.InterpType.BILINEAR)

            super().__init__(
                name="clipboard-element",
                on_clicked=lambda: self._handle_button_click(
                    f'bash -c "cliphist decode {id} | wl-copy"'
                ),
                child=Box(
                    children=[
                        CustomImage(
                            name="clipboard-image", pixbuf=pixbuf, size=[720, 405]
                        )
                    ],
                    h_expand=True,
                    v_expand=True,
                    h_align="center",
                    v_align="center",
                ),
            )
        else:
            super().__init__(
                name="clipboard-element",
                child=Label(
                    label=truncate(data.strip(), 70),
                    h_align="start",
                ),
                h_align="fill",
                h_expand=True,
                on_clicked=lambda: self._handle_button_click(
                    f'bash -c "cliphist decode {id} | wl-copy"'
                ),
            )


class ClipboardHistory(Window):
    """widget to show clipboard history"""

    def __init__(self, **kwargs):
        super().__init__(
            name="clipboard-history-window",
            title="clipboard_history",
            layer="top",
            anchor="center",
            exclusivity="auto",
            keyboard_mode="exclusive",
            visible=False,
            type="top-level",
            **kwargs,
        )
        self.is_hidden = True
        if not os.path.exists("/tmp/cliphist"):
            os.mkdir("/tmp/cliphist")
        self.pattern = re.compile(
            "^([0-9]+)\\s+\\[\\[ binary.*(jpg|jpeg|png|bmp)", flags=re.MULTILINE
        )

        self.scrolled_window = ScrolledWindow(
            name="clipboard-history-scrolled-window",
            orientation="h",
            min_content_size=(740, 600),
            max_content_size=(740, 600),
        )
        self.element_box = Box(name="clipboard-history-content", orientation="v",spacing=10)
        self.search_box = Entry(
            name="clipboard-history-search-box", placeholder="Search clipboard"
        )
        self.search_box.connect("changed", self._process_search)
        self.content = Box(orientation="v", v_expand=True, h_align="fill")
        self.content.add(self.search_box)
        self.scrolled_window.add(self.element_box)
        self.content.add(self.scrolled_window)
        self.event_box = EventBox(child=self.content)
        self.event_box.connect("key-release-event", self._handle_key_press)
        self.elements = {}
        self.buttons_dict: dict[str, Button] = {}
        self.add(self.event_box)
        self._refresh_data()

    def show(self):
        super().show()
        # Ensure it has focus after showing
        self.grab_focus()

    def _handle_key_press(self, _, key: Gdk.EventKey):
        if key.keyval == Gdk.KEY_Escape:  # type: ignore
            self.toggle_window()
        return True  # Return True to indicate the event was handled

    def _process_data(
        self, data: str | bytes, id: str, image_extension: str | None = None
    ):
        if image_extension:
            self.elements[id] = f"binary image data {image_extension}"

            button = ClipboardButton(id, data, image_extension)
            self.element_box.add(button)
        elif data := str(data):
            self.elements[id] = data
            button = ClipboardButton(id, data)
            self.element_box.add(button)

    def _handle_button_click(self, cmd: str):
        # print("cmd: ",cmd)
        exec_shell_command_async(cmd)
        self.toggle_window()

    def _fetch_data(self, item: str):
        # print(item)

        if match := re.match(self.pattern, item):
            # match [0] is matched string, match[1:] are captured groups
            # print(match[1])
            id = match[1]
            image_extension = None
            try:
                image_extension = match[2]

            except IndexError:
                pass
            # print("raw image data: ",subprocess.run(["cliphist","decode",id],check=True))
            if data := subprocess.run(
                ["cliphist", "decode", id], capture_output=True, check=True
            ).stdout:
                # print("image_extension: ", image_extension)
                # print("data: ",len(data))
                self._process_data(data, id, image_extension)
        else:
            match = item.split("\t")
            id = match[0]
            if data := exec_shell_command("cliphist decode " + id):
                # print("data: ", len(data))
                self._process_data(data, id, None)

    def _refresh_data(self):
        for filename in os.listdir("/tmp/cliphist"):
            os.remove(f"/tmp/cliphist/{filename}")
        self.elements.clear()
        self.element_box.children.clear()
        self.buttons_dict.clear()
        exec_shell_command_async("cliphist list", self._fetch_data)

    def _process_search(self, entry):
        search_query = entry.get_text()
        if len(search_query):
            matches = extract(search_query, self.elements)
            print("================================")
            print(matches)
            print("================================")
            self.element_box.children.clear()
            match_ids = [match[2] for match in matches]
            for button in self.element_box.children:
                if button.id not in match_ids:
                    button.hide()
                else:
                    button.show()
        else:
            self.element_box.show_all()

    def toggle_window(self):
        """Toggle the visibility of the theme selector window."""
        if self.is_hidden:
            self._refresh_data()
            self.show()
            self.grab_focus()
        else:
            self.hide()
        self.is_hidden = not self.is_hidden
