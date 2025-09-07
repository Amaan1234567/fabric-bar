from gi.repository import GdkPixbuf

def create_album_art(pix,size=200):
        """Create album art pixbuf with your original cropping logic"""
        try:
            # Load the original image
            if original_pixbuf := pix:
            
                # Get original dimensions
                original_width = original_pixbuf.get_width()
                original_height = original_pixbuf.get_height()
                
                # Check if aspect ratio is 1:1
                if original_width == original_height:
                    # Square image - just scale it
                    pic = original_pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
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
                        crop_size
                    )
                    
                    # Copy the center square
                    original_pixbuf.copy_area(
                        crop_x, crop_y,
                        crop_size, crop_size,
                        cropped_pixbuf,
                        0, 0
                    )
                    
                    # Scale the cropped square
                    pic = cropped_pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.HYPER)
                
                return pic
        except Exception as e:
            print(f"Error processing image: {e}")
            return None
    