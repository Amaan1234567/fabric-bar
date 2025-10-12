"""hold mpris popup"""

from loguru import logger
from gi.repository import GdkPixbuf, Gio  # type: ignore
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.revealer import Revealer
from fabric.utils import invoke_repeater
from fabric.utils import cooldown

from custom_widgets.popwindow import PopupWindow
from custom_widgets.image_rounded import CustomImage
from custom_widgets.animated_scale import AnimatedScale
from services.playerctlservice import SimplePlayerctlService
from helpers.helper_functions import pixbuf_cropping_if_image_is_not_1_1, truncate


class MprisPopup(PopupWindow):
    """mpris popup widget which shows more song details,progressbar and controls"""

    def __init__(self, parent, pointing_to, **kwargs):
        super().__init__(
            parent=parent,
            pointing_to=pointing_to,
            layer="top",
            name="mpris-overlay-window",
            type="popup",
            anchor="top right",
            title="fabric-mpris-popup",
            visible=False,
            v_expand=False,
            h_expand=False,
            **kwargs,
        )

        self.temp_art_pixbuf_cache = None
        self.temp_url_cache = ""
        self.song_length = 0
        self.art_url = ""

        self.service = SimplePlayerctlService()
        self.service.connect("track_change", self._update_widget)
        self.service.connect("track-status-change", self._on_status_change)
        self.album_art_overlay = CustomImage(name="album-art-overlay")
        self.album_art_overlay.set_size_request(100, 100)

        self.song_title = Label(
            name="song-title-overlay",
            line_wrap="word",
            chars_width=15,
            justification="center",
        )
        self.song_artist = Label(
            name="song-artist-overlay",
            line_wrap="word",
            chars_width=15,
            justification="center",
        )

        self.prev_button = Button(label="󰒮", name="prev-button")
        self.prev_button.connect("clicked", self._prev_track)

        self.play_button = Button(label="", name="play-button")
        self.play_button.connect("clicked", self._toggle_play)

        self.next_button = Button(label="󰒭", name="next-button")
        self.next_button.connect("clicked", self._next_track)

        self.shuffle_button = Button(label="󰒞", name="shuffle-button")
        self.shuffle_button.connect("clicked", self._toggle_shuffle)

        self.repeat_button = Button(label="󰑗", name="repeat-button")
        self.repeat_button.connect("clicked", self._toggle_repeat)
        self.scale = AnimatedScale(
            name="mpris-popup-scale",
            orientation="horizontal",
            value=0,
            draw_value=False,
            h_expand=True,
            v_expand=True,
            has_origin=True,
            increments=(0.3, 0.1),
            min_value=0,
        )
        self.scale.connect("change-value", self._on_scroll)
        self.control_row = Box(
            name="controls",
            orientation="horizontal",
            spacing=30,
            h_align="fill",
            children=[
                self.shuffle_button,
                self.prev_button,
                self.play_button,
                self.next_button,
                self.repeat_button,
            ],
        )

        self.song_details_box = Box(
            name="song-details",
            orientation="v",
            spacing=5,
            v_align="center",
            h_align="fill",
            children=[
                self.song_title,
                self.song_artist,
            ],
        )
        self.padding_box = Box(v_expand=True, h_expand=True)
        self.right_column = Box(
            name="right-column",
            orientation="vertical",
            spacing=0,
            v_align="fill",
            h_align="fill",
            v_expand=True,
            children=[
                self.song_details_box,
                self.padding_box,
                self.control_row,
                self.scale,
            ],
        )

        self.column = Box(
            orientation="horizontal",
            name="mpris-overlay",
            spacing=0,
            children=[self.album_art_overlay, self.right_column],
            v_expand=False,
            h_expand=False,
        )

        self.overlay_revealer = Revealer(
            name="mpris-revealer",
            child=self.column,
            transition_type="slide-down",
            transition_duration=250,
        )
        self.add(self.overlay_revealer)
        self._update_widget()
        self._on_status_change()
        invoke_repeater(1000, self._update_progress)

    def _prev_track(self, *_):
        self.service.previous_track()

    def _next_track(self, *_):
        self.service.next_track()

    def _toggle_play(self, *_):
        self.service.play_pause()
        self._on_status_change()

    def _toggle_shuffle(self, *_):
        self.service.toggle_shuffle()
        self._on_shuffle_change()

    def _toggle_repeat(self, *_):
        self.service.cycle_loop()
        self._on_repeat_change()

    def _on_status_change(self):
        status = self.service.get_status()
        self.play_button.set_label("" if status != "playing" else "")

    def _on_shuffle_change(self):
        state = self.service.get_shuffle()
        self.shuffle_button.set_label("󰒟" if state == "On" else "󰒞")

    def _on_repeat_change(self):
        state = self.service.get_loop()
        if state == "none":
            self.repeat_button.set_label("󰑗")  # custom icon for 'off'
        elif state == "playlist":
            self.repeat_button.set_label("󰕇")
        elif state == "track":
            self.repeat_button.set_label("󰑘")

    def _art_update(self, f, res):
        try:
            stream = f.read_finish(res)
            pix = GdkPixbuf.Pixbuf.new_from_stream(stream, None)

            if pixbuf := pix:
                self.album_art_overlay.set_from_pixbuf(pixbuf_cropping_if_image_is_not_1_1(pixbuf))
                self.temp_art_pixbuf_cache = pixbuf
        except Exception as e:
            logger.exception("encountered error:", e)

    def _update_progress(self):
        if not self.get_visible():
            return True
        position = self.service.get_position()

        if self.song_length != 0:

            if (position - self.scale.value) / self.song_length > 0.1:
                self.scale.animate_value(position)
            self.scale.set_value(position)
        return True

    @cooldown(0.4)
    def _on_scroll(self, _, __, value):
        """Mouse wheel sends ±STEP % *relative* increments."""
        self.service.set_position(value)

        self.scale.animate_value(value)
        self.scale.set_value(value)

    def _update_widget(self):
        data = self.service.get_metadata()
        if data:
            art_url, title, artist, self.song_length = (
                data["art_url"],
                data["title"],
                data["artist"],
                data["length"],
            )
            self.song_title.set_label(truncate(title.strip() or "—", max_len=20))
            self.song_artist.set_label(truncate(artist.strip() or "—", max_len=20))
            self.scale.max_value = self.song_length

            if self.temp_url_cache != art_url and art_url != "":
                Gio.File.new_for_uri(art_url).read_async(0, None, self._art_update)
                self.temp_url_cache = art_url

        return True
