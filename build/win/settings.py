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

# settings.py
# =========================================================
# SETTINGS DIALOG WITH PERSISTENCE
# =========================================================

import json
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout, QColorDialog, QComboBox, QSpinBox,
    QTabWidget, QWidget, QScrollArea, QFrame, QCheckBox
)
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtCore import Qt

from config import DARK, LIGHT, SETTINGS_FILE
from node import NODE_SHAPES, NODE_SHAPE_LABELS

# Default Values (Dark Theme Profile Blueprint Map)
DEFAULTS = {
    "theme": "dark",              
    "canvas_bg": "#232323",
    "menu_bg": "#2a2a2a",
    "menu_fg": "#ffffff",
    "node_color": DARK["node_bg"],
    "node_font_size": 22,
    "node_font_color": "#ffffff",
    "node_orientation": "left-right",
    "node_shape": "rectangle",
    "text_node_color": DARK["node_bg"],
    "text_node_font_color": "#ffffff",
    "text_node_font_size": 22,
    "text_node_orientation": "left-right",
    "text_node_shape": "rectangle",
    "image_node_color": DARK["node_bg"],
    "image_node_font_color": "#ffffff",
    "image_node_font_size": 22,
    "image_node_orientation": "left-right",
    "image_node_shape": "rectangle",
    "video_node_color": DARK["node_bg"],
    "video_node_font_color": "#ffffff",
    "video_node_font_size": 22,
    "video_node_orientation": "left-right",
    "video_node_shape": "rectangle",
    "audio_node_color": DARK["node_bg"],
    "audio_node_font_color": "#ffffff",
    "audio_node_font_size": 22,
    "audio_node_orientation": "left-right",
    "audio_node_shape": "rectangle",
    "doc_node_color": DARK["node_bg"],
    "doc_node_font_color": "#ffffff",
    "doc_node_font_size": 22,
    "doc_node_orientation": "left-right",
    "doc_node_shape": "rectangle",
    "paint_node_color": DARK["node_bg"],
    "paint_node_font_color": "#ffffff",
    "paint_node_font_size": 22,
    "paint_node_orientation": "left-right",
    "paint_node_shape": "rectangle",
    "dot_color": DARK["node_bg"],
    "dot_font_size": 22,
    "dot_font_color": "#ffffff",
    "dot_orientation": "left-right",
    "dot_shape": "circle",
    "sticky_color": "#e6d250",
    "sticky_font_size": 40,
    "sticky_font_color": "#281e00",
    "backdrop_color": "#3c3c50a0",
    "backdrop_font_size": 80,
    "backdrop_font_color": "#ffffff",
    "curve_color": "#ffffff",
    "curve_thickness": 3,
    "curve_style": "Solid",
    "curve_type": "Bezier",
    "socket_color": "#4a9eff",
    "socket_size": 10,
    "autosave": True,
    "annotation_color": "#FF8C00",
    "annotation_thickness": 6,
    "annotation_style": "solid"
}

# Default Values (Light Theme Profile Blueprint Map)
LIGHT_DEFAULTS = {
    "theme": "light",             
    "canvas_bg": "#9f9f9f",
    "menu_bg": "#e0e0e0",
    "menu_fg": "#1a1a1a",
    "node_color": "#d8d8d8",
    "node_font_size": 22,
    "node_font_color": "#333333",
    "node_orientation": "left-right",
    "node_shape": "rectangle",
    "text_node_color": "#d8d8d8",
    "text_node_font_color": "#333333",
    "text_node_font_size": 22,
    "text_node_orientation": "left-right",
    "text_node_shape": "rectangle",
    "image_node_color": "#d8d8d8",
    "image_node_font_color": "#333333",
    "image_node_font_size": 22,
    "image_node_orientation": "left-right",
    "image_node_shape": "rectangle",
    "video_node_color": "#d8d8d8",
    "video_node_font_color": "#333333",
    "video_node_font_size": 22,
    "video_node_orientation": "left-right",
    "video_node_shape": "rectangle",
    "audio_node_color": "#d8d8d8",
    "audio_node_font_color": "#333333",
    "audio_node_font_size": 22,
    "audio_node_orientation": "left-right",
    "audio_node_shape": "rectangle",
    "doc_node_color": "#d8d8d8",
    "doc_node_font_color": "#333333",
    "doc_node_font_size": 22,
    "doc_node_orientation": "left-right",
    "doc_node_shape": "rectangle",
    "paint_node_color": "#d8d8d8",
    "paint_node_font_color": "#333333",
    "paint_node_font_size": 22,
    "paint_node_orientation": "left-right",
    "paint_node_shape": "rectangle",
    "dot_color": "#d8d8d8",
    "dot_font_size": 22,
    "dot_font_color": "#333333",
    "dot_orientation": "left-right",
    "dot_shape": "circle",
    "sticky_color": "#fff9c4",
    "sticky_font_size": 40,
    "sticky_font_color": "#1a1a1a",
    "backdrop_color": "#3c3c500a",
    "backdrop_font_size": 80,
    "backdrop_font_color": "#1a1a1a",
    "curve_color": "#333333",
    "curve_thickness": 3,
    "curve_style": "Solid",
    "curve_type": "Bezier",
    "socket_color": "#0066cc",
    "socket_size": 10,
    "autosave": True,
    "annotation_color": "#379b32",
    "annotation_thickness": 6,
    "annotation_style": "solid"
}


class SettingsDialog(QDialog):

    def __init__(self, parent, scene):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Window)
        self.setWindowTitle("Settings")
        self.setMinimumSize(620, 680)

        # Fix sequence layout: Import and initialize self._MC first
        from utils import _MENU_COLORS as _MC
        self._MC = _MC

        bg = self._MC["bg"]; fg = self._MC["fg"]
        # Enforce buttons to stay visible and readable under all conditions
        self.setStyleSheet(f"""
            QDialog {{ background: {bg}; color: {fg}; }}
            QPushButton {{ color: {fg}; padding: 5px 10px; }}
        """)

        self.scene = scene
        self.parent_view = parent
        self._temp_settings = self.load_settings()

        # Build UI layout
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        _bg  = self._MC["bg"]
        _fg  = self._MC["fg"]
        _bdr = self._MC["border"]
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {_bdr}; }}
            QTabBar::tab {{ background:{_bdr}; color:{_fg}; padding:6px 14px; }}
            QTabBar::tab:selected {{ background:{_bg}; color:{_fg}; border-bottom: 2px solid #4a9eff; }}
        """)
        layout.addWidget(tabs)

        tabs.addTab(self._build_canvas_tab(),  "Canvas")
        tabs.addTab(self._build_nodes_tab(),   "Nodes")
        tabs.addTab(self._build_curves_tab(),  "Curves")
        tabs.addTab(self._build_sticky_tab(),  "Sticky Notes")
        tabs.addTab(self._build_backdrop_tab(), "Backdrops")
        tabs.addTab(self._build_annotation_tab(), "Annotations")

        action_layout = QHBoxLayout()
        btn_dark = QPushButton("Dark Theme")
        btn_dark.clicked.connect(lambda: self.apply_theme("dark"))
        action_layout.addWidget(btn_dark)

        btn_light = QPushButton("Light Theme")
        btn_light.clicked.connect(lambda: self.apply_theme("light"))
        action_layout.addWidget(btn_light)

        action_layout.addStretch()

        btn_reset_all = QPushButton("Reset All Defaults")
        btn_reset_all.clicked.connect(self.reset_all)
        action_layout.addWidget(btn_reset_all)

        btn_save = QPushButton("Save Settings")
        # Removed the green background-color style from here
        btn_save.clicked.connect(self.save_settings)
        action_layout.addWidget(btn_save)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        action_layout.addWidget(btn_close)

        layout.addLayout(action_layout)
        self._update_widgets()

    # =========================================================
    # UI TABS GENERATION BUILDERS
    # =========================================================

    def _build_canvas_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        form = QFormLayout()

        self.btn_c_bg = QPushButton()
        self.btn_c_bg.clicked.connect(lambda: self.pick("canvas_bg"))
        form.addRow("Canvas Background:", self.btn_c_bg)

        self.btn_m_bg = QPushButton()
        self.btn_m_bg.clicked.connect(lambda: self.pick("menu_bg"))
        form.addRow("Context Menu Background:", self.btn_m_bg)

        self.chk_autosave = QCheckBox("Autosave every 30 seconds (named files only)")
        self.chk_autosave.stateChanged.connect(
            lambda state: self.update("autosave", bool(state)))
        form.addRow("Autosave:", self.chk_autosave)

        # <-- The self.btn_m_fg row has been deleted from here -->

        layout.addLayout(form)
        layout.addStretch()
        # Removed "menu_fg" from the list below
        layout.addWidget(self._reset_btn("Canvas", ["canvas_bg", "menu_bg", "autosave"]))
        return w

    def _build_nodes_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        w = QWidget()
        scroll.setWidget(w)
        layout = QVBoxLayout(w)

        node_types = [
            ("Text Custom Node Layout",   "text_node"),
            ("Image Custom Node Layout",  "image_node"),
            ("Movie Custom Node Layout",  "video_node"),
            ("Audio Custom Node Layout",  "audio_node"),
            ("Document Custom Node Layout", "doc_node"),
            ("Paint Custom Node Layout",  "paint_node"),
            ("Dot Connection Anchor",     "dot")
        ]

        self.node_widgets = {}

        for title, key in node_types:
            box = QGroupBox(title)
            # Create a main layout for the group box to hold form items + the section reset button
            box_layout = QVBoxLayout(box)
            form = QFormLayout()

            btn_col = QPushButton()
            btn_col.clicked.connect(lambda checked, k=f"{key}_color": self.pick(k))
            form.addRow("Dot Color:" if key == "dot" else "Node Color:", btn_col)

            if key != "dot":
                spin_fs = QSpinBox()
                spin_fs.setRange(6, 100000)
                spin_fs.valueChanged.connect(lambda val, k=f"{key}_font_size": self.update(k, val))
                form.addRow("Font Title Size:", spin_fs)

                btn_fc = QPushButton()
                btn_fc.clicked.connect(lambda checked, k=f"{key}_font_color": self.pick(k))
                form.addRow("Font Color Style:", btn_fc)

            combo_or = QComboBox()
            combo_or.addItems(["left-right", "top-bottom", "right-left", "bottom-top"])
            combo_or.currentTextChanged.connect(lambda txt, k=f"{key}_orientation": self.update(k, txt))
            form.addRow("Sockets Orientation:", combo_or)

            combo_sh = None
            if key != "dot":
                combo_sh = QComboBox()
                for skey in NODE_SHAPES:
                    combo_sh.addItem(NODE_SHAPE_LABELS[skey], skey)
                combo_sh.currentIndexChanged.connect(lambda idx, c=combo_sh, k=f"{key}_shape": self.update(k, c.currentData()))
                form.addRow("Geometrical Shape:", combo_sh)

            box_layout.addLayout(form)

            # Gather keys strictly belonging to this individual node type section
            section_keys = [f"{key}_color", f"{key}_font_size", f"{key}_font_color", f"{key}_orientation", f"{key}_shape"]
            
            # Create and add the localized section reset button directly inside the layout block
            btn_section_reset = QPushButton("Reset Section Defaults")
            btn_section_reset.clicked.connect(lambda checked, ks=section_keys: self.reset_section(ks))
            box_layout.addWidget(btn_section_reset)

            self.node_widgets[key] = {
                "color": btn_col,
                "font_size": spin_fs if key != "dot" else None,
                "font_color": btn_fc if key != "dot" else None,
                "orientation": combo_or, "shape": combo_sh
            }
            layout.addWidget(box)

        layout.addStretch()
        # The giant global "Reset Nodes Defaults" button at the bottom has been removed
        return scroll

    def _build_curves_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        form = QFormLayout()

        self.btn_cur_col = QPushButton()
        self.btn_cur_col.clicked.connect(lambda: self.pick("curve_color"))
        form.addRow("Connection Line Color:", self.btn_cur_col)

        self.spin_cur_th = QSpinBox()
        self.spin_cur_th.setRange(1, 20)
        self.spin_cur_th.valueChanged.connect(lambda val: self.update("curve_thickness", val))
        form.addRow("Line Profile Thickness:", self.spin_cur_th)

        self.combo_cur_st = QComboBox()
        self.combo_cur_st.addItems(["Solid", "Dash", "Dot"])
        self.combo_cur_st.currentTextChanged.connect(lambda txt: self.update("curve_style", txt))
        form.addRow("Line Visual Style Pattern:", self.combo_cur_st)

        self.combo_cur_ty = QComboBox()
        self.combo_cur_ty.addItems(["Bezier", "Straight", "Step"])
        self.combo_cur_ty.currentTextChanged.connect(lambda txt: self.update("curve_type", txt))
        form.addRow("Link Calculus Routing Type:", self.combo_cur_ty)

        self.btn_sock_col = QPushButton()
        self.btn_sock_col.clicked.connect(lambda: self.pick("socket_color"))
        form.addRow("Socket Interface Terminal Color:", self.btn_sock_col)

        self.spin_sock_sz = QSpinBox()
        self.spin_sock_sz.setRange(4, 30)
        self.spin_sock_sz.valueChanged.connect(lambda val: self.update("socket_size", val))
        form.addRow("Socket Interface Terminal Size:", self.spin_sock_sz)

        layout.addLayout(form)
        layout.addStretch()
        layout.addWidget(self._reset_btn("Curves", ["curve_color", "curve_thickness", "curve_style", "curve_type", "socket_color", "socket_size"]))
        return w

    def _build_sticky_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        form = QFormLayout()

        self.btn_st_col = QPushButton()
        self.btn_st_col.clicked.connect(lambda: self.pick("sticky_color"))
        form.addRow("Sticky Note Block Background:", self.btn_st_col)

        self.spin_st_fs = QSpinBox()
        self.spin_st_fs.setRange(6, 100000)
        self.spin_st_fs.valueChanged.connect(lambda val: self.update("sticky_font_size", val))
        form.addRow("Body Text Default Font Size:", self.spin_st_fs)

        self.btn_st_fc = QPushButton()
        self.btn_st_fc.clicked.connect(lambda: self.pick("sticky_font_color"))
        form.addRow("Typography Contrast Ink Color:", self.btn_st_fc)

        layout.addLayout(form)
        layout.addStretch()
        layout.addWidget(self._reset_btn("Sticky Notes", ["sticky_color", "sticky_font_size", "sticky_font_color"]))
        return w

    def _build_backdrop_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        form = QFormLayout()

        self.btn_b_col = QPushButton()
        self.btn_b_col.clicked.connect(lambda: self.pick("backdrop_color"))
        form.addRow("Backdrop Group Layer Container Tint:", self.btn_b_col)

        self.spin_b_fs = QSpinBox()
        self.spin_b_fs.setRange(6, 100000)
        self.spin_b_fs.valueChanged.connect(lambda val: self.update("backdrop_font_size", val))
        form.addRow("Enclosure Title Header Size:", self.spin_b_fs)

        self.btn_b_fc = QPushButton()
        self.btn_b_fc.clicked.connect(lambda: self.pick("backdrop_font_color"))
        form.addRow("Enclosure Title Font Color:", self.btn_b_fc)

        layout.addLayout(form)
        layout.addStretch()
        layout.addWidget(self._reset_btn("Backdrops", ["backdrop_color", "backdrop_font_size", "backdrop_font_color"]))
        return w

    def _build_annotation_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        form = QFormLayout()

        self.btn_ann_col = QPushButton()
        self.btn_ann_col.clicked.connect(lambda: self.pick("annotation_color"))
        form.addRow("Stroke Color:", self.btn_ann_col)

        self.spin_ann_th = QSpinBox()
        self.spin_ann_th.setRange(1, 40)
        self.spin_ann_th.valueChanged.connect(lambda val: self.update("annotation_thickness", val))
        form.addRow("Stroke Thickness:", self.spin_ann_th)

        self.combo_ann_st = QComboBox()
        self.combo_ann_st.addItems(["solid", "dashed", "dotted"])
        self.combo_ann_st.currentTextChanged.connect(lambda txt: self.update("annotation_style", txt))
        form.addRow("Stroke Style:", self.combo_ann_st)

        layout.addLayout(form)
        layout.addStretch()
        layout.addWidget(self._reset_btn("Annotations", ["annotation_color", "annotation_thickness", "annotation_style"]))
        return w

    def _reset_btn(self, name, keys):
        btn = QPushButton(f"Reset {name} Defaults")
        btn.clicked.connect(lambda: self.reset_section(keys))
        return btn

    # =========================================================
    # CORE UI MUTATION & RESPONSIVENESS HANDLERS
    # =========================================================

    def pick(self, key):
        init_col = QColor(self._temp_settings.get(key, "#ffffff"))
        color = QColorDialog.getColor(init_col, self, f"Select color for {key}")
        if color.isValid():
            self.update(key, color.name(QColor.NameFormat.HexArgb))

    def update(self, key, val):
        self._temp_settings[key] = val
        self._apply_to_scene()
        self._update_widgets()

    def reset_section(self, keys):
        """Resets a specific section's defaults by inspecting the active theme key."""
        current_theme = self._temp_settings.get("theme", "dark")
        base_defaults = LIGHT_DEFAULTS if current_theme == "light" else DEFAULTS
        
        for k in keys:
            if k in base_defaults:
                self._temp_settings[k] = base_defaults[k]
                
        self._apply_to_scene()
        self._update_widgets()

    def reset_all(self):
        """Resets all defaults using the active theme identifier."""
        current_theme = self._temp_settings.get("theme", "dark")
        
        if current_theme == "light":
            self._temp_settings = LIGHT_DEFAULTS.copy()
            self._temp_settings["theme"] = "light"
        else:
            self._temp_settings = DEFAULTS.copy()
            self._temp_settings["theme"] = "dark"
            
        self._apply_to_scene()
        self._update_widgets()

    def apply_theme(self, theme):
        """Applies a theme profile and locks the theme identifier tracking string."""
        if theme == "light":
            self._temp_settings = LIGHT_DEFAULTS.copy()
            self._temp_settings["theme"] = "light"
        else:
            self._temp_settings = DEFAULTS.copy()
            self._temp_settings["theme"] = "dark"
            
        self._apply_to_scene()
        self._update_widgets()

    def _apply_to_scene(self):
        s = self._temp_settings
        if not self.scene or not self.scene._view:
            return

        from utils import update_menu_colors
        update_menu_colors(s['menu_bg'], s['menu_fg'])

        canvas_color = QColor(s['canvas_bg'])
        self.scene._view.setBackgroundBrush(canvas_color)
        self.scene.setBackgroundBrush(canvas_color)

        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QPalette
        app = QApplication.instance()
        if app:
            pal = app.palette()
            pal.setColor(QPalette.ColorRole.Window, QColor(s['menu_bg']))
            pal.setColor(QPalette.ColorRole.WindowText, QColor(s['menu_fg']))
            # Force target text styles to map safely to standard components
            pal.setColor(QPalette.ColorRole.ButtonText, QColor(s['menu_fg']))
            app.setPalette(pal)

        if self.scene and self.scene._view:
            for item in self.scene.items():
                if hasattr(item, 'update_from_settings'):
                    item.update_from_settings(s, force=True)
            self.scene._view._current_settings = s.copy()
            self.scene._current_settings = s.copy()

        self.scene.update()
        self.scene._view.viewport().update()

        # Push annotation defaults into the live CanvasPainter
        if hasattr(self.scene._view, '_canvas_painter'):
            cp = self.scene._view._canvas_painter
            cp.color     = QColor(s.get("annotation_color", "#FF8C00"))
            cp.thickness = int(s.get("annotation_thickness", 6))
            cp.style     = s.get("annotation_style", "solid")
            # Sync toolbar if currently open
            if cp._toolbar:
                cp._toolbar._color_swatch.setStyleSheet(
                    f"QPushButton {{ background:{cp.color.name()};"
                    f" border:2px solid #666; border-radius:4px; }}"
                    f"QPushButton:hover {{ border-color:#aaa; }}")
                cp._toolbar._thick_slider.blockSignals(True)
                cp._toolbar._thick_slider.setValue(cp.thickness)
                cp._toolbar._thick_slider.blockSignals(False)
                styles = ["solid", "dashed", "dotted"]
                if cp.style in styles:
                    cp._toolbar._style_combo.blockSignals(True)
                    cp._toolbar._style_combo.setCurrentIndex(styles.index(cp.style))
                    cp._toolbar._style_combo.blockSignals(False)

    def _contrast(self, hex_color):
        try:
            c = QColor(hex_color)
            lum = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue())
            return "#000000" if lum > 130 else "#ffffff"
        except Exception:
            return "#ffffff"

    def _update_widgets(self):
        s = self._temp_settings

        # 1. Update the Canvas Color Selector Buttons specifically
        self.btn_c_bg.setStyleSheet(f"background:{s['canvas_bg']};" + f" color:{self._contrast(s['canvas_bg'])};")
        self.btn_m_bg.setStyleSheet(f"background:{s['menu_bg']};" + f" color:{self._contrast(s['menu_bg'])};")
        self.chk_autosave.blockSignals(True)
        self.chk_autosave.setChecked(bool(s.get("autosave", True)))
        self.chk_autosave.blockSignals(False)
        # 2. Update all specific Node type configuration tabs
        for key, widgets in self.node_widgets.items():
            c_key = f"{key}_color"
            fs_key = f"{key}_font_size"
            fc_key = f"{key}_font_color"
            o_key = f"{key}_orientation"
            sh_key = f"{key}_shape"

            widgets["color"].setStyleSheet(f"background:{s[c_key]};" + f" color:{self._contrast(s[c_key])};")

            if widgets["font_size"] is not None:
                widgets["font_size"].blockSignals(True)
                widgets["font_size"].setValue(s[fs_key])
                widgets["font_size"].blockSignals(False)

            if widgets["font_color"] is not None:
                widgets["font_color"].setStyleSheet(f"background:{s[fc_key]};" + f" color:{self._contrast(s[fc_key])};")
            
            widgets["orientation"].blockSignals(True)
            widgets["orientation"].setCurrentText(s[o_key])
            widgets["orientation"].blockSignals(False)

            if widgets["shape"] is not None:
                widgets["shape"].blockSignals(True)
                idx = widgets["shape"].findData(s[sh_key])
                if idx >= 0:
                    widgets["shape"].setCurrentIndex(idx)
                widgets["shape"].blockSignals(False)

        # 3. Update Curves Tab values
        self.btn_cur_col.setStyleSheet(f"background:{s['curve_color']};" + f" color:{self._contrast(s['curve_color'])};")
        self.spin_cur_th.blockSignals(True)
        self.spin_cur_th.setValue(s['curve_thickness'])
        self.spin_cur_th.blockSignals(False)
        self.combo_cur_st.blockSignals(True)
        self.combo_cur_st.setCurrentText(s['curve_style'])
        self.combo_cur_st.blockSignals(False)
        self.combo_cur_ty.blockSignals(True)
        self.combo_cur_ty.setCurrentText(s['curve_type'])
        self.combo_cur_ty.blockSignals(False)
        self.btn_sock_col.setStyleSheet(f"background:{s['socket_color']};" + f" color:{self._contrast(s['socket_color'])};")
        self.spin_sock_sz.blockSignals(True)
        self.spin_sock_sz.setValue(s['socket_size'])
        self.spin_sock_sz.blockSignals(False)

        # 4. Update Sticky Notes tab values
        self.btn_st_col.setStyleSheet(f"background:{s['sticky_color']};" + f" color:{self._contrast(s['sticky_color'])};")
        self.spin_st_fs.blockSignals(True)
        self.spin_st_fs.setValue(s['sticky_font_size'])
        self.spin_st_fs.blockSignals(False)
        self.btn_st_fc.setStyleSheet(f"background:{s['sticky_font_color']};" + f" color:{self._contrast(s['sticky_font_color'])};")

        # 5. Update Backdrop tab values
        self.btn_b_col.setStyleSheet(f"background:{s['backdrop_color']};" + f" color:{self._contrast(s['backdrop_color'])};")
        self.spin_b_fs.blockSignals(True)
        self.spin_b_fs.setValue(s['backdrop_font_size'])
        self.spin_b_fs.blockSignals(False)
        self.btn_b_fc.setStyleSheet(f"background:{s['backdrop_font_color']};" + f" color:{self._contrast(s['backdrop_font_color'])};")

        # 6. Update Annotations tab values
        self.btn_ann_col.setStyleSheet(f"background:{s['annotation_color']};" + f" color:{self._contrast(s['annotation_color'])};")
        self.spin_ann_th.blockSignals(True)
        self.spin_ann_th.setValue(s['annotation_thickness'])
        self.spin_ann_th.blockSignals(False)
        self.combo_ann_st.blockSignals(True)
        self.combo_ann_st.setCurrentText(s['annotation_style'])
        self.combo_ann_st.blockSignals(False)
        # 6. DYNAMIC SYSTEM COMPONENT STYLESHEET OVERRIDE
        # ─────────────────────────────────────────────────────────
        theme = s.get("theme", "dark")
        bg = s['menu_bg']
        fg = s['menu_fg']
        
        if theme == "light":
            btn_bg = "#d4d4d4"       # Slightly darker than #e0e0e0 window background
            btn_border = "#bcbcbc"   # Clean matching edge border
            btn_hover = "#c8c8c8"    # Noticeable hover transition gray
            tab_bg = "#cccccc"       # Distinct inactive tab base bar color
            tab_selected = "#e0e0e0" # Selected tab matches your main window color
            pane_border = "#bcbcbc"  # Pane borders match button borders cleanly
        else:
            btn_bg = "#383838"       # Charcoal dark buttons
            btn_border = "#4e4e4e"   # Subtle dark border
            btn_hover = "#4a4a4a"    # Dark gray hover highlight
            tab_bg = "#1e1e1e"       # Dark tab bar backing
            tab_selected = "#2a2a2a" # Integrated open tab coloring
            pane_border = "#444444"  # Edge line color accent

        # Inject layout parameters down directly to control native element drawing profiles
        self.setStyleSheet(f"""
            QDialog {{ background: {bg}; color: {fg}; }}
            QLabel {{ color: {fg}; }}
            QGroupBox {{ color: {fg}; border: 1px solid {btn_border}; margin-top: 12px; padding-top: 14px; font-weight: bold; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; color: {fg}; }}
            
            QPushButton {{ 
                background-color: {btn_bg}; 
                color: {fg}; 
                border: 1px solid {btn_border}; 
                border-radius: 4px; 
                padding: 5px 14px; 
                min-height: 18px;
            }}
            QPushButton:hover {{ 
                background-color: {btn_hover}; 
            }}
            
            QTabWidget::pane {{ border: 1px solid {pane_border}; background: {bg}; }}
            QTabBar::tab {{ background: {tab_bg}; color: {fg}; padding: 6px 14px; border: 1px solid {pane_border}; border-bottom: none; }}
            QTabBar::tab:selected {{ background: {tab_selected}; border-bottom: 2px solid #4a9eff; }}
            
            QSpinBox, QComboBox {{
                background-color: {btn_bg};
                color: {fg};
                border: 1px solid {btn_border};
                border-radius: 4px;
                padding: 3px;
                min-height: 18px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {btn_bg};
                color: {fg};
                selection-background-color: #4a9eff;
            }}
        """)

    # =========================================================
    # PERSISTENCE
    # =========================================================

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                
                # ─── SMART AUTO-DETECTION FOR MISSING THEME KEY ───
                if "theme" not in data:
                    # If canvas background matches the light theme (#f0f0f0), mark it as light
                    cb = data.get("canvas_bg", "#1b1b1b").lower()
                    if cb in ["#9f9f9f", "#f0f0f0", "#ffffff"]:
                        data["theme"] = "light"
                    else:
                        data["theme"] = "dark"
                
                profile_theme = data.get("theme", "dark")
                merged = LIGHT_DEFAULTS.copy() if profile_theme == "light" else DEFAULTS.copy()
                merged.update(data)
                return merged
            except Exception:
                return DEFAULTS.copy()
        return DEFAULTS.copy()

    def save_settings(self):
        try:
            # ---> ADD THIS VERIFICATION PRINT LINE HERE <---
            print("--- VERIFYING DICTIONARY CONTENT BEFORE SAVING ---")
            print(json.dumps(self._temp_settings, indent=2)) 
            print("-------------------------------------------------")

            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self._temp_settings, f, indent=2)
            print(f"Settings successfully written to {SETTINGS_FILE}")
            if self.parent_view:
                self.parent_view.apply_settings(self._temp_settings)
        except Exception as e:
            print(f"Could not save settings configurations mapping downstream: {e}")