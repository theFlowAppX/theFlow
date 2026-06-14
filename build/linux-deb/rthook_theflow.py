# rthook_theflow.py
# =========================================================
# PyInstaller runtime hook for theFlow — Linux
#
# Runs BEFORE any app code. Does three things:
#
# 1. Path — ensures sys._MEIPASS is on sys.path so all
#    bundled modules find each other exactly as in dev.
#
# 2. Qt paths — sets QT_PLUGIN_PATH, QT_QPA_PLATFORM_PLUGIN_PATH,
#    LD_LIBRARY_PATH for bundled FFmpeg libs.
#
# 3. sip exception gate — installs a Qt message handler that
#    intercepts QMessageLogger::fatal() -> abort() when a Python
#    exception escapes a C++ virtual override (paintEvent, etc).
# =========================================================

import sys
import os
import traceback

# Force X11 backend — prevents Wayland transient-window issues
if 'QT_QPA_PLATFORM' not in os.environ:
    os.environ['QT_QPA_PLATFORM'] = 'xcb'

# ── Bundled FFmpeg + multimedia plugin paths ──────────────
if hasattr(sys, '_MEIPASS'):
    _mei = sys._MEIPASS

    _mm_dir = os.path.join(_mei, 'PyQt6', 'Qt6', 'plugins', 'multimedia')
    if os.path.isdir(_mm_dir):
        existing = os.environ.get('QT_PLUGIN_PATH', '')
        os.environ['QT_PLUGIN_PATH'] = _mm_dir + (':' + existing if existing else '')

    _lib_dir = os.path.join(_mei, 'PyQt6', 'Qt6', 'lib')
    if os.path.isdir(_lib_dir):
        existing = os.environ.get('LD_LIBRARY_PATH', '')
        os.environ['LD_LIBRARY_PATH'] = _lib_dir + (':' + existing if existing else '')

# ── 1. Fix sys.path ───────────────────────────────────────
if hasattr(sys, '_MEIPASS'):
    meipass = sys._MEIPASS
    if meipass not in sys.path:
        sys.path.insert(0, meipass)

    qt_plugins = os.path.join(meipass, 'PyQt6', 'Qt6', 'plugins')
    if not os.path.isdir(qt_plugins):
        qt_plugins = os.path.join(meipass, 'PyQt6', 'plugins')
    if os.path.isdir(qt_plugins):
        os.environ['QT_PLUGIN_PATH'] = qt_plugins
        platform_dir = os.path.join(qt_plugins, 'platforms')
        if os.path.isdir(platform_dir):
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = platform_dir

# ── 2. Global Python exception hook ──────────────────────
def _excepthook(exc_type, exc_value, exc_tb):
    traceback.print_exception(exc_type, exc_value, exc_tb)

sys.excepthook = _excepthook

# ── 3. Qt message handler — stops abort() on fatal msgs ──
def _install_qt_message_handler():
    try:
        from PyQt6.QtCore import qInstallMessageHandler, QtMsgType

        def _handler(msg_type, context, message):
            label = {
                QtMsgType.QtDebugMsg:    'QtDebug',
                QtMsgType.QtInfoMsg:     'QtInfo',
                QtMsgType.QtWarningMsg:  'QtWarning',
                QtMsgType.QtCriticalMsg: 'QtCritical',
                QtMsgType.QtFatalMsg:    'QtFatal',
            }.get(msg_type, 'Qt')
            print(f'[{label}] {message}', file=sys.stderr, flush=True)

        qInstallMessageHandler(_handler)
    except Exception as e:
        print(f'[rthook] could not install Qt message handler: {e}', file=sys.stderr)

import builtins
_real_import = builtins.__import__

def _patched_import(name, *args, **kwargs):
    mod = _real_import(name, *args, **kwargs)
    if name in ('PyQt6.QtWidgets', 'PyQt6.QtCore'):
        _install_qt_message_handler()
        builtins.__import__ = _real_import
    return mod

builtins.__import__ = _patched_import
