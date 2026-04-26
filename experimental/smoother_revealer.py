import fabric
from fabric import Application
from fabric.widgets.window import Window
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label

from hacktk import HackedRevealer


class RevealerTester(Window):
    def __init__(self):
        super().__init__(
            title="Revealer Test",
            all_visible=True,
            exclusive=True,
        )

        # 1. Create the Revealer
        # transition_type options: "slide_right", "slide_left", "slide_up", "slide_down", "crossfade"
        self.revealer = HackedRevealer( 
            child=Label(label="✨ You found the hidden content! ✨\nsd\n\n\n\n\n\nn\n\n\ndddddddddddddas", style="margin: 10px;background: cyan; border-radius: 5px; padding: 20px;"),
        )

        # 2. Create a Toggle Button
        self.toggle_btn = Button(
            label="Toggle Reveal",
            on_clicked=self.on_toggle
        )

        # 3. Layout
        self.box = Box(
            orientation="v",
            spacing=10,
            style="padding: 20px;",
            children=[
                self.toggle_btn,
                self.revealer
            ]
        )

        self.add(self.box)
        self.show_all()

    def on_toggle(self, button):
        # Simply flip the reveal_child boolean
        self.revealer.set_reveal_child(not self.revealer.get_reveal_child())

if __name__ == "__main__":
    app = Application(RevealerTester())
    app.run()