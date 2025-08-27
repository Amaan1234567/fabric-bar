from gi.repository import Gtk
import subprocess
from fabric import Fabricator
from fabric.widgets.box      import Box
from fabric.widgets.label    import Label
from fabric.widgets.overlay  import Overlay
from fabric.widgets.eventbox import EventBox
from fabric.utils            import cooldown
from time import sleep
from custom_widgets.animated_scale import AnimatedScale

# ---------------------------------------------------------------- helpers
MIN_BRIGHT = 5       # avoid a black screen
STEP       = 5       # percentage per scroll “tick”

def _read_brightness() -> int:
    """
    Current brightness percentage (0-100). Converts raw units if needed.
    """
    raw  = int(subprocess.check_output(["brightnessctl", "g"], text=True))
    maxi = int(subprocess.check_output(["brightnessctl", "m"], text=True))
    pct  = int(raw * 100 / maxi)
    return max(MIN_BRIGHT, min(100, int(round(pct)))) 

def _set_brightness_rel(delta_pct: int):
    """
    Add or subtract a *relative* percentage (positive or negative).
    """
    subprocess.getoutput(" ".join(["brightnessctl", "set", f"{abs(delta_pct)}%"]))

# ------------------------------------------------------------- main widget
class BrightnessSlider(Box):
    """
    Material-You slider with overlay label and scroll support.
    """

    def __init__(self, *, step: int = STEP, name="brightness-container"):
        super().__init__(orientation="vertical", spacing=0,size=[145,30], name=name,v_expand=True,h_expand=True)
        self._step=step
        self.scale = AnimatedScale(
            name="brightness-scale",
            orientation="horizontal",
            min=MIN_BRIGHT,
            max=100,
            value=_read_brightness(),
            draw_value=False,
            h_expand=True,
            v_expand=True,
            has_origin = True,
            increments=(0.3, 0.1)
        )

        self.label = Label(
            label="󰃠",
            name="brightness-label",
            justification=Gtk.Justification.LEFT,
            v_align="center",
            h_align="start",
            h_expand=False,
            v_expand=True,
            size = [30,30]
        )
        self.scale.connect("change-value",self._on_scroll)
        self.overlay = Overlay(child=self.scale,overlays=self.label)
        self.add(self.overlay)
        # self.add(self.scale)
        # self.add(self.label)
        self.value_changing = True 
        Fabricator(poll_from=lambda E: self.get_brightness(),interval=400).connect("changed",self._refresh)

    def get_brightness(self):
        """Return the latest brightness"""
        
        return _read_brightness()

    @cooldown(0.1)                           
    def _on_scroll(self, source, event,value):
        self.value_changing = True
        """Mouse wheel sends ±STEP % *relative* increments."""
        # print("detecting")
        # print(f"event: {event}")
        # print(f"source: {source}")
        

        #print(f"value: {value}")
        # print(f"delta: {delta}")
        _set_brightness_rel(value*100)

        self.scale.animate_value(value)
        if value*100 >MIN_BRIGHT:
            self.scale.set_value(value)
            self.value_changing = False

    def _refresh(self,_,value):
        #print("refreshing")
        #print("value changing",self.value_changing)
        if value != round(self.scale.value*100) and not self.value_changing:
            self.scale.animate_value(_read_brightness()/100)
            self.scale.set_value(value/100)
