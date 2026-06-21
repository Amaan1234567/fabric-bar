"""main python file that initialised the whole UI"""

import sys

import setproctitle
from fabric import Application
from fabric.utils.helpers import get_relative_path, monitor_file
from fabric.widgets.wayland import WaylandWindow
from fabric.widgets.box import Box
from loguru import logger

from modules.control_center import control_center
from modules.notification.notification_window import NotificationPopupWindow
from modules.tab_alt_overview.windows_overview import AltTab
from services.networkservice import NetworkService
from services.notification_service import NotificationService
from services.playerctlservice import SimplePlayerctlService
from utils.application_data_holder import Data
from widgets.brightness_osd import BrightnessOSD  # This now uses the new Service
from widgets.corners import ScreenCorners
from widgets.theme_selector import ThemeSelector
from widgets.top_bar import TopBar
from widgets.volume_osd import VolumeOSD
from widgets.wallpaper_selector import WallpaperSelector


def main():
    """Entry point for the application."""
    setproctitle.setproctitle("hypr-fabric-bar-main")
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
    alttab = AltTab()
    status_bar = TopBar(app_data, monitor=primary_monitor)
    corners = ScreenCorners(monitor=primary_monitor)
    notifications = NotificationPopupWindow(app_data, monitor=primary_monitor)
    volume_osd = VolumeOSD(monitor=primary_monitor)

    # Updated: Passing monitor_id so it can detect if it's internal or external
    brightness_osd = BrightnessOSD(monitor_id=primary_monitor)

    wallpaper_selector = WallpaperSelector()
    theme_selector = ThemeSelector()

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
            theme_selector,
            alttab
        ],
    )

    @Application.action()
    def toggle_wallpaper_selector():
        wallpaper_selector.toggle_window()

    @Application.action()
    def toggle_theme_selector():
        theme_selector.toggle_window()

    @Application.action()
    def alt_tab_next():
        alttab.cmd_next()

    @Application.action()
    def alt_tab_prev():
        alttab.cmd_prev()

    @Application.action()
    def alt_tab_activate():
        alttab.cmd_activate()

    @Application.action()
    def alt_tab_cancel():
        alttab.cmd_cancel()

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


if __name__ == "__main__":
    main()
