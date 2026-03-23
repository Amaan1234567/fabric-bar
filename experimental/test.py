from fabric import Application
from fabric.widgets.wayland import WaylandWindow
from fabric.widgets.box import Box
from fabric.utils import get_relative_path
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.entry import Entry


class TextScollBox(Box):
    def __init__(self, **kwargs):
        super().__init__(orientation="v", **kwargs)
        self.scrolled_window = ScrolledWindow(name="scroll-window",h_scrollbar_policy="automatic",v_scrollbar_policy="never")
        self.text_box = Label(name="text",orientation="h", spacing=10,label="testing label label testing 12 3 4 54 ")
        self.scrolled_window.children=[self.text_box]
        self.entry = Entry()
        self.add(self.scrolled_window)
        self.add(Button(label="start-scroll",on_clicked=self.start_scroll))
        self.add(Button(label="end-scroll",on_clicked=self.end_scroll))
        self.add(self.entry)
        self.add(Button(label="change label",on_clicked=self.change_label))
        print(6/len("testing label label testing 12 3 4 54 "))
        
        self.set_css(self.text_box.get_label())
    
    def change_label(self):
        self.text_box.set_label(self.entry.get_text())
        self.set_css(self.entry.get_text())

    def set_css(self,label):
        ctx = self.text_box.get_style_context()
        
        self.text_box.set_style("transition: "+"margin "+str(0.01*self.text_box.get_allocated_width())+"s "+" linear;")


    def start_scroll(self, button):
        print("adding class scrolling")
        self.text_box.set_style("transition: "+"margin "+str(0.01*self.text_box.get_allocated_width())+"s "+" linear;\n"+"margin-left: "+str(self.get_allocated_width()-self.text_box.get_allocated_width())+"px;")
        # self.text_box.get_style_context().set_property("margin-left",str(200-self.text_box.get_allocated_width()))
    def end_scroll(self, button):
        print(0.01*self.text_box.get_allocated_width())
        print("removing class scrolling")
        self.text_box.set_style("transition: "+"margin "+str(0.01*self.text_box.get_allocated_width())+"s "+" linear;\n"+"margin-left: "+"10"+"px;")
        # self.text_box.get_style_context().remove_class("scrolling")

if __name__ == "__main__":
    app = Application(
        "notifications",
        WaylandWindow(
            margin="8px 8px 8px 8px",
            anchor="top",
            child=Box(
                size=(200,200),  # so it's not ignored by the compositor
                spacing=4,
                orientation="v",
                children=[TextScollBox()],
            ),
            visible=True,
            all_visible=True,
            keyboard_mode="on-demand"
        ),
    )

    # app.set_stylesheet_from_file(get_relative_path("../styles/style.css"))

    app.run()
