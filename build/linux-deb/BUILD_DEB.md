# theFlow! — DEB Build Instructions
## For Ubuntu / Debian / Linux Mint (x86_64)

## Prerequisites

- Ubuntu 20.04+, Debian 11+, or Linux Mint 20+ (64-bit)
- Internet connection for the first install
- Your full theFlow source folder with all .py files

---

## Option A — Automatic (recommended)

Just run the build script and it does everything:

```
chmod +x build_deb.sh
./build_deb.sh
```

Your .deb will be at:
```
dist/theflow_0.1.0_amd64.deb
```

---

## Option B — Manual step by step

### 1. Install system dependencies
```
sudo apt install python3-pip dpkg-dev
sudo apt install libgl1 libgl1-mesa-glx
```

> Note: GStreamer is NOT required — theFlow uses the FFmpeg backend
> bundled inside PyQt6.

### 2. Install Python dependencies
```
pip3 install PyQt6 PyQt6-Qt6 PyQt6-sip pyinstaller Pillow
```

### 3. Project folder structure
```
theflow/
├── main.py
├── rthook_theflow.py
├── theflow.spec
├── theflow.desktop
├── theflow-mime.xml
├── build_deb.sh
├── backdrop.py
├── config.py
├── curve.py
├── logo.py
├── menu.py
├── node.py
├── note.py
├── paint.py
├── paint_on_canvas.py
├── scene_logic.py
├── settings.py
├── ui_components.py
├── utils.py
├── view_logic.py
├── logo/
│   ├── logo.svg
│   └── theFlow_white.svg
├── icons/
│   └── icon.png
├── documentation/
│   └── theFlow_manual.html
└── settings/          ← create this if it doesn't exist
```

### 4. Create empty settings folder
```
mkdir -p settings
```

### 5. Build the binary
```
python3.9 -m PyInstaller theflow.spec
```
Output: `dist/theflow`

> Important: do NOT use UPX or strip — it corrupts the bundled FFmpeg
> libraries and breaks audio/video playback. The spec already sets
> strip=False and upx=False correctly.

### 6. Build the .deb
```
bash build_deb.sh
```

---

## Install

```
sudo dpkg -i dist/theflow_0.1.0_amd64.deb
sudo gtk-update-icon-cache -f -t /usr/share/icons/hicolor
sudo update-desktop-database
```

Run:
```
theflow
```

Uninstall:
```
sudo dpkg -r theflow
```

---

## Settings location

Settings are saved to:
```
~/.config/theflow/settings.json
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| App does not launch | Run `theflow` from terminal to see errors |
| Blank window / no display | `QT_QPA_PLATFORM=xcb theflow` |
| No QtMultimedia backends | Rebuild with `strip=False` and `upx=False` |
| Audio/video not playing | Do NOT use strip or UPX — corrupts FFmpeg libs |
| Missing libGL error | `sudo apt install libgl1` |
| Wayland issues | `QT_QPA_PLATFORM=xcb theflow` forces X11 |
| Icon not showing | `sudo gtk-update-icon-cache -f /usr/share/icons/hicolor` |
| .flow file opens empty | Make sure theflow.desktop has `Exec=/usr/bin/theflow %f` |

---

## Notes

- Binary size is ~200–300 MB (FFmpeg is bundled — this is normal)
- UPX compression is disabled — it corrupts FFmpeg shared libraries
- The same `dist/theflow` binary works for both RPM and DEB packaging
