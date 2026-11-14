"""background op widget"""

from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay
from gi.repository import GLib  # type: ignore

from custom_widgets.animated_cirular_scale import AnimatedCircularScale
from modules.background_op_progress.background_op_progress_popup import (
    BackgroundOpProgressPopup,
)
from services.background_op_service import BackgroundOp, BackgroundOpService
from utils.popup_manager import popup_manager


class BackgroundOpProgress(Box):
    """Background Op widget"""

    def __init__(self, window, **kwargs):

        super().__init__(
            orientation="h",
            spacing=4,
            name="background-op-widget",
            h_expand=True,
            h_align="center",
            v_align="center",
            v_expand=True,
        )

        self._hide_timeout_id = None
        self._show_delay_id = None
        self._is_completing = False  # Lock to prevent premature widget hiding

        self.progress_bar = AnimatedCircularScale(
            name="background-op-circular-progress-bar",
            min_value=0,
            max_value=100,
            value=0,
            line_style="round",
            line_width=4,
            size=35,
            start_angle=105,
            end_angle=465,
        )
        self.progress_bar_label = Label(
            name="background-op-progress-bar-label", label=""
        )

        self.overlay = Overlay(
            child=self.progress_bar, overlays=self.progress_bar_label
        )

        self.label = Label(
            name="background-ops-complete-label", label="", visible=False
        )

        # Unified inner container so both progress and checkmark live inside the EventBox
        self.inner_box = Box(
            orientation="h",
            h_align="center",
            v_align="center",
            children=[self.overlay, self.label],
        )

        self.popup = BackgroundOpProgressPopup(parent=window, pointing_to=self)
        self.content_event_box = EventBox()
        self.content_event_box.add(self.inner_box)
        self.add(self.content_event_box)

        self.content_event_box.connect("enter-notify-event", self._hover_trigger)
        self.content_event_box.connect("leave-notify-event", self._on_hover_leave)

        self.popup.connect("enter-notify-event", self._on_popup_enter)
        self.popup.connect("leave-notify-event", self._on_popup_leave)

        self.background_op_service = BackgroundOpService()
        self.background_op_service.connect(
            "background_op_started", self._new_background_op_handler
        )
        self.background_op_service.connect(
            "background_op_finished", self._background_op_finished_handler
        )
        self.background_op_count = 0

        self._ui_update_handler()

    def _hover_trigger(self, *_):
        """Enter on the bar — start a short delay before showing."""
        self._show_delay_id = GLib.timeout_add(300, self._on_hover_enter)

    def _on_hover_enter(self, *_):
        self._cancel_hide_timeout()
        self._show_delay_id = None
        self.popup.refresh_ops()
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
        GLib.timeout_add(250, self.popup.set_visible, False)
        popup_manager.request_hide(self.popup, self)
        self._hide_timeout_id = None
        return False

    def _show_popup_temporarily(
        self, duration_seconds: int = 4, ops_just_completed=False
    ):
        """Show the popup automatically, then schedule its auto-close."""
        self.popup.refresh_ops(ops_just_completed=ops_just_completed)
        popup_manager.request_show(self.popup, self)
        self._cancel_hide_timeout()
        self._hide_timeout_id = GLib.timeout_add_seconds(
            duration_seconds, self._hide_popup
        )

    def _ui_update_handler(self):
        # Prevent normal updates from hiding the widget while completion sequence is active
        if self._is_completing:
            return

        if self.background_op_count == 0:
            self.set_visible(False)
        elif self.background_op_count == 1:
            self.set_visible(True)
        else:
            self.set_visible(True)
            self.progress_bar.max_value = self.background_op_count
            self.progress_bar.animate_value(0)

    def _new_background_op_handler(self, _, op: BackgroundOp):
        op.connect("state_update", self._state_update_handler)
        op.connect("progress_update", self._progress_update_handler)
        self.background_op_count += 1
        self._ui_update_handler()

        # Pop up automatically when a new operation starts
        self._show_popup_temporarily(4)

    def _background_op_finished_handler(self, _, op_obj: BackgroundOp):
        cur_val = self.progress_bar.value
        if self.background_op_count > 1:
            self.progress_bar.animate_value(cur_val + 1)
            self.progress_bar.value = cur_val + 1
            if cur_val + 1 == self.background_op_count:
                self._all_ops_complete_handler()
        else:
            self.background_op_count = 0
            self._all_ops_complete_handler()

    def _all_ops_complete_handler(self):
        self._is_completing = True  # Lock visibility state
        self.overlay.hide()
        self.label.show()
        self.label.queue_resize()
        self.label.queue_draw()
        self.set_visible(True)  # Force widget to stay visible
        self.background_op_count = 0

        # Update popup to completion state and pop it open automatically
        self.popup.set_tooltip_for_all_ops_completion("All background ops complete!!")
        self._show_popup_temporarily(3, ops_just_completed=True)

        # Hide the checkmark label and reset after 5 seconds
        GLib.timeout_add_seconds(3, self._reset_widget_state)

    def _reset_widget_state(self):
        self._is_completing = False  # Release lock
        self.label.hide()
        self.overlay.show()
        self.set_visible(False)  # Safely hide widget now
        self.popup.refresh_ops()
        return False

    def _state_update_handler(self, op: BackgroundOp):
        self._ui_update_handler()

    def _progress_update_handler(self, op: BackgroundOp, value: float):
        if self.background_op_count == 1:
            self.progress_bar.animate_value(value)
            self.progress_bar.value = value
        else:
            self._ui_update_handler()
