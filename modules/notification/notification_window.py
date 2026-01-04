"""holds the notification window widget"""

from typing import cast
from fabric.notifications.service import Notification
from fabric.widgets.wayland import WaylandWindow
from fabric.widgets.box import Box
from modules.notification.notification_popup import NotificationPopup
from services.notification_service import NotificationService


class NotificationPopupWindow(WaylandWindow):
    """The window that holds all the Notification Popups"""

    def __init__(self, app_data, **kwargs):
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
        self.app_data = app_data
        self.notifications_service: NotificationService = app_data.notification_service
        self.notifications_service.connect("notification-added", self._add_notification)

        self.content = Box(
            orientation="v",
            spacing=20,
            v_expand=True,
            v_align="start",
            h_align="fill",
            size=2,
        )
        self.add(self.content)
        self._dnd_on = self.notifications_service.dnd
        self.notifications_service.connect("dnd_toggled", self._set_dnd_status)

    def _set_dnd_status(self, _, is_dnd_on):
        print(is_dnd_on)
        self._dnd_on = is_dnd_on
        print(self._dnd_on)

    def _add_notification(self, _, notification):
        if self._dnd_on:
            return

        notification = NotificationPopup(
            cast(
                Notification,
                notification,
            )
        )
        self.content.add(notification)
        notification.revealer.set_reveal_child(True)
