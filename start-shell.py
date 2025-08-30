from widgets.bar import StatusBar
from widgets.corners import ScreenCorners
from widgets.borders import ScreenBorders
from fabric.utils.helpers import monitor_file, get_relative_path
from fabric import Application
from modules.right_module.right_module import control_center
from modules.notification.notification_popup import NotificationPopupWindow
import loguru

if __name__ == "__main__":
    loguru.logger.disable("")
    bar = StatusBar()
    corners = ScreenCorners()
    borders = ScreenBorders()
    notifications = NotificationPopupWindow()
    app = Application("hypr-fabric-bar", windows=[bar,corners,borders,control_center,notifications])

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