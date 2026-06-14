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
# LOGO  –  Animated SVG Logo Overlay for Empty Canvas
# =========================================================
#
# TIMING KNOBS — change these two values to adjust fade speed:
#
#   FADE_IN_MS  = 1000   # milliseconds for the logo to fade in
#   FADE_OUT_MS = 1000   # milliseconds for the logo to fade out
#
# Both are defined as class attributes on LogoOverlay so you
# can also override them per-instance after construction:
#   view._logo.FADE_IN_MS = 500
# =========================================================

import os
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtGui import QPainter
from PyQt6.QtCore import QRectF, QTimeLine


class LogoOverlay:
    """Manages loading, fading, and painting the SVG logo overlay.

    Usage in View
    -------------
    Construction (in View.__init__):
        self._logo = LogoOverlay(self)          # pass the view as parent

    After any scene change that may show/hide the logo:
        self._logo.check_fade(self._is_canvas_empty())

    In View.paintEvent, after super().paintEvent(event):
        self._logo.paint(QPainter(self.viewport()), self.viewport())
    """

    # ── Timing — edit these two values to change fade speed ──────────────
    FADE_IN_MS  = 200   # <- fade-in  duration in milliseconds
    FADE_OUT_MS = 200   # <- fade-out duration in milliseconds
    # ─────────────────────────────────────────────────────────────────────

    # Display scale (SVG natural size × SCALE)
    SCALE   = 3

    # Position offset from viewport centre (pixels)
    OFFSET_X = 0   # <- move logo left (negative) / right (positive)
    OFFSET_Y = 0   # <- move logo up   (negative) / down  (positive)

    def __init__(self, parent_view):
        self._view    = parent_view
        self._opacity = 0.0   # 0.0 = invisible, 1.0 = fully visible

        # Locate logo.svg relative to this file
        import sys as _sys
        if getattr(_sys, 'frozen', False):
            script_dir = _sys._MEIPASS
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path  = os.path.join(script_dir, "logo", "logo.svg")
        self._renderer = QSvgRenderer(logo_path)
        if not self._renderer.isValid():
            print(f"LogoOverlay: could not load SVG at {logo_path}")

        # Animation timeline (frame 0–100 maps to opacity 0.0–1.0)
        self._timeline = QTimeLine(self.FADE_IN_MS, parent_view)
        self._timeline.setFrameRange(0, 100)
        self._timeline.frameChanged.connect(self._on_frame)

        # Start the initial fade-in immediately
        self._start_fade(fade_in=True)

    # ── Public API ────────────────────────────────────────────────────────

    def check_fade(self, canvas_is_empty: bool):
        """Call after any scene change.  Triggers fade-in or fade-out as needed."""
        if canvas_is_empty:
            if self._opacity < 1.0:
                self._start_fade(fade_in=True)
        else:
            if self._opacity > 0.0:
                self._start_fade(fade_in=False)

    def paint(self, painter: QPainter, viewport):
        """Paint the logo onto *viewport* using *painter*.

        Call from View.paintEvent after super().paintEvent().
        The painter should be constructed on the viewport widget.
        """
        if self._opacity <= 0.0 or not self._renderer.isValid():
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setOpacity(self._opacity)

        default_size = self._renderer.defaultSize()
        logo_w = default_size.width()  * self.SCALE
        logo_h = default_size.height() * self.SCALE

        x = (viewport.width()  - logo_w) // 2 + self.OFFSET_X
        y = (viewport.height() - logo_h) // 2 + self.OFFSET_Y

        self._renderer.render(painter, QRectF(x, y, logo_w, logo_h))

    # ── Internal ──────────────────────────────────────────────────────────

    def _start_fade(self, fade_in: bool):
        tl = self._timeline
        tl.stop()
        if fade_in:
            tl.setDuration(self.FADE_IN_MS)
            tl.setDirection(QTimeLine.Direction.Forward)
            tl.setCurrentTime(int(self._opacity * self.FADE_IN_MS))
        else:
            tl.setDuration(self.FADE_OUT_MS)
            tl.setDirection(QTimeLine.Direction.Backward)
            tl.setCurrentTime(int(self._opacity * self.FADE_OUT_MS))
        tl.start()

    def _on_frame(self, frame: int):
        self._opacity = frame / 100.0
        self._view.viewport().update()
