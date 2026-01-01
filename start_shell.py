"""main python file that initialised the whole UI"""

import sys
from loguru import logger

from fabric.utils.helpers import monitor_file, get_relative_path
from fabric import Application
from modules.control_center import control_center
from modules.control_center.control_center import ControlCenter
from modules.notification.notification_window import NotificationPopupWindow
from utils.application_data_holder import Data
from services.notification_service import NotificationService
from services.playerctlservice import SimplePlayerctlService
from services.networkservice import NetworkService
from widgets import volume_osd
from widgets import brightness_osd
from widgets.top_bar import TopBar
from widgets.corners import ScreenCorners
from widgets.volume_osd import VolumeOSD
from widgets.brightness_osd import BrightnessOSD

if __name__ == "__main__":
    logger.remove()

    # Add a new sink, filtering out messages from 'noisy_module'
    logger.add(
        sys.stderr,
        filter=lambda record: record["name"] != "fabric.widgets.svg",
        level="INFO",
    )
    app_data = Data(
        notification_service=NotificationService(),
        playerctl_service=SimplePlayerctlService(),
        network_service=NetworkService(),
        control_center=None,
    )
    control_center = ControlCenter(app_data=app_data)
    app_data.control_center = control_center
    status_bar = TopBar(app_data)
    corners = ScreenCorners()
    notifications = NotificationPopupWindow(app_data)
    volume_osd = VolumeOSD(status_bar, status_bar.logout_btn)
    brightness_osd = BrightnessOSD(status_bar, status_bar.logout_btn)
    app = Application(
        "hypr-fabric-bar",
        windows=[
            status_bar,
            corners,
            control_center,
            notifications,
            volume_osd,
            brightness_osd,
        ],
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
            "changed",
            lambda *a: (
                app.set_stylesheet_from_file(style_path),
                app.set_stylesheet_from_file(get_relative_path("styles/style.css")),
            ),
        )
    app.run()
