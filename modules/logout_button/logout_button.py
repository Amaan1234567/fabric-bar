"""holds the logout button and its associated popup"""

from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.eventbox import EventBox
from custom_widgets.popup_window import PopupWindow
from custom_widgets.HackedStackRevealer import HackedRevealer as Revealer
import subprocess
from gi.repository import GLib  # type: ignore


class LogoutPopup(PopupWindow):
    """popup for logout options"""

    def __init__(self, parent, pointing_to, **kwargs):
        super().__init__(
            parent=parent,
            pointing_to=pointing_to,
            layer="top",
            type="popup",
            title="logout_popup",
            visible=False,
            **kwargs,
        )

        self._auto_hide_timer = None
        self._is_hovering = False

        self.box = Box(
            name="logout-box",
            orientation="vertical",
            spacing=5,
            children=[
                Button(
                    label="󰗽 Logout",
                    on_clicked=lambda *a: self._trigger_cmd("hyprctl dispatch exit"),
                ),
                Button(
                    label="󰤄 Suspend",
                    on_clicked=lambda *a: self._trigger_cmd("systemctl suspend"),
                ),
                Button(
                    label="󰜉 Reboot",
                    on_clicked=lambda *a: self._trigger_cmd("systemctl reboot"),
                ),
                Button(
                    label=" Shutdown",
                    on_clicked=lambda *a: self._trigger_cmd("systemctl poweroff"),
                ),
                Button(
                    label="󰌾 Lock", on_clicked=lambda *a: self._trigger_cmd("hyprlock")
                ),
            ],
        )

        self.revealer = Revealer(
            bezier_curve=(0.3, -0.06, 0, 1.02),
            duration=0.450,
            child=Box(orientation="h", children=[self.box]),
            # transition_type="slide-down",
        )

        self.add(self.revealer)

        self.connect("enter-notify-event", self.on_popup_enter)
        self.connect("leave-notify-event", self.on_popup_leave)

    def on_popup_enter(self, *_):
        """Called when the mouse enters the popup area. Sets hovering state
        and cancels auto-hide timer."""
        self._is_hovering = True
        self._cancel_auto_hide_timer()

    def on_popup_leave(self, *_):
        """Called when the mouse leaves the popup area.
        Clears hovering state and starts auto-hide timer."""
        self._is_hovering = False
        self._start_auto_hide_timer()

    def _start_auto_hide_timer(self):
        self._cancel_auto_hide_timer()
        self._auto_hide_timer = GLib.timeout_add(1500, self._auto_hide_popup)

    def _cancel_auto_hide_timer(self):
        if self._auto_hide_timer:
            GLib.source_remove(self._auto_hide_timer)
            self._auto_hide_timer = None

    def _auto_hide_popup(self):
        if not self._is_hovering and self.get_visible():
            self.toggle_popup()
        self._auto_hide_timer = None
        return False

    def _trigger_cmd(self, cmd):
        self.toggle_popup()
        GLib.timeout_add(350, self._run_cmd, cmd)

    def _run_cmd(self, cmd):
        subprocess.Popen(cmd, shell=True)
        return False

    def toggle_popup(self):
        """toggle the visibility of the popup with animation"""
        if self.is_visible():
            self.revealer.set_reveal_child(False)
            GLib.timeout_add(350, self.hide)
        else:
            self.show()
            self.revealer.set_reveal_child(True)
            self.on_popup_enter()  # Start with hover active


class LogoutButton(Box):
    """logout trigger button"""

    def __init__(self, window, **kwargs):
        super().__init__(**kwargs, name="logout-button-container")
        self.window = window
        self.button = Button(label="⏻", name="logout")
        self.content = EventBox(
            on_button_release_event=self._trigger_logout,
            on_enter_notify_event=lambda *a: self.popup.on_popup_enter(),
            on_leave_notify_event=lambda *a: self.popup.on_popup_leave(),
        )

        self.content.add(self.button)
        self.add(self.content)

        self.popup = LogoutPopup(parent=window, pointing_to=self)

    def _trigger_logout(self, *_):
        self.popup.toggle_popup()
        return True
