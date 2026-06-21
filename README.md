# theFlow!

**Visual node-based canvas for organising ideas, media and information.**

theFlow! is a free, open source desktop application that lets you place images, videos, audio, documents, and notes on an infinite canvas and connect them the way your mind naturally works.

![License](https://img.shields.io/badge/license-GPLv3-blue)
![Version](https://img.shields.io/badge/version-0.1.0-green)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)

---

## Download

Visit **[www.theflowapp.org](https://www.theflowapp.org)** to download the latest release for your platform.

| Platform | Format |
|---|---|
| macOS | `.app` + `.dmg` |
| Windows | `.exe` + installer |
| Linux Ubuntu/Debian | `.deb` |
| Linux Fedora/RHEL | `.rpm` |
| Linux AppImage | `.AppImage` (portable, any distro) |

---

## Features

- Infinite freeform canvas with smooth zoom and pan
- 7 node types: Text, Image, Movie, Audio, Document, Paint, Dot
- Inline media viewers — video player, audio waveform, PDF viewer
- Bézier connection curves between nodes
- Backdrop grouping with child pinning
- Canvas freehand annotation
- Full undo/redo, copy/paste, import/export
- Light and dark themes
- `.flow` file format — JSON, human-readable
- File association — double-click `.flow` files to open directly

---

## Repository Structure

```
theFlow/
├── build/
│   ├── mac/          ← macOS build scripts and source
│   ├── win/          ← Windows build scripts and source
│   ├── linux-deb/    ← Linux DEB build scripts and source
│   ├── linux-rpm/    ← Linux RPM build scripts and source
│   └── linux-appimage/ ← Linux AppImage build scripts and source
├── .gitignore
└── README.md
```

---

## Building from Source

Each platform folder contains everything needed to build theFlow! for that platform.

**macOS**
```bash
cd build/mac
chmod +x build_mac.sh
./build_mac.sh
```

**Windows**
```
cd build\win
build_windows.bat
```

**Linux DEB**
```bash
cd build/linux-deb
chmod +x setup_ubuntu.sh && ./setup_ubuntu.sh   # first time only
./build_deb.sh
```

**Linux RPM**
```bash
cd build/linux-rpm
chmod +x build_rpm.sh
./build_rpm.sh
```

**Linux AppImage**
```bash
cd build/linux-appimage
chmod +x build_appimage.sh
./build_appimage.sh
```

---

## Privacy

theFlow! collects no data of any kind.

- No telemetry, no analytics, no crash reporting
- No network requests are made by the application
- No user accounts, no login, no cloud sync
- All files are stored locally on your machine in the `.flow` format
- Settings are saved locally (`~/.config/theflow/` on Linux, next to the app on macOS and Windows)
- The only network activity is the Web Node, and only when you explicitly set a URL — it never runs automatically

theFlow! has no visibility into how you use it, what you store, or who you are.

---

## License

theFlow! is free and open source software released under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html).

---

## Links

- 🌐 [www.theflowapp.org](https://www.theflowapp.org)
- 🎥 [YouTube](https://www.youtube.com/@theFlowapplication)
- 📧 theflow!@protonmail.com
