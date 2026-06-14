# convert_icon_linux.py
# =========================================================
# Converts logo/logo.svg → theflow.png for the Linux RPM
# Run once before building: python3 convert_icon_linux.py
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
        print("Install deps first:  pip3 install cairosvg Pillow")
        sys.exit(1)

    svg_path = os.path.join("logo", "logo.svg")
    png_path = "theflow.png"

    if not os.path.isfile(svg_path):
        print(f"ERROR: {svg_path} not found. Run from the theFlow project root.")
        sys.exit(1)

    # 256x256 is the standard size for Linux app icons
    png_bytes = cairosvg.svg2png(
        url=svg_path,
        output_width=256,
        output_height=256
    )
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    img.save(png_path, format="PNG")
    print(f"Saved: {png_path}  (256x256 RGBA)")

if __name__ == "__main__":
    convert()
