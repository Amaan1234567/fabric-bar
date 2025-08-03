from widgets.bar import StatusBar
from widgets.corners import ScreenCorners
from fabric.utils.helpers import monitor_file, get_relative_path
from fabric import Application
from modules.right_module.right_module import control_center
from multiprocessing import Pipe

if __name__ == "__main__":
    parent_conn , child_conn = Pipe()
    bar = StatusBar()
    corners = ScreenCorners()
    app = Application("hypr-fabric-bar", windows=[bar,corners,control_center])

    style_path = get_relative_path("./style.css")
    if style_path:
        app.set_stylesheet_from_file(style_path)
        style_monitor = monitor_file(style_path)
        style_monitor.connect(
            "changed",
            lambda *a: app.set_stylesheet_from_file(style_path)
        )

    colors_path = get_relative_path("./colors.css")
    if colors_path:
        style_monitor = monitor_file(colors_path)
        style_monitor.connect(
            "changed",
            lambda *a: app.set_stylesheet_from_file(style_path)
        ) 
    app.run()