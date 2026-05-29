"""Memory stats popup with a flow graph and live system info."""

from fabric.widgets.box import Box
from fabric.widgets.label import Label

from custom_widgets.popup_window import PopupWindow
from custom_widgets.flow_graph import FlowGraph
from custom_widgets.HackedStackRevealer import HackedRevealer


class MemoryPopup(PopupWindow):
    """PopupWindow containing a FlowGraph and stats label for memory."""

    def __init__(self, parent, pointing_to, **kwargs):
        super().__init__(
            parent=parent,
            pointing_to=pointing_to,
            layer="top",
            name="memory-popup-window",
            type="popup",
            margin="15px 0 0 100px",
            anchor="top left",
            title="fabric-memory-popup",
            visible=False,
            v_expand=False,
            h_expand=False,
            **kwargs,
        )

        # ── build the popup content ─────────────────────────────
        self._content = Box(
            orientation="v",
            name="memory-popup-content",
            spacing=8,
            h_expand=True,
            v_expand=True,
        )

        self.graph = FlowGraph(
            values=[],
            min_value=0,
            max_value=100,
            bezier=(0.25, 0.1, 0.25, 1.0),
            animation_duration=0.5,
            line_width=2.0,
            grid_lines=4,
            tension=0,
            spline_steps=8,
            dot_radius=0,
            padding=0,
            visible=True,
            y_axis=True,
            y_axis_format="{:.0f}%",
            y_axis_width=32,
        )
        self.graph.set_size_request(80, 120)

        self.stats_label = Label(
            name="memory-stats-label",
            use_markup=True,
            h_align="start",
        )

        self._content.add(self.graph)
        self._content.add(self.stats_label)

        self.overlay_revealer = HackedRevealer(
            bezier_curve=(0.3, -0.06, 0, 1.02),
            duration=0.450,
            name="memory-revealer",
            child=self._content,
        )

        self.add(self.overlay_revealer)

    def update(self, history, stats_markup):
        """Push new data into the graph and stats label."""
        self.graph.set_values(list(history))
        self.stats_label.set_markup(stats_markup)
