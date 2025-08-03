import fabric
from fabric.widgets.datetime import DateTime
from fabric.widgets.box import Box

class Clock(Box):
    def __init__(self, **kwargs):
        super().__init__(name="clock", **kwargs)

        self.clock = DateTime(format_string = "%a, %b %d  %I:%M %p")
        self.children = self.clock
        

