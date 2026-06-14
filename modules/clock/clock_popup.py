"""Clock popup with live date/time and interactive calendar."""

from datetime import datetime
from gi.repository import Gtk  # type: ignore

from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.eventbox import EventBox

from custom_widgets.popup_window import PopupWindow
from custom_widgets.HackedStackRevealer import HackedRevealer


class ClockPopup(PopupWindow):
    """Popup with live clock display and a fully interactive Gtk.Calendar."""

    def __init__(self, parent, pointing_to, **kwargs):
        super().__init__(
            parent=parent,
            pointing_to=pointing_to,
            layer="top",
            name="clock-popup-window",
            type="popup",
            margin="",
            anchor="top left",
            title="fabric-clock-popup",
            visible=False,
            v_expand=False,
            h_expand=False,
            **kwargs,
        )

        self._now = datetime.now()

        content = Box(
            orientation="v",
            name="clock-popup-content",
            spacing=10,
        )

        # ── date + time ────────────────────────────────────────
        self._date_label = Label(
            label="",
            name="clock-popup-date",
            h_align="center",
        )
        self._time_label = Label(
            label="",
            name="clock-popup-time",
            h_align="center",
        )

        # ── today quick-jump ───────────────────────────────────
        today_row = Box(
            orientation="h",
            h_expand=True,
            name="clock-today-row",
        )
        spacer = Box(h_expand=True)
        self._today_btn = EventBox(name="clock-today-btn")
        today_lbl = Label(
            label="Today",
            name="clock-today-label",
            size=10,
        )
        self._today_btn.add(today_lbl)
        self._today_btn.connect("button-press-event", self._go_to_today)
        today_row.add(spacer)
        today_row.add(self._today_btn)

        # ── calendar ───────────────────────────────────────────
        cal_wrapper = Box(
            orientation="v",
            name="clock-cal-wrapper",
        )

        self._calendar = Gtk.Calendar()
        self._calendar.set_name("clock-calendar")
        self._calendar.set_display_options(
            Gtk.CalendarDisplayOptions.SHOW_HEADING
            | Gtk.CalendarDisplayOptions.SHOW_DAY_NAMES
            | Gtk.CalendarDisplayOptions.SHOW_WEEK_NUMBERS
        )
        self._calendar.set_size_request(260, 200)
        self._calendar.show()

        cal_wrapper.add(self._calendar)

        # select and mark today
        self._mark_today()
        self._calendar.connect("month-changed", self._on_month_changed)

        # ── assemble ───────────────────────────────────────────
        content.add(self._date_label)
        content.add(self._time_label)
        content.add(today_row)
        content.add(cal_wrapper)

        self.overlay_revealer = HackedRevealer(
            bezier_curve=(0.3, -0.06, 0, 1.02),
            duration=0.450,
            name="clock-revealer",
            child=content,
        )
        self.add(self.overlay_revealer)

    # ── calendar helpers ────────────────────────────────────────

    def _mark_today(self):
        self._now = datetime.now()
        self._calendar.select_month(self._now.month - 1, self._now.year)
        self._calendar.select_day(self._now.day)
        self._calendar.clear_marks()
        self._calendar.mark_day(self._now.day)

    def _on_month_changed(self, cal):
        self._now = datetime.now()
        y, m, _ = cal.get_date()
        cal.clear_marks()
        if m == self._now.month - 1 and y == self._now.year:
            cal.mark_day(self._now.day)

    def _go_to_today(self, *_):
        self._mark_today()

    # ── called by ClockWidget every second while visible ────────

    def update(self):
        self._now = datetime.now()
        self._date_label.set_text(self._now.strftime("%A, %B %d, %Y"))
        self._time_label.set_text(self._now.strftime("%H:%M:%S"))

        y, m, _ = self._calendar.get_date()
        if m == self._now.month - 1 and y == self._now.year:
            self._calendar.clear_marks()
            self._calendar.mark_day(self._now.day)
