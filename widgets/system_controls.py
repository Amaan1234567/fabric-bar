from fabric.widgets.box import Box

from modules.audio.audio import AudioWidget
from modules.bluetooth.bluetooth import BluetoothWidget
from modules.network.network import NetworkWidget


class SystemControls(Box):
    def __init__(self, window=None, **kwargs):
        super().__init__(**kwargs)
        self.children = [
            Box(
                name="system-controls",
                orientation="h",
                spacing=10,
                children=[
                    AudioWidget(window=window),
                    NetworkWidget(window=window),
                    BluetoothWidget(),
                ],
            )
        ]
