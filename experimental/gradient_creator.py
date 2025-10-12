from PIL import Image
import numpy as np


width = 500
height = 300
colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)] # Red, Green, Blue, Yellow
image_array = np.zeros((height, width, 3), dtype=np.uint8)
num_colors = len(colors)
segment_width = width // (num_colors - 1) if num_colors > 1 else width

for x in range(width):
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
        interpolated_color = start_color + (end_color - start_color) * interpolation_factor
        image_array[:, x, :] = interpolated_color.astype(np.uint8)

gradient_image = Image.fromarray(image_array)
gradient_image.save("./multi_color_gradient.png")