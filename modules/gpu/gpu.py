"""GPU Stats Widget for Fabric Bar"""
import subprocess
import threading
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from gi.repository import GLib

from custom_widgets.animated_scale import AnimatedScale

MAX_DEVICES_DISPLAYED = 3


class GpuWidget(Box):
    "Thread-safe GPU stats widget"

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

        # Start the update loop (every 2 seconds)
        GLib.timeout_add(2000, self._trigger_update)

    def _trigger_update(self):
        # Fire and forget: Move the heavy lifting to a background thread
        threading.Thread(target=self._fetch_gpu_data, daemon=True).start()
        return True  # Keep the timeout alive

    def _fetch_gpu_data(self):
        """Runs in a background thread to fetch expanded metrics."""
        # Querying: Name, GPU Util %, Mem Used (MiB), Mem Total (MiB), Temp, Graphics Clock, Mem Clock, Power
        cmd = [
            "nvidia-smi",
            "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,clocks.gr,clocks.mem,power.draw",
            "--format=csv,noheader,nounits",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split("\n")

            devices_data = []
            for index, line in enumerate(lines):
                if index >= MAX_DEVICES_DISPLAYED:
                    break
                parts = [p.strip() for p in line.split(",")]
                if len(parts) == 8:
                    used_mib = float(parts[2])
                    total_mib = float(parts[3])

                    # Calculate GB and VRAM fill percentage
                    used_gb = used_mib / 1024
                    vram_percent = (used_mib / total_mib) * 100

                    devices_data.append(
                        {
                            "name": parts[0],
                            "gpu_util": float(parts[1]),
                            "used_gb": used_gb,
                            "vram_percent": vram_percent,
                            "temp": parts[4],
                            "gpu_clock": parts[5],
                            "mem_clock": parts[6],
                            "power": parts[7],
                            "index": index,
                        }
                    )

            if devices_data:
                GLib.idle_add(self._apply_ui_updates, devices_data)

        except Exception as e:
            print(f"GPU Thread Error: {e}")

    def _apply_ui_updates(self, devices_data):
        """Updates widgets on the Main Thread."""
        primary = devices_data[0]
        
        # Scale 1: GPU Core Activity
        self.usage_scale.animate_value(primary["gpu_util"])
        self.usage_scale.set_value(primary["gpu_util"])
        
        # Scale 2: VRAM Capacity Used (%)
        self.memory_usage_scale.animate_value(primary["vram_percent"])
        self.memory_usage_scale.set_value(primary["vram_percent"])

        # Detailed Tooltip
        markup = ""
        for dev in devices_data:
            # Using the Device Name as the underlined heading
            markup += (
                f"<u><b>{dev['name']} (GPU {dev['index']})</b></u>\n"
                f"Memory: {dev['used_gb']:.2f} GB utilized\n"
                f"Temperature: {dev['temp']}°C\n"
                f"Graphics Clock: {dev['gpu_clock']} MHz\n"
                f"Memory Clock: {dev['mem_clock']} MHz\n"
                f"Power Draw: {dev['power']} W\n"
            )
            # Add a vertical spacer between cards if there are multiple
            if dev != devices_data[-1]:
                markup += "\n"
        
        self.set_tooltip_markup(markup.strip())
        return False
