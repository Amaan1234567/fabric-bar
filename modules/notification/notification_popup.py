from typing import cast
from fabric.notifications.service import Notifications, Notification
from fabric.widgets.box import Box
from fabric.widgets.flowbox import FlowBox
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.revealer import Revealer
from fabric.widgets.wayland import WaylandWindow
from fabric.widgets.revealer import Revealer
from fabric.utils import invoke_repeater
from gi.repository import GdkPixbuf, GLib, Gtk
from os import path
from custom_widgets.image_rounded import CustomImage

NOTIFICATION_TIMEOUT = 3 * 1000
NOTIFICATION_IMAGE_SIZE = 160


class NotificationPopup(Box):
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
            label=self._notification.summary,
            h_align="fill",
            max_chars_width=30,
            line_wrap="word-char",
            ellipsization="end",
        )
        self.notification_dynamic_pad = Box(v_expand=True)
        self.notification_body = Label(
            name="notification-body",
            label=self._notification.body,
            h_align="fill",
            line_wrap="word-char",
            chars_width=20,
            ellipsization="end",
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
            self.column_content.add(
                Box(
                    name="action-buttons",
                    spacing=4,
                    orientation="h",
                    children=[
                        Button(
                            h_expand=True,
                            v_expand=True,
                            label=action.label,
                            on_clicked=lambda *_, action=action: action.invoke(),
                        )
                        for action in actions
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
            self.close_notification,
        )

        # automatically close the notification after the timeout period
        invoke_repeater(
            NOTIFICATION_TIMEOUT,
            lambda: self._notification.close("expired"),
            initial_call=False,
        )

    def close_notification(self):
        self.revealer.set_reveal_child(False)

        def delete_self():
            parent.remove(self) if (parent := self.get_parent()) else None

        GLib.timeout_add(300, delete_self)
        GLib.timeout_add(300, self.destroy)

    def pixbuf_cropping_if_image_is_not_1_1(self, original_pixbuf): # remove this and use helper function
        try:

            # Get original dimensions
            original_width = original_pixbuf.get_width()
            original_height = original_pixbuf.get_height()

            # Check if aspect ratio is 1:1
            if original_width == original_height:
                # Square image - just scale it
                pic2 = original_pixbuf.scale_simple(
                    NOTIFICATION_IMAGE_SIZE,
                    NOTIFICATION_IMAGE_SIZE,
                    GdkPixbuf.InterpType.BILINEAR,
                )
            else:
                # Non-square image - center crop first, then scale
                crop_size = min(original_width, original_height)
                crop_x = (original_width - crop_size) // 2
                crop_y = (original_height - crop_size) // 2

                # Create cropped pixbuf
                cropped_pixbuf = GdkPixbuf.Pixbuf.new(
                    GdkPixbuf.Colorspace.RGB,
                    original_pixbuf.get_has_alpha(),
                    original_pixbuf.get_bits_per_sample(),
                    crop_size,
                    crop_size,
                )

                # Copy the center square
                original_pixbuf.copy_area(
                    crop_x, crop_y, crop_size, crop_size, cropped_pixbuf, 0, 0
                )

                # Scale the cropped square
                pic2 = cropped_pixbuf.scale_simple(
                    NOTIFICATION_IMAGE_SIZE,
                    NOTIFICATION_IMAGE_SIZE,
                    GdkPixbuf.InterpType.BILINEAR,
                )

            return pic2

        except Exception as e:
            print(f"Error processing image: {e}")
            return None

    def _load_notification_pixbuf(
        self, notification: Notification
    ) -> GdkPixbuf.Pixbuf | None:
        try:
            if getattr(notification, "image_pixbuf", None):
                return self.pixbuf_cropping_if_image_is_not_1_1(
                    notification.image_pixbuf
                )

            if getattr(notification, "image_data", None):
                loader = GdkPixbuf.PixbufLoader()
                loader.write(notification.image_data)
                loader.close()
                return self.pixbuf_cropping_if_image_is_not_1_1(loader.get_pixbuf())

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


class NotificationPopupWindow(WaylandWindow):
    def __init__(self, **kwargs):
        super().__init__(
            title="fabric-notifications",
            name="notifications-popup",
            type="popup",
            margin="26px 26px 26px 26px",
            layer="top",
            anchor="top right",
            exclusivity="none",
            v_expand=True,
            **kwargs,
        )

        self.notifications_service = Notifications()
        self.notifications_service.connect("notification-added", self.add_notification)

        self.content = Box(
            orientation="v",
            spacing=20,
            v_expand=True,
            v_align="start",
            h_align="fill",
            size=2,
        )
        self.add(self.content)

    def add_notification(self, notifs_service, nid):

        # print(cast(
        #         Notification,
        #         notifs_service.get_notification_from_id(nid),
        #     ).serialize())

        self.notification = NotificationPopup(
            cast(
                Notification,
                notifs_service.get_notification_from_id(nid),
            )
        )
        self.content.add(self.notification)
        self.notification.revealer.set_reveal_child(True)
