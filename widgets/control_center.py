from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.box import Box
from fabric.widgets.flowbox import FlowBox
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.revealer import Revealer
from fabric.widgets.eventbox import EventBox
from gi.repository import GLib

# notify_child_revealed=lambda revealer, _: [
#                 revealer.hide(),
#                 self.set_visible(False),
#             ]
#             if not revealer.fully_revealed
#             else None,
#             notify_content=lambda revealer, _: [
#                 self.set_visible(True),
#             ]
#             if revealer.child_revealed
#             else None,

class ControlCenter(Window):
    def __init__(self, **kwargs):
        super().__init__(layer="top",
                         title="control_center",
            anchor="right top bottom",
            exclusivity="auto",
            visible=False,
            **kwargs)

        self.padding = Box(orientation='v',children=[Label(label="padding")])
        self.power_profile_toggle = Box(name="control-center",children=[Button(name="power-profile",label="Performance")])
        self.revealer: Revealer = Revealer(
            visible=True,
            name="control-center-revealer",
            transition_type='slide-left',
            transition_duration=400,
            child_revealed=False,
            
        )
        self.revealer.set_reveal_child(False)
        self.revealer.add(self.power_profile_toggle)
        self.add(self.revealer)

       

    def toggle_control_center(self):
        is_opening = not self.revealer.get_reveal_child()

        self.revealer.set_reveal_child(is_opening)
        if is_opening:
            # Make window visible immediately when opening
            self.set_visible(True)
            self.revealer.set_reveal_child(is_opening)
        else:
            # Delay hiding window until animation finishes (~500ms)
            self.revealer.set_reveal_child(is_opening)
            GLib.timeout_add(250, self.set_visible, False)  # milliseconds