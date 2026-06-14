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

# =========================================================
# UTILS
# =========================================================

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QColorDialog, QTextEdit, QLineEdit,
)
from PyQt6.QtGui import (
    QColor, QPen, QPainterPath, QFont, QPolygonF,
    QTextCharFormat,
)
from PyQt6.QtCore import Qt, QPointF, QSizeF

# ================= CONSTANTS =================

NODE_BG             = "#2a2a2a"
NODE_BORDER         = "#5c5c5c"
TEXT_COLOR          = "#ffffff"
SOCKET_COLOR        = "#4a9eff"
LINE_COLOR          = "#ffffff"
LINE_SELECTED_COLOR = "#50aaff"
CORNER_RADIUS       = 12
DOT_RADIUS          = 24
SOCKET_SIZE         = 8
HANDLE_SIZE         = 12
MAX_FONT_SIZE       = 100000   # req 15: reasonable cap

# =========================================================
# GLOBAL DRAG STATE  – mutable dict shared across all modules
# =========================================================
DRAG_STATE = {"active": None}


# =========================================================
# HELPERS
# =========================================================

def _bezier_path(p_out, p_in, out_orient="left-right", in_orient="left-right"):
    """Build a bezier path where control point direction follows socket orientation."""
    def _ctrl_offset(orient, length):
        """Return (dx, dy) for the control point offset given socket orientation."""
        if orient in ("left-right",):
            return (length, 0)
        elif orient in ("right-left",):
            return (-length, 0)
        elif orient in ("top-bottom",):
            return (0, length)
        elif orient in ("bottom-top",):
            return (0, -length)
        return (length, 0)

    dist = max(abs(p_in.x() - p_out.x()), abs(p_in.y() - p_out.y())) * 0.5
    ox, oy = _ctrl_offset(out_orient, dist)
    ix, iy = _ctrl_offset(in_orient, -dist)
    c1 = QPointF(p_out.x() + ox, p_out.y() + oy)
    c2 = QPointF(p_in.x()  + ix, p_in.y()  + iy)
    path = QPainterPath(p_out)
    path.cubicTo(c1, c2, p_in)
    return path


def _make_temp_line(scene):
    from PyQt6.QtWidgets import QGraphicsPathItem
    line = QGraphicsPathItem()
    line.setPen(QPen(QColor(LINE_COLOR), 2))
    line.setZValue(100)
    scene.addItem(line)
    return line


def _remove_from(lst, item):
    if item in lst:
        lst.remove(item)


def _normalise(sock_a, sock_b):
    if sock_a.is_input:
        return sock_b, sock_a
    return sock_a, sock_b


def _diamond_poly(rect):
    cx, cy = rect.center().x(), rect.center().y()
    return QPolygonF([
        QPointF(cx, rect.top()),
        QPointF(rect.right(), cy),
        QPointF(cx, rect.bottom()),
        QPointF(rect.left(), cy),
    ])


def open_color_wheel(parent_widget, current_color=None):
    initial = QColor(current_color) if current_color else QColor("#4a9eff")
    color = QColorDialog.getColor(
        initial, parent_widget, "Choose Color",
        QColorDialog.ColorDialogOption.ShowAlphaChannel,
    )
    return color if color.isValid() else None


# Module-level menu color state — updated by apply_settings / _apply_to_scene
# so every _menu_style() call anywhere in the app picks up the current theme.
_MENU_COLORS = {
    "bg":       "#2a2a2a",
    "fg":       "#ffffff",
    "border":   "#5c5c5c",
    "hover":    "#4a9eff",
    "disabled": "#666666",
}

def update_menu_colors(bg: str, fg: str):
    """Call from apply_settings to switch theme colors globally."""
    import colorsys

    def _hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))

    def _rgb_to_hex(r, g, b):
        return "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))

    r, g, b = _hex_to_rgb(bg)
    import colorsys as _cs
    h, s, v = _cs.rgb_to_hsv(r, g, b)
    border_v = min(1.0, v + 0.15) if v < 0.5 else max(0.0, v - 0.15)
    border = _rgb_to_hex(*_cs.hsv_to_rgb(h, s, border_v))

    fr, fg_, fb = _hex_to_rgb(fg)
    br, bg_, bb = _hex_to_rgb(bg)
    disabled = _rgb_to_hex(fr*0.4 + br*0.6, fg_*0.4 + bg_*0.6, fb*0.4 + bb*0.6)

    _MENU_COLORS["bg"]       = bg
    _MENU_COLORS["fg"]       = fg
    _MENU_COLORS["border"]   = border
    _MENU_COLORS["disabled"] = disabled


def _menu_style():
    c = _MENU_COLORS
    return (
        f"QMenu {{"
        f"  background-color: {c['bg']};"
        f"  color: {c['fg']};"
        f"  border: 1px solid {c['border']};"
        f"  padding: 4px;"
        f"}}"
        f"QMenu::item {{ padding: 6px 24px; }}"
        f"QMenu::item:selected {{ background-color: {c['hover']}; color: #ffffff; }}"
        f"QMenu::separator {{ height: 1px; background: {c['border']}; margin: 4px 0; }}"
        f"QMenu::item:disabled {{ color: {c['disabled']}; }}"
    )


def _global_point(q_point_or_f):
    """Return a QPoint from QPoint, QPointF, or anything with x()/y() — safe on all platforms."""
    from PyQt6.QtCore import QPoint, QPointF
    if isinstance(q_point_or_f, QPoint):
        return q_point_or_f
    if isinstance(q_point_or_f, QPointF):
        return q_point_or_f.toPoint()
    if hasattr(q_point_or_f, 'toPoint'):
        return q_point_or_f.toPoint()
    if hasattr(q_point_or_f, 'x') and hasattr(q_point_or_f, 'y'):
        return QPoint(int(q_point_or_f.x()), int(q_point_or_f.y()))
    return q_point_or_f


# =========================================================
# STDERR SUPPRESSOR — silences noisy C-library media warnings
# e.g. "[mp3float @ 0x...] Could not update timestamps for skipped samples"
# These come from FFmpeg/AVFoundation directly via the OS fd, bypassing
# Python's sys.stderr, so os.dup2 is the only reliable intercept.
# =========================================================

import os as _os
import contextlib as _contextlib

@_contextlib.contextmanager
def suppress_media_stderr():
    """Redirect C-level stderr (fd 2) to /dev/null for the block."""
    try:
        devnull_fd = _os.open(_os.devnull, _os.O_WRONLY)
        saved_fd   = _os.dup(2)
        _os.dup2(devnull_fd, 2)
        _os.close(devnull_fd)
        try:
            yield
        finally:
            _os.dup2(saved_fd, 2)
            _os.close(saved_fd)
    except Exception:
        yield  # never crash the caller


# =========================================================
# RICH TEXT EDITOR DIALOG  (req 15 / node double-click)
# =========================================================

class RichTextEditDialog(QDialog):
    """Two-field editor:
    - Name  : shown on the canvas (plain text, single line)
    - Text  : hidden from the canvas (rich text with formatting tools)
    Font-size spinner and bold/italic/underline/strike apply to the Text field only.
    Name font size / color are controlled via the node's context menu.
    """

    def __init__(self, parent, initial_name="Name", initial_html="",
                 initial_font_size=35):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Window)
        self.setWindowTitle("Edit Node")
        self.setMinimumSize(480, 420)
        self.setStyleSheet("background:#2a2a2a; color:#ffffff;")

        layout = QVBoxLayout(self)

        # ── Name field ────────────────────────────────────
        name_row = QHBoxLayout()
        name_lbl = QLabel("Name  (visible on node):")
        name_lbl.setStyleSheet("color:#aaaaaa; font-size:11px;")
        name_row.addWidget(name_lbl)
        layout.addLayout(name_row)

        self.name_edit = QLineEdit()
        self.name_edit.setText(initial_name)
        self.name_edit.setStyleSheet(
            "background:#1b1b1b; color:#ffffff; border:1px solid #5c5c5c;"
            " padding:4px; font-size:13px;")
        layout.addWidget(self.name_edit)

        # ── Text field label ──────────────────────────────
        text_lbl = QLabel("Text:")
        text_lbl.setStyleSheet("color:#aaaaaa; font-size:11px; margin-top:8px;")
        layout.addWidget(text_lbl)

        # ── Formatting toolbar ─────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Canvas font size:"))

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(6, MAX_FONT_SIZE)
        self.font_size_spin.setValue(initial_font_size)
        # spinner does NOT drive the editor — it sets the canvas _font_size on OK
        toolbar.addWidget(self.font_size_spin)

        def _btn(label):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setFixedWidth(32)
            return b

        self.bold_btn      = _btn("B")
        self.italic_btn    = _btn("I")
        self.underline_btn = _btn("U")
        self.strike_btn    = _btn("S\u0336")
        for b in (self.bold_btn, self.italic_btn,
                  self.underline_btn, self.strike_btn):
            b.clicked.connect(self._apply_format)
            toolbar.addWidget(b)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # ── Rich-text editor — fixed comfortable reading size ─
        self.editor = QTextEdit()
        self.editor.setStyleSheet(
            "background:#1b1b1b; color:#ffffff; border:1px solid #5c5c5c;")
        self._set_editor_font(13)
        if initial_html:
            self.editor.setHtml(initial_html)
        else:
            self._set_editor_font(13)
        layout.addWidget(self.editor)

        # ── Clear text button ─────────────────────────────
        clear_row = QHBoxLayout()
        clear_text_btn = QPushButton("Clear Text")
        clear_text_btn.setFixedWidth(100)
        clear_text_btn.clicked.connect(self.editor.clear)
        clear_row.addStretch()
        clear_row.addWidget(clear_text_btn)
        layout.addLayout(clear_row)

        # ── OK / Cancel ───────────────────────────────────
        btn_row = QHBoxLayout()
        ok = QPushButton("OK")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(ok)
        btn_row.addWidget(cancel)
        layout.addLayout(btn_row)

    def get_name(self):       return self.name_edit.text()
    def get_html(self):
        return self.editor.toHtml() if self.editor.toPlainText().strip() else ""
    def get_plain(self):      return self.editor.toPlainText()
    def get_font_size(self):  return self.font_size_spin.value()

    def _set_editor_font(self, size):
        """Set document default font and current char format so all text uses this size."""
        doc_font = QFont("Arial", int(size))
        self.editor.document().setDefaultFont(doc_font)
        fmt = QTextCharFormat()
        fmt.setFontPointSize(float(size))
        fmt.setFontFamilies(["Arial"])
        self.editor.setCurrentCharFormat(fmt)

    def _apply_format(self):
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(cursor.SelectionType.Document)
        fmt = QTextCharFormat()
        fmt.setFontWeight(
            QFont.Weight.Bold if self.bold_btn.isChecked()
            else QFont.Weight.Normal)
        fmt.setFontItalic(self.italic_btn.isChecked())
        fmt.setFontUnderline(self.underline_btn.isChecked())
        fmt.setFontStrikeOut(self.strike_btn.isChecked())
        cursor.mergeCharFormat(fmt)

    def _apply_font_size(self, size):
        # Update document default so new typing uses this size
        self._set_editor_font(size)
        # Also apply to existing text
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(cursor.SelectionType.Document)
        fmt = QTextCharFormat()
        fmt.setFontPointSize(float(size))
        cursor.mergeCharFormat(fmt)
