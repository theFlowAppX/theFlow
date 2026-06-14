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

# backdrop.py
# =========================================================
# BACKDROP  –  Visual Grouping Enclosures with Live Updates
# =========================================================

from PyQt6.QtWidgets import QGraphicsItem, QLineEdit, QMenu, QColorDialog, QInputDialog
from PyQt6.QtGui import QColor, QPen, QBrush, QFont, QTextOption, QPainter
from PyQt6.QtCore import Qt, QRectF, QPointF

from utils import HANDLE_SIZE, MAX_FONT_SIZE, open_color_wheel, _menu_style, _global_point, RichTextEditDialog
from note import ResizeHandle


class BackdropResizeHandle(ResizeHandle):

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        # Snapshot scene positions of all pinned children at drag start
        p = self.parentItem()
        self._child_scene_positions = {}
        if p and hasattr(p, '_pinned_children'):
            for child in p._pinned_children:
                self._child_scene_positions[child] = child.scenePos()

    def mouseMoveEvent(self, event):
        if self._dragging:
            p = self.parentItem()
            if not p:
                return
            delta = event.scenePos() - self._start_pos
            orig_pos, orig_size = self._start_geometry

            w = orig_size.width()
            h = orig_size.height()
            x = orig_pos.x()
            y = orig_pos.y()

            if "right" in self.corner:
                w = max(100, w + delta.x())
            if "bottom" in self.corner:
                h = max(80,  h + delta.y())
            if "left" in self.corner:
                diff = min(delta.x(), w - 100)
                x += diff
                w -= diff
            if "top" in self.corner:
                diff = min(delta.y(), h - 80)
                y += diff
                h -= diff

            p.prepareGeometryChange()
            p.setPos(x, y)
            p.width  = w
            p.height = h
            if hasattr(p, '_reposition_handles'):
                p._reposition_handles()
            p.update()

            # Restore every child to its original scene position
            for child, scene_pos in self._child_scene_positions.items():
                child.setPos(p.mapFromScene(scene_pos))

            if p.scene():
                p.scene().mark_dirty()
            event.accept()
            return
        super(ResizeHandle, self).mouseMoveEvent(event)


class Backdrop(QGraphicsItem):

    def __init__(self, x=0, y=0, view=None):
        super().__init__()
        self.view        = view
        self.width       = 600
        self.height      = 400
        self._color      = QColor(60, 60, 80, 160)
        self._font_size  = 80
        self._font_color = QColor(255, 255, 255)
        self._color_locked = False
        self._name       = "Backdrop"
        self._text       = ""
        self._pinned_children = set()

        self.setPos(x, y)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable      |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable   |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setZValue(0)

        self._handle_size = HANDLE_SIZE
        self._handles: dict = {}
        self._create_handles()

    # ── LIVE UPDATE SETTINGS HOOK ────────────────────────────────────
    def update_from_settings(self, settings, force=False):
        """Pulls updated theme color modifications dynamically into the backdrop layout."""
        if "backdrop_color" in settings and not self._color_locked:
            # Reconstruct the color with an explicit alpha channel to maintain opacity layout properties
            base_color = QColor(settings["backdrop_color"])
            self._color = QColor(base_color.red(), base_color.green(), base_color.blue(), 160)
        if "backdrop_font_size" in settings:
            self._font_size = int(settings["backdrop_font_size"])
        if "backdrop_font_color" in settings:
            self._font_color = QColor(settings["backdrop_font_color"])
            
        self.update()  # Force canvas redraw

    def _create_handles(self):
        for c in ["top-left", "top-right", "bottom-left", "bottom-right"]:
            h = BackdropResizeHandle(self, c)
            self._handles[c] = h
        self._reposition_handles()

    def _reposition_handles(self):
        hs = self._handle_size
        self._handles["top-left"].setPos(0, 0)
        self._handles["top-right"].setPos(self.width - hs, 0)
        self._handles["bottom-left"].setPos(0, self.height - hs)
        self._handles["bottom-right"].setPos(self.width - hs, self.height - hs)

    def boundingRect(self):
        return QRectF(-15, -15, self.width + 30, self.height + 30)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width, self.height)

        # Fill — lighter when selected
        if self.isSelected():
            c = self._color
            lighter = QColor(min(255, c.red() + 40), min(255, c.green() + 40),
                             min(255, c.blue() + 40), c.alpha())
            painter.setBrush(QBrush(lighter))
        else:
            painter.setBrush(QBrush(self._color))
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1.5, Qt.PenStyle.SolidLine))
        painter.drawRoundedRect(rect, 12, 12)

        margin = 20
        painter.setPen(QPen(self._font_color))

        # Name — bold, top-left
        painter.setFont(QFont("Arial", int(self._font_size), QFont.Weight.Bold))
        header_rect = QRectF(rect.left() + margin, rect.top() + margin,
                             rect.width() - margin * 2, self._font_size * 2)
        painter.drawText(header_rect,
                         Qt.TextFlag.TextSingleLine |
                         Qt.AlignmentFlag.AlignTop  |
                         Qt.AlignmentFlag.AlignLeft,
                         self._name)

        # Body text — plain, word-wrapped
        if self._text:
            painter.setFont(QFont("Arial", int(self._font_size)))
            body_rect = QRectF(rect.left() + margin, header_rect.bottom() + 6,
                               rect.width() - margin * 2,
                               rect.bottom() - margin - header_rect.bottom() - 6)
            opt = QTextOption(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            opt.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
            painter.drawText(body_rect, self._text, opt)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged or \
           change == QGraphicsItem.GraphicsItemChange.ItemTransformHasChanged:
            if self.scene():
                self.scene().mark_dirty()
            self._refresh_curves_recursive()
        return super().itemChange(change, value)

    def _refresh_curves_recursive(self):
        """Walk all pinned children at every nesting depth and update their curves and inline viewers."""
        def _walk(children):
            for child in children:
                if hasattr(child, 'in_socket'):
                    child.in_socket.update_connections()
                if hasattr(child, 'out_socket'):
                    child.out_socket.update_connections()
                for attr in ('_inline_viewer', '_inline_player', '_inline_text_viewer'):
                    viewer = getattr(child, attr, None)
                    if viewer is not None:
                        try:
                            viewer.reposition()
                        except Exception:
                            pass
                if isinstance(child, Backdrop):
                    _walk(child._pinned_children)
        _walk(self._pinned_children)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            dlg = RichTextEditDialog(self.view or event.widget(), self._name, self._text,
                                     initial_font_size=self._font_size)
            if dlg.exec():
                old_name = self._name
                old_text = self._text
                old_fs   = self._font_size
                new_name = dlg.get_name()
                new_text = dlg.get_plain()
                new_fs   = dlg.get_font_size()
                if old_name != new_name or old_text != new_text or old_fs != new_fs:
                    self._name = new_name
                    self._text = new_text
                    self._font_size = new_fs
                    self.update()
                    if self.scene():
                        self.scene().mark_dirty()
                        if hasattr(self.scene(), '_push_undo'):
                            self.scene()._push_undo({
                                "type": "backdrop_label", "item": self,
                                "old": (old_name, old_text, old_fs),
                                "new": (new_name, new_text, new_fs),
                            })
            return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        view = self.view or event.widget()
        menu = QMenu(view)
        menu.setStyleSheet(_menu_style())

        menu.addAction("Edit Backdrop Color").triggered.connect(
            lambda: self._pick_color(view))
        menu.addAction("Edit Font Size").triggered.connect(
            lambda: self._change_font(view))
        menu.addAction("Edit Font Color").triggered.connect(
            lambda: self._pick_font_color(view))

        event.accept()
        menu.exec(_global_point(event.screenPos()))

    def _pick_color(self, parent):
        old = QColor(self._color)
        color = open_color_wheel(parent, self._color.name(QColor.NameFormat.HexArgb))
        if color:
            # Enforce backdrop translucency bounds so layered nodes stay clearly visible
            self._color = QColor(color.red(), color.green(), color.blue(), 160)
            self._color_locked = True
            self.update()
            if self.scene() and hasattr(self.scene(), '_push_undo'):
                self.scene()._push_undo({
                    "type": "backdrop_color", "item": self,
                    "old": old, "new": self._color,
                })

    def _change_font(self, parent):
        old = self._font_size
        sz, ok = QInputDialog.getInt(
            parent, "Font Size", "Size:", self._font_size, 6, 100000)
        if ok:
            self._font_size = sz
            self.update()
            if self.scene() and hasattr(self.scene(), '_push_undo'):
                self.scene()._push_undo({
                    "type": "backdrop_font_size", "item": self,
                    "old": old, "new": sz,
                })

    def _pick_font_color(self, parent):
        old = QColor(self._font_color)
        color = QColorDialog.getColor(self._font_color, parent, "Select Text Contrast Color")
        if color.isValid():
            self._font_color = color
            self.update()
            if self.scene() and hasattr(self.scene(), '_push_undo'):
                self.scene()._push_undo({
                    "type": "backdrop_font_color", "item": self,
                    "old": old, "new": color,
                })