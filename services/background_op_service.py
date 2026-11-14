"""service that reports status on background ops like wallpaper cache building."""

from fabric.core.service import Service, Signal
from gi.repository import GLib  # type:ignore
from loguru import logger


class BackgroundOp(Service):
    """background Op."""

    @Signal
    def progress_update(self, value: float):
        """Emitted when the progress of a background operation changes."""

    @Signal
    def state_update(self):
        """Emitted when the state of a background operation changes."""

    @Signal
    def op_complete(self, op_name: str):
        """Emitted when op is complete."""

    def __init__(self, op_name, display_text="", progress=0.0, **kwargs):
        super().__init__(**kwargs)
        self.op_name = op_name
        self.progress = progress
        self.display_text = display_text

    def set_display_text(self, text: str):
        """Set the display text for the background operation."""
        self.display_text = text
        GLib.idle_add(self.state_update.emit)

    def set_progress(self, progress: float):
        """Set the progress for the background operation."""
        self.progress = progress
        GLib.idle_add(self.progress_update.emit, progress)
        if progress == 100:
            GLib.idle_add(self.op_complete.emit, self.op_name)

    def get_display_text(self) -> str:
        """Get the display text for the background operation."""
        return self.display_text

    def get_progress(self) -> float:
        """Get the progress for the background operation."""
        return self.progress


class BackgroundOpService(Service):
    """Service for reporting background op status."""

    _instance = None

    @Signal
    def background_op_started(self, op_obj: BackgroundOp):
        """Background op start signal."""

    @Signal
    def background_op_finished(self, op_obj: BackgroundOp):
        """Background op finish signal."""

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, **kwargs):
        if hasattr(self, "_initialized"):
            return
        super().__init__(**kwargs)
        self.background_op = {}
        self._initialized = True

    def list_background_ops(self) -> list[BackgroundOp]:
        """List all background operations."""
        return list(self.background_op.values())

    def _op_complete_handler(self, _, op_name: str):  # Fixed: added op argument
        op_obj = self.background_op.pop(op_name, None)
        if op_obj:
            self.background_op_finished.emit(op_obj)  # Fixed: added .emit()

    def set_background_op(self, op_name: str, display_text: str, progress: float):
        """Set the background operation details."""
        logger.info(
            f"Registering new backround Op:\n op_name: {op_name}\nprogress={progress}"
        )
        op = BackgroundOp(op_name, display_text, progress)
        op.connect("op_complete", self._op_complete_handler)
        self.background_op[op_name] = op
        self.background_op_started.emit(op)
        return op
