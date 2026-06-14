"""Clock popup with live date/time and interactive calendar."""

import calendar
from datetime import datetime

from gi.repository import Gtk  # type: ignore

from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.eventbox import EventBox

from custom_widgets.popup_window import PopupWindow
from custom_widgets.HackedStackRevealer import HackedRevealer


CELL_SIZE = 34


class CalendarGrid(Box):
    """Calendar built from Fabric widgets on Gtk.Grid."""

    DAY_NAMES = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

    def __init__(self, **kwargs):
        super().__init__(orientation="v", spacing=4, **kwargs)

        now = datetime.now()
        self._year = now.year
        self._month = now.month
        self._today = (now.year, now.month, now.day)
        self._selected = self._today

        # ── header ────────────────────────────────────────────
        header = Box(orientation="h", name="cal-header", spacing=4, h_expand=True)
        header.add(self._nav("«", -1, True))
        header.add(self._nav("‹", -1, False))
        self._title = Label(
            label="", name="cal-month-label", h_expand=True, size=12,
        )
        header.add(self._title)
        header.add(self._nav("›", 1, False))
        header.add(self._nav("»", 1, True))

        # ── grid ──────────────────────────────────────────────
        self._grid = Gtk.Grid()
        self._grid.set_hexpand(True)
        self._grid.set_column_homogeneous(True)
        # self._grid.set_row_homogeneous(True)
        self._grid.set_column_spacing(2)
        self._grid.set_row_spacing(2)

        # day name headers
        for c, name in enumerate(self.DAY_NAMES):
            lbl = Label(label=name, name="cal-day-name", size=9, h_align="center")
            self._grid.attach(lbl, c, 0, 1, 1)

        # cells — created once, restyled on navigate
                # cells — created once, restyled on navigate
        self._cells = []
        for r in range(6):
            row = []
            for c in range(7):
                wrapper = Box(
                    orientation="v",
                    name="cal-cell",
                    h_align="center",
                    v_align="center",
                )
                wrapper.set_size_request(CELL_SIZE, CELL_SIZE)

                lbl = Label(
                    label="",
                    name="cal-num",
                    size=12,
                    h_align="center",
                    v_align="center",
                    h_expand=True,
                    v_expand=True,
                )
                wrapper.add(lbl)
                wrapper.connect("button-press-event", self._on_click)
                self._grid.attach(wrapper, c, r + 1, 1, 1)
                row.append((wrapper, lbl))
            self._cells.append(row)


        self.add(header)
        self.add(self._grid)
        self._rebuild()

    def _nav(self, symbol, delta, is_year):
        btn = EventBox(name="cal-nav-btn")
        btn.add(Label(label=symbol, name="cal-nav-icon", size=11))
        btn.connect(
            "button-press-event",
            lambda *a, d=delta, y=is_year: self._navigate(d, y),
        )
        return btn

    def _navigate(self, delta, is_year):
        if is_year:
            self._year += delta
        else:
            self._month += delta
            while self._month > 12:
                self._month -= 12
                self._year += 1
            while self._month < 1:
                self._month += 12
                self._year -= 1
        self._rebuild()

    def _on_click(self, widget, _event):
        day = widget.get_data("cal_day")
        if day and day > 0:
            self._selected = (self._year, self._month, day)
            self._rebuild()

    def go_to_today(self):
        now = datetime.now()
        self._today = (now.year, now.month, now.day)
        self._selected = self._today
        self._year, self._month = now.year, now.month
        self._rebuild()

    def refresh_today(self):
        now = datetime.now()
        today = (now.year, now.month, now.day)
        if today != self._today:
            self._today = today
            self._rebuild()

    def _rebuild(self):
        self._title.set_text(
            f"{calendar.month_name[self._month]} {self._year}"
        )
        first_dow, num_days = calendar.monthrange(self._year, self._month)
        day = 1
        # how many rows this month actually needs
        rows_needed = -(-(first_dow + num_days) // 7)  # ceiling division

        for r in range(6):
            for c in range(7):
                box, lbl = self._cells[r][c]

                if r >= rows_needed:
                    # trailing empty row — hide entirely
                    lbl.set_text("")
                    box._cal_day = 0
                    box.set_no_show_all(True)
                    box.set_visible(False)
                elif (r == 0 and c < first_dow) or day > num_days:
                    # empty cell within a used row
                    lbl.set_text("")
                    box.set_name("cal-cell-empty")
                    box._cal_day = 0
                    box.set_no_show_all(False)
                    box.set_visible(True)
                    box.set_sensitive(False)
                else:
                    # active day cell
                    box.set_no_show_all(False)
                    box.set_visible(True)
                    box.set_sensitive(True)
                    lbl.set_text(str(day))
                    box._cal_day = day

                    key = (self._year, self._month, day)
                    is_today = key == self._today
                    is_selected = key == self._selected and not is_today

                    if is_today:
                        box.set_name("cal-today-cell")
                        lbl.set_name("cal-today-num")
                    elif is_selected:
                        box.set_name("cal-selected-cell")
                        lbl.set_name("cal-selected-num")
                    else:
                        box.set_name("cal-cell")
                        lbl.set_name("cal-num")

                    day += 1

        self._grid.show_all()



class ClockPopup(PopupWindow):
    """Popup with live clock and interactive calendar."""

    def __init__(self, parent, pointing_to, **kwargs):
        super().__init__(
            parent=parent,
            pointing_to=pointing_to,
            layer="top",
            name="clock-popup-window",
            type="popup",
            margin="15 0 0 0",
            anchor="top left",
            title="fabric-clock-popup",
            visible=False,
            v_expand=False,
            h_expand=False,
            **kwargs,
        )

        content = Box(orientation="v", name="clock-popup-content", spacing=10)

        self._date_label = Label(
            label="", name="clock-popup-date", h_align="center",
        )
        self._time_label = Label(
            label="", name="clock-popup-time", h_align="center",
        )

        today_row = Box(orientation="h", h_expand=True, name="clock-today-row")
        spacer = Box(h_expand=True)
        self._today_btn = EventBox(name="clock-today-btn")
        self._today_btn.add(
            Label(label="Today", name="clock-today-label", size=10)
        )
        self._today_btn.connect("button-press-event", self._go_to_today)
        today_row.add(spacer)
        today_row.add(self._today_btn)

        self._calendar = CalendarGrid(name="cal-wrapper")

        content.add(self._date_label)
        content.add(self._time_label)
        content.add(today_row)
        content.add(self._calendar)

        self.overlay_revealer = HackedRevealer(
            bezier_curve=(0.3, -0.06, 0, 1.02),
            duration=0.450,
            name="clock-revealer",
            child=content,
        )
        self.add(self.overlay_revealer)

    def _go_to_today(self, *_):
        self._calendar.go_to_today()

    def update(self):
        now = datetime.now()
        self._date_label.set_text(now.strftime("%A, %B %d, %Y"))
        self._time_label.set_text(now.strftime("%H:%M:%S"))
        self._calendar.refresh_today()
