"""
This module defines the AnimatedScale widget, which extends the Scale widget
from the fabric library to add animation to the scale's value changes.
"""

from typing import Any

from fabric.widgets.scale import Scale
from utils.animator import Animator


class AnimatedScale(Scale):
    """
    A scale widget with animated value changes.
    """

    def __init__(self, **kwargs: Any):
        """
        Initializes the AnimatedScale with optional keyword arguments.

        The animation is configured using an Animator instance.
        """
        super().__init__(**kwargs)
        self.animator: Animator = (
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

    def animate_value(self, value: float) -> None:
        """
        Animates the scale's value to the specified target value.

        Args:
            value (float): The target value to animate to.
        """
        self.animator.pause()
        self.animator.min_value = self.value
        self.animator.max_value = value
        self.animator.play()
