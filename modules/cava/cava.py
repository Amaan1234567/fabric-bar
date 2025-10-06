"""holds cava widget"""

from fabric import Fabricator
from fabric.utils import get_relative_path
from fabric.widgets.button import Button
from fabric.widgets.label import Label


class CavaWidget(Button):
    """music visualiser widget, uses unicode bar symbols to visualise music
    decibel level at different frequencies
    """

    def __init__(self, **kwargs):
        super().__init__(orientation="h", spacing=0, name="cava", **kwargs)

        self.bars = 12

        self.cava_label = Label(
            label="▁" * self.bars,
            v_align="center",
            h_align="center",
        )

        script_path = get_relative_path("../../scripts/cava.sh")

        self.children = self.cava_label
        self.update_service = Fabricator(
            poll_from=f"sh -c '{script_path} {self.bars}'",
            stream=True,
            on_changed=self._update_label
        )

        ctx = self.get_style_context()
        ctx.add_class("cava-active")

    def _update_label(self, _, label):
        self.cava_label.set_label(label)
        return True
