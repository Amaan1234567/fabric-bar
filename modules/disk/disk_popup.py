"""Disk stats popup showing partition usage in aligned columns."""

from fabric.widgets.box import Box
from fabric.widgets.label import Label

from custom_widgets.popup_window import PopupWindow
from custom_widgets.HackedStackRevealer import HackedRevealer


class DiskPopup(PopupWindow):

    def __init__(self, parent, pointing_to, **kwargs):
        super().__init__(
            parent=parent,
            pointing_to=pointing_to,
            layer="top",
            name="disk-popup-window",
            type="popup",
            margin="15px 0 0 0px",
            anchor="top left",
            title="fabric-disk-popup",
            visible=False,
            v_expand=False,
            h_expand=False,
            **kwargs,
        )

        self._content = Box(
            orientation="v",
            name="disk-popup-content",
            spacing=0,
            h_expand=True,
            v_expand=True,
        )

        self.stats_label = Label(
            name="disk-stats-label",
            use_markup=True,
            h_align="start",
        )

        self._content.add(self.stats_label)

        self.overlay_revealer = HackedRevealer(
            bezier_curve=(0.3, -0.06, 0, 1.02),
            duration=0.450,
            name="disk-revealer",
            child=self._content,
        )

        self.add(self.overlay_revealer)

    def update(self, stats_markup):
        self.stats_label.set_markup(stats_markup)
