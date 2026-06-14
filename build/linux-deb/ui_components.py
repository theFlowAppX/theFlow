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

# ui_components.py
# =========================================================
# UI COMPONENTS FOR THEFLOW!
# =========================================================

from PyQt6.QtWidgets import QMenu, QApplication
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QCursor

from utils import _menu_style


class TabCreationMenu(QMenu):
    """Plain QMenu opened with Tab, styled like the rest of the app."""

    ITEMS = [
        ("Audio Node",    "audio"),
        ("Document Node", "doc"),
        ("Image Node",    "image"),
        ("Movie Node",    "movie"),
        ("Paint Node",    "paint"),
        ("Text Node",     "text"),
        (None,            None),
        ("Dot",           "dot"),
        (None,            None),
        ("Backdrop",      "backdrop"),
        ("Sticky Note",   "sticky"),
    ]

    def __init__(self, view, scene_pos, global_pos):
        super().__init__(view)
        self._view      = view
        self._scene_pos = scene_pos

        self.setStyleSheet(_menu_style())

        for label, key in self.ITEMS:
            if label is None:
                self.addSeparator()
            else:
                action = self.addAction(label)
                action.setData(key)

        self.triggered.connect(self._on_action)
        self.exec(global_pos)

    def _on_action(self, action):
        key = action.data()
        if key is None:
            return
        pos = self._scene_pos
        v   = self._view

        dispatch = {
            "text":     v.create_node_at,
            "image":    v.create_image_node_at,
            "movie":    v.create_movie_node_at,
            "audio":    v.create_audio_node_at,
            "doc":      v.create_doc_node_at,
            "paint":    v.create_paint_node_at,
            "dot":      v.create_dot_at,
            "backdrop": v.create_backdrop_at,
            "sticky":   v.create_sticky_at,
        }
        if key in dispatch:
            dispatch[key](pos)
