#!/usr/bin/env python3
import os
import tempfile
import urllib.request
from gi.repository import GdkPixbuf, GLib, Gdk

from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric import Fabricator
from fabric.widgets.wayland import WaylandWindow
from fabric.widgets.revealer import Revealer
from fabric.utils import cooldown

from custom_widgets.popwindow import PopupWindow
from custom_widgets.image_rounded import CustomImage

def _truncate(text, max_len=30):
    return text if len(text) <= max_len else text[: max_len - 1] + "…"

class Mpris(Box):
    def __init__(self, window, **kwargs):
        super().__init__(orientation="horizontal", spacing=6, **kwargs)

        self.content = Box(orientation='h', spacing=10)
        self.content_event_box = EventBox()
        self.album_art = CustomImage(name="album-art")
        self.album_art.set_size_request(20, 20)

        self.title_label = Label(name="song-title", label="")
        self.artist_label = Label(name="song-artist", label="")
        self.pause_icon = Label(label="", name="pause-icon")
        self.pause_icon.set_visible(False)

        self.content.add(self.album_art)
        self.content.add(self.pause_icon)
        self.content.add(self.title_label)
        self.content_event_box.add(self.content)
        self.add(self.content_event_box)

        self.temp_art_path = None
        self.temp_url_cache = ""

        Fabricator(
            poll_from="playerctl metadata --format '{{mpris:artUrl}}|{{title}}|{{artist}}'",
        ).connect("changed", self._on_metadata)

        Fabricator(
            interval=500,
            poll_from="playerctl status"
        ).connect("changed", self._on_status_change)

        Fabricator(
            interval=1000,
            poll_from="playerctl shuffle"
        ).connect("changed", self._on_shuffle_change)

        Fabricator(
            interval=1000,
            poll_from="playerctl loop"
        ).connect("changed", self._on_repeat_change)

        # Overlay elements
        self.album_art_overlay = CustomImage(name="album-art-overlay")
        self.album_art_overlay.set_size_request(100, 100)
        
        self.song_title = Label(name="song-title-overlay", line_wrap="word", chars_width=15, justification="center")
        self.song_artist = Label(name="song-artist-overlay", line_wrap="word", chars_width=15, justification="center")

        self.prev_button = Button(label="󰒮", name="prev-button")
        self.prev_button.connect("clicked", self.prev_track)

        self.play_button = Button(label="", name="play-button")
        self.play_button.connect("clicked", self.toggle_play)

        self.next_button = Button(label="󰒭", name="next-button")
        self.next_button.connect("clicked", self.next_track)

        self.shuffle_button = Button(label="󰒞", name="shuffle-button")
        self.shuffle_button.connect("clicked", self.toggle_shuffle)

        self.repeat_button = Button(label="󰑗", name="repeat-button")
        self.repeat_button.connect("clicked", self.toggle_repeat)

        self.control_row = Box(
            name="controls",
            orientation="horizontal",
            spacing=30,
            h_align="fill",
            children=[self.shuffle_button, self.prev_button,self.play_button,self.next_button, self.repeat_button],
        )

        self.song_details_box = Box(
            name="song-details",
            orientation='v',
            spacing=5,
            v_align="center",
            h_align="fill",
            children=[
                self.song_title,
                self.song_artist,
            ]
        )
        self.right_column = Box(
            name="right-column",
            orientation="vertical",
            spacing=30,
            v_align="center",
            h_align="fill",
            children=[
                self.song_details_box,
                self.control_row
            ]
        )

        self.column = Box(
            orientation="horizontal",
            name="mpris-overlay",
            spacing=0,
            children=[
                self.album_art_overlay,
                self.right_column
            ],
            v_expand=False,
            h_expand=False
        )
        
        self.overlay_revealer = Revealer(name="mpris-revealer",child=self.column,transition_type="slide-down",transition_duration=250)

        self.overlay = PopupWindow(parent=window,pointing_to=self,
            name="mpris-overlay-window",
            layer="top",
            type="popup",
            anchor="top right",
            visible=False,
            child=self.overlay_revealer,
            v_expand=False,
            h_expand=False
        )
  
        self.overlay_hide_timeout_id = None
        self.overlay.connect("enter-notify-event", self.on_overlay_enter)
        self.overlay.connect("leave-notify-event", self.on_overlay_leave)
        self.content_event_box.connect("enter-notify-event", self.hover_trigger)
        self.content_event_box.connect("leave-notify-event", self.on_hover_leave)
        self.overlay.do_reposition("x")

    def hover_trigger(self):
        self.delay = GLib.timeout_add(500,self.on_hover_enter)
    def on_hover_enter(self, *_):
        print("triggered")
        if(len(self.title_label.get_label()) != 0):
            self._cancel_hide_timeout()
            self.overlay.set_visible(True)
            self.overlay_revealer.set_reveal_child(True)

    def on_hover_leave(self, *_):
        print("triggered leave")
        self._schedule_overlay_hide()
        GLib.source_remove(self.delay)

    def on_overlay_enter(self, *_):
        self._cancel_hide_timeout()

    def on_overlay_leave(self, *_):
        self._schedule_overlay_hide()

    def _schedule_overlay_hide(self):
        self._cancel_hide_timeout()
        self.overlay_hide_timeout_id = GLib.timeout_add(1500, self._hide_overlay)

    def _cancel_hide_timeout(self):
        if self.overlay_hide_timeout_id:
            GLib.source_remove(self.overlay_hide_timeout_id)
            self.overlay_hide_timeout_id = None

    def _hide_overlay(self):
        self.overlay_revealer.set_reveal_child(False)
        GLib.timeout_add(250, self.overlay.set_visible, False)
        self.overlay_hide_timeout_id = None
        return False  # don't repeat timeout


    def prev_track(self, *_): os.system("playerctl previous")
    def next_track(self, *_): os.system("playerctl next")
    def toggle_play(self, *_): os.system("playerctl play-pause")
    def toggle_shuffle(self, *_): os.system("playerctl shuffle Toggle")

    def toggle_repeat(self, *_):
        # Cycle: None -> All -> One
        current = os.popen("playerctl loop").read().strip()
        new_mode = "None" if current == "Playlist" else "Track" if current == "None" else "Playlist"
        os.system(f"playerctl loop {new_mode}")


    def _on_metadata(self, _, output: str):
        parts = output.strip().split("|", 2)
        if len(parts) != 3:
            return
        art_url, title, artist = parts
        self.title_label.set_label(_truncate(title.strip() or "—"))
        self.song_title.set_label(_truncate(title.strip() or "—"))
        self.song_artist.set_label(_truncate(artist.strip() or "—"))
        self.artist_label.set_label(_truncate(artist.strip() or "—"))
        self._load_art(art_url.strip())

    def _on_status_change(self, _, output: str):
        status = output.strip()
        self.pause_icon.set_visible(status != "Playing")
        self.play_button.set_label("" if status != "Playing" else "")

    def _on_shuffle_change(self, _, output: str):
        state = output.strip()
        self.shuffle_button.set_label("󰒟" if state == "On" else "󰒞")

    def _on_repeat_change(self, _, output: str):
        state = output.strip()
        if state == "None":
            self.repeat_button.set_label("󰑗")  # custom icon for 'off'
        elif state == "Playlist":
            self.repeat_button.set_label("󰕇")
        elif state == "Track":
            self.repeat_button.set_label("󰑘")

    def create_album_art(self,path, size=200):
        try:
            # Load the original image
            original_pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
            
            # Get original dimensions
            original_width = original_pixbuf.get_width()
            original_height = original_pixbuf.get_height()
            
            # Check if aspect ratio is 1:1
            if original_width == original_height:
                # Square image - just scale it
                pic2 = original_pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
            else:
                # Non-square image - center crop first, then scale
                crop_size = min(original_width, original_height)
                crop_x = (original_width - crop_size) // 2
                crop_y = (original_height - crop_size) // 2
                
                # Create cropped pixbuf
                cropped_pixbuf = GdkPixbuf.Pixbuf.new(
                    GdkPixbuf.Colorspace.RGB,
                    original_pixbuf.get_has_alpha(),
                    original_pixbuf.get_bits_per_sample(),
                    crop_size,
                    crop_size
                )
                
                # Copy the center square
                original_pixbuf.copy_area(
                    crop_x, crop_y,
                    crop_size, crop_size,
                    cropped_pixbuf,
                    0, 0
                )
                
                # Scale the cropped square
                pic2 = cropped_pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
            
            return pic2
            
        except Exception as e:
            print(f"Error processing image: {e}")
            return None

    def _load_art(self, art_url: str):
        try:
            path = ""
            if art_url.startswith("file://"):
                path = art_url[7:]
            elif art_url.startswith("http://") or art_url.startswith("https://"):
                if self.temp_url_cache != art_url:
                    self.temp_url_cache = art_url
                    fd, path = tempfile.mkstemp(suffix=".png")
                    os.close(fd)
                    urllib.request.urlretrieve(art_url, path)
                    self._cleanup_temp()
                    self.temp_art_path = path
            if not os.path.exists(path): return
            pic1 = self.create_album_art(path=path,size=20)
            pic2 = self.create_album_art(path=path,size=200)

            self.album_art.set_from_pixbuf(pic1)
            self.album_art_overlay.set_from_pixbuf(pic2)
        except Exception as e:
            print(f"[MPRIS] failed loading album art: {e}")
            self.album_art.clear()

    def _cleanup_temp(self):
        if self.temp_art_path and os.path.isfile(self.temp_art_path):
            try: os.remove(self.temp_art_path)
            except: pass
        self.temp_art_path = None
