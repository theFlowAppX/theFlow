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

# paint_on_canvas.py
# =========================================================
# CANVAS PAINTING MODE  –  Draw Annotations
# =========================================================
# Activated with Ctrl+P or Draw > Draw Annotations menu.
# Each stroke is a CanvasStroke (QGraphicsItem, z=2000).
# Strokes taper at tips like PaintNode strokes.
# Erase mode removes any stroke whose spine the cursor crosses.
# =========================================================

import os
import math
from PyQt6.QtWidgets import (
    QGraphicsItem, QWidget, QHBoxLayout, QPushButton,
    QSlider, QLabel, QColorDialog, QComboBox,
)
from PyQt6.QtGui import (
    QColor, QPen, QPainter, QPainterPath, QBrush, QCursor,
    QIcon, QPixmap,
)
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtSvg import QSvgRenderer


def _icon_from_svg(path: str, size: int = 20) -> QIcon:
    """Render an SVG file to a QIcon at the given pixel size."""
    renderer = QSvgRenderer(path)
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    renderer.render(p)
    p.end()
    return QIcon(px)


def _cursor_from_svg(path: str, size: int = 32, hot_x: int = 2, hot_y: int = 30) -> QCursor:
    """Render an SVG file to a custom QCursor."""
    renderer = QSvgRenderer(path)
    if not renderer.isValid():
        return QCursor(Qt.CursorShape.CrossCursor)
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    renderer.render(p)
    p.end()
    # Clamp hotspot to pixmap bounds
    hx = max(0, min(hot_x, size - 1))
    hy = max(0, min(hot_y, size - 1))
    return QCursor(px, hx, hy)


# =========================================================
# CANVAS STROKE
# =========================================================

class CanvasStroke(QGraphicsItem):

    Z_VALUE = 2000

    def __init__(self, color=None, thickness=6, style="solid"):
        super().__init__()
        self._color     = color or QColor("#FF8C00")
        self._thickness = thickness
        self._style     = style
        self._points    = []
        self._path      = QPainterPath()
        self._spine     = QPainterPath()   # centre-line for erase hit-test
        self._bounds    = QRectF()

        self.setZValue(self.Z_VALUE)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def add_point(self, scene_pt: QPointF):
        self._points.append(scene_pt)
        self.prepareGeometryChange()
        self._rebuild()
        self.update()

    def finalise(self):
        self.prepareGeometryChange()
        self._rebuild()
        self.update()

    # ── Taper ────────────────────────────────────────────────────────

    def _taper(self, i: int, n: int) -> float:
        if n <= 1:
            return 1.0
        t = i / (n - 1)
        ramp = 0.12
        if t < ramp:
            return t / ramp
        if t > 1.0 - ramp:
            return (1.0 - t) / ramp
        return 1.0

    # ── Path rebuild ─────────────────────────────────────────────────

    def _rebuild(self):
        pts = self._points
        n   = len(pts)

        # Spine (centre-line) — used for erase intersection test
        spine = QPainterPath()
        if n >= 2:
            spine.moveTo(pts[0])
            for pt in pts[1:]:
                spine.lineTo(pt)
        self._spine = spine

        if n < 2:
            if n == 1:
                r = self._thickness * 0.3
                self._bounds = QRectF(
                    pts[0].x() - r, pts[0].y() - r, r * 2, r * 2)
            self._path = QPainterPath()
            return

        half  = self._thickness / 2.0
        left  = []
        right = []

        for i in range(n - 1):
            p1  = pts[i]
            p2  = pts[i + 1]
            dx  = p2.x() - p1.x()
            dy  = p2.y() - p1.y()
            seg = math.hypot(dx, dy)
            if seg < 1e-6:
                if left:
                    left.append(left[-1])
                    right.append(right[-1])
                continue
            nx  = -dy / seg
            ny  =  dx / seg
            w1  = half * self._taper(i,     n)
            w2  = half * self._taper(i + 1, n)
            left.append( QPointF(p1.x() + nx * w1, p1.y() + ny * w1))
            right.append(QPointF(p1.x() - nx * w1, p1.y() - ny * w1))
            if i == n - 2:
                left.append( QPointF(p2.x() + nx * w2, p2.y() + ny * w2))
                right.append(QPointF(p2.x() - nx * w2, p2.y() - ny * w2))

        if not left:
            self._path = QPainterPath()
            return

        path = QPainterPath()
        path.setFillRule(Qt.FillRule.WindingFill)
        path.moveTo(left[0])
        for pt in left[1:]:
            path.lineTo(pt)
        for pt in reversed(right):
            path.lineTo(pt)
        path.closeSubpath()

        self._path   = path
        self._bounds = path.boundingRect().adjusted(-2, -2, 2, 2)

    # ── QGraphicsItem ────────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        return self._bounds if not self._bounds.isNull() else QRectF(-1, -1, 2, 2)

    def shape(self):
        return self._path

    def spine_path(self) -> QPainterPath:
        return self._spine

    def paint(self, painter, option, widget):
        if self._path.isEmpty() and len(self._points) < 2:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self._color)

        if self.isSelected():
            glow = QPen(QColor(80, 160, 255, 80), self._thickness + 6)
            glow.setCapStyle(Qt.PenCapStyle.RoundCap)
            glow.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(glow)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(self._path)

        if self._style == "solid" and not self._path.isEmpty():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawPath(self._path)
        else:
            pen = QPen(color, self._thickness)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            if self._style == "dashed":
                pen.setDashPattern([4, 3])
            elif self._style == "dotted":
                pen.setDashPattern([1, 2.5])
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            spine = QPainterPath()
            if self._points:
                spine.moveTo(self._points[0])
                for pt in self._points[1:]:
                    spine.lineTo(pt)
            painter.drawPath(spine)


# =========================================================
# STROKE TOOLBAR
# =========================================================

class StrokeToolbar(QWidget):

    def __init__(self, painter: "CanvasPainter", parent=None):
        super().__init__(parent)
        self._painter      = painter
        self._drag_start   = None
        self._drag_orig    = None
        self._mode_before_drag = None   # restored after drag

        self.setWindowFlags(Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet(
            "StrokeToolbar { background:#1e1e1e; border:1px solid #555;"
            " border-radius:8px; }"
            "QPushButton { background:#2a2a2a; color:#ffffff; border:none;"
            " border-radius:4px; font-size:13px; font-weight:bold;"
            " min-width:32px; min-height:28px; padding:0 6px; }"
            "QPushButton:hover { background:#444; }"
            "QPushButton:checked { background:#555555; color:#ffffff; }"
            "QLabel { color:#aaa; font-size:11px; }"
            "QComboBox { background:#2a2a2a; color:#ffffff; border:1px solid #555;"
            " border-radius:4px; padding:2px 6px; min-height:26px; }"
            "QComboBox:hover { border-color:#888; }"
            "QComboBox QAbstractItemView { background:#2a2a2a; color:#ffffff;"
            " selection-background-color:#555555; selection-color:#ffffff; }"
            "QSlider::groove:horizontal { height:4px; background:#444;"
            " border-radius:2px; }"
            "QSlider::handle:horizontal { width:12px; height:12px;"
            " margin:-4px 0; background:#fff; border-radius:6px; }"
            "QSlider::sub-page:horizontal { background:#888888;"
            " border-radius:2px; }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(6)

        # Title / drag handle
        self._title = QLabel("Annotations")
        self._title.setStyleSheet(
            "color:#ffffff; font-weight:bold; font-size:12px;")
        self._title.setCursor(Qt.CursorShape.SizeAllCursor)
        layout.addWidget(self._title)

        layout.addSpacing(4)

        # Icon paths — live in /icons next to the app
        _base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
        _pencil_path = os.path.join(_base, "pencil.svg")
        _eraser_path = os.path.join(_base, "eraser.svg")

        # Draw — pencil icon
        self._draw_btn = QPushButton()
        self._draw_btn.setCheckable(True)
        self._draw_btn.setChecked(True)
        self._draw_btn.setFixedSize(32, 32)
        self._draw_btn.setToolTip("Draw")
        if os.path.exists(_pencil_path):
            self._draw_btn.setIcon(_icon_from_svg(_pencil_path, 18))
        else:
            self._draw_btn.setText("D")
        self._draw_btn.clicked.connect(self._on_draw)
        layout.addWidget(self._draw_btn)

        # Erase — eraser icon
        self._erase_btn = QPushButton()
        self._erase_btn.setCheckable(True)
        self._erase_btn.setFixedSize(32, 32)
        self._erase_btn.setToolTip("Erase")
        if os.path.exists(_eraser_path):
            self._erase_btn.setIcon(_icon_from_svg(_eraser_path, 18))
        else:
            self._erase_btn.setText("E")
        self._erase_btn.clicked.connect(self._on_erase)
        layout.addWidget(self._erase_btn)

        # Store paths for cursor creation later
        self._pencil_path = _pencil_path
        self._eraser_path = _eraser_path

        layout.addSpacing(4)

        # Color — clickable swatch (no C label)
        self._color_swatch = QPushButton()
        self._color_swatch.setFixedSize(28, 28)
        self._color_swatch.setToolTip("Pick color")
        self._color_swatch.setStyleSheet(
            f"QPushButton {{ background:{painter.color.name()};"
            f" border:2px solid #666; border-radius:4px; }}"
            f"QPushButton:hover {{ border-color:#aaa; }}")
        self._color_swatch.clicked.connect(self._on_color)
        layout.addWidget(self._color_swatch)

        layout.addSpacing(4)

        # Thickness slider — no label
        self._thick_slider = QSlider(Qt.Orientation.Horizontal)
        self._thick_slider.setRange(1, 40)
        self._thick_slider.setValue(painter.thickness)
        self._thick_slider.setFixedWidth(72)
        self._thick_slider.setToolTip("Thickness")
        self._thick_slider.valueChanged.connect(self._on_thickness)
        layout.addWidget(self._thick_slider)

        layout.addSpacing(4)

        # Style dropdown — symbols only, no text
        self._style_combo = QComboBox()
        self._style_combo.addItems(["——", "- -", "···"])
        self._style_combo.setCurrentIndex(0)
        self._style_combo.setToolTip("Stroke style")
        self._style_combo.setFixedWidth(56)
        self._style_combo.currentIndexChanged.connect(self._on_style_index)
        layout.addWidget(self._style_combo)

        layout.addSpacing(6)

        # Clear all annotations
        clear_btn = QPushButton("Clear")
        clear_btn.setToolTip("Clear all annotations")
        clear_btn.clicked.connect(self._on_clear)
        layout.addWidget(clear_btn)

        layout.addSpacing(4)

        # Close
        close_btn = QPushButton("Close")
        close_btn.setToolTip("Close annotations (Ctrl+P)")
        close_btn.clicked.connect(self._painter._view._toggle_canvas_paint)
        layout.addWidget(close_btn)

        self.adjustSize()

        for child in self.findChildren(QWidget):
            child.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    # ── Drag — only from title label, disable tool while moving ──────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Only start drag if click is within the title label bounds
            title_rect = self._title.geometry()
            if title_rect.contains(event.pos()):
                self._drag_start        = event.globalPosition().toPoint()
                self._drag_orig         = self.pos()
                self._mode_before_drag  = self._painter.mode
                self._painter.mode      = None
                self._painter._update_cursor()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start is not None:
            delta = event.globalPosition().toPoint() - self._drag_start
            self.move(self._drag_orig + delta)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag_start is not None:
            self._drag_start = None
            if self._mode_before_drag is not None:
                self._painter.mode = self._mode_before_drag
                self._mode_before_drag = None
                self._painter._update_cursor()
        super().mouseReleaseEvent(event)

    # ── Button handlers ───────────────────────────────────────────────

    def _on_draw(self):
        self._draw_btn.setChecked(True)
        self._erase_btn.setChecked(False)
        self._painter.mode = "draw"
        self._painter._update_cursor()

    def _on_erase(self):
        self._erase_btn.setChecked(True)
        self._draw_btn.setChecked(False)
        self._painter.mode = "erase"
        self._painter._update_cursor()

    def _on_color(self):
        c = QColorDialog.getColor(
            self._painter.color, None, "Annotation Color",
            QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            self._painter.color = c
            self._color_swatch.setStyleSheet(
                f"QPushButton {{ background:{c.name()};"
                f" border:2px solid #666; border-radius:4px; }}"
                f"QPushButton:hover {{ border-color:#aaa; }}")

    def _on_thickness(self, v):
        self._painter.thickness = v

    def _on_style_index(self, idx):
        styles = ["solid", "dashed", "dotted"]
        self._painter.style = styles[idx]

    def _on_clear(self):
        self._painter.clear_all_strokes()

    def set_style(self, style: str):
        """Sync combo from keyboard shortcut."""
        styles = ["solid", "dashed", "dotted"]
        if style in styles:
            self._style_combo.setCurrentIndex(styles.index(style))

    def keyPressEvent(self, event):
        self._painter._view.keyPressEvent(event)

    def wheelEvent(self, event):
        self._painter._view.wheelEvent(event)


# =========================================================
# GEOMETRY HELPER
# =========================================================

def _pt_seg_dist2(p: QPointF, a: QPointF, b: QPointF) -> float:
    """Squared distance from point p to segment a–b."""
    dx = b.x() - a.x()
    dy = b.y() - a.y()
    len2 = dx * dx + dy * dy
    if len2 < 1e-12:
        ex = p.x() - a.x()
        ey = p.y() - a.y()
        return ex * ex + ey * ey
    t = max(0.0, min(1.0, ((p.x() - a.x()) * dx + (p.y() - a.y()) * dy) / len2))
    cx = a.x() + t * dx - p.x()
    cy = a.y() + t * dy - p.y()
    return cx * cx + cy * cy


# =========================================================
# CANVAS PAINTER
# =========================================================

class CanvasPainter:

    def __init__(self, view):
        self._view      = view
        self._active    = False
        self._toolbar   = None
        self._stroke    = None
        self._prev_drag = view.dragMode()

        self.color     = QColor("#FF8C00")
        self.thickness = 6
        self.style     = "solid"
        self.mode      = "draw"

    # ── Toggle ───────────────────────────────────────────────────────

    def toggle(self):
        if self._active:
            self._deactivate()
        else:
            self._activate()

    def is_active(self) -> bool:
        return self._active

    def _activate(self):
        self._active = True
        from PyQt6.QtWidgets import QGraphicsView
        self._prev_drag = self._view.dragMode()
        self._view.setDragMode(QGraphicsView.DragMode.NoDrag)
        # setInteractive(False) stops the scene from processing mouse events
        # internally (selection changes, item hovers) that can trigger logo fade
        self._view.setInteractive(False)

        vp = self._view.viewport()
        vp_off = vp.pos()
        self._toolbar = StrokeToolbar(self, self._view)
        self._toolbar.move(vp_off.x() + 16, vp_off.y() + 16)
        self._toolbar.show()
        self._toolbar.raise_()
        self._update_cursor()

    def _deactivate(self):
        self._active = False
        self._view.setInteractive(True)
        if self._toolbar:
            self._toolbar.hide()
            self._toolbar.deleteLater()
            self._toolbar = None
        if self._stroke:
            if self._stroke.scene():
                self._stroke.scene().removeItem(self._stroke)
            self._stroke = None
        from PyQt6.QtWidgets import QGraphicsView
        self._view.setDragMode(self._prev_drag)
        self._view.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        self._view.setCursor(Qt.CursorShape.ArrowCursor)

    def _update_cursor(self):
        if not self._active:
            return
        tb = self._toolbar

        if self.mode == "draw":
            if tb and os.path.exists(tb._pencil_path):
                cur = _cursor_from_svg(tb._pencil_path, 32, 2, 30)
            else:
                cur = QCursor(Qt.CursorShape.CrossCursor)
        elif self.mode == "erase":
            if tb and os.path.exists(tb._eraser_path):
                cur = _cursor_from_svg(tb._eraser_path, 32, 2, 30)
            else:
                cur = QCursor(Qt.CursorShape.ForbiddenCursor)
        else:
            cur = QCursor(Qt.CursorShape.SizeAllCursor)

        self._view.viewport().setCursor(cur)
        self._view.setCursor(cur)

    # ── Mouse event handlers ──────────────────────────────────────────

    def mouse_press(self, event) -> bool:
        if not self._active or self.mode is None:
            return False
        if event.button() != Qt.MouseButton.LeftButton:
            return False

        scene_pt = self._view.mapToScene(event.pos())

        if self.mode == "erase":
            self._erase_at(scene_pt)
            return True

        self._stroke = CanvasStroke(
            color=QColor(self.color),
            thickness=self.thickness,
            style=self.style,
        )
        self._stroke.add_point(scene_pt)
        self._view.scene().addItem(self._stroke)
        if hasattr(self._view, '_check_logo_fade'):
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, self._view._check_logo_fade)
        return True

    def mouse_move(self, event) -> bool:
        if not self._active or self.mode is None:
            return False
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return False

        scene_pt = self._view.mapToScene(event.pos())

        if self.mode == "erase":
            self._erase_at(scene_pt)
            return True

        if self._stroke is not None:
            self._stroke.add_point(scene_pt)
        return True

    def mouse_release(self, event) -> bool:
        if not self._active:
            return False
        if event.button() != Qt.MouseButton.LeftButton:
            return False
        if self._stroke is not None:
            self._stroke.finalise()
            finished = self._stroke
            self._stroke = None
            # Register as undoable action
            scene = self._view.scene()
            if hasattr(scene, '_push_undo'):
                scene._push_undo({"type": "add_stroke", "stroke": finished})
        return True

    def delete_selected_strokes(self) -> bool:
        scene = self._view.scene()
        strokes = [i for i in scene.selectedItems()
                   if isinstance(i, CanvasStroke)]
        if not strokes:
            return False
        for s in strokes:
            scene.removeItem(s)
            if hasattr(scene, '_push_undo'):
                scene._push_undo({"type": "del_stroke", "stroke": s})
        if hasattr(self._view, '_check_logo_fade'):
            self._view._check_logo_fade()
        return True

    def clear_all_strokes(self):
        """Remove every CanvasStroke from the scene — undoable as one action."""
        scene = self._view.scene()
        strokes = [i for i in scene.items() if isinstance(i, CanvasStroke)]
        if not strokes:
            return
        for s in strokes:
            scene.removeItem(s)
        if hasattr(scene, '_push_undo'):
            scene._push_undo({"type": "clear_strokes", "strokes": strokes})
        if hasattr(self._view, '_check_logo_fade'):
            self._view._check_logo_fade()

    # ── Erase — robust segment-distance hit test ──────────────────────

    def _erase_at(self, scene_pt: QPointF):
        """Erase any CanvasStroke whose spine comes within the eraser radius
        of scene_pt. Uses segment-distance geometry so thin lines are reliably
        hit even when the filled path is narrow."""
        scale  = self._view.transform().m11()
        # 12 screen pixels → scene units
        radius = max(6.0, 12.0 / scale)
        r2     = radius * radius

        scene = self._view.scene()

        # Broad-phase: only test strokes whose bounding rect is nearby
        search = QRectF(
            scene_pt.x() - radius, scene_pt.y() - radius,
            radius * 2, radius * 2)

        for item in list(scene.items(search)):
            if not isinstance(item, CanvasStroke):
                continue
            pts = item._points
            if not pts:
                continue
            # Single-point stroke
            if len(pts) == 1:
                dx = pts[0].x() - scene_pt.x()
                dy = pts[0].y() - scene_pt.y()
                if dx * dx + dy * dy <= r2:
                    scene.removeItem(item)
                    if hasattr(scene, '_push_undo'):
                        scene._push_undo({"type": "del_stroke", "stroke": item})
                continue
            # Check each segment
            hit = False
            for i in range(len(pts) - 1):
                if _pt_seg_dist2(scene_pt, pts[i], pts[i + 1]) <= r2:
                    hit = True
                    break
            if hit:
                scene.removeItem(item)
                if hasattr(scene, '_push_undo'):
                    scene._push_undo({"type": "del_stroke", "stroke": item})
        if hasattr(self._view, '_check_logo_fade'):
            self._view._check_logo_fade()

    # ── Keyboard shortcuts ────────────────────────────────────────────

    def key_press(self, event) -> bool:
        return False
