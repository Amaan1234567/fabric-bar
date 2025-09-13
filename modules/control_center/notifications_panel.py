import fabric
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.scrolledwindow import ScrolledWindow
import subprocess
import json
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gio


class NotificationItem(Box):
    def __init__(self, notification_data, on_dismiss=None):
        super().__init__(
            name="notification-item",
            orientation="horizontal",
            spacing=8,
        )

        self.notification_data = notification_data
        self.on_dismiss = on_dismiss

        # App icon using Nerd Font
        self.app_icon = Label(
            name="notification-app-icon",
            label=self.get_app_icon(notification_data.get("app_name", "Unknown App")),
        )

        # Content box
        self.content_box = Box(
            name="notification-content-box",
            orientation="vertical",
            spacing=4,
        )

        # App name and time
        self.header_box = Box(
            name="notification-header-box",
            orientation="horizontal",
            spacing=8,
        )

        self.app_name_label = Label(
            name="notification-app-name-label",
            label=notification_data.get("app_name", "Unknown App"),
        )

        self.time_label = Label(
            name="notification-time-label",
            label=notification_data.get("time", ""),
        )

        self.header_box.children = [self.app_name_label, self.time_label]

        # Title and body
        self.title_label = Label(
            name="notification-title-label",
            label=notification_data.get("title", ""),
        )

        self.body_label = Label(
            name="notification-body-label",
            label=notification_data.get("body", ""),
        )

        self.content_box.children = [
            self.header_box,
            self.title_label,
            self.body_label,
        ]

        # Actions box
        self.actions_box = Box(
            name="notification-actions-box",
            orientation="vertical",
            spacing=4,
        )

        # Dismiss button with Nerd Font icon
        self.dismiss_button = Button(
            name="notification-dismiss-button",
            label="",  # Close/X icon
            on_clicked=self.dismiss_notification,
        )

        # Action buttons if available
        actions = notification_data.get("actions", [])
        for action in actions:
            action_button = Button(
                name="notification-action-button",
                label=action.get("label", "Action"),
                on_clicked=lambda btn, action_id=action.get("id"): self.perform_action(
                    action_id
                ),
            )
            self.actions_box.children.append(action_button)

        self.actions_box.children.append(self.dismiss_button)

        self.children = [
            self.app_icon,
            self.content_box,
            self.actions_box,
        ]

    def get_app_icon(self, app_name):
        """Get appropriate Nerd Font icon based on app name"""
        app_name_lower = app_name.lower()

        # Map common app names to Nerd Font icons
        icon_map = {
            "spotify": "",  # Spotify icon
            "discord": "󰙯",  # Discord icon
            "telegram": "",  # Telegram icon
            "firefox": "",  # Firefox icon
            "chrome": "",  # Chrome icon
            "chromium": "",  # Chrome icon
            "code": "",  # VSCode icon
            "terminal": "",  # Terminal icon
            "system": "",  # System/settings icon
            "mail": "",  # Mail icon
            "thunderbird": "",  # Mail icon
            "steam": "",  # Steam icon
            "github": "",  # GitHub icon
            "git": "",  # Git icon
            "music": "",  # Music note icon
            "video": "",  # Video icon
            "image": "",  # Image icon
            "file": "",  # File icon
            "update": "",  # Update/download icon
            "calendar": "",  # Calendar icon
            "clock": "",  # Clock icon
            "battery": "",  # Battery icon
            "network": "",  # Network icon
            "bluetooth": "",  # Bluetooth icon
            "audio": "",  # Audio icon
        }

        # Try to match app name with icon
        for key, icon in icon_map.items():
            if key in app_name_lower:
                return icon

        # Default generic app icon
        return ""

    def dismiss_notification(self, button):
        """Dismiss this notification"""
        if self.on_dismiss:
            self.on_dismiss(self)

    def perform_action(self, action_id):
        """Perform notification action"""
        try:
            subprocess.run(
                [
                    "gdbus",
                    "call",
                    "--session",
                    "--dest=org.freedesktop.Notifications",
                    "--object-path=/org/freedesktop/Notifications",
                    "--method=org.freedesktop.Notifications.ActionInvoked",
                    str(self.notification_data.get("id", 0)),
                    action_id,
                ]
            )
        except:
            pass


class NotificationsPanel(Box):
    def __init__(self):
        super().__init__(
            name="notifications-panel-container",
            orientation="vertical",
            spacing=8,
        )

        # Header
        self.header_box = Box(
            name="notifications-header-box",
            orientation="horizontal",
            spacing=8,
        )

        self.notifications_icon = Label(
            name="notifications-icon",
            label="",  # Bell/notification icon
        )

        self.notifications_title = Label(
            name="notifications-title-label",
            label="Notifications",
        )

        self.count_label = Label(
            name="notifications-count-label",
            label="",
        )

        # Clear all button with Nerd Font icon
        self.clear_all_button = Button(
            name="notifications-clear-all-button",
            label=" Clear All",  # Trash/clear icon
            on_clicked=self.clear_all_notifications,
        )

        self.header_box.children = [
            self.notifications_icon,
            self.notifications_title,
            self.count_label,
            self.clear_all_button,
        ]

        # Scrolled window for notifications
        self.scrolled_window = ScrolledWindow(
            name="notifications-scrolled-window",
            min_content_height=200,
            max_content_height=400,
        )

        # Notifications container
        self.notifications_box = Box(
            name="notifications-list-box",
            orientation="vertical",
            spacing=4,
        )

        self.scrolled_window.child = self.notifications_box

        # Empty state with Nerd Font icon
        self.empty_label = Label(
            name="notifications-empty-label",
            label=" No new notifications",  # Bell slash icon
        )

        self.children = [
            self.header_box,
            self.scrolled_window,
        ]

        # Sample notifications for demo
        self.notifications = []
        self.load_sample_notifications()
        self.update_display()

        # Setup D-Bus monitoring for real notifications
        self.setup_notification_monitoring()

    def setup_notification_monitoring(self):
        """Setup D-Bus monitoring for notifications"""
        try:
            # This would require proper D-Bus setup for notification monitoring
            # For now, we'll use a timer to simulate notifications
            GLib.timeout_add_seconds(30, self.check_for_new_notifications)
        except:
            pass

    def load_sample_notifications(self):
        """Load some sample notifications for demo"""
        import datetime

        sample_notifications = [
            {
                "id": 1,
                "app_name": "Spotify",
                "title": "Now Playing",
                "body": "The Weeknd - Blinding Lights",
                "time": "2 min ago",
                "actions": [{"id": "play", "label": "⏵"}, {"id": "next", "label": "⏭"}],
            },
            {
                "id": 2,
                "app_name": "Discord",
                "title": "New Message",
                "body": "Friend: Hey, want to game tonight?",
                "time": "5 min ago",
                "actions": [{"id": "reply", "label": "Reply"}],
            },
            {
                "id": 3,
                "app_name": "System",
                "title": "Update Available",
                "body": "23 packages can be upgraded",
                "time": "1 hour ago",
                "actions": [{"id": "update", "label": "Update Now"}],
            },
        ]

        self.notifications = sample_notifications

    def check_for_new_notifications(self):
        """Check for new notifications (placeholder)"""
        # In a real implementation, this would query the notification daemon
        return True

    def add_notification(self, notification_data):
        """Add a new notification"""
        self.notifications.insert(0, notification_data)
        self.update_display()

    def remove_notification(self, notification_item):
        """Remove a notification"""
        # Find and remove the notification data
        for i, notif in enumerate(self.notifications):
            if notif.get("id") == notification_item.notification_data.get("id"):
                self.notifications.pop(i)
                break

        self.update_display()

    def clear_all_notifications(self, button):
        """Clear all notifications"""
        self.notifications.clear()
        self.update_display()

        # Update main notifications icon to show empty state
        self.notifications_icon.label = ""  # Bell slash for no notifications

    def update_display(self):
        """Update the notifications display"""
        # Clear current display
        for child in self.notifications_box.children[:]:
            self.notifications_box.remove(child)

        if not self.notifications:
            # Show empty state
            self.notifications_box.children = [self.empty_label]
            self.count_label.label = ""
            self.notifications_icon.label = ""  # Bell slash for empty
        else:
            # Show notifications
            notification_widgets = []
            for notif_data in self.notifications:
                notif_widget = NotificationItem(
                    notif_data, on_dismiss=self.remove_notification
                )
                notification_widgets.append(notif_widget)

            self.notifications_box.children = notification_widgets
            self.count_label.label = f"({len(self.notifications)})"

            # Update main icon based on notification count
            if len(self.notifications) > 5:
                self.notifications_icon.label = ""  # Bell with badge
            else:
                self.notifications_icon.label = ""  # Regular bell
