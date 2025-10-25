"""holds the mpris widget shown in bar"""

from loguru import logger
from gi.repository import GdkPixbuf, GLib, Gio  # type: ignore
from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label
from fabric.utils import invoke_repeater

from custom_widgets.image_rounded import CustomImage
from custom_widgets.animated_circular_progress_bar import AnimatedCircularProgressBar
from services.playerctlservice import SimplePlayerctlService
from helpers.helper_functions import pixbuf_cropping_if_image_is_not_1_1, truncate

from modules.mpris.mpris_popup import MprisPopup


class Mpris(Box):
    """mpris widget that is shown in the bar, which shows truncated song name and album art"""

    def __init__(self, window, **kwargs):
        super().__init__(orientation="horizontal", spacing=6, **kwargs)

        self.delay = None
        self.temp_art_pixbuf_cache = None
        self.temp_url_cache = ""
        self.content = Box(orientation="h", spacing=10)
        self.content_event_box = EventBox()
        self.album_art = CustomImage(name="album-art")
        self.album_art.set_size_request(30, 30)

        self.title_label = Label(name="song-title", label="")
        self.pause_icon = Label(label="", name="pause-icon")
        self.song_progress = AnimatedCircularProgressBar(
            name="cpu-progress-bar",
            child=self.pause_icon,
            value=0,
            line_style="round",
            line_width=4,
            size=35,
            start_angle=140,
            end_angle=395,
            invert=True,
        )

        self.content.add(self.song_progress)
        self.content.add(self.album_art)
        self.content.add(self.title_label)
        self.content_event_box.add(self.content)
        self.add(self.content_event_box)

        self.song_length = 0
        self.service = SimplePlayerctlService()
        self._init_widget_data()
        self.overlay = MprisPopup(parent=window, pointing_to=self)

        self.overlay_hide_timeout_id = None
        self.overlay.connect("enter-notify-event", self._on_overlay_enter)
        self.overlay.connect("leave-notify-event", self._on_overlay_leave)
        self.content_event_box.connect("enter-notify-event", self._hover_trigger)
        self.content_event_box.connect("leave-notify-event", self._on_hover_leave)
        self.overlay.do_reposition("x")

        invoke_repeater(2000, self._update_progress)

    def _init_widget_data(self):
        if self.service.current_player is not None:
            self.service.connect("changed", self._update_widget)
            self.service.connect("changed", self._on_status_change)
        self._update_widget()
        self._on_status_change()

    def _update_progress(self):
        if self.service.current_player is None:
            return
        position = self.service.current_player.get_position()  # type: ignore
        # print(self.song_length)
        if self.song_length != 0:
            # print(position)
            if abs(self.song_progress.value - position) / self.song_length > 0.05:
                self.song_progress.animate_value(position)
            self.song_progress.set_value(position)  # type: ignore
        return True

    def _hover_trigger(self):
        self.delay = GLib.timeout_add(300, self._on_hover_enter)

    def _on_hover_enter(self, *_):
        # print("triggered")
        if len(self.title_label.get_label()) != 0:
            self._cancel_hide_timeout()
            self.overlay.set_visible(True)
            self.overlay.overlay_revealer.set_reveal_child(True)

    def _on_hover_leave(self, *_):
        # print("triggered leave")
        self._schedule_overlay_hide()
        if self.delay:
            GLib.source_remove(self.delay)

    def _on_overlay_enter(self, *_):
        self._cancel_hide_timeout()

    def _on_overlay_leave(self, *_):
        self._schedule_overlay_hide()

    def _schedule_overlay_hide(self):
        self._cancel_hide_timeout()
        self.overlay_hide_timeout_id = GLib.timeout_add(1500, self._hide_overlay)

    def _cancel_hide_timeout(self):
        if self.overlay_hide_timeout_id:
            GLib.source_remove(self.overlay_hide_timeout_id)
            self.overlay_hide_timeout_id = None

    def _hide_overlay(self):
        self.overlay.overlay_revealer.set_reveal_child(False)
        GLib.timeout_add(250, self.overlay.set_visible, False)
        self.overlay_hide_timeout_id = None
        return False  # don't repeat timeout

    def _art_update(self, f, res):
        try:
            pix = GdkPixbuf.Pixbuf.new_from_stream(f.read_finish(res), None)

            if pixbuf := pix:
                self.album_art.set_from_pixbuf(
                    pixbuf_cropping_if_image_is_not_1_1(pixbuf, 30)
                )
                self.temp_art_pixbuf_cache = pixbuf
        except Exception as e:  # type: ignore
            logger.exception("encountered_error: ", e)

    def _update_widget(self):
        if self.service.current_player is None:
            self.album_art.set_visible(False)
            self.song_progress.set_visible(False)
            self.title_label.set_visible(False)
            return

        if data := self.service.current_player.get_metadata():  # type: ignore
            logger.info(f"mpris metadata: {data}")
            art_url, title, song_length = (
                data["art_url"],
                data["title"],
                data["length"],
            )
            self.album_art.set_visible(True)
            self.song_progress.set_visible(True)
            self.title_label.set_visible(True)

            self.song_length = song_length
            if song_length:
                self.song_progress.max_value = self.song_length
            self.title_label.set_label(truncate(title.strip() or "—"))
            if art_url not in (self.temp_url_cache, ""):
                Gio.File.new_for_uri(art_url).read_async(0, None, self._art_update)
                self.temp_url_cache = art_url
        else:
            self.album_art.set_visible(False)
            self.song_progress.set_visible(False)
            self.title_label.set_visible(False)
        return True

    def _on_status_change(self):
        if self.service.current_player is None:
            return
        status = self.service.current_player.get_status()  # type: ignore
        self.pause_icon.set_label("" if status != "playing" else "")
        self._update_widget()
