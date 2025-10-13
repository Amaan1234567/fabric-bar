"""contains notification Popups widget and the window that it belongs to"""

from os import path

from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.notifications.service import Notification
from fabric.widgets.revealer import Revealer
from fabric.utils import invoke_repeater
from gi.repository import GdkPixbuf, GLib, Gtk
from custom_widgets.image_rounded import CustomImage
from helpers.helper_functions import pixbuf_cropping_if_image_is_not_1_1,truncate

NOTIFICATION_TIMEOUT = 3 * 1000
NOTIFICATION_TIMEOUT_WITH_ACTIONS = 5 * 1000
NOTIFICATION_IMAGE_SIZE = 160
NOTIFICATION_BUTTONS_WRAP_THRESHOLD = 2

class NotificationPopup(Box):
    """the notification popup"""

    def __init__(self, notification: Notification, **kwargs):
        super().__init__(
            name="notification",
            orientation="v",
            spacing=5,
            h_align="fill",
            h_expand=True,
            v_expand=True,
            size=(0, -1),
        )

        self.column_content = Box(
            orientation="v",
            spacing=5,
            h_align="fill",
            h_expand=True,
            v_expand=True,
        )
        self.row_content = Box(
            name="notification-content",
            orientation="h",
            spacing=10,
            h_align="fill",
            h_expand=True,
            v_expand=True,
        )
        self._notification = notification
        self.image = None
        if image_pixbuf := self._load_notification_pixbuf(self._notification):
            self.image = CustomImage(
                name="notification-thumbnail",
                pixbuf=image_pixbuf.scale_simple(
                    NOTIFICATION_IMAGE_SIZE,
                    NOTIFICATION_IMAGE_SIZE,
                    GdkPixbuf.InterpType.BILINEAR,
                ),
            )
            self.row_content.add(self.image)

        self.right_content = Box(
            name="notification-info",
            orientation="v",
            h_expand=True,
            v_expand=True,
            v_align="fill",
        )
        self.notification_title = Label(
            name="notification-title",
            label=truncate(self._notification.summary,20),
            h_align="fill",
            line_wrap="word"
        )
        self.notification_dynamic_pad = Box(v_expand=True)
        self.notification_body = Label(
            name="notification-body",
            label=truncate(self._notification.body,50),
            h_align="fill",
            h_expand=True,
            line_wrap="word-char",
        )
        self.right_content.children = [
            self.notification_title,
            self.notification_dynamic_pad,
            self.notification_body,
        ]
        self.row_content.add(self.right_content)
        self.close_button = Button(
            "󰅙",
            name="notification-close-button",
            v_align="start",
            h_align="end",
            on_clicked=lambda *_: self._notification.close(),
        )
        self.row_content.add(self.close_button)
        self.column_content.add(self.row_content)
        if actions := self._notification.actions:
            self.right_content.add(
                Box(
                    name="action-buttons",
                    spacing=4,
                    orientation="v",
                    children=[
                        Box(spacing=4,orientation='h',children = [
                            Button(
                            h_expand=True,
                            v_expand=True,
                            label=action.label,
                            on_clicked=lambda *_, action=action: action.invoke(),
                        )
                        for action in actions[i:i+NOTIFICATION_BUTTONS_WRAP_THRESHOLD]
                        ])
                        for i in range(0,len(actions),NOTIFICATION_BUTTONS_WRAP_THRESHOLD)
                    ],
                )
            )
        self.revealer = Revealer(
            child=self.column_content,
            child_revealed=False,
            transition_duration=250,
            transition_type="slide-down",
        )
        self.add(self.revealer)

        self._notification.connect(
            "closed",
            self._close_notification,
        )

        # automatically close the notification after the timeout period
        if len(self._notification.actions) != 0:
            invoke_repeater(
                NOTIFICATION_TIMEOUT_WITH_ACTIONS,
                lambda: self._notification.close("expired"),
                initial_call=False,
            )
        else:
            invoke_repeater(
                NOTIFICATION_TIMEOUT,
                lambda: self._notification.close("expired"),
                initial_call=False,
            )

    def _delete_self(self):
        parent.remove(self) if (parent := self.get_parent()) else None

    def _close_notification(self):
        self.revealer.set_reveal_child(False)

        GLib.timeout_add(300, self._delete_self)
        GLib.timeout_add(300, self.destroy)

    def _load_notification_pixbuf(
        self, notification: Notification
    ) -> GdkPixbuf.Pixbuf | None:
        try:
            if getattr(notification, "image_pixbuf", None):
                return pixbuf_cropping_if_image_is_not_1_1(notification.image_pixbuf)

            if getattr(notification, "image_data", None):
                loader = GdkPixbuf.PixbufLoader()
                loader.write(notification.image_data, 1)
                loader.close()
                return pixbuf_cropping_if_image_is_not_1_1(loader.get_pixbuf())

            if getattr(notification, "image_path", None) and path.exists(
                notification.image_path
            ):
                return GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    notification.image_path,
                    NOTIFICATION_IMAGE_SIZE,
                    NOTIFICATION_IMAGE_SIZE,
                    True,
                )

            if getattr(notification, "app_icon", None):
                app_icon = notification.app_icon
                # Try as file path first
                if path.exists(app_icon):
                    return GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        app_icon,
                        NOTIFICATION_IMAGE_SIZE,
                        NOTIFICATION_IMAGE_SIZE,
                        True,
                    )
                # Otherwise, try from icon theme
                theme = Gtk.IconTheme.get_default()
                info = theme.lookup_icon(app_icon, NOTIFICATION_IMAGE_SIZE, 0)
                if info:
                    return info.load_icon()
        except Exception as e:
            print(f"Failed to load notification icon: {e}")

        return None
