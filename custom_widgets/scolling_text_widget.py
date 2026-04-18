import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, GLib, Pango, PangoCairo

class ScrollingLabel(Gtk.DrawingArea):
    def __init__(self, text="---", speed=0.4, max_width=200, **kwargs):
        super().__init__(**kwargs)
        self.set_name("song-title")
        self.text = text
        self.speed = speed
        self.max_width_limit = max_width
        
        # Prevent the widget from stretching to fill its parent
        self.set_halign(Gtk.Align.START) 
        
        self.x_offset = 0
        self.direction = -1
        self.pause_counter = 0
        
        # GLib.timeout_add(16, self.update_position)
        self.add_tick_callback(self.update_position)

    def get_text(self):
        """ Returns the current text string. """
        return self.text

    def set_text(self, new_text):
        """ Updates text and resets scrolling state. """
        if self.text != str(new_text):
            self.text = str(new_text)
            self.x_offset = 0
            self.direction = -1
            self.pause_counter = 0
            self.queue_resize()

    def do_get_preferred_width(self):
        layout = self.create_pango_layout(self.text)
        style_context = self.get_style_context()
        layout.set_font_description(style_context.get_font(Gtk.StateFlags.NORMAL))
        text_w, _ = layout.get_pixel_size()
        
        # Enforce max width limit
        natural = min(text_w, self.max_width_limit)
        return natural, natural 

    def do_get_preferred_height(self):
        layout = self.create_pango_layout(self.text)
        style_context = self.get_style_context()
        layout.set_font_description(style_context.get_font(Gtk.StateFlags.NORMAL))
        _, text_h = layout.get_pixel_size()
        return text_h, text_h

    def do_draw(self, cr):
        width = self.get_allocated_width()
        height = self.get_allocated_height()

        style_context = self.get_style_context()
        rgba = style_context.get_color(Gtk.StateFlags.NORMAL)
        font_desc = style_context.get_font(Gtk.StateFlags.NORMAL)

        layout = self.create_pango_layout(self.text)
        layout.set_font_description(font_desc)
        text_w, text_h = layout.get_pixel_size()

        # Define visible area
        cr.rectangle(0, 0, width, height)
        cr.clip()

        y_pos = (height - text_h) / 2

        # Bounce Logic
        if text_w > width:
            max_scroll = width - text_w - 4
            if self.pause_counter <= 0:
                self.x_offset += (self.speed * self.direction)
                if self.x_offset <= max_scroll:
                    self.x_offset = max_scroll
                    self.direction = 1
                    self.pause_counter = 187.5
                elif self.x_offset >= 0:
                    self.x_offset = 0
                    self.direction = -1
                    self.pause_counter = 187.5
            else:
                self.pause_counter -= 1
        else:
            self.x_offset = 0

        # Paint using CSS color
        cr.set_source_rgba(rgba.red, rgba.green, rgba.blue, rgba.alpha)
        cr.move_to(self.x_offset, y_pos)
        PangoCairo.show_layout(cr, layout)

    def update_position(self, widget, frame_clock):
        self.queue_draw()
        # 3. Return Continue to keep the loop going
        return GLib.SOURCE_CONTINUE
