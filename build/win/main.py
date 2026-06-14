# main.py
# =========================================================
# ENTRY POINT FOR THEFLOW! — Windows
# =========================================================

import sys
import os
import json

# Ensure bundled modules are findable in frozen binary
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    if sys._MEIPASS not in sys.path:
        sys.path.insert(0, sys._MEIPASS)

# =========================================================
# 1. IMPORT QApplication FIRST
# =========================================================
from PyQt6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication(sys.argv)
_app.setStyle("Fusion")

# =========================================================
# 2. LOAD & INITIALIZE SETTINGS DYNAMICALLY
# =========================================================
from config import SETTINGS_FILE
from settings import DEFAULTS

def load_initial_settings():
    settings_dir = os.path.dirname(SETTINGS_FILE)
    if not os.path.exists(settings_dir):
        try:
            os.makedirs(settings_dir, exist_ok=True)
        except Exception as e:
            print(f"Failed to create settings folder: {e}")

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
            merged = DEFAULTS.copy()
            merged.update(data)
            return merged
        except Exception as e:
            print(f"Could not read settings file, falling back: {e}")
            return DEFAULTS.copy()

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
        app = QApplication(sys.argv)
        app.setStyle("Fusion")

    v = View()
    v.resize(1280, 720)

    if GLOBAL_SETTINGS:
        v.apply_settings(GLOBAL_SETTINGS)

    v.show()

    # Open file passed as argument (e.g. double-click .flow file from Explorer)
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.isfile(file_path):
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(400, lambda: v.load_file(file_path))

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
