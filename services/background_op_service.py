"""service that reports status on background ops like wallpaper cache building"""

from fabric.core.service import Service, Signal


class BackgroundOpService(Service):
    """Service for reporting background op status"""

    @Signal
    def progress_update(self):
        """Emitted when the progress of a background operation changes."""

    @Signal
    def state_update(self):
        """Emitted when the state of a background operation changes."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.display_text = ""
        self.progress = 0

    def set_display_text(self, text: str):
        """Set the display text for the background operation."""
        self.display_text = text
        self.state_update.emit()

    def set_progress(self, progress: int):
        """Set the progress for the background operation."""
        self.progress = progress
        self.progress_update.emit()

    def get_display_text(self) -> str:
        """Get the display text for the background operation."""
        return self.display_text

    def get_progress(self) -> int:
        """Get the progress for the background operation."""
        return self.progress
