"""widget to show clipboard history"""

import os
import re

from fabric.utils.helpers import exec_shell_command, exec_shell_command_async
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.entry import Entry
from fabric.widgets.eventbox import EventBox
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.wayland import WaylandWindow as Window
from gi.repository import Gdk, GdkPixbuf  # type: ignore
from rapidfuzz.process import extract


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
        self.pattern = re.compile(
            "^([0-9]+)\\s(\\[\\[\\s)?binary.*(jpg|jpeg|png|bmp)", flags=re.MULTILINE
        )

        self.content = ScrolledWindow(
            name="clipboard-history-scrolled-window",
            orientation="h",
            min_content_size=(800, 600),
            max_content_size=(800, 600),
        )
        self.element_box = Box(name="clipboard-history-content", orientation="v")
        self.search_box = Entry(
            name="clipboard-history-search-box", placeholder="Search clipboard"
        )
        self.search_box.connect("changed", self._process_search)
        self.content.add(self.search_box)
        self.content.add(self.element_box)
        self.event_box = EventBox(child=self.content)
        self.event_box.connect("key-release-event", self._handle_key_press)
        self.elements = {}
        self.buttons_list = []
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

    def _process_data(self, data: str, id: str, image_extension: str | None = None):
        if image_extension:
            self.elements[id] = f"binary image data {image_extension}"
            loader = GdkPixbuf.PixbufLoader()
            loader.write(data, 1)  # type: ignore
            loader.close()
            pixbuf: GdkPixbuf.Pixbuf = loader.get_pixbuf()
            pixbuf = pixbuf.scale_simple(720, 405, GdkPixbuf.InterpType.BILINEAR)
            button = Button(
                name="clipboard-element",
                label=f"binary image data {image_extension}",
                image=pixbuf,
                on_clicked=lambda: exec_shell_command_async(
                    f"cliphist decode {id} | wl-copy"
                ),
            )
            self.element_box.add(button)
            self.buttons_list.append(button)
        else:
            self.elements[id] = data
            button = Button(
                name="clipboard-element",
                label=data,
                on_clicked=lambda: exec_shell_command_async(
                    f"cliphist decode {id} | wl-copy"
                ),
            )
            self.element_box.add(button)
            self.buttons_list.append(button)

    def _fetch_data(self, list_data: str):
        items = list_data.split("\n")
        print("cliphist items: ", items)
        for item in items:
            if match := re.match(self.pattern, item):
                # match [0] is matched string, match[1:] are captured groups
                id = match[1]
                image_extension = None
                try:
                    image_extension = match[3]

                except IndexError:
                    pass
                print(match[1])
                if data := exec_shell_command("cliphist decode " + id):
                    self._process_data(data, id, image_extension)

    def _refresh_data(self):
        for filename in os.listdir("/tmp/cliphist"):
            os.remove(f"/tmp/cliphist/{filename}")
        self.elements.clear()
        self.element_box.children.clear()
        self.buttons_list.clear()
        exec_shell_command_async("cliphist list", self._fetch_data)

    def _process_search(self, entry):
        matches = extract(entry.get_text(), self.elements)
        print(self.elements)
        print(matches)

    def toggle_window(self):
        """Toggle the visibility of the theme selector window."""
        if self.is_hidden:
            self._refresh_data()
            self.show()
            self.grab_focus()
        else:
            self.hide()
        self.is_hidden = not self.is_hidden
