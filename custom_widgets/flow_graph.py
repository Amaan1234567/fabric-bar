"""
FlowGraph — a smooth, animated graph widget for fabric / PyGTK desktop shells.

Renders flowing line graphs with gradient fills, using cubic spline interpolation
for silky curves and the fabric Animator for graceful data transitions.
"""

import gi
import cairo
from gi.repository import Gtk  # type: ignore
from typing import Any, List, Optional, Tuple
from functools import partial
from utils.animator import Animator, cubic_bezier

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")


# ── Colour helpers ────────────────────────────────────────────────────────────


def _hex_to_rgba(hex_str: str) -> Tuple[float, float, float, float]:
    """Convert '#RRGGBB' or '#RRGGBBAA' to floats in 0-1."""
    h = hex_str.lstrip("#")
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return r / 255, g / 255, b / 255, 1.0
    r, g, b, a = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16)
    return r / 255, g / 255, b / 255, a / 255


def _lerp_color(
    c1: Tuple[float, ...], c2: Tuple[float, ...], t: float
) -> Tuple[float, ...]:
    return tuple(a + (b - a) * t for a, b in zip(c1, c2))


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
    pts: List[Tuple[float, float]] = []
    alpha = tension
    for i in range(steps + 1):
        t = i / steps
        t2, t3 = t * t, t * t * t
        # Catmull‑Rom matrix form
        x = (
            (alpha * (-t3 + 2 * t2 - t) + t3 - t2) * 0.5 * p0[0]
            + (alpha * (t3 - 2 * t2 + t) + (-2 * t3 + 3 * t2) + 1) * p1[0]
            + (alpha * (-t3 + t2) + (2 * t3 - 3 * t2 + 1) * 0.0 + (t3 - t2)) * 0.0
            + 0  # placeholder, real formula below
        )
        # Simpler standard formulation:
        x = (
            (
                (-alpha * t3 + 2 * alpha * t2 - alpha * t) * p0[0]
                + ((2 - alpha) * t3 + (alpha - 3) * t2 + 1) * p1[0]
                + ((alpha - 2) * t3 + (3 - 2 * alpha) * t2 + alpha * t) * p2[0]
                + (alpha * t3 - alpha * t2) * p3[0]
            )
            if False  # pylint: disable=using-constant-test
            else None
        )  # noqa — we use the cleaner version below

    # ---- Clean Catmull‑Rom (uniform, tension 0 = Catmull‑Rom, 1 = linear) ----
    tau = 0.5 * (1.0 - tension)  # standard Catmull‑Rom tension factor
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
    """Build a smooth polyline through *points* using Catmull‑Rom interpolation.

    Duplicate the first/last point so every real segment has a neighbour.
    """
    if len(points) < 2:
        return list(points)

    padded = [points[0]] + list(points) + [points[-1]]
    result: List[Tuple[float, float]] = []
    for i in range(1, len(padded) - 2):
        seg = _catmull_rom_segment(
            padded[i - 1],
            padded[i],
            padded[i + 1],
            padded[i + 2],
            tension=tension,
            steps=steps,
        )
        result.extend(seg if i == 1 else seg[1:])  # avoid duplicating joints
    return result


# ── The widget ────────────────────────────────────────────────────────────────


class FlowGraph(Gtk.DrawingArea):
    """A smooth animated line-/area-graph widget.

    Parameters
    ----------
    values : list[float]
        Initial data values (0.0 - 1.0 normalised range, or pass min/max).
    min_value, max_value : float
        Data range.  Points are normalised to [0, 1] internally for drawing.
    bezier : tuple[float, float, float, float]
        Cubic-bezier control points for the transition animation.
    animation_duration : float
        Seconds for a full data transition.
    line_width : float
        Stroke width of the graph line.
    line_color : str
        Hex colour for the line (e.g. ``"#7aa2f7"``).
    fill_color : str | None
        Hex colour for the area under the curve.  ``None`` = no fill.
    fill_end_color : str | None
        If set, gradient fill from *fill_color* (top) → *fill_end_color* (bottom).
    grid_color : str | None
        Hex colour for horizontal guide lines.  ``None`` = hidden.
    grid_lines : int
        Number of horizontal grid divisions.
    tension : float
        Catmull-Rom tension (0 = very smooth, 1 = straight segments).
    spline_steps : int
        Interpolation sub-steps per data segment (higher = smoother).
    padding : float
        Inner padding in pixels.
    animate_on_resize : bool
        Re-animate when the widget is resized.
    background_color : str | None
        Solid widget background.  ``None`` = transparent.
    dot_radius : float
        Radius of data-point dots (0 = hidden).
    dot_color : str | None
        Hex colour for dots.  Falls back to *line_color*.
    """

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
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        if not self.get_name():
            self.set_name("flow-graph")

        # ---- public config ----
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

        # ---- state ----
        self._current: List[float] = list(values) if values else []
        self._target: List[float] = list(self._current)
        self._display: List[float] = list(self._current)

        # ---- animator ----
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

        # First data ever — nothing to animate from, just set directly
        if not self._display:
            self._current = list(new)
            self._target = list(new)
            self._display = list(new)
            self.queue_draw()
            return

        # Snapshot what's on screen right now
        cur = list(self._display)

        # Pad the shorter list so both have equal length —
        # without this, zip in _on_tick truncates and the new
        # point never appears until the animation finishes.
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

        draw_w = w - 2 * pad
        draw_h = h - 2 * pad
        n = len(raw)
        if n < 2:
            return []

        lo, hi = self.min_value, self.max_value
        span = hi - lo if hi != lo else 1.0

        pts: List[Tuple[float, float]] = []
        for i, v in enumerate(raw):
            x = pad + (i / (n - 1)) * draw_w
            norm = (v - lo) / span
            norm = max(0.0, min(1.0, norm))
            y = pad + (1.0 - norm) * draw_h  # invert y
            pts.append((x, y))
        return pts

    # ── GTK size negotiation ───────────────────────────────────────────────

    def do_get_preferred_width(self):
        """Suggest a default width, but allow expanding if needed."""
        return 100, 200

    def do_get_preferred_height(self):
        """Suggest a default height, but allow expanding if needed."""
        return 25, 50

    # ── Cairo draw ─────────────────────────────────────────────────────────

    def do_draw(self, cr):
        """Draw the graph using Cairo.  Called automatically when the widget needs redrawing."""
        w = self.get_allocated_width()
        h = self.get_allocated_height()

        # ── read CSS color (same pattern as ScrollingLabel) ─────────
        style_context = self.get_style_context()
        rgba = style_context.get_color(Gtk.StateFlags.NORMAL)
        css_color = (rgba.red, rgba.green, rgba.blue, rgba.alpha)

        # line = CSS color
        line_rgba = css_color
        # grid = faint white
        grid_rgba = (1.0, 1.0, 1.0, 0.04)

        # background
        if self.bg_rgba:
            cr.set_source_rgba(*self.bg_rgba)
            cr.rectangle(0, 0, w, h)
            cr.fill()

        # grid
        if self.grid_lines > 0:
            cr.set_source_rgba(*grid_rgba)
            cr.set_line_width(0.5)
            pad = self.padding
            draw_h = h - 2 * pad
            for i in range(1, self.grid_lines + 1):
                y = pad + (i / (self.grid_lines + 1)) * draw_h
                cr.move_to(pad, y)
                cr.line_to(w - pad, y)
                cr.stroke()

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

        cr.line_to(smooth[-1][0], h - self.padding)
        cr.line_to(smooth[0][0], h - self.padding)
        cr.close_path()

        grad_y_top = min(p[1] for p in data_pts)
        grad_y_bot = h - self.padding
        pat = cairo.LinearGradient(0, grad_y_top, 0, grad_y_bot)  # pylint: disable=no-member
        pat.add_color_stop_rgba(
            0.0, rgba.red, rgba.green, rgba.blue, 0.14
        )  # top — visible
        pat.add_color_stop_rgba(
            0.6, rgba.red, rgba.green, rgba.blue, 0.10
        )  # 60% — still visible
        pat.add_color_stop_rgba(
            1.0, rgba.red, rgba.green, rgba.blue, 0.0
        )  # bottom — transparent

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
