"""holds network speed widget"""

from threading import Thread
import time
import psutil
from loguru import logger
from gi.repository import GLib #type: ignore
from fabric.widgets.box import Box
from fabric.widgets.label import Label


class NetworkSpeed(Box):
    """network speed widget, shows current network speed and ping in tooltip"""

    def __init__(self, **kwargs):
        super().__init__(orientation="h", name="network-speed", spacing=5)

        self.download_icon = Label(name="download-icon", label="")
        self.download_speed = Label(name="download-speed", label="")

        self.upload_icon = Label(name="upload-icon", label="")
        self.upload_speed = Label(name="upload-speed", label="")

        self.add(self.download_icon)
        self.add(self.download_speed)

        self.add(self.upload_icon)
        self.add(self.upload_speed)

        self._update_stats()

    def _update_stats(self):
        Thread(target=self._get_network_speed, daemon=True).start()

    def _get_network_speed(self):
        while True:
            # Get the initial network counters
            initial_counters = psutil.net_io_counters()

            time.sleep(1)

            # Get the counters again after the interval
            final_counters = psutil.net_io_counters()

            # Calculate the difference in bytes
            bytes_sent = final_counters.bytes_sent - initial_counters.bytes_sent
            bytes_recv = final_counters.bytes_recv - initial_counters.bytes_recv

            download_speed = 0
            upload_speed = 0

            if bytes_sent < 1_048_576 and bytes_recv < 1_048_576:
                download_speed = bytes_recv / (1024 * 1)
                upload_speed = bytes_sent / (1024 * 1)
                
                GLib.idle_add(self.download_speed.set_label,f"{download_speed:.2f} KB/s")
                GLib.idle_add(self.upload_speed.set_label,f"{upload_speed:.2f} KB/s")
            else:
                download_speed = (bytes_recv) / (1_048_576 * 1)
                upload_speed = (bytes_sent) / (1_048_576 * 1)
                GLib.idle_add(self.download_speed.set_label,f"{download_speed:.2f} MB/s")
                GLib.idle_add(self.upload_speed.set_label,f"{upload_speed:.2f} MB/s")

            logger.debug(f"download speed: {download_speed}")
            logger.debug(f"upload speed: {upload_speed}")
