# theFlow! — RPM Build Instructions
# For Fedora / RHEL / CentOS / Rocky Linux (x86_64)

## Prerequisites

- Fedora, RHEL 9, Rocky Linux 9, or CentOS Stream 9 (64-bit)
- Internet connection for the first install
- Your full theFlow source folder with all .py files

---

## Option A — Automatic (recommended)

Just run the build script and it does everything:

```
chmod +x build_rpm.sh
./build_rpm.sh
```

That's it. Your RPM will be at:
```
~/rpmbuild/RPMS/x86_64/theflow-0.1.0-1.fc*.x86_64.rpm
```

Skip to "Test it" below.

---

## Option B — Manual step by step

### 1. Install system dependencies
```
sudo dnf install gcc rpm-build rpmlint upx
sudo dnf install gstreamer1-plugins-base gstreamer1-plugins-good
sudo dnf install mesa-libGL libGL python3-pip
```

### 2. Install Python dependencies
```
pip3 install PyQt6 PyQt6-Qt6 PyQt6-sip pyinstaller cairosvg Pillow
```

### 3. Place all files in the same folder
```
theflow/
├── main_linux.py            ← from this package
├── rthook_linux.py          ← from this package
├── theflow_linux.spec       ← from this package
├── theflow.spec             ← from this package (RPM spec)
├── theflow.desktop          ← from this package
├── convert_icon_linux.py    ← from this package
├── config.py                ← use the patched version
├── backdrop.py
├── curve.py
├── logo.py
├── menu.py
├── node.py
├── note.py
├── paint.py
├── scene_logic.py
├── settings.py
├── ui_components.py
├── utils.py
├── view_logic.py
├── logo/
│   └── logo.svg
└── settings/                ← create this empty folder
```

### 4. Convert the logo
```
python3 convert_icon_linux.py
```
Creates `theflow.png` (256x256) in the project root.

### 5. Create empty settings folder
```
mkdir -p settings
```

### 6. Build the binary
```
pyinstaller theflow_linux.spec
```
Output: `dist/theflow`

### 7. Set up the rpmbuild tree
```
mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
mkdir -p ~/rpmbuild/BUILD/theflow-0.1.0

cp dist/theflow         ~/rpmbuild/BUILD/theflow-0.1.0/theflow
cp theflow.desktop      ~/rpmbuild/BUILD/theflow-0.1.0/theflow.desktop
cp logo/logo.svg        ~/rpmbuild/BUILD/theflow-0.1.0/theflow.svg
cp theflow.png          ~/rpmbuild/BUILD/theflow-0.1.0/theflow.png
cp theflow.spec         ~/rpmbuild/SPECS/theflow.spec
```

### 8. Build the RPM
```
rpmbuild -bb ~/rpmbuild/SPECS/theflow.spec
```

---

## Test it

Install on the same machine:
```
sudo rpm -ivh ~/rpmbuild/RPMS/x86_64/theflow-0.1.0-1.*.rpm
theflow
```

Uninstall:
```
sudo rpm -e theflow
```

---

## Settings location on Linux

Unlike macOS (where settings go to your Documents folder), on Linux the
bundled app writes settings next to the binary — but since the binary
lives at `/usr/bin/theflow` after install, and that's not writable by
regular users, settings instead fall back to the `frozen` path logic
in `config.py`.

**You should add this to `config.py`** for a proper Linux XDG path:

Find the `frozen` block you already added and extend it like this:

```python
if getattr(sys, 'frozen', False):
    import platform
    if platform.system() == 'Linux':
        # Use XDG config dir: ~/.config/theflow/
        _BASE_DIR = os.path.join(
            os.environ.get('XDG_CONFIG_HOME',
                           os.path.expanduser('~/.config')),
            'theflow'
        )
    else:
        # Windows: next to the .exe
        _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
```

This writes settings to `~/.config/theflow/settings.json` — the
standard Linux location, writable by the user, persists across updates.

---

## If something goes wrong

| Error | Fix |
|-------|-----|
| "No module named X" | Add module to `hiddenimports` in `theflow_linux.spec`, rebuild |
| App launches then crashes | Run `theflow` from terminal to see the traceback |
| Blank window / no display | Try `QT_QPA_PLATFORM=xcb theflow` in terminal |
| Missing libGL error | `sudo dnf install mesa-libGL` |
| Wayland issues | `QT_QPA_PLATFORM=xcb theflow` forces X11 mode |
| rpmbuild permission error | Make sure you're NOT running as root |
| Icon not showing in menu | Run `sudo gtk-update-icon-cache -f /usr/share/icons/hicolor` |

---

## File sizes to expect

| File | Approximate size |
|------|-----------------|
| `dist/theflow` binary | ~90–130 MB |
| `.rpm` package | ~55–85 MB (UPX compressed) |

Qt6 + multimedia is inherently large — this is normal.
