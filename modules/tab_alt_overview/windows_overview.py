"""Alt-Tab window switcher with live Glace previews.

Follows the Fabrika Pager pattern for Glace lifecycle and capture,
with a file-based toggle_window() like WallpaperSelector.
"""

import random
from typing import Callable

import gi
import json

gi.require_version("Glace", "0.1")
from gi.repository import Glace, GdkPixbuf, GLib, Gtk, Gdk  # type: ignore
from loguru import logger

from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay
from fabric.widgets.eventbox import EventBox
from fabric.hyprland.widgets import get_hyprland_connection
from custom_widgets.image_rounded import CustomImage

_SCALE = 0.2
_CAP_FPS = 2


# ────────────────────────────────────────────────────────────
#  TickChoker — from Fabrika, rate-limited widget tick callback
# ────────────────────────────────────────────────────────────


class TickChoker:
    """Throttles a callback to target FPS via GTK widget tick callbacks."""

    def __init__(
        self,
        widget: Gtk.Widget,
        target_fps: int,
        callback: Callable,
        *callback_data,
    ):
        self.widget = widget
        self.callback = callback
        self.callback_data = callback_data
        self.period = 1.0 / target_fps
        self.offset = random.uniform(0, self.period)
        self.last_tick = 0.0
        self.handler_id = 0

        self.widget.connect("map", self.on_map)
        self.widget.connect("unmap", self.on_unmap)

    def on_map(self, _):
        GLib.timeout_add(round(self.offset * 50), self.wireup)
        return False

    def on_unmap(self, _):
        self.stop()

    def do_tick(self, *_):
        if not self.widget.get_mapped():
            return False
        now = GLib.get_monotonic_time() / 1_000_000
        if self.last_tick == 0.0:
            self.last_tick = now + self.offset
        if now - self.last_tick >= self.period:
            self.last_tick = now
            self.callback(*self.callback_data)
        return True

    def wireup(self):
        self.stop()
        self.handler_id = self.widget.add_tick_callback(self.do_tick)
        return False

    def stop(self):
        if self.handler_id:
            self.widget.remove_tick_callback(self.handler_id)
            self.handler_id = 0


# ────────────────────────────────────────────────────────────
#  ClientPreview — live thumbnail
# ────────────────────────────────────────────────────────────


class ClientPreview(Box):
    """Live window thumbnail using Glace capture + TickChoker."""

    def __init__(self, client: Glace.Client, manager: Glace.Manager, **kwargs):
        super().__init__(
            style_classes=["alttab-preview"],
            v_align="center",
            h_align="center",
            **kwargs,
        )
        self.client = client
        self.manager = manager

        self.image = CustomImage(
            name="alttab-image",
            icon_name="image-missing",
            h_expand=True,
            v_expand=True,
        )

        self.title_label = Label(
            label="",
            style_classes=["alttab-title"],
            h_align="center",
            v_align="end",
        )

        self.thumb = Box(
            style_classes=["alttab-thumb"],
            h_expand=True,
            v_expand=True,
        )
        self.thumb.add(Overlay(child=self.image, overlays=self.title_label))
        self.children = self.thumb

        # Glace signals (Fabrika pattern)
        self.client.connect("close", self.do_close)
        self.client.connect("notify::activated", self.do_update_style)

        # TickChoker for capture at target FPS (Fabrika pattern)
        self.tick = TickChoker(
            self,
            _CAP_FPS,
            self.manager.capture_client,
            self.client,
            False,
            self.do_captured,
        )

        self.do_update_style()
        self.show()

    def update_for_data(self, hyprland_data: dict):
        w, h = hyprland_data.get("size", [500, 350])
        self.set_size_request(round(w * _SCALE), round(h * _SCALE))

        title = hyprland_data.get("title", "")
        app_id = hyprland_data.get("initialClass", "")
        display = title or app_id or "Unknown"
        if len(display) > 22:
            display = display[:20] + "…"
        self.title_label.set_text(display)

    def do_captured(self, pixbuf: GdkPixbuf.Pixbuf | None):
        if not pixbuf:
            return
        try:
            scaled = pixbuf.scale_simple(
                round(pixbuf.get_width() * _SCALE),
                round(pixbuf.get_height() * _SCALE),
                GdkPixbuf.InterpType.BILINEAR,
            )
            self.image.set_from_pixbuf(scaled)
        except Exception:
            pass

    def do_update_style(self, *_):
        if self.client.get_activated():
            self.add_style_class("focused")
        else:
            self.remove_style_class("focused")

    def set_selected(self, yes: bool):
        if yes:
            self.add_style_class("selected")
        else:
            self.remove_style_class("selected")

    def do_close(self, *_):
        self.tick.stop()
        self.destroy()


# ────────────────────────────────────────────────────────────
#  AltTab — window subclass (WallpaperSelector pattern)
# ────────────────────────────────────────────────────────────


class AltTab(Window):
    """Alt-Tab switcher using Glace for live window previews."""

    def __init__(self, **kwargs):
        super().__init__(
            name="alttab-window",
            title="fabric-alttab",
            layer="overlay",
            anchor="",
            margin="0px 0px 0px 0px",
            visible=False,
            exclusivity="none",
            keyboard_mode="on-demand",
            **kwargs,
        )

        self.is_hidden = True
        self._glace = Glace.Manager()
        self._glace.connect("client-added", self._on_client_added)

        self._client_views: dict[int, ClientPreview] = {}
        self._focus_order: list[Glace.Client] = []
        self._selected = 0
        self._show_time = 0.0
        self._focus_timeout = 0
        self._activate_timeout = 0    # ← was missing, caused silent crashes

        # cache connection — don't re-fetch on every sync
        self._conn = get_hyprland_connection()

        # ── UI ──────────────────────────────────────────────
        self.content = Box(
            name="alttab-backdrop",
            h_expand=True,
            v_expand=True,
            h_align="fill",
            v_align="fill",
        )
        self._grid = Box(
            name="alttab-grid",
            orientation="h",
            spacing=12,
            h_align="center",
            v_align="center",
        )
        self.content.add(self._grid)
        self.children = [self.content]

        # ── keyboard + focus events ─────────────────────────
        self.connect("key-press-event", self._on_key_press)
        self.connect("key-release-event", self._on_key_release)
        self.connect("focus-out-event", self._on_focus_out)

        logger.info("AltTab ready")

    # ────────────────────────────────────────────────────────
    #  Glace lifecycle (Fabrika Pager pattern)
    # ────────────────────────────────────────────────────────

    def _on_client_added(self, manager: Glace.Manager, client: Glace.Client):
        client.connect("notify::hyprland-address", self._on_client_ready)

    def _on_client_ready(self, client: Glace.Client, _pspec):
        address = client.get_hyprland_address()
        if not address or address in self._client_views:
            return

        preview = ClientPreview(client, self._glace)
        self._client_views[address] = preview

        client.connect("notify::activated", self._on_activated, client)
        if client.get_activated():
            self._focus_order.insert(0, client)
        else:
            self._focus_order.append(client)

        if not self.is_hidden:
            self._rebuild()

    def _on_activated(self, _obj, _pspec, client: Glace.Client):
        # ← guard: don't waste cycles reordering when hidden
        if client.get_activated():
            if client in self._focus_order:
                self._focus_order.remove(client)
            self._focus_order.insert(0, client)

    def _on_client_closed(self, address: int):
        if preview := self._client_views.pop(address, None):
            preview.tick.stop()

    def remove_client_view(self, address: int):
        if view := self._client_views.pop(address, None):
            parent = view.get_parent()   # ← fixed: parent might be row box
            if parent:
                parent.remove(view)
            view.destroy()

        self._focus_order = [
            c for c in self._focus_order if c.get_hyprland_address() != address
        ]

        if not self.is_hidden:
            if self._selected >= len(self._focus_order):
                self._selected = max(0, len(self._focus_order) - 1)
            self._rebuild()

    # ────────────────────────────────────────────────────────
    #  Sync with Hyprland (Fabrika Pager.do_sync_state pattern)
    # ────────────────────────────────────────────────────────

    def _sync(self):
        """Pull fresh window data from Hyprland and update previews."""
        if not self._client_views:
            return

        try:
            # ← use cached connection instead of re-fetching
            if not self._conn.ready:
                return

            clients = json.loads(self._conn.send_command("j/clients").reply.decode())

            seen = set()
            for c in clients:
                try:
                    addr = int(c["address"], 16)
                except (ValueError, KeyError):
                    continue
                seen.add(addr)
                if view := self._client_views.get(addr):
                    view.update_for_data(c)

            stale = set(self._client_views.keys()) - seen
            for addr in stale:
                self.remove_client_view(addr)

        except Exception as e:
            logger.debug(f"AltTab sync: {e}")

    # ────────────────────────────────────────────────────────
    #  Display
    # ────────────────────────────────────────────────────────

    def _rebuild(self):
        for ch in list(self._grid.get_children()):
            self._grid.remove(ch)

        self._sync()

        for i, client in enumerate(self._focus_order):
            addr = client.get_hyprland_address()
            view = self._client_views.get(addr)
            if view:
                view.set_selected(i == self._selected)
                self._grid.add(view)

        self._grid.show_all()

    def _swap_selection(self, old: int, new: int):
        for idx in (old, new):
            if 0 <= idx < len(self._focus_order):
                addr = self._focus_order[idx].get_hyprland_address()
                if view := self._client_views.get(addr):
                    view.set_selected(idx == new)

    # ────────────────────────────────────────────────────────
    #  Auto-activate timer (handles ALT release problem)
    # ────────────────────────────────────────────────────────

    def _reset_activate_timer(self):
        if self._activate_timeout:
            GLib.source_remove(self._activate_timeout)
        self._activate_timeout = GLib.timeout_add(1000, self._auto_activate)

    def _cancel_activate_timer(self):
        if self._activate_timeout:
            GLib.source_remove(self._activate_timeout)
            self._activate_timeout = 0

    def _auto_activate(self):
        self._activate_timeout = 0
        self._do_activate()
        return False

    def _do_activate(self):
        self._cancel_activate_timer()
        if self.is_hidden:
            return
        client = (
            self._focus_order[self._selected]
            if self._focus_order and self._selected < len(self._focus_order)
            else None
        )
        self._hide()
        if client:
            client.activate()

    def toggle_window(self):
        if self.is_hidden:
            self._selected = 1
            self._show()
        else:
            self._hide()

    # ── keyboard handlers ───────────────────────────────────

    def _on_key_press(self, _, event):
        if event.keyval == Gdk.KEY_Escape:
            self.cmd_cancel()
            return True
        return False

    def _on_key_release(self, _, event):
        if event.keyval in (Gdk.KEY_Alt_L, Gdk.KEY_Alt_R):
            self.cmd_activate()
            return True
        return False

    def _on_focus_out(self, *_):
        if not self.is_hidden and not self._focus_timeout:
            self._focus_timeout = GLib.timeout_add(200, self._do_focus_lost)
        return False

    def _do_focus_lost(self):
        self._focus_timeout = 0
        if not self.is_hidden:
            self.cmd_activate()
        return False

    def _cancel_focus_timeout(self):
        if self._focus_timeout:
            GLib.source_remove(self._focus_timeout)
            self._focus_timeout = 0

    # ── show / hide ─────────────────────────────────────────

    def _show(self):
        self._cancel_focus_timeout()
        self.is_hidden = False
        self._show_time = GLib.get_monotonic_time() / 1_000_000
        self._rebuild()
        self.show()
        self.grab_focus()

    def _hide(self):
        self._cancel_focus_timeout()
        self._cancel_activate_timer()         # ← clean up timer
        self.is_hidden = True
        for view in self._client_views.values():  # ← stop all captures
            view.tick.stop()
        self.hide()

    # ────────────────────────────────────────────────────────
    #  Public commands
    # ────────────────────────────────────────────────────────

    def cmd_next(self):
        now = GLib.get_monotonic_time() / 1_000_000

        if self.is_hidden:
            self._selected = 1
            self._show()
        elif self._focus_order:
            if now - self._show_time < 0.06:
                return
            old = self._selected
            self._selected = (self._selected + 1) % len(self._focus_order)
            self._swap_selection(old, self._selected)

    def cmd_activate(self):
        if self.is_hidden:
            return
        client = (
            self._focus_order[self._selected]
            if self._focus_order and self._selected < len(self._focus_order)
            else None
        )
        if client:
            client.activate()
        self._hide()

    def cmd_cancel(self):
        self._hide()