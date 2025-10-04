"""Module of Helper functions for the project"""

from loguru import logger
from gi.repository import GdkPixbuf  # type: ignore


def create_album_art(
    original_pixbuf: GdkPixbuf.Pixbuf, size: int = 200
) -> GdkPixbuf.Pixbuf | None:
    """Helper functions to create a 1:1 pixbuf

    Args:
        original_pixbuf (GdkPixbuf.Pixbuf): original image pixbuf
        size (int, optional): size of 1:1 picture. Defaults to 200.

    Raises:
        Exception: If for some reason cropping wasnt possible

    Returns:
        GdkPixbuf.Pixbuf | None: return 1:1 pixbuf image else returns None if cropping went wrong
    """
    original_width = original_pixbuf.get_width()
    original_height = original_pixbuf.get_height()

    # Check if aspect ratio is 1:1
    if original_width == original_height:
        # Square image - just scale it
        pic = original_pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
        return pic
    else:
        # Non-square image - center crop first, then scale
        crop_size = min(original_width, original_height)
        crop_x = (original_width - crop_size) // 2
        crop_y = (original_height - crop_size) // 2

        # Create cropped pixbuf
        cropped_pixbuf = GdkPixbuf.Pixbuf.new(
            GdkPixbuf.Colorspace.RGB,
            original_pixbuf.get_has_alpha(),
            original_pixbuf.get_bits_per_sample(),
            crop_size,
            crop_size,
        )

        # Copy the center square
        logger.debug(f"cropped_pixbuf: {cropped_pixbuf}")
        if cropped_pixbuf is not None:
            original_pixbuf.copy_area(
                crop_x, crop_y, crop_size, crop_size, cropped_pixbuf, 0, 0
            )

            # Scale the cropped square
            pic = cropped_pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.HYPER)

            return pic
        else:
            logger.error("could not get cropped_pixbuf, cropped_pixbuf was None")
            raise RuntimeError("could not get cropped_pixbuf, cropped_pixbuf was None")


def truncate(text, max_len=15):
    return text if len(text) <= max_len else text[: max_len - 1] + "…"
