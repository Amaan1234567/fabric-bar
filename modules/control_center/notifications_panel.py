import os
from loguru import logger
from fabric.widgets.box import Box
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.notifications.service import Notification
from fabric.widgets.revealer import Revealer
from fabric.utils import invoke_repeater, get_relative_path
from gi.repository import GdkPixbuf, GLib, Gtk
from custom_widgets.image_rounded import CustomImage
from helpers.helper_functions import pixbuf_cropping_if_image_is_not_1_1, truncate
from utils.variables import APP_ICON_MAP
from services.notification_service import NotificationService

NOTIFICATION_IMAGE_SIZE = 100


class NotificationItem(Box):
    """the notification item in the notifications panel"""

    def __init__(self, notification: Notification, **kwargs):
        super().__init__(
            name="notification-item",
            orientation="h",
            spacing=20,
            h_align="fill",
        )
        self._notification = notification
        self.image = None
        if image_pixbuf := self._load_notification_pixbuf(self._notification):
            self.image = CustomImage(
                name="notification-item-thumbnail",
                pixbuf=image_pixbuf.scale_simple(
                    NOTIFICATION_IMAGE_SIZE,
                    NOTIFICATION_IMAGE_SIZE,
                    GdkPixbuf.InterpType.BILINEAR,
                ),
            )
            self.add(self.image)

        self.column_content = Box(
            name="notification-item-content",
            orientation="v",
            spacing=5,
            h_align="fill",
        )

        self.title_label = Label(
            name="notification-item-title",
            label=truncate(self._notification.summary,25),
            ellipsize=True,
            line_wrap="word-char",
            max_chars_width=25,
            h_align="center",
        )
        self.column_content.add(self.title_label)

        self.body_label = Label(
            name="notification-item-body",
            label=truncate(self._notification.body,40),
            ellipsize=True,
            line_wrap="word-char",
            max_chars_width=25,
            h_align="center",
        )
        self.column_content.add(self.body_label)

        self.add(self.column_content)

    def _load_notification_pixbuf(
        self, notification: Notification
    ) -> GdkPixbuf.Pixbuf | None:
        try:
            if getattr(notification, "image_pixbuf", None):
                return pixbuf_cropping_if_image_is_not_1_1(notification.image_pixbuf)

            if getattr(notification, "image_data", None):
                loader = GdkPixbuf.PixbufLoader()
                loader.write(notification.image_data, 1)  # type: ignore
                loader.close()
                return pixbuf_cropping_if_image_is_not_1_1(loader.get_pixbuf())  # type: ignore

            if getattr(notification, "image_path", None) and os.path.exists(
                notification.image_path  # type: ignore
            ):
                logger.info("trying to find image in path")
                return pixbuf_cropping_if_image_is_not_1_1(
                    GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        notification.image_path,  # type: ignore
                        NOTIFICATION_IMAGE_SIZE,
                        NOTIFICATION_IMAGE_SIZE,
                        True,
                    )
                )

            if getattr(notification, "app_icon", None):
                app_icon = notification.app_icon
                # Try as file path first
                if os.path.exists(app_icon):
                    return GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        app_icon,
                        NOTIFICATION_IMAGE_SIZE,
                        NOTIFICATION_IMAGE_SIZE,
                        True,
                    )
                logger.info("trying to find icon in theme")
                # Otherwise, try from icon theme
                theme = Gtk.IconTheme.get_default()  # type: ignore
                info = theme.lookup_icon(app_icon, NOTIFICATION_IMAGE_SIZE, 0)
                if info:
                    icon_pixbuf = info.load_icon()
                    return pixbuf_cropping_if_image_is_not_1_1(icon_pixbuf)
        except Exception as e:
            print(f"Failed to load notification icon: {e}")
        if path := APP_ICON_MAP.get(self._notification.app_name.lower()):
            return pixbuf_cropping_if_image_is_not_1_1(
                GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    get_relative_path(f"../../{path}"),
                    NOTIFICATION_IMAGE_SIZE,
                    NOTIFICATION_IMAGE_SIZE,
                    True,
                )  # type: ignore
            )
        return pixbuf_cropping_if_image_is_not_1_1(
            GdkPixbuf.Pixbuf.new_from_file_at_scale(
                get_relative_path("../../assets/default_notification_pic.png"),
                NOTIFICATION_IMAGE_SIZE,
                NOTIFICATION_IMAGE_SIZE,
                True,
            )  # type: ignore
        )


class NotificationsPanel(ScrolledWindow):
    """the notifications panel that holds all notification items"""

    def __init__(self, app_data, **kwargs):
        super().__init__(
            name="notifications-panel",
            orientation="v",
            spacing=15,
            h_align="fill",
            kinetic_scroll=True,
        )
        self.app_data = app_data
        self.notifications_service: NotificationService = app_data.notification_service
        self.notifications_service.connect("notification-added", self._add_notification)
        self.notifications_service.connect(
            "notification-dismissed", self._load_notifications
        )

        self.content = Box(
            name="notifications-panel-content",
            orientation="v",
            spacing=15,
            h_align="fill",
        )
        self._load_notifications()

        self.add(self.content)

    def _load_notifications(self):
        """Load existing notifications into the panel."""
        self.content.children = []
        # logger.debug(self.notifications_service.notifications.values())
        for notification in self.notifications_service.notifications.values():
            logger.info(notification.serialize())
            notif_item = NotificationItem(notification)
            self.content.add(notif_item)

    def _add_notification(self, _, notification):
        """Add a new notification item to the panel."""
        logger.info("adding notification to notifications panel")
        notif_item = NotificationItem(notification)
        self.content.add(notif_item)
