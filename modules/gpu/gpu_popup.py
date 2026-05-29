"""GPU stats popup with flow graphs for core and VRAM usage."""

from fabric.widgets.box import Box
from fabric.widgets.label import Label

from custom_widgets.popup_window import PopupWindow
from custom_widgets.flow_graph import FlowGraph
from custom_widgets.HackedStackRevealer import HackedRevealer


class GpuPopup(PopupWindow):
    """PopupWindow with two FlowGraphs and a stats label."""

    def __init__(self, parent, pointing_to, **kwargs):
        super().__init__(
            parent=parent,
            pointing_to=pointing_to,
            layer="top",
            name="gpu-popup-window",
            type="popup",
            margin="15px 0 0 120px",
            anchor="top left",
            title="fabric-gpu-popup",
            visible=False,
            v_expand=False,
            h_expand=False,
            **kwargs,
        )

        self._content = Box(
            orientation="v",
            name="gpu-popup-content",
            spacing=8,
            h_expand=True,
            v_expand=True,
        )

        # ── core usage graph ────────────────────────────────────
        self.core_graph_label = Label(
            label="Core",
            name="gpu-graph-label",
            use_markup=True,
            h_align="start",
        )
        self.core_graph = FlowGraph(
            name="gpu-core-graph",
            values=[],
            min_value=0,
            max_value=100,
            bezier=(0.25, 0.1, 0.25, 1.0),
            animation_duration=0.5,
            line_width=2.0,
            grid_lines=3,
            tension=0,
            spline_steps=8,
            dot_radius=0,
            padding=0,
            visible=True,
            y_axis=True,
            y_axis_format="{:.0f}%",
            y_axis_width=32,
        )
        self.core_graph.set_size_request(200, 50)

        # ── VRAM usage graph ────────────────────────────────────
        self.vram_graph_label = Label(
            label="VRAM",
            name="gpu-graph-label",
            use_markup=True,
            h_align="start",
        )
        self.vram_graph = FlowGraph(
            name="gpu-vram-graph",
            values=[],
            min_value=0,
            max_value=100,
            bezier=(0.25, 0.1, 0.25, 1.0),
            animation_duration=0.5,
            line_width=2.0,
            grid_lines=3,
            tension=0,
            spline_steps=8,
            dot_radius=0,
            padding=0,
            visible=True,
            y_axis=True,
            y_axis_format="{:.0f}%",
            y_axis_width=32,
        )
        self.vram_graph.set_size_request(200, 50)

        # ── stats text ──────────────────────────────────────────
        self.stats_label = Label(
            name="gpu-stats-label",
            use_markup=True,
            h_align="start",
        )

        self._content.add(self.core_graph_label)
        self._content.add(self.core_graph)
        self._content.add(self.vram_graph_label)
        self._content.add(self.vram_graph)
        self._content.add(self.stats_label)

        # ── revealer ────────────────────────────────────────────
        self.overlay_revealer = HackedRevealer(
            bezier_curve=(0.3, -0.06, 0, 1.02),
            duration=0.450,
            name="gpu-revealer",
            child=self._content,
        )

        self.add(self.overlay_revealer)

    def update(self, core_history, vram_history, stats_markup):
        """Push new data into both graphs and the stats label."""
        self.core_graph.set_values(list(core_history))
        self.vram_graph.set_values(list(vram_history))
        self.stats_label.set_markup(stats_markup)
