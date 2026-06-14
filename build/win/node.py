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
# NODE
# =========================================================

# =================================================================
# ✏️  EDIT THESE VALUES TO MOVE NAME / ICON FOR EACH SHAPE (pixels)
#    NAME_X_OFF / NAME_Y_OFF : name label offset from auto position
#    ICON_X_OFF / ICON_Y_OFF : icon offset from auto position
# =================================================================
NAME_X_OFF = {"rectangle": 0, "circle": 20, "ellipse": 0, "diamond": 0, "triangle": 0, "hexagon": 0}
NAME_Y_OFF = {"rectangle": 0, "circle": 100, "ellipse": 0, "diamond": 0, "triangle": 0, "hexagon": 0}
ICON_X_OFF = {"rectangle": 0, "circle": 0, "ellipse": 0, "diamond": 0, "triangle": 0, "hexagon": 0}
ICON_Y_OFF = {"rectangle": 0, "circle": 0, "ellipse": 0, "diamond": 0, "triangle": 0, "hexagon": 0}
# =================================================================

import os
import math
import struct

from PyQt6.QtWidgets import (
    QGraphicsTextItem, QGraphicsItem, QMenu, QInputDialog,
    QDialog, QColorDialog, QPushButton, QSlider, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel,
)
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtGui import QColor, QPen, QBrush, QPainter, QFont, QPainterPath, QPolygonF, QPixmap
from PyQt6.QtCore import Qt, QRectF, QPointF, QObject

from curve import Socket, ConnectionLine
from utils import (
    NODE_BG, NODE_BORDER, CORNER_RADIUS, SOCKET_SIZE,
    RichTextEditDialog, _menu_style, _global_point,
    open_color_wheel, _diamond_poly, _remove_from,
    suppress_media_stderr,
)


NODE_SHAPES = ["rectangle", "circle", "diamond", "triangle", "ellipse", "hexagon"]

# Shape display labels for the menu
NODE_SHAPE_LABELS = {
    "rectangle": "Square",
    "circle":    "Circle",
    "diamond":   "Diamond",
    "triangle":  "Triangle (down)",
    "ellipse":   "Ellipse",
    "hexagon":   "Hexagon",
}

# orientation → (in_pos_func, out_pos_func) called with (width, height)
# returns (x, y) relative to node origin
def _node_socket_positions(orientation, width, height):
    """Return (in_xy, out_xy) for a given orientation string."""
    if orientation == "left-right":
        return (0, height / 2), (width, height / 2)
    elif orientation == "right-left":
        return (width, height / 2), (0, height / 2)
    elif orientation == "top-bottom":
        return (width / 2, 0), (width / 2, height)
    elif orientation == "bottom-top":
        return (width / 2, height), (width / 2, 0)
    else:
        return (0, height / 2), (width, height / 2)


# =========================================================
# EDITABLE TITLE  (name field – single click inline edit)
# =========================================================

class EditableTitle(QGraphicsTextItem):

    def __init__(self, text="Text", view=None, parent=None,
                 color="#ffffff", font_size=40, bold=True):
        super().__init__(text, parent)
        self.view       = view
        self._font_size = font_size
        self._bold      = bold
        self._html      = ""          # body text (rich text editor)
        self._plain     = text        # name field value
        self._font_color = QColor(color)
        self.setDefaultTextColor(self._font_color)
        self._apply_font()
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

    def _apply_font(self):
        w = QFont.Weight.Bold if self._bold else QFont.Weight.Normal
        self.setFont(QFont("Arial", self._font_size, w))

    def set_font_size(self, sz):
        self._font_size = sz
        self._apply_font()

    def set_font_color(self, color: QColor):
        self._font_color = color
        self.setDefaultTextColor(color)

    # Single click and double-click pass through to the parent node.
    # Name editing is handled exclusively via the rich text dialog
    # (double-click on the node body → RichTextEditDialog).
    def mousePressEvent(self, event):
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        # Propagate to parent node so the rich text dialog opens
        if self.parentItem():
            self.parentItem().mouseDoubleClickEvent(event)
        else:
            super().mouseDoubleClickEvent(event)


# =========================================================
# NODE
# =========================================================

def _svg_to_pixmap(path, size=256):
    """Render an SVG file to a transparent QPixmap at the given size."""
    from PyQt6.QtGui import QPainter
    from PyQt6.QtCore import QRectF
    renderer = QSvgRenderer(path)
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    if renderer.isValid():
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(p, QRectF(0, 0, size, size))
        p.end()
    return pix


_VOL_ICON_PIX = None

def _vol_icon_label(size=20):
    """Return a QLabel showing audio_white.svg at the given pixel size."""
    from PyQt6.QtWidgets import QLabel
    global _VOL_ICON_PIX
    if _VOL_ICON_PIX is None:
        _base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
        _VOL_ICON_PIX = _svg_to_pixmap(os.path.join(_base, "audio_white.svg"), 64)
    lbl = QLabel()
    lbl.setPixmap(_VOL_ICON_PIX.scaled(size, size,
                                        Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation))
    lbl.setFixedSize(size, size)
    return lbl


class Node(QGraphicsItem):

    def __init__(self, x=0, y=0, view=None, name="Text"):
        super().__init__()
        self.width       = 240
        self.height      = 90
        self.view        = view
        self._shape      = "rectangle"
        self._color      = QColor(NODE_BG)
        self._font_size  = 22
        self._font_color = QColor("#ffffff")
        self._orientation = "left-right"
        self._node_type  = "text"   # overridden by subclasses
        self._color_locked = False  # True once user picks a custom color
        # Canonical rectangle dimensions — always preserved so switching
        # shapes back and forth never compounds size changes.
        self._base_w = self.width
        self._base_h = self.height
        self.setPos(x, y)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable      |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable   |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges      |
            QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges
        )
        self.setZValue(0)

        self.title = EditableTitle(name, view, self,
                                   font_size=self._font_size)
        self.title.setPos(20, 14)

        self.in_socket  = Socket(self, True)
        self.out_socket = Socket(self, False)
        self._apply_orientation()
        self._fit_to_text()   # size node to fit name + icon from the start
        self._inline_text_viewer = None   # InlineTextViewer instance or None
        self._settings_locked = False     # True after load — prevents settings overwrite

        # ── LIVE UPDATE SETTINGS HOOK ────────────────────────────────────
    def update_from_settings(self, settings, force=False):
        """Pulls updated custom theme definitions instantly from settings UI.
        Skipped for nodes loaded from file (_settings_locked=True) unless force=True.
        Shape and orientation are node-specific — never overwritten by a theme switch."""
        if self._settings_locked and not force:
            return
        prefix = getattr(self, "_node_type", "text")

        # Dot uses flat keys (dot_color) while all other nodes use _node_ infix
        if prefix == "dot":
            color_key = "dot_color"
            fs_key    = "dot_font_size"
            fc_key    = "dot_font_color"
            sh_key    = "dot_shape"
            or_key    = "dot_orientation"
        else:
            color_key = f"{prefix}_node_color"
            fs_key    = f"{prefix}_node_font_size"
            fc_key    = f"{prefix}_node_font_color"
            sh_key    = f"{prefix}_node_shape"
            or_key    = f"{prefix}_node_orientation"

        if color_key in settings and not self._color_locked:
            self._color = QColor(settings[color_key])
        if fs_key in settings:
            self._font_size = int(settings[fs_key])
            self.title.set_font_size(self._font_size)
        if fc_key in settings:
            self._font_color = QColor(settings[fc_key])
            self.title.set_font_color(self._font_color)

        # Shape and orientation are per-node choices, not theme properties.
        # Only apply them when initialising a brand-new node (not force).
        if not force:
            if sh_key in settings:
                self._shape = settings[sh_key]
                self._apply_shape_size()
            if or_key in settings:
                self._orientation = settings[or_key]

        self._fit_to_text()
        self.update()

    def _apply_orientation(self):
        """Place sockets on the actual visible edge of the shape for the current orientation."""
        import math as _m
        w, h  = self.width, self.height
        cx, cy = w / 2, h / 2
        ori   = self._orientation

        if self._shape == "circle":
            # Radius = half the side (bounding box is square after _apply_shape_size)
            r = h / 2
            if ori == "left-right":
                in_pos, out_pos = (cx - r, cy), (cx + r, cy)
            elif ori == "right-left":
                in_pos, out_pos = (cx + r, cy), (cx - r, cy)
            elif ori == "top-bottom":
                in_pos, out_pos = (cx, cy - r), (cx, cy + r)
            else:  # bottom-top
                in_pos, out_pos = (cx, cy + r), (cx, cy - r)

        elif self._shape == "ellipse":
            rx = w / 2
            ry = h / 2
            if ori == "left-right":
                in_pos, out_pos = (cx - rx, cy), (cx + rx, cy)
            elif ori == "right-left":
                in_pos, out_pos = (cx + rx, cy), (cx - rx, cy)
            elif ori == "top-bottom":
                in_pos, out_pos = (cx, cy - ry), (cx, cy + ry)
            else:  # bottom-top
                in_pos, out_pos = (cx, cy + ry), (cx, cy - ry)

        elif self._shape == "diamond":
            # Diamond tips: top=(cx,0), right=(w,cy), bottom=(cx,h), left=(0,cy)
            if ori == "left-right":
                in_pos, out_pos = (0, cy), (w, cy)
            elif ori == "right-left":
                in_pos, out_pos = (w, cy), (0, cy)
            elif ori == "top-bottom":
                in_pos, out_pos = (cx, 0), (cx, h)
            else:  # bottom-top
                in_pos, out_pos = (cx, h), (cx, 0)

        elif self._shape == "triangle":
            # Downward triangle: top-left=(0,0), top-right=(w,0), bottom=(cx,h)
            if ori == "left-right":
                in_pos, out_pos = (0, 0), (w, 0)
            elif ori == "right-left":
                in_pos, out_pos = (w, 0), (0, 0)
            elif ori == "top-bottom":
                in_pos, out_pos = (cx, 0), (cx, h)
            else:  # bottom-top
                in_pos, out_pos = (cx, h), (cx, 0)

        elif self._shape == "hexagon":
            # Flat-top hex: left mid=(0,cy), right mid=(w,cy), top-cx=(cx,0), bot-cx=(cx,h)
            if ori == "left-right":
                in_pos, out_pos = (0, cy), (w, cy)
            elif ori == "right-left":
                in_pos, out_pos = (w, cy), (0, cy)
            elif ori == "top-bottom":
                in_pos, out_pos = (cx, 0), (cx, h)
            else:  # bottom-top
                in_pos, out_pos = (cx, h), (cx, 0)

        else:  # rectangle — use generic helper
            in_pos, out_pos = _node_socket_positions(ori, w, h)

        self.in_socket.setPos(*in_pos)
        self.out_socket.setPos(*out_pos)
        self.in_socket.update_connections()
        self.out_socket.update_connections()

    # ── auto-size ──────────────────────────────────────────────────────────

    _MIN_W = 240
    _MIN_H = 90

    # Icon area on the right: icon_size + gap + socket_radius + right_pad
    _ICON_W   = 56
    _ICON_GAP = 12
    _SOCK_R   = SOCKET_SIZE * 2   # 16 px
    _PAD_R    = 20
    _PAD_L    = 20
    _PAD_V    = 14

    @property
    def _icon_reserved(self):
        return self._ICON_W + self._ICON_GAP + self._SOCK_R + self._PAD_R

    def _text_inset(self):
        """Return (x, y, w, h) of the usable text area inside the current shape,
        leaving room for the icon on the right side."""
        import math
        W, H = self.width, self.height
        s = self._shape

        if s == "rectangle":
            x = self._PAD_L
            y = self._PAD_V
            w = W - self._PAD_L - self._icon_reserved
            h = H - self._PAD_V * 2

        elif s == "ellipse":
            # Inscribed rect using actual node dimensions
            rx, ry = W / 2, H / 2
            # Widest rectangle that fits: x_box = rx/√2, y_box = ry/√2
            bx = rx / math.sqrt(2)
            by = ry / math.sqrt(2)
            x = W / 2 - bx + self._PAD_L
            y = H / 2 - by + self._PAD_V
            w = 2 * bx - self._PAD_L - self._icon_reserved
            h = 2 * by - self._PAD_V * 2

        elif s == "circle":
            r = H / 2
            b = r / math.sqrt(2)
            x = W / 2 - b + self._PAD_L
            y = H / 2 - b + self._PAD_V
            w = 2 * b - self._PAD_L - self._icon_reserved
            h = 2 * b - self._PAD_V * 2

        elif s == "diamond":
            # Diamond: usable horizontal band at centre = half the full width
            hw, hh = W / 2, H / 2
            # At vertical centre ±text_h/2, the diamond width is proportional
            # Use 60% of the half-width as a safe inner zone
            safe_w = hw * 0.60
            safe_h = hh * 0.40
            x = W / 2 - safe_w + self._PAD_L
            y = H / 2 - safe_h + self._PAD_V
            w = 2 * safe_w - self._PAD_L - self._icon_reserved
            h = 2 * safe_h - self._PAD_V * 2

        elif s == "triangle":
            # Downward triangle: widest safe band is upper 1/3 (near the top edge)
            # At y_frac from top, width = W * (1 - y_frac) for a symmetric triangle
            y_frac_top = 0.10
            y_frac_bot = 0.45
            mid_frac   = (y_frac_top + y_frac_bot) / 2
            available_w = W * (1 - mid_frac) - self._PAD_L * 2
            x = W / 2 - available_w / 2 + self._PAD_L
            y = H * y_frac_top + self._PAD_V
            w = available_w - self._icon_reserved
            h = H * (y_frac_bot - y_frac_top) - self._PAD_V * 2

        elif s == "hexagon":
            # Flat-top hex: widest at mid-height, narrows by 25% at top/bottom
            x = W * 0.15 + self._PAD_L
            y = H * 0.20 + self._PAD_V
            w = W * 0.70 - self._PAD_L - self._icon_reserved
            h = H * 0.60 - self._PAD_V * 2

        else:
            x, y = self._PAD_L, self._PAD_V
            w = W - self._PAD_L - self._icon_reserved
            h = H - self._PAD_V * 2

        return x, y, max(w, 40), max(h, 20)

    def _fit_to_text(self):
        """Size node then place label and icon to match the reference layout:
        - rectangle: label inside-left at socket Y, icon right-of-centre inside
        - all others: label outside-left of input socket at socket Y, icon dead-centre
        """
        import math
        # Force unconstrained layout so boundingRect reflects the actual font/text
        self.title.setTextWidth(-1)
        self.title.document().adjustSize()
        self.title.adjustSize()
        tr     = self.title.boundingRect()
        tw, th = tr.width(), tr.height()
        s      = self._shape
        ICON   = 56   # icon size px
        GAP    = 8    # px gap between label right-edge and socket centre

        # ── 1. Minimum node size ──────────────────────────────────────────────
        if s == "rectangle":
            self._base_w = max(self._MIN_W, self._PAD_L + tw + self._icon_reserved)
            self._base_h = max(self._MIN_H, th + self._PAD_V * 2)
        elif s == "ellipse":
            self._base_w = max(self._MIN_W, ICON * 2)
            self._base_h = max(self._MIN_H, ICON + 24)
        elif s == "circle":
            d = max(ICON + 24, self._MIN_H * 2)
            self._base_h = d / 2
            self._base_w = d / 2
        elif s == "diamond":
            d = max(ICON * 2 + 40, self._MIN_W)
            self._base_w = d
            self._base_h = d
        elif s in ("triangle", "hexagon"):
            self._base_w = self._MIN_W
            self._base_h = int(self._MIN_W * math.sqrt(3) / 2)

        self._apply_shape_size()
        self._apply_orientation()

        # ── 2. Label placement ────────────────────────────────────────────────
        # Always use left/right reference positions so label & icon stay
        # consistent regardless of orientation.
        _sr = self._SOCK_R
        _cx = self.width / 2
        _cy = self.height / 2

        # Left socket centre (where in_socket is in left-right orientation)
        sx = _sr / 2
        sy = _cy - _sr / 2

        # Right socket centre (where out_socket is in left-right orientation)
        ox = self.width - _sr / 2

        if s == "rectangle":
            name_x = self._PAD_L   + 0
            name_y = sy - th / 2   + 0
        elif s == "circle":
            name_x = sx + GAP      + 10
            name_y = sy - th / 2   + 0
        elif s == "ellipse":
            name_x = sx + GAP      + 10
            name_y = sy - th / 2   + 0
        elif s == "diamond":
            name_x = sx + GAP      + 10
            name_y = sy - th / 2   + 0
        elif s == "triangle":
            name_x = sx + GAP      + 10
            name_y = sy - th / 2   - 60
        else:  # hexagon
            name_x = sx + GAP      + 10
            name_y = sy - th / 2   + 0

        self.title.setPos(name_x, name_y)

        self.update()
        if self.scene():
            self.scene().mark_dirty()

    def _apply_shape_size(self):
        """Set self.width / self.height from _base_w/_base_h for the current shape.
        Always derives from the canonical rectangle size so switching never compounds."""
        import math
        self.prepareGeometryChange()
        if self._shape == "circle":
            # Square bounding box; side = _base_h * 2 (diameter)
            side        = self._base_h * 2
            self.width  = side
            self.height = side
        elif self._shape == "diamond":
            # Square bounding box so both diagonals are equal; side = _base_w
            self.width  = self._base_w
            self.height = self._base_w
        elif self._shape in ("triangle", "hexagon"):
            # Width = _base_w; height = _base_w * √3/2 (equilateral proportions)
            self.width  = self._base_w
            self.height = int(self._base_w * math.sqrt(3) / 2)
        else:  # rectangle, ellipse — keep base dimensions
            self.width  = self._base_w
            if self._shape == "ellipse":
                # Height = 2/3 of width so the ellipse has the right proportions.
                # Stored directly so _ellipse_rect can just return the rect unchanged,
                # allowing the glow loop to expand both axes uniformly.
                self.height = max(self._MIN_H, int(self._base_w * 2 / 3))
            else:
                self.height = self._base_h

    def boundingRect(self):
        m = 20  # margin large enough to contain the full glow (10 steps × 1.5px spread)
        r = QRectF(-m, -m, self.width + m * 2, self.height + m * 2)
        # If the label is positioned outside the shape (non-rectangle shapes),
        # expand the bounding rect to include it so it gets painted and hit-tested.
        tp = self.title.pos()
        tr = self.title.boundingRect()
        label_left = tp.x() - m
        if label_left < r.left():
            r.setLeft(label_left)
        label_top = tp.y() - m
        if label_top < r.top():
            r.setTop(label_top)
        label_right = tp.x() + tr.width() + m
        if label_right > r.right():
            r.setRight(label_right)
        label_bottom = tp.y() + tr.height() + m
        if label_bottom > r.bottom():
            r.setBottom(label_bottom)
        return r

    def shape(self):
        # Return exact painted outline so hit-test and selection match the shape
        rect = QRectF(0, 0, self.width, self.height)
        path = QPainterPath()
        s = self._shape
        if s == "circle":
            path.addEllipse(self._circle_rect(rect))
        elif s == "ellipse":
            path.addEllipse(self._ellipse_rect(rect))
        elif s == "diamond":
            path = self._diamond_path(rect)
        elif s == "triangle":
            path = self._triangle_path(rect)
        elif s == "hexagon":
            path = self._hexagon_path(rect)
        else:
            path.addRoundedRect(rect, CORNER_RADIUS, CORNER_RADIUS)
        return path

    def contains(self, point):
        body = QRectF(0, 0, self.width, self.height)
        if not body.contains(point):
            return False
        cx, cy = self.width / 2, self.height / 2
        px, py = point.x(), point.y()

        if self._shape == "circle":
            # Circle centred in bounding box, radius = height/2
            r = self.height / 2
            return (px - cx) ** 2 + (py - cy) ** 2 <= r ** 2

        elif self._shape == "ellipse":
            rx = self.width  / 2
            ry = self.height / 2
            return (px - cx) ** 2 / rx ** 2 + (py - cy) ** 2 / ry ** 2 <= 1.0

        elif self._shape == "diamond":
            rx, ry = self.width / 2, self.height / 2
            return abs(px - cx) / rx + abs(py - cy) / ry <= 1.0

        elif self._shape == "triangle":
            path = self._triangle_path(QRectF(0, 0, self.width, self.height))
            return path.contains(point)

        elif self._shape == "hexagon":
            path = self._hexagon_path(QRectF(0, 0, self.width, self.height))
            return path.contains(point)

        return True  # rectangle

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update()
        if change in (QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged,
                      QGraphicsItem.GraphicsItemChange.ItemScenePositionHasChanged):
            self.in_socket.update_connections()
            self.out_socket.update_connections()
            if self.scene():
                self.scene().mark_dirty()
            if self._inline_text_viewer is not None:
                self._inline_text_viewer.reposition()
        return super().itemChange(change, value)

    def open_inline_text_viewer(self):
        if not self.scene():
            return
        view = self.scene().views()[0] if self.scene().views() else None
        if not view:
            return
        if self._inline_text_viewer is not None:
            self.close_inline_text_viewer()
        self._inline_text_viewer = InlineTextViewer(view, self)

    def close_inline_text_viewer(self):
        if self._inline_text_viewer is not None:
            self._inline_text_viewer.close()
            self._inline_text_viewer = None

    def mousePressEvent(self, event):
        # Cmd+Left Click (⌘) → disconnect all curves (merged if possible)
        if (event.button() == Qt.MouseButton.LeftButton and
                event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self._disconnect_curves()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        # issue 15+18: do NOT split while dragging; wait for release

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self._try_split_on_release()

    def _try_split_on_release(self):
        """After drag release, check if node landed on a curve and split it (issue 15).
        Skip if the node already has connections (issue 18)."""
        scene = self.scene()
        if not scene:
            return
        # issue 18: only split if both sockets are free
        if self.in_socket.connections or self.out_socket.connections:
            return
        body_rect = QRectF(0, 0, self.width, self.height)
        scene_body_rect = self.mapRectToScene(body_rect).adjusted(-15, -15, 15, 15)
        for item in scene.items(scene_body_rect):
            if isinstance(item, ConnectionLine):
                if item.a.parent_node is self or item.b.parent_node is self:
                    continue
                self._split_curve_at(item)
                break

    def _disconnect_curves(self):
        scene = self.scene()
        if not scene:
            return
        # Collect all connected curves
        in_c  = list(self.in_socket.connections)
        out_c = list(self.out_socket.connections)
        all_c = in_c + out_c
        # If exactly one in and one out, merge them
        if len(in_c) == 1 and len(out_c) == 1:
            c1, c2 = in_c[0], out_c[0]
            merged = ConnectionLine(c1.a, c2.b)
            merged.curve_type        = c1.curve_type
            merged._line_color       = c1._line_color
            merged._line_style       = c1._line_style
            merged._thickness        = c1._thickness
            merged._color_locked     = c1._color_locked
            merged._style_locked     = c1._style_locked
            merged._thickness_locked = c1._thickness_locked
            for c in (c1, c2):
                c.disconnect_from_sockets()
                scene.removeItem(c)
            scene.addItem(merged)
            merged.a.connections.append(merged)
            merged.b.connections.append(merged)
            scene._push_undo({"type": "join_curves",
                               "dot": self,   # reuse join_curves undo shape
                               "c1": c1, "c2": c2, "merged": merged})
        else:
            for conn in all_c:
                conn.disconnect_from_sockets()
                scene.removeItem(conn)
            scene.mark_dirty()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        # issue 15+18: splitting only happens on release, not during drag

    def _split_curve_at(self, curve):
        scene = self.scene()
        if not scene:
            return

        _remove_from(curve.a.connections, curve)
        _remove_from(curve.b.connections, curve)
        scene.removeItem(curve)

        c1 = ConnectionLine(curve.a, self.in_socket)
        c1.curve_type        = curve.curve_type
        c1._line_color       = curve._line_color
        c1._line_style       = curve._line_style
        c1._thickness        = curve._thickness
        c1._color_locked     = curve._color_locked
        c1._style_locked     = curve._style_locked
        c1._thickness_locked = curve._thickness_locked

        c2 = ConnectionLine(self.out_socket, curve.b)
        c2.curve_type        = curve.curve_type
        c2._line_color       = curve._line_color
        c2._line_style       = curve._line_style
        c2._thickness        = curve._thickness
        c2._color_locked     = curve._color_locked
        c2._style_locked     = curve._style_locked
        c2._thickness_locked = curve._thickness_locked

        scene.addItem(c1)
        scene.addItem(c2)

        curve.a.connections.append(c1)
        self.in_socket.connections.append(c1)

        self.out_socket.connections.append(c2)
        curve.b.connections.append(c2)

        c1.update_path()
        c2.update_path()

        scene._push_undo({
            "type": "split_curve",
            "dot": self,
            "c1": c1, "c2": c2, "original": curve,
            "orig_a": curve.a, "orig_b": curve.b,
        })

    def contextMenuEvent(self, event):
        view = (self.scene().views()[0]
                if self.scene() and self.scene().views() else None)
        if not view:
            return
        menu = QMenu(view)
        menu.setStyleSheet(_menu_style())

        # Edit Orientation (dropdown)
        orient_menu = menu.addMenu("Edit Orientation")
        _orient_labels = {
            "left-right":  "Left → Right",
            "right-left":  "Right → Left",
            "top-bottom":  "Top → Bottom",
            "bottom-top":  "Bottom → Top",
        }
        for o, label in _orient_labels.items():
            act = orient_menu.addAction(label)
            act.triggered.connect(lambda checked, ov=o: self._set_orientation(ov))

        # Edit Shape
        shape_menu = menu.addMenu("Edit Shape")
        for s in NODE_SHAPES:
            label = NODE_SHAPE_LABELS.get(s, s.capitalize())
            shape_menu.addAction(label).triggered.connect(
                lambda checked, sh=s: self._set_shape(sh))

        menu.addSeparator()

        menu.addAction("Edit Node Color").triggered.connect(
            lambda: self._pick_color(view))
        menu.addAction("Edit Font Size").triggered.connect(
            lambda: self._change_font(view))
        menu.addAction("Edit Font Color").triggered.connect(
            lambda: self._pick_font_color(view))

        event.accept()
        menu.exec(_global_point(event.screenPos()))

    def mouseDoubleClickEvent(self, event):
        """Double-click anywhere on the node body -> rich text editor
        (two fields: Name visible on canvas, Text hidden from canvas)."""
        view = (self.scene().views()[0]
                if self.scene() and self.scene().views() else None)
        if not view:
            return

        dialog = RichTextEditDialog(
            view,
            initial_name=self.title._plain,
            initial_html=self.title._html,
            initial_font_size=self._font_size,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            old_html  = self.title._html
            old_plain = self.title._plain
            old_fs    = self._font_size

            new_plain = dialog.get_name().strip() or self.title._plain
            new_html  = dialog.get_html()
            new_fs    = dialog.get_font_size()

            self.title._plain = new_plain
            self.title._html  = new_html
            self.title.setPlainText(new_plain)
            self._font_size = new_fs
            self.title.set_font_size(new_fs)
            self._fit_to_text()

            if self.scene():
                self.scene()._push_undo({
                    "type":      "node_html",
                    "node":      self,
                    "old":       old_html,
                    "new":       new_html,
                    "old_plain": old_plain,
                    "new_plain": new_plain,
                    "old_fs":    old_fs,
                    "new_fs":    new_fs,
                })
                self.scene().mark_dirty()
        event.accept()

    def _set_orientation(self, orientation):
        old = self._orientation
        self._orientation = orientation
        self._apply_orientation()
        self.update()
        if self.scene():
            self.scene()._push_undo({
                "type": "node_orientation", "node": self,
                "old": old, "new": orientation,
            })
            self.scene().mark_dirty()

    def _set_shape(self, shape):
        old = self._shape
        self._shape = shape
        self._fit_to_text()
        self.update()
        if self.scene():
            self.scene()._push_undo({
                "type": "node_shape", "node": self,
                "old": old, "new": shape,
            })
            self.scene().mark_dirty()

    def _pick_color(self, parent):
        old = QColor(self._color)
        color = open_color_wheel(parent, self._color.name())
        if color:
            self._color        = color
            self._color_locked = True
            self.update()
            if self.scene():
                self.scene()._push_undo({
                    "type": "node_color", "node": self,
                    "old": old, "new": color,
                })
                self.scene().mark_dirty()

    def _change_font(self, parent):
        old = self._font_size
        sz, ok = QInputDialog.getInt(
            parent, "Font Size", "Size:", self._font_size, 6, 10000)
        if ok:
            self._font_size = sz
            self.title.set_font_size(sz)
            self._fit_to_text()
            if self.scene():
                self.scene()._push_undo({
                    "type": "node_font_size", "node": self,
                    "old": old, "new": sz,
                })
                self.scene().mark_dirty()

    def _pick_font_color(self, parent):
        old = QColor(self._font_color)
        color = QColorDialog.getColor(self._font_color, parent, "Select Font Color")
        if color.isValid():
            self._font_color = color
            self.title.set_font_color(color)
            self.update()
            if self.scene():
                self.scene()._push_undo({
                    "type": "node_font_color", "node": self,
                    "old": old, "new": color,
                })
                self.scene().mark_dirty()

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width, self.height)

        if self.isSelected():
            glow_color = QColor(80, 170, 255, 35)
            for i in range(10):
                spread = i * 1.5
                c = QColor(glow_color)
                c.setAlpha(max(0, 35 - i * 4))
                painter.setPen(QPen(c, 1 + i))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                gr = rect.adjusted(-spread, -spread, spread, spread)
                self._draw_shape(painter, gr, spread)

        painter.setBrush(QBrush(self._color))
        painter.setPen(QPen(QColor(NODE_BORDER), 1.2))
        self._draw_shape(painter, rect, 0)

        if self.isSelected():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(255, 255, 255, 140), 2))
            self._draw_shape(painter, rect, 0)

        # SVG icon badge: white when node has text content, black otherwise
        self._draw_text_icon(painter)

    # ── Text icon badge ───────────────────────────────────────────────────────

    _PNG_ICON_BLACK = None
    _PNG_ICON_WHITE = None

    @classmethod
    def _get_text_renderers(cls):
        if cls._PNG_ICON_BLACK is None:
            _base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
            cls._PNG_ICON_BLACK = _svg_to_pixmap(os.path.join(_base, "text_black.svg"))
            cls._PNG_ICON_WHITE = _svg_to_pixmap(os.path.join(_base, "text_white.svg"))
        return cls._PNG_ICON_BLACK, cls._PNG_ICON_WHITE

    def _draw_text_icon(self, painter):
        black_px, white_px = self._get_text_renderers()
        px = white_px if self.title._html else black_px
        if px.isNull():
            return
        icon_size = 56
        gap       = 10
        ox = self.width - self._SOCK_R
        ty = self.title.pos().y()
        th = self.title.boundingRect().height()
        x  = ox - gap - icon_size
        y  = ty + th / 2 - icon_size / 2
        painter.save()
        painter.drawPixmap(QRectF(x, y, icon_size, icon_size).toRect(),
                           px.scaled(icon_size, icon_size,
                                     Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation))
        painter.restore()

    # ── Shape helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _circle_rect(rect):
        """Circle centred in rect, diameter = rect.height() (bounding box is square)."""
        d  = rect.height()
        cx = rect.center().x()
        cy = rect.center().y()
        return QRectF(cx - d / 2, cy - d / 2, d, d)

    @staticmethod
    def _ellipse_rect(rect):
        """Wide ellipse centred in rect, using the rect's own width and height.
        The base shape uses height = width * 2/3; glow passes an already-expanded
        rect so both axes grow uniformly and the glow follows the ellipse outline."""
        return rect

    @staticmethod
    def _diamond_path(rect, radius=10):
        """Rotated square (equal diagonals) with rounded corners.
        Bounding box is square (width == height) so diagonals are equal."""
        cx = rect.center().x()
        cy = rect.center().y()
        hw = rect.width()  / 2
        hh = rect.height() / 2
        r  = min(radius, hw * 0.35, hh * 0.35)

        top    = QPointF(cx,      cy - hh)
        right  = QPointF(cx + hw, cy)
        bottom = QPointF(cx,      cy + hh)
        left   = QPointF(cx - hw, cy)

        def _lerp(a, b, t):
            return QPointF(a.x() + (b.x() - a.x()) * t,
                           a.y() + (b.y() - a.y()) * t)

        fx = r / hw
        fy = r / hh

        path = QPainterPath()
        path.moveTo(_lerp(top, right, fx))
        path.lineTo(_lerp(right, top, fy))
        path.quadTo(right, _lerp(right, bottom, fy))
        path.lineTo(_lerp(bottom, right, fx))
        path.quadTo(bottom, _lerp(bottom, left, fx))
        path.lineTo(_lerp(left, bottom, fy))
        path.quadTo(left, _lerp(left, top, fy))
        path.lineTo(_lerp(top, left, fx))
        path.quadTo(top, _lerp(top, right, fx))
        path.closeSubpath()
        return path

    @staticmethod
    def _triangle_path(rect, corner_radius=None):
        """Downward-pointing equilateral triangle with rounded corners.
        Corner radius is the same absolute pixel value as CORNER_RADIUS (rectangle)."""
        import math
        r = CORNER_RADIUS if corner_radius is None else corner_radius
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()

        tl = QPointF(x,       y)        # top-left  ← in_socket
        tr = QPointF(x + w,   y)        # top-right ← out_socket
        bt = QPointF(x + w/2, y + h)    # bottom tip

        def _dist(a, b):
            return math.sqrt((b.x()-a.x())**2 + (b.y()-a.y())**2)

        def _lerp(a, b, t):
            return QPointF(a.x() + (b.x()-a.x())*t,
                           a.y() + (b.y()-a.y())*t)

        d_top   = _dist(tl, tr)
        d_left  = _dist(tl, bt)
        d_right = _dist(tr, bt)

        # Clamp so the radius never overruns an edge
        r = min(r, d_top * 0.4, d_left * 0.4, d_right * 0.4)

        path = QPainterPath()
        # Start just past top-left corner going rightward along top edge
        path.moveTo(_lerp(tl, tr,  r / d_top))
        path.lineTo(_lerp(tr, tl,  r / d_top))   # approach top-right
        path.quadTo(tr, _lerp(tr, bt,  r / d_right))
        path.lineTo(_lerp(bt, tr,  r / d_right)) # approach bottom tip
        path.quadTo(bt, _lerp(bt, tl,  r / d_left))
        path.lineTo(_lerp(tl, bt,  r / d_left))  # approach top-left
        path.quadTo(tl, _lerp(tl, tr,  r / d_top))
        path.closeSubpath()
        return path

    @staticmethod
    def _hexagon_path(rect, radius=10):
        """Flat-top regular hexagon with rounded corners.
        Sockets sit at the left and right midpoints."""
        import math
        cx = rect.center().x()
        cy = rect.center().y()
        # Flat-top hexagon: 6 vertices equally spaced, starting from left middle
        # angles: 180, 120, 60, 0, -60, -120  (flat top/bottom)
        hw = rect.width()  / 2
        hh = rect.height() / 2
        angles = [180, 120, 60, 0, -60, -120]
        verts = [
            QPointF(cx + hw * math.cos(math.radians(a)),
                    cy + hh * math.sin(math.radians(a)))
            for a in angles
        ]

        r = min(radius, hw * 0.15, hh * 0.25)

        def _lerp(a, b, t):
            return QPointF(a.x() + (b.x() - a.x()) * t,
                           a.y() + (b.y() - a.y()) * t)

        def _dist(a, b):
            return math.sqrt((b.x()-a.x())**2 + (b.y()-a.y())**2)

        n = len(verts)
        path = QPainterPath()
        for i in range(n):
            cur  = verts[i]
            nxt  = verts[(i + 1) % n]
            prv  = verts[(i - 1) % n]
            d_in  = _dist(prv, cur)
            d_out = _dist(cur, nxt)
            p_in  = _lerp(prv, cur, 1 - r / d_in)
            p_out = _lerp(cur, nxt,     r / d_out)
            if i == 0:
                path.moveTo(p_in)
            else:
                path.lineTo(p_in)
            path.quadTo(cur, p_out)
        path.closeSubpath()
        return path

    def _draw_shape(self, painter, rect, spread):
        if self._shape == "circle":
            painter.drawEllipse(self._circle_rect(rect))

        elif self._shape == "ellipse":
            painter.drawEllipse(self._ellipse_rect(rect))

        elif self._shape == "diamond":
            radius = max(4, CORNER_RADIUS - spread * 0.5)
            painter.drawPath(self._diamond_path(rect, radius))

        elif self._shape == "triangle":
            painter.drawPath(self._triangle_path(rect, CORNER_RADIUS))

        elif self._shape == "hexagon":
            painter.drawPath(self._hexagon_path(rect))

        else:  # rectangle (default)
            painter.drawRoundedRect(rect, CORNER_RADIUS + spread,
                                    CORNER_RADIUS + spread)


# =========================================================
# IMAGE NODE
# =========================================================

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QLineEdit, QScrollArea, QSizePolicy,
)
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene as _QGS2
from PyQt6.QtCore import QSize


class ZoomPanImageView(QGraphicsView):
    """QGraphicsView with mouse-wheel zoom and drag-to-pan for image preview."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._gscene = _QGS2(self)
        self.setScene(self._gscene)
        self._pix_item = None
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setStyleSheet("background:#1b1b1b; border:1px solid #5c5c5c;")
        self.setMinimumSize(460, 280)

    def load(self, pixmap):
        self._gscene.clear()
        if pixmap and not pixmap.isNull():
            self._pix_item = self._gscene.addPixmap(pixmap)
            self._gscene.setSceneRect(QRectF(pixmap.rect()))
            self.fitInView(self._pix_item, Qt.AspectRatioMode.KeepAspectRatio)
        else:
            self._pix_item = None
            self._gscene.addText("No image", QFont("Arial", 14))

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)


class ImageNodeDialog(QDialog):
    """Dialog for ImageNode: name field + zoomable/pannable image preview."""

    def __init__(self, parent, initial_name="Image", image_path=""):
        super().__init__(parent)
        self.setWindowTitle("Edit Image Node")
        self.setMinimumSize(520, 500)
        self.setStyleSheet("background:#2a2a2a; color:#ffffff;")

        self._image_path = image_path
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Name ──────────────────────────────────────────────
        name_lbl = QLabel("Name  (visible on node):")
        name_lbl.setStyleSheet("color:#aaaaaa; font-size:11px;")
        layout.addWidget(name_lbl)
        self.name_edit = QLineEdit(initial_name)
        self.name_edit.setStyleSheet(
            "background:#1b1b1b; color:#ffffff; border:1px solid #5c5c5c;"
            " padding:4px; font-size:13px;")
        layout.addWidget(self.name_edit)

        # ── File row ──────────────────────────────────────────
        img_row = QHBoxLayout()
        self._path_label = QLabel(image_path or "No image loaded")
        self._path_label.setStyleSheet("color:#888888; font-size:10px;")
        self._path_label.setWordWrap(True)
        img_row.addWidget(self._path_label, 1)
        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse)
        img_row.addWidget(browse_btn)
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(60)
        clear_btn.clicked.connect(self._clear_image)
        img_row.addWidget(clear_btn)
        layout.addLayout(img_row)

        # ── Zoom hint ─────────────────────────────────────────
        hint = QLabel("Scroll to zoom · Drag to pan")
        hint.setStyleSheet("color:#555555; font-size:10px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(hint)

        # ── Zoomable/pannable preview ─────────────────────────
        self._img_view = ZoomPanImageView()
        layout.addWidget(self._img_view, 1)
        self._refresh_preview()

        # ── OK / Cancel ───────────────────────────────────────
        btn_row = QHBoxLayout()
        ok = QPushButton("OK")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(ok)
        btn_row.addWidget(cancel)
        layout.addLayout(btn_row)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.svg *.tif *.tiff);;All Files (*)")
        if path:
            self._image_path = path
            self._path_label.setText(path)
            self._refresh_preview()

    def _clear_image(self):
        self._image_path = ""
        self._path_label.setText("No image loaded")
        self._img_view.load(None)

    def _refresh_preview(self):
        pix = QPixmap(self._image_path) if self._image_path else None
        self._img_view.load(pix)

    def get_name(self):       return self.name_edit.text().strip() or "Image"
    def get_image_path(self): return self._image_path


class ImageNode(Node):
    """A node that can carry an image.  Inherits all shape/socket/color
    behaviour from Node; adds image loading and a 'P' badge when loaded."""

    def __init__(self, x=0, y=0, view=None, name="Image"):
        super().__init__(x, y, view, name)
        self._node_type   = "image"
        self._image_path  = ""    # absolute path to loaded image
        self._pixmap      = None  # QPixmap, None when no image loaded
        self._inline_viewer = None

    # ── Inline image viewer ───────────────────────────────────

    def open_inline_viewer(self):
        if not self._pixmap or self._pixmap.isNull() or not self.scene():
            return
        view = self.scene().views()[0] if self.scene().views() else None
        if not view:
            return
        if self._inline_viewer is not None:
            self.close_inline_viewer()
        self._inline_viewer = InlineImageViewer(view, self)

    def close_inline_viewer(self):
        if self._inline_viewer is not None:
            self._inline_viewer.close()
            self._inline_viewer = None

    def itemChange(self, change, value):
        result = super().itemChange(change, value)
        if change in (QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged,
                      QGraphicsItem.GraphicsItemChange.ItemScenePositionHasChanged):
            if self._inline_viewer is not None:
                self._inline_viewer.reposition()
        return result

    # ── Override double-click to open ImageNodeDialog ─────────

    def mouseDoubleClickEvent(self, event):
        view = (self.scene().views()[0]
                if self.scene() and self.scene().views() else None)
        if not view:
            return

        dialog = ImageNodeDialog(view, self.title._plain, self._image_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            old_name  = self.title._plain
            old_path  = self._image_path

            new_name  = dialog.get_name()
            new_path  = dialog.get_image_path()

            # Update name
            self.title._plain = new_name
            self.title.setPlainText(new_name)
            self._fit_to_text()

            # Update image
            self._image_path = new_path
            if new_path:
                pix = QPixmap(new_path)
                self._pixmap = pix if not pix.isNull() else None
            else:
                self._pixmap = None

            self.update()

            if self.scene():
                self.scene()._push_undo({
                    "type":      "image_node_edit",
                    "node":      self,
                    "old_name":  old_name,
                    "new_name":  new_name,
                    "old_path":  old_path,
                    "new_path":  new_path,
                })
                self.scene().mark_dirty()
        event.accept()

    # ── Override paint to show 'P' badge instead of 'T' ──────

    def paint(self, painter, option, widget):
        # Draw all the normal node geometry (shape, glow, border)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width, self.height)

        if self.isSelected():
            glow_color = QColor(80, 170, 255, 35)
            for i in range(10):
                spread = i * 1.5
                c = QColor(glow_color)
                c.setAlpha(max(0, 35 - i * 4))
                painter.setPen(QPen(c, 1 + i))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                gr = rect.adjusted(-spread, -spread, spread, spread)
                self._draw_shape(painter, gr, spread)

        painter.setBrush(QBrush(self._color))
        painter.setPen(QPen(QColor(NODE_BORDER), 1.2))
        self._draw_shape(painter, rect, 0)

        if self.isSelected():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(255, 255, 255, 140), 2))
            self._draw_shape(painter, rect, 0)

        # SVG icon badge: black when empty, white when image loaded
        self._draw_image_icon(painter)

    _PNG_IMG_BLACK = None
    _PNG_IMG_WHITE = None

    @classmethod
    def _get_image_renderers(cls):
        if cls._PNG_IMG_BLACK is None:
            _base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
            cls._PNG_IMG_BLACK = _svg_to_pixmap(os.path.join(_base, "image_black.svg"))
            cls._PNG_IMG_WHITE = _svg_to_pixmap(os.path.join(_base, "image_white.svg"))
        return cls._PNG_IMG_BLACK, cls._PNG_IMG_WHITE

    def _draw_image_icon(self, painter):
        black_px, white_px = self._get_image_renderers()
        px = white_px if (self._pixmap and not self._pixmap.isNull()) else black_px
        if px.isNull():
            return
        icon_size = 56
        gap       = 10
        ox = self.width - self._SOCK_R
        ty = self.title.pos().y()
        th = self.title.boundingRect().height()
        x  = int(ox - gap - icon_size)
        y  = int(ty + th / 2 - icon_size / 2)
        painter.save()
        painter.drawPixmap(x, y,
                           px.scaled(icon_size, icon_size,
                                     Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation))
        painter.restore()

    def _load_pixmap(self):
        """Re-load pixmap from path (used after deserialisation)."""
        if self._image_path:
            pix = QPixmap(self._image_path)
            self._pixmap = pix if not pix.isNull() else None
        else:
            self._pixmap = None

# =========================================================
# MOVIE NODE
# =========================================================

from PyQt6.QtCore import QUrl, QTimer


class MovieNodeDialog(QDialog):
    """Movie node editor: browse + video playback inside the dialog window."""

    def __init__(self, parent, initial_name="Movie", movie_path="", thumbnail=None):
        super().__init__(parent)
        from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
        from PyQt6.QtMultimediaWidgets import QGraphicsVideoItem
        from PyQt6.QtWidgets import QGraphicsScene
        from PyQt6.QtCore import QSizeF

        self.setWindowTitle("Edit Movie Node")
        self.setMinimumSize(640, 520)
        self.setStyleSheet("background:#1b1b1b; color:#ffffff;")

        self._movie_path = movie_path
        self._duration   = 0
        self._ready      = False

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 12, 12, 12)

        # ── Name ──────────────────────────────────────────────
        name_lbl = QLabel("Name:")
        name_lbl.setStyleSheet("color:#aaaaaa; font-size:11px;")
        layout.addWidget(name_lbl)
        self.name_edit = QLineEdit(initial_name)
        self.name_edit.setStyleSheet(
            "background:#2a2a2a; color:#ffffff; border:1px solid #5c5c5c;"
            " padding:4px; font-size:13px;")
        layout.addWidget(self.name_edit)

        # ── File row ──────────────────────────────────────────
        file_row = QHBoxLayout()
        self._path_label = QLabel(movie_path or "No file loaded")
        self._path_label.setStyleSheet("color:#666666; font-size:10px;")
        self._path_label.setWordWrap(True)
        file_row.addWidget(self._path_label, 1)
        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedWidth(80)
        browse_btn.setStyleSheet(self._btn_style())
        browse_btn.clicked.connect(self._browse)
        file_row.addWidget(browse_btn)
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(60)
        clear_btn.setStyleSheet(self._btn_style())
        clear_btn.clicked.connect(self._clear)
        file_row.addWidget(clear_btn)
        layout.addLayout(file_row)

        # ── Video area: QGraphicsView + QGraphicsVideoItem ────
        self._scene = QGraphicsScene(self)
        self._scene.setBackgroundBrush(QBrush(QColor("#000000")))
        self._video_item = QGraphicsVideoItem()
        self._scene.addItem(self._video_item)

        self._gview = QGraphicsView(self._scene, self)
        self._gview.setMinimumSize(600, 340)
        self._gview.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._gview.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._gview.setStyleSheet("background:#000000; border:1px solid #3a3a3a;")
        self._gview.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        layout.addWidget(self._gview, 1)

        # ── Timeline ──────────────────────────────────────────
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 1000)
        self._slider.setValue(0)
        self._slider.setEnabled(False)
        self._slider.setStyleSheet(self._slider_style())
        self._slider.sliderMoved.connect(self._seek)
        layout.addWidget(self._slider)

        self._time_lbl = QLabel("0:00 / 0:00")
        self._time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._time_lbl.setStyleSheet("color:#666666; font-size:10px;")
        layout.addWidget(self._time_lbl)

        # ── Transport + volume ────────────────────────────────
        ctrl = QHBoxLayout()
        self._play_btn  = QPushButton("▶")
        self._pause_btn = QPushButton("⏸")
        self._stop_btn  = QPushButton("⏹")
        for b in (self._play_btn, self._pause_btn, self._stop_btn):
            b.setFixedSize(40, 32)
            b.setEnabled(False)
            b.setStyleSheet(self._btn_style())
            ctrl.addWidget(b)
        ctrl.addSpacing(12)
        ctrl.addWidget(_vol_icon_label(20))
        self._vol = QSlider(Qt.Orientation.Horizontal)
        self._vol.setRange(0, 100)
        self._vol.setValue(80)
        self._vol.setFixedWidth(100)
        self._vol.setStyleSheet(self._slider_style("#aaaaaa"))
        self._vol.valueChanged.connect(lambda v: self._audio.setVolume(v / 100.0))
        ctrl.addWidget(self._vol)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        # ── OK ────────────────────────────────────────────────
        ok_row = QHBoxLayout()
        ok_row.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setFixedWidth(80)
        ok_btn.setStyleSheet(self._btn_style())
        ok_btn.clicked.connect(self._on_ok)
        ok_row.addWidget(ok_btn)
        layout.addLayout(ok_row)

        # ── Player ────────────────────────────────────────────
        self._player = QMediaPlayer(self)
        self._audio  = QAudioOutput(self)
        self._audio.setVolume(0.8)
        self._player.setAudioOutput(self._audio)
        self._player.setVideoOutput(self._video_item)

        self._play_btn.clicked.connect(self._player.play)
        self._pause_btn.clicked.connect(self._player.pause)
        self._stop_btn.clicked.connect(self._player.stop)
        self._player.mediaStatusChanged.connect(self._on_status)
        self._player.positionChanged.connect(self._on_position)
        self._player.durationChanged.connect(self._on_duration)
        self._video_item.nativeSizeChanged.connect(self._fit_video)

        if movie_path:
            QTimer.singleShot(0, lambda: self._load(movie_path))

    @staticmethod
    def _btn_style():
        return ("QPushButton{background:#2a2a2a;color:#ffffff;border:1px solid #5c5c5c;"
                "border-radius:4px;padding:4px 8px;}"
                "QPushButton:hover{background:#3a3a3a;}"
                "QPushButton:disabled{color:#555555;border-color:#444444;}")

    @staticmethod
    def _slider_style(color="#4a9eff"):
        return (f"QSlider::groove:horizontal{{height:4px;background:#333;border-radius:2px;}}"
                f"QSlider::handle:horizontal{{width:12px;height:12px;margin:-4px 0;"
                f"background:{color};border-radius:6px;}}"
                f"QSlider::sub-page:horizontal{{background:{color};border-radius:2px;}}")

    def _load(self, path):
        with suppress_media_stderr():
            self._player.setSource(QUrl.fromLocalFile(path))

    def _fit_video(self, size):
        if size.width() <= 0 or size.height() <= 0:
            return
        from PyQt6.QtCore import QSizeF
        vw = self._gview.width()
        vh = self._gview.height()
        scale = min(vw / size.width(), vh / size.height())
        w = size.width()  * scale
        h = size.height() * scale
        self._video_item.setSize(QSizeF(w, h))
        self._scene.setSceneRect(0, 0, w, h)
        self._gview.fitInView(self._scene.sceneRect(),
                              Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        ns = self._video_item.nativeSize()
        if ns.isValid():
            self._fit_video(ns)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Movie", "",
            "Movies (*.mp4 *.mov *.avi *.mkv *.wmv *.flv *.webm *.m4v *.mpg *.mpeg)"
            ";;All Files (*)")
        if path:
            self._player.stop()
            self._movie_path = path
            self._path_label.setText(path)
            self._ready = False
            self._duration = 0
            self._slider.setValue(0)
            self._time_lbl.setText("0:00 / 0:00")
            self._set_enabled(False)
            QTimer.singleShot(0, lambda: self._load(path))

    def _clear(self):
        self._player.stop()
        self._player.setSource(QUrl())
        self._movie_path = ""
        self._path_label.setText("No file loaded")
        self._ready = False
        self._duration = 0
        self._slider.setValue(0)
        self._time_lbl.setText("0:00 / 0:00")
        self._set_enabled(False)

    def _set_enabled(self, on):
        for b in (self._play_btn, self._pause_btn, self._stop_btn):
            b.setEnabled(on)
        self._slider.setEnabled(on)

    def _on_status(self, status):
        from PyQt6.QtMultimedia import QMediaPlayer
        if status in (QMediaPlayer.MediaStatus.LoadedMedia,
                      QMediaPlayer.MediaStatus.BufferedMedia,
                      QMediaPlayer.MediaStatus.BufferingMedia):
            if not self._ready:
                self._ready = True
                self._set_enabled(True)

    def _seek(self, v):
        if self._duration > 0:
            self._player.setPosition(int(v / 1000.0 * self._duration))

    def _on_position(self, ms):
        if self._duration > 0:
            self._slider.blockSignals(True)
            self._slider.setValue(int(ms / self._duration * 1000))
            self._slider.blockSignals(False)
        self._time_lbl.setText(f"{self._fmt(ms)} / {self._fmt(self._duration)}")

    def _on_duration(self, ms):
        self._duration = ms
        self._time_lbl.setText(f"0:00 / {self._fmt(ms)}")

    @staticmethod
    def _fmt(ms):
        s = ms // 1000
        return f"{s // 60}:{s % 60:02d}"

    def _stop_player(self):
        self._player.stop()
        self._player.setVideoOutput(None)
        self._player.setSource(QUrl())

    def _on_ok(self):
        self._stop_player()
        self.accept()

    def closeEvent(self, event):
        self._stop_player()
        super().closeEvent(event)

    def get_name(self):       return self.name_edit.text().strip() or "Movie"
    def get_movie_path(self): return self._movie_path

    @staticmethod
    def _grab_thumbnail(dialog):
        return None


# =========================================================
# INLINE IMAGE VIEWER  (arrow-down on selected ImageNode)
# =========================================================

class InlineImageViewer(QObject):
    """Viewport-parented image viewer anchored to bottom-left of an ImageNode.
    Scales with zoom. No controls needed — just the image."""

    MAX_W = 640

    def __init__(self, view, node):
        super().__init__()
        self._view  = view
        self._node  = node

        # Compute display size from pixmap
        px = node._pixmap
        if px and not px.isNull():
            w = min(px.width(), self.MAX_W)
            h = int(px.height() * w / px.width()) if px.width() > 0 else w
        else:
            w, h = self.MAX_W, self.MAX_W

        self._native_w = w
        self._native_h = h

        self._container = QWidget(view.viewport())
        self._container.setStyleSheet("background:#111;border:none;")
        self._container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._label = QLabel(self._container)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("background:#000;border:none;")

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

        self._set_pixmap(px)
        self._apply_size()
        self._container.show()
        self._container.raise_()

    def _set_pixmap(self, px):
        if px and not px.isNull():
            self._label.setPixmap(
                px.scaled(self._label.size(),
                          Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation))

    def _apply_size(self):
        scale = self._view.transform().m11()
        w = max(40, int(self._native_w * scale))
        h = max(30, int(self._native_h * scale))
        self._container.setFixedSize(w, h)
        self._label.setFixedSize(w, h)
        px = self._node._pixmap
        if px and not px.isNull():
            self._label.setPixmap(
                px.scaled(w, h,
                          Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation))
        self.reposition()

    def reposition(self):
        scale = self._view.transform().m11()
        w     = max(40, int(self._native_w * scale))
        h     = max(30, int(self._native_h * scale))
        self._container.setFixedSize(w, h)
        self._label.setFixedSize(w, h)
        # Re-scale the pixmap to the new pixel size
        px = self._node._pixmap
        if px and not px.isNull():
            self._label.setPixmap(
                px.scaled(w, h,
                          Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation))
        scene_pt = self._node.mapToScene(QPointF(0, self._node.height))
        vp_pt    = self._view.mapFromScene(scene_pt)
        self._container.move(vp_pt.x(), vp_pt.y())

    def close(self):
        self._container.hide()
        self._container.deleteLater()

# =========================================================
# INLINE DOC VIEWER  (arrow-down on selected DocumentNode)
# =========================================================

class InlineDocViewer(QObject):
    """Viewport-parented image viewer anchored to DocumentNode.
    Loads logo/F!.png. Zoom behaviour is identical to InlineImageViewer.
    Has an Open button bar at the bottom."""

    MAX_W  = 640
    BAR_H  = 28

    def __init__(self, view, node):
        super().__init__()
        self._view = view
        self._node = node

        _png = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "logo", "F!.png")
        self._pixmap = QPixmap(_png)

        if not self._pixmap.isNull():
            w = min(self._pixmap.width(), self.MAX_W)
            h = int(self._pixmap.height() * w / self._pixmap.width()) if self._pixmap.width() > 0 else w
        else:
            w, h = self.MAX_W, self.MAX_W
        self._native_w = w
        self._native_h = h
        self._name_h   = 20

        self._container = QWidget(view.viewport())
        self._container.setStyleSheet("background:#505050; border-radius:12px;")
        self._container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # Filename label
        self._name_label = QLabel(self._container)
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fname = os.path.basename(node._doc_path) if node._doc_path else ""
        self._name_label.setText(fname)

        # Image
        self._label = QLabel(self._container)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("background:#505050; border:none; border-radius:0px;")

        # Open button bar
        from PyQt6.QtWidgets import QHBoxLayout, QPushButton
        self._bar = QWidget(self._container)
        self._bar.setStyleSheet("background:#333; border-top:1px solid #222; border-bottom-left-radius:12px; border-bottom-right-radius:12px;")
        bar_l = QHBoxLayout(self._bar)
        bar_l.setContentsMargins(8, 0, 8, 0)
        self._open_btn = QPushButton("Open")
        self._open_btn.setStyleSheet(
            "QPushButton{background:#3a3a3a;color:#fff;border:none;"
            "border-radius:4px;padding:2px 14px;font-size:11px;}"
            "QPushButton:hover{background:#4a9eff;}")
        self._open_btn.clicked.connect(self._open_file)
        self._open_btn.setEnabled(bool(node._doc_path and os.path.isfile(node._doc_path)))
        bar_l.addStretch()
        bar_l.addWidget(self._open_btn)
        bar_l.addStretch()

        self._container.show()
        self._container.raise_()
        self.reposition()

    def _open_file(self):
        if self._node._doc_path and os.path.isfile(self._node._doc_path):
            _open_with_system(self._node._doc_path)

    def reposition(self):
        scale  = self._view.transform().m11()
        w      = max(40, int(self._native_w * scale))
        h      = max(30, int(self._native_h * scale))
        name_h = max(14, int(self._name_h * scale))
        bar_h  = max(20, int(self.BAR_H * scale))
        fnt    = max(8,  int(11 * scale))
        total_h = name_h + h + bar_h

        self._container.setFixedSize(w, total_h)

        self._name_label.setFixedSize(w, name_h)
        self._name_label.move(0, 0)
        self._name_label.setStyleSheet(
            f"background:#505050; color:#ffffff; font-size:{fnt}px; padding:2px; border-top-left-radius:12px; border-top-right-radius:12px;")

        self._label.setFixedSize(w, h)
        self._label.move(0, name_h)
        if not self._pixmap.isNull():
            self._label.setPixmap(
                self._pixmap.scaled(w, h,
                                    Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation))

        self._bar.setFixedSize(w, bar_h)
        self._bar.move(0, name_h + h)
        btn_fnt = max(8, int(11 * scale))
        self._open_btn.setStyleSheet(
            f"QPushButton{{background:#3a3a3a;color:#fff;border:none;"
            f"border-radius:4px;padding:2px 14px;font-size:{btn_fnt}px;}}"
            f"QPushButton:hover{{background:#4a9eff;}}")

        scene_pt = self._node.mapToScene(QPointF(0, self._node.height))
        vp_pt    = self._view.mapFromScene(scene_pt)
        self._container.move(vp_pt.x(), vp_pt.y())

    def close(self):
        self._container.hide()
        self._container.deleteLater()


class InlineTextViewer(QObject):
    """Sticky-note style inline text viewer — shows body text only.
    Resizable from the bottom-right corner. Scales with zoom."""

    _DEFAULT_SCENE_W = 900   # 3× original 300
    _DEFAULT_SCENE_H = 660   # 3× original 220
    _CORNER          = 16    # resize handle size in viewport px

    def __init__(self, view, node):
        super().__init__()
        self._view   = view
        self._node   = node

        # Size stored in scene units so it scales with zoom
        self._scene_w = self._DEFAULT_SCENE_W
        self._scene_h = self._DEFAULT_SCENE_H

        self._container = QWidget(view.viewport())
        self._container.setStyleSheet(
            "background:#c8c8c8; border-radius:12px;")
        self._container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._container.setMinimumSize(80, 60)

        from PyQt6.QtWidgets import QTextBrowser
        self._text_edit = QTextBrowser(self._container)
        self._text_edit.setReadOnly(True)
        self._text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._text_edit.setFrameShape(self._text_edit.Shape.NoFrame)
        self._text_edit.setOpenLinks(False)
        self._text_edit.anchorClicked.connect(self._open_link)
        html = getattr(node.title, '_html', '')
        if html:
            self._text_edit.setHtml(html)
        else:
            self._text_edit.setPlainText(getattr(node.title, '_plain', ''))

        # Bottom-right resize grip
        self._grip = QWidget(self._container)
        self._grip.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self._grip.setStyleSheet("background:transparent;")
        self._grip.setFixedSize(self._CORNER, self._CORNER)
        self._grip.installEventFilter(self)
        self._grip_dragging = False

        self._container.show()
        self._container.raise_()
        self.reposition()

    def _open_link(self, url):
        """Open clicked hyperlink in the system browser."""
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(url)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if obj is self._grip:
            if event.type() == QEvent.Type.MouseButtonPress and \
               event.button() == Qt.MouseButton.LeftButton:
                self._grip_dragging = True
                self._drag_start    = event.globalPosition().toPoint()
                self._drag_scene_w  = self._scene_w
                self._drag_scene_h  = self._scene_h
                return True
            elif event.type() == QEvent.Type.MouseMove and self._grip_dragging:
                delta  = event.globalPosition().toPoint() - self._drag_start
                scale  = self._view.transform().m11()
                # Convert viewport pixel delta to scene units
                self._scene_w = max(120, self._drag_scene_w + delta.x() / scale)
                self._scene_h = max(80,  self._drag_scene_h + delta.y() / scale)
                self._layout()
                return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self._grip_dragging = False
                return True
        return False

    def _layout(self):
        from PyQt6.QtGui import QFont, QTextCharFormat, QTextCursor
        scale = self._view.transform().m11()
        w = max(80,  int(self._scene_w * scale))
        h = max(60,  int(self._scene_h * scale))
        fnt = max(6, int(30 * scale))
        self._container.setFixedSize(w, h)
        self._text_edit.setFixedSize(w, h)
        self._text_edit.move(0, 0)

        # Scale document font so text grows/shrinks with zoom
        doc_font = QFont("Arial", fnt)
        self._text_edit.document().setDefaultFont(doc_font)
        cursor = self._text_edit.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        fmt = QTextCharFormat()
        fmt.setFontPointSize(float(fnt))
        fmt.setFontFamilies(["Arial"])
        cursor.mergeCharFormat(fmt)

        self._text_edit.setStyleSheet(
            f"QTextEdit{{background:#c8c8c8;color:#1a1a1a;border:none;"
            f"padding:10px;font-size:{fnt}px;font-family:Arial;}}"
            "QScrollBar:vertical{background:#b0b0b0;width:6px;margin:0;}"
            "QScrollBar::handle:vertical{background:#808080;border-radius:3px;min-height:16px;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0px;}")
        self._grip.move(w - self._CORNER, h - self._CORNER)

    def reposition(self):
        self._layout()
        scene_pt = self._node.mapToScene(QPointF(0, self._node.height))
        vp_pt    = self._view.mapFromScene(scene_pt)
        self._container.move(vp_pt.x(), vp_pt.y())

    def close(self):
        self._container.hide()
        self._container.deleteLater()


    def close(self):
        self._container.hide()
        self._container.deleteLater()


# =========================================================
# INLINE AUDIO PLAYER  (arrow-down on selected AudioNode)
# =========================================================

def _fmt_ms(ms):
    s = max(0, ms) // 1000
    return f"{s // 60}:{s % 60:02d}"


class _ClickSlider(QSlider):
    """QSlider that emits seek_requested(fraction) on click anywhere in groove."""
    from PyQt6.QtCore import pyqtSignal
    seek_requested = pyqtSignal(float)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            frac = max(0.0, min(1.0, event.pos().x() / self.width()))
            self.seek_requested.emit(frac)
            self.setValue(int(frac * self.maximum()))
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            frac = max(0.0, min(1.0, event.pos().x() / self.width()))
            self.seek_requested.emit(frac)
            self.setValue(int(frac * self.maximum()))
        super().mouseMoveEvent(event)


class SimpleWaveformWidget(QWidget):
    """RMS gradient silhouette waveform — smooth, tapered, gradient-filled.
    Supports WAV natively and MP3/AAC/FLAC/OGG via pydub (optional).
    Falls back to a sine-envelope preview for unsupported formats.
    Clicking or dragging seeks the player via set_seek_callback."""

    _BARS     = 200   # number of RMS buckets
    _SMOOTH_R = 3     # smoothing radius in buckets

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rms      = []
        self._has_real = False
        self._playhead = 0.0    # 0.0–1.0 fraction
        self._seek_cb  = None   # callable(fraction) set by InlineAudioPlayer
        self.setStyleSheet("background:#111111;")
        self.setMouseTracking(True)

    def set_seek_callback(self, cb):
        """Register a callable(fraction) called on waveform click/drag."""
        self._seek_cb = cb

    def set_position(self, fraction: float):
        """Update playhead (0.0–1.0) and repaint."""
        self._playhead = max(0.0, min(1.0, fraction))
        self.update()

    def __del__(self):
        try:
            self._stop_decoder()
        except Exception:
            pass

    def load(self, path):
        self._rms      = []
        self._has_real = False
        self._stop_decoder()
        if not path:
            self.update()
            return
        ext = os.path.splitext(path)[1].lower()
        if ext == ".wav":
            samples = self._read_wav_samples(path)
            if samples:
                self._rms      = self._compute_rms(samples)
                self._has_real = True
            else:
                self._rms = self._sine_envelope()
            self.update()
        else:
            self._decode_via_qt(path)

    def _read_wav_samples(self, path):
        try:
            import wave as _wave
            with _wave.open(path, "rb") as wf:
                n_ch  = wf.getnchannels()
                sampw = wf.getsampwidth()
                n_fr  = wf.getnframes()
                raw   = wf.readframes(n_fr)
            fmt = {1: "B", 2: "h", 4: "i"}.get(sampw, "h")
            if sampw == 1:
                vals = [(v - 128) / 128.0
                        for v in struct.unpack_from(f"{n_fr*n_ch}{fmt}", raw)[::n_ch]]
            else:
                scale = float(2 ** (sampw * 8 - 1))
                vals  = [v / scale
                         for v in struct.unpack_from(f"{n_fr*n_ch}{fmt}", raw)[::n_ch]]
            return vals
        except Exception:
            return []

    def _stop_decoder(self):
        """Stop and clean up any running QAudioDecoder."""
        if hasattr(self, "_decoder") and self._decoder is not None:
            try:
                self._decoder.stop()
                self._decoder.deleteLater()
            except Exception:
                pass
            self._decoder = None
        self._decode_buf = []

    def _decode_via_qt(self, path):
        """Decode any format via QAudioDecoder (AVFoundation on macOS).
        Asynchronous — waveform renders when decoding completes."""
        from PyQt6.QtMultimedia import QAudioDecoder, QAudioFormat
        from PyQt6.QtCore import QUrl

        fmt = QAudioFormat()
        fmt.setSampleRate(22050)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Float)

        self._decode_buf = []
        self._decoder = QAudioDecoder()
        self._decoder.setAudioFormat(fmt)
        self._decoder.setSource(QUrl.fromLocalFile(path))

        self._decoder.bufferReady.connect(self._on_decode_buffer)
        self._decoder.finished.connect(self._on_decode_finished)
        self._decoder.error.connect(self._on_decode_error)
        self._decoder.start()

    def _on_decode_buffer(self):
        buf = self._decoder.read()
        if not buf.isValid():
            return
        # sip.voidptr — convert via bytes() then unpack as floats
        import struct as _struct
        raw = bytes(buf.constData())
        n = len(raw) // 4
        if n > 0:
            self._decode_buf.extend(_struct.unpack_from(f"{n}f", raw))

    def _on_decode_finished(self):
        samples = self._decode_buf
        self._decode_buf = []
        if samples:
            self._rms      = self._compute_rms(samples)
            self._has_real = True
        else:
            self._rms = self._sine_envelope()
        self.update()

    def _on_decode_error(self, error):
        self._decode_buf = []
        self._rms = self._sine_envelope()
        self.update()

    def _compute_rms(self, samples):
        n      = len(samples)
        bucket = max(1, n // self._BARS)
        raw_rms = []
        for i in range(self._BARS):
            chunk = samples[i * bucket: i * bucket + bucket]
            if chunk:
                rms = math.sqrt(sum(v * v for v in chunk) / len(chunk))
            else:
                rms = 0.0
            raw_rms.append(rms)
        peak = max(raw_rms) or 1.0
        norm = [v / peak for v in raw_rms]
        r = self._SMOOTH_R
        smoothed = []
        for i in range(len(norm)):
            lo, hi = max(0, i - r), min(len(norm) - 1, i + r)
            smoothed.append(sum(norm[lo:hi+1]) / (hi - lo + 1))
        return smoothed

    def _sine_envelope(self):
        return [math.pow(math.sin(math.pi * i / (self._BARS - 1)), 0.5) * 0.7
                for i in range(self._BARS)]

    def paintEvent(self, event):
        from PyQt6.QtGui import (QPainter as _QP, QPainterPath as _QPP,
                                  QLinearGradient as _QLG, QBrush as _QBr)
        p = _QP(self)
        p.setRenderHint(_QP.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        mid  = h / 2.0

        p.fillRect(0, 0, w, h, QColor("#111111"))

        if not self._rms:
            p.setPen(QPen(QColor(80, 80, 80), 1))
            p.drawLine(0, int(mid), w, int(mid))
            return

        n = len(self._rms)

        path = _QPP()
        path.moveTo(0.0, mid)
        for i, v in enumerate(self._rms):
            path.lineTo(i * w / (n - 1), mid - v * mid * 0.92)
        for i in range(n - 1, -1, -1):
            path.lineTo(i * w / (n - 1), mid + self._rms[i] * mid * 0.92)
        path.closeSubpath()

        grad = _QLG(0, 0, 0, h)
        if self._has_real:
            grad.setColorAt(0.0,  QColor(74, 158, 255,   0))
            grad.setColorAt(0.45, QColor(74, 158, 255, 210))
            grad.setColorAt(0.5,  QColor(74, 158, 255, 230))
            grad.setColorAt(0.55, QColor(74, 158, 255, 210))
            grad.setColorAt(1.0,  QColor(74, 158, 255,   0))
        else:
            grad.setColorAt(0.0,  QColor(80, 80, 80,   0))
            grad.setColorAt(0.5,  QColor(80, 80, 80, 140))
            grad.setColorAt(1.0,  QColor(80, 80, 80,   0))

        p.setBrush(_QBr(grad))
        p.setPen(QPen(QColor(0, 0, 0, 0)))
        p.drawPath(path)

        edge_col = QColor(74, 158, 255, 90) if self._has_real else QColor(80, 80, 80, 60)
        p.setPen(QPen(edge_col, 1.0))
        p.setBrush(QColor(0, 0, 0, 0))
        top = _QPP()
        top.moveTo(0.0, mid)
        for i, v in enumerate(self._rms):
            top.lineTo(i * w / (n - 1), mid - v * mid * 0.92)
        p.drawPath(top)
        bot = _QPP()
        bot.moveTo(0.0, mid)
        for i, v in enumerate(self._rms):
            bot.lineTo(i * w / (n - 1), mid + v * mid * 0.92)
        p.drawPath(bot)

        if not self._has_real:
            p.setPen(QColor(100, 100, 100))
            p.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter,
                       "Waveform preview (install pydub for real data)")

        # Playhead — vertical line at current position
        if self._playhead > 0.0:
            px = int(self._playhead * w)
            p.setPen(QPen(QColor(255, 255, 255, 200), 1.5))
            p.drawLine(px, 0, px, h)
            # Small triangle cap at top
            p.setBrush(QColor(255, 255, 255, 200))
            p.setPen(QPen(QColor(0, 0, 0, 0)))
            from PyQt6.QtGui import QPolygon
            from PyQt6.QtCore import QPoint
            tri = QPolygon([QPoint(px-4, 0), QPoint(px+4, 0), QPoint(px, 7)])
            p.drawPolygon(tri)


    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._seek_cb:
            frac = max(0.0, min(1.0, event.pos().x() / self.width()))
            self._seek_cb(frac)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self._seek_cb:
            frac = max(0.0, min(1.0, event.pos().x() / self.width()))
            self._seek_cb(frac)

class InlineAudioPlayer(QObject):
    """Viewport-parented audio player: waveform / timeline slider / controls."""

    MAX_W      = 480
    WAVE_H     = 80
    TIMELINE_H = 18
    CTRL_H     = 44

    def __init__(self, view, node):
        super().__init__()
        from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
        from PyQt6.QtCore       import QUrl

        self._view     = view
        self._node     = node
        self._duration = 0
        self._seeking  = False
        self._preview_done = False

        # Native (unscaled) dimensions — mirrors InlineImageViewer._native_w/_native_h
        self._native_w      = self.MAX_W
        self._native_wv_h   = self.WAVE_H
        self._native_tl_h   = self.TIMELINE_H
        self._native_ctrl_h = self.CTRL_H

        self._container = QWidget(view.viewport())
        self._container.setStyleSheet(
            "background:#111;border:1px solid #3a3a3a;border-radius:4px;")
        self._container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._container.setMouseTracking(True)
        # No layout manager — children positioned absolutely in reposition()
        # so setFixedSize on the container is never overridden by a layout.

        # Waveform — pure QPainter widget, no WebEngine compositor, scales perfectly
        self._waveform = SimpleWaveformWidget(self._container)
        self._waveform.load(node._audio_path)
        self._waveform.set_seek_callback(self._seek_from_waveform)

        # Timeline slider bar — direct child
        self._timeline_bar = QWidget(self._container)
        self._timeline_bar.setStyleSheet("background:#0a0a0a;")
        self._timeline_bar.setMouseTracking(True)
        tl = QHBoxLayout(self._timeline_bar)
        tl.setContentsMargins(6, 2, 6, 2)
        tl.setSpacing(0)
        self._timeline = _ClickSlider(Qt.Orientation.Horizontal, self._timeline_bar)
        self._timeline.setRange(0, 1000)
        self._timeline.setValue(0)
        self._timeline.setEnabled(False)
        self._timeline.setStyleSheet(
            "QSlider::groove:horizontal{height:6px;background:#333;border-radius:3px;}"
            "QSlider::handle:horizontal{width:12px;height:12px;margin:-3px 0;"
            "background:#4a9eff;border-radius:6px;}"
            "QSlider::sub-page:horizontal{background:#4a9eff;border-radius:3px;}")
        self._timeline.seek_requested.connect(self._on_timeline_click)
        tl.addWidget(self._timeline)
        self._timeline_bar.setVisible(False)

        # Controls bar — direct child
        self._ctrl_bar = QWidget(self._container)
        self._ctrl_bar.setStyleSheet("background:#111;border-top:1px solid #2a2a2a;")
        self._ctrl_bar.setMouseTracking(True)
        cl = QHBoxLayout(self._ctrl_bar)
        cl.setContentsMargins(10, 6, 10, 6)
        cl.setSpacing(8)

        def _btn(t):
            b = QPushButton(t)
            b.setFixedSize(34, 28)
            b.setStyleSheet(
                "QPushButton{background:#3a3a3a;color:#fff;border:none;"
                "border-radius:5px;font-size:14px;}"
                "QPushButton:hover{background:#606060;}")
            return b

        self._play_btn  = _btn("▶")
        self._pause_btn = _btn("⏸")
        self._stop_btn  = _btn("⏹")
        for b in (self._play_btn, self._pause_btn, self._stop_btn):
            cl.addWidget(b)

        self._time_lbl = QLabel("0:00 / 0:00")
        self._time_lbl.setStyleSheet("color:#aaa;font-size:10px;min-width:80px;")
        cl.addWidget(self._time_lbl)

        lbl = _vol_icon_label(20)
        lbl.setStyleSheet("color:#aaa;font-size:12px;")
        cl.addWidget(lbl)

        self._vol = QSlider(Qt.Orientation.Horizontal)
        self._vol.setRange(0, 100)
        self._vol.setValue(80)
        self._vol.setFixedWidth(80)
        self._vol.setStyleSheet(
            "QSlider::groove:horizontal{height:4px;background:#555;border-radius:2px;}"
            "QSlider::handle:horizontal{width:12px;height:12px;margin:-4px 0;"
            "background:#fff;border-radius:6px;}"
            "QSlider::sub-page:horizontal{background:#4a9eff;border-radius:2px;}")
        cl.addWidget(self._vol)
        cl.addStretch()
        self._ctrl_bar.setVisible(False)

        self._player = QMediaPlayer(self)
        self._audio  = QAudioOutput(self)
        self._audio.setVolume(0.8)
        self._player.setAudioOutput(self._audio)

        def _play():
            self._player.play()

        def _pause():
            self._player.pause()

        def _stop():
            self._player.stop()

        self._play_btn.clicked.connect(_play)
        self._pause_btn.clicked.connect(_pause)
        self._stop_btn.clicked.connect(_stop)
        self._vol.valueChanged.connect(self._on_volume)
        self._timeline.sliderPressed.connect(self._on_slider_pressed)
        self._timeline.sliderMoved.connect(self._on_slider_moved)
        self._timeline.sliderReleased.connect(self._on_slider_released)
        self._player.mediaStatusChanged.connect(self._on_status)
        self._player.positionChanged.connect(self._on_position)
        self._player.durationChanged.connect(self._on_duration)

        for w in (self._container, self._waveform, self._timeline_bar, self._ctrl_bar):
            w.installEventFilter(self)

        self._apply_size()
        self._container.show()
        self._container.raise_()

        with suppress_media_stderr():
            self._player.setSource(QUrl.fromLocalFile(node._audio_path))

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if max(0, int(self.CTRL_H * self._view.transform().m11())) < self._MIN_CTRL_PX:
            return False  # controls hidden at this zoom — ignore hover
        if event.type() == QEvent.Type.Enter:
            self._timeline_bar.setVisible(True)
            self._ctrl_bar.setVisible(True)
            self.reposition()
        elif event.type() == QEvent.Type.Leave:
            from PyQt6.QtGui import QCursor
            local = self._container.mapFromGlobal(QCursor.pos())
            if not self._container.rect().contains(local):
                self._timeline_bar.setVisible(False)
                self._ctrl_bar.setVisible(False)
                self.reposition()
        return False
    def _apply_size(self):
        """Initial sizing — calls reposition() which handles all scale logic."""
        self.reposition()

    # Below this scale the controls are hidden — container becomes waveform-only
    _MIN_CTRL_PX = 10   # hide controls only when scaled height < this many pixels

    def reposition(self):
        scale   = self._view.transform().m11()
        w       = max(60, int(self._native_w * scale))
        wv_h    = max(20, int(self._native_wv_h * scale))

        tl_h   = max(0, int(self._native_tl_h   * scale))
        ctrl_h = max(0, int(self._native_ctrl_h * scale))
        show_controls = ctrl_h >= self._MIN_CTRL_PX

        if show_controls:
            tl_visible   = self._timeline_bar.isVisible()
            ctrl_visible = self._ctrl_bar.isVisible()
        else:
            tl_h   = 0
            ctrl_h = 0
            tl_visible   = False
            ctrl_visible = False

        total_h = wv_h + (tl_h if tl_visible else 0) + (ctrl_h if ctrl_visible else 0)

        # Waveform always shown, fills full width
        self._waveform.setFixedSize(w, wv_h)
        self._waveform.move(0, 0)

        # Timeline and controls — hidden when too small
        self._timeline_bar.setFixedSize(w, tl_h if tl_h else 1)
        self._timeline_bar.move(0, wv_h)
        self._ctrl_bar.setFixedSize(w, ctrl_h if ctrl_h else 1)
        self._ctrl_bar.move(0, wv_h + (tl_h if tl_visible else 0))

        if not show_controls:
            self._timeline_bar.setVisible(False)
            self._ctrl_bar.setVisible(False)

        # Container = waveform only when controls hidden, full stack otherwise
        y_ctrl = wv_h
        if tl_visible:   y_ctrl += tl_h
        if ctrl_visible: y_ctrl += ctrl_h
        self._container.setFixedSize(w, wv_h if not show_controls else
                                     wv_h + (tl_h if tl_visible else 0) +
                                     (ctrl_h if ctrl_visible else 0))

        if show_controls:
            btn_sz = max(20, int(34 * scale))
            fnt_sz = max(8,  int(14 * scale))
            for b in (self._play_btn, self._pause_btn, self._stop_btn):
                b.setFixedSize(btn_sz, max(18, int(28 * scale)))
                b.setStyleSheet(
                    f"QPushButton{{background:#3a3a3a;color:#fff;border:none;"
                    f"border-radius:{max(2,int(5*scale))}px;font-size:{fnt_sz}px;}}"
                    f"QPushButton:hover{{background:#606060;}}")
            self._vol.setFixedWidth(max(40, int(80 * scale)))
            self._time_lbl.setStyleSheet(
                f"color:#aaa;font-size:{max(8,int(10*scale))}px;"
                f"min-width:{max(60,int(80*scale))}px;")

        scene_pt = self._node.mapToScene(QPointF(0, self._node.height))
        vp_pt    = self._view.mapFromScene(scene_pt)
        self._container.move(vp_pt.x(), vp_pt.y())

    def _on_slider_pressed(self):  self._seeking = True
    def _on_slider_moved(self, v):
        if self._duration > 0:
            self._time_lbl.setText(f"{_fmt_ms(int(v/1000*self._duration))} / {_fmt_ms(self._duration)}")
    def _on_slider_released(self):
        self._seeking = False
        if self._duration > 0:
            frac = self._timeline.value() / 1000.0
            self._player.setPosition(int(frac * self._duration))

    def _on_volume(self, v):
        self._audio.setVolume(v / 100.0)

    def _on_status(self, status):
        from PyQt6.QtMultimedia import QMediaPlayer
        if self._preview_done:
            return
        if status in (QMediaPlayer.MediaStatus.LoadedMedia,
                      QMediaPlayer.MediaStatus.BufferedMedia):
            self._preview_done = True
            self._timeline.setEnabled(True)

    def _on_duration(self, dur_ms):
        self._duration = dur_ms
        self._time_lbl.setText(f"0:00 / {_fmt_ms(dur_ms)}")

    def _on_position(self, pos_ms):
        frac = pos_ms / self._duration if self._duration > 0 else 0.0
        if not self._seeking and self._duration > 0:
            self._timeline.blockSignals(True)
            self._timeline.setValue(int(frac * 1000))
            self._timeline.blockSignals(False)
        self._waveform.set_position(frac)
        self._time_lbl.setText(f"{_fmt_ms(pos_ms)} / {_fmt_ms(self._duration)}")
    def _seek_from_waveform(self, fraction):
        """Called by waveform click/drag — seek player and update UI."""
        if self._duration > 0:
            self._player.setPosition(int(fraction * self._duration))
            self._timeline.blockSignals(True)
            self._timeline.setValue(int(fraction * 1000))
            self._timeline.blockSignals(False)
            self._waveform.set_position(fraction)

    def _on_timeline_click(self, fraction):
        """Called by _ClickSlider seek_requested — seek player and update waveform."""
        if self._duration > 0:
            self._player.setPosition(int(fraction * self._duration))
            self._waveform.set_position(fraction)


    def close(self):
        self._player.stop()
        from PyQt6.QtCore import QUrl
        self._player.setSource(QUrl())
        self._container.hide()
        self._container.deleteLater()


def _fmt_ms_v(ms):
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"


# =========================================================
# INLINE VIDEO PLAYER  (arrow-down on selected MovieNode)
# =========================================================

class InlineVideoPlayer(QObject):
    """Viewport-parented video player anchored below a MovieNode.
    Uses QGraphicsView + QGraphicsVideoItem — no QVideoWidget CALayer crash.
    Controls appear on hover, hide when zoomed out, disappear entirely when
    too small — mirrors InlineAudioPlayer behaviour exactly.
    """

    MAX_W      = 560
    TIMELINE_H = 18
    CTRL_H     = 44
    _MIN_CTRL_PX = 10   # hide controls only when scaled height < this many pixels
    _HIDE_SCALE      = 0.25

    def __init__(self, view, node):
        super().__init__()
        from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
        from PyQt6.QtMultimediaWidgets import QGraphicsVideoItem
        from PyQt6.QtWidgets import QGraphicsScene
        from PyQt6.QtCore import QUrl, QSizeF

        self._view         = view
        self._node         = node
        self._duration     = 0
        self._seeking      = False
        self._preview_done = False
        self._w            = int(node.width) * 3   # 3× node width
        self._h            = int(self._w * 9 / 16)

        # ── Container — no layout, absolute positioning ────────
        self._container = QWidget(view.viewport())
        self._container.setStyleSheet("background:#000;border:none;")
        self._container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._container.setMouseTracking(True)

        # ── Video: QGraphicsView + QGraphicsVideoItem ──────────
        self._scene = QGraphicsScene(self._container)
        self._scene.setBackgroundBrush(QBrush(QColor("#000000")))
        self._video_item = QGraphicsVideoItem()
        self._scene.addItem(self._video_item)

        self._gview = QGraphicsView(self._scene, self._container)
        self._gview.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._gview.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._gview.setStyleSheet("background:#000000;border:none;")
        self._gview.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self._gview.setMouseTracking(True)
        self._video_item.nativeSizeChanged.connect(self._fit_video)

        # ── Timeline bar ───────────────────────────────────────
        self._timeline_bar = QWidget(self._container)
        self._timeline_bar.setStyleSheet("background:#0a0a0a;")
        self._timeline_bar.setMouseTracking(True)
        tl = QHBoxLayout(self._timeline_bar)
        tl.setContentsMargins(6, 2, 6, 2)
        tl.setSpacing(0)
        self._timeline = _ClickSlider(Qt.Orientation.Horizontal, self._timeline_bar)
        self._timeline.setRange(0, 1000)
        self._timeline.setValue(0)
        self._timeline.setEnabled(False)
        self._timeline.setStyleSheet(
            "QSlider::groove:horizontal{height:6px;background:#333;border-radius:3px;}"
            "QSlider::handle:horizontal{width:12px;height:12px;margin:-3px 0;"
            "background:#4a9eff;border-radius:6px;}"
            "QSlider::sub-page:horizontal{background:#4a9eff;border-radius:3px;}")
        self._timeline.seek_requested.connect(self._on_timeline_click)
        tl.addWidget(self._timeline)
        self._timeline_bar.setVisible(False)
        # ── Controls bar ───────────────────────────────────────
        self._ctrl_bar = QWidget(self._container)
        self._ctrl_bar.setStyleSheet("background:#111;")
        self._ctrl_bar.setMouseTracking(True)
        cl = QHBoxLayout(self._ctrl_bar)
        cl.setContentsMargins(10, 6, 10, 6)
        cl.setSpacing(8)

        def _btn(t):
            b = QPushButton(t)
            b.setFixedSize(34, 28)
            b.setStyleSheet(
                "QPushButton{background:#3a3a3a;color:#fff;border:none;"
                "border-radius:5px;font-size:14px;}"
                "QPushButton:hover{background:#606060;}")
            return b

        self._play_btn  = _btn("▶")
        self._pause_btn = _btn("⏸")
        self._stop_btn  = _btn("⏹")
        for b in (self._play_btn, self._pause_btn, self._stop_btn):
            cl.addWidget(b)

        self._time_lbl = QLabel("0:00 / 0:00")
        self._time_lbl.setStyleSheet("color:#aaa;font-size:10px;min-width:80px;")
        cl.addWidget(self._time_lbl)

        lbl = _vol_icon_label(20)
        lbl.setStyleSheet("color:#aaa;font-size:12px;")
        cl.addWidget(lbl)

        self._vol = QSlider(Qt.Orientation.Horizontal)
        self._vol.setRange(0, 100)
        self._vol.setValue(80)
        self._vol.setFixedWidth(80)
        self._vol.setStyleSheet(
            "QSlider::groove:horizontal{height:4px;background:#555;border-radius:2px;}"
            "QSlider::handle:horizontal{width:12px;height:12px;margin:-4px 0;"
            "background:#fff;border-radius:6px;}"
            "QSlider::sub-page:horizontal{background:#4a9eff;border-radius:2px;}")
        cl.addWidget(self._vol)
        cl.addStretch()
        self._ctrl_bar.setVisible(False)

        # ── Player ─────────────────────────────────────────────
        self._player = QMediaPlayer(self)
        self._audio  = QAudioOutput(self)
        self._audio.setVolume(0.8)
        self._player.setAudioOutput(self._audio)
        self._player.setVideoOutput(self._video_item)

        self._play_btn.clicked.connect(self._player.play)
        self._pause_btn.clicked.connect(self._player.pause)
        self._stop_btn.clicked.connect(self._player.stop)
        self._vol.valueChanged.connect(lambda v: self._audio.setVolume(v / 100.0))
        self._timeline.sliderPressed.connect(lambda: setattr(self, '_seeking', True))
        self._timeline.sliderMoved.connect(self._on_slider_moved)
        self._timeline.sliderReleased.connect(self._on_slider_released)
        self._player.mediaStatusChanged.connect(self._on_status)
        self._player.positionChanged.connect(self._on_position)
        self._player.durationChanged.connect(self._on_duration)

        for w in (self._container, self._gview, self._timeline_bar, self._ctrl_bar):
            w.installEventFilter(self)

        self._apply_size()
        self._container.show()
        self._container.raise_()

        with suppress_media_stderr():
            self._player.setSource(QUrl.fromLocalFile(node._movie_path))

    def _fit_video(self, size):
        if size.width() <= 0 or size.height() <= 0:
            return
        from PyQt6.QtCore import QSizeF
        w, h = self._gview.width(), self._gview.height()
        scale = min(w / size.width(), h / size.height())
        vw = size.width()  * scale
        vh = size.height() * scale
        self._video_item.setSize(QSizeF(vw, vh))
        self._scene.setSceneRect(0, 0, vw, vh)
        self._gview.fitInView(self._scene.sceneRect(),
                              Qt.AspectRatioMode.KeepAspectRatio)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if max(0, int(self.CTRL_H * self._view.transform().m11())) < self._MIN_CTRL_PX:
            return False
        if event.type() == QEvent.Type.Enter:
            self._timeline_bar.setVisible(True)
            self._ctrl_bar.setVisible(True)
            self.reposition()
        elif event.type() == QEvent.Type.Leave:
            from PyQt6.QtGui import QCursor
            local = self._container.mapFromGlobal(QCursor.pos())
            if not self._container.rect().contains(local):
                self._timeline_bar.setVisible(False)
                self._ctrl_bar.setVisible(False)
                self.reposition()
        return False

    def _apply_size(self):
        self.reposition()

    def reposition(self):
        scale = self._view.transform().m11()

        self._container.show()

        w = max(80, int(self._w * scale))
        h = max(45, int(self._h * scale))

        tl_h   = max(0, int(self.TIMELINE_H * scale))
        ctrl_h = max(0, int(self.CTRL_H     * scale))
        show_controls = ctrl_h >= self._MIN_CTRL_PX
        if show_controls:
            tl_visible   = self._timeline_bar.isVisible()
            ctrl_visible = self._ctrl_bar.isVisible()
        else:
            tl_h = ctrl_h = 0
            tl_visible = ctrl_visible = False

        # Video view
        self._gview.setFixedSize(w, h)
        self._gview.move(0, 0)
        # Re-fit video item to new pixel size
        ns = self._video_item.nativeSize()
        if ns.isValid():
            self._fit_video(ns)

        # Timeline
        self._timeline_bar.setFixedSize(w, tl_h if tl_h else 1)
        self._timeline_bar.move(0, h)

        # Controls
        self._ctrl_bar.setFixedSize(w, ctrl_h if ctrl_h else 1)
        self._ctrl_bar.move(0, h + (tl_h if tl_visible else 0))

        if not show_controls:
            self._timeline_bar.setVisible(False)
            self._ctrl_bar.setVisible(False)

        total_h = h + (tl_h if tl_visible else 0) + (ctrl_h if ctrl_visible else 0)
        self._container.setFixedSize(w, total_h)

        if show_controls:
            btn_sz = max(20, int(34 * scale))
            fnt_sz = max(8,  int(14 * scale))
            for b in (self._play_btn, self._pause_btn, self._stop_btn):
                b.setFixedSize(btn_sz, max(18, int(28 * scale)))
                b.setStyleSheet(
                    f"QPushButton{{background:#3a3a3a;color:#fff;border:none;"
                    f"border-radius:{max(2,int(5*scale))}px;font-size:{fnt_sz}px;}}"
                    f"QPushButton:hover{{background:#606060;}}")
            self._vol.setFixedWidth(max(40, int(80 * scale)))
            self._time_lbl.setStyleSheet(
                f"color:#aaa;font-size:{max(8,int(10*scale))}px;"
                f"min-width:{max(60,int(80*scale))}px;")

        scene_pt = self._node.mapToScene(QPointF(0, self._node.height))
        vp_pt    = self._view.mapFromScene(scene_pt)
        self._container.move(vp_pt.x(), vp_pt.y())

    def _on_slider_moved(self, v):
        if self._duration > 0:
            self._time_lbl.setText(
                f"{_fmt_ms_v(int(v/1000*self._duration))} / {_fmt_ms_v(self._duration)}")

    def _on_slider_released(self):
        self._seeking = False
        if self._duration > 0:
            self._player.setPosition(int(self._timeline.value() / 1000.0 * self._duration))

    def _on_status(self, status):
        from PyQt6.QtMultimedia import QMediaPlayer
        if self._preview_done:
            return
        if status in (QMediaPlayer.MediaStatus.LoadedMedia,
                      QMediaPlayer.MediaStatus.BufferedMedia):
            self._preview_done = True
            self._timeline.setEnabled(True)

    def _on_duration(self, dur_ms):
        self._duration = dur_ms
        self._time_lbl.setText(f"0:00 / {_fmt_ms_v(dur_ms)}")

    def _on_position(self, pos_ms):
        if not self._seeking and self._duration > 0:
            self._timeline.blockSignals(True)
            self._timeline.setValue(int(pos_ms / self._duration * 1000))
            self._timeline.blockSignals(False)
        self._time_lbl.setText(f"{_fmt_ms_v(pos_ms)} / {_fmt_ms_v(self._duration)}")


    def _on_timeline_click(self, fraction):
        """Called by _ClickSlider seek_requested — jump to position."""
        if self._duration > 0:
            self._player.setPosition(int(fraction * self._duration))
            self._timeline.blockSignals(True)
            self._timeline.setValue(int(fraction * 1000))
            self._timeline.blockSignals(False)
    def close(self):
        self._player.stop()
        self._player.setVideoOutput(None)
        self._player.setSource(QUrl())
        self._container.hide()
        self._container.deleteLater()


class MovieNode(Node):
    """A node that carries a movie file.  Inherits all shape/socket/color
    behaviour from Node; adds movie loading and an 'M' badge when loaded."""

    def __init__(self, x=0, y=0, view=None, name="Movie"):
        super().__init__(x, y, view, name)
        self._node_type      = "video"
        self._movie_path     = ""
        self._thumbnail      = None
        self._saved_position = 0
        self._inline_player  = None

    # ── Inline player ──────────────────────────────────────────

    def open_inline_player(self):
        if not self._movie_path or not self.scene():
            return
        view = self.scene().views()[0] if self.scene().views() else None
        if not view:
            return
        if self._inline_player is not None:
            self.close_inline_player()
        self._inline_player = InlineVideoPlayer(view, self)

    def close_inline_player(self):
        if self._inline_player is not None:
            self._inline_player.close()
            self._inline_player = None

    def itemChange(self, change, value):
        result = super().itemChange(change, value)
        if change in (QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged,
                      QGraphicsItem.GraphicsItemChange.ItemScenePositionHasChanged):
            if self._inline_player is not None:
                self._inline_player.reposition()
        return result

    # ── Override double-click ─────────────────────────────────

    def mouseDoubleClickEvent(self, event):
        view = (self.scene().views()[0]
                if self.scene() and self.scene().views() else None)
        if not view:
            return

        dialog = MovieNodeDialog(
            view, self.title._plain, self._movie_path, self._thumbnail)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            old_name  = self.title._plain
            old_path  = self._movie_path

            new_name  = dialog.get_name()
            new_path  = dialog.get_movie_path()

            self.title._plain = new_name
            self.title.setPlainText(new_name)
            self._fit_to_text()

            self._movie_path = new_path
            # Capture thumbnail from the paused video widget
            if new_path:
                self._thumbnail = self._grab_thumbnail(dialog)
            else:
                self._thumbnail = None

            self.update()

            if self.scene():
                self.scene()._push_undo({
                    "type":     "movie_node_edit",
                    "node":     self,
                    "old_name": old_name,
                    "new_name": new_name,
                    "old_path": old_path,
                    "new_path": new_path,
                })
                self.scene().mark_dirty()
        event.accept()

    @staticmethod
    def _grab_thumbnail(dialog):
        """No video output in audio-only mode — no thumbnail to grab."""
        return None

    # ── Override paint to show 'M' badge ─────────────────────

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width, self.height)

        if self.isSelected():
            glow_color = QColor(80, 170, 255, 35)
            for i in range(10):
                spread = i * 1.5
                c = QColor(glow_color)
                c.setAlpha(max(0, 35 - i * 4))
                painter.setPen(QPen(c, 1 + i))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                gr = rect.adjusted(-spread, -spread, spread, spread)
                self._draw_shape(painter, gr, spread)

        painter.setBrush(QBrush(self._color))
        painter.setPen(QPen(QColor(NODE_BORDER), 1.2))
        self._draw_shape(painter, rect, 0)

        if self.isSelected():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(255, 255, 255, 140), 2))
            self._draw_shape(painter, rect, 0)

        # SVG icon badge: white when video loaded, black when empty
        self._draw_video_icon(painter)

    _PNG_VID_BLACK = None
    _PNG_VID_WHITE = None

    @classmethod
    def _get_video_renderers(cls):
        if cls._PNG_VID_BLACK is None:
            _base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
            cls._PNG_VID_BLACK = _svg_to_pixmap(os.path.join(_base, "video_black.svg"))
            cls._PNG_VID_WHITE = _svg_to_pixmap(os.path.join(_base, "video_white.svg"))
        return cls._PNG_VID_BLACK, cls._PNG_VID_WHITE

    def _draw_video_icon(self, painter):
        black_px, white_px = self._get_video_renderers()
        px = white_px if self._movie_path else black_px
        if px.isNull():
            return
        icon_size = 56
        gap       = 10
        ox = self.width - self._SOCK_R
        ty = self.title.pos().y()
        th = self.title.boundingRect().height()
        x  = int(ox - gap - icon_size)
        y  = int(ty + th / 2 - icon_size / 2)
        painter.save()
        painter.drawPixmap(x, y,
                           px.scaled(icon_size, icon_size,
                                     Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation))
        painter.restore()


# =========================================================
# AUDIO NODE
# =========================================================

from PyQt6.QtWidgets import QSlider, QStyle
from PyQt6.QtCore import QTimer, Qt as _Qt


# WaveformWidget — pure QPainter implementation (no QWebEngineView).
# QWebEngineView segfaults on PyQt6 6.4.x / macOS when QAudioOutput has
# already been imported in the same process (CoreAudio session conflict).
# SimpleWaveformWidget above provides identical visual output; this class
# is kept as a named alias so AudioNodeDialog can reference it unchanged.
class WaveformWidget(SimpleWaveformWidget):
    """QPainter waveform widget used by AudioNodeDialog.

    Inherits everything from SimpleWaveformWidget.  The ws_* stubs below
    keep AudioNodeDialog callers working without any if-branches.
    """

    # _web_ok is always False — AudioNodeDialog checks it before calling ws_*
    _web_ok = False

    def ws_play(self):  pass
    def ws_pause(self): pass
    def ws_stop(self):  pass
    def ws_seek(self, fraction): pass
    def ws_volume(self, vol):    pass


class AudioNodeDialog(QDialog):
    """Dialog for AudioNode: name + browser + real waveform + timeline + volume."""

    def __init__(self, parent, initial_name="Audio", audio_path=""):
        super().__init__(parent)
        from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
        self.setWindowTitle("Edit Audio Node")
        self.setMinimumSize(520, 480)
        self.setStyleSheet("background:#2a2a2a; color:#ffffff;")

        self._audio_path = audio_path

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ── Name ──────────────────────────────────────────────
        name_lbl = QLabel("Name  (visible on node):")
        name_lbl.setStyleSheet("color:#aaaaaa; font-size:11px;")
        layout.addWidget(name_lbl)
        self.name_edit = QLineEdit(initial_name)
        self.name_edit.setStyleSheet(
            "background:#1b1b1b; color:#ffffff; border:1px solid #5c5c5c;"
            " padding:4px; font-size:13px;")
        layout.addWidget(self.name_edit)

        # ── File row ──────────────────────────────────────────
        file_row = QHBoxLayout()
        self._path_label = QLabel(audio_path or "No audio loaded")
        self._path_label.setStyleSheet("color:#888888; font-size:10px;")
        self._path_label.setWordWrap(True)
        file_row.addWidget(self._path_label, 1)
        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse)
        file_row.addWidget(browse_btn)
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(60)
        clear_btn.clicked.connect(self._clear)
        file_row.addWidget(clear_btn)
        layout.addLayout(file_row)

        # ── Waveform ──────────────────────────────────────────
        self._waveform = WaveformWidget()
        layout.addWidget(self._waveform, 0, Qt.AlignmentFlag.AlignHCenter)

        # ── Timeline slider ───────────────────────────────────
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 1000)
        self._slider.setValue(0)
        self._slider.setEnabled(False)
        self._slider.setStyleSheet(self._slider_style("#4a9eff"))
        self._slider.sliderMoved.connect(self._seek)
        layout.addWidget(self._slider)

        self._time_label = QLabel("0:00 / 0:00")
        self._time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._time_label.setStyleSheet("color:#888888; font-size:10px;")
        layout.addWidget(self._time_label)

        # ── Transport + volume ────────────────────────────────
        ctrl_row = QHBoxLayout()
        self._play_btn  = QPushButton("▶ Play")
        self._pause_btn = QPushButton("⏸ Pause")
        self._stop_btn  = QPushButton("⏹ Stop")
        for btn in (self._play_btn, self._pause_btn, self._stop_btn):
            btn.setFixedHeight(28)
            btn.setEnabled(False)
            ctrl_row.addWidget(btn)

        ctrl_row.addSpacing(16)
        vol_lbl = _vol_icon_label(20)
        vol_lbl.setStyleSheet("color:#aaaaaa;")
        ctrl_row.addWidget(vol_lbl)
        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(80)
        self._vol_slider.setFixedWidth(90)
        self._vol_slider.setStyleSheet(self._slider_style("#aaaaaa"))
        self._vol_slider.valueChanged.connect(self._on_volume)
        ctrl_row.addWidget(self._vol_slider)
        layout.addLayout(ctrl_row)

        # ── Player ────────────────────────────────────────────
        self._player    = QMediaPlayer(self)
        self._audio_out = QAudioOutput(self)
        self._audio_out.setVolume(0.8)
        self._player.setAudioOutput(self._audio_out)
        self._duration  = 0

        self._play_btn.clicked.connect(self._ws_play)
        self._pause_btn.clicked.connect(self._ws_pause)
        self._stop_btn.clicked.connect(self._ws_stop)
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._player.positionChanged.connect(self._on_position)
        self._player.durationChanged.connect(self._on_duration)

        # ── OK / Cancel ───────────────────────────────────────
        btn_row = QHBoxLayout()
        ok = QPushButton("OK")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self._stop_player)
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self._stop_player)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(ok)
        btn_row.addWidget(cancel)
        layout.addLayout(btn_row)

        if audio_path:
            self._load_audio(audio_path)

    @staticmethod
    def _slider_style(color):
        return (
            f"QSlider::groove:horizontal {{ height:4px; background:#444; border-radius:2px; }}"
            f"QSlider::handle:horizontal {{ width:12px; height:12px; margin:-4px 0;"
            f" background:{color}; border-radius:6px; }}"
            f"QSlider::sub-page:horizontal {{ background:{color}; border-radius:2px; }}")

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio", "",
            "Audio (*.wav *.mp3 *.aac *.flac *.ogg *.m4a *.aiff *.wma);;All Files (*)")
        if path:
            self._audio_path = path
            self._path_label.setText(path)
            self._load_audio(path)

    def _clear(self):
        self._player.stop()
        self._player.setSource(QUrl())
        self._audio_path = ""
        self._path_label.setText("No audio loaded")
        self._waveform.load("")
        self._duration = 0
        self._slider.setValue(0)
        self._slider.setEnabled(False)
        self._time_label.setText("0:00 / 0:00")
        for btn in (self._play_btn, self._pause_btn, self._stop_btn):
            btn.setEnabled(False)

    def _load_audio(self, path):
        with suppress_media_stderr():
            self._player.setSource(QUrl.fromLocalFile(path))
        self._waveform.load(path)
        self._slider.setValue(0)
        self._time_label.setText("0:00 / 0:00")

    def _on_media_status(self, status):
        from PyQt6.QtMultimedia import QMediaPlayer
        loaded = status in (
            QMediaPlayer.MediaStatus.LoadedMedia,
            QMediaPlayer.MediaStatus.BufferedMedia,
            QMediaPlayer.MediaStatus.BufferingMedia,
        )
        if loaded:
            for btn in (self._play_btn, self._pause_btn, self._stop_btn):
                btn.setEnabled(True)
            self._slider.setEnabled(True)

    def _seek(self, value):
        if self._duration > 0:
            self._player.setPosition(int(value / 1000.0 * self._duration))

    def _on_position(self, pos_ms):
        if self._duration > 0:
            self._slider.blockSignals(True)
            self._slider.setValue(int(pos_ms / self._duration * 1000))
            self._slider.blockSignals(False)
        self._time_label.setText(f"{self._fmt(pos_ms)} / {self._fmt(self._duration)}")

    def _on_duration(self, dur_ms):
        self._duration = dur_ms
        self._time_label.setText(f"0:00 / {self._fmt(dur_ms)}")

    def _ws_play(self):
        self._player.play()

    def _ws_pause(self):
        self._player.pause()

    def _ws_stop(self):
        self._player.stop()

    def _on_volume(self, value):
        self._audio_out.setVolume(value / 100.0)

    @staticmethod
    def _fmt(ms):
        s = ms // 1000
        return f"{s // 60}:{s % 60:02d}"

    def _stop_player(self):
        self._player.stop()
        self._player.setSource(QUrl())

    def closeEvent(self, event):
        self._stop_player()
        super().closeEvent(event)

    def get_name(self):       return self.name_edit.text().strip() or "Audio"
    def get_audio_path(self): return self._audio_path


class AudioNode(Node):
    """A node that carries an audio file.  Inherits all shape/socket/color
    behaviour from Node; adds audio loading and a cyan 'A' badge when loaded."""

    def __init__(self, x=0, y=0, view=None, name="Audio"):
        super().__init__(x, y, view, name)
        self._node_type     = "audio"
        self._audio_path    = ""    # absolute path to loaded audio file
        self._inline_player = None  # InlineAudioPlayer instance or None

    def open_inline_player(self):
        if not self._audio_path or not self.scene():
            return
        view = self.scene().views()[0] if self.scene().views() else None
        if not view:
            return
        if self._inline_player is not None:
            self.close_inline_player()
        self._inline_player = InlineAudioPlayer(view, self)

    def close_inline_player(self):
        if self._inline_player is not None:
            self._inline_player.close()
            self._inline_player = None

    def itemChange(self, change, value):
        result = super().itemChange(change, value)
        if (change in (QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged,
                       QGraphicsItem.GraphicsItemChange.ItemScenePositionHasChanged)
                and self._inline_player is not None):
            self._inline_player.reposition()
        return result

    def mouseDoubleClickEvent(self, event):
        view = (self.scene().views()[0]
                if self.scene() and self.scene().views() else None)
        if not view:
            return

        dialog = AudioNodeDialog(view, self.title._plain, self._audio_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            old_name = self.title._plain
            old_path = self._audio_path

            new_name = dialog.get_name()
            new_path = dialog.get_audio_path()

            self.title._plain = new_name
            self.title.setPlainText(new_name)
            self._fit_to_text()
            self._audio_path = new_path
            self.update()

            if self.scene():
                self.scene()._push_undo({
                    "type":     "audio_node_edit",
                    "node":     self,
                    "old_name": old_name,
                    "new_name": new_name,
                    "old_path": old_path,
                    "new_path": new_path,
                })
                self.scene().mark_dirty()
        event.accept()

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width, self.height)

        if self.isSelected():
            glow_color = QColor(80, 170, 255, 35)
            for i in range(10):
                spread = i * 1.5
                c = QColor(glow_color)
                c.setAlpha(max(0, 35 - i * 4))
                painter.setPen(QPen(c, 1 + i))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                gr = rect.adjusted(-spread, -spread, spread, spread)
                self._draw_shape(painter, gr, spread)

        painter.setBrush(QBrush(self._color))
        painter.setPen(QPen(QColor(NODE_BORDER), 1.2))
        self._draw_shape(painter, rect, 0)

        if self.isSelected():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(255, 255, 255, 140), 2))
            self._draw_shape(painter, rect, 0)

        # SVG icon badge: white when audio loaded, black when empty
        self._draw_audio_icon(painter)

    _PNG_AUD_BLACK = None
    _PNG_AUD_WHITE = None

    @classmethod
    def _get_audio_renderers(cls):
        if cls._PNG_AUD_BLACK is None:
            _base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
            cls._PNG_AUD_BLACK = _svg_to_pixmap(os.path.join(_base, "audio_black.svg"))
            cls._PNG_AUD_WHITE = _svg_to_pixmap(os.path.join(_base, "audio_white.svg"))
        return cls._PNG_AUD_BLACK, cls._PNG_AUD_WHITE

    def _draw_audio_icon(self, painter):
        black_px, white_px = self._get_audio_renderers()
        px = white_px if self._audio_path else black_px
        if px.isNull():
            return
        icon_size = 56
        gap       = 10
        ox = self.width - self._SOCK_R
        ty = self.title.pos().y()
        th = self.title.boundingRect().height()
        x  = int(ox - gap - icon_size)
        y  = int(ty + th / 2 - icon_size / 2)
        painter.save()
        painter.drawPixmap(x, y,
                           px.scaled(icon_size, icon_size,
                                     Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation))
        painter.restore()


# =========================================================
# DOCUMENT NODE
# =========================================================

import subprocess
import platform
import mimetypes

from PyQt6.QtWidgets import QTextBrowser, QSizePolicy
from PyQt6.QtGui import QIcon


def _open_with_system(path):
    """Open a file with its default system application."""
    try:
        sys_name = platform.system()
        if sys_name == "Darwin":
            subprocess.Popen(["open", path])
        elif sys_name == "Windows":
            subprocess.Popen(["start", "", path], shell=True)
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        print(f"Could not open file: {e}")


def _file_preview_widget(path):
    """Return a widget that previews the file, or a QLabel placeholder."""
    if not path or not os.path.isfile(path):
        lbl = QLabel("No file loaded")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color:#666666; font-size:13px;")
        return lbl

    mime, _ = mimetypes.guess_type(path)
    ext = os.path.splitext(path)[1].lower()

    # ── Image ──────────────────────────────────────────────
    if mime and mime.startswith("image/"):
        pix = QPixmap(path)
        if not pix.isNull():
            view = ZoomPanImageView()
            view.load(pix)
            return view

    # ── Plain text / source code / markdown ────────────────
    text_exts = {".txt", ".md", ".py", ".js", ".ts", ".html", ".css",
                 ".json", ".xml", ".yaml", ".yml", ".csv", ".sh",
                 ".bat", ".c", ".cpp", ".h", ".rs", ".go", ".swift",
                 ".java", ".kt", ".rb", ".php", ".sql", ".toml", ".ini",
                 ".cfg", ".log"}
    if ext in text_exts or (mime and mime.startswith("text/")):
        try:
            with open(path, "r", errors="replace") as f:
                content = f.read(8000)   # first 8 KB
            browser = QTextBrowser()
            browser.setPlainText(content)
            browser.setStyleSheet(
                "background:#1b1b1b; color:#cccccc; font-family:monospace;"
                " font-size:11px; border:1px solid #5c5c5c;")
            browser.setMinimumHeight(220)
            return browser
        except Exception:
            pass

    # ── PDF thumbnail (first page rendered via QPdfDocument if available) ──
    if ext == ".pdf":
        try:
            from PyQt6.QtPdf import QPdfDocument
            doc = QPdfDocument(None)
            doc.load(path)
            if doc.pageCount() > 0:
                size = doc.pagePointSize(0)
                scale = min(460 / size.width(), 280 / size.height())
                img_size = QSize(int(size.width() * scale),
                                 int(size.height() * scale))
                img = doc.render(0, img_size)
                if not img.isNull():
                    pix = QPixmap.fromImage(img)
                    view = ZoomPanImageView()
                    view.load(pix)
                    return view
        except Exception:
            pass

    # ── Generic fallback: file info card ──────────────────
    size_bytes = os.path.getsize(path)
    size_str   = (f"{size_bytes / 1_048_576:.1f} MB" if size_bytes >= 1_048_576
                  else f"{size_bytes / 1024:.1f} KB" if size_bytes >= 1024
                  else f"{size_bytes} B")
    lbl = QLabel(
        f"📄  {os.path.basename(path)}\n\n"
        f"Type:  {mime or ext or 'Unknown'}\n"
        f"Size:  {size_str}\n\n"
        f"No preview available.\nDouble-click the node to open with system application.")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setWordWrap(True)
    lbl.setStyleSheet("color:#aaaaaa; font-size:12px; padding:20px;")
    return lbl


class DocumentNodeDialog(QDialog):
    """Dialog for DocumentNode: name + file browser + preview + open button."""

    def __init__(self, parent, initial_name="Document", doc_path=""):
        super().__init__(parent)
        self.setWindowTitle("Edit Document Node")
        self.setMinimumSize(520, 540)
        self.setStyleSheet("background:#2a2a2a; color:#ffffff;")

        self._doc_path = doc_path
        self._preview_widget = None

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ── Name ──────────────────────────────────────────────
        name_lbl = QLabel("Name  (visible on node):")
        name_lbl.setStyleSheet("color:#aaaaaa; font-size:11px;")
        layout.addWidget(name_lbl)
        self.name_edit = QLineEdit(initial_name)
        self.name_edit.setStyleSheet(
            "background:#1b1b1b; color:#ffffff; border:1px solid #5c5c5c;"
            " padding:4px; font-size:13px;")
        layout.addWidget(self.name_edit)

        # ── File browser row ──────────────────────────────────
        file_row = QHBoxLayout()
        self._path_label = QLabel(doc_path or "No file loaded")
        self._path_label.setStyleSheet("color:#888888; font-size:10px;")
        self._path_label.setWordWrap(True)
        file_row.addWidget(self._path_label, 1)

        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse)
        file_row.addWidget(browse_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(60)
        clear_btn.clicked.connect(self._clear)
        file_row.addWidget(clear_btn)

        layout.addLayout(file_row)

        # ── Open with system application button ───────────────
        open_btn = QPushButton("Open with System Application")
        open_btn.setFixedHeight(28)
        open_btn.clicked.connect(self._open_file)
        open_btn.setStyleSheet(
            "QPushButton { background:#3a3a3a; color:#ffffff; border:1px solid #5c5c5c;"
            " border-radius:4px; padding:0 12px; }"
            "QPushButton:hover { background:#4a9eff; }"
            "QPushButton:disabled { color:#555555; }")
        layout.addWidget(open_btn)
        self._open_btn = open_btn

        # ── Preview container ─────────────────────────────────
        self._preview_container = QVBoxLayout()
        self._preview_container.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._preview_container, 1)
        self._refresh_preview()

        # ── OK / Cancel ───────────────────────────────────────
        btn_row = QHBoxLayout()
        ok = QPushButton("OK")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(ok)
        btn_row.addWidget(cancel)
        layout.addLayout(btn_row)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select File", "", "All Files (*)")
        if path:
            self._doc_path = path
            self._path_label.setText(path)
            self._refresh_preview()

    def _clear(self):
        self._doc_path = ""
        self._path_label.setText("No file loaded")
        self._refresh_preview()

    def _open_file(self):
        if self._doc_path and os.path.isfile(self._doc_path):
            _open_with_system(self._doc_path)

    def _refresh_preview(self):
        # Remove old preview widget
        if self._preview_widget is not None:
            self._preview_container.removeWidget(self._preview_widget)
            self._preview_widget.setParent(None)
            self._preview_widget.deleteLater()
            self._preview_widget = None

        self._preview_widget = _file_preview_widget(self._doc_path)
        self._preview_container.addWidget(self._preview_widget)
        self._open_btn.setEnabled(bool(self._doc_path and
                                       os.path.isfile(self._doc_path)))

    def get_name(self):     return self.name_edit.text().strip() or "Document"
    def get_doc_path(self): return self._doc_path


class DocumentNode(Node):
    """A node that references an external file of any kind.
    Inherits all shape/socket/color behaviour from Node;
    adds a file browser, preview dialog, and a yellow 'D' badge."""

    def __init__(self, x=0, y=0, view=None, name="Document"):
        super().__init__(x, y, view, name)
        self._node_type = "doc"
        self._doc_path = ""
        self._inline_player = None

    def open_inline_player(self):
        if not self.scene():
            return
        view = self.scene().views()[0] if self.scene().views() else None
        if not view:
            return
        if self._inline_player is not None:
            self.close_inline_player()
        self._inline_player = InlineDocViewer(view, self)
    def close_inline_player(self):
        if self._inline_player is not None:
            self._inline_player.close()
            self._inline_player = None

    def itemChange(self, change, value):
        result = super().itemChange(change, value)
        if change in (QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged,
                      QGraphicsItem.GraphicsItemChange.ItemScenePositionHasChanged):
            if self._inline_player is not None:
                self._inline_player.reposition()
        return result

    def mouseDoubleClickEvent(self, event):
        view = (self.scene().views()[0]
                if self.scene() and self.scene().views() else None)
        if not view:
            return

        dialog = DocumentNodeDialog(view, self.title._plain, self._doc_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            old_name = self.title._plain
            old_path = self._doc_path
            new_name = dialog.get_name()
            new_path = dialog.get_doc_path()

            self.title._plain = new_name
            self.title.setPlainText(new_name)
            self._fit_to_text()
            self._doc_path = new_path
            self.update()

            if self.scene():
                self.scene()._push_undo({
                    "type":     "doc_node_edit",
                    "node":     self,
                    "old_name": old_name,
                    "new_name": new_name,
                    "old_path": old_path,
                    "new_path": new_path,
                })
                self.scene().mark_dirty()
        event.accept()

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width, self.height)

        if self.isSelected():
            glow_color = QColor(80, 170, 255, 35)
            for i in range(10):
                spread = i * 1.5
                c = QColor(glow_color)
                c.setAlpha(max(0, 35 - i * 4))
                painter.setPen(QPen(c, 1 + i))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                gr = rect.adjusted(-spread, -spread, spread, spread)
                self._draw_shape(painter, gr, spread)

        painter.setBrush(QBrush(self._color))
        painter.setPen(QPen(QColor(NODE_BORDER), 1.2))
        self._draw_shape(painter, rect, 0)

        if self.isSelected():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(255, 255, 255, 140), 2))
            self._draw_shape(painter, rect, 0)

        # SVG icon badge: white when document loaded, black when empty
        self._draw_doc_icon(painter)

    _PNG_DOC_BLACK = None
    _PNG_DOC_WHITE = None

    @classmethod
    def _get_doc_renderers(cls):
        if cls._PNG_DOC_BLACK is None:
            _base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
            cls._PNG_DOC_BLACK = _svg_to_pixmap(os.path.join(_base, "doc_black.svg"))
            cls._PNG_DOC_WHITE = _svg_to_pixmap(os.path.join(_base, "doc_white.svg"))
        return cls._PNG_DOC_BLACK, cls._PNG_DOC_WHITE

    def _draw_doc_icon(self, painter):
        black_px, white_px = self._get_doc_renderers()
        px = white_px if self._doc_path else black_px
        if px.isNull():
            return
        icon_size = 56
        gap       = 10
        ox = self.width - self._SOCK_R
        ty = self.title.pos().y()
        th = self.title.boundingRect().height()
        x  = int(ox - gap - icon_size)
        y  = int(ty + th / 2 - icon_size / 2)
        painter.save()
        painter.drawPixmap(x, y,
                           px.scaled(icon_size, icon_size,
                                     Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation))
        painter.restore()
