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

## Security

All binaries are scanned and verified. Independent analysis reports:

| Binary | Report |
|---|---|
| macOS `.dmg` | [Hybrid Analysis](https://hybrid-analysis.com/sample/e7a8a960fbc8f3a1efe846a5a745984ea087d6e604a03f2776caf1ff7b14e797) |
| Windows `.exe` | [Hybrid Analysis](https://hybrid-analysis.com/sample/0ef820d434dbbe89555eb19eda70abafa02cb0b8e313274249fb13944979239b) |
| Linux `.deb` | [Hybrid Analysis](https://hybrid-analysis.com/sample/32c8af3ce6575a37f72c90406df188954b439d963656195b543d2a751ec2af39) |
| Linux `.rpm` | [Hybrid Analysis](https://hybrid-analysis.com/sample/e0e7a8f3e97c99756f54f77d4f2b5636919f031368551138adeef4a25252db24) |
| Linux `.AppImage` | [Hybrid Analysis](https://hybrid-analysis.com/sample/22e62dc78d5e5063076a566242b9e221a664f87c076e17b78b803cd4049f7d5d/6a340978efc7c344180f9007) |

Any flags from obscure AV engines are false positives typical of PyInstaller-built binaries. Major engines (Bitdefender, Sophos, ESET, SentinelOne, ClamAV, Avira, Emsisoft) all return clean.

---

## License

theFlow! is free and open source software released under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html).

---

## Links

- 🌐 [www.theflowapp.org](https://www.theflowapp.org)
- 🎥 [YouTube](https://www.youtube.com/@theFlowapplication)
- 📧 theflow!@protonmail.com
