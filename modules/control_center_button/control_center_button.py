"""holds the control-center trigger button"""

from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from fabric.widgets.button import Button

from modules.control_center.control_center import ControlCenter

control_center = ControlCenter()


class ControlCenterButton(Box):
    """control center trigger button"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs, name="notification-button")

        self.content = EventBox(on_button_release_event=self._trigger_control_center)
        self.container_box = Box(orientation="h", spacing=4)
        self.notifcations = Button(label="")
        self.notifcations.connect(
            "state-flags-changed",
            lambda btn, *_: (
                (
                    btn.set_cursor("pointer")
                    if btn.get_state_flags() & 2  # type: ignore
                    else btn.set_cursor("default")
                ),
            ),
        )

        self.container_box.add(self.notifcations)
        self.content.add(self.container_box)
        self.add(self.content)

    def _trigger_control_center(self, _, __):
        control_center.toggle_control_center()
