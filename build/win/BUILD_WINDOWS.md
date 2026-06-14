# theFlow! — Windows 64-bit Build Instructions

## Prerequisites

- Windows 10 or 11 (64-bit)
- Python 3.10, 3.11, or 3.12 — **64-bit installer** from python.org
  - During install: tick **"Add Python to PATH"**
- Your full theFlow! source folder with all .py files

---

## Step 1 — Install dependencies

Open Command Prompt or PowerShell in your theFlow project folder:

```
pip install PyQt6 PyQt6-Qt6 PyQt6-sip pyinstaller Pillow
```

Verify PyQt6 works:
```
python -c "from PyQt6.QtWidgets import QApplication; print('PyQt6 OK')"
```

---

## Step 2 — Convert your logo to .ico

PyInstaller needs a `.ico` file for the Windows taskbar icon.

**Option A — with Python:**
```
pip install Pillow
python convert_icon_windows.py
```
Saves `logo/F!.ico` from `logo/F!.png`

**Option B — online:**
Go to https://convertio.co/svg-ico/ and convert `logo/logo.svg` → `logo/logo.ico`

**Option C — skip the icon:**
Remove the `icon='icons\\logo.ico'` line from `theflow.spec`

---

## Step 3 — Create the settings folder

```
mkdir settings
```

---

## Step 4 — Project folder structure

```
theflow/
├── main.py                  ← entry point
├── rthook_theflow.py        ← runtime hook
├── theflow.spec             ← PyInstaller spec
├── theflow_setup.iss        ← Inno Setup installer script
├── build_windows.bat        ← builds exe + installer in one step
├── version_info.txt         ← EXE metadata
├── convert_icon_windows.py  ← icon converter (run once)
├── backdrop.py
├── config.py
├── curve.py
├── group.py
├── logo.py
├── menu.py
├── node.py
├── note.py
├── paint.py
├── paint_on_canvas.py
├── reference.py
├── scene_logic.py
├── settings.py
├── ui_components.py
├── utils.py
├── view_logic.py
├── web.py
├── logo/
│   ├── logo.svg
│   ├── logo.ico             ← converted in Step 2
│   └── F!.png
├── icons/
│   └── logo.ico
├── documentation/
│   └── theFlow_manual.html
└── settings/                ← empty folder, create if missing
```

---

## Step 5 — Build everything

```
build_windows.bat
```

This runs PyInstaller then Inno Setup automatically.

Output:
- `dist\theFlow.exe` — standalone executable
- `dist\theFlow-0.1.0-setup.exe` — Windows installer

---

## Step 6 — Install and test

Run the installer:
```
dist\theFlow-0.1.0-setup.exe
```

Or test the exe directly:
```
dist\theFlow.exe
```

Double-click a `.flow` file — it should open directly in theFlow!

---

## How double-click works

The installer registers `.flow` files in the Windows registry so that:
- `.flow` files show the theFlow! icon in Explorer
- Double-clicking passes the file path as `sys.argv[1]` to the app
- The app calls `load_file(sys.argv[1])` on startup

This is handled by `[Registry]` entries in `theflow_setup.iss` and
the `load_file()` method in `view_logic.py`.

---

## Settings location on Windows

Settings are saved next to the `.exe`:
```
<install folder>\settings\settings.json
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| App does not launch | Run `dist\theFlow.exe` from terminal to see errors |
| Double-click opens empty scene | Reinstall — registry entries need installer to run |
| Settings not saving | Ensure install folder is writable |
| Missing Qt multimedia | Add `PyQt6.QtMultimedia` to `hiddenimports` in spec |
| Logo not showing | Check `logo/logo.svg` is in spec datas |
| Icon missing on .flow files | Re-run installer, then log out and back in |

---

## File sizes

| File | Size |
|------|------|
| `dist\theFlow.exe` | ~80–120 MB |
| `dist\theFlow-0.1.0-setup.exe` | ~80–120 MB |

Qt6 + multimedia is large — this is normal. UPX is disabled because
it can corrupt Qt multimedia plugins.
