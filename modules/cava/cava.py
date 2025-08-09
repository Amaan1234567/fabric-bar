from fabric import Fabricator
from fabric.utils import exec_shell_command_async, get_relative_path
from fabric.widgets.box import Box
from fabric.widgets.label import Label




class CavaWidget(Box):

    def __init__(self, **kwargs):
        super().__init__(orientation="h", spacing=1,name="cava", **kwargs)

        self.bars = 12

        self.cava_label = Label(
            v_align="center",
            h_align="center",
        )

        script_path = get_relative_path("../../scripts/cava.sh")

        self.children = self.cava_label
        self.update_service = Fabricator(
            interval=100,
            poll_from=f"{script_path} {self.bars}",
            stream=True,
        ).connect("changed",self.update_label)
        
        

    def update_label(self,_, label):
        if( label == "▁"*self.bars): #means nothing playing
            label=""
        self.cava_label.set_label(label)
        #print(label)
        return True