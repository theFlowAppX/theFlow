# theflow.spec
# =========================================================
# PyInstaller spec file for theFlow! — Windows 64-bit
# =========================================================
# Run with:   python -m PyInstaller theflow.spec
# Output:     dist\theFlow.exe   (single-file executable)
# =========================================================

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# ── Collect all PyQt6 multimedia plugin data ──────────────
pyqt6_datas = collect_data_files('PyQt6', includes=['Qt6/plugins/**'])

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('logo/logo.svg',                    'logo'),
        ('logo/theFlow!.svg',               'logo'),
        ('logo/Fet_a_Horta.svg',            'logo'),
        ('logo/theFlow_white.svg',          'logo'),
        # NOTE: logo/F!.png must live next to theFlow.exe (not inside _MEIPASS)
        # so InlineDocViewer can find it via sys.executable at runtime.
        # It is copied by the post_build() step at the bottom of this file.
        ('settings',                         'settings'),
        ('documentation/theFlow_manual.html','documentation'),
        *pyqt6_datas,
    ],
    hiddenimports=[
        'PyQt6.QtMultimedia',
        'PyQt6.QtMultimediaWidgets',
        'PyQt6.QtSvg',
        'PyQt6.QtSvgWidgets',
        'PyQt6.QtPdf',
        'PyQt6.QtPdfWidgets',
        'PyQt6.QtNetwork',
        'PyQt6.QtOpenGL',
        'PyQt6.QtPrintSupport',
        'mimetypes',
        'struct',
        'colorsys',
        'wave',
        'math',
        'platform',
        'subprocess',
        'traceback',
        'contextlib',
        'pathlib',
        'shutil',
        'threading',
        'tempfile',
        'config',
        'settings',
        'utils',
        'node',
        'note',
        'curve',
        'backdrop',
        'paint',
        'paint_on_canvas',
        'logo',
        'menu',
        'scene_logic',
        'view_logic',
        'ui_components',
        'web',
        'pdf',
        'group',
        'reference',
        'playwright',
        'playwright.sync_api',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['rthook_theflow.py'],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'PIL',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='theFlow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icons\\logo.ico',
    version='version_info.txt',
)

# =========================================================
# POST-BUILD: copy logo/F!.png next to theFlow.exe
# =========================================================
import shutil, os as _os

def post_build():
    src = _os.path.join('logo', 'F!.png')
    dst_dir = _os.path.join('dist', 'logo')
    dst = _os.path.join(dst_dir, 'F!.png')
    if not _os.path.isfile(src):
        print(f'\n[post_build] WARNING: {src} not found — skipping copy.\n')
        return
    _os.makedirs(dst_dir, exist_ok=True)
    shutil.copy2(src, dst)
    print(f'\n[post_build] Copied {src}  ->  {dst}\n')

post_build()
