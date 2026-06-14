# Building theFlow! — macOS .app Bundle

## What you need

| Tool | Install |
|---|---|
| Python 3.10–3.12 | [python.org](https://python.org) or `brew install python` |
| pip | Comes with Python |
| Xcode CLI tools | `xcode-select --install` |

---

## Quick start

1. **Copy these two files into your project root** (same folder as `main.py`):
   - `theflow.spec`
   - `build_mac.sh`

2. **Make the script executable and run it:**
   ```bash
   chmod +x build_mac.sh
   ./build_mac.sh
   ```

3. **Find your app at** `dist/theFlow.app`  
   Double-click it or run `open dist/theFlow.app`.

---

## What the script does

1. Upgrades `pip`, then installs `pyinstaller`, `PyQt6`, and `PyQt6-sip`.
2. Cleans any old `build/` and `dist/` folders.
3. Runs `pyinstaller theflow.spec` to produce `dist/theFlow.app`.
4. Ad-hoc code-signs the bundle so macOS will launch it without a paid Developer account.

---

## Project layout expected

```
your-project/
├── main.py
├── backdrop.py
├── config.py
├── curve.py
├── logo.py          ← module
├── logo/
│   └── logo.svg     ← SVG asset (must exist)
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
├── theflow.spec     ← from this package
└── build_mac.sh     ← from this package
```

> **logo/logo.svg** — the spec bundles the entire `logo/` folder.  
> If your SVG is somewhere else, edit the `added_files` list in `theflow.spec`.

---

## Optional: custom dock icon

1. Create a `logo/theflow.icns` file (use **Image2Icon** or **iconutil**).
2. Uncomment this line in `theflow.spec`:
   ```python
   # icon="logo/theflow.icns",
   ```
3. Re-run `./build_mac.sh`.

---

## Optional: create a distributable DMG

```bash
hdiutil create -volname "theFlow" \
  -srcfolder dist/theFlow.app \
  -ov -format UDZO \
  dist/theFlow.dmg
```

---

## Universal binary (Apple Silicon + Intel)

PyInstaller can only build for the architecture of the machine running it.  
To produce a true universal binary you need to:

1. Build on an Intel Mac → `dist/theFlow-x86.app`
2. Build on an Apple Silicon Mac → `dist/theFlow-arm.app`
3. Merge with `lipo`:
   ```bash
   # (advanced — merge the inner Mach-O executables)
   ```
   Or simply ship the arm64 build; it runs natively on Apple Silicon and under Rosette on Intel.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` at launch | Add the module name to `hiddenimports` in `theflow.spec` |
| App crashes on multimedia playback | Ensure `AVFoundation` is available; don't set `QT_VIDEO_BACKEND=dummy` |
| "App is damaged" on another Mac | You need a paid Apple Developer ID to notarise for distribution |
| SVG logo not showing | Check the `logo/logo.svg` path and the `added_files` entry in the spec |
