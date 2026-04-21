"""app/ui/components/skeleton.py — Animated shimmer placeholder.

Usage:
    sk = SkeletonBlock(height=120)
    # replace later: parent_layout.replaceWidget(sk, real_widget)
"""
from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QPainter, QLinearGradient, QColor

from app.core.theme import THEME


class SkeletonBlock(QFrame):
    """A rounded rectangle with a slowly-sweeping gradient highlight.

    The shimmer moves left→right over ~1.2s and loops. Colours pick up
    from the current theme so it blends in with any card that's hosting
    it.
    """

    def __init__(self, parent=None, *, height: int = 80) -> None:
        super().__init__(parent)
        self.setMinimumHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._phase = 0.0   # 0.0 .. 1.0 (shimmer position)
        self._timer = QTimer(self)
        self._timer.setInterval(40)  # ~25 fps
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self) -> None:
        self._phase = (self._phase + 0.03) % 1.0
        self.update()

    def paintEvent(self, _evt) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w, h = self.width(), self.height()
        rect = self.rect().adjusted(0, 0, -1, -1)
        radius = 6

        tk = THEME.tokens
        base = QColor(tk.card2)
        # Slightly brighter shimmer stripe based on current text tone
        shine = QColor(tk.t4)
        shine.setAlpha(80)

        # Background
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(base)
        p.drawRoundedRect(rect, radius, radius)

        # Gradient stripe
        span = w + 80
        x = -80 + int(self._phase * (w + 160))
        grad = QLinearGradient(QPointF(x, 0), QPointF(x + 80, 0))
        grad.setColorAt(0.0, QColor(tk.card2))
        grad.setColorAt(0.5, shine)
        grad.setColorAt(1.0, QColor(tk.card2))
        p.setBrush(grad)
        p.drawRoundedRect(rect, radius, radius)

        p.end()

    def stop(self) -> None:
        """Stop the animation timer (call before removing from layout)."""
        if self._timer.isActive():
            self._timer.stop()
