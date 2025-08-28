from fabric.widgets.wayland import WaylandWindow
from fabric.widgets.box import Box
from fabric.widgets.label import Label

class ScreenBorders(WaylandWindow): 
    def __init__(self,**kwargs):
        super().__init__(
            layer="top",
            name="borders-window",
            anchor="top bottom left right",
            exclusivity="auto",
            type="top-level",
            pass_through=True,
            visible=True,
            all_visible=True,**kwargs)
        self.content = Box(name="screen-borders",h_expand=True,v_expand=True,h_align="fill",v_align="fill")
        # self.content.add(Label("_"))
        self.add(self.content)