from fabric.widgets.scale import Scale
from utils.animator import Animator

class AnimatedScale(Scale):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.animator = (
            Animator(
                # edit the following parameters to customize the animation
                bezier_curve=(0.8, 1.55, 0.265, 1.25),
                duration=0.3,
                min_value=self.min_value,
                max_value=self.value,
                tick_widget=self,
                notify_value=lambda p, *_: self.set_value(p.value),
            )
            .build()
            .play()
            .unwrap()
        )

    def animate_value(self, value: float):
        self.animator.pause()
        self.animator.min_value = self.value
        self.animator.max_value = value
        self.animator.play()
        return