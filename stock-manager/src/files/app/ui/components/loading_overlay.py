"""
app/ui/components/loading_overlay.py — Semi-transparent page loading overlay.

Shown over a page while its data loads in a background thread.
Provides animated spinner + label so the UI never feels frozen.
"""
from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QFont

from app.core.theme import THEME


class LoadingOverlay(QWidget):
    """Translucent overlay with a spinning arc and status label.

    Usage:
        self._overlay = LoadingOverlay(self)
        self._overlay.show_loading("Loading inventory…")
        # … after data is ready:
        self._overlay.hide_loading()
    """

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.hide()

        self._angle  = 0
        self._label  = ""

        self._spin_timer = QTimer(self)
        self._spin_timer.setInterval(16)   # ~60 fps
        self._spin_timer.timeout.connect(self._tick)

    # ── Public ────────────────────────────────────────────────────────────────

    def show_loading(self, label: str = "Loading…") -> None:
        self._label = label
        self._angle = 0
        self.resize(self.parent().size())   # fill parent
        self.raise_()
        self.show()
        self._spin_timer.start()

    def hide_loading(self) -> None:
        self._spin_timer.stop()
        self.hide()

    def resizeEvent(self, ev) -> None:
        if self.parent():
            self.resize(self.parent().size())

    # ── Internal ─────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        self._angle = (self._angle + 6) % 360
        self.update()

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Dimmed background
        tk = THEME.tokens
        bg = QColor(tk.card)
        bg.setAlpha(210)
        p.fillRect(self.rect(), bg)

        # Spinner arc
        cx, cy = w // 2, h // 2
        r = 24
        pen = QPen(QColor(tk.green), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(QRect(cx - r, cy - r - 20, r * 2, r * 2),
                  self._angle * 16, 270 * 16)

        # Track arc
        track_pen = QPen(QColor(tk.border), 3)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(track_pen)
        p.drawArc(QRect(cx - r, cy - r - 20, r * 2, r * 2), 0, 360 * 16)

        # Re-draw spinner arc on top
        p.setPen(pen)
        p.drawArc(QRect(cx - r, cy - r - 20, r * 2, r * 2),
                  self._angle * 16, 270 * 16)

        # Label
        p.setPen(QColor(tk.t2))
        p.setFont(QFont("Segoe UI", 10))
        fm = p.fontMetrics()
        lw = fm.horizontalAdvance(self._label)
        p.drawText(cx - lw // 2, cy + 20, self._label)

        p.end()
