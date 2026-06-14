#!/bin/bash
# =========================================================
# build_deb.sh — builds theFlow! .deb from PyInstaller binary
# Run from the project root:  bash build_deb.sh
# =========================================================
set -e

VERSION="0.1.0"
NAME="theflow"
ARCH="amd64"
PKG="${NAME}_${VERSION}_${ARCH}"
PROJECT_DIR=$(pwd)

echo "=== Step 1: Build PyInstaller binary ==="
export PATH=$HOME/.local/bin:$PATH
python3.9 -m PyInstaller theflow.spec

echo ""
echo "=== Step 2: Create .deb folder structure ==="
rm -rf /tmp/${PKG}
mkdir -p /tmp/${PKG}/DEBIAN
mkdir -p /tmp/${PKG}/usr/bin
mkdir -p /tmp/${PKG}/usr/share/applications
mkdir -p /tmp/${PKG}/usr/share/icons/hicolor/256x256/apps
mkdir -p /tmp/${PKG}/usr/share/doc/${NAME}
mkdir -p /tmp/${PKG}/usr/share/mime/packages

echo ""
echo "=== Step 3: Copy files ==="
cp dist/${NAME}                          /tmp/${PKG}/usr/bin/${NAME}
chmod 755                                /tmp/${PKG}/usr/bin/${NAME}

# Icon — try icon.png, fall back to any png in icons/
if [ -f "icons/icon.png" ]; then
    cp icons/icon.png /tmp/${PKG}/usr/share/icons/hicolor/256x256/apps/${NAME}.png
else
    ICON=$(find icons/ -name "*.png" | head -1)
    if [ -n "$ICON" ]; then
        cp "$ICON" /tmp/${PKG}/usr/share/icons/hicolor/256x256/apps/${NAME}.png
        echo "⚠️  icons/icon.png not found, used $ICON instead"
    else
        echo "⚠️  No icon found in icons/ — skipping icon"
    fi
fi

# Desktop file
if [ -f "theflow.desktop" ]; then
    cp theflow.desktop /tmp/${PKG}/usr/share/applications/${NAME}.desktop
else
    echo "⚠️  theflow.desktop not found — skipping"
fi

# MIME type
if [ -f "theflow-mime.xml" ]; then
    cp theflow-mime.xml /tmp/${PKG}/usr/share/mime/packages/${NAME}.xml
else
    echo "⚠️  theflow-mime.xml not found — skipping"
fi

cp documentation/theFlow_manual.html /tmp/${PKG}/usr/share/doc/${NAME}/theFlow_manual.html

echo ""
echo "=== Step 4: Write control file ==="
cat > /tmp/${PKG}/DEBIAN/control << CTRL
Package: theflow
Version: ${VERSION}
Architecture: amd64
Maintainer: Xavier Gares <theflow!@protonmail.com>
Description: theFlow! — Visual node-based canvas application
 Visual canvas for organising images, video, audio,
 documents and notes in a freeform flow graph.
 Built with PyQt6, self-contained binary.
Section: graphics
Priority: optional
CTRL

echo ""
echo "=== Step 5: Write postinst script ==="
cat > /tmp/${PKG}/DEBIAN/postinst << POST
#!/bin/bash
update-desktop-database &>/dev/null || true
update-mime-database /usr/share/mime &>/dev/null || true
gtk-update-icon-cache -f -t /usr/share/icons/hicolor &>/dev/null || true
POST
chmod 755 /tmp/${PKG}/DEBIAN/postinst

echo ""
echo "=== Step 6: Build .deb ==="
dpkg-deb --build /tmp/${PKG} ${PROJECT_DIR}/${PKG}.deb

echo ""
echo "=== Step 7: Move .deb to dist/ ==="
mkdir -p ${PROJECT_DIR}/dist
mv ${PROJECT_DIR}/${PKG}.deb ${PROJECT_DIR}/dist/${PKG}.deb

echo ""
echo "=== Done! ==="
echo "  Binary:  ${PROJECT_DIR}/dist/${NAME}"
echo "  Package: ${PROJECT_DIR}/dist/${PKG}.deb"
echo ""
echo "To install:"
echo "  sudo dpkg -i dist/${PKG}.deb"
