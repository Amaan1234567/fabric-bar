from widgets.bar import StatusBar
from widgets.corners import ScreenCorners
from fabric.utils.helpers import monitor_file, get_relative_path
from fabric import Application
from modules.control_center import control_center
from modules.notification.notification_popup import NotificationPopupWindow
from loguru import logger
import sys

if __name__ == "__main__":
    logger.remove()

    # Add a new sink, filtering out messages from 'noisy_module'
    logger.add(sys.stderr, filter=lambda record: record["name"] != "fabric.widgets.svg")
    bar = StatusBar()
    corners = ScreenCorners()
    notifications = NotificationPopupWindow()
    app = Application(
        "hypr-fabric-bar",
        windows=[bar, corners, control_center, notifications],
    )

    style_path = get_relative_path("styles/style.css")
    if style_path:
        app.set_stylesheet_from_file(style_path)
        style_monitor = monitor_file(style_path)
        style_monitor.connect(
            "changed", lambda *a: app.set_stylesheet_from_file(style_path)
        )

    colors_path = get_relative_path("styles/colors.css")
    if colors_path:
        style_monitor = monitor_file(colors_path)
        style_monitor.connect(
            "changed", lambda *a: app.set_stylesheet_from_file(style_path)
        )
    app.run()
