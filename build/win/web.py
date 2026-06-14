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

# web.py
# =========================================================
# WEB NODE  –  Inline browser node
# =========================================================
# WebNode displays a URL in an inline QWebEngineView anchored
# below the node, scaling with zoom. Double-click opens a dialog
# to set the node name and URL. Shortcut: W.
# =========================================================

import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QWidget, QGraphicsItem,
)
from PyQt6.QtCore import Qt, QUrl, QPointF, QRectF
from PyQt6.QtGui import QColor, QPen, QBrush, QPainter

from node import Node
from utils import NODE_BORDER, CORNER_RADIUS


# =========================================================
# DIALOG
# =========================================================

class WebNodeDialog(QDialog):
    """Name + URL editor for WebNode."""

    def __init__(self, parent, initial_name="Web", initial_url=""):
        super().__init__(parent)
        self.setWindowTitle("Edit Web Node")
        self.setMinimumWidth(480)
        self.setStyleSheet("background:#2a2a2a; color:#ffffff;")

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Name
        name_lbl = QLabel("Name  (visible on node):")
        name_lbl.setStyleSheet("color:#aaaaaa; font-size:11px;")
        layout.addWidget(name_lbl)

        self._name_edit = QLineEdit(initial_name)
        self._name_edit.setStyleSheet(
            "background:#1b1b1b; color:#ffffff; border:1px solid #5c5c5c;"
            " padding:4px; font-size:13px;")
        layout.addWidget(self._name_edit)

        # URL
        url_lbl = QLabel("URL:")
        url_lbl.setStyleSheet("color:#aaaaaa; font-size:11px; margin-top:6px;")
        layout.addWidget(url_lbl)

        url_row = QHBoxLayout()
        self._url_edit = QLineEdit(initial_url)
        self._url_edit.setPlaceholderText("https://example.com")
        self._url_edit.setStyleSheet(
            "background:#1b1b1b; color:#ffffff; border:1px solid #5c5c5c;"
            " padding:4px; font-size:13px;")
        url_row.addWidget(self._url_edit)

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(56)
        clear_btn.clicked.connect(lambda: self._url_edit.clear())
        clear_btn.setStyleSheet(
            "QPushButton{background:#3a3a3a;color:#fff;border:1px solid #5c5c5c;"
            "border-radius:4px;padding:2px 8px;}"
            "QPushButton:hover{background:#555;}")
        url_row.addWidget(clear_btn)

        open_btn = QPushButton("Open in Browser")
        open_btn.setStyleSheet(
            "QPushButton{background:#3a3a3a;color:#4a9eff;border:1px solid #5c5c5c;"
            "border-radius:4px;padding:2px 8px;}"
            "QPushButton:hover{background:#555;}")
        open_btn.clicked.connect(self._open_in_browser)
        url_row.addWidget(open_btn)
        layout.addLayout(url_row)

        # Buttons
        btn_row = QHBoxLayout()
        ok = QPushButton("OK")
        cancel = QPushButton("Cancel")
        ok.setStyleSheet(
            "QPushButton{background:#4a9eff;color:#fff;border:none;"
            "border-radius:4px;padding:4px 20px;}"
            "QPushButton:hover{background:#6ab0ff;}")
        cancel.setStyleSheet(
            "QPushButton{background:#3a3a3a;color:#fff;border:1px solid #5c5c5c;"
            "border-radius:4px;padding:4px 20px;}"
            "QPushButton:hover{background:#555;}")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(ok)
        btn_row.addWidget(cancel)
        layout.addLayout(btn_row)

    def _open_in_browser(self):
        import subprocess
        url = self.get_url()
        if url:
            subprocess.Popen(["open", url])

    def get_name(self) -> str:
        return self._name_edit.text().strip() or "Web"

    def get_url(self) -> str:
        url = self._url_edit.text().strip()
        if url and not url.startswith(("http://", "https://", "file://")):
            url = "https://" + url
        return url


# =========================================================
# INLINE WEB VIEWER
# =========================================================

class InlineWebViewer:
    """Off-screen rendering inline viewer — mirrors InlineImageViewer pattern.
    A hidden QWebEnginePage loads and renders the page off-screen; a QTimer
    grabs a pixmap every second and displays it in a viewport-parented QLabel.
    Double-clicking the label opens the full floating interactive viewer."""

    _NATIVE_W = 640
    _NATIVE_H = 480
    _GRAB_INTERVAL_MS = 1000   # refresh rate in milliseconds

    def __init__(self, view, node):
        self._view      = view
        self._node      = node
        self._pixmap    = None
        self._full_win  = None   # FloatingWebViewer when open

        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtCore import QTimer, QSize, QPoint

        # Off-screen view — must be SHOWN to render, but positioned off-screen
        self._offscreen = QWebEngineView()
        self._offscreen.resize(self._NATIVE_W, self._NATIVE_H)
        # Move far off-screen so it's invisible but renders
        self._offscreen.move(-2000, -2000)
        self._offscreen.setWindowFlags(Qt.WindowType.Tool |
                                       Qt.WindowType.FramelessWindowHint)
        self._offscreen.show()

        # Viewport-parented container — same pattern as InlineImageViewer
        self._container = QWidget(view.viewport())
        self._container.setStyleSheet("background:#111; border:none;")
        self._container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # URL label at top
        self._url_lbl = QLabel(self._container)
        self._url_lbl.setStyleSheet(
            "background:#1e1e1e; color:#4a9eff; font-size:10px; padding:2px 6px;")
        self._url_lbl.setText(node._url or "No URL — double-click node to set")
        self._url_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft |
                                   Qt.AlignmentFlag.AlignVCenter)

        # Pixmap label — shows the grabbed page, fills its entire area
        self._label = QLabel(self._container)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("background:#111; border:none; margin:0; padding:0;")
        self._label.setScaledContents(True)

        # Bottom bar with Open in Browser button
        self._bar = QWidget(self._container)
        self._bar.setStyleSheet("background:#1a1a1a;")
        bar_l = QHBoxLayout(self._bar)
        bar_l.setContentsMargins(4, 2, 4, 2)
        self._open_btn = QPushButton("Open in Browser")
        self._open_btn.setStyleSheet(
            "QPushButton{background:#2a2a2a;color:#4a9eff;border:none;"
            "border-radius:3px;font-size:9px;padding:1px 8px;}"
            "QPushButton:hover{background:#444;}")
        self._open_btn.clicked.connect(self._open_external)
        bar_l.addStretch()
        bar_l.addWidget(self._open_btn)
        bar_l.addStretch()

        # Grab timer
        self._timer = QTimer()
        self._timer.setInterval(self._GRAB_INTERVAL_MS)
        self._timer.timeout.connect(self._grab)

        # Load URL off-screen
        url = node._url
        if url:
            self._offscreen.load(QUrl(url))
            self._offscreen.loadFinished.connect(self._on_load_finished)
        else:
            self._offscreen.setHtml(_PLACEHOLDER_HTML)

        self._container.show()
        self._container.raise_()
        self.reposition()

    def _on_load_finished(self, ok):
        # Wait 500ms for the page to finish painting before grabbing
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, self._grab)
        self._timer.start()

    def _grab(self):
        """Capture the off-screen page and scale to fill the label exactly."""
        px = self._offscreen.grab()
        if not px.isNull():
            self._pixmap = px
            self._update_label()

    def _update_label(self):
        if self._pixmap and not self._pixmap.isNull():
            self._label.setPixmap(self._pixmap)

    def _open_external(self):
        import subprocess
        url = self._node._url
        if url:
            subprocess.Popen(["open", url])

    def load_url(self, url):
        """Called when the URL changes while the viewer is open."""
        self._url_lbl.setText(url or "No URL — double-click node to set")
        self._timer.stop()
        if url:
            self._offscreen.load(QUrl(url))
        else:
            self._offscreen.setHtml(_PLACEHOLDER_HTML)

    def open_full(self):
        """Open the floating interactive viewer."""
        if self._full_win is None:
            self._full_win = FloatingWebViewer(self._view, self._node)
        else:
            self._full_win._win.raise_()
            self._full_win._win.activateWindow()

    def reposition(self):
        scale  = self._view.transform().m11()
        w      = max(80,  int(self._NATIVE_W * scale))
        h      = max(60,  int(self._NATIVE_H * scale))
        url_h  = max(16,  int(20 * scale))
        bar_h  = max(18,  int(22 * scale))
        img_h  = h - url_h - bar_h

        self._container.setFixedSize(w, h)
        self._url_lbl.setGeometry(0, 0, w, url_h)
        self._label.setGeometry(0, url_h, w, img_h)
        self._bar.setGeometry(0, url_h + img_h, w, bar_h)

        # Rounded corners — clip all four corners using path-to-region
        from PyQt6.QtGui import QPainterPath
        from PyQt6.QtCore import QRect
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, 12, 12)
        from PyQt6.QtWidgets import QApplication as _QA
        from PyQt6.QtGui import QRegion, QPolygon
        poly = path.toFillPolygon().toPolygon()
        self._container.setMask(QRegion(poly))

        fnt = max(7, int(9 * scale))
        self._url_lbl.setStyleSheet(
            f"background:#1e1e1e;color:#4a9eff;font-size:{fnt}px;padding:2px 6px;")
        self._open_btn.setStyleSheet(
            f"QPushButton{{background:#2a2a2a;color:#4a9eff;border:none;"
            f"border-radius:3px;font-size:{fnt}px;padding:1px 8px;}}"
            f"QPushButton:hover{{background:#444;}}")

        # Resize off-screen page stays at native size for sharp grabs
        self._update_label()

        scene_pt = self._node.mapToScene(QPointF(0, self._node.height))
        vp_pt    = self._view.mapFromScene(scene_pt)
        self._container.move(vp_pt.x(), vp_pt.y())

    def close(self):
        self._timer.stop()
        self._offscreen.stop()
        self._offscreen.setUrl(QUrl("about:blank"))
        self._offscreen.hide()
        self._offscreen.deleteLater()
        if self._full_win is not None:
            self._full_win.close()
            self._full_win = None
        self._container.hide()
        self._container.deleteLater()


class FloatingWebViewer:
    """Full interactive floating viewer opened by double-clicking InlineWebViewer."""

    _W = 900
    _H = 640

    def __init__(self, view, node):
        self._view = view
        self._node = node

        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtCore import QTimer

        self._win = QWidget(None,
                            Qt.WindowType.Tool |
                            Qt.WindowType.FramelessWindowHint)
        self._win.setStyleSheet("background:#111; border:1px solid #444;")
        self._win.resize(self._W, self._H)

        root = QVBoxLayout(self._win)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        bar = QWidget()
        bar.setFixedHeight(30)
        bar.setStyleSheet("background:#1e1e1e; border-bottom:1px solid #333;")
        bar_l = QHBoxLayout(bar)
        bar_l.setContentsMargins(6, 2, 6, 2)
        bar_l.setSpacing(4)

        self._back_btn   = QPushButton("←")
        self._fwd_btn    = QPushButton("→")
        self._reload_btn = QPushButton("⟳")
        self._open_btn   = QPushButton("Open in Browser")
        self._close_btn  = QPushButton("×")

        for btn in (self._back_btn, self._fwd_btn, self._reload_btn):
            btn.setFixedSize(28, 24)
            btn.setStyleSheet(
                "QPushButton{background:#2a2a2a;color:#fff;border:none;"
                "border-radius:3px;font-size:12px;}"
                "QPushButton:hover{background:#444;}"
                "QPushButton:disabled{color:#555;}")

        self._open_btn.setStyleSheet(
            "QPushButton{background:#2a2a2a;color:#4a9eff;border:none;"
            "border-radius:3px;font-size:10px;padding:0 6px;}"
            "QPushButton:hover{background:#444;}")

        self._close_btn.setFixedSize(24, 24)
        self._close_btn.setStyleSheet(
            "QPushButton{background:#3a2020;color:#ff6666;border:none;"
            "border-radius:3px;font-size:14px;}"
            "QPushButton:hover{background:#662020;}")
        self._close_btn.clicked.connect(self.close)

        self._url_bar = QLineEdit()
        self._url_bar.setStyleSheet(
            "background:#0d0d0d;color:#ccc;border:1px solid #333;"
            "border-radius:3px;padding:1px 4px;font-size:10px;")
        self._url_bar.returnPressed.connect(self._navigate_from_bar)

        bar_l.addWidget(self._back_btn)
        bar_l.addWidget(self._fwd_btn)
        bar_l.addWidget(self._reload_btn)
        bar_l.addWidget(self._url_bar, 1)
        bar_l.addWidget(self._open_btn)
        bar_l.addWidget(self._close_btn)
        root.addWidget(bar)

        self._web = QWebEngineView()
        root.addWidget(self._web, 1)

        self._back_btn.clicked.connect(self._web.back)
        self._fwd_btn.clicked.connect(self._web.forward)
        self._reload_btn.clicked.connect(self._web.reload)
        self._open_btn.clicked.connect(self._open_external)
        self._web.urlChanged.connect(self._on_url_changed)
        self._web.loadFinished.connect(self._on_load_finished)

        # Position below node
        scene_pt  = node.mapToScene(QPointF(0, node.height))
        vp_pt     = view.mapFromScene(scene_pt)
        global_pt = view.viewport().mapToGlobal(vp_pt)
        self._win.move(global_pt)
        self._win.show()

        url = node._url
        if url:
            self._web.load(QUrl(url))
        else:
            self._web.setHtml(_PLACEHOLDER_HTML)

    def _navigate_from_bar(self):
        text = self._url_bar.text().strip()
        if text:
            if not text.startswith(("http://", "https://", "file://")):
                text = "https://" + text
            self._web.load(QUrl(text))

    def _on_url_changed(self, url):
        self._url_bar.setText(url.toString())

    def _on_load_finished(self, ok):
        hist = self._web.page().history()
        self._back_btn.setEnabled(hist.canGoBack())
        self._fwd_btn.setEnabled(hist.canGoForward())

    def _open_external(self):
        import subprocess
        url = self._web.url().toString()
        if url and url not in ("", "about:blank"):
            subprocess.Popen(["open", url])

    def close(self):
        self._web.stop()
        self._web.setUrl(QUrl("about:blank"))
        self._win.hide()
        self._win.deleteLater()
_PLACEHOLDER_HTML = """
<html><body style='background:#111;color:#555;font-family:sans-serif;
display:flex;align-items:center;justify-content:center;height:100%;margin:0;'>
<p style='text-align:center;font-size:14px;'>No URL set<br>
<span style='font-size:11px;'>Double-click the node to add one</span></p>
</body></html>
"""


# =========================================================
# WEB NODE
# =========================================================

class WebNode(Node):
    """A node that loads and displays a web page inline.

    Badge: a globe icon (W) in the top-right.
    Double-click: opens WebNodeDialog to set name + URL.
    Arrow-down: opens/closes the inline web viewer.
    """

    _PNG_WEB_BLACK = None
    _PNG_WEB_WHITE = None

    @classmethod
    def _get_web_icons(cls):
        if cls._PNG_WEB_BLACK is None:
            from node import _svg_to_pixmap
            _base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
            cls._PNG_WEB_BLACK = _svg_to_pixmap(
                os.path.join(_base, "internet_black.svg"))
            cls._PNG_WEB_WHITE = _svg_to_pixmap(
                os.path.join(_base, "internet_white.svg"))
        return cls._PNG_WEB_BLACK, cls._PNG_WEB_WHITE

    def _draw_web_icon(self, painter):
        black_px, white_px = self._get_web_icons()
        px = white_px if self._url else black_px
        if px is None or px.isNull():
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

    def __init__(self, x=0, y=0, view=None, name="Web"):
        super().__init__(x, y, view, name)
        self._node_type    = "web"
        self._url          = ""
        self._inline_player = None   # InlineWebViewer instance

    # ── Inline viewer ─────────────────────────────────────────────────

    def open_inline_player(self):
        if not self.scene():
            return
        view = self.scene().views()[0] if self.scene().views() else None
        if not view:
            return
        if self._inline_player is not None:
            self.close_inline_player()
        self._inline_player = InlineWebViewer(view, self)

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

    # ── Double-click → dialog ─────────────────────────────────────────

    def mouseDoubleClickEvent(self, event):
        view = (self.scene().views()[0]
                if self.scene() and self.scene().views() else None)
        if not view:
            return

        dlg = WebNodeDialog(view, self.title._plain, self._url)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            old_name = self.title._plain
            old_url  = self._url
            new_name = dlg.get_name()
            new_url  = dlg.get_url()

            self.title._plain = new_name
            self.title.setPlainText(new_name)
            self._fit_to_text()
            self._url = new_url
            self.update()

            # Reload inline viewer if open
            if self._inline_player is not None:
                self._inline_player.load_url(new_url)

            if self.scene():
                self.scene()._push_undo({
                    "type":     "web_node_edit",
                    "node":     self,
                    "old_name": old_name, "new_name": new_name,
                    "old_url":  old_url,  "new_url":  new_url,
                })
                self.scene().mark_dirty()
        event.accept()

    # ── Paint — blue globe badge ──────────────────────────────────────

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width, self.height)

        # Selection glow
        if self.isSelected():
            glow = QColor(74, 158, 255, 35)
            for i in range(10):
                spread = i * 1.5
                c = QColor(glow)
                c.setAlpha(max(0, 35 - i * 4))
                painter.setPen(QPen(c, 1 + i))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                self._draw_shape(painter, rect.adjusted(-spread, -spread, spread, spread), spread)

        painter.setBrush(QBrush(self._color))
        painter.setPen(QPen(QColor(NODE_BORDER), 1.2))
        self._draw_shape(painter, rect, 0)

        if self.isSelected():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(255, 255, 255, 140), 2))
            self._draw_shape(painter, rect, 0)

        self._draw_web_icon(painter)
