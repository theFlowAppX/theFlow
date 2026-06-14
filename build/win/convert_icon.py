# convert_icon.py
# =========================================================
# Converts logo/logo.svg → logo/logo.ico for Windows
# Run once before building: python convert_icon.py
# Requires: pip install cairosvg Pillow
# =========================================================

import os
import sys

def convert():
    try:
        import cairosvg
        from PIL import Image
        import io
    except ImportError:
        print("Install deps first:  pip install cairosvg Pillow")
        sys.exit(1)

    svg_path = os.path.join("logo", "logo.svg")
    ico_path = os.path.join("logo", "logo.ico")

    if not os.path.isfile(svg_path):
        print(f"ERROR: {svg_path} not found. Run from the theFlow project root.")
        sys.exit(1)

    # Render at multiple sizes for a proper multi-resolution .ico
    sizes = [16, 32, 48, 64, 128, 256]
    images = []
    for size in sizes:
        png_bytes = cairosvg.svg2png(
            url=svg_path,
            output_width=size,
            output_height=size
        )
        img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        images.append(img)

    # Save as .ico with all sizes embedded
    images[0].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:]
    )
    print(f"Saved: {ico_path}  ({len(sizes)} sizes embedded)")

if __name__ == "__main__":
    convert()
