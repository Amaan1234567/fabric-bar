"""
FlowGraph — a smooth, animated graph widget for fabric / PyGTK desktop shells.

Renders flowing line graphs with gradient fills, using cubic spline interpolation
for silky curves and the fabric Animator for graceful data transitions.
"""

import gi
import cairo
from gi.repository import Gtk, Pango, PangoCairo  # type: ignore
from typing import Any, List, Optional, Tuple
from functools import partial
from utils.animator import Animator, cubic_bezier

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")


# ── Colour helpers ────────────────────────────────────────────────────────────


def _hex_to_rgba(hex_str: str) -> Tuple[float, float, float, float]:
    """Convert '#RRGGBB' or '#RRGGBBAA' to floats in 0-1."""
    h = hex_str.lstrip("#")
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return r / 255, g / 255, b / 255, 1.0
    r, g, b, a = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16)
    return r / 255, g / 255, b / 255, a / 255


# ── Spline math ───────────────────────────────────────────────────────────────


def _catmull_rom_segment(
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    tension: float = 0.5,
    steps: int = 24,
) -> List[Tuple[float, float]]:
    """Return *steps* interpolated points on a Catmull-Rom segment p1→p2."""
    tau = 0.5 * (1.0 - tension)
    pts = []
    for i in range(steps + 1):
        s = i / steps
        s2, s3 = s * s, s * s * s

        x = (
            tau * ((-s3 + 2 * s2 - s) * p0[0])
            + (1.0) * ((2 * s3 - 3 * s2 + 1) * p1[0] + tau * (s3 - 2 * s2 + s) * p1[0])
            + (1.0) * ((-2 * s3 + 3 * s2) * p2[0] + tau * (-s3 + s2) * p2[0])
            + tau * ((s3 - s2) * p3[0])
        )
        y = (
            tau * ((-s3 + 2 * s2 - s) * p0[1])
            + (1.0) * ((2 * s3 - 3 * s2 + 1) * p1[1] + tau * (s3 - 2 * s2 + s) * p1[1])
            + (1.0) * ((-2 * s3 + 3 * s2) * p2[1] + tau * (-s3 + s2) * p2[1])
            + tau * ((s3 - s2) * p3[1])
        )
        pts.append((x, y))
    return pts


def _smooth_path(
    points: List[Tuple[float, float]], tension: float = 0.4, steps: int = 32
) -> List[Tuple[float, float]]:
    """Build a smooth polyline through *points* using Catmull-Rom interpolation."""
    if len(points) < 2:
        return list(points)

    padded = [points[0]] + list(points) + [points[-1]]
    result: List[Tuple[float, float]] = []
    for i in range(1, len(padded) - 2):
        seg = _catmull_rom_segment(
            padded[i - 1], padded[i], padded[i + 1], padded[i + 2],
            tension=tension, steps=steps,
        )
        result.extend(seg if i == 1 else seg[1:])
    return result


# ── The widget ────────────────────────────────────────────────────────────────


class FlowGraph(Gtk.DrawingArea):
    """A smooth animated line-/area-graph widget."""

    __gtype_name__ = "FlowGraph"

    def __init__(
        self,
        values: Optional[List[float]] = None,
        min_value: float = 0.0,
        max_value: float = 100.0,
        bezier: Tuple[float, float, float, float] = (0.4, 0.0, 0.2, 1.0),
        animation_duration: float = 0.6,
        line_width: float = 2.0,
        grid_lines: int = 4,
        tension: float = 0.4,
        spline_steps: int = 32,
        padding: float = 8.0,
        animate_on_resize: bool = True,
        background_color: Optional[str] = None,
        dot_radius: float = 0.0,
        y_axis: bool = False,
        y_axis_format: str = "{:.0f}",
        y_axis_width: int = 30,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        if not self.get_name():
            self.set_name("flow-graph")

        self.min_value = min_value
        self.max_value = max_value
        self.line_width = line_width
        self.tension = tension
        self.spline_steps = spline_steps
        self.padding = padding
        self.grid_lines = grid_lines
        self.dot_radius = dot_radius
        self.animate_on_resize = animate_on_resize

        self.bg_rgba = _hex_to_rgba(background_color) if background_color else None

        # ── Y-axis config ───────────────────────────────────────
        self.y_axis = y_axis
        self.y_axis_format = y_axis_format
        self.y_axis_width = y_axis_width  # px reserved for labels

        # ── state ───────────────────────────────────────────────
        self._current: List[float] = list(values) if values else []
        self._target: List[float] = list(self._current)
        self._display: List[float] = list(self._current)

        # ── animator ────────────────────────────────────────────
        self._animator = Animator(
            duration=animation_duration,
            timing_function=partial(cubic_bezier, *bezier),
            min_value=0.0,
            max_value=1.0,
            repeat=False,
            tick_widget=self,
        )
        self._animator.connect("notify::value", self._on_tick)
        self._animator.connect("finished", self._on_finished)

        self.connect("destroy", self._on_destroy)

    # ── public API ─────────────────────────────────────────────────────────

    def set_values(self, new_values: List[float]) -> None:
        """Animate from current data to *new_values*."""
        new = list(new_values)
        if not new:
            return

        if not self._display:
            self._current = list(new)
            self._target = list(new)
            self._display = list(new)
            self.queue_draw()
            return

        cur = list(self._display)
        max_len = max(len(cur), len(new))
        if len(cur) < max_len:
            cur.extend([cur[-1]] * (max_len - len(cur)))
        if len(new) < max_len:
            new.extend([new[-1]] * (max_len - len(new)))

        self._current = cur
        self._target = new

        self._animator.pause()
        self._animator.value = 0.0
        self._animator.min_value = 0.0
        self._animator.max_value = 1.0
        self._animator.play()

    def _on_tick(self, animator, *_args):
        t = animator.value
        self._display = (
            [c + (tgt_v - c) for c, tgt_v in zip(self._current, self._target)]
            if t >= 1.0
            else [c + (tgt_v - c) * t for c, tgt_v in zip(self._current, self._target)]
        )
        self.queue_draw()

    def _on_finished(self, *_args):
        self._current = list(self._target)
        self._display = list(self._target)
        self.queue_draw()

    def _on_destroy(self, *_args):
        self._animator.pause()

    # ── geometry helpers ───────────────────────────────────────────────────

    def _normalize(self, raw: List[float]) -> List[Tuple[float, float]]:
        """Map data values → (x, y) pixel coords (y grows *down* in Cairo)."""
        w = self.get_allocated_width()
        h = self.get_allocated_height()
        pad = self.padding
        y_off = self.y_axis_width if self.y_axis else 0

        draw_w = w - 2 * pad - y_off
        draw_h = h - 2 * pad
        n = len(raw)
        if n < 2:
            return []

        lo, hi = self.min_value, self.max_value
        span = hi - lo if hi != lo else 1.0

        pts: List[Tuple[float, float]] = []
        for i, v in enumerate(raw):
            x = pad + y_off + (i / (n - 1)) * draw_w
            norm = (v - lo) / span
            norm = max(0.0, min(1.0, norm))
            y = pad + (1.0 - norm) * draw_h
            pts.append((x, y))
        return pts

    # ── GTK size negotiation ───────────────────────────────────────────────

    def do_get_preferred_width(self):
        base = 100 + (self.y_axis_width if self.y_axis else 0)
        return base, base * 2

    def do_get_preferred_height(self):
        return 25, 50

    # ── Cairo draw ─────────────────────────────────────────────────────────

    def do_draw(self, cr):
        w = self.get_allocated_width()
        h = self.get_allocated_height()

        # ── CSS colour (same pattern as ScrollingLabel) ──────────
        style_context = self.get_style_context()
        rgba = style_context.get_color(Gtk.StateFlags.NORMAL)

        line_rgba = (rgba.red, rgba.green, rgba.blue, rgba.alpha)
        grid_rgba = (1.0, 1.0, 1.0, 0.4)

        y_off = self.y_axis_width if self.y_axis else 0
        pad = self.padding

        # background
        if self.bg_rgba:
            cr.set_source_rgba(*self.bg_rgba)
            cr.rectangle(0, 0, w, h)
            cr.fill()

        # ── Y-axis labels + grid ────────────────────────────────
        if self.grid_lines > 0:
            draw_h = h - 2 * pad

            for i in range(self.grid_lines + 2):
                frac = i / (self.grid_lines + 1)
                y = pad + frac * draw_h

                # grid line (skip top edge i=0 and bottom edge i=grid_lines+1)
                if 0 < i < self.grid_lines + 1:
                    cr.set_source_rgba(*grid_rgba)
                    cr.set_line_width(0.5)
                    cr.move_to(pad + y_off, y)
                    cr.line_to(w - pad, y)
                    cr.stroke()

                # Y-axis label
                        # ── Y-axis labels + grid ────────────────────────────────
        if self.grid_lines > 0:
            draw_h = h - 2 * pad

            for i in range(self.grid_lines + 2):
                frac = i / (self.grid_lines + 1)
                y = pad + frac * draw_h

                # grid line at every breakpoint (including top/bottom edges)
                cr.set_source_rgba(*grid_rgba)
                cr.set_line_width(0.5)
                cr.move_to(pad + y_off, y)
                cr.line_to(w - pad, y)
                cr.stroke()

                # Y-axis label (skip top and bottom edges)
                if self.y_axis and 0 < i < self.grid_lines + 1:
                    value = self.max_value - frac * (self.max_value - self.min_value)
                    label = self.y_axis_format.format(value)

                    layout = self.create_pango_layout(label)
                    font_desc = style_context.get_font(Gtk.StateFlags.NORMAL)
                    font_desc.set_size(int(8.5 * Pango.SCALE))
                    layout.set_font_description(font_desc)
                    layout.set_alignment(Pango.Alignment.RIGHT)
                    lw, lh = layout.get_pixel_size()

                    cr.set_source_rgba(rgba.red, rgba.green, rgba.blue, 0.35)
                    cr.move_to(pad, y - lh / 2)
                    PangoCairo.show_layout(cr, layout)



        # ── data ────────────────────────────────────────────────
        raw = self._display
        if len(raw) < 2:
            return

        data_pts = self._normalize(raw)
        smooth = _smooth_path(data_pts, tension=self.tension, steps=self.spline_steps)

        if len(smooth) < 2:
            return

        # ---- fill ----
        cr.move_to(smooth[0][0], smooth[0][1])
        for px, py in smooth[1:]:
            cr.line_to(px, py)

        cr.line_to(smooth[-1][0], h - pad)
        cr.line_to(smooth[0][0], h - pad)
        cr.close_path()

        grad_y_top = min(p[1] for p in data_pts)
        grad_y_bot = h - pad
        pat = cairo.LinearGradient(0, grad_y_top, 0, grad_y_bot)  # pylint: disable=no-member
        pat.add_color_stop_rgba(0.0, rgba.red, rgba.green, rgba.blue, 0.14)
        pat.add_color_stop_rgba(0.6, rgba.red, rgba.green, rgba.blue, 0.10)
        pat.add_color_stop_rgba(1.0, rgba.red, rgba.green, rgba.blue, 0.0)
        cr.set_source(pat)
        cr.fill()

        # ---- line ----
        cr.set_source_rgba(*line_rgba)
        cr.set_line_width(self.line_width)
        cr.set_line_join(1)
        cr.set_line_cap(1)

        cr.move_to(smooth[0][0], smooth[0][1])
        for px, py in smooth[1:]:
            cr.line_to(px, py)
        cr.stroke()

        # ---- dots ----
        if self.dot_radius > 0:
            cr.set_source_rgba(*line_rgba)
            for px, py in data_pts:
                cr.arc(px, py, self.dot_radius, 0, 6.283185307)
                cr.fill()
