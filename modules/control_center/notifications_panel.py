from operator import le
import os
from socket import SocketIO
from loguru import logger
from fabric.widgets.box import Box
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.revealer import Revealer
from fabric.notifications.service import Notification
from fabric.utils import get_relative_path
from gi.repository import GdkPixbuf, Gtk, GLib
from custom_widgets.image_rounded import CustomImage
from helpers.helper_functions import pixbuf_cropping_if_image_is_not_1_1, truncate
from utils.variables import APP_ICON_MAP
from services.notification_service import NotificationService

NOTIFICATION_IMAGE_SIZE = 120
NOTIFICATION_BUTTONS_WRAP_THRESHOLD = 2


class NotificationItem(Box):
    """the notification item in the notifications panel"""

    def __init__(self, notification: Notification, **kwargs):
        super().__init__(
            name="notification-item",
            orientation="v",
            spacing=0,
            h_align="fill",
        )
        self._notification = notification
        self.image = None
        self.top_content = Box(orientation="h", h_align="fill", spacing=10)
        if image_pixbuf := self._load_notification_pixbuf(self._notification):
            self.image = CustomImage(
                name="notification-item-thumbnail",
                pixbuf=image_pixbuf.scale_simple(
                    NOTIFICATION_IMAGE_SIZE,
                    NOTIFICATION_IMAGE_SIZE,
                    GdkPixbuf.InterpType.BILINEAR,
                ),
            )
            self.top_content.add(self.image)

        self.column_content = Box(
            name="notification-item-content",
            orientation="v",
            spacing=5,
            h_align="fill",
            h_expand=True,
            v_expand=True,
        )

        self.title_label = Label(
            name="notification-item-title",
            label=truncate(self._notification.summary, 30),
            ellipsize=True,
            line_wrap="word-char",
            max_chars_width=20,
            h_align="fill",
        )
        self.column_content.add(self.title_label)

        self.body_label = Label(
            name="notification-item-body",
            label=truncate(self._notification.body, 80),
            ellipsize=True,
            line_wrap="char",
            max_chars_width=25,
            h_align="fill",
        )
        self.column_content.add(Box(v_expand=True))
        self.column_content.add(self.body_label)
        self.top_content.add(self.column_content)
        self.buttons_box = Box(
            name="notification-item-buttons",
            orientation="v",
            spacing=0,
            h_align="center",
            v_align="fill",
        )
        self.close_button = Button(
            name="notification-item-close-button",
            label="󰅙",
            v_align="start",
            h_align="end",
            on_clicked=self._dismiss_notification,
        )
        self.revealer_button = Button(
            name="notification-item-revealer-button",
            label="",
            v_align="end",
            h_align="center",
            on_clicked=self._reveal_action_buttons,
        )
        self.buttons_box.add(self.close_button)
        self.buttons_box.add(Box(v_expand=True))
        self.action_buttons_container = Box(
            name="notification-action-buttons-container",
            orientation="h",
            h_align="fill",
            h_expand=True,
        )
        self.top_content.add(self.buttons_box)
        self.add(self.top_content)
        self.revealer_widget = Revealer(
            child=self.action_buttons_container,
            transition_type="slide-down",
            transition_duration=200,
            size=[1, -1],
        )
        if actions := self._notification.actions:
            self.action_buttons_container.add(
                Box(
                    name="action-buttons",
                    spacing=4,
                    orientation="v",
                    h_expand=True,
                    children=[
                        Box(
                            spacing=4,
                            orientation="h",
                            children=[
                                Button(
                                    h_expand=True,
                                    v_expand=True,
                                    label=action.label,
                                    on_clicked=lambda *_,
                                    action=action: action.invoke(),
                                )
                                for action in actions[
                                    i : i + NOTIFICATION_BUTTONS_WRAP_THRESHOLD
                                ]
                            ],
                        )
                        for i in range(
                            0, len(actions), NOTIFICATION_BUTTONS_WRAP_THRESHOLD
                        )
                    ],
                )
            )
            self.buttons_box.add(self.revealer_button)
            self.add(self.revealer_widget)

    def _reveal_action_buttons(self):
        if self.revealer_widget.get_child_revealed():
            self.revealer_button.set_label("")
            self.revealer_widget.set_reveal_child(False)
        else:
            self.revealer_button.set_label("")
            self.revealer_widget.set_reveal_child(True)

    def _delete_self(self):
        parent.remove(self) if (parent := self.get_parent()) else None

    def _close_notification(self):
        GLib.timeout_add(300, self._delete_self)
        GLib.timeout_add(300, self.destroy)

    def _dismiss_notification(self, _):
        """Dismiss the notification."""
        logger.info("dismissing notification from notifications panel")
        self._notification.close("dismissed-by-user")
        self._close_notification()

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


class NotificationsPanel(Box):
    """the notifications panel that holds all notification items"""

    def __init__(self, app_data, **kwargs):
        super().__init__(
            name="notifications-panel",
            orientation="v",
            spacing=15,
            h_align="fill",
        )

        self._dnd_on = False
        self.app_data = app_data
        self.notifications_service: NotificationService = app_data.notification_service
        self.notifications_service.connect("notification-added", self._add_notification)
        self.notifications_service.connect(
            "notification-dismissed", self._load_notifications
        )

        self.notifications_box = Box(
            name="notifications-panel-content",
            orientation="v",
            spacing=15,
            h_align="fill",
        )
        self.notifications_scrolled_window = ScrolledWindow(
            name="notifications-scrolled-window",
            kinetic_scroll=True,
            child=self.notifications_box,
        )
        self._load_notifications()

        self.heading = Label(
            name="notifications-panel-heading",
            label="Notifications",
            h_align="start",
        )
        self.dnd_button = Button(
            label="DND", name="dnd-button", on_clicked=self.toggle_dnd
        )
        self.clear_all_button = Button(
            label="󰎟", name="dismiss-all-button", on_clicked=self._dismiss_all
        )
        self.dnd_button_enabled = False

        self.content = Box(
            name="notifications-panel-container",
            orientation="v",
            spacing=10,
            h_align="fill",
        )

        self.title_bar = CenterBox(
            name="notifications-panel-title-bar",
            orientation="h",
            spacing=10,
            h_align="fill",
            h_expand=True,
            start_children=self.heading,
            center_children=Box(h_expand=True),
            end_children=[
                Box(spacing=10, children=[self.dnd_button, self.clear_all_button])
            ],
        )
        self.content.add(self.title_bar)
        self.content.add(self.notifications_scrolled_window)
        self.add(self.content)

    def _dismiss_all(self):
        self.notifications_box.children = []
        GLib.timeout_add(10, self.notifications_service.dismiss_all_notifications)

    def toggle_dnd(self, button):
        """Toggle Do Not Disturb mode."""
        ctx = self.dnd_button.get_style_context()
        self.notifications_service.toggle_dnd()
        if self.dnd_button_enabled:
            self.dnd_button_enabled = False
            ctx.remove_class("active")
        else:
            self.dnd_button_enabled = True
            ctx.add_class("active")

    def _load_notifications(self):
        """Load existing notifications into the panel."""
        self.notifications_box.children = []
        # logger.debug(self.notifications_service.notifications.values())
        for notification in self.notifications_service.notifications.values():
            notif_item = NotificationItem(notification)
            self.notifications_box.add(notif_item)

    def _add_notification(self, _, notification):
        """Add a new notification item to the panel."""
        if self._dnd_on:
            return

        logger.info("adding notification to notifications panel")

        notif_item = NotificationItem(notification)
        self.notifications_box.add(notif_item)
