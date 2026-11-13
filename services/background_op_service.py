"""service that reports status on background ops like wallpaper cache building"""

from fabric.core.service import Service, Signal


class BackgroundOp(Service):
    """background Op"""

    @Signal
    def progress_update(self, value: int):
        """Emitted when the progress of a background operation changes."""

    @Signal
    def state_update(self):
        """Emitted when the state of a background operation changes."""

    @Signal
    def op_complete(self,op_name):
        """Emitted when op is complete"""

    def __init__(self, op_name,display_text,progress, **kwargs):
        super().__init__(**kwargs)
        self.op_name = op_name
        self.progress = progress
        self.display_text = display_text

    def set_display_text(self, text: str):
        """Set the display text for the background operation."""
        self.display_text = text
        self.state_update.emit()

    def set_progress(self, progress: int):
        """Set the progress for the background operation."""
        self.progress = progress
        self.progress_update.emit(progress)
        if progress == 100:
            self.op_complete(self.op_name)

    def get_display_text(self) -> str:
        """Get the display text for the background operation."""
        return self.display_text

    def get_progress(self) -> int:
        """Get the progress for the background operation."""
        return self.progress


class BackgroundOpService(Service):
    """Service for reporting background op status"""

    @Signal
    def background_op_started(self, op_obj: BackgroundOp):
        """background op start signal"""

    @Signal
    def background_op_finished(self, op_obj: BackgroundOp):
        """background op finish signal"""

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_op = {}

    def list_background_ops(self):
        """List all background operations."""
        return self.background_op

    def _op_complete_handler(self,op_name:str):
        op_obj =self.background_op.pop(op_name)
        self.background_op_finished(op_obj)


    def set_background_op(self, op_name: str, display_text: str, progress: int):
        """Set the background operation details."""
        op = BackgroundOp(op_name,display_text,progress)
        op.connect("op_complete",self._op_complete_handler)
        self.background_op[op_name]=op
        self.background_op_started.emit(op)
