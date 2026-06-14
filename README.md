# theFlow!

A visual node-based canvas application for creative workflows.

![theFlow!](logo/logo.svg)

## Features

- Infinite canvas with node-based workflow
- Text, Image, Movie, Audio, Document and Paint nodes
- Backdrops and Sticky Notes for organisation
- Dark and Light themes, fully customisable
- Connect, group and visualise ideas in one place

## Download

Visit the [Download page](https://theFlowAppX.github.io/theFlow) or go to [Releases](https://github.com/theFlowAppX/theFlow/releases) to download the latest version for your platform.

| Platform | File |
|----------|------|
| macOS    | `theFlow-x.x.x.dmg` |
| Windows  | `theFlow-x.x.x.exe` |
| Linux (RPM) | `theFlow-x.x.x.rpm` |
| Linux (DEB) | `theFlow-x.x.x.deb` |

## Project Structure

```
theFlow/
├── src/                    ← Python source files
│   ├── main.py
│   ├── main_linux.py
│   ├── view_logic.py
│   ├── scene_logic.py
│   ├── node.py
│   ├── note.py
│   ├── backdrop.py
│   ├── paint.py
│   ├── curve.py
│   ├── menu.py
│   ├── ui_components.py
│   ├── settings.py
│   ├── config.py
│   ├── utils.py
│   └── logo.py
├── build/
│   ├── mac/                ← macOS build scripts
│   ├── win/                ← Windows build scripts
│   ├── linux-rpm/          ← Linux RPM build scripts
│   └── linux-deb/          ← Linux DEB build scripts
├── logo/                   ← App logo SVG
├── documentation/          ← User manual
└── README.md
```

## Building from Source

### Requirements
- Python 3.10+
- PyQt6
- PyInstaller

### macOS
```bash
cd build/mac
chmod +x build_mac.sh
./build_mac.sh
```

### Windows
```bash
cd build/win
pyinstaller theflow_win.spec
```

### Linux RPM
```bash
cd build/linux-rpm
chmod +x build_rpm.sh
./build_rpm.sh
```

### Linux DEB
```bash
cd build/linux-deb
chmod +x build_deb.sh
./build_deb.sh
```

## License

GPLv3 — see [LICENSE](LICENSE)

## Contact

theflowapp@protonmail.com

## Author

Xavier Garès © 2026
