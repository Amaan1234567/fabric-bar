"""
This module defines the AnimatedCircularProgressBar widget, which extends the CircularProgressBar
from the fabric library to add animation to the progress updates.
"""

from typing import Any

from fabric.widgets.circularprogressbar import CircularProgressBar
from utils.animator import Animator


class AnimatedCircularProgressBar(CircularProgressBar):
    """An animated circular progress bar."""

    def __init__(self, **kwargs: Any):
        """Initialize the progress bar with optional parameters."""
        super().__init__(**kwargs)
        self.animator: Animator = (
            Animator(
                # edit the following parameters to customize the animation
                bezier_curve=(0.34, 1.56, 0.64, 1.0),
                duration=0.8,
                min_value=self.min_value,
                max_value=self.value,
                tick_widget=self,
                notify_value=lambda p, *_: self.set_value(p.value),
            )
            .build()
            .play()
            .unwrap()
        )

    def animate_value(self, value: float) -> None:
        """Animate the value of the progress bar."""
        self.animator.pause()
        self.animator.min_value = self.value
        self.animator.max_value = value
        self.animator.play()
