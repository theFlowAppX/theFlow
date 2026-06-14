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

# group.py
# =========================================================
# GROUP NODE
# =========================================================
# Shortcut: G
# Groups selected nodes into a single GroupNode.
# Arrow-down on a selected GroupNode dives into its internal scene.
# Arrow-up exits back to the parent scene.
# The "Explode" button extracts all internal nodes back to the parent
# scene, restores external connections, and removes the GroupNode.
# =========================================================

import os

from PyQt6.QtWidgets import (
    QGraphicsItem, QWidget, QLabel,
    QHBoxLayout, QPushButton, QMessageBox,
)
from PyQt6.QtGui import QColor, QPen, QBrush, QPainter, QFont
from PyQt6.QtCore import Qt, QRectF, QPointF

from scene_logic import Scene
from node import Node
from curve import Socket, ConnectionLine, Dot
from backdrop import Backdrop
from note import StickyNote
from utils import NODE_BG, NODE_BORDER, CORNER_RADIUS, SOCKET_SIZE, SOCKET_COLOR


# =========================================================
# GROUP SCENE  –  an internal QGraphicsScene owned by GroupNode
# =========================================================

class GroupScene(Scene):
    """Internal scene for a GroupNode. Inherits all Scene behaviour so the
    View works unchanged inside a group."""

    def __init__(self, group_node, parent_scene):
        super().__init__()
        self._group_node    = group_node
        self._parent_scene  = parent_scene
        self._view          = parent_scene._view
        self._current_settings = getattr(parent_scene, '_current_settings', {})
        self.setSceneRect(-100000, -100000, 200000, 200000)

    def mark_dirty(self):
        self._dirty = True
        self._parent_scene.mark_dirty()
        if self._view:
            self._view.update_title()
            self._view.viewport().update()


# =========================================================
# BREADCRUMB BAR  –  shown inside the view while inside a group
# =========================================================

class GroupBreadcrumb(QWidget):
    """Floating bar at the top of the viewport showing the navigation path
    and an Exit Group (↑) button."""

    def __init__(self, view, path_names):
        super().__init__(view)
        self.setStyleSheet(
            "background:#1a1a2e; border-bottom:1px solid #4a9eff;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(6)

        # Path labels  e.g.  Main  >  Group A  >  Group B
        for i, name in enumerate(path_names):
            lbl = QLabel(name)
            if i == len(path_names) - 1:
                lbl.setStyleSheet("color:#4a9eff; font-weight:bold; font-size:12px;")
            else:
                lbl.setStyleSheet("color:#888888; font-size:12px;")
            layout.addWidget(lbl)
            if i < len(path_names) - 1:
                sep = QLabel("›")
                sep.setStyleSheet("color:#555; font-size:12px;")
                layout.addWidget(sep)

        layout.addStretch()

        exit_btn = QPushButton("↑  Exit Group")
        exit_btn.setStyleSheet(
            "QPushButton{background:#2a2a4a;color:#4a9eff;border:1px solid #4a9eff;"
            "border-radius:4px;padding:2px 12px;font-size:11px;}"
            "QPushButton:hover{background:#3a3a6a;}")
        exit_btn.clicked.connect(view.group_exit)
        layout.addWidget(exit_btn)

        self.setFixedHeight(32)
        self.resize(view.width(), 32)
        self.show()
        self.raise_()

    def resizeEvent(self, event):
        if self.parent():
            self.resize(self.parent().width(), 32)


# =========================================================
# GROUP NODE
# =========================================================

class GroupNode(Node):
    """A node that encapsulates a sub-graph.

    External connections that crossed the group boundary become
    input/output sockets on the GroupNode. The node can have multiple
    input sockets (left side) and multiple output sockets (right side).

    The internal GroupScene stores the original nodes and their connections.
    Port sockets (GroupPortIn / GroupPortOut) appear inside the group scene
    to represent the boundary connections.
    """

    _SOCK_R   = SOCKET_SIZE * 2
    _GROUP_COLOR = QColor(40, 40, 70)

    def __init__(self, x=0, y=0, view=None, name="Group",
                 internal_scene=None):
        # Initialise as a Node but we'll manage our own sockets
        super().__init__(x, y, view, name)
        self._node_type     = "group"
        self._group_scene   = internal_scene   # GroupScene
        self._inline_player = None

        # Extra sockets beyond the built-in in/out pair
        self._extra_in_sockets  = []   # list of Socket
        self._extra_out_sockets = []

        # Mapping: (socket on GroupNode) ↔ (port node inside GroupScene)
        self._port_for_socket   = {}   # socket → GroupPortNode
        self._socket_for_port   = {}   # port_node → socket

        # Override color
        self._color = self._GROUP_COLOR

    # ── Dive in ───────────────────────────────────────────────────────

    def dive_in(self):
        view = self.scene().views()[0] if self.scene() and self.scene().views() else None
        if view and self._group_scene:
            view.group_enter(self)

    # ── Explode ───────────────────────────────────────────────────────

    def explode(self):
        """Extract internal nodes back to the parent scene and remove this GroupNode."""
        view = self.scene().views()[0] if self.scene() and self.scene().views() else None
        if not view or not self._group_scene:
            return

        parent_scene = self.scene()
        gscene       = self._group_scene
        offset       = self.scenePos()

        # ── 1. Collect real internal items (exclude port nodes) ───────
        from node import Node as _Node
        from backdrop import Backdrop
        from note import StickyNote
        from curve import Dot as _Dot

        internal_nodes = [
            i for i in gscene.items()
            if isinstance(i, (_Node, Backdrop, StickyNote))
            and not isinstance(i, GroupPortNode)
        ]
        internal_conns = [
            i for i in gscene.items()
            if isinstance(i, ConnectionLine)
            and not isinstance(i.a.parent_node, GroupPortNode)
            and not isinstance(i.b.parent_node, GroupPortNode)
        ]

        # ── 2. Move internal nodes to parent scene ────────────────────
        for item in internal_nodes:
            old_pos = item.scenePos()
            gscene.removeItem(item)
            parent_scene.addItem(item)
            item.setPos(offset + old_pos)

        # ── 3. Move internal connections to parent scene ──────────────
        for conn in internal_conns:
            gscene.removeItem(conn)
            parent_scene.addItem(conn)

        # ── 4. Rewire boundary connections ────────────────────────────
        for sock, port in self._port_for_socket.items():
            if isinstance(port, GroupPortIn):
                # Find internal socket(s) connected to port.out_socket
                int_sockets = []
                for conn in list(port.out_socket.connections):
                    s = conn.b if conn.a is port.out_socket else conn.a
                    if not isinstance(s.parent_node, GroupPortNode):
                        int_sockets.append(s)
                # Find external socket connected to the group socket
                for ec in list(sock.connections):
                    ext_sock = ec.a if ec.b is sock else ec.b
                    ec.disconnect_from_sockets()
                    parent_scene.removeItem(ec)
                    for int_sock in int_sockets:
                        new_conn = ConnectionLine(ext_sock, int_sock)
                        parent_scene.addItem(new_conn)
                        ext_sock.connections.append(new_conn)
                        int_sock.connections.append(new_conn)

            elif isinstance(port, GroupPortOut):
                int_sockets = []
                for conn in list(port.in_socket.connections):
                    s = conn.a if conn.b is port.in_socket else conn.b
                    if not isinstance(s.parent_node, GroupPortNode):
                        int_sockets.append(s)
                for ec in list(sock.connections):
                    ext_sock = ec.a if ec.b is sock else ec.b
                    ec.disconnect_from_sockets()
                    parent_scene.removeItem(ec)
                    for int_sock in int_sockets:
                        new_conn = ConnectionLine(int_sock, ext_sock)
                        parent_scene.addItem(new_conn)
                        int_sock.connections.append(new_conn)
                        ext_sock.connections.append(new_conn)

        # ── 5. Nuke everything remaining in the group scene ───────────
        for item in list(gscene.items()):
            if isinstance(item, ConnectionLine):
                item.disconnect_from_sockets()
            gscene.removeItem(item)

        # ── 6. Remove all GroupNode sockets' remaining connections ─────
        all_socks = ([self.in_socket, self.out_socket]
                     + self._extra_in_sockets
                     + self._extra_out_sockets)
        for s in all_socks:
            for ec in list(s.connections):
                ec.disconnect_from_sockets()
                if ec.scene():
                    ec.scene().removeItem(ec)

        # ── 7. Remove the GroupNode itself ────────────────────────────
        parent_scene.removeItem(self)
        parent_scene.mark_dirty()
        parent_scene._check_logo_fade() if hasattr(parent_scene, '_check_logo_fade') else None
        if hasattr(view, '_check_logo_fade'):
            view._check_logo_fade()

    # ── Paint ─────────────────────────────────────────────────────────

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            view = (self.scene().views()[0]
                    if self.scene() and self.scene().views() else None)
            if not view:
                event.accept()
                return
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout
            dlg = QDialog(view)
            dlg.setWindowTitle("Group")
            dlg.setStyleSheet("background:#2a2a2a; color:#ffffff;")
            dlg.setMinimumWidth(260)
            layout = QVBoxLayout(dlg)
            layout.setSpacing(10)
            layout.setContentsMargins(16, 16, 16, 16)

            from PyQt6.QtWidgets import QLabel
            lbl = QLabel(f"<b>{self.title._plain}</b>")
            lbl.setStyleSheet("color:#aaaaff; font-size:13px;")
            layout.addWidget(lbl)

            btn_row = QHBoxLayout()

            _grey = ("QPushButton{background:#3a3a3a;color:#ffffff;"
                     "border:1px solid #555;border-radius:4px;"
                     "padding:6px 16px;font-size:12px;}"
                     "QPushButton:hover{background:#4a4a4a;}")

            dive_btn = QPushButton("Dive In")
            dive_btn.setStyleSheet(_grey)
            dive_btn.clicked.connect(lambda: (dlg.accept(), self.dive_in()))
            btn_row.addWidget(dive_btn)

            explode_btn = QPushButton("Explode")
            explode_btn.setStyleSheet(_grey)
            explode_btn.clicked.connect(lambda: (dlg.accept(), self.explode()))
            btn_row.addWidget(explode_btn)

            layout.addLayout(btn_row)

            cancel_btn = QPushButton("Cancel")
            cancel_btn.setStyleSheet(
                "QPushButton{background:#333;color:#aaa;border:1px solid #555;"
                "border-radius:4px;padding:4px 16px;font-size:11px;}"
                "QPushButton:hover{background:#444;}")
            cancel_btn.clicked.connect(dlg.reject)
            layout.addWidget(cancel_btn)

            dlg.exec()
            event.accept()

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width, self.height)

        if self.isSelected():
            glow = QColor(100, 100, 220, 40)
            for i in range(8):
                spread = i * 1.5
                c = QColor(glow); c.setAlpha(max(0, 40 - i * 5))
                painter.setPen(QPen(c, 1 + i))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(
                    rect.adjusted(-spread, -spread, spread, spread),
                    CORNER_RADIUS + spread, CORNER_RADIUS + spread)

        painter.setBrush(QBrush(self._color))
        painter.setPen(QPen(QColor("#6666cc"), 1.5))
        painter.drawRoundedRect(rect, CORNER_RADIUS, CORNER_RADIUS)

        if self.isSelected():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(180, 180, 255, 160), 2))
            painter.drawRoundedRect(rect, CORNER_RADIUS, CORNER_RADIUS)

        # SVG icon badge
        self._draw_group_icon(painter)

    _PNG_GROUP_BLACK = None
    _PNG_GROUP_WHITE = None

    @classmethod
    def _get_group_icons(cls):
        if cls._PNG_GROUP_BLACK is None:
            from node import _svg_to_pixmap
            _base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
            cls._PNG_GROUP_BLACK = _svg_to_pixmap(
                os.path.join(_base, "group_black.svg"))
            cls._PNG_GROUP_WHITE = _svg_to_pixmap(
                os.path.join(_base, "group_white.svg"))
        return cls._PNG_GROUP_BLACK, cls._PNG_GROUP_WHITE

    def _draw_group_icon(self, painter):
        black_px, white_px = self._get_group_icons()
        px = white_px if (black_px is None or black_px.isNull()) else black_px
        # Use white when we have a url set (dark bg), same pattern as other nodes
        px = white_px
        if px is None or px.isNull():
            # Fallback to text badge
            painter.setPen(QPen(QColor("#ffffff")))
            painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            badge_r = 10
            ox = self.width - self._SOCK_R - 2
            ty = self.title.pos().y()
            th = self.title.boundingRect().height()
            cx = int(ox - badge_r - 6)
            cy = int(ty + th / 2)
            painter.setBrush(QBrush(QColor(80, 80, 160)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(cx, cy), badge_r, badge_r)
            painter.setPen(QPen(QColor("#ffffff")))
            painter.drawText(
                QRectF(cx - badge_r, cy - badge_r, badge_r * 2, badge_r * 2),
                Qt.AlignmentFlag.AlignCenter, "G")
            return
        icon_size = 56
        gap = 10
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
# GROUP PORT NODES  –  live inside GroupScene as boundaries
# =========================================================

class GroupPortNode(Node):
    """Base class for port nodes that appear inside the GroupScene."""
    pass


class GroupPortIn(GroupPortNode):
    """Input boundary — data flows in from parent. Has only right (out) socket."""
    def __init__(self, x, y, view, name="In"):
        super().__init__(x, y, view, name)
        self._color = QColor(30, 60, 30)
        self.in_socket.setVisible(False)
        self.in_socket.setFlag(
            self.in_socket.GraphicsItemFlag.ItemIsMovable, False)
        # Detach and hide the text title — port nodes show name via paint()
        self.title.setParentItem(None)
        self.title.setVisible(False)

    def open_inline_text_viewer(self): pass
    def close_inline_text_viewer(self): pass

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width, self.height)
        painter.setBrush(QBrush(self._color))
        painter.setPen(QPen(QColor("#44aa44"), 1.5))
        painter.drawRoundedRect(rect, CORNER_RADIUS, CORNER_RADIUS)
        painter.setPen(QPen(QColor("#88ff88")))
        painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter,
                         self.title._plain)


class GroupPortOut(GroupPortNode):
    """Output boundary — data flows out to parent. Has only left (in) socket."""
    def __init__(self, x, y, view, name="Out"):
        super().__init__(x, y, view, name)
        self._color = QColor(60, 30, 30)
        self.out_socket.setVisible(False)
        self.out_socket.setFlag(
            self.out_socket.GraphicsItemFlag.ItemIsMovable, False)
        self.title.setParentItem(None)
        self.title.setVisible(False)

    def open_inline_text_viewer(self): pass
    def close_inline_text_viewer(self): pass

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width, self.height)
        painter.setBrush(QBrush(self._color))
        painter.setPen(QPen(QColor("#aa4444"), 1.5))
        painter.drawRoundedRect(rect, CORNER_RADIUS, CORNER_RADIUS)
        painter.setPen(QPen(QColor("#ff8888")))
        painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter,
                         self.title._plain)


# =========================================================
# GROUP CREATION  –  called by View.create_group
# =========================================================

def create_group_from_selection(view):
    """
    Groups the currently selected items in view._scene into a GroupNode.

    Steps:
    1. Collect selected nodes and their inter-connections
    2. Find boundary connections (one end inside, one end outside)
    3. Create GroupScene, move items into it
    4. Create GroupPortIn/Out nodes at the boundary
    5. Create GroupNode with N input + N output sockets
    6. Rewire external connections to GroupNode sockets
    7. Remove original items from parent scene
    """
    from scene_logic import Scene
    scene = view._scene
    # Collect all groupable items: nodes, dots, backdrops, stickies
    _groupable = (Node, Dot, Backdrop, StickyNote)
    selected_nodes = [i for i in scene.selectedItems()
                      if isinstance(i, Node) and not isinstance(i, GroupNode)]
    selected_extras = [i for i in scene.selectedItems()
                       if isinstance(i, (Backdrop, StickyNote))]
    selected_dots   = [i for i in scene.selectedItems()
                       if isinstance(i, Dot)]
    selected = selected_nodes + selected_dots
    all_selected = selected + selected_extras

    if not all_selected:
        QMessageBox.information(view, "Group", "Nothing selected to group!")
        return

    selected_set = set(id(i) for i in selected)   # nodes+dots for connection boundary

    # ── Find boundary connections ──────────────────────────────────
    # boundary_in:  external_out_socket → internal_in_socket
    # boundary_out: internal_out_socket → external_in_socket
    boundary_in  = []   # (ext_socket, int_socket, conn)
    boundary_out = []   # (int_socket, ext_socket, conn)
    internal_conns = []

    for item in scene.items():
        if not isinstance(item, ConnectionLine):
            continue
        a_internal = id(item.a.parent_node) in selected_set
        b_internal = id(item.b.parent_node) in selected_set

        if a_internal and b_internal:
            internal_conns.append(item)
        elif not a_internal and b_internal:
            # a is external out, b is internal in
            boundary_in.append((item.a, item.b, item))
        elif a_internal and not b_internal:
            # a is internal out, b is external in
            boundary_out.append((item.a, item.b, item))

    # ── Un-parent all selected items first ───────────────────────────
    # reeval_backdrop_containment makes items children of backdrops;
    # scenePos() becomes relative to parent — must un-parent before snapshot
    for item in all_selected:
        if item.parentItem() is not None:
            abs_pos = item.scenePos()
            item.setParentItem(None)
            item.setPos(abs_pos)

    # ── Snapshot ALL positions BEFORE any scene manipulation ──────────
    # Use item object as key (NOT id() — Python reuses addresses after GC)
    snaps = {item: item.scenePos() for item in all_selected}

    # ── Compute group node position (centroid of all selected items) ──
    xs = [snaps[n].x() for n in all_selected]
    ys = [snaps[n].y() for n in all_selected]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)

    # ── Compute bounding box from snapshots ───────────────────────────
    abs_lefts  = [snaps[n].x() for n in all_selected]
    abs_rights = [snaps[n].x() + getattr(n, 'width', n.boundingRect().width())
                  for n in all_selected]
    abs_left   = min(abs_lefts)
    abs_right  = max(abs_rights)

    # Port positions in internal (centroid-relative) coords
    # Place ports 5× node width outside the actual bounding box edges
    NODE_W     = 240
    GAP        = NODE_W * 5
    box_left   = abs_left  - cx - GAP
    box_right  = abs_right - cx + GAP

    # ── Create GroupScene ──────────────────────────────────────────
    gscene = GroupScene(None, scene)

    # ── Move all selected items into GroupScene using snapshots ───────
    for node in all_selected:
        snap = snaps[node]
        scene.removeItem(node)
        gscene.addItem(node)
        node.setPos(snap - QPointF(cx, cy))

    # Move internal connections
    for conn in internal_conns:
        scene.removeItem(conn)
        gscene.addItem(conn)

    # ── Create port nodes inside the group ────────────────────────
    port_spacing = 120
    port_in_nodes  = []
    port_out_nodes = []

    for i, (ext_sock, int_sock, conn) in enumerate(boundary_in):
        px = box_left
        py = (i - (len(boundary_in) - 1) / 2) * port_spacing
        port = GroupPortIn(px, py, view, f"In {i+1}")
        gscene.addItem(port)
        # Connect port's out_socket → int_sock
        scene.removeItem(conn)
        new_conn = ConnectionLine(port.out_socket, int_sock)
        gscene.addItem(new_conn)
        port.out_socket.connections.append(new_conn)
        int_sock.connections.append(new_conn)
        port_in_nodes.append((port, ext_sock))

    for i, (int_sock, ext_sock, conn) in enumerate(boundary_out):
        px = box_right
        py = (i - (len(boundary_out) - 1) / 2) * port_spacing
        port = GroupPortOut(px, py, view, f"Out {i+1}")
        gscene.addItem(port)
        # Connect int_sock → port's in_socket
        scene.removeItem(conn)
        new_conn = ConnectionLine(int_sock, port.in_socket)
        gscene.addItem(new_conn)
        int_sock.connections.append(new_conn)
        port.in_socket.connections.append(new_conn)
        port_out_nodes.append((port, ext_sock))

    # ── Create GroupNode in parent scene ──────────────────────────
    n_in  = len(port_in_nodes)
    n_out = len(port_out_nodes)
    group = GroupNode(cx - 120, cy - 45, view,
                      name="Group",
                      internal_scene=gscene)
    gscene._group_node = group
    scene.addItem(group)
    scene._push_undo({"type": "add_node", "node": group})

    # ── Add extra sockets to GroupNode ────────────────────────────
    # The Node base already provides in_socket (input) and out_socket (output).
    # We repurpose them for the first ports and add more as needed.

    all_in_sockets  = _ensure_sockets(group, n_in,  is_input=True)
    all_out_sockets = _ensure_sockets(group, n_out, is_input=False)

    # ── Wire external connections to GroupNode sockets ────────────
    for i, (port, ext_sock) in enumerate(port_in_nodes):
        gsock = all_in_sockets[i]
        new_conn = ConnectionLine(ext_sock, gsock)
        scene.addItem(new_conn)
        ext_sock.connections.append(new_conn)
        gsock.connections.append(new_conn)
        group._port_for_socket[gsock] = port
        group._socket_for_port[port]  = gsock

    for i, (port, ext_sock) in enumerate(port_out_nodes):
        gsock = all_out_sockets[i]
        new_conn = ConnectionLine(gsock, ext_sock)
        scene.addItem(new_conn)
        gsock.connections.append(new_conn)
        ext_sock.connections.append(new_conn)
        group._port_for_socket[gsock] = port
        group._socket_for_port[port]  = gsock

    scene.mark_dirty()
    return group


def _ensure_sockets(group_node, count, is_input):
    """Return a list of `count` sockets on group_node (creating extras as needed)."""
    base = group_node.in_socket if is_input else group_node.out_socket
    existing = [base] + (group_node._extra_in_sockets if is_input
                         else group_node._extra_out_sockets)
    while len(existing) < count:
        sock = Socket(group_node, is_input=is_input)
        if is_input:
            group_node._extra_in_sockets.append(sock)
        else:
            group_node._extra_out_sockets.append(sock)
        existing.append(sock)

    # Reposition all sockets vertically
    _reposition_extra_sockets(group_node, existing, is_input)
    return existing[:count]


def _reposition_extra_sockets(group_node, sockets, is_input):
    """Spread sockets evenly down the left (input) or right (output) side."""
    n = len(sockets)
    h = group_node.height
    sock_r = group_node._SOCK_R
    for i, sock in enumerate(sockets):
        y = (i + 1) * h / (n + 1) - sock_r
        x = -sock_r if is_input else group_node.width - sock_r
        sock.setPos(x, y)
