"""widget to show clipboard history"""

import re
import subprocess
from concurrent.futures import ThreadPoolExecutor

from fabric.utils.helpers import exec_shell_command_async
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.entry import Entry
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.wayland import WaylandWindow as Window
from gi.repository import Gdk, GdkPixbuf, GLib  # type: ignore
from rapidfuzz.process import extract

from custom_widgets.image_rounded import CustomImage
from utils.helper_functions import truncate


class ClipboardButton(Button):
    """custom button class to store search data in button, easier for search query handling"""

    def __init__(
        self,
        item_id: str,
        data: str | GdkPixbuf.Pixbuf,
        image_extension: str | None = None,
    ):
        self.id = item_id
        self.data = data
        self.image_extension = image_extension

        if image_extension and isinstance(data, GdkPixbuf.Pixbuf):
            super().__init__(
                name="clipboard-element",
                on_clicked=lambda _btn: self._handle_button_click(
                    f'bash -c "cliphist decode {item_id} | wl-copy"'
                ),
                child=Box(
                    children=[
                        CustomImage(
                            name="clipboard-image", pixbuf=data, size=[720, 405]
                        )
                    ],
                    h_expand=True,
                    v_expand=True,
                    h_align="center",
                    v_align="center",
                ),
            )
        else:
            text_data = data if isinstance(data, str) else ""
            super().__init__(
                name="clipboard-element",
                child=Label(
                    label=truncate(text_data.strip(), 70),
                    h_align="start",
                ),
                h_align="fill",
                h_expand=True,
                on_clicked=lambda _btn: self._handle_button_click(
                    f'bash -c "cliphist decode {item_id} | wl-copy"'
                ),
            )

    def _handle_button_click(self, cmd: str):
        exec_shell_command_async(cmd)


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
        self._generation = 0
        self._executor = ThreadPoolExecutor(
            max_workers=8, thread_name_prefix="cliphist"
        )
        self._pending_buttons: list[tuple[int, str, ClipboardButton]] = []
        self._flush_scheduled = False
        self.pattern = re.compile(
            r"^([0-9]+)\s+\[\[ binary.*(jpg|jpeg|png|bmp)", flags=re.MULTILINE
        )
        self.scrolled_window = ScrolledWindow(
            name="clipboard-history-scrolled-window",
            orientation="h",
            min_content_size=(740, 600),
            max_content_size=(740, 600),
        )
        self.element_box = Box(
            name="clipboard-history-content", orientation="v", spacing=10
        )
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
        self.elements: dict[str, str] = {}
        self.buttons_dict: dict[str, ClipboardButton] = {}
        self.add(self.event_box)
        self._refresh_data()

    def show(self):
        super().show()
        self.grab_focus()

    def _handle_key_press(self, _, key: Gdk.EventKey):
        if key.keyval == Gdk.KEY_Escape:  # type: ignore
            self.toggle_window()
        return True

    def _schedule_flush(self):
        if self._flush_scheduled:
            return
        self._flush_scheduled = True
        GLib.timeout_add(16, self._flush_pending_buttons)

    def _flush_pending_buttons(self):
        self._flush_scheduled = False
        batch = self._pending_buttons[:15]
        del self._pending_buttons[:15]

        for gen, item_id, button in batch:
            if gen != self._generation:
                button.destroy()
                continue
            self.element_box.add(button)
            self.buttons_dict[item_id] = button
            button.show_all()

        if self._pending_buttons:
            self._schedule_flush()
        return False

    def _decode_image_pixbuf(self, data: bytes) -> GdkPixbuf.Pixbuf | None:
        loader = GdkPixbuf.PixbufLoader()
        loader.write(data)  # type: ignore
        loader.close()
        pixbuf = loader.get_pixbuf()
        if pixbuf is None:
            return None
        return pixbuf.scale_simple(720, 405, GdkPixbuf.InterpType.BILINEAR)

    def _process_image_data(self, args: tuple[int, GdkPixbuf.Pixbuf, str, str]):
        gen, pixbuf, item_id, image_extension = args
        if gen != self._generation:
            return

        self.elements[item_id] = f"binary image data {image_extension}"
        button = ClipboardButton(item_id, pixbuf, image_extension)
        button.connect("clicked", lambda _btn: self.toggle_window())
        self._pending_buttons.append((gen, item_id, button))
        self._schedule_flush()

    def _fetch_image_data(self, gen: int, item_id: str, image_extension: str):
        if gen != self._generation:
            return
        result = subprocess.run(
            ["cliphist", "decode", item_id],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout and gen == self._generation:
            pixbuf = self._decode_image_pixbuf(result.stdout)
            if pixbuf is not None and gen == self._generation:
                GLib.idle_add(
                    self._process_image_data, (gen, pixbuf, item_id, image_extension)
                )

    def _process_text_data(self, args: tuple[int, str, str]):
        gen, data, item_id = args
        if gen != self._generation:
            return

        self.elements[item_id] = data
        button = ClipboardButton(item_id, data)
        button.connect("clicked", lambda _btn: self.toggle_window())
        self._pending_buttons.append((gen, item_id, button))
        self._schedule_flush()

    def _fetch_text_data(self, gen: int, item_id: str):
        if gen != self._generation:
            return
        result = subprocess.run(
            ["cliphist", "decode", item_id],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout and gen == self._generation:
            GLib.idle_add(self._process_text_data, (gen, result.stdout, item_id))

    def _fetch_data(self, gen: int, item_id: str, image_extension: str | None = None):
        if gen != self._generation:
            return
        if image_extension:
            self._executor.submit(self._fetch_image_data, gen, item_id, image_extension)
        else:
            self._executor.submit(self._fetch_text_data, gen, item_id)

    def _fetch_list_data(self, item: str, gen: int):
        if gen != self._generation or not item.strip():
            return

        image_extension = None
        if match := re.match(self.pattern, item):
            item_id = match[1]
            image_extension = match[2]
        else:
            item_id = item.split("\t", 1)[0]

        GLib.idle_add(self._fetch_data, gen, item_id, image_extension)  # type: ignore

    def _refresh_data(self):
        self._generation += 1
        gen = self._generation
        self._pending_buttons.clear()
        for child in list(self.element_box.children):
            child.destroy()
        self.elements.clear()
        self.buttons_dict.clear()
        exec_shell_command_async(
            "cliphist list", lambda line, g=gen: self._fetch_list_data(line, g)
        )

    def _process_search(self, entry):
        search_query = entry.get_text().strip()
        if search_query:
            matches = extract(search_query, self.elements, limit=50)
            matched_ids = {match[2] for match in matches if match[1] > 0}
            for item_id, button in self.buttons_dict.items():
                if item_id in matched_ids:
                    button.show()
                else:
                    button.hide()
        else:
            for button in self.buttons_dict.values():
                button.show()

    def toggle_window(self):
        """Toggle the visibility of the clipboard history window."""
        if self.is_hidden:
            self._refresh_data()
            self.show()
            self.grab_focus()
        else:
            self.hide()
        self.is_hidden = not self.is_hidden
