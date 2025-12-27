"""hold mpris popup"""

from fabric.widgets.revealer import Revealer
from modules.mpris.mpris_player_stack import MprisPlayerStack
from custom_widgets.popup_window import PopupWindow


class MprisPopup(PopupWindow):
    """mpris popup window"""

    def __init__(self, parent, pointing_to, **kwargs):
        super().__init__(
            parent=parent,
            pointing_to=pointing_to,
            layer="top",
            name="mpris-overlay-window",
            type="popup",
            anchor="top right",
            title="fabric-mpris-popup",
            visible=False,
            v_expand=False,
            h_expand=False,
            **kwargs,
        )

        self.overlay_revealer = Revealer(
            name="mpris-revealer",
            child=MprisPlayerStack(),
            transition_type="slide-down",
            transition_duration=250,
        )

        self.add(self.overlay_revealer)
