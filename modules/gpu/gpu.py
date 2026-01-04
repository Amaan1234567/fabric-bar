"""holds the gpu stats widget"""

import json
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.utils.helpers import exec_shell_command, invoke_repeater

from custom_widgets.animated_scale import AnimatedScale

MAX_DEVICES_DISPLAYED = 3


class GpuWidget(Box):
    "gpu stats widget with more details in tooltip"

    def __init__(self, **kwargs):
        super().__init__(name="gpu-stats", orientation="h", spacing=5)

        self.icon = Label(label="GPU", name="gpu-icon", h_align="start")

        self.usage_scale = AnimatedScale(
            name="gpu-usage-scale",
            orientation="horizontal",
            min_value=0,
            max_value=100,
            value=0,
            h_expand=True,
            v_expand=True,
        )
        self.memory_usage_scale = AnimatedScale(
            name="gpu-mem-usage-scale",
            orientation="horizontal",
            min_value=0,
            max_value=100,
            value=0,
            h_expand=True,
            v_expand=True,
        )

        self.scales_holder = Box(
            name="gpu-scales-container",
            orientation="v",
            children=[self.usage_scale, self.memory_usage_scale],
            spacing=1,
        )
        self.add(self.icon)
        self.add(self.scales_holder)

        invoke_repeater(1000, self._process_data)

    def _process_data(self):
        # print("data: ",data)
        data = exec_shell_command("nvtop -s")
        if data is False:
            return
        devices = json.loads(data)
        # print(float(devices[0]["gpu_util"][:-1]))
        self.usage_scale.animate_value(float(devices[0]["gpu_util"][:-1]))
        self.usage_scale.set_value(float(devices[0]["gpu_util"][:-1]))
        self.memory_usage_scale.animate_value(float(devices[0]["mem_util"][:-1]))
        self.memory_usage_scale.set_value(float(devices[0]["mem_util"][:-1]))

        self._set_tooltip(devices)

        return True

    def _set_tooltip(self, devices):
        markup = "<u>GPU Stats</u>\n"

        for idx, device in enumerate(devices[:MAX_DEVICES_DISPLAYED]):
            markup += f"GPU: {device["device_name"]}" + "\n"
            markup += f"Clock Speed: {device["gpu_clock"]}" + "\n"
            markup += f"Memory Speed: {device["mem_clock"]}" + "\n"
            markup += f"Power Draw: {device["power_draw"]}"
            if idx != min(len(devices) - 1, MAX_DEVICES_DISPLAYED - 1):
                markup += "\n\n"
        self.set_tooltip_markup(markup)
