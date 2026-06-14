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


# config.py
# =========================================================
# GLOBAL CONFIGURATION FOR THEFLOW!
# =========================================================

import os
import sys

# ------------------------------------------------------------------
# APPLICATION METADATA
# ------------------------------------------------------------------
APP_NAME = "theFlow"
VERSION = "0.1.0"
AUTHOR = "Xavier Gares"
COPYRIGHT_YEAR = "2026"
LICENSE_URL = "https://www.gnu.org/licenses/gpl-3.0.html"
CONTACT_EMAIL = "theflow!@protonmail.com"

# ------------------------------------------------------------------
# FILE HANDLING & DIRECTORIES (RELATIVE CALCULATION)
# ------------------------------------------------------------------
DEFAULT_FILE_EXT = ".flow"
FILE_FILTER = f"{APP_NAME} Files (*{DEFAULT_FILE_EXT});;All Files (*)"

# Anchor to the absolute folder where settings are stored.
# When running as a PyInstaller .exe, __file__ resolves to the temp
# _MEIPASS unpack directory which is deleted on exit — settings would
# never persist. Instead we use the folder next to the .exe itself.
if getattr(sys, 'frozen', False):
    import platform
    if platform.system() == 'Linux':
        # XDG config dir: ~/.config/theflow/ — writable, persists across updates
        _BASE_DIR = os.path.join(
            os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')),
            'theflow'
        )
    else:
        # macOS / Windows: next to the executable
        _BASE_DIR = os.path.dirname(sys.executable)
else:
    # Running from source
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Target path mapping: <next to exe or source root>/settings/settings.json
_SETTINGS_DIR = os.path.join(_BASE_DIR, "settings")
SETTINGS_FILE = os.path.join(_SETTINGS_DIR, "settings.json")

# ------------------------------------------------------------------
# COLOR PALETTES
# ------------------------------------------------------------------

# Dark Theme (Default)
DARK = {
    "bg": "#232323",           # Canvas Background
    "node_bg": "#2a2a2a",      # Node Background
    "node_border": "#5c5c5c",  # Node Border
    "text": "#ffffff",         # Default Text Color
    "text_secondary": "#aaaaaa",
    "socket": "#4a9eff",       # Socket Color
    "line": "#ffffff",         # Connection Line
    "line_selected": "#50aaff",
    "menu_bg": "#2a2a2a",
    "menu_fg": "#ffffff",
    "menu_hover": "#4a9eff",
    "menu_disabled": "#555555"
}

# Light Theme Layout Palette Options
LIGHT = {
    "bg": "#9f9f9f",
    "node_bg": "#ffffff",
    "node_border": "#cccccc",
    "text": "#1a1a1a",
    "text_secondary": "#666666",
    "socket": "#0066cc",
    "line": "#333333",
    "line_selected": "#0066cc",
    "menu_bg": "#ffffff",
    "menu_fg": "#1a1a1a",
    "menu_hover": "#e0f0ff",
    "menu_disabled": "#aaaaaa"
}

# ------------------------------------------------------------------
# MACOS MULTIMEDIA FIXES
# ------------------------------------------------------------------

# Environment variables to set BEFORE QApplication creation.
# NOTE: QT_VIDEO_BACKEND=dummy has been removed — it causes a segfault
# on macOS with PyQt6 >= 6.4 because the dummy backend conflicts with
# the AVFoundation compositor that QVideoWidget requires at runtime.
# These are macOS-only and have no effect on Windows.
MACOS_ENV_VARS = {
    "QT_AUDIO_BACKEND": "coreaudio",
    # QT_MAC_WANTS_LAYER is now always enabled by Qt; setting it has no effect.
}

# ------------------------------------------------------------------
# CLIPBOARD  –  In-memory copy/paste buffer (list of snapshot dicts)
# ------------------------------------------------------------------
CLIPBOARD = []

# ------------------------------------------------------------------
# SHORTCUTS
# ------------------------------------------------------------------

SHORTCUTS = {
    "create_text": "T",
    "create_image": "I",
    "create_movie": "M",
    "create_audio": "A",
    "create_doc": "D",
    "create_dot": "Q",
    "create_backdrop": "B",
    "create_sticky": "S",
    "undo": "Ctrl+Z",
    "redo": "Ctrl+Y",
    "copy": "Ctrl+C",
    "cut": "Ctrl+X",
    "paste": "Ctrl+V",
    "delete": "Del",
    "save": "Ctrl+S",
    "save_as": "Ctrl+Shift+S",
    "open": "Ctrl+O",
    "new": "Ctrl+N",
    "quit": "Ctrl+Q",
    "shortcuts_help": "K",
    "tab_menu": "Tab",
    "expand_nodes": "Shift+Down",
    "contract_nodes": "Shift+Up",
    "frame_selected": "F",
    "zoom_in": "Ctrl+Plus",
    "zoom_out": "Ctrl+Minus",
}
