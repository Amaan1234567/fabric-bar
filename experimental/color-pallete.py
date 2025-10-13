import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
from colorist import BgColorRGB
import subprocess


def extract_colors_kmeans(image_path: str, n_colors: int = 16):
    """Extract dominant colors using K-means clustering"""
    try:
        # Load and prepare the image
        with Image.open(image_path) as img:
            img = img.convert("RGB")

            # Convert image to numpy array
            img_array = np.array(img)

            # Reshape to (num_pixels, 3) for RGB values
            pixels = img_array.reshape(-1, 3)

            # Apply K-means clustering
            kmeans = KMeans(
                n_clusters=n_colors, random_state=42, init="k-means++", n_init=1
            )
            kmeans.fit(pixels)

            # Get the color centroids (dominant colors)
            colors = kmeans.cluster_centers_.astype(int)

            # Get labels to calculate color dominance
            labels = kmeans.labels_

            # Calculate percentage of each color
            unique, counts = np.unique(labels, return_counts=True)
            percentages = counts / len(labels) * 100

            # Sort colors by dominance
            # print(colors)
            sorted_indices = np.argsort(percentages)[::-1]  # Descending order
            dominant_colors = colors[sorted_indices]
            # print(dominant_colors)
            dominant_percentages = percentages[sorted_indices]

            return dominant_colors, dominant_percentages

    except Exception as e:
        print(f"Error extracting colors: {e}")
        return None, None


def display_color_palette(colors, percentages):
    """Display the color palette with percentages"""
    if colors is None:
        print("No colors to display")
        return

    print("🎨 K-means Color Palette (by dominance):")

    # Display color blocks
    palette_row = ""
    for i, (color, percentage) in enumerate(zip(colors, percentages)):
        r, g, b = color
        bg_color = BgColorRGB(r, g, b)
        palette_row += f"{bg_color}  {bg_color.OFF}"

        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        print(
            f"Color {i+1}: {bg_color}  {bg_color.OFF} RGB({r},{g},{b}) {hex_color} ({percentage:.1f}%)"
        )

    print(f"\nPalette: {palette_row}")

    # Show hex codes
    hex_codes = [f"#{r:02x}{g:02x}{b:02x}" for r, g, b in colors]
    print(f"Hex:     {' '.join(hex_codes)}")


if __name__ == "__main__":
    # Extract colors using K-means
    colors, percentages = extract_colors_kmeans(
        subprocess.getoutput("swww query | awk -F'image: ' '{print $2}'"), n_colors=8
    )
    # print(colors)
    if colors is not None:
        display_color_palette(colors, percentages)
    else:
        print("Failed to extract colors")
