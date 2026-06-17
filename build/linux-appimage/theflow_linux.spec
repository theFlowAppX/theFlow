# theflow_linux.spec
# =========================================================
# PyInstaller spec file for theFlow! — Linux x86_64
# =========================================================
# Run with:   pyinstaller theflow_linux.spec
# Output:     dist/theflow   (single-file binary)
# =========================================================

from PyInstaller.utils.hooks import collect_data_files
import glob, os

block_cipher = None

pyqt6_datas = collect_data_files('PyQt6', includes=['Qt6/plugins/**'])

# ── Optional folders ───────────────────────────────────────────────
_extra_datas = []
if os.path.isdir('icons'):
    _extra_datas.append(('icons', 'icons'))

# ── FFmpeg libs bundled inside PyQt6 ──────────────────────────────
# PyInstaller doesn't auto-collect these — we must add them explicitly
# so QMediaPlayer can decode audio/video in the frozen binary.
_pyqt6_lib = os.path.join(
    os.path.expanduser('~'),
    '.local/lib/python3.9/site-packages/PyQt6/Qt6/lib'
)
_ffmpeg_libs = []
for _pattern in ('libavcodec.so*', 'libavformat.so*', 'libavutil.so*',
                 'libswresample.so*', 'libswscale.so*'):
    for _f in glob.glob(os.path.join(_pyqt6_lib, _pattern)):
        _ffmpeg_libs.append((_f, 'PyQt6/Qt6/lib'))

# ── FFmpeg multimedia plugin ───────────────────────────────────────
_mm_plugin = os.path.join(
    os.path.expanduser('~'),
    '.local/lib/python3.9/site-packages/PyQt6/Qt6/plugins/multimedia/libffmpegmediaplugin.so'
)
if os.path.isfile(_mm_plugin):
    _ffmpeg_libs.append((_mm_plugin, 'PyQt6/Qt6/plugins/multimedia'))

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=_ffmpeg_libs,
    datas=[
        ('logo',                               'logo'),
        ('settings',                           'settings'),
        ('documentation/theFlow_manual.html',  'documentation'),
        *_extra_datas,
        *pyqt6_datas,
    ],
    hiddenimports=[
        'PyQt6.QtMultimedia',
        'PyQt6.QtMultimediaWidgets',
        'PyQt6.QtSvg',
        'PyQt6.QtSvgWidgets',
        'mimetypes',
        'struct',
        'colorsys',
        'paint_on_canvas',
        'pydub',
    ],
    hookspath=[],
    runtime_hooks=['rthook.py'],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'PIL',
    ],
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
    name='theflow',        # lowercase — Linux convention
    debug=False,
    strip=False,           # DO NOT strip — breaks FFmpeg .so alignment
    upx=False,             # DO NOT compress — UPX corrupts FFmpeg libs on Linux
    upx_exclude=[],
    console=False,         # no terminal window
    target_arch=None,
)
