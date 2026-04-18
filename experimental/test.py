from fabric import Application
from fabric.widgets.wayland import WaylandWindow
from fabric.widgets.box import Box
from fabric.utils import get_relative_path
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import cairo

class MarqueeLabel(Gtk.DrawingArea):
    def __init__(self, text="Media Title - Artist - Album", speed=0.01):
        super().__init__()
        self.text = text
        self.x_offset = 0
        self.speed = speed
        self.direction = -1  # -1 for moving left, 1 for moving right
        self.pause_counter = 0
        self.set_size_request(200, 40)
        GLib.timeout_add(10, self.update_position)

    def do_draw(self, cr):
        width = self.get_allocated_width()
        height = self.get_allocated_height()

        # 1. Mask/Clip (keeps text inside the widget)
        cr.rectangle(0, 0, width, height)
        cr.clip()

        # 2. Text Setup
        cr.set_source_rgb(0, 0, 0)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(14)

        extents = cr.text_extents(self.text)
        text_w = extents.width
        y_pos = (height / 2) + (extents.height / 2)

        # 3. Bounce Logic
        if text_w > width:
            # Maximum distance the text can scroll to the left
            max_scroll = width - text_w - 5 # 10px padding

            if self.pause_counter <= 0:
                self.x_offset += (self.speed * self.direction)
                # print(f"Offset: {self.x_offset:.2f}, Direction: {self.direction}, Pause: {self.pause_counter}")
                # Hit left boundary (scrolled all the way to the end)
                if self.x_offset <= max_scroll:
                    self.x_offset = max_scroll
                    self.direction = 1
                    self.pause_counter = 50 # Pause for ~1 second

                # Hit right boundary (returned to start)
                elif self.x_offset >= 0:
                    self.x_offset = 0
                    self.direction = -1
                    self.pause_counter = 50
            else:
                self.pause_counter -= 1
        else:
            self.x_offset = 0 # Center/Align if short enough

        # 4. Render
        cr.move_to(self.x_offset, y_pos)
        cr.show_text(self.text)

    def update_position(self):
        self.queue_draw()
        return True



if __name__ == "__main__":
    app = Application(
        "notifications",
        WaylandWindow(
            margin="8px 8px 8px 8px",
            anchor="top",
            child=Box(
                size=(200,200),  # so it's not ignored by the compositor
                spacing=4,
                orientation="v",
                children=[MarqueeLabel(text="Scrolling ", speed=0.4)],
            ),
            visible=True,
            all_visible=True,
            keyboard_mode="on-demand"
        ),
    )

    # app.set_stylesheet_from_file(get_relative_path("../styles/style.css"))

    app.run()
