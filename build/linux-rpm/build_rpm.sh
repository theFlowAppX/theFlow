#!/bin/bash
# =========================================================
# build_rpm.sh — builds theFlow! RPM from PyInstaller binary
# Run from the project root:  bash build_rpm.sh
# =========================================================
set -e

VERSION="0.1.0"
NAME="theflow"
PROJECT_DIR=$(pwd)

echo "=== Step 1: Build PyInstaller binary ==="
pyinstaller theflow_linux.spec

echo ""
echo "=== Step 2: Set up RPM build tree ==="
mkdir -p ~/rpmbuild/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}

echo ""
echo "=== Step 3: Package binary into tarball ==="
tar -czf ~/rpmbuild/SOURCES/${NAME}-${VERSION}.tar.gz \
    -C dist ${NAME}

echo ""
echo "=== Step 4: Copy icon and desktop file ==="
cp icons/icon.png          ~/rpmbuild/SOURCES/icon.png
cp theflow.desktop         ~/rpmbuild/SOURCES/theflow.desktop
cp documentation/theFlow_manual.html ~/rpmbuild/SOURCES/theFlow_manual.html

echo ""
echo "=== Step 5: Copy RPM spec ==="
cp theflow.spec ~/rpmbuild/SPECS/theflow.spec

echo ""
echo "=== Step 6: Build RPM ==="
rpmbuild -bb ~/rpmbuild/SPECS/theflow.spec

echo ""
echo "=== Step 7: Move RPM to dist/ ==="
mkdir -p ${PROJECT_DIR}/dist
find ~/rpmbuild/RPMS -name "*.rpm" | while read f; do
    cp "$f" ${PROJECT_DIR}/dist/
    echo "  Copied: $(basename $f) -> dist/"
done

echo ""
echo "=== Done! ==="
echo "  Binary:  ${PROJECT_DIR}/dist/${NAME}"
echo "  Package: ${PROJECT_DIR}/dist/${NAME}-${VERSION}-1.*.rpm"
