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

# view_logic.py
# =========================================================
# VIEW LOGIC FOR THEFLOW!
# =========================================================

import os

from PyQt6.QtWidgets import (
    QGraphicsView, QMessageBox, QFileDialog, QDialog,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QInputDialog, QColorDialog
)
from PyQt6.QtGui import QColor, QPainter, QFont, QPalette, QIcon
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer

from config import APP_NAME, DARK, LIGHT, SHORTCUTS
from scene_logic import Scene
from ui_components import TabCreationMenu
from menu import build_menu
from logo import LogoOverlay
from settings import SettingsDialog
from paint_on_canvas import CanvasPainter

# --- Corrected Imports from Separate Modules ---
from node import Node, ImageNode, MovieNode, AudioNode, DocumentNode
from paint import PaintNode
from curve import ConnectionLine, Dot
from backdrop import Backdrop
from note import StickyNote
from utils import _menu_style, _global_point, open_color_wheel

class View(QGraphicsView):
    def __init__(self):
        super().__init__()
        self._scene = Scene()
        self._scene._view = self

        # Logo overlay
        self._logo = LogoOverlay(self)

        # View Setup
        self.setScene(self._scene)
        self.setSceneRect(-100000, -100000, 200000, 200000)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QColor(DARK["bg"]))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setRubberBandSelectionMode(Qt.ItemSelectionMode.ContainsItemShape)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        # State
        self._panning = False
        self._pan_start = None
        self._filepath = None
        self._drag_start_positions = {}
        self._selection_before_right_click = []
        self._rubber_band_start = None
        self._tab_menu = None
        self._current_settings = {}  # Persisted settings dict for new node creation

        # Intercept Tab globally so it works even when inline players have focus
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().installEventFilter(self)

        # Autosave timer — fires every 30 s, saves only when enabled + file named + dirty
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(30_000)
        self._autosave_timer.timeout.connect(self._autosave_tick)
        self._autosave_timer.start()

        # Canvas annotation painter
        self._canvas_painter = CanvasPainter(self)

        self.update_title()

    def _autosave_tick(self):
        """Called every 30 s. Saves silently if autosave is on, file is named, and scene is dirty."""
        if not self._current_settings.get("autosave", True):
            return
        if self._filepath and self._scene._dirty:
            self._write_file(self._filepath)

    def apply_settings(self, settings_dict):
        """Applies configuration settings across the entire application workspace."""
        if not settings_dict or not self._scene:
            return

        # Store for use when new nodes/curves are created
        self._current_settings = settings_dict.copy()
        self._scene._current_settings = settings_dict.copy()

        # 0. Update menu stylesheet colors globally
        from utils import update_menu_colors
        update_menu_colors(
            settings_dict.get('menu_bg', '#2a2a2a'),
            settings_dict.get('menu_fg', '#ffffff'),
        )

        # 1. Canvas background — must be set on the VIEW (not the scene);
        #    QGraphicsView.setBackgroundBrush overrides the scene brush.
        canvas_color = QColor(settings_dict.get('canvas_bg', '#1b1b1b'))
        self.setBackgroundBrush(canvas_color)
        # Keep scene brush in sync so scene.backgroundBrush() is consistent.
        self._scene.setBackgroundBrush(canvas_color)

        # 2. Menu / window palette — must target QApplication so the palette
        #    propagates to all widgets (menus, dialogs, title bar chrome).
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            pal = app.palette()
            pal.setColor(QPalette.ColorRole.Window,
                         QColor(settings_dict.get('menu_bg', '#2a2a2a')))
            pal.setColor(QPalette.ColorRole.WindowText,
                         QColor(settings_dict.get('menu_fg', '#ffffff')))
            pal.setColor(QPalette.ColorRole.Base,
                         QColor(settings_dict.get('menu_bg', '#2a2a2a')))
            pal.setColor(QPalette.ColorRole.Text,
                         QColor(settings_dict.get('menu_fg', '#ffffff')))
            app.setPalette(pal)

        # 3. Push updates down to every item currently on the canvas
        for item in self._scene.items():
            if hasattr(item, 'update_from_settings'):
                item.update_from_settings(settings_dict, force=True)

        # Force redraw
        self.viewport().update()

        # 4. Push annotation defaults into CanvasPainter
        self._canvas_painter.color     = QColor(settings_dict.get("annotation_color", "#FF8C00"))
        self._canvas_painter.thickness = int(settings_dict.get("annotation_thickness", 6))
        self._canvas_painter.style     = settings_dict.get("annotation_style", "solid")

    # ── Title ─────────────────────────────────────────────

    def update_title(self):
        name = self._filepath.split("/")[-1] if self._filepath else "Untitled"
        dirty = " *" if self._scene._dirty else ""
        self.setWindowTitle(f"{APP_NAME} — {name}{dirty}")

    # ── Logo Fade ─────────────────────────────────────────

    def _check_logo_fade(self):
        """Delegate to LogoOverlay — see logo.py to adjust timings."""
        self._logo.check_fade(self._is_canvas_empty())

    def _is_canvas_empty(self):
        from paint_on_canvas import CanvasStroke
        for item in self._scene.items():
            if isinstance(item, (Node, ImageNode, MovieNode, AudioNode,
                                 DocumentNode, PaintNode, Dot, Backdrop,
                                 StickyNote, CanvasStroke)):
                return False
        return True

    # ── Scroll & Zoom ─────────────────────────────────────

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self.viewport().update()
        self._reposition_inline_players()

    def _reposition_inline_players(self):
        for item in self._scene.items():
            if isinstance(item, MovieNode) and item._inline_player:
                item._inline_player.reposition()
            elif isinstance(item, AudioNode) and item._inline_player:
                item._inline_player.reposition()
            elif isinstance(item, DocumentNode) and item._inline_player:
                item._inline_player.reposition()
            elif isinstance(item, PaintNode) and item._inline_viewer:
                item._inline_viewer.reposition()
            elif isinstance(item, ImageNode) and item._inline_viewer:
                item._inline_viewer.reposition()
            elif isinstance(item, Node) and item._inline_text_viewer:
                item._inline_text_viewer.reposition()

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        # Reset to viewport (screen) coordinates so the logo stays centred
        painter.save()
        painter.resetTransform()
        self._logo.paint(painter, self.viewport())
        painter.restore()

    def wheelEvent(self, e):
        factor = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)
        self._update_handle_sizes()
        self._reposition_inline_players()

    def _update_handle_sizes(self):
        """Keep resize handles at a constant screen size regardless of zoom."""
        from utils import HANDLE_SIZE
        zoom = self.transform().m11()
        scene_h = HANDLE_SIZE / zoom
        for item in self._scene.items():
            if isinstance(item, (Backdrop, StickyNote)):
                item._handle_size = scene_h
                item._reposition_handles()
                for h in item._handles.values():
                    h.setRect(0, 0, scene_h, scene_h)

    # ── Mouse Events ──────────────────────────────────────

    def _toggle_canvas_paint(self):
        self._canvas_painter.toggle()

    def mousePressEvent(self, e):
        if self._canvas_painter.mouse_press(e):
            return

        # Close tab menu if open
        if getattr(self, '_tab_menu', None) and self._tab_menu.isVisible():
            self._tab_menu.reject()
            self._tab_menu = None

        if e.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = e.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            e.accept()
            return

        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_start_positions = {
                item: item.pos()
                for item in self._scene.items()
                if isinstance(item, (Node, Dot, Backdrop, StickyNote))
            }
            self._rubber_band_start = e.pos()

        if e.button() == Qt.MouseButton.RightButton:
            if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
                super().mousePressEvent(e)
                return
            self._selection_before_right_click = list(self._scene.selectedItems())
            e.accept()
            return

        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._canvas_painter.mouse_move(e):
            return

        if self._panning:
            delta = e.pos() - self._pan_start
            self._pan_start = e.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y())
            e.accept()
            return

        super().mouseMoveEvent(e)

        if e.buttons() & Qt.MouseButton.LeftButton and hasattr(self, '_rubber_band_start'):
            start_scene = self.mapToScene(self._rubber_band_start)
            end_scene = self.mapToScene(e.pos())
            rect = QRectF(start_scene, end_scene).normalized()
            for item in self._scene.items(rect):
                if isinstance(item, ConnectionLine):
                    item.setSelected(True)

    def mouseReleaseEvent(self, e):
        if self._canvas_painter.mouse_release(e):
            return

        if e.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            e.accept()
            return

        if e.button() == Qt.MouseButton.LeftButton:
            # Push undo for moved items
            selected_set = set(self._scene.selectedItems())
            for item, old_pos in self._drag_start_positions.items():
                if item not in selected_set:
                    continue
                new_pos = item.pos()
                if (new_pos - old_pos).manhattanLength() > 1:
                    self._scene._push_undo({
                        "type": "move",
                        "item": item,
                        "old_pos": old_pos,
                        "new_pos": new_pos,
                    })
            
            # Re-evaluate backdrop containment on every release
            self._scene.reeval_backdrop_containment()

            self._drag_start_positions = {}
            if hasattr(self, '_rubber_band_start'):
                delattr(self, '_rubber_band_start')

        if e.button() == Qt.MouseButton.RightButton:
            if self._selection_before_right_click:
                for item in self._selection_before_right_click:
                    item.setSelected(True)
                self._selection_before_right_click = []

        super().mouseReleaseEvent(e)

    # ── Context Menu ──────────────────────────────────────

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        from curve import Socket
        from note import ResizeHandle
        while item and isinstance(item, (Socket, ResizeHandle)):
            item = item.parentItem()

        if isinstance(item, (Node, Backdrop, StickyNote, ConnectionLine, Dot)):
            item.contextMenuEvent(self._scene_ctx_for(event, item))
            event.accept()
        else:
            self._canvas_menu(event.pos())
            event.accept()

    def _scene_ctx_for(self, view_event, item):
        from PyQt6.QtCore import QPointF, QPoint
        # globalPosition() is the PyQt6 way; toPoint() gives QPoint for menu.exec()
        gp = view_event.globalPosition().toPoint()
        sp = self.mapToScene(view_event.pos())
        class _Ctx:
            _sp  = sp
            _scp = QPointF(gp.x(), gp.y())
            _gp  = gp
            def scenePos(self):  return self._sp
            def screenPos(self): return self._scp
            def globalPos(self): return self._gp
            def accept(self): pass
            def ignore(self): pass
        return _Ctx()

    def _canvas_menu(self, pos):
        """Main right-click menu on empty canvas"""
        scene = self._scene
        center_pos = self._get_center_scene_pos()
        m = build_menu(self, scene, center_pos)
        menu = m["menu"]
        actions = m["actions"]

        actions["new"].triggered.connect(self.file_new)
        actions["open"].triggered.connect(self.file_open)
        actions["save"].triggered.connect(self.file_save)
        actions["save_as"].triggered.connect(self.file_save_as)
        actions["export_selected"].triggered.connect(self.file_export_selected)
        actions["import_nodes"].triggered.connect(self.file_import_nodes)

        actions["create"].triggered.connect(lambda: self.create_node_at(self.mapToScene(pos)))
        actions["create_image"].triggered.connect(lambda: self.create_image_node_at(self.mapToScene(pos)))
        actions["create_movie"].triggered.connect(lambda: self.create_movie_node_at(self.mapToScene(pos)))
        actions["create_audio"].triggered.connect(lambda: self.create_audio_node_at(self.mapToScene(pos)))
        actions["create_doc"].triggered.connect(lambda: self.create_doc_node_at(self.mapToScene(pos)))
        actions["create_paint"].triggered.connect(lambda: self.create_paint_node_at(self.mapToScene(pos)))
        actions["create_dot"].triggered.connect(lambda: self.create_dot_at(self.mapToScene(pos)))
        actions["create_backdrop"].triggered.connect(lambda: self.create_backdrop_at(self.mapToScene(pos)))
        actions["create_sticky"].triggered.connect(lambda: self.create_sticky_at(self.mapToScene(pos)))

        actions["copy"].triggered.connect(scene.copy)
        actions["cut"].triggered.connect(scene.cut)
        actions["paste"].triggered.connect(lambda: scene.paste(self.mapToScene(pos)))

        actions["arrange_v"].triggered.connect(self.arrange_vertical)
        actions["arrange_h"].triggered.connect(self.arrange_horizontal)
        actions["frame_selected"].triggered.connect(
            lambda: self.frame_items(list(scene.selectedItems())))
        actions["frame_all"].triggered.connect(
            lambda: self.frame_items(list(scene.items())))
        actions["center_selected"].triggered.connect(
            lambda: self.center_items(list(scene.selectedItems())))

        actions["undo"].triggered.connect(scene.undo)
        actions["redo"].triggered.connect(scene.redo)
        actions["expand_nodes"].triggered.connect(self.expand_all_nodes)
        actions["contract_nodes"].triggered.connect(self.contract_all_nodes)
        actions["about"].triggered.connect(self._show_about)
        actions["quit"].triggered.connect(self.close)
        actions["shortcuts"].triggered.connect(self._show_shortcuts)
        actions["documentation"].triggered.connect(self._open_documentation)

        # Settings Action
        actions["settings"].triggered.connect(lambda: self._open_settings())
        actions["draw_annotation"].triggered.connect(self._toggle_canvas_paint)

        menu.exec(self.mapToGlobal(pos))

    # ── Creation Methods ──────────────────────────────────

    def _get_center_scene_pos(self):
        return self.mapToScene(self.viewport().rect().center())

    def create_node_at(self, pos):
        x, y = self._scene._non_overlapping(pos.x() - 120, pos.y() - 45, 240, 90)
        node = Node(x, y, self)
        self._scene.addItem(node)
        if self._current_settings:
            node.update_from_settings(self._current_settings); node._settings_locked = True
        self._scene._push_undo({"type": "add_node", "node": node})
        self._check_logo_fade()
        self.viewport().update()
        return node

    def create_image_node_at(self, pos):
        x, y = self._scene._non_overlapping(pos.x() - 120, pos.y() - 45, 240, 90)
        node = ImageNode(x, y, self)
        self._scene.addItem(node)
        if self._current_settings:
            node.update_from_settings(self._current_settings); node._settings_locked = True
        self._scene._push_undo({"type": "add_node", "node": node})
        self._check_logo_fade()
        self.viewport().update()
        return node

    def create_movie_node_at(self, pos):
        x, y = self._scene._non_overlapping(pos.x() - 120, pos.y() - 45, 240, 90)
        node = MovieNode(x, y, self)
        self._scene.addItem(node)
        if self._current_settings:
            node.update_from_settings(self._current_settings); node._settings_locked = True
        self._scene._push_undo({"type": "add_node", "node": node})
        self._check_logo_fade()
        self.viewport().update()
        return node

    def create_audio_node_at(self, pos):
        x, y = self._scene._non_overlapping(pos.x() - 120, pos.y() - 45, 240, 90)
        node = AudioNode(x, y, self)
        self._scene.addItem(node)
        if self._current_settings:
            node.update_from_settings(self._current_settings); node._settings_locked = True
        self._scene._push_undo({"type": "add_node", "node": node})
        self._check_logo_fade()
        self.viewport().update()
        return node

    def create_doc_node_at(self, pos):
        x, y = self._scene._non_overlapping(pos.x() - 120, pos.y() - 45, 240, 90)
        node = DocumentNode(x, y, self)
        self._scene.addItem(node)
        if self._current_settings:
            node.update_from_settings(self._current_settings); node._settings_locked = True
        self._scene._push_undo({"type": "add_node", "node": node})
        self._check_logo_fade()
        self.viewport().update()
        return node

    def create_paint_node_at(self, pos):
        x, y = self._scene._non_overlapping(pos.x() - 120, pos.y() - 45, 240, 90)
        node = PaintNode(x, y, self)
        self._scene.addItem(node)
        if self._current_settings:
            node.update_from_settings(self._current_settings); node._settings_locked = True
        self._scene._push_undo({"type": "add_node", "node": node})
        self._check_logo_fade()
        self.viewport().update()
        return node

    def create_dot_at(self, pos):
        x, y = self._scene._non_overlapping(pos.x() - 24, pos.y() - 24, 48, 48)
        dot = Dot(x, y, self)
        self._scene.addItem(dot)
        if self._current_settings:
            dot.update_from_settings(self._current_settings); dot._settings_locked = True
        self._scene._push_undo({"type": "add_node", "node": dot})
        self._check_logo_fade()
        self.viewport().update()
        return dot

    def create_backdrop_at(self, pos):
        selected = [
            item for item in self._scene.selectedItems()
            if not isinstance(item, ConnectionLine)
        ]

        if selected:
            rect = QRectF()
            for item in selected:
                rect = rect.united(item.sceneBoundingRect())

            pad         = 20
            font_size   = self._current_settings.get("backdrop_font_size", 80)
            title_h     = int(font_size) * 2 + pad   # margin + header_rect height

            # Expand: standard pad on all sides, extra top for the title area
            rect.adjust(-pad, -(pad + title_h), pad, pad)
            x, y = rect.x(), rect.y()
            w = max(rect.width(), 600)
            h = max(rect.height(), 400)
            bd = Backdrop(x, y, self)
            bd.width = w
            bd.height = h
            bd._reposition_handles()
            self._scene.addItem(bd)
            if self._current_settings:
                bd.update_from_settings(self._current_settings)
            self._scene._push_undo({"type": "add_node", "node": bd})
            bd._last_pos = bd.pos()
            self._scene.reeval_backdrop_containment()
            self._scene.clearSelection()
            bd.setSelected(True)
        else:
            bd = Backdrop(pos.x(), pos.y(), self)
            self._scene.addItem(bd)
            if self._current_settings:
                bd.update_from_settings(self._current_settings)
            self._scene._push_undo({"type": "add_node", "node": bd})
        
        self._update_handle_sizes()
        self._check_logo_fade()
        self.viewport().update()
        return bd

    def create_sticky_at(self, pos):
        x, y = self._scene._non_overlapping(pos.x() - 120, pos.y() - 90, 240, 180)
        s = StickyNote(x, y, self)
        self._scene.addItem(s)
        if self._current_settings:
            s.update_from_settings(self._current_settings)
        self._scene._push_undo({"type": "add_node", "node": s})
        self._update_handle_sizes()
        self._check_logo_fade()
        self.viewport().update()
        return s

    # ── File Operations ───────────────────────────────────

    def _ask_save_if_dirty(self):
        if not self._scene._dirty:
            return True
        reply = QMessageBox.question(
            self, "Unsaved Changes",
            "The scene has unsaved changes. Save now?",
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Save:
            return self.file_save()
        elif reply == QMessageBox.StandardButton.Discard:
            return True
        return False

    def _close_all_inline_viewers(self):
        """Close every open inline viewer/player in the scene before clearing or quitting."""
        for item in self._scene.items():
            self._close_inline_for(item)

    def file_new(self):
        if not self._ask_save_if_dirty(): return
        self._close_all_inline_viewers()
        self._scene.clear()
        self._scene._undo_stack.clear()
        self._scene._redo_stack.clear()
        self._scene._dirty = False
        self._filepath = None
        self.update_title()
        self._check_logo_fade()
        self.viewport().update()

    def load_file(self, path):
        """Open a .flow file by path — called from sys.argv (file manager double-click)."""
        if not self._ask_save_if_dirty(): return
        if hasattr(self, "_logo"):
            self._logo._opacity = 1.0
            self._logo._start_fade(fade_in=False)
        try:
            with open(path) as f:
                import json
                data = json.load(f)
            self._close_all_inline_viewers()
            self._scene.from_dict(data, self)
            self._update_handle_sizes()
            self._filepath = path
            self._scene._dirty = False
            self.update_title()
            self.frame_items(list(self._scene.items()))
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, self._check_logo_fade)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open:\n{e}")

    def file_open(self):
        if not self._ask_save_if_dirty(): return
        from config import FILE_FILTER
        path, _ = QFileDialog.getOpenFileName(self, "Open File", "", FILE_FILTER)
        if not path: return
        try:
            with open(path) as f:
                import json
                data = json.load(f)
            self._close_all_inline_viewers()
            self._scene.from_dict(data, self)
            self._update_handle_sizes()
            self._filepath = path
            self._scene._dirty = False
            self.update_title()
            self._check_logo_fade()
            self.frame_items(list(self._scene.items()))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open:\n{e}")

    def load_file(self, path):
        """Load a .flow file directly — used when launched with a file argument
        (e.g. double-click from Windows Explorer or CLI: theFlow.exe myfile.flow)."""
        try:
            import json
            with open(path) as f:
                data = json.load(f)
            self._close_all_inline_viewers()
            self._scene.from_dict(data, self)
            self._update_handle_sizes()
            self._filepath = path
            self._scene._dirty = False
            self.update_title()
            self._check_logo_fade()
            self.frame_items(list(self._scene.items()))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open:\n{e}")

    def file_save(self):
        if not self._filepath:
            return self.file_save_as()
        self._write_file(self._filepath)
        return True

    def file_save_as(self):
        from config import FILE_FILTER
        path, _ = QFileDialog.getSaveFileName(self, "Save As", "", FILE_FILTER)
        if not path: return False
        if not path.endswith(".flow"): path += ".flow"
        self._filepath = path
        self._write_file(path)
        return True

    def file_export_selected(self):
        """Export only the selected nodes/backdrops/stickies to a .flow file."""
        import json
        from config import FILE_FILTER
        from node import Node, ImageNode, MovieNode, AudioNode, DocumentNode
        from paint import PaintNode
        from backdrop import Backdrop
        from note import StickyNote
        from curve import Dot, ConnectionLine
        from PyQt6.QtGui import QColor

        selected = [i for i in self._scene.selectedItems()
                    if not isinstance(i, ConnectionLine)]
        if not selected:
            QMessageBox.information(self, "Export Selected",
                                    "No items selected — nothing to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Selected", "", FILE_FILTER)
        if not path:
            return
        if not path.endswith(".flow"):
            path += ".flow"

        # Build a minimal to_dict payload for only the selected items.
        # Re-use the scene's full serialisation but filter to selected ids.
        full = self._scene.to_dict()
        selected_ids = {id(i) for i in selected}

        # Match by the "id" key stored in each node snapshot.
        nodes = [n for n in full.get("nodes", []) if n.get("id") in selected_ids]

        # Connections use socket strings like "4715949216_out" / "4715948064_in".
        # Build the set of node-id prefixes that belong to selected nodes, then
        # keep connections where BOTH endpoints belong to selected nodes.
        node_id_prefixes = {str(n["id"]) for n in nodes}

        def _socket_belongs(sock_str):
            # sock_str is "<node_id>_in" or "<node_id>_out"
            parts = sock_str.rsplit("_", 1)
            return len(parts) == 2 and parts[0] in node_id_prefixes

        conns = [c for c in full.get("connections", [])
                 if _socket_belongs(c.get("a", ""))
                 and _socket_belongs(c.get("b", ""))]

        # Include strokes that overlap the bounding rect of the selection.
        from paint_on_canvas import CanvasStroke
        from PyQt6.QtCore import QRectF
        if selected:
            sel_rect = QRectF()
            for i in selected:
                sel_rect = sel_rect.united(i.sceneBoundingRect())
            strokes = [s for s in full.get("strokes", [])
                       if any(sel_rect.contains(p[0], p[1])
                              for p in s.get("points", []))]
        else:
            strokes = []

        data = {"nodes": nodes, "connections": conns, "strokes": strokes}
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not export:\n{e}")

    def file_import_nodes(self):
        """Import nodes from a .flow file and add them to the current canvas."""
        import json
        from config import FILE_FILTER

        path, _ = QFileDialog.getOpenFileName(
            self, "Import Nodes", "", FILE_FILTER)
        if not path:
            return
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not read file:\n{e}")
            return

        # Offset imported nodes by a fixed amount so they don't land on top
        # of existing items and are immediately visible.
        OFFSET = 80
        for node_snap in data.get("nodes", []):
            node_snap["x"] = node_snap.get("x", 0) + OFFSET
            node_snap["y"] = node_snap.get("y", 0) + OFFSET

        try:
            # Merge into current scene rather than replacing it.
            self._scene.merge_from_dict(data, self)
            self._update_handle_sizes()
            self._scene.mark_dirty()
            self.viewport().update()
            # Defer logo fade so Qt has processed the newly added items first.
            QTimer.singleShot(0, self._check_logo_fade)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not import nodes:\n{e}")

    def _write_file(self, path):
        try:
            import json
            with open(path, "w") as f:
                json.dump(self._scene.to_dict(), f, indent=2)
            self._scene._dirty = False
            self.update_title()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save:\n{e}")

    # ── View Helpers ──────────────────────────────────────

    @staticmethod
    def _filter_non_curves(items):
        return [i for i in items if not isinstance(i, ConnectionLine)]

    def frame_items(self, items):
        items = self._filter_non_curves(items)
        if not items: return
        rect = QRectF()
        for item in items:
            rect = rect.united(item.sceneBoundingRect())
        rect.adjust(-80, -80, 80, 80)
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
        self._update_handle_sizes()
        self._reposition_inline_players()

    def center_items(self, items):
        items = self._filter_non_curves(items)
        if not items: return
        rect = QRectF()
        for item in items:
            rect = rect.united(item.sceneBoundingRect())
        self.centerOn(rect.center())

    def arrange_horizontal(self):
        nodes = self._scene.selected_nodes()
        if len(nodes) < 2: return
        GAP = 40
        nodes.sort(key=lambda n: n.scenePos().x())
        y   = nodes[0].scenePos().y()
        x   = nodes[0].scenePos().x()
        for n in nodes:
            n.setPos(x, y)
            # Use the node's shape path bounding rect mapped to scene coords
            # so spacing respects the actual visual edge of every shape.
            shape_br = n.mapToScene(n.shape().boundingRect()).boundingRect()
            x += shape_br.width() + GAP

    def arrange_vertical(self):
        nodes = self._scene.selected_nodes()
        if len(nodes) < 2: return
        GAP = 40
        nodes.sort(key=lambda n: n.scenePos().y())
        x   = nodes[0].scenePos().x()
        y   = nodes[0].scenePos().y()
        for n in nodes:
            n.setPos(x, y)
            shape_br = n.mapToScene(n.shape().boundingRect()).boundingRect()
            y += shape_br.height() + GAP

    def expand_all_nodes(self):
        """Expand inline viewers/players for all nodes in the scene."""
        for item in self._scene.items():
            self._open_inline_for(item)
        self._scene.mark_dirty()

    def contract_all_nodes(self):
        """Close all inline viewers/players in the scene."""
        for item in self._scene.items():
            self._close_inline_for(item)
        self._scene.mark_dirty()

    def _open_inline_for(self, item):
        from node import MovieNode, ImageNode, AudioNode, DocumentNode, Node
        from paint import PaintNode
        if isinstance(item, MovieNode):
            item.open_inline_player()
        elif isinstance(item, AudioNode):
            item.open_inline_player()
        elif isinstance(item, DocumentNode):
            item.open_inline_player()
        elif isinstance(item, PaintNode):
            item.open_inline_viewer()
        elif isinstance(item, ImageNode):
            item.open_inline_viewer()
        elif isinstance(item, Node):
            if getattr(item.title, '_html', '') or getattr(item.title, '_plain', ''):
                item.open_inline_text_viewer()

    def _close_inline_for(self, item):
        from node import MovieNode, ImageNode, AudioNode, DocumentNode, Node
        from paint import PaintNode
        if isinstance(item, MovieNode):
            item.close_inline_player()
        elif isinstance(item, AudioNode):
            item.close_inline_player()
        elif isinstance(item, DocumentNode):
            item.close_inline_player()
        elif isinstance(item, PaintNode):
            item.close_inline_viewer()
        elif isinstance(item, ImageNode):
            item.close_inline_viewer()
        elif isinstance(item, Node):
            item.close_inline_text_viewer()

    # ── Keyboard & Special Actions ────────────────────────

    def _space_toggle_player(self):
        """Play/pause the inline player whose container is under the cursor.
        Returns True if a player was found and toggled."""
        from node import MovieNode, AudioNode
        cursor_global = self.cursor().pos()
        for item in self._scene.items():
            player = None
            if isinstance(item, MovieNode) and getattr(item, '_inline_player', None):
                player = item._inline_player
            elif isinstance(item, AudioNode) and getattr(item, '_inline_player', None):
                player = item._inline_player
            if player is None:
                continue
            container = getattr(player, '_container', None)
            if container is None or not container.isVisible():
                continue
            if container.rect().contains(container.mapFromGlobal(cursor_global)):
                try:
                    from PyQt6.QtMultimedia import QMediaPlayer
                    state = player._player.playbackState()
                    if state == QMediaPlayer.PlaybackState.PlayingState:
                        player._pause_btn.click()
                    else:
                        player._play_btn.click()
                except Exception:
                    pass
                return True
        return False

    def _toggle_inline_player(self, open):
        from node import MovieNode, ImageNode, AudioNode, DocumentNode, Node
        for item in self._scene.selectedItems():
            if isinstance(item, MovieNode):
                item.open_inline_player() if open else item.close_inline_player()
            elif isinstance(item, AudioNode):
                item.open_inline_player() if open else item.close_inline_player()
            elif isinstance(item, DocumentNode):
                item.open_inline_player() if open else item.close_inline_player()
            elif isinstance(item, PaintNode):
                item.open_inline_viewer() if open else item.close_inline_viewer()
            elif isinstance(item, ImageNode):
                item.open_inline_viewer() if open else item.close_inline_viewer()
            elif isinstance(item, Node):
                if open:
                    if getattr(item.title, '_html', '') or getattr(item.title, '_plain', ''):
                        item.open_inline_text_viewer()
                else:
                    item.close_inline_text_viewer()

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Tab:
                # Only intercept if the focused widget is a child of our viewport
                from PyQt6.QtWidgets import QApplication
                fw = QApplication.focusWidget()
                if fw and (fw is self or self.isAncestorOf(fw) or
                           self.viewport().isAncestorOf(fw) or fw is self.viewport()):
                    self._open_tab_menu()
                    return True
        return super().eventFilter(obj, event)

    def _open_tab_menu(self):
        cursor_global = self.cursor().pos()
        scene_pos = self.mapToScene(self.mapFromGlobal(cursor_global))
        TabCreationMenu(self, scene_pos, cursor_global)

    def _open_documentation(self):
        import os, sys, webbrowser
        from PyQt6.QtWidgets import QMessageBox

        candidates = []

        # Dev / source mode
        candidates.append(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "documentation", "theFlow_manual.html"))

        # PyInstaller frozen — next to the .exe
        if getattr(sys, 'frozen', False):
            candidates.append(os.path.join(
                os.path.dirname(sys.executable),
                "documentation", "theFlow_manual.html"))

        doc_path = next((p for p in candidates if os.path.isfile(p)), None)

        if doc_path:
            webbrowser.open(f"file:///{doc_path}")
        else:
            QMessageBox.warning(self, "Documentation Not Found",
                "Manual not found. Looked in:\n" +
                "\n".join(candidates))

    def _show_shortcuts(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget
        from utils import _MENU_COLORS

        bg       = _MENU_COLORS["bg"]
        fg       = _MENU_COLORS["fg"]
        border   = _MENU_COLORS["border"]
        disabled = _MENU_COLORS["disabled"]

        def _darken(hex_color, amount=0.10):
            h = hex_color.lstrip("#")
            r, g, b = [int(h[i:i+2], 16)/255.0 for i in (0, 2, 4)]
            return "#{:02x}{:02x}{:02x}".format(
                int(max(0, r - amount) * 255),
                int(max(0, g - amount) * 255),
                int(max(0, b - amount) * 255),
            )

        key_bg = _darken(bg)

        dlg = QDialog(self)
        dlg.setWindowTitle("Keyboard Shortcuts")
        dlg.setMinimumWidth(340)
        dlg.setStyleSheet(f"background:{bg}; color:{fg};")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;")
        inner = QWidget()
        inner.setStyleSheet(f"background:{bg};")
        vbox = QVBoxLayout(inner)
        vbox.setSpacing(4)

        shortcuts = [
            ("Create", None),
            ("T", "Text node"), ("I", "Image node"), ("M", "Movie node"),
            ("A", "Audio node"), ("D", "Document node"), ("P", "Paint node"),
            ("Q", "Dot"), ("B", "Backdrop"), ("S", "Sticky note"),
            ("Tab", "Quick create menu"), ("", None),
            ("Edit", None),
            ("Ctrl+Z", "Undo"), ("Ctrl+Y", "Redo"), ("Ctrl+C", "Copy"),
            ("Ctrl+X", "Cut"), ("Ctrl+V", "Paste"),
            ("Del / Bksp", "Delete selected"), ("", None),
            ("Connections", None),
            ("Shift+Click curve", "Create dot / split"),
            ("Shift+Click dot", "Disconnect / merge"),
            ("Shift+Click node", "Disconnect all curves"), ("", None),
            ("View", None),
            ("F", "Frame selected"),
            ("Z", "Frame all"),
            ("C", "Center selected"),
            ("H", "Rearrange horizontally"),
            ("V", "Rearrange vertically"),
            ("↓", "Expand selected inline viewers"),
            ("↑", "Close selected inline viewers"),
            ("Shift+↓", "Expand all inline viewers"),
            ("Shift+↑", "Close all inline viewers"),
            ("Space", "Play/pause inline player"),
            ("Middle drag", "Pan"), ("Scroll", "Zoom"), ("", None),
            ("File", None),
            ("Ctrl+N", "New file"), ("Ctrl+O", "Open"), ("Ctrl+S", "Save"),
            ("Ctrl+Shift+S", "Save As"), ("Ctrl+E", "Export Selected"),
            ("Ctrl+I", "Import Nodes"), ("Ctrl+Q", "Quit"), ("", None),
            ("Draw Annotation", None),
            ("Ctrl+P", "Toggle annotation mode"),
            ("Other", None),
            ("K", "Show shortcuts"),
        ]

        for key, desc in shortcuts:
            if desc is None:
                if key:
                    lbl = QLabel(key)
                    lbl.setStyleSheet(
                        f"color:#4a9eff; font-weight:bold; font-size:13px;"
                        f" margin-top:10px; padding-bottom:2px;"
                        f" border-bottom:1px solid {border};")
                    vbox.addWidget(lbl)
                else:
                    spacer = QLabel("")
                    spacer.setFixedHeight(4)
                    vbox.addWidget(spacer)
            else:
                row = QWidget()
                row.setStyleSheet("background:transparent;")
                rl = QHBoxLayout(row)
                rl.setContentsMargins(0, 0, 0, 0)
                key_lbl = QLabel(key)
                key_lbl.setStyleSheet(
                    f"background:{key_bg}; color:{fg}; font-family:monospace;"
                    f" font-size:12px; padding:2px 8px; border-radius:4px;"
                    f" border:1px solid {border};")
                key_lbl.setFixedWidth(170)
                desc_lbl = QLabel(desc)
                desc_lbl.setStyleSheet(f"color:{disabled}; font-size:12px; padding-left:8px;")
                rl.addWidget(key_lbl)
                rl.addWidget(desc_lbl)
                rl.addStretch()
                vbox.addWidget(row)

        vbox.addStretch()
        scroll.setWidget(inner)

        layout = QVBoxLayout(dlg)
        layout.addWidget(scroll)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        close_btn.setStyleSheet("background:#4a9eff; color:#ffffff; padding:6px 20px; border-radius:4px; font-size:13px;")
        layout.addWidget(close_btn)
        dlg.exec()

    def _open_settings(self):
        """Open the settings dialog."""
        dialog = SettingsDialog(self, self._scene)
        dialog.exec()

    def _show_about(self):
        import os
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
        from PyQt6.QtCore import Qt

        script_dir = os.path.dirname(os.path.abspath(__file__))

        is_light = self._current_settings.get("theme", "dark") == "light"
        bg   = "#f0f0f0" if is_light else "#1b1b1b"
        fg   = "#1a1a1a" if is_light else "#ffffff"
        fg2  = "#555555" if is_light else "#aaaaaa"
        btn_bg = "#dddddd" if is_light else "#3a3a3a"

        dlg = QDialog(self)
        dlg.setWindowTitle("About theFlow!")
        dlg.setFixedSize(380, 460)
        dlg.setStyleSheet(f"background:{bg}; color:{fg};")

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        def _svg_row(rel_path, w=160, h=80):
            from PyQt6.QtSvg import QSvgRenderer
            from PyQt6.QtGui import QPixmap, QPainter as _P
            from PyQt6.QtCore import QRectF as _R
            path = os.path.join(script_dir, rel_path)
            renderer = QSvgRenderer(path)
            pixmap = QPixmap(w, h)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = _P(pixmap)
            renderer.render(painter, _R(0, 0, w, h))
            painter.end()
            lbl = QLabel(dlg)
            lbl.setPixmap(pixmap)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row = QHBoxLayout()
            row.addStretch()
            row.addWidget(lbl)
            row.addStretch()
            layout.addLayout(row)

        def _lbl(text, bold=False, size=12, color=None, align=Qt.AlignmentFlag.AlignCenter):
            if color is None:
                color = fg
            l = QLabel(text)
            l.setAlignment(align)
            l.setOpenExternalLinks(True)
            style = f"color:{color}; font-size:{size}px;"
            if bold: style += " font-weight:bold;"
            l.setStyleSheet(style)
            return l

        layout.addSpacing(8)
        _svg_row(os.path.join("logo", "theFlow!.svg"), w=340, h=170)
        layout.addSpacing(2)
        layout.addWidget(_lbl("Version 1.0.0", size=12, color=fg2))
        layout.addSpacing(4)
        layout.addWidget(_lbl("Copyright © 2026", size=12))
        layout.addSpacing(4)
        layout.addWidget(_lbl("Author  Xavier Garès", size=12))
        layout.addSpacing(4)
        layout.addWidget(_lbl('License  <a href="https://www.gnu.org/licenses/gpl-3.0.html" style="color:#4a9eff;">GPLv3</a>', size=12))
        layout.addSpacing(4)
        layout.addWidget(_lbl('Contact  <a href="mailto:theflowapp@protonmail.com" style="color:#4a9eff;">theflowapp@protonmail.com</a>', size=12))
        layout.addSpacing(16)
        _svg_row(os.path.join("logo", "Fet_a_Horta.svg"), w=105, h=52)
        layout.addSpacing(16)
        ok = QPushButton("OK")
        ok.setFixedWidth(80)
        ok.setStyleSheet(f"QPushButton{{background:{btn_bg};color:{fg};border:none;border-radius:5px;padding:6px;}}QPushButton:hover{{background:#4a9eff;color:#ffffff;}}")
        ok.clicked.connect(dlg.accept)
        row_ok = QHBoxLayout()
        row_ok.addStretch()
        row_ok.addWidget(ok)
        row_ok.addStretch()
        layout.addLayout(row_ok)
        dlg.exec()

    def keyPressEvent(self, e):
        ctrl = bool(e.modifiers() & Qt.KeyboardModifier.ControlModifier)
        k = e.key()

        # Let canvas painter consume keys when active (D/E/C/S toolbar shortcuts)
        if self._canvas_painter.key_press(e):
            return

        if ctrl and e.modifiers() & Qt.KeyboardModifier.ShiftModifier and k == Qt.Key.Key_S:
            self.file_save_as(); return

        if ctrl:
            if k == Qt.Key.Key_P: self._toggle_canvas_paint(); return
            if k == Qt.Key.Key_Z: self._scene.undo(); return
            if k == Qt.Key.Key_Y: self._scene.redo(); return
            if k == Qt.Key.Key_C: self._scene.copy(); return
            if k == Qt.Key.Key_X: self._scene.cut(); return
            if k == Qt.Key.Key_V:
                cursor_pos = self.mapToScene(self.mapFromGlobal(self.cursor().pos()))
                self._scene.paste(cursor_pos); return
            if k == Qt.Key.Key_S: self.file_save(); return
            if k == Qt.Key.Key_O: self.file_open(); return
            if k == Qt.Key.Key_N: self.file_new(); return
            if k == Qt.Key.Key_E: self.file_export_selected(); return
            if k == Qt.Key.Key_I: self.file_import_nodes(); return
            if k == Qt.Key.Key_Q: self.close(); return

        if k in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self._scene.delete_selected(); return

        if k == Qt.Key.Key_T: self.create_node_at(self.mapToScene(self.mapFromGlobal(self.cursor().pos()))); return
        if k == Qt.Key.Key_I: self.create_image_node_at(self.mapToScene(self.mapFromGlobal(self.cursor().pos()))); return
        if k == Qt.Key.Key_M: self.create_movie_node_at(self.mapToScene(self.mapFromGlobal(self.cursor().pos()))); return
        if k == Qt.Key.Key_A: self.create_audio_node_at(self.mapToScene(self.mapFromGlobal(self.cursor().pos()))); return
        if k == Qt.Key.Key_D: self.create_doc_node_at(self.mapToScene(self.mapFromGlobal(self.cursor().pos()))); return
        if k == Qt.Key.Key_P: self.create_paint_node_at(self.mapToScene(self.mapFromGlobal(self.cursor().pos()))); return
        if k == Qt.Key.Key_Q: self.create_dot_at(self.mapToScene(self.mapFromGlobal(self.cursor().pos()))); return
        if k == Qt.Key.Key_B: self.create_backdrop_at(self.mapToScene(self.mapFromGlobal(self.cursor().pos()))); return
        if k == Qt.Key.Key_S: self.create_sticky_at(self.mapToScene(self.mapFromGlobal(self.cursor().pos()))); return

        if k == Qt.Key.Key_K: self._show_shortcuts(); return
        if k == Qt.Key.Key_Tab: self._open_tab_menu(); return

        shift = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        if shift and k == Qt.Key.Key_Down: self.expand_all_nodes(); return
        if shift and k == Qt.Key.Key_Up: self.contract_all_nodes(); return

        if k == Qt.Key.Key_Space:
            if self._space_toggle_player():
                return

        if k == Qt.Key.Key_Down: self._toggle_inline_player(open=True); return
        if k == Qt.Key.Key_Up: self._toggle_inline_player(open=False); return

        if k == Qt.Key.Key_F:
            sel = list(self._scene.selectedItems())
            self.frame_items(sel if sel else list(self._scene.items())); return
        if k == Qt.Key.Key_Z: self.frame_items(list(self._scene.items())); return
        if k == Qt.Key.Key_H: self.arrange_horizontal(); return
        if k == Qt.Key.Key_V: self.arrange_vertical(); return
        if k == Qt.Key.Key_C: self.center_items(list(self._scene.selectedItems())); return

        super().keyPressEvent(e)

    def closeEvent(self, e):
        if not self._ask_save_if_dirty():
            e.ignore()
        else:
            self._close_all_inline_viewers()
            e.accept()