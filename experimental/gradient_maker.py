from curses import window
from PIL import Image
from fabric import Application
from fabric.widgets.wayland import WaylandWindow
from fabric.widgets.label import Label
from fabric.widgets.box import Box
import numpy as np
from fabric.utils.helpers import monitor_file, get_relative_path
import re
from watcher import Watcher


class gradientMaker:
    def __init__(self, width=1220, height=62) -> None:

        self.width = width
        self.height = height
        self.watcher = Watcher(
            get_relative_path("../styles/colors.css"), self._generate_gradient_image
        )
        self.watcher.watch()

    def _hex_to_rgb_converter(self, str):
        str = str.lstrip("#")
        return tuple(int(str[i : i + 2], 16) for i in (0, 2, 4))

    def _generate_gradient_image(self):
        print("generating colors")
        colors = []
        with open(
            get_relative_path("../styles/colors.css"), "r", encoding="utf-8"
        ) as file:
            data = file.read()
            matches = re.findall(
                r"#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?(?!$)", data, re.MULTILINE
            )
            for match in matches:
                colors.append(self._hex_to_rgb_converter(match))
        colors = colors[2:7]
        image_array = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        num_colors = len(colors)
        segment_width = self.width // (num_colors - 1) if num_colors > 1 else self.width
        for x in range(self.width):
            if num_colors == 1:
                # If only one color, fill the entire image with it
                image_array[:, x, :] = colors[0]
            else:
                # Determine which color segment 'x' falls into
                segment_index = min(x // segment_width, num_colors - 2)

                # Calculate interpolation factor within the segment
                local_x = x - (segment_index * segment_width)
                interpolation_factor = local_x / segment_width

                # Get start and end colors for the current segment
                start_color = np.array(colors[segment_index])
                end_color = np.array(colors[segment_index + 1])

                # Linearly interpolate the color for the current column
                interpolated_color = (
                    start_color + (end_color - start_color) * interpolation_factor
                )
                image_array[:, x, :] = interpolated_color.astype(np.uint8)

        gradient_image = Image.fromarray(image_array)
        gradient_image.save("./assets/gradient.png")


class example(Box):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.children = [Label("hello")]
        print(get_relative_path("../styles/colors.css"))
        monitor_file("./styles/colors.css", lambda *a: print("detected change"))


if __name__ == "__main__":
    app = Application(window=WaylandWindow(child=example()))
    maker = gradientMaker()
    maker._generate_gradient_image()
    monitor_file(get_relative_path("../styles/style.css")).connect(
        "changed", lambda *a: maker._generate_gradient_image()
    )
    app.run()
