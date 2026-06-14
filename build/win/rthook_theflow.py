# rthook_theflow.py
# =========================================================
# PyInstaller runtime hook for theFlow — Windows 64-bit
# Runs BEFORE main.py
# =========================================================

import sys
import os

# ── 1. Fix sys.path ───────────────────────────────────────
if hasattr(sys, '_MEIPASS'):
    meipass = sys._MEIPASS
    if meipass not in sys.path:
        sys.path.insert(0, meipass)
    exe_dir = os.path.dirname(sys.executable)
    if exe_dir not in sys.path:
        sys.path.insert(0, exe_dir)
    # Qt plugin paths
    qt_plugins = os.path.join(meipass, 'PyQt6', 'Qt6', 'plugins')
    if not os.path.isdir(qt_plugins):
        qt_plugins = os.path.join(meipass, 'PyQt6', 'plugins')
    if os.path.isdir(qt_plugins):
        os.environ['QT_PLUGIN_PATH'] = qt_plugins
        platform_dir = os.path.join(qt_plugins, 'platforms')
        if os.path.isdir(platform_dir):
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = platform_dir

# ── 2. Exception hook ─────────────────────────────────────
import traceback
def _excepthook(exc_type, exc_value, exc_tb):
    traceback.print_exception(exc_type, exc_value, exc_tb)
sys.excepthook = _excepthook
