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
# CURVE  –  Connections, Sockets, Dots
# =========================================================

import math

from PyQt6.QtWidgets import QGraphicsPathItem, QGraphicsEllipseItem, QGraphicsItem, QMenu
from PyQt6.QtGui import QColor, QPen, QBrush, QPainter, QPainterPath, QPainterPathStroker
from PyQt6.QtCore import Qt, QRectF, QPointF

from utils import (
    DRAG_STATE, _bezier_path, _make_temp_line, _remove_from, _normalise,
    _menu_style, _global_point, open_color_wheel,
    SOCKET_COLOR, LINE_COLOR, LINE_SELECTED_COLOR,
    SOCKET_SIZE, DOT_RADIUS, NODE_BG,
)


# =========================================================
# DRAG HELPERS
# =========================================================

def _drag_move(cursor):
    drag = DRAG_STATE["active"]
    if not drag:
        return
    scene        = drag["line"].scene()
    free_end     = drag["free_end"]
    fixed_socket = drag["fixed_socket"]

    hovered = None
    for item in scene.items(cursor):
        if isinstance(item, Socket) and item is not fixed_socket:
            if item.parent_node is not fixed_socket.parent_node:
                hovered = item
                break
    drag["hover_socket"] = hovered
    end = hovered.scenePos() if hovered else cursor

    if fixed_socket.is_input:
        p_out, p_in = end, fixed_socket.scenePos()
    else:
        p_out, p_in = fixed_socket.scenePos(), end
    drag["line"].setPath(_bezier_path(p_out, p_in))

    if drag["conn"]:
        drag["conn"].update_path(cursor, free_end)


def _drag_release(scene):
    drag = DRAG_STATE["active"]
    if not drag:
        return
    target       = drag["hover_socket"]
    conn         = drag["conn"]
    free_end     = drag["free_end"]
    fixed_socket = drag["fixed_socket"]

    if drag["line"]:
        scene.removeItem(drag["line"])

    if target and target.parent_node is not fixed_socket.parent_node:
        out_sock, in_sock = _normalise(fixed_socket, target)
        if conn:
            old_a, old_b = conn.a, conn.b
            conn.a = out_sock
            conn.b = in_sock
            target.connections.append(conn)
            conn.update_path()
            scene._push_undo({
                "type": "rehook", "conn": conn,
                "old_a": old_a, "old_b": old_b,
                "new_a": out_sock, "new_b": in_sock,
            })
        else:
            new_conn = ConnectionLine(out_sock, in_sock)
            scene.addItem(new_conn)
            out_sock.connections.append(new_conn)
            in_sock.connections.append(new_conn)
            scene._push_undo({"type": "add_conn", "conn": new_conn})
    else:
        if conn:
            _remove_from(fixed_socket.connections, conn)
            scene.removeItem(conn)
            scene._push_undo({
                "type": "del_conn", "conn": conn,
                "a": conn.a, "b": conn.b,
            })
    DRAG_STATE["active"] = None


# =========================================================
# SOCKET  –  2x size
# =========================================================

class Socket(QGraphicsEllipseItem):

    def __init__(self, parent, is_input=False):
        super().__init__()
        self.parent_node = parent
        self.is_input    = is_input
        self.connections = []
        s = SOCKET_SIZE * 2          # 2x size
        self.setRect(-s, -s, s * 2, s * 2)
        self.setBrush(QBrush(QColor(SOCKET_COLOR)))
        self.setPen(QPen(QColor("#111111"), 1))
        self.setParentItem(parent)
        self.setZValue(1000)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)

    def update_connections(self):
        for conn in self.connections:
            conn.update_path()

    def update_from_settings(self, settings, force=False):
        if "socket_color" in settings:
            self.setBrush(QBrush(QColor(settings["socket_color"])))
            self.update()

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            event.accept()
            return
        DRAG_STATE["active"] = {
            "conn":         None,
            "free_end":     "b",
            "fixed_socket": self,
            "line":         _make_temp_line(self.scene()),
            "hover_socket": None,
        }
        event.accept()

    def mouseMoveEvent(self, event):
        if DRAG_STATE["active"]:
            _drag_move(event.scenePos())
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and DRAG_STATE["active"]:
            _drag_release(self.scene())
        event.accept()


# =========================================================
# CONNECTION LINE
# =========================================================

class ConnectionLine(QGraphicsPathItem):

    CURVE_BEZIER      = "bezier"
    CURVE_LINE        = "line"
    CURVE_STEP        = "step"
    LINE_STYLE_SOLID  = "solid"
    LINE_STYLE_DOTTED = "dotted"
    LINE_STYLE_DASHED = "dashed"

    def __init__(self, a, b):
        super().__init__()
        self.a = a
        self.b = b
        self.curve_type   = self.CURVE_BEZIER
        self._line_color  = QColor(LINE_COLOR)
        self._line_style  = self.LINE_STYLE_SOLID
        self._thickness   = 2
        # Per-attribute dirty flags — set True when user explicitly customises
        # that attribute so theme switches no longer override it.
        self._color_locked     = False
        self._style_locked     = False
        self._thickness_locked = False
        self.setZValue(900)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.update_path()

        # Apply current scene settings immediately if available
        scene = a.scene() if a else None
        if scene and hasattr(scene, '_current_settings') and scene._current_settings:
            self.update_from_settings(scene._current_settings)

    def update_from_settings(self, settings, force=False):
        """Apply global curve defaults from the Settings dialog.
        force=True means a theme switch — only the color is updated, and only
        when the user has not individually customised it (_color_locked=False).
        All other attributes (type, style, thickness) are always preserved."""
        if force:
            # Theme switch: only update color on curves that still have the
            # theme default (i.e. the user never picked a custom color).
            if not self._color_locked and "curve_color" in settings:
                self._line_color = QColor(settings["curve_color"])
                self.update_path()
                self.update()
            return
        # New curve getting its initial defaults — apply everything.
        if "curve_color" in settings:
            self._line_color = QColor(settings["curve_color"])
        if "curve_type" in settings:
            self.curve_type = settings["curve_type"]
        if "curve_thickness" in settings:
            self._thickness = int(settings["curve_thickness"])
        if "curve_style" in settings:
            self._apply_style_str(settings["curve_style"])
        self.update_path()
        self.update()

    def _apply_style_str(self, style):
        """Convert a style name string to the internal line-style constant."""
        s = style.lower()
        if s == "solid":
            self._line_style = self.LINE_STYLE_SOLID
        elif s in ("dash", "dashed"):
            self._line_style = self.LINE_STYLE_DASHED
        elif s in ("dot", "dotted"):
            self._line_style = self.LINE_STYLE_DOTTED
        else:
            self._line_style = s

    def update_path(self, free_pos=None, free_end=None):
        if free_pos and free_end == "a":
            p_out, p_in = free_pos, self.b.scenePos()
        elif free_pos and free_end == "b":
            p_out, p_in = self.a.scenePos(), free_pos
        else:
            p_out, p_in = self.a.scenePos(), self.b.scenePos()

        # issue 8: bezier direction follows socket orientation
        def _sock_orient(sock):
            parent = sock.parent_node
            if parent and hasattr(parent, '_orientation'):
                return parent._orientation
            return "left-right"

        out_orient = _sock_orient(self.a)
        in_orient  = _sock_orient(self.b)

        if self.curve_type == self.CURVE_LINE:
            path = QPainterPath(p_out)
            path.lineTo(p_in)
        elif self.curve_type == self.CURVE_STEP:
            mid_x = (p_out.x() + p_in.x()) / 2
            path  = QPainterPath(p_out)
            path.lineTo(QPointF(mid_x, p_out.y()))
            path.lineTo(QPointF(mid_x, p_in.y()))
            path.lineTo(p_in)
        else:
            path = _bezier_path(p_out, p_in, out_orient, in_orient)
        self.setPath(path)

    def shape(self):
        stroker = QPainterPathStroker()
        stroker.setWidth(12)
        return stroker.createStroke(self.path())

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        dash_pattern = [4, 4]

        if self._line_style == self.LINE_STYLE_DOTTED:
            pen = QPen(self._line_color, self._thickness, Qt.PenStyle.DotLine)
        elif self._line_style == self.LINE_STYLE_DASHED:
            pen = QPen(self._line_color, self._thickness, Qt.PenStyle.CustomDashLine)
            pen.setDashPattern(dash_pattern)
        else:
            pen = QPen(self._line_color, self._thickness)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        if self.isSelected():
            glow = QColor(80, 170, 255)
            for i in range(8):
                c = QColor(glow)
                c.setAlpha(max(0, 40 - i * 5))
                gp = QPen(c, self._thickness + i * 1.5)
                gp.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(gp)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(self.path())

            if self._line_style == self.LINE_STYLE_DASHED:
                pen = QPen(QColor(LINE_SELECTED_COLOR), self._thickness + 0.5, Qt.PenStyle.CustomDashLine)
                pen.setDashPattern(dash_pattern)
            elif self._line_style == self.LINE_STYLE_DOTTED:
                pen = QPen(QColor(LINE_SELECTED_COLOR), self._thickness + 0.5, Qt.PenStyle.DotLine)
            else:
                pen = QPen(QColor(LINE_SELECTED_COLOR), self._thickness + 0.5)

            pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path())

        # ── Arrowhead at the tip (b / input end) ──────────────
        self._draw_arrowhead(painter, pen)

        # ── Cover the curve inside both sockets with socket colour ──
        self._paint_socket_caps(painter)

    def _draw_arrowhead(self, painter, pen):
        """Draw a filled arrowhead polygon just outside the b-socket (input) circle."""
        import math
        path = self.path()
        if path.isEmpty():
            return

        # Sample two close points near the end of the path to get the tangent direction
        t_tip  = path.pointAtPercent(1.0)
        t_back = path.pointAtPercent(0.97)

        dx = t_tip.x() - t_back.x()
        dy = t_tip.y() - t_back.y()
        length = math.hypot(dx, dy)
        if length == 0:
            return

        # Unit vector along the curve direction at the tip
        ux, uy = dx / length, dy / length

        arrow_len  = 12   # px — length of the arrowhead
        arrow_half = 5    # px — half-width at the base

        # The path ends at the socket centre; pull the arrowhead back so its
        # tip sits flush with the outer edge of the socket circle (radius = SOCKET_SIZE*2).
        socket_r = SOCKET_SIZE * 2   # 16 px

        tip_x = t_tip.x() - ux * socket_r
        tip_y = t_tip.y() - uy * socket_r
        tip   = QPointF(tip_x, tip_y)

        # Base centre (step back from tip along the curve)
        base_cx = tip_x - ux * arrow_len
        base_cy = tip_y - uy * arrow_len

        # Left and right base corners (perpendicular to the curve)
        left  = QPointF(base_cx - uy * arrow_half, base_cy + ux * arrow_half)
        right = QPointF(base_cx + uy * arrow_half, base_cy - ux * arrow_half)

        arrow = QPainterPath()
        arrow.moveTo(tip)
        arrow.lineTo(left)
        arrow.lineTo(right)
        arrow.closeSubpath()

        painter.setPen(QPen(pen.color(), 1))
        painter.setBrush(QBrush(pen.color()))
        painter.drawPath(arrow)

    def _paint_socket_caps(self, painter):
        """Paint filled circles over both socket centres so the curve line
        inside each socket appears in the socket colour, not the line colour."""
        border_color = QColor("#111111")
        r = SOCKET_SIZE * 2   # matches Socket.__init__ radius (16 px)

        for sock in (self.a, self.b):
            # Read colour live from the Socket's brush so settings changes apply
            socket_color = sock.brush().color() if sock.brush().color().isValid() else QColor(SOCKET_COLOR)
            centre = sock.scenePos()
            local  = self.mapFromScene(centre)
            painter.setPen(QPen(border_color, 1))
            painter.setBrush(QBrush(socket_color))
            painter.drawEllipse(local, r, r)

    def contextMenuEvent(self, event):
        view = self.scene().views()[0] if self.scene() and self.scene().views() else None
        if not view:
            return
        menu = QMenu(view)
        menu.setStyleSheet(_menu_style())

        ct = menu.addMenu("Edit Curve Type")
        ct.addAction("Bezier").triggered.connect(lambda: self._set_curve_type(self.CURVE_BEZIER))
        ct.addAction("Line").triggered.connect(lambda: self._set_curve_type(self.CURVE_LINE))
        ct.addAction("Step").triggered.connect(lambda: self._set_curve_type(self.CURVE_STEP))

        ls = menu.addMenu("Edit Line Style")
        ls.addAction("Solid").triggered.connect(lambda: self._set_line_style(self.LINE_STYLE_SOLID))
        ls.addAction("Dotted").triggered.connect(lambda: self._set_line_style(self.LINE_STYLE_DOTTED))
        ls.addAction("Dashed").triggered.connect(lambda: self._set_line_style(self.LINE_STYLE_DASHED))

        menu.addAction("Edit Color").triggered.connect(lambda: self._pick_color(view))
        menu.addAction("Edit Width...").triggered.connect(lambda: self._pick_width(view))
        event.accept()
        menu.exec(_global_point(event.screenPos()))

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        # Cmd+Click (⌘) → split at click point
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self._split_at(event.scenePos())
            event.accept()
            return

        cursor = event.scenePos()
        dist_a = (cursor - self.a.scenePos()).manhattanLength()
        dist_b = (cursor - self.b.scenePos()).manhattanLength()
        # 50px unhook radius in display (screen) space – scale to scene space
        scene = self.scene()
        view = scene.views()[0] if scene and scene.views() else None
        display_radius = 100
        scale = view.transform().m11() if view else 1.0
        socket_r = display_radius / scale if scale > 0 else display_radius

        if (dist_a <= socket_r or dist_b <= socket_r) and self.isSelected():
            if dist_a <= socket_r:
                fixed_socket = self.b
                free_end = "a"
                _remove_from(self.a.connections, self)
            else:
                fixed_socket = self.a
                free_end = "b"
                _remove_from(self.b.connections, self)

            DRAG_STATE["active"] = {
                "conn":         self,
                "free_end":     free_end,
                "fixed_socket": fixed_socket,
                "line":         _make_temp_line(self.scene()),
                "hover_socket": None,
            }

            if free_end == "b":
                DRAG_STATE["active"]["line"].setPath(
                    _bezier_path(self.a.scenePos(), cursor))
            else:
                DRAG_STATE["active"]["line"].setPath(
                    _bezier_path(cursor, self.b.scenePos()))
            event.accept()
            return

        if dist_a >= 20 and dist_b >= 20:
            super().mousePressEvent(event)
            return

        if not self.isSelected():
            super().mousePressEvent(event)
            return

        free_end = "a" if dist_a <= dist_b else "b"
        if free_end == "a":
            fixed_socket = self.b
            _remove_from(self.a.connections, self)
        else:
            fixed_socket = self.a
            _remove_from(self.b.connections, self)

        DRAG_STATE["active"] = {
            "conn":         self,
            "free_end":     free_end,
            "fixed_socket": fixed_socket,
            "line":         _make_temp_line(self.scene()),
            "hover_socket": None,
        }
        if free_end == "b":
            DRAG_STATE["active"]["line"].setPath(
                _bezier_path(self.a.scenePos(), cursor))
        else:
            DRAG_STATE["active"]["line"].setPath(
                _bezier_path(cursor, self.b.scenePos()))
        event.accept()

    def mouseMoveEvent(self, event):
        drag = DRAG_STATE["active"]
        if drag and drag["conn"] is self:
            _drag_move(event.scenePos())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        drag = DRAG_STATE["active"]
        if event.button() == Qt.MouseButton.LeftButton and drag and drag["conn"] is self:
            _drag_release(self.scene())
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _set_curve_type(self, ct):
        scene = self.scene()
        if scene:
            scene._push_undo({"type": "curve_type", "conn": self,
                               "old": self.curve_type, "new": ct})
        self.curve_type = ct
        self.update_path()

    def _set_line_style(self, ls):
        scene = self.scene()
        if scene:
            scene._push_undo({"type": "line_style", "conn": self,
                               "old": self._line_style, "new": ls})
        self._line_style   = ls
        self._style_locked = True
        self.update()

    def _pick_color(self, parent):
        color = open_color_wheel(parent, self._line_color.name())
        if color:
            old = QColor(self._line_color)
            self._line_color   = color
            self._color_locked = True
            if self.scene():
                self.scene()._push_undo({"type": "curve_color", "conn": self,
                                         "old": old, "new": color})
            self.update()

    def _pick_width(self, parent):
        from PyQt6.QtWidgets import QInputDialog
        w, ok = QInputDialog.getInt(
            parent, "Line Width", "Width:", self._thickness, 1, 100)
        if ok:
            old = self._thickness
            self._thickness        = w
            self._thickness_locked = True
            if self.scene() and hasattr(self.scene(), '_push_undo'):
                self.scene()._push_undo({"type": "curve_width", "conn": self,
                                         "old": old, "new": w})
            self.update()

    def _split_at(self, scene_pos):
        scene = self.scene()
        if not scene:
            return
        view = scene.views()[0] if scene.views() else None
        dot = Dot(scene_pos.x(), scene_pos.y(), view)
        scene.addItem(dot)
        _remove_from(self.a.connections, self)
        _remove_from(self.b.connections, self)
        scene.removeItem(self)
        c1 = ConnectionLine(self.a, dot.in_socket)
        c2 = ConnectionLine(dot.out_socket, self.b)
        for c in (c1, c2):
            scene.addItem(c)
        self.a.connections.append(c1)
        dot.in_socket.connections.append(c1)
        dot.out_socket.connections.append(c2)
        self.b.connections.append(c2)
        scene._push_undo({
            "type": "split_curve", "dot": dot,
            "c1": c1, "c2": c2, "original": self,
            "orig_a": self.a, "orig_b": self.b,
        })

    def disconnect_from_sockets(self):
        _remove_from(self.a.connections, self)
        _remove_from(self.b.connections, self)


# =========================================================
# DOT
# Orientations: "left-right" | "right-left" | "top-bottom" | "bottom-top"
# =========================================================

_DOT_ORIENTATION_OFFSETS = {
    "left-right":  ((-1, 0), (1, 0)),
    "right-left":  ((1, 0),  (-1, 0)),
    "top-bottom":  ((0, -1), (0, 1)),
    "bottom-top":  ((0, 1),  (0, -1)),
}


class Dot(QGraphicsItem):

    def __init__(self, x=0, y=0, view=None):
        super().__init__()
        self.view = view
        self.setPos(x, y)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable      |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable   |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setZValue(5)
        self._orientation = "left-right"
        self._color = QColor(NODE_BG)
        self._color_locked = False

        self.in_socket  = Socket(self, True)
        self.out_socket = Socket(self, False)
        self._apply_orientation()

    def update_from_settings(self, settings, force=False):
        if "dot_color" in settings and not self._color_locked:
            self._color = QColor(settings["dot_color"])
        if "dot_orientation" in settings:
            self._orientation = settings["dot_orientation"]
            self._apply_orientation()
        self.update()

    def _apply_orientation(self):
        r = DOT_RADIUS
        offsets = _DOT_ORIENTATION_OFFSETS.get(self._orientation, ((-1, 0), (1, 0)))
        ix, iy = offsets[0]
        ox, oy = offsets[1]
        self.in_socket.setPos(ix * r, iy * r)
        self.out_socket.setPos(ox * r, oy * r)
        self.in_socket.update_connections()
        self.out_socket.update_connections()

    def boundingRect(self):
        r = DOT_RADIUS + 20
        return QRectF(-r, -r, r * 2, r * 2)

    def contains(self, point):
        return (point.x() ** 2 + point.y() ** 2) <= DOT_RADIUS ** 2

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.in_socket.update_connections()
            self.out_socket.update_connections()
            if self.scene():
                self.scene().mark_dirty()
        return super().itemChange(change, value)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = DOT_RADIUS
        if self.isSelected():
            glow = QColor(80, 170, 255)
            for i in range(6):
                c = QColor(glow)
                c.setAlpha(max(0, 40 - i * 7))
                painter.setPen(QPen(c, 1 + i))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPointF(0, 0), r + i, r + i)
        painter.setBrush(QBrush(self._color))
        painter.setPen(QPen(QColor("#111111"), 1.2))
        painter.drawEllipse(QPointF(0, 0), r, r)

    def mousePressEvent(self, event):
        # Cmd+Left Click (⌘) → disconnect / merge curves
        if (event.button() == Qt.MouseButton.LeftButton and
                event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self._disconnect_curves()
            event.accept()
            return
        super().mousePressEvent(event)

    def _disconnect_curves(self):
        scene = self.scene()
        if not scene:
            return
        in_c  = list(self.in_socket.connections)
        out_c = list(self.out_socket.connections)
        if len(in_c) == 1 and len(out_c) == 1:
            # merge: delegate to scene's delete_dot which handles undo properly
            scene._delete_dot(self)
        else:
            for conn in in_c + out_c:
                conn.disconnect_from_sockets()
                scene.removeItem(conn)
            scene.removeItem(self)
            scene.mark_dirty()

    def contextMenuEvent(self, event):
        view = (self.scene().views()[0]
                if self.scene() and self.scene().views() else None)
        if not view:
            event.ignore()
            return
        menu = QMenu(view)
        menu.setStyleSheet(_menu_style())

        orient_menu = menu.addMenu("Edit Orientation")
        _labels = {
            "left-right":  "Left → Right",
            "right-left":  "Right → Left",
            "top-bottom":  "Top → Bottom",
            "bottom-top":  "Bottom → Top",
        }
        for o, label in _labels.items():
            orient_menu.addAction(label).triggered.connect(
                lambda checked, ov=o: self._set_orientation(ov))

        menu.addAction("Edit Dot Color").triggered.connect(
            lambda: self._pick_color(view))

        event.accept()
        menu.exec(_global_point(event.screenPos()))

    def _set_orientation(self, orientation):
        old = self._orientation
        self._orientation = orientation
        self._apply_orientation()
        self.update()
        if self.scene():
            self.scene()._push_undo({
                "type": "dot_orientation", "dot": self,
                "old": old, "new": orientation,
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
                    "type": "dot_color", "dot": self,
                    "old": old, "new": color,
                })
                self.scene().mark_dirty()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        # issue 15+18: splitting happens on release only

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self._try_split_on_release()

    def _try_split_on_release(self):
        scene = self.scene()
        if not scene:
            return
        # issue 18: skip if already connected
        if self.in_socket.connections or self.out_socket.connections:
            return
        center = self.mapToScene(0, 0)
        check_rect = QRectF(center.x() - 5, center.y() - 5, 10, 10)
        for item in scene.items(check_rect):
            if isinstance(item, ConnectionLine):
                if item.a.parent_node is self or item.b.parent_node is self:
                    continue
                self._split_curve_at(item, center)
                break

    def _split_curve_at(self, curve, split_point):
        scene = self.scene()
        if not scene:
            return

        _remove_from(curve.a.connections, curve)
        _remove_from(curve.b.connections, curve)
        scene.removeItem(curve)

        c1 = ConnectionLine(curve.a, self.in_socket)
        c1.curve_type  = curve.curve_type
        c1._line_color = curve._line_color
        c1._line_style = curve._line_style

        c2 = ConnectionLine(self.out_socket, curve.b)
        c2.curve_type  = curve.curve_type
        c2._line_color = curve._line_color
        c2._line_style = curve._line_style

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
