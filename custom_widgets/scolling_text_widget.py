from functools import partial
import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, GLib, Pango, PangoCairo

from utils.animator import Animator, _cubic_bezier


class ScrollingLabel(Gtk.DrawingArea):
    def __init__(
        self,
        text="---",
        bezier=(0, 0.37, 1, 0.65),
        speed=0.8,
        pause_ms=2000,
        max_width=200,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.set_name("song-title")
        self.text = text
        self.speed = speed
        self.max_width_limit = max_width
        self.pause_ms = pause_ms

        self.set_halign(Gtk.Align.START)

        self._pause_source_id = None
        self._is_mapped = False

        # ── Surface cache ───────────────────────────────────────
        self._surface = None
        self._surface_dirty = True
        self._text_w = 0
        self._text_h = 0

        # ── Pixel-snap state ────────────────────────────────────
        self._last_drawn_offset = None

        self.animator = Animator(
            duration=1.0,
            timing_function=partial(_cubic_bezier, *bezier),
            min_value=0.0,
            max_value=1.0,
            repeat=False,
            tick_widget=self,
        )

        self.animator.connect("notify::value", self._on_animator_step)
        self.animator.connect("finished", self._on_animator_finished)

        self.connect("map", self._on_map)
        self.connect("unmap", self._on_unmap)

    # ── Visibility gating ───────────────────────────────────────

    def _on_map(self, *_):
        self._is_mapped = True
        self._invalidate_surface()
        self.queue_resize()
        self._last_drawn_offset = None
        self._start_scrolling_if_needed()

    def _on_unmap(self, *_):
        self._is_mapped = False
        self._last_drawn_offset = None
        self.animator.pause()
        if self._pause_source_id:
            GLib.source_remove(self._pause_source_id)
            self._pause_source_id = None

    # ── Surface rendering ───────────────────────────────────────

    def _render_surface(self):
        style_context = self.get_style_context()
        font_desc = style_context.get_font(Gtk.StateFlags.NORMAL)
        rgba = style_context.get_color(Gtk.StateFlags.NORMAL)

        layout = self.create_pango_layout(self.text)
        layout.set_font_description(font_desc)
        self._text_w, self._text_h = layout.get_pixel_size()

        surface_w = max(self._text_w + 4, 1)
        surface_h = max(self._text_h, 1)

        self._surface = cairo.ImageSurface(cairo.Format.ARGB32, surface_w, surface_h)
        cr = cairo.Context(self._surface)

        cr.set_operator(cairo.Operator.CLEAR)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)

        cr.set_source_rgba(rgba.red, rgba.green, rgba.blue, rgba.alpha)
        cr.move_to(0, 0)
        PangoCairo.show_layout(cr, layout)

        self._surface_dirty = False

    def _invalidate_surface(self):
        self._surface_dirty = True
        self._surface = None

    # ── Animation callbacks ─────────────────────────────────────

    def _on_animator_step(self, animator, *args):
        if not self._is_mapped:
            return

        width = self.get_allocated_width()
        if width <= 0 or self._text_w <= width:
            return

        # Only queue a redraw if the pixel position actually changed
        max_scroll = width - self._text_w - 4
        new_offset = round(max_scroll * animator.value)
        if new_offset == self._last_drawn_offset:
            return  # same pixel -- skip this frame entirely

        self._last_drawn_offset = new_offset
        self.queue_draw()

    def _on_animator_finished(self, *args):
        self.animator.min_value, self.animator.max_value = (
            self.animator.max_value,
            self.animator.min_value,
        )

        self._last_drawn_offset = None

        if self._pause_source_id:
            GLib.source_remove(self._pause_source_id)

        self._pause_source_id = GLib.timeout_add(self.pause_ms, self._resume_animation)

    def _resume_animation(self):
        self._pause_source_id = None
        self._last_drawn_offset = None
        if self._is_mapped:
            self.animator.play()
        return GLib.SOURCE_REMOVE

    def _start_scrolling_if_needed(self):
        width = self.get_allocated_width()
        if width > 0 and self._text_w > width:
            if not self.animator.playing and self._pause_source_id is None:
                self.animator.play()

    # ── Public API ──────────────────────────────────────────────

    def get_text(self):
        return self.text

    def set_text(self, new_text):
        if self.text != str(new_text):
            self.text = str(new_text)
            self._invalidate_surface()
            self._last_drawn_offset = None

            self.animator.pause()
            if self._pause_source_id:
                GLib.source_remove(self._pause_source_id)
                self._pause_source_id = None

            self.animator.min_value = 0.0
            self.animator.max_value = 1.0
            self.animator.value = 0.0

            self.queue_resize()

    # ── GTK size requests ───────────────────────────────────────

    def do_get_preferred_width(self):
        if self._surface_dirty or self._surface is None:
            self._render_surface()
        natural = min(self._text_w, self.max_width_limit)
        return natural, natural

    def do_get_preferred_height(self):
        if self._surface_dirty or self._surface is None:
            self._render_surface()
        return self._text_h, self._text_h

    # ── Drawing ─────────────────────────────────────────────────

    def do_draw(self, cr):
        width = self.get_allocated_width()
        height = self.get_allocated_height()

        if self._surface_dirty or self._surface is None:
            self._render_surface()

        if self._surface is None:
            return

        cr.rectangle(0, 0, width, height)
        cr.clip()

        y_pos = (height - self._text_h) / 2

        if self._text_w > width:
            max_scroll = width - self._text_w - 4
            scroll_distance = abs(max_scroll)

            pixels_per_second = self.speed * (1000 / 16)
            target_duration = scroll_distance / pixels_per_second

            if abs(self.animator.duration - target_duration) > 0.01:
                self.animator.duration = target_duration

            if not self.animator.playing and self._pause_source_id is None:
                self.animator.play()

            x_offset = max_scroll * self.animator.value
        else:
            if self.animator.playing:
                self.animator.pause()
            if self._pause_source_id:
                GLib.source_remove(self._pause_source_id)
                self._pause_source_id = None
            self.animator.value = 0.0
            self.animator.min_value = 0.0
            self.animator.max_value = 1.0
            x_offset = 0

        cr.set_source_surface(self._surface, round(x_offset), y_pos)
        cr.paint()