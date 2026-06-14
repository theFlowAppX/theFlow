# theflow.spec
# =========================================================
# PyInstaller spec file for theFlow! macOS .app bundle
# =========================================================
#
# Usage:
#   pyinstaller theflow.spec --clean
#
# Output: dist/theFlow.app
# =========================================================

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

added_files = [
    ("logo",          "logo"),
    ("documentation", "documentation"),
    ("icons",         "icons"),
    ("settings",      "settings"),   # FIXED: was commented out — needed at runtime
]

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        # PyQt6 — sip must be explicit or the ABI layer fails silently
        "PyQt6.sip",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.QtSvg",
        "PyQt6.QtSvgWidgets",
        "PyQt6.QtMultimedia",
        "PyQt6.QtMultimediaWidgets",
        "PyQt6.QtOpenGL",
        "PyQt6.QtPrintSupport",
        "PyQt6.QtNetwork",
        "PyQt6.QtPdf",
        "PyQt6.QtPdfWidgets",
        # stdlib modules used at paint/event time — missing any one
        # of these causes a NameError inside a virtual override → abort()
        "colorsys",
        "wave",
        "struct",
        "math",
        "mimetypes",
        "platform",
        "subprocess",
        "traceback",
        "contextlib",
        "pathlib",
        "shutil",
        # App modules
        "backdrop",
        "config",
        "curve",
        "logo",
        "menu",
        "node",
        "note",
        "paint",
        "paint_on_canvas",
        "scene_logic",
        "settings",
        "ui_components",
        "utils",
        "view_logic",
        "hook_fix_cfbundle",
    ],
    hookspath=[],
    hooksconfig={},
    # FIXED: runtime hook installs Qt message handler that prevents
    # abort() when a Python exception escapes a paint/event method.
    runtime_hooks=["hook_fix_cfbundle.py"],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="theFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="theFlow",
)

app = BUNDLE(
    coll,
    name="theFlow.app",
    icon="icons/icon.icns",
    bundle_identifier="com.xaviergares.theflow",
    info_plist={
        "CFBundleName":               "theFlow",
        "CFBundleDisplayName":        "theFlow!",
        "CFBundleVersion":            "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
        "NSHighResolutionCapable":    True,
        "NSRequiresAquaSystemAppearance": False,
        "LSUIElement":                False,
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName":       "theFlow Document",
                "CFBundleTypeRole":       "Editor",
                "CFBundleTypeExtensions": ["flow"],
                "CFBundleTypeIconFile":   "icon.icns",
                "LSHandlerRank":          "Owner",
                "LSItemContentTypes":     ["com.xaviergares.theflow.document"],
            }
        ],
        "UTExportedTypeDeclarations": [
            {
                "UTTypeIdentifier":       "com.xaviergares.theflow.document",
                "UTTypeDescription":      "theFlow Document",
                "UTTypeConformsTo":       ["public.data"],
                "UTTypeTagSpecification": {"public.filename-extension": ["flow"]},
                "UTTypeIconFile":         "icon.icns",
            }
        ],
    },
)
