"""Network speed popup with side-by-side flow graphs and top network processes."""

from fabric.widgets.box import Box
from fabric.widgets.label import Label

from custom_widgets.popup_window import PopupWindow
from custom_widgets.flow_graph import FlowGraph
from custom_widgets.HackedStackRevealer import HackedRevealer


class NetworkSpeedPopup(PopupWindow):

    def __init__(self, parent, pointing_to, **kwargs):
        super().__init__(
            parent=parent,
            pointing_to=pointing_to,
            layer="top",
            name="network-speed-popup-window",
            type="popup",
            margin="15px 0 0 0px",
            anchor="top left",
            title="fabric-network-speed-popup",
            visible=False,
            v_expand=False,
            h_expand=False,
            **kwargs,
        )

        self._content = Box(
            orientation="v",
            name="network-speed-popup-content",
            spacing=8,
            h_expand=True,
            v_expand=True,
        )

        # ── side-by-side graphs ─────────────────────────────────
        self.download_graph = FlowGraph(
            name="network-download-graph",
            values=[0.0] * 30,
            min_value=0,
            max_value=10,
            bezier=(0.25, 0.1, 0.25, 1.0),
            animation_duration=0.5,
            line_width=2.0,
            grid_lines=3,
            tension=0,
            spline_steps=8,
            dot_radius=0,
            padding=0,
            y_axis=True,
            y_axis_format="{:.1f}",  # no unit — it's in the title now
            y_axis_width=36,
            visible=True,
        )
        self.download_graph.set_size_request(100, 50)

        self.upload_graph = FlowGraph(
            name="network-upload-graph",
            values=[0.0] * 30,
            min_value=0,
            max_value=10,
            bezier=(0.25, 0.1, 0.25, 1.0),
            animation_duration=0.5,
            line_width=2.0,
            grid_lines=3,
            tension=0,
            spline_steps=8,
            dot_radius=0,
            padding=0,
            y_axis=True,
            y_axis_format="{:.1f}",  # no unit — it's in the title now
            y_axis_width=36,
            visible=True,
        )
        self.upload_graph.set_size_request(100, 50)

        # ── titles with unit in brackets ────────────────────────
        dl_col = Box(
            orientation="v",
            spacing=4,
            h_expand=True,
            children=[
                Label(
                    label="↓ Download (MB/s)",
                    name="network-speed-graph-label",
                    use_markup=True,
                    h_align="start",
                ),
                self.download_graph,
            ],
        )
        ul_col = Box(
            orientation="v",
            spacing=4,
            h_expand=True,
            children=[
                Label(
                    label="↑ Upload (MB/s)",
                    name="network-speed-graph-label",
                    use_markup=True,
                    h_align="start",
                ),
                self.upload_graph,
            ],
        )
        graphs_row = Box(
            orientation="h",
            spacing=12,
            h_expand=True,
            children=[dl_col, ul_col],
        )

        # ── top processes ───────────────────────────────────────
        self.processes_label = Label(
            name="network-speed-processes-label",
            use_markup=True,
            h_align="start",
        )

        self._content.add(graphs_row)
        self._content.add(self.processes_label)

        self.overlay_revealer = HackedRevealer(
            bezier_curve=(0.3, -0.06, 0, 1.02),
            duration=0.450,
            name="network-speed-revealer",
            child=self._content,
        )

        self.add(self.overlay_revealer)

    def update(
        self, dl_history_mb, ul_history_mb, dl_max_mb, ul_max_mb, processes_markup=""
    ):
        if dl_max_mb > 0:
            self.download_graph.max_value = dl_max_mb
        if ul_max_mb > 0:
            self.upload_graph.max_value = ul_max_mb
        self.download_graph.set_values(list(dl_history_mb))
        self.upload_graph.set_values(list(ul_history_mb))
        if processes_markup:
            self.processes_label.set_markup(processes_markup)
