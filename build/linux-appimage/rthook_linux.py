# rthook_linux.py
# =========================================================
# PyInstaller runtime hook for theFlow — Linux
# Runs BEFORE main_linux.py
# =========================================================

import sys
import os
import traceback

# ── 1. Fix sys.path ───────────────────────────────────────
if hasattr(sys, '_MEIPASS'):
    meipass = sys._MEIPASS
    if meipass not in sys.path:
        sys.path.insert(0, meipass)

    # Qt plugin paths
    qt_plugins = os.path.join(meipass, 'PyQt6', 'Qt6', 'plugins')
    if not os.path.isdir(qt_plugins):
        qt_plugins = os.path.join(meipass, 'PyQt6', 'plugins')
    if os.path.isdir(qt_plugins):
        os.environ['QT_PLUGIN_PATH'] = qt_plugins
        platform_dir = os.path.join(qt_plugins, 'platforms')
        if os.path.isdir(platform_dir):
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = platform_dir

    # Library path
    lib_dir = os.path.join(meipass, 'PyQt6', 'Qt6', 'lib')
    if os.path.isdir(lib_dir):
        os.environ['LD_LIBRARY_PATH'] = lib_dir + ':' + os.environ.get('LD_LIBRARY_PATH', '')

# ── 2. Exception hook ─────────────────────────────────────
def _excepthook(exc_type, exc_value, exc_tb):
    traceback.print_exception(exc_type, exc_value, exc_tb)

sys.excepthook = _excepthook
