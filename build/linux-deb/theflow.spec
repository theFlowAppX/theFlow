# theflow.spec
# =========================================================
# PyInstaller spec file for theFlow!
# =========================================================
# Run with:   python3.9 -m PyInstaller theflow.spec
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
import PyQt6 as _pyqt6_mod
_pyqt6_lib = os.path.join(os.path.dirname(_pyqt6_mod.__file__), 'Qt6', 'lib')
_ffmpeg_libs = []
for _pattern in ('libavcodec.so*', 'libavformat.so*', 'libavutil.so*',
                 'libswresample.so*', 'libswscale.so*'):
    for _f in glob.glob(os.path.join(_pyqt6_lib, _pattern)):
        _ffmpeg_libs.append((_f, 'PyQt6/Qt6/lib'))

# ── FFmpeg multimedia plugin ───────────────────────────────────────
_mm_plugin = os.path.join(
    os.path.dirname(_pyqt6_mod.__file__),
    'Qt6', 'plugins', 'multimedia', 'libffmpegmediaplugin.so'
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
    ],
    hookspath=[],
    runtime_hooks=['rthook_theflow.py'],
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
    name='theflow',
    debug=False,
    strip=False,           # DO NOT strip — breaks FFmpeg .so alignment
    upx=False,             # DO NOT compress — UPX corrupts FFmpeg libs
    upx_exclude=[],
    console=False,
    target_arch=None,
)
