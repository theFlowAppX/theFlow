# hook_fix_cfbundle.py
# =========================================================
# PyInstaller runtime hook for theFlow — macOS
#
# Fixes two distinct crash types:
#
# 1. CFBundle crash — EXC_BAD_ACCESS when PyQt6 calls
#    CFBundleCopyBundleURL before the bundle is initialized.
#
# 2. abort() crash — PyQt6/sip calls QMessageLogger::fatal()
#    -> abort() when any Python exception escapes a C++
#    virtual override (paintEvent, mouseDoubleClickEvent…).
#    Installing a Qt message handler intercepts the fatal
#    call and prints the traceback instead of killing the app.
# =========================================================

import os
import sys
import traceback

# ── Global Python exception hook ──────────────────────────
# Catches any unhandled Python exception and prints it
# instead of letting it propagate silently into C++.
def _excepthook(exc_type, exc_value, exc_tb):
    traceback.print_exception(exc_type, exc_value, exc_tb)

sys.excepthook = _excepthook

# ── 1. Tell Qt exactly where its plugins live ─────────────
if hasattr(sys, '_MEIPASS'):
    meipass = sys._MEIPASS

    qt_plugins = os.path.join(meipass, 'PyQt6', 'Qt6', 'plugins')
    if not os.path.isdir(qt_plugins):
        qt_plugins = os.path.join(meipass, 'PyQt6', 'plugins')

    if os.path.isdir(qt_plugins):
        os.environ['QT_PLUGIN_PATH'] = qt_plugins

    platform_plugins = os.path.join(qt_plugins, 'platforms')
    if os.path.isdir(platform_plugins):
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = platform_plugins

    # ── 2. Pre-initialize the macOS bundle reference ──────
    try:
        import ctypes
        import ctypes.util

        cf = ctypes.cdll.LoadLibrary(
            ctypes.util.find_library('CoreFoundation'))

        cf.CFBundleGetMainBundle.restype = ctypes.c_void_p
        cf.CFBundleGetMainBundle.argtypes = []

        bundle = cf.CFBundleGetMainBundle()
        if not bundle:
            cf.CFBundleCreate.restype  = ctypes.c_void_p
            cf.CFBundleCreate.argtypes = [ctypes.c_void_p,
                                          ctypes.c_void_p]
            cf.CFURLCreateFromFileSystemRepresentation.restype  = ctypes.c_void_p
            cf.CFURLCreateFromFileSystemRepresentation.argtypes = [
                ctypes.c_void_p, ctypes.c_char_p,
                ctypes.c_long,   ctypes.c_bool]

            exe_dir = os.path.dirname(sys.executable).encode('utf-8')
            url = cf.CFURLCreateFromFileSystemRepresentation(
                None, exe_dir, len(exe_dir), True)
            if url:
                cf.CFBundleCreate(None, url)

    except Exception:
        pass

# ── 3. Qt message handler — stops abort() on fatal messages ──
# PyQt6's sip layer calls QMessageLogger::fatal() when a Python
# exception escapes a virtual override. This replaces Qt's default
# handler (which calls abort()) with one that just prints and returns.
#
# Must be installed after QApplication exists, so we hook the
# import system to install it the moment QtWidgets is imported.

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
            # Return without calling abort() — this is the key fix.

        qInstallMessageHandler(_handler)
    except Exception:
        pass


import builtins
_real_import = builtins.__import__

def _patched_import(name, *args, **kwargs):
    mod = _real_import(name, *args, **kwargs)
    if name in ('PyQt6.QtWidgets', 'PyQt6.QtCore'):
        _install_qt_message_handler()
        builtins.__import__ = _real_import  # restore after first hit
    return mod

builtins.__import__ = _patched_import
