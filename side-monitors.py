"""main python file that initialised the whole UI"""

import sys
from loguru import logger

from fabric.utils.helpers import monitor_file, get_relative_path
from fabric import Application
from modules.notification.notification_window import NotificationPopupWindow
from utils.application_data_holder import Data
from services.notification_service import NotificationService
from services.playerctlservice import SimplePlayerctlService
from services.networkservice import NetworkService
from widgets.corners import ScreenCorners


if __name__ == "__main__":
    script_name = sys.argv[0]

    if len(sys.argv) <= 1 or sys.argv[1] != "--monitor-id":
        print(f"Usage: {script_name} [--monitor-id <monitor_id>]")
        exit(1)

    monitor_id = int(sys.argv[2]) if len(sys.argv) >= 2 else 0
    logger.info(f"Starting in side monitors mode on monitor {monitor_id}")
    logger.remove()

    # Add a new sink, filtering out messages from 'noisy_module'
    logger.add(
        sys.stderr,
        filter=lambda record: record["name"] != "fabric.widgets.svg",
        level="INFO",
    )
    
    corners = ScreenCorners(monitor=monitor_id)
    app = Application(
        f"hypr-fabric-bar-side-monitor-{monitor_id}",
        windows=[
            corners,
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
