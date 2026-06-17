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

# paint.py
# =========================================================
# PAINT NODE – freehand painting with zoom/pan
# =========================================================

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QLabel,
    QWidget, QColorDialog, QMenu, QScrollArea,
)
from PyQt6.QtGui import QColor, QPen, QPainter, QPixmap, QImage, QFont
from PyQt6.QtCore import Qt, QRectF, QPointF, QPoint


# =========================================================
# PAINT CANVAS
# =========================================================

class PaintCanvas(QWidget):
    NATIVE_W = 1200
    NATIVE_H = 900

    def __init__(self, parent=None):
        super().__init__(parent)
        self._display_zoom  = 1.0
        self._bg_color      = QColor("#808080")
        # Strokes stored separately on transparent layer
        self._strokes       = QImage(self.NATIVE_W, self.NATIVE_H,
                                     QImage.Format.Format_ARGB32)
        self._strokes.fill(Qt.GlobalColor.transparent)
        self._brush_color   = QColor("#000000")
        self._brush_size    = 8
        self._stroke_radius = 4
        self._eraser        = False
        self._last_point    = None
        self._drawing       = False
        self._stroke_pts    = []
        self._cursor_pos    = None
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.BlankCursor)
        self._update_size()

    def _update_size(self):
        z = self._display_zoom
        self.setFixedSize(max(1, int(self.NATIVE_W * z)),
                          max(1, int(self.NATIVE_H * z)))

    def _w2i(self, pt):
        z = max(0.001, self._display_zoom)
        return QPoint(int(pt.x() / z), int(pt.y() / z))

    # ── Drawing ───────────────────────────────────────────

    def _paint_line(self, p1, p2, width):
        painter = QPainter(self._strokes)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._eraser:
            # Erase: set pixels to transparent
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_Clear)
            color = Qt.GlobalColor.transparent
        else:
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver)
            color = self._brush_color
        cap  = (Qt.PenCapStyle.RoundCap  if self._stroke_radius > 0
                else Qt.PenCapStyle.FlatCap)
        join = (Qt.PenJoinStyle.RoundJoin if self._stroke_radius > 0
                else Qt.PenJoinStyle.MiterJoin)
        painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine, cap, join))
        painter.drawLine(p1, p2)
        painter.end()

    def _taper(self, i, n):
        if n <= 1: return 1.0
        t = i / (n - 1)
        ramp = 0.15
        if t < ramp:     return t / ramp
        if t > 1 - ramp: return (1 - t) / ramp
        return 1.0

    def _redraw_tapered(self, pts):
        painter = QPainter(self._strokes)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cap  = (Qt.PenCapStyle.RoundCap  if self._stroke_radius > 0
                else Qt.PenCapStyle.FlatCap)
        join = (Qt.PenJoinStyle.RoundJoin if self._stroke_radius > 0
                else Qt.PenJoinStyle.MiterJoin)
        n = len(pts)

        if self._eraser:
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_Clear)
            painter.setPen(QPen(Qt.GlobalColor.transparent,
                                self._brush_size + 2,
                                Qt.PenStyle.SolidLine, cap, join))
            for i in range(n - 1):
                painter.drawLine(pts[i], pts[i + 1])
        else:
            # Erase live preview
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_Clear)
            painter.setPen(QPen(Qt.GlobalColor.transparent,
                                self._brush_size + 2,
                                Qt.PenStyle.SolidLine, cap, join))
            for i in range(n - 1):
                painter.drawLine(pts[i], pts[i + 1])
            # Redraw tapered
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver)
            for i in range(n - 1):
                w = max(0.5, self._brush_size *
                        (self._taper(i, n) + self._taper(i+1, n)) / 2)
                painter.setPen(QPen(self._brush_color, w,
                                    Qt.PenStyle.SolidLine, cap, join))
                painter.drawLine(pts[i], pts[i + 1])
        painter.end()

    # ── Events ────────────────────────────────────────────

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drawing    = True
            ip = self._w2i(e.position().toPoint())
            self._stroke_pts = [ip]
            self._last_point = ip
            self._paint_line(ip, ip, self._brush_size * 0.1)

    def mouseMoveEvent(self, e):
        self._cursor_pos = e.position().toPoint()
        if self._drawing:
            ip = self._w2i(e.position().toPoint())
            self._stroke_pts.append(ip)
            self._paint_line(self._last_point, ip, self._brush_size)
            self._last_point = ip
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self._drawing:
            self._drawing = False
            if len(self._stroke_pts) >= 2:
                self._redraw_tapered(self._stroke_pts)
            self._stroke_pts = []
            self._last_point = None
            self.update()

    def leaveEvent(self, e):
        self._cursor_pos = None
        self.update()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        z = self._display_zoom
        # BG
        painter.fillRect(self.rect(), self._bg_color)
        # Strokes scaled
        painter.scale(z, z)
        painter.drawImage(0, 0, self._strokes)
        painter.resetTransform()
        # Cursor circle
        # Use QPointF + float radii to avoid the QPainter overload ambiguity
        # that causes a TypeError (→ abort()) when _cursor_pos is a QPoint
        # and r is a float.  Also use "is not None" so QPoint(0,0) is not
        # silently skipped (QPoint truthiness is False when both coords are 0).
        if self._cursor_pos is not None:
            r = (self._brush_size / 2) * z
            cx = float(self._cursor_pos.x())
            cy = float(self._cursor_pos.y())
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(0, 0, 0, 180), 1.5))
            painter.drawEllipse(QPointF(cx, cy), r, r)
            painter.setPen(QPen(QColor(255, 255, 255, 180), 1))
            painter.drawEllipse(QPointF(cx, cy), max(1.0, r - 1.5), max(1.0, r - 1.5))

    def clear(self):
        self._strokes.fill(Qt.GlobalColor.transparent)
        self.update()

    def get_pixmap(self):
        # Composite bg + strokes into final image
        result = QImage(self.NATIVE_W, self.NATIVE_H, QImage.Format.Format_ARGB32)
        result.fill(self._bg_color)
        p = QPainter(result)
        p.drawImage(0, 0, self._strokes)
        p.end()
        return QPixmap.fromImage(result)

    def load_pixmap(self, pix):
        # Load into strokes layer (bg is separate)
        img = pix.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        self._strokes = img.scaled(self.NATIVE_W, self.NATIVE_H,
                                   Qt.AspectRatioMode.IgnoreAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
        self.update()


# =========================================================
# PAINT VIEWPORT  –  zoom + pan wrapper
# =========================================================

class PaintViewport(QWidget):
    MIN_ZOOM = 0.1
    MAX_ZOOM = 16.0

    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self._canvas      = canvas
        self._zoom        = 0.5          # start at 50% so canvas fits nicely
        self._panning     = False
        self._pan_start   = None
        self._pan_scroll  = None
        self._space_held  = False

        self._scroll = QScrollArea(self)
        self._scroll.setWidget(canvas)
        self._scroll.setWidgetResizable(False)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll.setStyleSheet("background:#2a2a2a; border:none;")
        self._scroll.viewport().installEventFilter(self)
        self._scroll.viewport().setMouseTracking(True)
        canvas.installEventFilter(self)   # catch middle-button on canvas itself

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._scroll)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._apply_zoom_abs(self._zoom, None)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Space and not e.isAutoRepeat():
            self._space_held = True
            self._scroll.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key.Key_Space:
            self._space_held = False
            self._scroll.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        super().keyReleaseEvent(e)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        is_vp     = obj is self._scroll.viewport()
        is_canvas = obj is self._canvas

        if not (is_vp or is_canvas):
            return False

        t = event.type()

        # Wheel → zoom (from viewport or canvas)
        if t == QEvent.Type.Wheel:
            anchor = event.position().toPoint()
            if is_canvas:
                # Translate canvas-local coords to viewport coords
                anchor = self._canvas.mapTo(self._scroll.viewport(), anchor)
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self._apply_zoom_rel(factor, anchor)
            return True

        # Middle-button or space+left → pan
        if t == QEvent.Type.MouseButtonPress:
            mid  = event.button() == Qt.MouseButton.MiddleButton
            left = (event.button() == Qt.MouseButton.LeftButton and self._space_held)
            if mid or left:
                self._panning    = True
                self._pan_start  = event.globalPosition().toPoint()
                self._pan_scroll = (
                    self._scroll.horizontalScrollBar().value(),
                    self._scroll.verticalScrollBar().value())
                obj.setCursor(Qt.CursorShape.ClosedHandCursor)
                return True

        if t == QEvent.Type.MouseMove and self._panning:
            d = event.globalPosition().toPoint() - self._pan_start
            self._scroll.horizontalScrollBar().setValue(self._pan_scroll[0] - d.x())
            self._scroll.verticalScrollBar().setValue(self._pan_scroll[1] - d.y())
            return True

        if t == QEvent.Type.MouseButtonRelease and self._panning:
            if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.LeftButton):
                self._panning = False
                cur = (Qt.CursorShape.OpenHandCursor if self._space_held
                       else Qt.CursorShape.ArrowCursor)
                obj.setCursor(cur)
                return True

        return False

    def _apply_zoom_rel(self, factor, anchor_vp):
        new_z = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self._zoom * factor))
        if new_z == self._zoom:
            return
        self._apply_zoom_abs(new_z, anchor_vp)

    def _apply_zoom_abs(self, new_z, anchor_vp):
        sb_h = self._scroll.horizontalScrollBar()
        sb_v = self._scroll.verticalScrollBar()
        if anchor_vp and self._zoom > 0:
            sx = (sb_h.value() + anchor_vp.x()) / self._zoom
            sy = (sb_v.value() + anchor_vp.y()) / self._zoom
        else:
            sx = sy = 0

        self._zoom = new_z
        self._canvas._display_zoom = new_z
        self._canvas._update_size()

        if anchor_vp:
            sb_h.setValue(int(sx * new_z - anchor_vp.x()))
            sb_v.setValue(int(sy * new_z - anchor_vp.y()))


# =========================================================
# PAINT DIALOG
# =========================================================

class PaintDialog(QDialog):
    def __init__(self, parent, node):
        super().__init__(None)
        self.setWindowTitle(f"Paint — {node.title._plain}")
        self.setMinimumSize(900, 700)
        self.setStyleSheet("background:#1b1b1b; color:#ffffff;")

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        toolbar = QHBoxLayout()

        # Color
        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(32, 32)
        self._color_btn.setStyleSheet(
            f"background:{node._brush_color.name()}; border:1px solid #555;")
        self._color_btn.clicked.connect(self._pick_color)
        toolbar.addWidget(QLabel("Color:"))
        toolbar.addWidget(self._color_btn)

        # BG
        self._bg_btn = QPushButton()
        self._bg_btn.setFixedSize(32, 32)
        self._bg_btn.setStyleSheet(
            f"background:{node._bg_color.name()}; border:1px solid #555;")
        self._bg_btn.clicked.connect(self._pick_bg)
        toolbar.addWidget(QLabel("  BG:"))
        toolbar.addWidget(self._bg_btn)

        # Size
        toolbar.addWidget(QLabel("  Size:"))
        self._size_slider = QSlider(Qt.Orientation.Horizontal)
        self._size_slider.setRange(1, 80)
        self._size_slider.setValue(node._brush_size)
        self._size_slider.setFixedWidth(120)
        self._size_lbl = QLabel(str(node._brush_size))
        self._size_lbl.setFixedWidth(28)
        self._size_slider.valueChanged.connect(
            lambda v: self._size_lbl.setText(str(v)))
        toolbar.addWidget(self._size_slider)
        toolbar.addWidget(self._size_lbl)

        # Radius
        toolbar.addWidget(QLabel("  Radius:"))
        self._radius_slider = QSlider(Qt.Orientation.Horizontal)
        self._radius_slider.setRange(0, 20)
        self._radius_slider.setValue(node._stroke_radius)
        self._radius_slider.setFixedWidth(80)
        self._radius_lbl = QLabel(str(node._stroke_radius))
        self._radius_lbl.setFixedWidth(24)
        self._radius_slider.valueChanged.connect(
            lambda v: self._radius_lbl.setText(str(v)))
        toolbar.addWidget(self._radius_slider)
        toolbar.addWidget(self._radius_lbl)

        # Eraser / Clear / Done
        self._eraser_btn = QPushButton("Eraser")
        self._eraser_btn.setCheckable(True)
        toolbar.addWidget(self._eraser_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(lambda: self._canvas.clear())
        toolbar.addWidget(clear_btn)

        toolbar.addStretch()

        zoom_lbl = QLabel("Scroll=zoom  Space+drag=pan  MMB=pan")
        zoom_lbl.setStyleSheet("color:#666; font-size:10px;")
        toolbar.addWidget(zoom_lbl)

        ok_btn = QPushButton("Done")
        ok_btn.clicked.connect(self.accept)
        toolbar.addWidget(ok_btn)
        layout.addLayout(toolbar)

        # Canvas + viewport
        self._canvas = PaintCanvas(self)
        if node._paint_pixmap is not None and not node._paint_pixmap.isNull():
            self._canvas.load_pixmap(node._paint_pixmap)
        self._canvas._brush_color   = node._brush_color
        self._canvas._brush_size    = node._brush_size
        self._canvas._stroke_radius = node._stroke_radius
        self._canvas._bg_color      = node._bg_color

        self._vp = PaintViewport(self._canvas, self)
        layout.addWidget(self._vp)

        # Wire sliders
        self._size_slider.valueChanged.connect(
            lambda v: setattr(self._canvas, '_brush_size', v))
        self._radius_slider.valueChanged.connect(
            lambda v: setattr(self._canvas, '_stroke_radius', v))
        self._eraser_btn.toggled.connect(
            lambda v: setattr(self._canvas, '_eraser', v))

    def _pick_color(self):
        c = QColorDialog.getColor(self._canvas._brush_color, self, "Brush Color")
        if c.isValid():
            self._canvas._brush_color = c
            self._canvas._eraser = False
            self._eraser_btn.setChecked(False)
            self._color_btn.setStyleSheet(
                f"background:{c.name()}; border:1px solid #555;")

    def _pick_bg(self):
        c = QColorDialog.getColor(self._canvas._bg_color, self, "Background Color")
        if c.isValid():
            self._canvas._bg_color = c
            self._canvas.update()
            self._bg_btn.setStyleSheet(
                f"background:{c.name()}; border:1px solid #555;")

    def get_pixmap(self):        return self._canvas.get_pixmap()
    def get_brush_color(self):   return self._canvas._brush_color
    def get_brush_size(self):    return self._size_slider.value()
    def get_stroke_radius(self): return self._radius_slider.value()
    def get_bg_color(self):      return self._canvas._bg_color

    def closeEvent(self, event):
        """Closing the window is treated as Done — paint is always saved."""
        self.accept()
        event.accept()


# =========================================================
# INLINE PAINT VIEWER
# =========================================================

# =========================================================
# INLINE PAINT VIEWER
# =========================================================

class _RoundedPaintLabel(QWidget):
    """Custom widget that paints a pixmap with rounded corners."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._radius = 12

    def set_pixmap(self, pix, radius):
        self._pixmap = pix
        self._radius = radius
        self.update()

    def paintEvent(self, e):
        if self._pixmap is None:
            return
        from PyQt6.QtGui import QPainterPath
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), self._radius, self._radius)
        painter.setClipPath(path)
        scaled = self._pixmap.scaled(self.size(),
                                     Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
        x = (self.width()  - scaled.width())  // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)


class InlinePaintViewer:
    MAX_W    = 640
    _RADIUS  = 12   # corner radius in scene units

    def __init__(self, view, node):
        self._view = view
        self._node = node
        pix = node._paint_pixmap
        if pix is not None and not pix.isNull():
            w = min(pix.width(), self.MAX_W)
            h = int(pix.height() * w / pix.width()) if pix.width() > 0 else w
        else:
            w, h = self.MAX_W, int(self.MAX_W * 3 / 4)
        self._native_w = w
        self._native_h = h

        self._container = _RoundedPaintLabel(view.viewport())
        self._container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._container.show()
        self._container.raise_()
        self.reposition()

    def reposition(self):
        scale = self._view.transform().m11()
        pix   = self._node._paint_pixmap
        if pix is not None and not pix.isNull():
            w = min(pix.width(), self.MAX_W)
            h = int(pix.height() * w / pix.width()) if pix.width() > 0 else w
            self._native_w, self._native_h = w, h

        w = max(40, int(self._native_w * scale))
        h = max(30, int(self._native_h * scale))
        radius = max(2, int(self._RADIUS * scale))

        self._container.setFixedSize(w, h)
        self._container.set_pixmap(pix, radius)

        scene_pt = self._node.mapToScene(QPointF(0, self._node.height))
        vp_pt    = self._view.mapFromScene(scene_pt)
        self._container.move(vp_pt.x(), vp_pt.y())

    def close(self):
        self._container.hide()
        self._container.deleteLater()


# =========================================================
# PAINT NODE  –  subclass of Node
# =========================================================

from node import Node, _svg_to_pixmap, NODE_SHAPES, NODE_SHAPE_LABELS
from utils import _menu_style, _global_point
from PyQt6.QtWidgets import QGraphicsItem


class PaintNode(Node):
    _node_type = "paint"

    _PNG_PAINT_BLACK = None
    _PNG_PAINT_WHITE = None

    @classmethod
    def _get_paint_renderers(cls):
        if cls._PNG_PAINT_BLACK is None:
            _base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
            cls._PNG_PAINT_BLACK = _svg_to_pixmap(os.path.join(_base, "paint_black.svg"))
            cls._PNG_PAINT_WHITE = _svg_to_pixmap(os.path.join(_base, "paint_white.svg"))
        return cls._PNG_PAINT_BLACK, cls._PNG_PAINT_WHITE

    def __init__(self, x=0, y=0, view=None, name="Paint"):
        super().__init__(x, y, view, name)
        self._node_type     = "paint"
        self._brush_color   = QColor("#000000")
        self._brush_size    = 8
        self._stroke_radius = 4
        self._bg_color      = QColor("#808080")
        self._paint_pixmap  = None
        self._inline_viewer = None

    def _draw_text_icon(self, painter):
        black_px, white_px = self._get_paint_renderers()
        px = white_px if (self._paint_pixmap is not None and not self._paint_pixmap.isNull()) \
             else black_px
        if px.isNull():
            return
        icon_size = 56
        ox = self.out_socket.pos().x()
        ty = self.title.pos().y()
        th = self.title.boundingRect().height()
        x  = int(ox - 10 - icon_size)
        y  = int(ty + th / 2 - icon_size / 2)
        painter.save()
        painter.drawPixmap(x, y,
                           px.scaled(icon_size, icon_size,
                                     Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation))
        painter.restore()

    def itemChange(self, change, value):
        result = super().itemChange(change, value)
        if (change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged
                and self._inline_viewer):
            self._inline_viewer.reposition()
        return result

    def open_inline_viewer(self):
        if self._inline_viewer is not None:
            self.close_inline_viewer()
        view = self.scene().views()[0] if self.scene() and self.scene().views() else None
        if view:
            self._inline_viewer = InlinePaintViewer(view, self)

    def close_inline_viewer(self):
        if self._inline_viewer is not None:
            self._inline_viewer.close()
            self._inline_viewer = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            self._open_paint_dialog()
            return
        super().mouseDoubleClickEvent(event)

    def _open_paint_dialog(self):
        view = self.scene().views()[0] if self.scene() and self.scene().views() else None
        if not view:
            return
        dlg = PaintDialog(view, self)
        if dlg.exec():
            self._paint_pixmap  = dlg.get_pixmap()
            self._brush_color   = dlg.get_brush_color()
            self._brush_size    = dlg.get_brush_size()
            self._stroke_radius = dlg.get_stroke_radius()
            self._bg_color      = dlg.get_bg_color()
            self.update()
            if self._inline_viewer:
                self._inline_viewer.reposition()
            if self.scene():
                self.scene().mark_dirty()

    def contextMenuEvent(self, event):
        view = self.scene().views()[0] if self.scene() and self.scene().views() else None
        if not view:
            return
        menu = QMenu(view)
        menu.setStyleSheet(_menu_style())

        orient_menu = menu.addMenu("Edit Orientation")
        for o, label in {"left-right": "Left → Right", "right-left": "Right → Left",
                         "top-bottom": "Top → Bottom", "bottom-top": "Bottom → Top"}.items():
            orient_menu.addAction(label).triggered.connect(
                lambda checked, ov=o: self._set_orientation(ov))

        shape_menu = menu.addMenu("Edit Shape")
        for s in NODE_SHAPES:
            shape_menu.addAction(NODE_SHAPE_LABELS.get(s, s.capitalize())).triggered.connect(
                lambda checked, sh=s: self._set_shape(sh))

        menu.addSeparator()

        menu.addAction("Edit Node Color").triggered.connect(lambda: self._pick_color(view))
        menu.addAction("Edit Font Size").triggered.connect(lambda: self._change_font(view))
        menu.addAction("Edit Font Color").triggered.connect(lambda: self._pick_font_color(view))

        event.accept()
        menu.exec(_global_point(event.screenPos()))

    def _edit_name(self, view):
        from utils import RichTextEditDialog
        dlg = RichTextEditDialog(view, self.title._plain, self.title._html,
                                 initial_font_size=self._font_size)
        if dlg.exec():
            self.title._plain = dlg.get_name()
            self.title._html  = dlg.get_html()
            self.title.setPlainText(self.title._plain)
            self._font_size = dlg.get_font_size()
            self.title.set_font_size(self._font_size)
            self._fit_to_text()
            if self.scene():
                self.scene().mark_dirty()

    def _clear_canvas(self):
        self._paint_pixmap = None
        self.update()
        if self._inline_viewer:
            self._inline_viewer.reposition()
        if self.scene():
            self.scene().mark_dirty()

    def update_from_settings(self, settings, force=False):
        if getattr(self, '_settings_locked', False) and not force:
            return
        if "paint_node_color" in settings and not self._color_locked:
            self._color = QColor(settings["paint_node_color"])
        if "paint_node_font_size" in settings:
            self._font_size = int(settings["paint_node_font_size"])
            self.title.set_font_size(self._font_size)
        if "paint_node_font_color" in settings:
            self._font_color = QColor(settings["paint_node_font_color"])
            self.title.set_font_color(self._font_color)
        # Shape and orientation are per-node choices, not theme properties.
        if not force:
            if "paint_node_orientation" in settings:
                self._orientation = settings["paint_node_orientation"]
            if "paint_node_shape" in settings:
                self._shape = settings["paint_node_shape"]
                self._apply_shape_size()
        self._fit_to_text()
        self._apply_orientation()
        self.update()

    def snapshot(self):
        import base64
        from PyQt6.QtCore import QBuffer, QByteArray, QIODevice
        px_b64 = ""
        if self._paint_pixmap is not None and not self._paint_pixmap.isNull():
            ba  = QByteArray()
            buf = QBuffer(ba)
            buf.open(QIODevice.OpenModeFlag.WriteOnly)
            self._paint_pixmap.save(buf, "PNG")
            px_b64 = base64.b64encode(bytes(ba)).decode()
        return {
            "type": "paint_node", "name": self.title._plain,
            "x": self.scenePos().x(), "y": self.scenePos().y(),
            "color": self._color.name(), "color_locked": self._color_locked,
            "font_size": self._font_size,
            "font_color": self._font_color.name(), "orientation": self._orientation,
            "shape": self._shape, "brush_color": self._brush_color.name(),
            "brush_size": self._brush_size, "stroke_radius": self._stroke_radius,
            "bg_color": self._bg_color.name(), "painting": px_b64,
        }

    def restore_snapshot(self, data):
        import base64
        from PyQt6.QtCore import QByteArray
        self._color         = QColor(data.get("color", "#2a2a2a"))
        self._color_locked  = data.get("color_locked", False)
        self._font_size     = data.get("font_size", 22)
        self._font_color    = QColor(data.get("font_color", "#ffffff"))
        self._orientation   = data.get("orientation", "left-right")
        self._shape         = data.get("shape", "rectangle")
        self._brush_color   = QColor(data.get("brush_color", "#000000"))
        self._brush_size    = data.get("brush_size", 8)
        self._stroke_radius = data.get("stroke_radius", 4)
        self._bg_color      = QColor(data.get("bg_color", "#808080"))
        self.title._plain   = data.get("name", "Paint")
        self.title.setPlainText(self.title._plain)
        self.title.set_font_size(self._font_size)
        self.title.set_font_color(self._font_color)
        px_b64 = data.get("painting", "")
        if px_b64:
            pix = QPixmap()
            pix.loadFromData(QByteArray(base64.b64decode(px_b64)), "PNG")
            self._paint_pixmap = pix if not pix.isNull() else None
        self._fit_to_text()
        self.update()
