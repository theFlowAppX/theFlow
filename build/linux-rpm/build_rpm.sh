#!/bin/bash
# =========================================================
# build_rpm.sh — Install deps + build theFlow! RPM
# Run from the project root:
#   chmod +x build_rpm.sh
#   ./build_rpm.sh
# =========================================================

set -e

VERSION="0.1.0"
NAME="theflow"
PROJECT_DIR=$(pwd)

echo "=== theFlow! RPM Builder ==="
echo ""

# ── 1. Install system packages if needed ──────────────────
echo "--- Checking system packages ---"
PKGS=""
for pkg in python3 python3-devel python3-pip rpm-build rpmdevtools libGL; do
    if ! rpm -q "$pkg" &>/dev/null; then
        PKGS="$PKGS $pkg"
    fi
done
if [ -n "$PKGS" ]; then
    echo "Installing:$PKGS"
    sudo dnf install -y $PKGS
    echo "✅  System packages installed."
else
    echo "✅  System packages already installed."
fi

# ── 2. Install Python packages if needed ──────────────────
echo ""
echo "--- Checking Python packages ---"
export PATH=$HOME/.local/bin:$PATH

# Force reinstall if PyQt6 version is wrong
PYQT_VER=$(python3 -c "import PyQt6.QtCore; print(PyQt6.QtCore.PYQT_VERSION_STR)" 2>/dev/null || echo "none")
if ! python3 -m PyInstaller --version &>/dev/null || [ "$PYQT_VER" != "6.4.2" ]; then
    echo "Installing Python packages (PyQt6 6.4.2 required)..."
    python3 -m pip install --upgrade pip
    python3 -m pip install \
        pyinstaller \
        "PyQt6==6.4.2" \
        "PyQt6-Qt6==6.4.2" \
        "PyQt6-sip>=13.4" \
        Pillow
    echo "✅  Python packages installed."
else
    echo "✅  Python packages already installed."
fi

# ── 3. Set up RPM build tree ──────────────────────────────
echo ""
echo "--- Setting up RPM build tree ---"
mkdir -p ~/rpmbuild/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
echo "✅  ~/rpmbuild tree ready."

# ── 4. Build PyInstaller binary ───────────────────────────
echo ""
echo "=== Step 1: Build PyInstaller binary ==="
python3 -m PyInstaller theflow_linux.spec

# ── 5. Package binary into tarball ────────────────────────
echo ""
echo "=== Step 2: Package binary into tarball ==="
tar -czf ~/rpmbuild/SOURCES/${NAME}-${VERSION}.tar.gz \
    -C dist ${NAME}

# ── 6. Copy icon, desktop file and manual ─────────────────
echo ""
echo "=== Step 3: Copy assets ==="
cp icons/icon.png                       ~/rpmbuild/SOURCES/icon.png
cp theflow.desktop                      ~/rpmbuild/SOURCES/theflow.desktop
cp documentation/theFlow_manual.html   ~/rpmbuild/SOURCES/theFlow_manual.html
cp theflow-mime.xml                     ~/rpmbuild/SOURCES/theflow-mime.xml
echo "✅  Assets copied."

# ── 7. Copy RPM spec ──────────────────────────────────────
echo ""
echo "=== Step 4: Copy RPM spec ==="
cp -f theflow.spec ~/rpmbuild/SPECS/theflow.spec
echo "✅  Spec copied."

# ── 8. Build RPM ──────────────────────────────────────────
echo ""
echo "=== Step 5: Build RPM ==="
rpmbuild -bb ~/rpmbuild/SPECS/theflow.spec

# ── 9. Move RPM to dist/ ──────────────────────────────────
echo ""
echo "=== Step 6: Move RPM to dist/ ==="
mkdir -p ${PROJECT_DIR}/dist
find ~/rpmbuild/RPMS -name "*.rpm" | while read f; do
    cp "$f" ${PROJECT_DIR}/dist/
    echo "  Copied: $(basename $f) -> dist/"
done

echo ""
echo "=== Done! ==="
echo "  Binary:  ${PROJECT_DIR}/dist/${NAME}"
echo "  Package: ${PROJECT_DIR}/dist/${NAME}-${VERSION}-1.*.rpm"
