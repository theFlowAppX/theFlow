#!/bin/bash
# =========================================================
# build_appimage.sh — Build theFlow! AppImage
# Works on any Linux x86_64 (Ubuntu, Fedora, Arch, etc.)
# Run from the project root:
#   chmod +x build_appimage.sh
#   ./build_appimage.sh
# =========================================================

set -e

VERSION="0.1.0"
NAME="theflow"
APP_DIR="theFlow.AppDir"
PROJECT_DIR=$(pwd)

echo "=== theFlow! AppImage Builder ==="
echo ""

# ── 1. Install system packages if needed ──────────────────
echo "--- Checking system packages ---"
if command -v apt-get &>/dev/null; then
    PKG_MGR="apt-get"
    sudo apt-get update -q
    sudo apt-get install -y python3 python3-pip python3-venv libgl1 libglib2.0-0 fuse
elif command -v dnf &>/dev/null; then
    PKG_MGR="dnf"
    sudo dnf install -y python3 python3-pip libGL fuse fuse-libs
else
    echo "⚠️  Unknown package manager — skipping system package install"
fi
echo "✅  System packages ready."

# ── 2. Install Python packages if needed ──────────────────
echo ""
echo "--- Checking Python packages ---"
export PATH=$HOME/.local/bin:$PATH

if ! python3 -m PyInstaller --version &>/dev/null; then
    echo "Installing Python packages..."
    python3 -m pip install --upgrade pip
    python3 -m pip install \
        pyinstaller \
        "PyQt6==6.4.2" \
        "PyQt6-Qt6==6.4.2" \
        "PyQt6-sip>=13.4" \
        Pillow
    echo "✅  Python packages installed."
else
    PYQT_VER=$(python3 -c "import PyQt6.QtCore; print(PyQt6.QtCore.PYQT_VERSION_STR)" 2>/dev/null || echo "none")
    if [ "$PYQT_VER" != "6.4.2" ]; then
        echo "Wrong PyQt6 version ($PYQT_VER) — reinstalling 6.4.2..."
        python3 -m pip install "PyQt6==6.4.2" "PyQt6-Qt6==6.4.2" "PyQt6-sip>=13.4" --force-reinstall
    else
        echo "✅  Python packages already installed."
    fi
fi

# ── 3. Download appimagetool if needed ────────────────────
echo ""
echo "--- Checking appimagetool ---"
APPIMAGETOOL="$PROJECT_DIR/appimagetool-x86_64.AppImage"
if [ ! -f "$APPIMAGETOOL" ]; then
    echo "Downloading appimagetool..."
    curl -L -o "$APPIMAGETOOL" \
        "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$APPIMAGETOOL"
    echo "✅  appimagetool downloaded."
else
    echo "✅  appimagetool already present."
fi

# ── 4. Build PyInstaller binary ───────────────────────────
echo ""
echo "=== Step 1: Build PyInstaller binary ==="
python3 -m PyInstaller theflow_linux.spec
echo "✅  Binary built: dist/${NAME}"

# ── 5. Create AppDir structure ────────────────────────────
echo ""
echo "=== Step 2: Create AppDir structure ==="
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/usr/bin"
mkdir -p "$APP_DIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$APP_DIR/usr/share/applications"

# Copy binary
cp dist/${NAME} "$APP_DIR/usr/bin/${NAME}"
chmod 755 "$APP_DIR/usr/bin/${NAME}"

# Bundle ffmpeg for pydub audio waveform support
if command -v ffmpeg &>/dev/null; then
    cp "$(which ffmpeg)" "$APP_DIR/usr/bin/ffmpeg"
    chmod 755 "$APP_DIR/usr/bin/ffmpeg"
    echo "✅  ffmpeg bundled."
fi

# Copy icon
if [ -f "icons/icon.png" ]; then
    cp icons/icon.png "$APP_DIR/usr/share/icons/hicolor/256x256/apps/${NAME}.png"
    cp icons/icon.png "$APP_DIR/${NAME}.png"
else
    ICON=$(find icons/ -name "*.png" | head -1)
    [ -n "$ICON" ] && cp "$ICON" "$APP_DIR/usr/share/icons/hicolor/256x256/apps/${NAME}.png"
    [ -n "$ICON" ] && cp "$ICON" "$APP_DIR/${NAME}.png"
fi

# Desktop file
cat > "$APP_DIR/${NAME}.desktop" << DESKTOP
[Desktop Entry]
Name=theFlow!
GenericName=Visual Canvas
Comment=Visual node-based canvas for creative workflows
Exec=theflow %f
Icon=theflow
Terminal=false
Type=Application
Categories=Graphics;Office;Education;
Keywords=canvas;nodes;flow;visual;creative;
StartupWMClass=theflow
MimeType=application/x-theflow;
DESKTOP

cp "$APP_DIR/${NAME}.desktop" "$APP_DIR/usr/share/applications/${NAME}.desktop"

# AppRun entrypoint
cat > "$APP_DIR/AppRun" << 'APPRUN'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=$(dirname "$SELF")
export PATH="$HERE/usr/bin:$PATH"
export LD_LIBRARY_PATH="$HERE/usr/lib:$LD_LIBRARY_PATH"
exec "$HERE/usr/bin/theflow" "$@"
APPRUN
chmod +x "$APP_DIR/AppRun"

echo "✅  AppDir structure created."

# ── 6. Build AppImage ─────────────────────────────────────
echo ""
echo "=== Step 3: Build AppImage ==="
mkdir -p dist
ARCH=x86_64 "$APPIMAGETOOL" "$APP_DIR" "dist/theFlow-${VERSION}-x86_64.AppImage"
chmod +x "dist/theFlow-${VERSION}-x86_64.AppImage"

# ── 7. Clean up AppDir ────────────────────────────────────
rm -rf "$APP_DIR"

echo ""
echo "=== Done! ==="
echo "  AppImage: ${PROJECT_DIR}/dist/theFlow-${VERSION}-x86_64.AppImage"
echo ""
echo "To run:"
echo "  chmod +x dist/theFlow-${VERSION}-x86_64.AppImage"
echo "  ./dist/theFlow-${VERSION}-x86_64.AppImage"
