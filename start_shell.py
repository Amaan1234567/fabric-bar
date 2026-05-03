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
from widgets.top_bar import TopBar
from widgets.corners import ScreenCorners
from widgets.volume_osd import VolumeOSD
from widgets.brightness_osd import BrightnessOSD # This now uses the new Service
from widgets.wallpaper_selector import WallpaperSelector

def main():
    logger.remove()

    logger.add(
        sys.stderr,
        filter=lambda record: record["name"] != "fabric.widgets.svg",
        level="INFO",
    )
    
    app_data = Data(
        notification_service=NotificationService(),
        playerctl_service=SimplePlayerctlService(),
        network_service=NetworkService(),
    )

    # Primary Monitor ID
    primary_monitor = 0

    status_bar = TopBar(app_data, monitor=primary_monitor)
    corners = ScreenCorners(monitor=primary_monitor)
    notifications = NotificationPopupWindow(app_data, monitor=primary_monitor)
    volume_osd = VolumeOSD(status_bar, status_bar.logout_btn, monitor=primary_monitor)
    
    # Updated: Passing monitor_id so it can detect if it's internal or external
    brightness_osd = BrightnessOSD(status_bar, status_bar.logout_btn, monitor_id=primary_monitor)
    
    wallpaper_selector = WallpaperSelector()
    
    app = Application(
        "hypr-fabric-bar-main",
        windows=[
            status_bar,
            corners,
            control_center,
            notifications,
            volume_osd,
            brightness_osd,
            wallpaper_selector,
        ],
    )

    @Application.action()
    def toggle_wallpaper_selector():
        wallpaper_selector.toggle_window()

    style_path = get_relative_path("styles/style.css")
    if style_path:
        app.set_stylesheet_from_file(style_path)
        style_monitor = monitor_file(style_path)
        style_monitor.connect("changed", lambda *a: app.set_stylesheet_from_file(style_path))

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

if __name__ == "__main__":
    main()