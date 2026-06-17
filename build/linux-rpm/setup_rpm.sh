#!/bin/bash
# =========================================================
# setup_rpm.sh — Install all dependencies for theFlow! RPM build
# Run once on a fresh Fedora/RHEL/CentOS system:
#   chmod +x setup_rpm.sh
#   ./setup_rpm.sh
# =========================================================

set -e

echo "=== theFlow! RPM Build Dependency Setup ==="
echo ""

# ── 1. System packages ────────────────────────────────────
echo "--- Installing system packages ---"
sudo dnf install -y \
    python3 \
    python3-devel \
    python3-pip \
    rpm-build \
    rpmdevtools \
    libGL \
    libglib2.0 \
    dbus-libs \
    gcc \
    make
echo "✅  System packages installed."

# ── 2. Python packages ────────────────────────────────────
echo ""
echo "--- Installing Python packages ---"
python3 -m pip install --upgrade pip
python3 -m pip install \
    pyinstaller \
    "PyQt6==6.4.2" \
    "PyQt6-Qt6==6.4.2" \
    "PyQt6-sip>=13.4" \
    Pillow \
    playwright
echo "✅  Python packages installed."

# ── 3. Playwright Chromium ────────────────────────────────
echo ""
echo "--- Installing Playwright Chromium (for Web Node) ---"
python3 -m playwright install chromium
python3 -m playwright install-deps chromium
echo "✅  Playwright Chromium installed."

# ── 4. Set up RPM build tree ──────────────────────────────
echo ""
echo "--- Setting up RPM build tree ---"
rpmdev-setuptree
echo "✅  ~/rpmbuild tree created."

# ── 5. Add local bin to PATH ──────────────────────────────
echo ""
echo "--- Adding ~/.local/bin to PATH ---"
if ! grep -q 'HOME/.local/bin' ~/.bashrc; then
    echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.bashrc
    echo "✅  Added to ~/.bashrc"
else
    echo "✅  Already in ~/.bashrc"
fi
export PATH=$HOME/.local/bin:$PATH

# ── 6. Verify ─────────────────────────────────────────────
echo ""
echo "--- Verifying ---"
echo -n "Python:      "; python3 --version
echo -n "PyInstaller: "; python3 -m PyInstaller --version
echo -n "PyQt6:       "; python3 -c "import PyQt6.QtCore; print(PyQt6.QtCore.PYQT_VERSION_STR)"
echo -n "rpmbuild:    "; rpmbuild --version

echo ""
echo "=== All done! ==="
echo ""
echo "To build theFlow:"
echo "  chmod +x build_rpm.sh"
echo "  ./build_rpm.sh"
