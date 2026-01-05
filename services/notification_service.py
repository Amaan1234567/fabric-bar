"""Notification Service Module"""

from typing import Dict, cast
from loguru import logger
from gi.repository import GLib  # type: ignore
from fabric import Property
from fabric.notifications.service import (
    Notifications,
    Notification,
    NotificationCloseReason,
)
from fabric.core.service import Service, Signal


class NotificationService(Service):
    """Service to manage notifications."""

    @Signal
    def changed(self) -> None:
        """Emitted when the notifications list changes."""

    @Signal
    def notification_added(self, notification: Notification) -> None:
        """Emitted when a new notification is added."""
        self.notify("notifications")

    @Signal
    def notification_dismissed(self, notification_id: int) -> None:
        """Emitted when a notification is removed."""
        self.notify("notifications")

    @Signal
    def all_notifications_dismissed(self) -> None: ...

    @Signal
    def dnd_toggled(self, dnd_is_on: bool) -> None:
        """dnd toggle signal"""

    @Property(Dict[int, Notification], "readable")
    def notifications(self) -> Dict[int, Notification]:
        """Get the current list of notifications."""
        return self._notifications

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._notifications = {}
        self._notifications_service = Notifications()
        self._notifications_service.connect(
            "notification-added", self._on_notification_added
        )
        # self._notifications_service.connect(
        #     "notification-removed", self._on_notification_removed
        # )
        self._notifications_service.connect(
            "notification-closed", self._on_notification_closed
        )

        self._is_dnd_on = False

    @property
    def dnd(self):
        """dnd property"""
        return self._is_dnd_on

    @dnd.setter
    def dnd(self, dnd):
        self.dnd_toggled.emit(dnd)
        self._is_dnd_on = dnd

    def _on_notification_added(self, _, notification_id: int) -> None:
        notification: Notification = (
            self._notifications_service.get_notification_from_id(notification_id)
        )  # type: ignore
        self._notifications[notification_id] = notification
        self.notification_added.emit(notification)

    def _on_notification_removed(self, _, notification_id: int, *args) -> None:
        if notification_id in self._notifications:
            print("inside removed")
            # self.notification_added.emit(self._notifications.pop(notification_id))
            self.notification_dismissed.emit(notification_id)

    def _on_notification_closed(self, _, notification_id: int, reason: object) -> None:
        close_reason: NotificationCloseReason = NotificationCloseReason(
            cast(int, reason)
        )
        logger.info(f"Notification {notification_id} closed with reason {close_reason}")
        if (
            notification_id in self._notifications.keys()  # type : ignore
            and close_reason == NotificationCloseReason.DISMISSED_BY_USER
        ):
            self._notifications.pop(notification_id)
            self.notification_dismissed.emit(notification_id)

    def dismiss_notification(self, notification_id: int) -> None:
        """Dismiss a notification by its ID."""
        if notification_id in self._notifications:
            GLib.idle_add(
                self._notifications_service.close_notification,
                notification_id,
                NotificationCloseReason.DISMISSED_BY_USER,
            )

    def dismiss_all_notifications(self) -> None:
        """Dismiss all notifications."""
        self._notifications = {}
        self.all_notifications_dismissed.emit()

    def get_notification_from_id(self, notification_id: int) -> Notification:
        """Get a notification by its ID."""
        print(notification_id)
        return self._notifications[notification_id]

    def toggle_dnd(self):
        """function to toggle dnd"""
        print("toggling")
        self._is_dnd_on = not self._is_dnd_on
        print("dnd: ", self._is_dnd_on)
        self.dnd_toggled.emit(self._is_dnd_on)
