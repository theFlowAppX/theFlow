# convert_icon_windows.py
# =========================================================
# Converts logo/F!.png → logo/F!.ico for the Windows build
# Run once before building: python convert_icon_windows.py
# Requires: pip install Pillow
# =========================================================

import os
import sys

def convert():
    try:
        from PIL import Image
    except ImportError:
        print("Install deps:  pip install Pillow")
        sys.exit(1)

    png_path = os.path.join("logo", "F!.png")
    ico_path = os.path.join("logo", "F!.ico")

    if not os.path.isfile(png_path):
        print(f"ERROR: {png_path} not found. Run from the theFlow project root.")
        sys.exit(1)

    img = Image.open(png_path).convert("RGBA")

    # Save ICO with multiple sizes for Windows
    sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
    icons = [img.resize(s, Image.LANCZOS) for s in sizes]
    img.save(ico_path, format="ICO", sizes=sizes)
    print(f"Saved: {ico_path}  (multi-size Windows icon)")

if __name__ == "__main__":
    convert()
