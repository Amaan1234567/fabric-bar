"""Clock widget with calendar popup."""

from fabric.widgets.datetime import DateTime
from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from gi.repository import GLib  # type: ignore

from utils.popup_manager import popup_manager
from modules.clock.clock_popup import ClockPopup


class Clock(Box):
    """Clock widget with interactive calendar popup on hover."""

    def __init__(self, window, **kwargs):
        super().__init__(name="clock", **kwargs)

        self.clock = DateTime(format_string="%a, %b %d  %I:%M %p")
        self.clock.connect(
            "state-flags-changed",
            lambda btn, *_: (
                btn.set_cursor("pointer")
                if btn.get_state_flags() & 2  # type: ignore
                else btn.set_cursor("default")
            ),
        )

        # wrap in EventBox for hover
        self.content_event_box = EventBox()
        self.content_event_box.add(self.clock)
        self.add(self.content_event_box)

        # ── popup state ────────────────────────────────────────
        self._hide_timeout_id = None
        self._show_delay_id = None

        self.popup = ClockPopup(
            parent=window,
            pointing_to=self,
            exclusivity="none",
        )

        self.content_event_box.connect(
            "enter-notify-event", self._hover_trigger
        )
        self.content_event_box.connect(
            "leave-notify-event", self._on_hover_leave
        )
        self.popup.connect("enter-notify-event", self._on_popup_enter)
        self.popup.connect("leave-notify-event", self._on_popup_leave)
        self.popup.do_reposition("x")

        # ── tick for popup time update ─────────────────────────
        GLib.timeout_add(1000, self._tick)

    # ── tick ────────────────────────────────────────────────────

    def _tick(self):
        if self.popup.get_visible():
            self.popup.update()
        return True

    # ── hover flow ──────────────────────────────────────────────

    def _hover_trigger(self, *_):
        self._show_delay_id = GLib.timeout_add(300, self._on_hover_enter)

    def _on_hover_enter(self, *_):
        self._cancel_hide_timeout()
        self._show_delay_id = None
        self.popup.update()
        popup_manager.request_show(self.popup, self)
        return False

    def _on_hover_leave(self, *_):
        self._schedule_hide()
        if self._show_delay_id:
            GLib.source_remove(self._show_delay_id)
            self._show_delay_id = None

    def _on_popup_enter(self, *_):
        self._cancel_hide_timeout()

    def _on_popup_leave(self, *_):
        self._schedule_hide()

    def _schedule_hide(self):
        self._cancel_hide_timeout()
        self._hide_timeout_id = GLib.timeout_add(1000, self._hide_popup)

    def _cancel_hide_timeout(self):
        if self._hide_timeout_id:
            GLib.source_remove(self._hide_timeout_id)
            self._hide_timeout_id = None

    def _hide_popup(self):
        self.popup.overlay_revealer.set_reveal_child(False)
        GLib.timeout_add(450, self.popup.set_visible, False)
        popup_manager.request_hide(self.popup, self)
        self._hide_timeout_id = None
        return False
