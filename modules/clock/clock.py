import fabric
from fabric.widgets.datetime import DateTime
from fabric.widgets.box import Box

class Clock(Box):
    def __init__(self, **kwargs):
        super().__init__(name="clock", **kwargs)

        self.clock = DateTime(format_string = "%a, %b %d  %I:%M %p")
        self.clock.connect(
            "state-flags-changed",
            lambda btn, *_: (
                btn.set_cursor("pointer")
                if btn.get_state_flags() & 2  # type: ignore
                else btn.set_cursor("default"),
            ),
        )
        self.children = self.clock
        

