from fabric.utils import monitor_file, get_relative_path
from fabric.widgets.label import Label
from fabric.widgets.box import Box
from fabric.widgets.wayland import WaylandWindow
from fabric import Application


class window(WaylandWindow):
    def __init__(self, **kwargs):
        super().__init__(margin="8px 8px 8px 8px", **kwargs)
        self.label = Box(children=[Label(label="asdas")])
        self.count = 0
        monitor_file(get_relative_path("./test_file.txt"), self.callback)
        self.add(self.label)

    def callback(self):
        self.count += 1
        self.label.set_label(self.count)
        print("detected change")


if __name__ == "__main__":
    window_ = window()
    app = Application(window=window_)
    app.run()
