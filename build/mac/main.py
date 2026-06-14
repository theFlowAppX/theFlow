# =========================================================
# theFlow! - Visual Canvas Application
# =========================================================
#
# Copyright (c) 2026 [Xavier Gares]
#
# This file is part of theFlow.
#
# theFlow is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# theFlow is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# main.py
# =========================================================
# ENTRY POINT FOR THEFLOW!
# =========================================================

import sys
import os
import json

# =========================================================
# CRITICAL: macOS Multimedia Backend Fix
# =========================================================
os.environ['QT_AUDIO_BACKEND'] = 'coreaudio'
# NOTE: QT_VIDEO_BACKEND=dummy removed — it causes a segfault on macOS
# with PyQt6 >= 6.4 because the dummy backend conflicts with the
# AVFoundation compositor that QVideoWidget requires.
# QT_MAC_WANTS_LAYER is now always enabled by Qt and has no effect.

# ── Frozen binary AVFoundation pixel buffer fix ──────────────────
# When running as a PyInstaller bundle, libdarwinmediaplugin.dylib
# negotiates pixel buffer attributes with CoreVideo at startup which
# can crash on macOS 14/15 due to a selector mismatch in the bundled
# Qt 6.4 AVFoundation backend vs the system VideoToolbox.
# Disabling Metal surface rendering forces the software path which
# avoids the CVPixelBuffer negotiation entirely.
if getattr(sys, 'frozen', False):
    os.environ.setdefault('QT_QUICK_BACKEND', 'software')
    os.environ.setdefault('QT_OPENGL', 'software')
    # Force AVFoundation to use a compatible pixel format
    os.environ.setdefault('QT_MULTIMEDIA_PREFERRED_PLUGINS', 'darwin')

# =========================================================
# 1. IMPORT QApplication FIRST — with macOS file open support
# =========================================================
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QEvent

class TheFlowApp(QApplication):
    """Custom QApplication that handles macOS QFileOpenEvent.
    When the user double-clicks a .flow file in Finder, macOS sends
    this event to the running app instead of passing argv."""

    def __init__(self, argv):
        super().__init__(argv)
        self._pending_file = None   # file to open once View is ready
        self._view         = None   # set after View is constructed

    def event(self, e):
        if e.type() == QEvent.Type.FileOpen:
            path = e.file()
            if path.endswith('.flow'):
                if self._view is not None:
                    self._view.open_path(path)
                else:
                    self._pending_file = path  # View not ready yet
            return True
        return super().event(e)

_app = QApplication.instance() or TheFlowApp(sys.argv)
_app.setStyle("Fusion")

# =========================================================
# 2. LOAD & INITIALIZE SETTINGS DYNAMICALLY
# =========================================================
from config import SETTINGS_FILE
from settings import DEFAULTS

def load_initial_settings():
    """
    Guarantees settings/settings.json exists at startup.
    Creates directory/file if missing, reads and merges if existing.
    """
    settings_dir = os.path.dirname(SETTINGS_FILE)

    # Ensure directory folder exists
    if not os.path.exists(settings_dir):
        try:
            os.makedirs(settings_dir, exist_ok=True)
        except Exception as e:
            print(f"Failed to create settings folder: {e}")

    # Build or update configuration file layout
    if not os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(DEFAULTS, f, indent=2)
            return DEFAULTS.copy()
        except Exception as e:
            print(f"Failed to write default settings file: {e}")
            return DEFAULTS.copy()
    else:
        try:
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
            # Enforce schema integrity by merging loaded file into full defaults
            merged = DEFAULTS.copy()
            merged.update(data)
            return merged
        except Exception as e:
            print(f"Could not read settings file, falling back: {e}")
            return DEFAULTS.copy()

# Load verified full data map array globally into application lifecycle
GLOBAL_SETTINGS = load_initial_settings()

# =========================================================
# 3. IMPORT CUSTOM MODULES
# =========================================================
from view_logic import View

# =========================================================
# 4. MAIN ENTRY POINT
# =========================================================
def main():
    app = QApplication.instance()
    if not app:
        app = TheFlowApp(sys.argv)
        app.setStyle("Fusion")

    v = View()
    v.resize(1280, 720)

    if GLOBAL_SETTINGS:
        v.apply_settings(GLOBAL_SETTINGS)

    # Wire view into app for QFileOpenEvent handling
    if isinstance(app, TheFlowApp):
        app._view = v
        # Open pending file if QFileOpenEvent arrived before View was ready
        if app._pending_file:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(400, lambda: v.open_path(app._pending_file))
            app._pending_file = None

    # Handle file passed via command line (e.g. open from terminal)
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if path.endswith('.flow') and os.path.isfile(path):
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(400, lambda: v.open_path(path))

    v.show()
    exit_code = app.exec()
    # On PyQt6 6.4.x / macOS, the C++ destructor sequence triggered by
    # sys.exit() races with Python's GC and causes a segfault on shutdown.
    # os._exit() terminates the process immediately without running
    # destructors — safe here because the event loop has already finished
    # and all user data has been saved.
    os._exit(exit_code)

if __name__ == "__main__":
    main()
