# =========================================================
# theFlow! - Visual Canvas Application
# =========================================================
#
# Copyright (c) 2026 [Xavier Gares]
#
# This file is part of theFlow.
#
# theFlow is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option)
# any later version.

# reference.py
# =========================================================
# REFERENCE NODE  –  Live external .flow file embed
# =========================================================
# Key: R
#
# Inherits from Backdrop — items inside are Qt children of
# the ReferenceNode, so they drag along with it automatically.
# reeval_backdrop_containment handles parenting.
#
# View mode  (default):
#   — Items inside are locked (not selectable/movable)
#   — QFileSystemWatcher monitors the .flow file on disk
#   — Auto-reloads when file changes externally
#
# Edit mode:
#   — Items become interactive
#   — .flow.lock file written; watcher paused
#   — "Export Edits" saves changes back to the .flow file
#   — Closing edit mode removes the lock file
#
# Connections: always active regardless of mode
# =========================================================

import os
import json
import copy

from PyQt6.QtWidgets import (
    QGraphicsItem, QWidget, QLabel, QDialog, QVBoxLayout,
    QHBoxLayout, QPushButton, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, QFileSystemWatcher, QTimer,
)
from PyQt6.QtGui import (
    QColor, QPen, QBrush, QPainter, QFont, QPainterPath,
)

from backdrop import Backdrop
from curve import ConnectionLine
from utils import HANDLE_SIZE


# =========================================================
# LOCK FILE HELPERS
# =========================================================

def _lock_path(flow_path):
    return flow_path + ".lock"

def _write_lock(flow_path):
    try:
        with open(_lock_path(flow_path), "w") as f:
            f.write("locked")
    except Exception:
        pass

def _remove_lock(flow_path):
    try:
        lp = _lock_path(flow_path)
        if os.path.exists(lp):
            os.remove(lp)
    except Exception:
        pass

def _is_locked(flow_path):
    return os.path.exists(_lock_path(flow_path))


# =========================================================
# INLINE HEADER BAR
# =========================================================

class ReferenceHeader(QWidget):
    """Viewport-parented bar above the ReferenceNode."""

    def __init__(self, ref_node, view):
        super().__init__(view.viewport())
        self._ref  = ref_node
        self._view = view
        self.setStyleSheet(
            "background:#2a2a2a; border:1px solid #555; border-radius:4px;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(6)

        self._path_lbl = QLabel("")
        self._path_lbl.setStyleSheet(
            "color:#aaaaaa; font-size:10px; font-family:monospace;")
        self._path_lbl.setMaximumWidth(280)
        layout.addWidget(self._path_lbl)

        layout.addStretch()

        _s = ("QPushButton{background:#3a3a3a;color:#fff;"
              "border:1px solid #555;border-radius:3px;"
              "font-size:10px;padding:0 8px;min-height:20px;}"
              "QPushButton:hover{background:#555;}")

        self._edit_btn = QPushButton("Reference")
        self._edit_btn.setStyleSheet(_s)
        self._edit_btn.clicked.connect(self._on_reference)
        layout.addWidget(self._edit_btn)

        self._direct_edit_btn = QPushButton("Edit")
        self._direct_edit_btn.setStyleSheet(_s)
        self._direct_edit_btn.clicked.connect(ref_node.enter_edit_mode)
        layout.addWidget(self._direct_edit_btn)

        self._push_btn = QPushButton("Export Edits")
        self._push_btn.setStyleSheet(_s)
        self._push_btn.clicked.connect(ref_node.push_to_source)
        self._push_btn.setVisible(False)
        layout.addWidget(self._push_btn)

        self._view_btn = QPushButton("Close Edit")
        self._view_btn.setStyleSheet(_s)
        self._view_btn.clicked.connect(ref_node.enter_view_mode)
        self._view_btn.setVisible(False)
        layout.addWidget(self._view_btn)

        self.adjustSize()
        self.show()
        self.raise_()

    def set_path(self, path):
        self._path_lbl.setText(os.path.basename(path) if path else "—")
        self._path_lbl.setToolTip(path or "")

    def set_edit_mode(self, editing):
        self._edit_btn.setVisible(not editing)
        self._direct_edit_btn.setVisible(not editing)
        self._push_btn.setVisible(editing)
        self._view_btn.setVisible(editing)

    def _on_reference(self):
        ref  = self._ref
        view = self._view

        dlg = QDialog(view)
        dlg.setWindowTitle("Reference")
        dlg.setMinimumWidth(440)
        dlg.setStyleSheet("background:#2a2a2a; color:#ffffff;")
        layout = QVBoxLayout(dlg)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        lbl = QLabel("Referenced file:")
        lbl.setStyleSheet("color:#aaaaaa; font-size:11px;")
        layout.addWidget(lbl)

        _s = ("QPushButton{background:#3a3a3a;color:#fff;"
              "border:1px solid #5c5c5c;border-radius:4px;"
              "padding:4px 10px;font-size:11px;}"
              "QPushButton:hover{background:#555;}")

        path_row = QHBoxLayout()
        path_lbl = QLabel(ref._flow_path or "—")
        path_lbl.setStyleSheet(
            "background:#1b1b1b;color:#4a9eff;border:1px solid #5c5c5c;"
            "padding:4px;font-size:10px;font-family:monospace;")
        path_lbl.setWordWrap(True)
        path_row.addWidget(path_lbl, 1)

        finder_btn = QPushButton("Show in Finder")
        finder_btn.setStyleSheet(_s)
        def _show():
            import subprocess
            if ref._flow_path and os.path.exists(ref._flow_path):
                subprocess.Popen(["open", "-R", ref._flow_path])
        finder_btn.clicked.connect(_show)
        path_row.addWidget(finder_btn)
        layout.addLayout(path_row)

        browse_btn = QPushButton("Browse…  Choose different file")
        browse_btn.setStyleSheet(_s)
        dlg._new_path = None
        def _browse():
            from config import FILE_FILTER
            new_path, _ = QFileDialog.getOpenFileName(
                view, "Select Reference File", "", FILE_FILTER)
            if new_path:
                path_lbl.setText(new_path)
                dlg._new_path = new_path
        browse_btn.clicked.connect(_browse)
        layout.addWidget(browse_btn)

        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:#444;")
        layout.addWidget(sep)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet(
            "QPushButton{background:#4a9eff;color:#fff;border:none;"
            "border-radius:4px;padding:4px 20px;font-size:11px;}"
            "QPushButton:hover{background:#6ab0ff;}")
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(_s)
        ok_btn.clicked.connect(dlg.accept)
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            if dlg._new_path and dlg._new_path != ref._flow_path:
                ref.load_file(dlg._new_path)
                self.set_path(dlg._new_path)

    def reposition(self):
        scale    = self._view.transform().m11()
        scene_pt = self._ref.mapToScene(QPointF(0, 0))
        vp_pt    = self._view.mapFromScene(scene_pt)
        bar_h    = self.sizeHint().height()
        w        = int(self._ref.width * scale)

        # Hide if node is too small on screen
        if w < 200:
            self.hide()
            return

        self.setFixedWidth(max(200, w))
        self.move(int(vp_pt.x()), int(vp_pt.y()) - bar_h - 4)
        self.show()

    def close(self):
        self.hide()
        self.deleteLater()


# =========================================================
# REFERENCE NODE  (inherits Backdrop)
# =========================================================

class ReferenceNode(Backdrop):
    """A live-linked .flow file embedded as a backdrop.

    Inherits from Backdrop so:
      - Items inside become Qt children via reeval_backdrop_containment
      - Dragging the reference drags all internal items
      - Resize handles work out of the box

    Additional behaviour:
      - QFileSystemWatcher reloads on external file change
      - Edit mode: lock file written, items unlocked
      - View mode: items locked, watcher active
    """

    _HEADER_H   = 30    # scene units reserved for the header area at top
    _PAD        = 24    # padding around content

    def __init__(self, x=0, y=0, view=None, flow_path=""):
        super().__init__(x, y, view)
        self._flow_path    = flow_path
        self._edit_mode    = False
        self._ref_items    = []       # items loaded from the file
        self._header       = None
        self._watcher      = None
        self._reload_timer = None
        self._suppress_header = False

        # Override backdrop defaults
        self._color      = QColor(50, 50, 55, 210)
        self._name       = os.path.basename(flow_path) if flow_path else "Reference"
        self._text       = ""
        self._font_size  = 14
        self._font_color = QColor(180, 180, 180)
        self.setZValue(-8)   # behind normal backdrops

        # Hide all resize handles — reference size is determined by content
        for h in self._handles.values():
            h.hide()
            h.setEnabled(False)

    def mouseDoubleClickEvent(self, event):
        event.accept()   # suppress Backdrop's edit dialog

    # ── File loading ──────────────────────────────────────────────────

    def load_file(self, path, reposition=True):
        """Load external .flow and populate items. Call after addItem().
        Set reposition=False when restoring saved position/size from a .flow file."""
        if not path or not os.path.exists(path):
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[ReferenceNode] Failed to load {path}: {e}")
            return

        self._flow_path = path
        self._name      = os.path.basename(path)
        self._rebuild_items(data, reposition=reposition)
        self._start_watcher()
        if self._header:
            self._header.set_path(path)

    def _rebuild_items(self, data, reposition=True):
        """Load items via from_dict_merge, then optionally size backdrop around them.
        When reposition=False (loading from saved file), use existing pos/size."""
        scene = self.scene()
        if not scene:
            return
        view = self.view

        self._clear_ref_items()

        if not data.get("nodes"):
            return

        # ── Move self far off screen during load so reeval never parents
        #    items to us at the wrong position ─────────────────────────
        _saved_pos = self.pos()
        self.setPos(-999999, -999999)

        # When not repositioning, offset items to land inside the reference boundary
        load_data = copy.deepcopy(data)
        if not reposition and load_data.get("nodes"):
            pad     = self._PAD
            title_h = self._HEADER_H
            ox = _saved_pos.x() + pad
            oy = _saved_pos.y() + pad + title_h
            for nd in load_data["nodes"]:
                nd["x"] = nd.get("x", 0) + ox
                nd["y"] = nd.get("y", 0) + oy

        before = set(id(i) for i in scene.items())
        scene.from_dict_merge(load_data, view)

        self.setPos(_saved_pos)

        # ── Collect and tag ───────────────────────────────────────────
        new_items = [i for i in scene.items()
                     if id(i) not in before and i is not self]
        for item in new_items:
            item._is_reference_item = True
        self._ref_items = new_items

        from node import Node as _Node
        from curve import Dot as _Dot, ConnectionLine as _CL
        from backdrop import Backdrop as _Backdrop
        from note import StickyNote as _StickyNote

        content = [i for i in new_items
                   if isinstance(i, (_Node, _Dot, _Backdrop, _StickyNote))
                   and not isinstance(i, _CL)]

        if not content:
            self._apply_lock_state()
            self.update()
            return

        # ── Un-parent first ───────────────────────────────────────────
        for item in content:
            if item.parentItem() is not None:
                abs_pos = item.scenePos()
                item.setParentItem(None)
                item.setPos(abs_pos)

        if reposition:
            # ── Auto-size: compute bbox and reposition backdrop ────────
            rect = QRectF()
            for item in content:
                rect = rect.united(item.sceneBoundingRect())

            pad     = self._PAD
            title_h = self._HEADER_H
            rect.adjust(-pad, -(pad + title_h), pad, pad)

            self.prepareGeometryChange()
            self.setPos(rect.x(), rect.y())
            self.width  = max(300, rect.width())
            self.height = max(200, rect.height())
            self._reposition_handles()
        # else: keep existing pos/size (restored by caller from saved data)

        # ── Parent content items directly to reference node ──────────
        # Skip reeval_backdrop_containment — it runs again after from_dict
        # and would interfere. Manually parent ref items here.
        for item in content:
            snap = item.scenePos()
            item.setParentItem(self)
            item.setPos(self.mapFromScene(snap))

        self._apply_lock_state()
        self.update()
        if self._header:
            self._header.reposition()

    def _clear_ref_items(self):
        scene = self.scene()
        for item in list(self._ref_items):
            item._is_reference_item = False   # untag before removal
            if scene and item.scene() is scene:
                if isinstance(item, ConnectionLine):
                    item.disconnect_from_sockets()
                scene.removeItem(item)
        self._ref_items.clear()

    # ── Lock / unlock ─────────────────────────────────────────────────

    def _apply_lock_state(self):
        locked = not self._edit_mode
        for item in self._ref_items:
            if isinstance(item, ConnectionLine):
                continue
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
                         not locked)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
                         not locked)

    # ── Edit / View mode ──────────────────────────────────────────────

    def enter_edit_mode(self):
        if not self._flow_path:
            QMessageBox.warning(self.view, "Reference",
                                "No file linked to this reference.")
            return
        if _is_locked(self._flow_path):
            QMessageBox.warning(self.view, "Reference",
                                f"File is locked by another session:\n"
                                f"{self._flow_path}")
            return
        self._edit_mode = True
        self._stop_watcher()
        _write_lock(self._flow_path)
        self._apply_lock_state()
        if self._header:
            self._header.set_edit_mode(True)
        self.update()

    def enter_view_mode(self):
        self._edit_mode = False
        if self._flow_path:
            _remove_lock(self._flow_path)
        self._apply_lock_state()
        self._start_watcher()
        if self._header:
            self._header.set_edit_mode(False)
        self.update()

    def push_to_source(self):
        """Warn user, select internal items, then run Export Selected to source file."""
        view = self.view
        if not self._flow_path:
            return

        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            view,
            "Export Edits",
            "You are about to override an external reference!",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        if reply != QMessageBox.StandardButton.Ok:
            return

        # Temporarily untag so to_dict includes them
        for item in self._ref_items:
            item._is_reference_item = False

        try:
            # Select all internal items
            scene = self.scene()
            scene.clearSelection()
            for item in self._ref_items:
                if hasattr(item, 'setSelected'):
                    item.setSelected(True)

            # Export Selected to the source file
            view.export_selected(path=self._flow_path)
        finally:
            # Re-tag regardless of outcome
            for item in self._ref_items:
                item._is_reference_item = True

        # Close edit mode and confirm
        self.enter_view_mode()
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox(view)
        msg.setWindowTitle("Reference")
        msg.setText("Reference has been updated!")
        msg.setStandardButtons(QMessageBox.StandardButton.Close)
        msg.exec()

    # ── File watcher ──────────────────────────────────────────────────

    def _start_watcher(self):
        if self._watcher:
            try:
                self._watcher.fileChanged.disconnect()
            except Exception:
                pass
        self._watcher = QFileSystemWatcher()
        if self._flow_path:
            self._watcher.addPath(self._flow_path)
        self._watcher.fileChanged.connect(self._on_file_changed)

    def _stop_watcher(self):
        if self._watcher:
            try:
                self._watcher.fileChanged.disconnect()
            except Exception:
                pass
            self._watcher = None

    def _on_file_changed(self, path):
        if self._edit_mode:
            return
        if self._reload_timer:
            self._reload_timer.stop()
        self._reload_timer = QTimer()
        self._reload_timer.setSingleShot(True)
        self._reload_timer.setInterval(500)
        self._reload_timer.timeout.connect(self._do_reload)
        self._reload_timer.start()
        if self._watcher and path not in self._watcher.files():
            self._watcher.addPath(path)

    def _do_reload(self):
        if not self._edit_mode and self._flow_path:
            self.load_file(self._flow_path)

    # ── Header ────────────────────────────────────────────────────────

    def attach_header(self, view):
        self._header = ReferenceHeader(self, view)
        self._header.set_path(self._flow_path)
        self._header.set_edit_mode(self._edit_mode)
        self._header.reposition()

    def detach_header(self):
        if self._header:
            self._header.close()
            self._header = None

    def reposition_header(self):
        if self._suppress_header:
            return
        if self._header:
            self._header.reposition()

    # ── itemChange ────────────────────────────────────────────────────

    def itemChange(self, change, value):
        # When removed from scene, clean up lock/watcher/header/items
        if change == QGraphicsItem.GraphicsItemChange.ItemSceneChange:
            if value is None and self.scene() is not None:
                self.cleanup()
        result = super().itemChange(change, value)
        if change in (QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged,
                      QGraphicsItem.GraphicsItemChange.ItemScenePositionHasChanged):
            if not getattr(self, '_suppress_header', False):
                self.reposition_header()
        return result

    # ── Cleanup ───────────────────────────────────────────────────────

    def cleanup(self):
        self._stop_watcher()
        if self._flow_path:
            _remove_lock(self._flow_path)
        self.detach_header()
        self._clear_ref_items()

    # ── Paint ─────────────────────────────────────────────────────────

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width, self.height)

        # Body fill
        painter.setBrush(QBrush(self._color))
        border = QColor(100, 180, 100) if self._edit_mode \
                 else QColor(90, 90, 95)
        painter.setPen(QPen(border, 1.5))
        painter.drawRoundedRect(rect, 12, 12)

        # Header strip
        hdr = QRectF(0, 0, self.width, self._HEADER_H)
        hdr_col = QColor(55, 80, 55, 230) if self._edit_mode \
                  else QColor(38, 38, 42, 230)
        painter.setBrush(QBrush(hdr_col))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(hdr, 12, 12)
        painter.drawRect(QRectF(0, 12, self.width, self._HEADER_H - 12))

        # File name
        painter.setPen(QPen(QColor("#cccccc")))
        painter.setFont(QFont("Menlo", 10, QFont.Weight.Bold))
        name = os.path.basename(self._flow_path) if self._flow_path else "Reference"
        painter.drawText(
            QRectF(10, 0, self.width - 90, self._HEADER_H),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            name)

        # Mode badge
        if self._edit_mode:
            painter.setPen(QPen(QColor("#88ff88")))
            painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            painter.drawText(
                QRectF(self.width - 85, 0, 80, self._HEADER_H),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                "● EDIT")
        else:
            painter.setPen(QPen(QColor("#777777")))
            painter.setFont(QFont("Arial", 9))
            painter.drawText(
                QRectF(self.width - 85, 0, 80, self._HEADER_H),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                "○ VIEW")

        # Selection ring
        if self.isSelected():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(255, 255, 255, 70), 2))
            painter.drawRoundedRect(rect, 12, 12)


# =========================================================
# CREATION HELPER
# =========================================================

def create_reference_node_at(view, pos):
    from config import FILE_FILTER
    path, _ = QFileDialog.getOpenFileName(
        view, "Link Reference File", "", FILE_FILTER)
    if not path:
        return None

    if _is_locked(path):
        reply = QMessageBox.question(
            view, "Reference",
            f"This file is locked by another session:\n{path}\n\n"
            "Open as read-only view?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return None

    scene = view._scene
    node = ReferenceNode(pos.x(), pos.y(), view, path)
    scene.addItem(node)

    # Load AFTER addItem so scene exists for from_dict_merge
    node.load_file(path)

    # Now node has final size — find non-overlapping position
    x, y = scene._non_overlapping(
        node.scenePos().x(), node.scenePos().y(),
        node.width, node.height, step=40, max_tries=200)
    node.setPos(x, y)

    node.attach_header(view)

    scene._push_undo({"type": "add_node", "node": node})
    scene.mark_dirty()
    if hasattr(view, '_check_logo_fade'):
        view._check_logo_fade()
    return node
