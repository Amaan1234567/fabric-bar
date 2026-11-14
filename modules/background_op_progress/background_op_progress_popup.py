from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label

from custom_widgets.animated_scale import AnimatedScale
from custom_widgets.HackedStackRevealer import HackedRevealer
from custom_widgets.popup_window import PopupWindow
from services.background_op_service import BackgroundOp, BackgroundOpService
from utils.helper_functions import truncate


class BackgroundOpItem(Box):
    """Background Operation Item for popup."""

    def __init__(self, op_obj, **kwargs):
        super().__init__(
            orientation="v", h_expand=True, h_align="fill", spacing=4, **kwargs
        )

        self.scale = AnimatedScale(
            name="background-op-scale",
            orientation="horizontal",
            min_value=0,
            max_value=100,
            value=0,
            h_expand=False,
            v_expand=False,
        )
        self.op: BackgroundOp = op_obj
        self.op_name_label = Label(
            name="background-op-name-label", label=self.op.op_name
        )
        self.details_button = Button(
            name="background-op-details-button",
            label="▸",
            on_clicked=self._handle_click,
        )
        self.details_label = Label(
            name="background-op-details-label",
            label=truncate(self.op.display_text),
            h_align="start",
        )

        self.main_content = Box(
            orientation="h",
            spacing=5,
            children=[
                self.op_name_label,
                Box(h_expand=True),
                self.scale,
                self.details_button,
            ],
        )
        self.detail_content = HackedRevealer(
            bezier_curve=(0.3, -0.06, 0, 1.02),
            duration=0.450,
            child=self.details_label,
        )

        self.add(self.main_content)
        self.add(self.detail_content)

        self.op.connect("progress_update", self._progress_update_handler)
        self.op.connect("state_update", self._state_update_handler)
        self.op.connect("op_complete", self._op_complete_handler)

    def _progress_update_handler(self, _, value: float):
        self.scale.animate_value(value)
        self.scale.value = value

    def _state_update_handler(self, _):
        self.details_label.set_label(truncate(self.op.display_text))

    def _op_complete_handler(self, _, op_name):
        self.scale.set_visible(False)
        self.details_button.set_visible(False)
        self.op_name_label.set_label(f"{self.op.op_name} is complete 󱁖")

    def _handle_click(self):
        is_revealed = self.detail_content.get_reveal_child()
        self.detail_content.set_reveal_child(not is_revealed)
        if not is_revealed:
            self.details_button.set_label("▾")
        else:
            self.details_button.set_label("▸")


class BackgroundOpProgressPopup(PopupWindow):
    """Background operations popup."""

    def __init__(self, parent, pointing_to, **kwargs):
        super().__init__(
            parent=parent,
            pointing_to=pointing_to,
            layer="top",
            name="background-op-popup-window",
            type="popup",
            anchor="top",
            margin="15px 0 0 0",
            title="fabric-background-op-popup",
            visible=False,
            v_expand=False,
            h_expand=False,
            **kwargs,
        )

        self.main_content = Box(
            name="background-op-popup-content",
            orientation="v",
            h_expand=True,
            v_expand=True,
        )
        self.tooltip_label = Label(name="single-op-tooltip", label="")
        self.background_ops_list = {}
        self.background_ops_box = Box(
            orientation="v", spacing=10, h_expand=True, v_expand=True
        )

        self.main_content.add(self.tooltip_label)
        self.main_content.add(self.background_ops_box)

        self.overlay_revealer = HackedRevealer(
            child=self.main_content,
            bezier_curve=(0.3, -0.06, 0, 1.02),
            duration=0.450,
        )
        self.add(self.overlay_revealer)

    def refresh_ops(self, ops_just_completed=False):
        """Clear and repopulate the popup with current background operations."""
        # Remove existing items safely
        for child in self.background_ops_box.children:
            self.background_ops_box.remove(child)
            child.destroy()
        self.background_ops_list.clear()

        data = BackgroundOpService().list_background_ops()
        count = len(data)

        if count == 0:
            if not ops_just_completed:
                self.tooltip_label.set_label("No active background operations")
            self.tooltip_label.set_visible(True)
            self.background_ops_box.set_visible(False)
        elif count == 1:
            self.tooltip_label.set_label(f"{data[0].op_name}: {data[0].display_text}")
            self.tooltip_label.set_visible(True)
            self.background_ops_box.set_visible(False)
        else:
            self.tooltip_label.set_visible(False)
            self.background_ops_box.set_visible(True)
            for op in data:
                new_obj = BackgroundOpItem(op)
                self.background_ops_list[op.op_name] = new_obj
                self.background_ops_box.add(new_obj)

    def set_tooltip_for_all_ops_completion(self, text):
        """To set tooltip when everything is complete."""
        self.tooltip_label.set_label(text)
        self.tooltip_label.set_visible(True)
        self.background_ops_box.set_visible(False)
