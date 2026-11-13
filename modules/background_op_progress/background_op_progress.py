"""background op widget"""
from fabric.widgets.box import Box

from custom_widgets.animated_circular_progress_bar import AnimatedCircularProgressBar
from services.background_op_service import BackgroundOpService, BackgroundOp


class BackgroundOpProgress(Box):
    """Background Op widget"""

    def __init__(self,**kwargs):

        super().__init__(self,name="background-op-widget",**kwargs)

        self.content = Box(h_expand=True,h_align="center",v_align="center")
        self.progress_bar = AnimatedCircularProgressBar(
            name="background-op-circular-progress-bar",
            min_value=0,
            max_value=100,
            value = 0
        )
        self.background_op_service = BackgroundOpService()
        self.background_op_service.connect("background_op_started",self._new_background_op_handler)
        self.background_op_service.connect("background_op_finshed",self._background_op_finished_handler)
        


    def _new_background_op_handler(self,op:BackgroundOp):
        op.connect("state_update",self._state_update_handler)
        op.connect("progress_update",self._progress_update_handler)

    def _state_update_handler(self,op_name:str):
        
        
        
    def _progress_update_handler(self,op_name:str,value:int):    
        self.progress_bar.animate_value(value)
        self.progress_bar.value = value

