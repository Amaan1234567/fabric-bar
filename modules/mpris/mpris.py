#!/usr/bin/env python3

from gi.repository import GdkPixbuf, GLib, Gio
from time import sleep
from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric import Fabricator
from fabric.widgets.wayland import WaylandWindow
from fabric.widgets.revealer import Revealer
from fabric.utils import invoke_repeater
from fabric.utils import cooldown

from custom_widgets.popwindow import PopupWindow
from custom_widgets.image_rounded import CustomImage
from custom_widgets.animated_circular_progress_bar import AnimatedCircularProgressBar
from services.playerctlservice import SimplePlayerctlService
def _truncate(text, max_len=30):
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


class MprisPopup(PopupWindow):
    def __init__(self,parent,pointing_to,name="mpris-overlay-window",**kwargs):
        super().__init__(parent=parent,pointing_to=pointing_to,layer="top",
            type="popup",
            anchor="top right",
            visible=False,
            v_expand=False,
            h_expand=False,**kwargs)
        
        self.temp_art_pixbuf_cache = None
        self.temp_url_cache = ""

        self.service = SimplePlayerctlService()
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
        self.add(self.overlay_revealer)

        invoke_repeater(500,self.update)
        
    
    def prev_track(self, *_): self.service.previous_track()
    def next_track(self, *_): self.service.next_track()
    def toggle_play(self, *_): 
        self.service.play_pause()
        self._on_status_change()
    def toggle_shuffle(self, *_): 
        self.service.toggle_shuffle()
        self._on_shuffle_change()
    def toggle_repeat(self, *_): 
        self.service.cycle_loop()
        self._on_repeat_change()
    def _on_status_change(self):
        status = self.service.get_status()
        self.play_button.set_label("" if status != "Playing" else "")

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

    def art_update(self,f,res):
        pix = GdkPixbuf.Pixbuf.new_from_stream(f.read_finish(res))
        
        if pixbuf := pix:
                self.album_art_overlay.set_from_pixbuf(self.service.create_album_art(pixbuf))
                self.temp_art_pixbuf_cache = pixbuf

    def update(self):
        data = self.service.get_metadata()
        if data: 
            art_url, title, artist ,song_length = data['art_url'] , data['title'], data['artist'], data['length']
            self.song_title.set_label(_truncate(title.strip() or "—",max_len=20))
            self.song_artist.set_label(_truncate(artist.strip() or "—",max_len=20))
            #print(art_url)
            if self.temp_url_cache != art_url:
                Gio.File.new_for_uri(art_url).read_async(0, None, self.art_update)
                self.temp_url_cache = art_url
            
        return True

class Mpris(Box):
    def __init__(self, window, **kwargs):
        super().__init__(orientation="horizontal", spacing=6, **kwargs)

        self.temp_art_pixbuf_cache = None
        self.temp_url_cache = ""

        self.content = Box(orientation='h', spacing=10)
        self.content_event_box = EventBox()
        self.album_art = CustomImage(name="album-art")
        self.album_art.set_size_request(30, 30)

        self.title_label = Label(name="song-title", label="")
        self.artist_label = Label(name="song-artist", label="")
        self.pause_icon = Label(label="", name="pause-icon")
        self.song_progress = AnimatedCircularProgressBar(name="cpu-progress-bar",
            child=self.pause_icon,
            value=0,
            line_style="round",
            line_width=4,
            size=35,
            start_angle=140,
            end_angle=395,
            invert=True)

        self.content.add(self.song_progress)
        self.content.add(self.album_art)
        self.content.add(self.title_label)
        self.content_event_box.add(self.content)
        self.add(self.content_event_box)

        self.song_length = 0
        self.service = SimplePlayerctlService()

        self.overlay = MprisPopup(parent=window,pointing_to=self)

        self.overlay_hide_timeout_id = None
        self.overlay.connect("enter-notify-event", self.on_overlay_enter)
        self.overlay.connect("leave-notify-event", self.on_overlay_leave)
        self.content_event_box.connect("enter-notify-event", self.hover_trigger)
        self.content_event_box.connect("leave-notify-event", self.on_hover_leave)
        self.overlay.do_reposition("x")

        invoke_repeater(500,self.update)

    def _update_progress(self):
        position = self.service.get_position()
        #print(self.song_length)
        if self.song_length!=0:
            #print(position)
            self.song_progress.animate_value((position/self.song_length))
            self.song_progress.set_value(position/self.song_length)

    def hover_trigger(self):
        self.delay = GLib.timeout_add(500,self.on_hover_enter)
    def on_hover_enter(self, *_):
        #print("triggered")
        if(len(self.title_label.get_label()) != 0):
            self._cancel_hide_timeout()
            self.overlay.set_visible(True)
            self.overlay.overlay_revealer.set_reveal_child(True)

    def on_hover_leave(self, *_):
        #print("triggered leave")
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
        self.overlay.overlay_revealer.set_reveal_child(False)
        GLib.timeout_add(250, self.overlay.set_visible, False)
        self.overlay_hide_timeout_id = None
        return False  # don't repeat timeout

    def art_update(self,f,res):
        pix = GdkPixbuf.Pixbuf.new_from_stream(f.read_finish(res))
        
        if pixbuf := pix:
                
                self.album_art.set_from_pixbuf(self.service.create_album_art(pixbuf,30))
                self.temp_art_pixbuf_cache = pixbuf
                
    def update(self):
        if data := self.service.get_metadata():
            #print("updating")
            art_url, title, artist ,song_length = data['art_url'] , data['title'], data['artist'], data['length']
            self.album_art.set_visible(True)
            self.song_progress.set_visible(True)
            #print(song_length)
            self.song_length=song_length
            
            self.title_label.set_label(_truncate(title.strip() or "—"))
            self.artist_label.set_label(_truncate(artist.strip() or "—"))
            if self.temp_url_cache != art_url:
                Gio.File.new_for_uri(art_url).read_async(0, None, self.art_update)
                self.temp_url_cache = art_url
            self._update_progress()
            self._on_status_change()
        else:
            self.album_art.set_visible(False)
            self.song_progress.set_visible(False)
        return True

    def _on_status_change(self):
        status = self.service.get_status()
        self.pause_icon.set_label("" if status != "playing" else "")

    
