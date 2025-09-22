from fabric import Fabricator
from fabric.utils import get_relative_path
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from loguru import logger

class CavaWidget(Box):
    """music visualiser widget, uses unicode bar symbols to visualise music
    decibel level at different frequencies
    """
    def __init__(self, **kwargs):
        super().__init__(orientation="h", spacing=1, name="cava", **kwargs)

        self.bars = 12

        self.cava_label = Label(
            label="▁" * self.bars,
            v_align="center",
            h_align="center",
        )

        script_path = get_relative_path("../../scripts/cava.sh")

        self.children = self.cava_label
        self.update_service = Fabricator(
            interval=100,
            poll_from=f"{script_path} {self.bars}",
            stream=True,
        ).connect("changed", self._update_label)

        ctx = self.get_style_context()
        ctx.add_class("cava-active")

    def _update_label(self, _, label):
        if self.cava_label.get_label() == label:
            return True
        
        self.cava_label.set_label(label)
        logger.debug(f"cava_label:{label}")
        return True
