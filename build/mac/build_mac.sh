#!/bin/bash
# =========================================================
# build_mac.sh  —  Build theFlow! macOS .app bundle + DMG
# =========================================================
# Run from your project root:
#   chmod +x build_mac.sh
#   ./build_mac.sh
# =========================================================

set -e   # stop on any error

APP_NAME="theFlow"
VERSION="0.1.0"
DMG="dist/${APP_NAME}-${VERSION}.dmg"
APP="dist/${APP_NAME}.app"
STAGED="dist/dmg_stage"
VENV=".venv_build"

echo "=== theFlow! macOS Builder ==="
echo ""

# ── 1. Find Python 3.12 ───────────────────────────────────
if   [ -x "/opt/homebrew/opt/python@3.12/bin/python3" ]; then
    BASE_PYTHON="/opt/homebrew/opt/python@3.12/bin/python3"
elif [ -x "/usr/local/opt/python@3.12/bin/python3" ]; then
    BASE_PYTHON="/usr/local/opt/python@3.12/bin/python3"
elif [ -x "/opt/homebrew/bin/python3.12" ]; then
    BASE_PYTHON="/opt/homebrew/bin/python3.12"
elif [ -x "/usr/local/bin/python3.12" ]; then
    BASE_PYTHON="/usr/local/bin/python3.12"
elif command -v python3.12 &>/dev/null; then
    BASE_PYTHON="python3.12"
else
    echo "❌  Python 3.12 not found. Install it with:"
    echo "      brew install python@3.12"
    exit 1
fi

echo "✅  Found Python: $BASE_PYTHON ($($BASE_PYTHON --version))"

# ── 2. Create / reuse a build virtual environment ─────────
echo ""
echo "--- Setting up build virtual environment ($VENV) ---"
if [ ! -d "$VENV" ]; then
    $BASE_PYTHON -m venv "$VENV"
    echo "✅  Virtual environment created."
else
    echo "✅  Reusing existing virtual environment."
fi

# All further commands use the venv's Python & pip
PYTHON="$VENV/bin/python"
PIP="$VENV/bin/pip"

# ── 3. Install build deps inside the venv ─────────────────
echo ""
echo "--- Installing dependencies into venv ---"
$PIP install --upgrade pip
$PIP install --upgrade pyinstaller
$PIP install --upgrade "PyQt6" "PyQt6-Qt6" "PyQt6-sip"
echo "✅  Dependencies installed."

# ── 4. Convert icons/icon.png → icons/icon.icns ───────────
echo ""
echo "--- Converting icon.png to icon.icns ---"
PNG="icons/icon.png"
ICNS="icons/icon.icns"
ICONSET="icon.iconset"

if [ ! -f "$PNG" ]; then
    echo "⚠️  $PNG not found — skipping icon conversion."
else
    rm -rf "$ICONSET"
    mkdir "$ICONSET"
    sips -z 16   16   "$PNG" --out "$ICONSET/icon_16x16.png"      &>/dev/null
    sips -z 32   32   "$PNG" --out "$ICONSET/icon_16x16@2x.png"   &>/dev/null
    sips -z 32   32   "$PNG" --out "$ICONSET/icon_32x32.png"       &>/dev/null
    sips -z 64   64   "$PNG" --out "$ICONSET/icon_32x32@2x.png"   &>/dev/null
    sips -z 128  128  "$PNG" --out "$ICONSET/icon_128x128.png"     &>/dev/null
    sips -z 256  256  "$PNG" --out "$ICONSET/icon_128x128@2x.png" &>/dev/null
    sips -z 256  256  "$PNG" --out "$ICONSET/icon_256x256.png"     &>/dev/null
    sips -z 512  512  "$PNG" --out "$ICONSET/icon_256x256@2x.png" &>/dev/null
    sips -z 512  512  "$PNG" --out "$ICONSET/icon_512x512.png"     &>/dev/null
    sips -z 1024 1024 "$PNG" --out "$ICONSET/icon_512x512@2x.png" &>/dev/null
    iconutil -c icns "$ICONSET" -o "$ICNS"
    rm -rf "$ICONSET"
    echo "✅  Created $ICNS"
fi

# ── 5. Clean previous builds ──────────────────────────────
echo ""
echo "--- Cleaning previous build artefacts ---"
rm -rf build dist __pycache__
find . -name "*.pyc" -delete 2>/dev/null || true

# ── 6. Run PyInstaller from inside the venv ───────────────
echo ""
echo "--- Running PyInstaller ---"
$PYTHON -m PyInstaller theflow_mac.spec

# ── 7. Verify .app ────────────────────────────────────────
if [ ! -d "$APP" ]; then
    echo ""
    echo "❌  Build failed — check output above for errors."
    exit 1
fi
echo ""
echo "✅  Build succeeded: $APP"

# ── 8. Copy icon.icns into bundle Resources ───────────────
echo ""
echo "--- Copying icon.icns into bundle Resources ---"
RESOURCES="$APP/Contents/Resources"
if [ -f "$ICNS" ]; then
    cp "$ICNS" "$RESOURCES/icon.icns"
    echo "✅  Copied icon.icns to bundle Resources"
else
    echo "⚠️  icon.icns not found — document icon may not show"
fi

# ── 9. Ad-hoc code signing ────────────────────────────────
echo ""
echo "--- Ad-hoc code signing ---"
codesign --force --deep --sign - "$APP" && \
    echo "✅  Signed successfully." || \
    echo "⚠️  Signing failed — app may still run locally."

echo ""
echo "--- Creating DMG ---"
rm -f "$DMG"
rm -rf "$STAGED"
mkdir -p "$STAGED"
cp -R "$APP" "$STAGED/"

# Symlink to /Applications so the user can drag-install
ln -s /Applications "$STAGED/Applications"

hdiutil create \
    -volname "$APP_NAME" \
    -srcfolder "$STAGED" \
    -ov \
    -format UDZO \
    "$DMG" && \
    echo "✅  DMG created: $DMG" || \
    echo "⚠️  DMG creation failed — .app is still at $APP"

rm -rf "$STAGED"

echo ""
echo "Done."
echo ""
echo "Deliverables:"
echo "  App : $APP"
echo "  DMG : $DMG"
