"""CPU stats popup with a flow graph and live system info."""

from fabric.widgets.box import Box
from fabric.widgets.label import Label

from custom_widgets.popup_window import PopupWindow
from custom_widgets.FlowGraph import FlowGraph
from custom_widgets.HackedStackRevealer import HackedRevealer


class CpuPopup(PopupWindow):
    """PopupWindow containing a FlowGraph and stats label, with revealer animation."""

    def __init__(self, parent, pointing_to, **kwargs):
        super().__init__(
            parent=parent,
            pointing_to=pointing_to,
            layer="top",
            name="cpu-popup-window",
            type="popup",
            anchor="top left",
            title="fabric-cpu-popup",
            margin="",
            visible=False,
            v_expand=False,
            h_expand=False,
            **kwargs,
        )

        # ── build the popup content ─────────────────────────────
        self._content = Box(
            orientation="h",
            name="cpu-popup-content",
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
            line_color="#7aa2f7",
            fill_color="#7aa2f714",
            fill_end_color="#7aa2f700",
            grid_color="#ffffff0a",
            grid_lines=4,
            tension=0.4,
            spline_steps=32,
            dot_radius=0,
            padding=0,
            visible=True,
        )
        self.graph.set_size_request(100, 50)

        self.stats_label = Label(
            name="cpu-stats-label",
            use_markup=True,
            h_align="start",
        )

        self._content.add(self.graph)
        self._content.add(self.stats_label)

        self.overlay_revealer = HackedRevealer(
            bezier_curve=(0.3, -0.06, 0, 1.02),
            duration=0.450,
            name="cpu-revealer",
            transition_type="slide-down",
            child=self._content,
        )

        self.add(self.overlay_revealer)


    def update(self, history, stats_markup):
        """Push new data into the graph and stats label."""
        self.graph.set_values(list(history))
        self.stats_label.set_markup(stats_markup)
