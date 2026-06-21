import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Glace", "0.1")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, Gdk, Glace, GtkLayerShell


class GlaceClientMenu(Gtk.Menu):
    def __init__(self, client, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        activate_item = Gtk.MenuItem(label="Activate")
        maximize_item = Gtk.MenuItem(label="Maximize")
        minimize_item = Gtk.MenuItem(label="Minimize")
        fullscreen_item = Gtk.MenuItem(label="Fullscreen")
        close_item = Gtk.MenuItem(label="Close")
        activate_item.connect("activate", lambda *args: self.client.activate())
        maximize_item.connect("activate", lambda *args: self.client.maximize())
        minimize_item.connect("activate", lambda *args: self.client.minimize())
        fullscreen_item.connect(
            "activate",
            lambda *args: self.client.unfullscreen()
            if self.client.get_fullscreen()
            else self.client.fullscreen(),
        )
        close_item.connect("activate", lambda *args: self.client.close())
        self.append(activate_item)
        self.append(maximize_item)
        self.append(minimize_item)
        self.append(fullscreen_item)
        self.append(close_item)
        self.show_all()

        self.client.connect(
            "notify::fullscreen",
            lambda *args: fullscreen_item.set_label(
                "UnFullscreen" if client.get_fullscreen() else "Fullscreen"
            ),
        )


class GlaceClientButton(Gtk.Button):
    def __init__(self, client, manager, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.manager = manager
        self.client.connect("changed", self.on_changed)
        self.menu = GlaceClientMenu(self.client)

        self.connect("button-press-event", self.on_press_event)
        self.connect("query-tooltip", self.on_query_tooltip)

    def on_query_tooltip(self, _, x, y, keyboard_tip, tooltip):
        box = Gtk.VBox()
        scale_down_size = 128 * 2
        image = Gtk.Image()
        box.pack_start(image, False, False, 0)
        tooltip.set_custom(box)
        box.show_all()

        def stage_two(pixbuf, first_time):
            pixbuf_size = (pixbuf.get_width(), pixbuf.get_height())
            scale_factor = min(
                scale_down_size / pixbuf.get_width(),
                scale_down_size / pixbuf.get_height(),
            )
            scaled_down = (i * scale_factor for i in pixbuf_size)
            image.set_from_pixbuf(pixbuf.scale_simple(*scaled_down, 2))
            del pixbuf

            if first_time or box.get_realized():
                self.manager.capture_client(self.client, True, stage_two, False)

        self.manager.capture_client(self.client, True, stage_two, True)

        return True

    def on_press_event(self, _, event):
        if event.button == 3:
            return self.menu.popup_at_widget(
                self, Gdk.Gravity.SOUTH, Gdk.Gravity.NORTH, event
            )
        return self.client.activate()

    def on_changed(self, *args):
        app_id = self.client.get_app_id()
        title = self.client.get_title()
        self.set_label(f"{app_id}{' <' if self.client.get_activated() else ''}")
        self.set_tooltip_text(str(title))
        if not self.get_image():
            self.set_image(
                Gtk.Image(icon_name=app_id, icon_size=Gtk.IconSize.LARGE_TOOLBAR)
            )


class GlaceTaskBar(Gtk.Box):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.manager = Glace.Manager()
        self.manager.connect("client-added", self.on_client_added)

    def on_client_added(self, _, client):
        client_button = GlaceClientButton(client, self.manager)
        self.add(client_button)
        client.connect("close", lambda *args: self.remove(client_button))
        client_button.show_all()


if __name__ == "__main__":
    window = Gtk.Window()
    window.add(GlaceTaskBar())
    GtkLayerShell.init_for_window(window)
    GtkLayerShell.auto_exclusive_zone_enable(window)
    GtkLayerShell.set_layer(window, GtkLayerShell.Layer.TOP)
    GtkLayerShell.set_anchor(window, GtkLayerShell.Edge.LEFT, True)
    GtkLayerShell.set_anchor(window, GtkLayerShell.Edge.TOP, True)
    GtkLayerShell.set_anchor(window, GtkLayerShell.Edge.RIGHT, True)
    window.show_all()

    Gtk.main()