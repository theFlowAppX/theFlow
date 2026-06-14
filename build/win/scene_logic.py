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

# scene_logic.py
# =========================================================
# SCENE LOGIC FOR THEFLOW!
# =========================================================

from PyQt6.QtWidgets import QGraphicsScene, QMessageBox
from PyQt6.QtGui import QColor, QPainter, QFont
from PyQt6.QtCore import Qt, QPointF, QRectF

from config import DARK, FILE_FILTER, DEFAULT_FILE_EXT
from node import Node, ImageNode, MovieNode, AudioNode, DocumentNode
from paint import PaintNode
from curve import ConnectionLine, Socket, Dot
from backdrop import Backdrop
from note import StickyNote
from utils import _remove_from, HANDLE_SIZE

class Scene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self._view = None
        self._undo_stack = []
        self._redo_stack = []
        self._dirty = False
        self._current_settings = {}

    # ── Dirty Flag ─────────────────────────────────────────────

    def mark_dirty(self):
        self._dirty = True
        if self._view:
            self._view.update_title()
            self._view.viewport().update()

    # ── Backdrop Containment ─────────────────────────────

    def reeval_backdrop_containment(self, bd=None):
        """Re-evaluate backdrop parenting on mouse release.

        Any item (including backdrops) fully inside a backdrop becomes a Qt
        child so it moves with it. Each item goes to the innermost
        (smallest-area) backdrop that fully contains it.
        Nested backdrops always sit further forward in z than their parent.
        ConnectionLine / Socket items are always ignored.
        """
        STRIDE = 100

        backdrops  = [i for i in self.items() if isinstance(i, Backdrop)]
        candidates = [i for i in self.items()
                      if isinstance(i, (Node, Dot, StickyNote, Backdrop))]

        # ── Step 1: un-parent EVERYTHING so sceneBoundingRect is accurate ─
        for item in candidates:
            if item.parentItem() is not None:
                scene_pos = item.scenePos()
                item.setParentItem(None)
                item.setPos(scene_pos)

        # ── Step 2: clear pinned sets ─────────────────────────────────────
        for b in backdrops:
            b._pinned_children.clear()

        # ── Step 3: assign each item to its innermost backdrop ───────────
        for item in candidates:
            item_br    = item.sceneBoundingRect()
            owner      = None
            owner_area = float('inf')
            for b in backdrops:
                if b is item:
                    continue
                b_br = b.sceneBoundingRect().adjusted(2, 2, -2, -2)
                if b_br.contains(item_br):
                    area = b.width * b.height
                    if area < owner_area:
                        owner_area = area
                        owner      = b
            if owner is not None:
                owner._pinned_children.add(item)

        # ── Step 4: apply Qt parentage to ALL candidates ─────────────────
        # Parent backdrops first (outer → inner) so child backdrops get the
        # right parent before their own children are re-parented.
        def _sort_key(b):
            # smaller area = more nested = should be parented later
            return b.width * b.height

        for b in sorted(backdrops, key=_sort_key, reverse=True):
            owner = next(
                (other for other in backdrops if b in other._pinned_children), None)
            if owner is not None:
                scene_pos = b.scenePos()
                b.setParentItem(owner)
                b.setPos(owner.mapFromScene(scene_pos))

        for item in candidates:
            if isinstance(item, Backdrop):
                continue
            owner = next(
                (b for b in backdrops if item in b._pinned_children), None)
            if owner is not None:
                scene_pos = item.scenePos()
                item.setParentItem(owner)
                item.setPos(owner.mapFromScene(scene_pos))

        # ── Step 5: compute nesting depth for every backdrop ─────────────
        depth_map = {}

        def _depth(b):
            if b in depth_map:
                return depth_map[b]
            parent = next(
                (other for other in backdrops if b in other._pinned_children),
                None)
            d = 0 if parent is None else _depth(parent) + 1
            depth_map[b] = d
            return d

        for b in backdrops:
            _depth(b)

        # ── Step 6: assign z-values ───────────────────────────────────────
        # Nested backdrop: parent_depth * STRIDE + STRIDE/2  (sits above parent,
        # below parent's non-backdrop children which are at depth*STRIDE + 50)
        for b in backdrops:
            d = depth_map[b]
            # z is relative to parent when Qt-parented, so just use depth offset
            b.setZValue(d * STRIDE)

        for item in candidates:
            if isinstance(item, Backdrop):
                continue
            owner = next(
                (b for b in backdrops if item in b._pinned_children), None)
            d = 0 if owner is None else depth_map[owner] + 1
            item.setZValue(d * STRIDE + 50)

    # ── Undo / Redo ───────────────────────────────────────

    def _push_undo(self, cmd):
        self._undo_stack.append(cmd)
        self._redo_stack.clear()
        self.mark_dirty()

    def undo(self):
        if not self._undo_stack:
            return
        cmd = self._undo_stack.pop()
        self._apply(cmd, undo=True)
        self._redo_stack.append(cmd)

    def redo(self):
        if not self._redo_stack:
            return
        cmd = self._redo_stack.pop()
        self._apply(cmd, undo=False)
        self._undo_stack.append(cmd)

    def _apply(self, cmd, undo):
        t = cmd["type"]

        if t == "add_node":
            if undo:
                self.removeItem(cmd["node"])
            else:
                self.addItem(cmd["node"])

        elif t == "del_node":
            if undo:
                self.addItem(cmd["node"])
                for conn in cmd.get("conns", []):
                    self.addItem(conn)
                    conn.a.connections.append(conn)
                    conn.b.connections.append(conn)
            else:
                for conn in cmd.get("conns", []):
                    conn.disconnect_from_sockets()
                    self.removeItem(conn)
                self.removeItem(cmd["node"])

        elif t == "add_conn":
            if undo:
                cmd["conn"].disconnect_from_sockets()
                self.removeItem(cmd["conn"])
            else:
                self.addItem(cmd["conn"])
                cmd["conn"].a.connections.append(cmd["conn"])
                cmd["conn"].b.connections.append(cmd["conn"])

        elif t == "del_conn":
            if undo:
                self.addItem(cmd["conn"])
                cmd["a"].connections.append(cmd["conn"])
                cmd["b"].connections.append(cmd["conn"])
            else:
                cmd["conn"].disconnect_from_sockets()
                self.removeItem(cmd["conn"])

        elif t == "rehook":
            c = cmd["conn"]
            if undo:
                _remove_sock(c, cmd["new_a"])
                _remove_sock(c, cmd["new_b"])
                c.a = cmd["old_a"]
                c.b = cmd["old_b"]
                cmd["old_a"].connections.append(c)
                cmd["old_b"].connections.append(c)
            else:
                _remove_sock(c, cmd["old_a"])
                _remove_sock(c, cmd["new_b"])
                c.a = cmd["new_a"]
                c.b = cmd["new_b"]
                cmd["new_a"].connections.append(c)
                cmd["new_b"].connections.append(c)
            c.update_path()

        elif t == "curve_type":
            cmd["conn"].curve_type = cmd["old"] if undo else cmd["new"]
            cmd["conn"].update_path()

        elif t == "line_style":
            cmd["conn"]._line_style = cmd["old"] if undo else cmd["new"]
            cmd["conn"].update()

        elif t == "curve_color":
            cmd["conn"]._line_color = cmd["old"] if undo else cmd["new"]
            cmd["conn"].update()

        elif t == "split_curve":
            orig = cmd["original"]
            if undo:
                for c in (cmd["c1"], cmd["c2"]):
                    c.disconnect_from_sockets()
                    self.removeItem(c)
                self.removeItem(cmd["dot"])
                orig.a = cmd["orig_a"]
                orig.b = cmd["orig_b"]
                self.addItem(orig)
                orig.a.connections.append(orig)
                orig.b.connections.append(orig)
                orig.update_path()
            else:
                orig.disconnect_from_sockets()
                self.removeItem(orig)
                self.addItem(cmd["dot"])
                for c in (cmd["c1"], cmd["c2"]):
                    self.addItem(c)
                    c.a.connections.append(c)
                    c.b.connections.append(c)
                cmd["c1"].update_path()
                cmd["c2"].update_path()

        elif t == "join_curves":
            if undo:
                self.removeItem(cmd["merged"])
                _remove_from(cmd["merged"].a.connections, cmd["merged"])
                _remove_from(cmd["merged"].b.connections, cmd["merged"])
                self.addItem(cmd["dot"])
                for c in (cmd["c1"], cmd["c2"]):
                    self.addItem(c)
                    c.a.connections.append(c)
                    c.b.connections.append(c)
            else:
                for c in (cmd["c1"], cmd["c2"]):
                    c.disconnect_from_sockets()
                    self.removeItem(c)
                self.removeItem(cmd["dot"])
                self.addItem(cmd["merged"])
                cmd["merged"].a.connections.append(cmd["merged"])
                cmd["merged"].b.connections.append(cmd["merged"])

        elif t == "node_color":
            cmd["node"]._color = cmd["old"] if undo else cmd["new"]
            cmd["node"].update()

        elif t == "node_font_size":
            sz = cmd["old"] if undo else cmd["new"]
            cmd["node"]._font_size = sz
            cmd["node"].title.set_font_size(sz)
            cmd["node"].update()

        elif t == "node_font_color":
            c = cmd["old"] if undo else cmd["new"]
            cmd["node"]._font_color = c
            cmd["node"].title.set_font_color(c)
            cmd["node"].update()

        elif t == "node_shape":
            cmd["node"]._shape = cmd["old"] if undo else cmd["new"]
            cmd["node"]._apply_shape_size()
            cmd["node"]._apply_orientation()
            cmd["node"].update()

        elif t == "image_node_edit":
            node = cmd["node"]
            node.title._plain = cmd["old_name"] if undo else cmd["new_name"]
            node.title.setPlainText(node.title._plain)
            node._image_path = cmd["old_path"] if undo else cmd["new_path"]
            node._load_pixmap()
            node._fit_to_text()
            node.update()

        elif t == "movie_node_edit":
            node = cmd["node"]
            node.title._plain = cmd["old_name"] if undo else cmd["new_name"]
            node.title.setPlainText(node.title._plain)
            node._movie_path = cmd["old_path"] if undo else cmd["new_path"]
            node._fit_to_text()
            node.update()

        elif t == "audio_node_edit":
            node = cmd["node"]
            node.title._plain = cmd["old_name"] if undo else cmd["new_name"]
            node.title.setPlainText(node.title._plain)
            node._audio_path = cmd["old_path"] if undo else cmd["new_path"]
            node._fit_to_text()
            node.update()

        elif t == "doc_node_edit":
            node = cmd["node"]
            node.title._plain = cmd["old_name"] if undo else cmd["new_name"]
            node.title.setPlainText(node.title._plain)
            node._doc_path = cmd["old_path"] if undo else cmd["new_path"]
            node._fit_to_text()
            node.update()

        elif t == "node_orientation":
            cmd["node"]._orientation = cmd["old"] if undo else cmd["new"]
            cmd["node"]._apply_orientation()
            cmd["node"].update()

        elif t == "dot_color":
            cmd["dot"]._color = cmd["old"] if undo else cmd["new"]
            cmd["dot"].update()

        elif t == "dot_orientation":
            cmd["dot"]._orientation = cmd["old"] if undo else cmd["new"]
            cmd["dot"]._apply_orientation()
            cmd["dot"].update()

        elif t == "backdrop_color":
            cmd["item"]._color = cmd["old"] if undo else cmd["new"]
            cmd["item"].update()

        elif t == "backdrop_font_size":
            cmd["item"]._font_size = cmd["old"] if undo else cmd["new"]
            cmd["item"].update()

        elif t == "backdrop_font_color":
            cmd["item"]._font_color = cmd["old"] if undo else cmd["new"]
            cmd["item"].update()

        elif t == "backdrop_label":
            val = cmd["old"] if undo else cmd["new"]
            if isinstance(val, tuple):
                if len(val) == 3:
                    cmd["item"]._name, cmd["item"]._text, cmd["item"]._font_size = val
                else:
                    cmd["item"]._name, cmd["item"]._text = val
            else:
                cmd["item"]._name = val  # backwards compat
            cmd["item"].update()

        elif t == "sticky_color":
            cmd["item"]._color = cmd["old"] if undo else cmd["new"]
            cmd["item"].update()

        elif t == "sticky_font_size":
            cmd["item"]._font_size = cmd["old"] if undo else cmd["new"]
            cmd["item"].update()

        elif t == "sticky_font_color":
            cmd["item"]._font_color = cmd["old"] if undo else cmd["new"]
            cmd["item"].update()

        elif t == "sticky_text":
            val = cmd["old"] if undo else cmd["new"]
            if isinstance(val, tuple):
                if len(val) == 3:
                    cmd["item"]._name, cmd["item"]._text, cmd["item"]._font_size = val
                else:
                    cmd["item"]._name, cmd["item"]._text = val
            else:
                cmd["item"]._text = val  # backwards compat with old saves
            cmd["item"].update()

        elif t == "node_html":
            html = cmd["old"] if undo else cmd["new"]
            cmd["node"].title._html = html
            cmd["node"].title._plain = cmd["old_plain"] if undo else cmd["new_plain"]
            cmd["node"].title.setPlainText(cmd["node"].title._plain)
            cmd["node"]._font_size = cmd["old_fs"] if undo else cmd["new_fs"]
            cmd["node"].title.set_font_size(cmd["node"]._font_size)
            cmd["node"].update()

        elif t == "move":
            item = cmd["item"]
            item.setPos(cmd["old_pos"] if undo else cmd["new_pos"])

        elif t == "resize":
            item = cmd["item"]
            if undo:
                old_sz = cmd["old_size"]
                item.width, item.height = old_sz.width(), old_sz.height()
                item.setPos(cmd["old_pos"])
            else:
                new_sz = cmd["new_size"]
                item.width, item.height = new_sz.width(), new_sz.height()
                item.setPos(cmd["new_pos"])
            item.prepareGeometryChange()
            item._reposition_handles()
            item.update()

        elif t == "node_name":
            node = cmd["node"]
            name = cmd["old"] if undo else cmd["new"]
            node.title._plain = name
            node.title.setPlainText(name)
            node._fit_to_text()
            node.update()

        elif t == "add_stroke":
            if undo:
                self.removeItem(cmd["stroke"])
            else:
                self.addItem(cmd["stroke"])

        elif t == "del_stroke":
            if undo:
                self.addItem(cmd["stroke"])
            else:
                self.removeItem(cmd["stroke"])

        elif t == "clear_strokes":
            if undo:
                for s in cmd["strokes"]:
                    self.addItem(s)
            else:
                for s in cmd["strokes"]:
                    self.removeItem(s)

    # ── Selection Helpers ─────────────────────────────────

    def selected_nodes(self):
        return [i for i in self.selectedItems()
                if isinstance(i, (Node, Dot))]

    def selected_connections(self):
        return [i for i in self.selectedItems()
                if isinstance(i, ConnectionLine)]

    # ── Copy / Cut / Paste ────────────────────────────────

    def copy(self):
        from config import CLIPBOARD
        CLIPBOARD.clear()
        selected = list(self.selectedItems())
        if not selected:
            return

        node_map = {}
        nodes_data = []
        for item in selected:
            if isinstance(item, (Node, Dot)):
                node_map[id(item)] = item
                entry = {
                    "id": id(item),
                    "type": ("paint_node" if isinstance(item, PaintNode)
                             else "doc_node" if isinstance(item, DocumentNode)
                             else "audio_node" if isinstance(item, AudioNode)
                             else "movie_node" if isinstance(item, MovieNode)
                             else "image_node" if isinstance(item, ImageNode)
                             else "node" if isinstance(item, Node) else "dot"),
                    "x": item.scenePos().x(), "y": item.scenePos().y(),
                }
                if isinstance(item, PaintNode):
                    snap = item.snapshot()
                    snap["id"] = id(item)
                    entry = snap
                elif isinstance(item, DocumentNode):
                    entry.update({
                        "name": item.title._plain,
                        "shape": item._shape,
                        "color": item._color.name(QColor.NameFormat.HexArgb),
                    "color_locked": getattr(item, "_color_locked", False),
                        "font_size": item._font_size,
                        "font_color": item._font_color.name(QColor.NameFormat.HexArgb),
                        "orientation": item._orientation,
                        "doc_path": item._doc_path,
                    })
                elif isinstance(item, AudioNode):
                    entry.update({
                        "name": item.title._plain,
                        "shape": item._shape,
                        "color": item._color.name(QColor.NameFormat.HexArgb),
                    "color_locked": getattr(item, "_color_locked", False),
                        "font_size": item._font_size,
                        "font_color": item._font_color.name(QColor.NameFormat.HexArgb),
                        "orientation": item._orientation,
                        "audio_path": item._audio_path,
                    })
                elif isinstance(item, MovieNode):
                    entry.update({
                        "name": item.title._plain,
                        "shape": item._shape,
                        "color": item._color.name(QColor.NameFormat.HexArgb),
                    "color_locked": getattr(item, "_color_locked", False),
                        "font_size": item._font_size,
                        "font_color": item._font_color.name(QColor.NameFormat.HexArgb),
                        "orientation": item._orientation,
                        "movie_path": item._movie_path,
                    })
                elif isinstance(item, ImageNode):
                    entry.update({
                        "name": item.title._plain,
                        "shape": item._shape,
                        "color": item._color.name(QColor.NameFormat.HexArgb),
                    "color_locked": getattr(item, "_color_locked", False),
                        "font_size": item._font_size,
                        "font_color": item._font_color.name(QColor.NameFormat.HexArgb),
                        "orientation": item._orientation,
                        "image_path": item._image_path,
                    })
                elif isinstance(item, Node):
                    entry.update({
                        "name": item.title._plain,
                        "shape": item._shape,
                        "color": item._color.name(QColor.NameFormat.HexArgb),
                    "color_locked": getattr(item, "_color_locked", False),
                        "font_size": item._font_size,
                        "font_color": item._font_color.name(QColor.NameFormat.HexArgb),
                        "html": item.title._html,
                        "orientation": item._orientation,
                    })
                else:  # Dot
                    entry.update({
                        "color": item._color.name(QColor.NameFormat.HexArgb),
                    "color_locked": getattr(item, "_color_locked", False),
                        "orientation": item._orientation,
                    })
                nodes_data.append(entry)

        # Preserve connections
        conns_data = []
        seen_conns = set()
        for item in self.items():
            if isinstance(item, ConnectionLine):
                a_owner = id(item.a.parent_node)
                b_owner = id(item.b.parent_node)
                a_in_sel = a_owner in node_map
                b_in_sel = b_owner in node_map
                if not (a_in_sel or b_in_sel):
                    continue
                key = (a_owner, b_owner, item.a.is_input)
                if key in seen_conns:
                    continue
                seen_conns.add(key)
                a_is_in = item.a.is_input
                conns_data.append({
                    "a_node_id": a_owner,
                    "b_node_id": b_owner,
                    "a_is_in": a_is_in,
                    "a_in_sel": a_in_sel,
                    "b_in_sel": b_in_sel,
                    "curve_type": item.curve_type,
                    "color": item._line_color.name(QColor.NameFormat.HexArgb),
                    "line_style": item._line_style,
                    "thickness": item._thickness,
                    "color_locked":     item._color_locked,
                    "style_locked":     item._style_locked,
                    "thickness_locked": item._thickness_locked,
                })

        extras = []
        for item in selected:
            if isinstance(item, Backdrop):
                extras.append({
                    "type": "backdrop",
                    "x": item.scenePos().x(), "y": item.scenePos().y(),
                    "w": item.width, "h": item.height,
                    "color": item._color.name(QColor.NameFormat.HexArgb),
                    "color_locked": getattr(item, "_color_locked", False),
                    "font_color": item._font_color.name(QColor.NameFormat.HexArgb),
                    "name": item._name,
                    "text": item._text,
                    "font_size": item._font_size,
                })
            elif isinstance(item, StickyNote):
                extras.append({
                    "type": "sticky",
                    "x": item.scenePos().x(), "y": item.scenePos().y(),
                    "w": item.width, "h": item.height,
                    "color": item._color.name(QColor.NameFormat.HexArgb),
                    "color_locked": getattr(item, "_color_locked", False),
                    "font_color": item._font_color.name(QColor.NameFormat.HexArgb),
                    "name": item._name,
                    "text": item._text,
                    "font_size": item._font_size,
                })

        CLIPBOARD.append({
            "nodes": nodes_data,
            "conns": conns_data,
            "extras": extras,
        })

    def cut(self):
        self.copy()
        for item in list(self.selectedItems()):
            self._delete_item(item)

    def paste(self, pos):
        from config import CLIPBOARD
        if not CLIPBOARD:
            return
        data = CLIPBOARD[-1]

        all_x = [nd["x"] for nd in data.get("nodes", [])] + \
                [ex["x"] for ex in data.get("extras", [])]
        all_y = [nd["y"] for nd in data.get("nodes", [])] + \
                [ex["y"] for ex in data.get("extras", [])]

        if all_x:
            cx = (min(all_x) + max(all_x)) / 2
            cy = (min(all_y) + max(all_y)) / 2
        else:
            cx, cy = pos.x(), pos.y()
        
        PASTE_STEP = 30
        count = data.get("_paste_count", 0)
        data["_paste_count"] = count + 1
        ox = pos.x() - cx + count * PASTE_STEP
        oy = pos.y() - cy + count * PASTE_STEP

        id_map = {}

        for nd in data.get("nodes", []):
            t = nd["type"]
            nx = nd["x"] + ox
            ny = nd["y"] + oy
            if t == "paint_node":
                n = PaintNode(nx, ny, self._view, nd.get("name", "Paint"))
                n.restore_snapshot(nd)
                n.setPos(nx, ny)
                self.addItem(n)
                id_map[nd["id"]] = n
                self._push_undo({"type": "add_node", "node": n})
            elif t == "doc_node":
                n = DocumentNode(nx, ny, self._view, nd.get("name", "Document"))
                n._shape = nd.get("shape", "rectangle")
                n._color = QColor(nd.get("color", "#2a2a2a")); n._color_locked = nd.get("color_locked", False)
                n._font_size = nd.get("font_size", 22)
                n._font_color = QColor(nd.get("font_color", "#ffffff"))
                n._orientation = nd.get("orientation", "left-right")
                n._doc_path = nd.get("doc_path", "")
                n.title.set_font_size(n._font_size)
                n.title.set_font_color(n._font_color)
                n._apply_orientation()
                n._fit_to_text()
                n._settings_locked = True
                self.addItem(n)
                id_map[nd["id"]] = n
                self._push_undo({"type": "add_node", "node": n})
            elif t == "audio_node":
                n = AudioNode(nx, ny, self._view, nd.get("name", "Audio"))
                n._shape = nd.get("shape", "rectangle")
                n._color = QColor(nd.get("color", "#2a2a2a")); n._color_locked = nd.get("color_locked", False)
                n._font_size = nd.get("font_size", 22)
                n._font_color = QColor(nd.get("font_color", "#ffffff"))
                n._orientation = nd.get("orientation", "left-right")
                n._audio_path = nd.get("audio_path", "")
                n.title.set_font_size(n._font_size)
                n.title.set_font_color(n._font_color)
                n._apply_orientation()
                n._fit_to_text()
                n._settings_locked = True
                self.addItem(n)
                id_map[nd["id"]] = n
                self._push_undo({"type": "add_node", "node": n})
            elif t == "movie_node":
                n = MovieNode(nx, ny, self._view, nd.get("name", "Movie"))
                n._shape = nd.get("shape", "rectangle")
                n._color = QColor(nd.get("color", "#2a2a2a")); n._color_locked = nd.get("color_locked", False)
                n._font_size = nd.get("font_size", 22)
                n._font_color = QColor(nd.get("font_color", "#ffffff"))
                n._orientation = nd.get("orientation", "left-right")
                n._movie_path = nd.get("movie_path", "")
                n.title.set_font_size(n._font_size)
                n.title.set_font_color(n._font_color)
                n._apply_orientation()
                n._fit_to_text()
                n._settings_locked = True
                self.addItem(n)
                id_map[nd["id"]] = n
                self._push_undo({"type": "add_node", "node": n})
            elif t == "image_node":
                n = ImageNode(nx, ny, self._view, nd.get("name", "Image"))
                n._shape = nd.get("shape", "rectangle")
                n._color = QColor(nd.get("color", "#2a2a2a")); n._color_locked = nd.get("color_locked", False)
                n._font_size = nd.get("font_size", 22)
                n._font_color = QColor(nd.get("font_color", "#ffffff"))
                n._orientation = nd.get("orientation", "left-right")
                n._image_path = nd.get("image_path", "")
                n.title.set_font_size(n._font_size)
                n.title.set_font_color(n._font_color)
                n._apply_orientation()
                n._load_pixmap()
                n._fit_to_text()
                n._settings_locked = True
                self.addItem(n)
                id_map[nd["id"]] = n
                self._push_undo({"type": "add_node", "node": n})
            elif t == "node":
                n = Node(nx, ny, self._view, nd.get("name", "Name"))
                n._shape = nd.get("shape", "rectangle")
                n._color = QColor(nd.get("color", "#2a2a2a")); n._color_locked = nd.get("color_locked", False)
                n._font_size = nd.get("font_size", 22)
                n._font_color = QColor(nd.get("font_color", "#ffffff"))
                n._orientation = nd.get("orientation", "left-right")
                n.title.set_font_size(n._font_size)
                n.title.set_font_color(n._font_color)
                n._apply_orientation()
                html = nd.get("html", "")
                if html:
                    n.title._html = html
                    n.title.setPlainText(n.title._plain)
                n._fit_to_text()
                n._settings_locked = True
                self.addItem(n)
                id_map[nd["id"]] = n
                self._push_undo({"type": "add_node", "node": n})
            elif t == "dot":
                d = Dot(nx, ny, self._view)
                d._color = QColor(nd.get("color", "#2a2a2a")); d._color_locked = nd.get("color_locked", False)
                d._orientation = nd.get("orientation", "left-right")
                d._apply_orientation()
                self.addItem(d)
                id_map[nd["id"]] = d
                self._push_undo({"type": "add_node", "node": d})

        for ex in data.get("extras", []):
            t = ex["type"]
            ex_x = ex["x"] + ox
            ex_y = ex["y"] + oy
            if t == "backdrop":
                b = Backdrop(ex_x, ex_y, self._view)
                b.width = ex.get("w", 600)
                b.height = ex.get("h", 400)
                b._color = QColor(ex.get("color", "#3c3c50")); b._color_locked = ex.get("color_locked", False)
                b._font_color = QColor(ex.get("font_color", "#ffffff"))
                b._name = ex.get("name", "Backdrop")
                b._text = ex.get("text", "")
                b._font_size = ex.get("font_size", 80)
                b._reposition_handles()
                self.addItem(b)
                self._push_undo({"type": "add_node", "node": b})
            elif t == "sticky":
                s = StickyNote(ex_x, ex_y, self._view)
                s.width = ex.get("w", 400)
                s.height = ex.get("h", 300)
                s._color = QColor(ex.get("color", "#c7ba5f")); s._color_locked = ex.get("color_locked", False)
                s._font_color = QColor(ex.get("font_color", "#000000"))
                s._name = ex.get("name", "Note")
                s._text = ex.get("text", "")
                s._font_size = ex.get("font_size", 40)
                s._reposition_handles()
                self.addItem(s)
                self._push_undo({"type": "add_node", "node": s})

        # Restore connections
        for cd in data.get("conns", []):
            a_item = id_map.get(cd["a_node_id"])
            b_item = id_map.get(cd["b_node_id"])
            a_in_sel = cd.get("a_in_sel", True)
            b_in_sel = cd.get("b_in_sel", True)

            a_is_in = cd.get("a_is_in", False)
            if a_item:
                a_sock = getattr(a_item, "in_socket" if a_is_in else "out_socket", None)
            else:
                a_sock = self._find_socket_by_id(cd["a_node_id"], a_is_in)
            if b_item:
                b_sock = getattr(b_item, "in_socket" if not a_is_in else "out_socket", None)
            else:
                b_sock = self._find_socket_by_id(cd["b_node_id"], not a_is_in)

            if a_is_in:
                out_sock, in_sock = b_sock, a_sock
            else:
                out_sock, in_sock = a_sock, b_sock

            if out_sock and in_sock:
                conn = ConnectionLine(out_sock, in_sock)
                conn.curve_type        = cd.get("curve_type", ConnectionLine.CURVE_BEZIER)
                conn._line_color       = QColor(cd.get("color", "#ffffff"))
                conn._line_style       = cd.get("line_style", ConnectionLine.LINE_STYLE_SOLID)
                conn._thickness        = cd.get("thickness", conn._thickness)
                conn._color_locked     = cd.get("color_locked", False)
                conn._style_locked     = cd.get("style_locked", False)
                conn._thickness_locked = cd.get("thickness_locked", False)
                self.addItem(conn)
                out_sock.connections.append(conn)
                in_sock.connections.append(conn)
                self._push_undo({"type": "add_conn", "conn": conn})

    def _find_socket_by_id(self, node_id, is_input):
        for item in self.items():
            if isinstance(item, (Node, Dot)) and id(item) == node_id:
                return item.in_socket if is_input else item.out_socket
        return None

    def _non_overlapping(self, x, y, w, h, step=20, max_tries=50):
        for _ in range(max_tries):
            test = QRectF(x, y, w, h)
            overlap = False
            for item in self.items(test):
                if isinstance(item, (Node, Dot, StickyNote, Backdrop)):
                    overlap = True
                    break
            if not overlap:
                return x, y
            x += step
            y += step
        return x, y

    # ── Delete ────────────────────────────────────────────

    def delete_selected(self):
        for conn in self.selected_connections():
            conn.disconnect_from_sockets()
            self.removeItem(conn)
            self._push_undo({"type": "del_conn", "conn": conn,
                              "a": conn.a, "b": conn.b})
        for item in list(self.selectedItems()):
            if not isinstance(item, ConnectionLine):
                self._delete_item(item)
        if self._view:
            self._view._check_logo_fade()

    def _delete_item(self, item):
        if isinstance(item, ConnectionLine):
            item.disconnect_from_sockets()
            self.removeItem(item)
            self._push_undo({"type": "del_conn", "conn": item,
                              "a": item.a, "b": item.b})
        elif isinstance(item, Dot):
            self._delete_dot(item)
        elif isinstance(item, Node):
            self._delete_node(item)
        elif isinstance(item, (Backdrop, StickyNote)):
            if isinstance(item, Backdrop) and item._pinned_children:
                for child in list(item._pinned_children):
                    scene_pos = child.scenePos()
                    child.setParentItem(None)
                    child.setPos(scene_pos)
                item._pinned_children.clear()
            self.removeItem(item)
            self._push_undo({"type": "del_node", "node": item, "conns": []})

    def _delete_node(self, node):
        """Delete a node; if exactly one in-connection and one out-connection, merge them."""
        if hasattr(node, '_inline_player') and node._inline_player:
            node.close_inline_player()
        if hasattr(node, '_inline_viewer') and node._inline_viewer:
            node.close_inline_viewer()
        if hasattr(node, '_inline_text_viewer') and node._inline_text_viewer:
            node.close_inline_text_viewer()
        in_c = list(node.in_socket.connections)
        out_c = list(node.out_socket.connections)

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
                self.removeItem(c)
            self.removeItem(node)
            self.addItem(merged)
            merged.a.connections.append(merged)
            merged.b.connections.append(merged)
            self._push_undo({"type": "join_curves",
                               "dot": node,
                               "c1": c1, "c2": c2, "merged": merged})
        else:
            conns = []
            for sock in (node.in_socket, node.out_socket):
                for conn in list(sock.connections):
                    conn.disconnect_from_sockets()
                    self.removeItem(conn)
                    conns.append(conn)
            self.removeItem(node)
            self._push_undo({"type": "del_node", "node": node, "conns": conns})

    def _delete_dot(self, dot):
        in_c = list(dot.in_socket.connections)
        out_c = list(dot.out_socket.connections)
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
                self.removeItem(c)
            self.removeItem(dot)
            self.addItem(merged)
            merged.a.connections.append(merged)
            merged.b.connections.append(merged)
            self._push_undo({"type": "join_curves", "dot": dot,
                              "c1": c1, "c2": c2, "merged": merged})
        else:
            conns = []
            for sock in (dot.in_socket, dot.out_socket):
                for conn in list(sock.connections):
                    conn.disconnect_from_sockets()
                    self.removeItem(conn)
                    conns.append(conn)
            self.removeItem(dot)
            self._push_undo({"type": "del_node", "node": dot, "conns": conns})

    # ── Serialization ─────────────────────────────────────

    def to_dict(self):
        nodes, conns = [], []
        id_map = {}
        for item in self.items():
            if isinstance(item, PaintNode):
                nid = id(item)
                id_map[id(item.in_socket)] = f"{nid}_in"
                id_map[id(item.out_socket)] = f"{nid}_out"
                snap = item.snapshot()
                snap["id"] = nid
                nodes.append(snap)
            elif isinstance(item, DocumentNode):
                nid = id(item)
                id_map[id(item.in_socket)] = f"{nid}_in"
                id_map[id(item.out_socket)] = f"{nid}_out"
                nodes.append({
                    "id": nid, "type": "doc_node",
                    "name": item.title._plain,
                    "x": item.scenePos().x(), "y": item.scenePos().y(),
                    "shape": item._shape,
                    "color": item._color.name(QColor.NameFormat.HexArgb),
                    "color_locked": getattr(item, "_color_locked", False),
                    "font_size": item._font_size,
                    "font_color": item._font_color.name(QColor.NameFormat.HexArgb),
                    "orientation": item._orientation,
                    "doc_path": item._doc_path,
                })
            elif isinstance(item, AudioNode):
                nid = id(item)
                id_map[id(item.in_socket)] = f"{nid}_in"
                id_map[id(item.out_socket)] = f"{nid}_out"
                nodes.append({
                    "id": nid, "type": "audio_node",
                    "name": item.title._plain,
                    "x": item.scenePos().x(), "y": item.scenePos().y(),
                    "shape": item._shape,
                    "color": item._color.name(QColor.NameFormat.HexArgb),
                    "color_locked": getattr(item, "_color_locked", False),
                    "font_size": item._font_size,
                    "font_color": item._font_color.name(QColor.NameFormat.HexArgb),
                    "orientation": item._orientation,
                    "audio_path": item._audio_path,
                })
            elif isinstance(item, MovieNode):
                nid = id(item)
                id_map[id(item.in_socket)] = f"{nid}_in"
                id_map[id(item.out_socket)] = f"{nid}_out"
                nodes.append({
                    "id": nid, "type": "movie_node",
                    "name": item.title._plain,
                    "x": item.scenePos().x(), "y": item.scenePos().y(),
                    "shape": item._shape,
                    "color": item._color.name(QColor.NameFormat.HexArgb),
                    "color_locked": getattr(item, "_color_locked", False),
                    "font_size": item._font_size,
                    "font_color": item._font_color.name(QColor.NameFormat.HexArgb),
                    "orientation": item._orientation,
                    "movie_path": item._movie_path,
                })
            elif isinstance(item, ImageNode):
                nid = id(item)
                id_map[id(item.in_socket)] = f"{nid}_in"
                id_map[id(item.out_socket)] = f"{nid}_out"
                nodes.append({
                    "id": nid, "type": "image_node",
                    "name": item.title._plain,
                    "x": item.scenePos().x(), "y": item.scenePos().y(),
                    "shape": item._shape,
                    "color": item._color.name(QColor.NameFormat.HexArgb),
                    "color_locked": getattr(item, "_color_locked", False),
                    "font_size": item._font_size,
                    "font_color": item._font_color.name(QColor.NameFormat.HexArgb),
                    "orientation": item._orientation,
                    "image_path": item._image_path,
                })
            elif isinstance(item, Node):
                nid = id(item)
                id_map[id(item.in_socket)] = f"{nid}_in"
                id_map[id(item.out_socket)] = f"{nid}_out"
                nodes.append({
                    "id": nid, "type": "node",
                    "name": item.title._plain,
                    "x": item.scenePos().x(), "y": item.scenePos().y(),
                    "shape": item._shape,
                    "color": item._color.name(QColor.NameFormat.HexArgb),
                    "color_locked": getattr(item, "_color_locked", False),
                    "font_size": item._font_size,
                    "font_color": item._font_color.name(QColor.NameFormat.HexArgb),
                    "html": item.title._html,
                    "orientation": item._orientation,
                })
            elif isinstance(item, Dot):
                nid = id(item)
                id_map[id(item.in_socket)] = f"{nid}_in"
                id_map[id(item.out_socket)] = f"{nid}_out"
                nodes.append({
                    "id": nid, "type": "dot",
                    "x": item.scenePos().x(), "y": item.scenePos().y(),
                    "color": item._color.name(QColor.NameFormat.HexArgb),
                    "color_locked": getattr(item, "_color_locked", False),
                    "orientation": item._orientation,
                })
            elif isinstance(item, Backdrop):
                nodes.append({
                    "id": id(item),
                    "type": "backdrop",
                    "x": item.scenePos().x(), "y": item.scenePos().y(),
                    "w": item.width, "h": item.height,
                    "color": item._color.name(QColor.NameFormat.HexArgb),
                    "color_locked": getattr(item, "_color_locked", False),
                    "font_color": item._font_color.name(QColor.NameFormat.HexArgb),
                    "name": item._name,
                    "text": item._text,
                    "font_size": item._font_size,
                })
            elif isinstance(item, StickyNote):
                nodes.append({
                    "id": id(item),
                    "type": "sticky",
                    "x": item.scenePos().x(), "y": item.scenePos().y(),
                    "w": item.width, "h": item.height,
                    "color": item._color.name(QColor.NameFormat.HexArgb),
                    "color_locked": getattr(item, "_color_locked", False),
                    "font_color": item._font_color.name(QColor.NameFormat.HexArgb),
                    "name": item._name,
                    "text": item._text,
                    "font_size": item._font_size,
                })
        
        for item in self.items():
            if isinstance(item, ConnectionLine):
                a_id = id_map.get(id(item.a))
                b_id = id_map.get(id(item.b))
                if a_id and b_id:
                    conns.append({
                        "a": a_id, "b": b_id,
                        "curve_type": item.curve_type,
                        "color": item._line_color.name(QColor.NameFormat.HexArgb),
                        "line_style": item._line_style,
                        "color_locked":     item._color_locked,
                        "style_locked":     item._style_locked,
                        "thickness_locked": item._thickness_locked,
                        "thickness": item._thickness,
                    })
        return {"nodes": nodes, "connections": conns, "strokes": self._strokes_to_list()}

    def _strokes_to_list(self):
        """Serialise all CanvasStroke items to a list of dicts."""
        from paint_on_canvas import CanvasStroke
        out = []
        try:
            for item in self.items():
                if isinstance(item, CanvasStroke):
                    c = item._color
                    out.append({
                        "color":     [c.red(), c.green(), c.blue(), c.alpha()],
                        "thickness": item._thickness,
                        "style":     item._style,
                        "points":    [[p.x(), p.y()] for p in item._points],
                    })
        except Exception as e:
            print(f"[theFlow] _strokes_to_list error: {e}")
        return out

    def _strokes_from_list(self, strokes_data):
        """Deserialise and add CanvasStroke items from a list of dicts."""
        from paint_on_canvas import CanvasStroke
        from PyQt6.QtCore import QPointF as _QPointF
        for sd in strokes_data:
            # Color stored as [r,g,b,a] list or legacy hex string
            raw_color = sd.get("color", [255, 140, 0, 255])
            if isinstance(raw_color, list):
                c = QColor(*raw_color)
            else:
                c = QColor(raw_color)
            s = CanvasStroke(
                color=c,
                thickness=sd.get("thickness", 6),
                style=sd.get("style", "solid"),
            )
            for xy in sd.get("points", []):
                s._points.append(_QPointF(xy[0], xy[1]))
            s.finalise()
            self.addItem(s)

    def from_dict(self, data, view):
        self.clear()
        self._undo_stack.clear()
        self._redo_stack.clear()
        socket_map = {}
        
        for nd in data.get("nodes", []):
            t = nd.get("type", "node")
            if t == "paint_node":
                n = PaintNode(nd["x"], nd["y"], view, nd.get("name", "Paint"))
                n.restore_snapshot(nd)
                n._settings_locked = True
                self.addItem(n)
                socket_map[f'{nd["id"]}_in'] = n.in_socket
                socket_map[f'{nd["id"]}_out'] = n.out_socket
            elif t == "doc_node":
                n = DocumentNode(nd["x"], nd["y"], view, nd.get("name", "Document"))
                n._shape = nd.get("shape", "rectangle")
                n._color = QColor(nd.get("color", "#2a2a2a")); n._color_locked = nd.get("color_locked", False)
                n._font_size = nd.get("font_size", 22)
                n._font_color = QColor(nd.get("font_color", "#ffffff"))
                n._orientation = nd.get("orientation", "left-right")
                n._doc_path = nd.get("doc_path", "")
                n.title.set_font_size(n._font_size)
                n.title.set_font_color(n._font_color)
                n._apply_orientation()
                n._fit_to_text()
                n._settings_locked = True
                self.addItem(n)
                socket_map[f'{nd["id"]}_in'] = n.in_socket
                socket_map[f'{nd["id"]}_out'] = n.out_socket
            elif t == "audio_node":
                n = AudioNode(nd["x"], nd["y"], view, nd.get("name", "Audio"))
                n._shape = nd.get("shape", "rectangle")
                n._color = QColor(nd.get("color", "#2a2a2a")); n._color_locked = nd.get("color_locked", False)
                n._font_size = nd.get("font_size", 22)
                n._font_color = QColor(nd.get("font_color", "#ffffff"))
                n._orientation = nd.get("orientation", "left-right")
                n._audio_path = nd.get("audio_path", "")
                n.title.set_font_size(n._font_size)
                n.title.set_font_color(n._font_color)
                n._apply_orientation()
                n._fit_to_text()
                n._settings_locked = True
                self.addItem(n)
                socket_map[f'{nd["id"]}_in'] = n.in_socket
                socket_map[f'{nd["id"]}_out'] = n.out_socket
            elif t == "movie_node":
                n = MovieNode(nd["x"], nd["y"], view, nd.get("name", "Movie"))
                n._shape = nd.get("shape", "rectangle")
                n._color = QColor(nd.get("color", "#2a2a2a")); n._color_locked = nd.get("color_locked", False)
                n._font_size = nd.get("font_size", 22)
                n._font_color = QColor(nd.get("font_color", "#ffffff"))
                n._orientation = nd.get("orientation", "left-right")
                n._movie_path = nd.get("movie_path", "")
                n.title.set_font_size(n._font_size)
                n.title.set_font_color(n._font_color)
                n._apply_orientation()
                n._fit_to_text()
                n._settings_locked = True
                self.addItem(n)
                socket_map[f'{nd["id"]}_in'] = n.in_socket
                socket_map[f'{nd["id"]}_out'] = n.out_socket
            elif t == "image_node":
                n = ImageNode(nd["x"], nd["y"], view, nd.get("name", "Image"))
                n._shape = nd.get("shape", "rectangle")
                n._color = QColor(nd.get("color", "#2a2a2a")); n._color_locked = nd.get("color_locked", False)
                n._font_size = nd.get("font_size", 22)
                n._font_color = QColor(nd.get("font_color", "#ffffff"))
                n._orientation = nd.get("orientation", "left-right")
                n._image_path = nd.get("image_path", "")
                n.title.set_font_size(n._font_size)
                n.title.set_font_color(n._font_color)
                n._apply_orientation()
                n._load_pixmap()
                n._fit_to_text()
                n._settings_locked = True
                self.addItem(n)
                socket_map[f'{nd["id"]}_in'] = n.in_socket
                socket_map[f'{nd["id"]}_out'] = n.out_socket
            elif t == "node":
                n = Node(nd["x"], nd["y"], view, nd.get("name", "Name"))
                n._shape = nd.get("shape", "rectangle")
                n._color = QColor(nd.get("color", "#2a2a2a")); n._color_locked = nd.get("color_locked", False)
                n._font_size = nd.get("font_size", 22)
                n._font_color = QColor(nd.get("font_color", "#ffffff"))
                n._orientation = nd.get("orientation", "left-right")
                n.title.set_font_size(n._font_size)
                n.title.set_font_color(n._font_color)
                n._apply_orientation()
                html = nd.get("html", "")
                if html:
                    n.title._html = html
                    n.title.setPlainText(n.title._plain)
                n._fit_to_text()
                n._settings_locked = True
                self.addItem(n)
                socket_map[f'{nd["id"]}_in'] = n.in_socket
                socket_map[f'{nd["id"]}_out'] = n.out_socket
            elif t == "dot":
                d = Dot(nd["x"], nd["y"], view)
                d._color = QColor(nd.get("color", "#2a2a2a")); d._color_locked = nd.get("color_locked", False)
                d._orientation = nd.get("orientation", "left-right")
                d._apply_orientation()
                self.addItem(d)
                socket_map[f'{nd["id"]}_in'] = d.in_socket
                socket_map[f'{nd["id"]}_out'] = d.out_socket
            elif t == "backdrop":
                b = Backdrop(nd["x"], nd["y"], view)
                b.width = nd.get("w", 600)
                b.height = nd.get("h", 400)
                b._color = QColor(nd.get("color", "#3c3c50")); b._color_locked = nd.get("color_locked", False)
                b._font_color = QColor(nd.get("font_color", "#ffffff"))
                b._name = nd.get("name", "Backdrop")
                b._text = nd.get("text", "")
                b._font_size = nd.get("font_size", 80)
                b._reposition_handles()
                self.addItem(b)
            elif t == "sticky":
                s = StickyNote(nd["x"], nd["y"], view)
                s.width = nd.get("w", 400)
                s.height = nd.get("h", 300)
                s._color = QColor(nd.get("color", "#c7ba5f")); s._color_locked = nd.get("color_locked", False)
                s._font_color = QColor(nd.get("font_color", "#000000"))
                s._name = nd.get("name", "Note")
                s._text = nd.get("text", "")
                s._font_size = nd.get("font_size", 40)
                s._reposition_handles()
                self.addItem(s)
        
        for cd in data.get("connections", []):
            a = socket_map.get(cd["a"])
            b = socket_map.get(cd["b"])
            if a and b:
                conn = ConnectionLine(a, b)
                conn.curve_type        = cd.get("curve_type", ConnectionLine.CURVE_BEZIER)
                conn._line_color       = QColor(cd.get("color", "#ffffff"))
                conn._line_style       = cd.get("line_style", ConnectionLine.LINE_STYLE_SOLID)
                conn._thickness        = cd.get("thickness", conn._thickness)
                conn._color_locked     = cd.get("color_locked", False)
                conn._style_locked     = cd.get("style_locked", False)
                conn._thickness_locked = cd.get("thickness_locked", False)
                self.addItem(conn)
                a.connections.append(conn)
                b.connections.append(conn)
        
        self._strokes_from_list(data.get("strokes", []))
        self.reeval_backdrop_containment()

    def merge_from_dict(self, data, view):
        """Like from_dict but ADDITIVE — appends imported items without clearing the scene.

        Connections are restored only between nodes that are part of the import
        payload; existing scene connections are untouched.
        """
        socket_map = {}

        for nd in data.get("nodes", []):
            t = nd.get("type", "node")
            if t == "paint_node":
                n = PaintNode(nd["x"], nd["y"], view, nd.get("name", "Paint"))
                n.restore_snapshot(nd)
                n._settings_locked = True
                self.addItem(n)
                socket_map[f'{nd["id"]}_in']  = n.in_socket
                socket_map[f'{nd["id"]}_out'] = n.out_socket
            elif t == "doc_node":
                n = DocumentNode(nd["x"], nd["y"], view, nd.get("name", "Document"))
                n._shape = nd.get("shape", "rectangle")
                n._color = QColor(nd.get("color", "#2a2a2a")); n._color_locked = nd.get("color_locked", False)
                n._font_size = nd.get("font_size", 22)
                n._font_color = QColor(nd.get("font_color", "#ffffff"))
                n._orientation = nd.get("orientation", "left-right")
                n._doc_path = nd.get("doc_path", "")
                n.title.set_font_size(n._font_size)
                n.title.set_font_color(n._font_color)
                n._apply_orientation()
                n._fit_to_text()
                n._settings_locked = True
                self.addItem(n)
                socket_map[f'{nd["id"]}_in']  = n.in_socket
                socket_map[f'{nd["id"]}_out'] = n.out_socket
            elif t == "audio_node":
                n = AudioNode(nd["x"], nd["y"], view, nd.get("name", "Audio"))
                n._shape = nd.get("shape", "rectangle")
                n._color = QColor(nd.get("color", "#2a2a2a")); n._color_locked = nd.get("color_locked", False)
                n._font_size = nd.get("font_size", 22)
                n._font_color = QColor(nd.get("font_color", "#ffffff"))
                n._orientation = nd.get("orientation", "left-right")
                n._audio_path = nd.get("audio_path", "")
                n.title.set_font_size(n._font_size)
                n.title.set_font_color(n._font_color)
                n._apply_orientation()
                n._fit_to_text()
                n._settings_locked = True
                self.addItem(n)
                socket_map[f'{nd["id"]}_in']  = n.in_socket
                socket_map[f'{nd["id"]}_out'] = n.out_socket
            elif t == "movie_node":
                n = MovieNode(nd["x"], nd["y"], view, nd.get("name", "Movie"))
                n._shape = nd.get("shape", "rectangle")
                n._color = QColor(nd.get("color", "#2a2a2a")); n._color_locked = nd.get("color_locked", False)
                n._font_size = nd.get("font_size", 22)
                n._font_color = QColor(nd.get("font_color", "#ffffff"))
                n._orientation = nd.get("orientation", "left-right")
                n._movie_path = nd.get("movie_path", "")
                n.title.set_font_size(n._font_size)
                n.title.set_font_color(n._font_color)
                n._apply_orientation()
                n._fit_to_text()
                n._settings_locked = True
                self.addItem(n)
                socket_map[f'{nd["id"]}_in']  = n.in_socket
                socket_map[f'{nd["id"]}_out'] = n.out_socket
            elif t == "image_node":
                n = ImageNode(nd["x"], nd["y"], view, nd.get("name", "Image"))
                n._shape = nd.get("shape", "rectangle")
                n._color = QColor(nd.get("color", "#2a2a2a")); n._color_locked = nd.get("color_locked", False)
                n._font_size = nd.get("font_size", 22)
                n._font_color = QColor(nd.get("font_color", "#ffffff"))
                n._orientation = nd.get("orientation", "left-right")
                n._image_path = nd.get("image_path", "")
                n.title.set_font_size(n._font_size)
                n.title.set_font_color(n._font_color)
                n._apply_orientation()
                n._load_pixmap()
                n._fit_to_text()
                n._settings_locked = True
                self.addItem(n)
                socket_map[f'{nd["id"]}_in']  = n.in_socket
                socket_map[f'{nd["id"]}_out'] = n.out_socket
            elif t == "node":
                n = Node(nd["x"], nd["y"], view, nd.get("name", "Name"))
                n._shape = nd.get("shape", "rectangle")
                n._color = QColor(nd.get("color", "#2a2a2a")); n._color_locked = nd.get("color_locked", False)
                n._font_size = nd.get("font_size", 22)
                n._font_color = QColor(nd.get("font_color", "#ffffff"))
                n._orientation = nd.get("orientation", "left-right")
                n.title.set_font_size(n._font_size)
                n.title.set_font_color(n._font_color)
                n._apply_orientation()
                html = nd.get("html", "")
                if html:
                    n.title._html = html
                    n.title.setPlainText(n.title._plain)
                n._fit_to_text()
                n._settings_locked = True
                self.addItem(n)
                socket_map[f'{nd["id"]}_in']  = n.in_socket
                socket_map[f'{nd["id"]}_out'] = n.out_socket
            elif t == "dot":
                d = Dot(nd["x"], nd["y"], view)
                d._color = QColor(nd.get("color", "#2a2a2a")); d._color_locked = nd.get("color_locked", False)
                d._orientation = nd.get("orientation", "left-right")
                d._apply_orientation()
                self.addItem(d)
                socket_map[f'{nd["id"]}_in']  = d.in_socket
                socket_map[f'{nd["id"]}_out'] = d.out_socket
            elif t == "backdrop":
                b = Backdrop(nd["x"], nd["y"], view)
                b.width = nd.get("w", 600)
                b.height = nd.get("h", 400)
                b._color = QColor(nd.get("color", "#3c3c50")); b._color_locked = nd.get("color_locked", False)
                b._font_color = QColor(nd.get("font_color", "#ffffff"))
                b._name = nd.get("name", "Backdrop")
                b._text = nd.get("text", "")
                b._font_size = nd.get("font_size", 80)
                b._reposition_handles()
                self.addItem(b)
            elif t == "sticky":
                s = StickyNote(nd["x"], nd["y"], view)
                s.width = nd.get("w", 400)
                s.height = nd.get("h", 300)
                s._color = QColor(nd.get("color", "#c7ba5f")); s._color_locked = nd.get("color_locked", False)
                s._font_color = QColor(nd.get("font_color", "#000000"))
                s._name = nd.get("name", "Note")
                s._text = nd.get("text", "")
                s._font_size = nd.get("font_size", 40)
                s._reposition_handles()
                self.addItem(s)

        for cd in data.get("connections", []):
            a = socket_map.get(cd["a"])
            b = socket_map.get(cd["b"])
            if a and b:
                conn = ConnectionLine(a, b)
                conn.curve_type        = cd.get("curve_type", ConnectionLine.CURVE_BEZIER)
                conn._line_color       = QColor(cd.get("color", "#ffffff"))
                conn._line_style       = cd.get("line_style", ConnectionLine.LINE_STYLE_SOLID)
                conn._thickness        = cd.get("thickness", conn._thickness)
                conn._color_locked     = cd.get("color_locked", False)
                conn._style_locked     = cd.get("style_locked", False)
                conn._thickness_locked = cd.get("thickness_locked", False)
                self.addItem(conn)
                a.connections.append(conn)
                b.connections.append(conn)

        self._strokes_from_list(data.get("strokes", []))
        self.reeval_backdrop_containment()

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        has_items = any(
            isinstance(i, (Node, Dot, Backdrop, StickyNote))
            for i in self.items()
        )
        if not has_items:
            painter.save()
            painter.setPen(QColor(120, 120, 140, 180))
            painter.setFont(QFont("Arial", 18))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Create a node to start")
            painter.restore()

def _remove_sock(conn, sock):
    if conn in sock.connections:
        sock.connections.remove(conn)