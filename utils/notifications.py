"""Reusable desktop notification helper over org.freedesktop.Notifications."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import dbus
from gi.repository import GLib  # type: ignore
from loguru import logger

NOTIFY_BUS_NAME = "org.freedesktop.Notifications"
NOTIFY_OBJ_PATH = "/org/freedesktop/Notifications"
NOTIFY_IFACE = "org.freedesktop.Notifications"


class NotificationHelper:
    """Sends desktop notifications asynchronously and dispatches action callbacks."""

    def __init__(self, app_name: str = "SystemService") -> None:
        self.app_name = app_name
        self._bus: dbus.SessionBus | None = None
        self._iface: dbus.Interface | None = None
        self._action_callbacks: dict[int, dict[str, Callable[[], None]]] = {}
        self._signals_connected = False

    def _ensure_bus(self) -> dbus.Interface | None:
        if self._iface is not None:
            return self._iface
        try:
            self._bus = dbus.SessionBus()
            proxy = self._bus.get_object(NOTIFY_BUS_NAME, NOTIFY_OBJ_PATH)
            self._iface = dbus.Interface(proxy, NOTIFY_IFACE)
            if not self._signals_connected:
                self._bus.add_signal_receiver(
                    self._on_action_invoked,
                    signal_name="ActionInvoked",
                    dbus_interface=NOTIFY_IFACE,
                    bus_name=NOTIFY_BUS_NAME,
                    path=NOTIFY_OBJ_PATH,
                )
                self._bus.add_signal_receiver(
                    self._on_notification_closed,
                    signal_name="NotificationClosed",
                    dbus_interface=NOTIFY_IFACE,
                    bus_name=NOTIFY_BUS_NAME,
                    path=NOTIFY_OBJ_PATH,
                )
                self._signals_connected = True
            return self._iface
        except Exception as exc:
            logger.warning(f"Notifications unavailable over session D-Bus: {exc}")
            return None

    def send(
        self,
        summary: str,
        body: str = "",
        *,
        icon: str = "dialog-information",
        actions: dict[str, Callable[[], None]] | None = None,
        urgency: int = 1,
        expire_timeout: int = 8000,
        replaces_id: int = 0,
    ) -> None:
        """Send a notification asynchronously without blocking the GLib main loop."""
        iface = self._ensure_bus()
        if iface is None:
            return

        action_list: list[str] = []
        callbacks: dict[str, Callable[[], None]] = {}
        if actions:
            for key, cb in actions.items():
                action_list.extend([key, key.capitalize()])
                callbacks[key] = cb

        def _on_notified(notif_id: Any) -> None:
            if callbacks:
                self._action_callbacks[int(notif_id)] = callbacks

        def _on_notify_error(err: Exception) -> None:
            logger.error(f"Failed to send notification '{summary}': {err}")

        try:
            iface.Notify(
                self.app_name,
                replaces_id,
                icon,
                summary,
                body,
                action_list,
                dbus.Dictionary({"urgency": dbus.Byte(urgency)}, signature="sv"),
                expire_timeout,
                reply_handler=_on_notified,
                error_handler=_on_notify_error,
            )
        except Exception as exc:
            logger.error(f"Failed to dispatch notification '{summary}': {exc}")

    def _on_action_invoked(self, notif_id: Any, action_key: str) -> None:
        nid = int(notif_id)
        callbacks = self._action_callbacks.pop(nid, None)
        if not callbacks:
            return
        cb = callbacks.get(str(action_key))
        if cb:
            GLib.idle_add(self._invoke_safe, cb, str(action_key))

    @staticmethod
    def _invoke_safe(cb: Callable[[], None], action_key: str) -> bool:
        try:
            cb()
        except Exception as exc:
            logger.error(f"Notification action '{action_key}' failed: {exc}")
        return False

    def _on_notification_closed(self, notif_id: Any, _reason: Any) -> None:
        self._action_callbacks.pop(int(notif_id), None)