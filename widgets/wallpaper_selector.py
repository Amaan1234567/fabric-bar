
from wsgiref.util import is_hop_by_hop
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.scrolledwindow import ScrolledWindow

class WallpaperSelector(Window):
    """wallpaper selector widget"""
    def __init__(self,**kwargs):
        super().__init__(
            name="wallpaper-selector-window",
            title="wallpaper-selector",
            layer="overlay",
            anchor="center",
            exclusivity="auto",
            keyboard_mode="on-demand",
            visible=False,
            type="popup",**kwargs
        )

        self.content = Box(name="wallpaper-selector-container",)
        self.scrolling_container = ScrolledWindow(name="wallpaper-selector-scroll-container")
        self.label1 = Button(label="testing1",on_clicked=lambda _: print("pressed "))
        self.label2 = Button(label="testing2",on_clicked=lambda _: print("pressed "))
        self.label3 = Button(label="testing3",on_clicked=lambda _: print("pressed "))
        self.box = Box(orientation="h",spacing=20,children=[self.label1,self.label2,self.label3])

        self.scrolling_container.children = [self.box]
        self.content.add(self.scrolling_container)
        self.children = [self.content]
        self.is_hidden=True
    
    def toggle_window(self):
        """function to toggle window"""
        if self.is_hidden:
            self.show_all()
            self.grab_focus()
        else:
            self.hide()
        self.is_hidden = not self.is_hidden
