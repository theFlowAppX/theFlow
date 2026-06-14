# =========================================================
# theFlow! - Visual Canvas Application
# =========================================================
#
# Copyright (c) 2026 [Xavier Gares]
# GPLv3 License — see https://www.gnu.org/licenses/gpl-3.0.html

# =========================================================
# MENU
# =========================================================

from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction, QKeySequence
from utils import _menu_style


def build_menu(view, scene, scene_pos):
    ss = _menu_style()
    menu = QMenu(view)
    menu.setStyleSheet(ss)

    def act(label, shortcut=""):
        a = QAction(label, view)
        if shortcut:
            a.setShortcutVisibleInContextMenu(True)
            try:
                a.setShortcut(QKeySequence(shortcut))
            except Exception:
                pass
        return a

    # ── File ──────────────────────────────────────────────
    new_file     = act("New File",    "Ctrl+N")
    open_file    = act("Open",        "Ctrl+O")
    save_file    = act("Save",        "Ctrl+S")
    save_as_file    = act("Save As",        "Ctrl+Shift+S")
    export_selected = act("Export Selected", "Ctrl+E")
    import_nodes    = act("Import Nodes",    "Ctrl+I")
    quit_act        = act("Quit",        "Ctrl+Q")

    # ── Edit ──────────────────────────────────────────────
    copy_node  = act("Copy",          "Ctrl+C")
    cut_node   = act("Cut",           "Ctrl+X")
    paste_node = act("Paste",         "Ctrl+V")
    undo_act   = act("Undo",          "Ctrl+Z")
    redo_act   = act("Redo",          "Ctrl+Y")

    # ── Create → Node ─────────────────────────────────────
    create_text_node  = act("Text Node",     "T")
    create_image_node = act("Image Node",    "I")
    create_movie_node = act("Movie Node",    "M")
    create_audio_node = act("Audio Node",    "A")
    create_doc_node   = act("Document Node", "D")
    create_paint_node = act("Paint Node",    "P")
    create_dot        = act("Dot",           "Q")
    create_backdrop   = act("Backdrop",      "B")
    create_sticky     = act("Sticky Note",   "S")

    # ── View ──────────────────────────────────────────────
    rearrange_h   = act("Rearrange Horizontally", "H")
    rearrange_v   = act("Rearrange Vertically",   "V")
    frame_sel     = act("Frame Selected",          "F")
    frame_all     = act("Frame All",               "Z")
    center_sel    = act("Center Selected",         "C")
    expand_nodes        = act("Expand All Inline Viewers",      "Shift+Down")
    contract_nodes      = act("Close All Inline Viewers",       "Shift+Up")
    expand_selected     = act("Expand Selected Inline Viewers", "Down")
    contract_selected   = act("Close Selected Inline Viewers",  "Up")

    # ── Settings / Help / About ───────────────────────────
    settings_act      = act("Settings")
    draw_annot_act    = act("Draw Annotation", "Ctrl+P")
    shortcuts_act     = act("Shortcuts",            "K")
    documentation_act = act("Documentation")
    about_act         = act("About")

    # ── Build submenus ────────────────────────────────────
    def _sub(title):
        m = QMenu(title, view)
        m.setStyleSheet(ss)
        return m

    file_menu = _sub("File")
    file_menu.addAction(new_file)
    file_menu.addAction(open_file)
    file_menu.addAction(save_file)
    file_menu.addAction(save_as_file)
    file_menu.addAction(export_selected)
    file_menu.addAction(import_nodes)
    file_menu.addSeparator()
    file_menu.addAction(quit_act)

    edit_menu = _sub("Edit")
    edit_menu.addAction(copy_node)
    edit_menu.addAction(cut_node)
    edit_menu.addAction(paste_node)
    edit_menu.addSeparator()
    edit_menu.addAction(undo_act)
    edit_menu.addAction(redo_act)

    node_sub = _sub("Node")
    node_sub.addAction(create_audio_node)
    node_sub.addAction(create_doc_node)
    node_sub.addAction(create_image_node)
    node_sub.addAction(create_movie_node)
    node_sub.addAction(create_paint_node)
    node_sub.addAction(create_text_node)

    create_menu = _sub("Create")
    create_menu.addMenu(node_sub)
    create_menu.addAction(create_dot)
    create_menu.addSeparator()
    create_menu.addAction(create_backdrop)
    create_menu.addAction(create_sticky)

    view_menu = _sub("View")
    view_menu.addAction(rearrange_h)
    view_menu.addAction(rearrange_v)
    view_menu.addAction(frame_sel)
    view_menu.addAction(frame_all)
    view_menu.addAction(center_sel)
    view_menu.addSeparator()
    view_menu.addAction(expand_nodes)
    view_menu.addAction(contract_nodes)
    view_menu.addAction(expand_selected)
    view_menu.addAction(contract_selected)

    help_menu = _sub("Help")
    help_menu.addAction(shortcuts_act)
    help_menu.addAction(documentation_act)

    draw_menu = _sub("Draw")
    draw_menu.addAction(draw_annot_act)

    menu.addMenu(file_menu)
    menu.addSeparator()
    menu.addMenu(edit_menu)
    menu.addSeparator()
    menu.addMenu(create_menu)
    menu.addSeparator()
    menu.addMenu(view_menu)
    menu.addSeparator()
    menu.addMenu(draw_menu)
    menu.addSeparator()
    menu.addAction(settings_act)
    menu.addSeparator()
    menu.addMenu(help_menu)
    menu.addSeparator()
    menu.addAction(about_act)

    view._menu_actions = [
        new_file, open_file, save_file, save_as_file, export_selected,
        import_nodes, quit_act,
        copy_node, cut_node, paste_node, undo_act, redo_act,
        create_text_node, create_image_node, create_movie_node,
        create_audio_node, create_doc_node, create_paint_node,
        create_dot, create_backdrop, create_sticky,
        rearrange_h, rearrange_v, frame_sel, frame_all, center_sel,
        expand_nodes, contract_nodes, expand_selected, contract_selected,
        settings_act, shortcuts_act, documentation_act, about_act,
        draw_annot_act,
    ]

    return {
        "menu": menu,
        "actions": {
            "new":              new_file,
            "open":             open_file,
            "save":             save_file,
            "save_as":          save_as_file,
            "export_selected":  export_selected,
            "import_nodes":     import_nodes,
            "quit":             quit_act,
            "copy":             copy_node,
            "cut":              cut_node,
            "paste":            paste_node,
            "undo":             undo_act,
            "redo":             redo_act,
            "create":           create_text_node,
            "create_text":      create_text_node,
            "create_image":     create_image_node,
            "create_movie":     create_movie_node,
            "create_audio":     create_audio_node,
            "create_doc":       create_doc_node,
            "create_paint":     create_paint_node,
            "create_dot":       create_dot,
            "create_backdrop":  create_backdrop,
            "create_sticky":    create_sticky,
            "arrange_h":        rearrange_h,
            "arrange_v":        rearrange_v,
            "frame_selected":   frame_sel,
            "frame_all":        frame_all,
            "center_selected":  center_sel,
            "expand_nodes":          expand_nodes,
            "contract_nodes":        contract_nodes,
            "expand_selected":       expand_selected,
            "contract_selected":     contract_selected,
            "settings":         settings_act,
            "draw_annotation":  draw_annot_act,
            "shortcuts":        shortcuts_act,
            "documentation":    documentation_act,
            "about":            about_act,
        },
    }
