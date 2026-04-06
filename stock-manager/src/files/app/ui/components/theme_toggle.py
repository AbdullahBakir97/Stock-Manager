"""
app/ui/components/theme_toggle.py — Animated sliding theme toggle.
"""
from __future__ import annotations

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont

from app.core.theme import THEME
from app.core.i18n import t


class ThemeToggle(QWidget):
    """Animated sliding toggle with sun/moon icons. Click = toggle, right-click = cycle."""
    theme_toggled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(52, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(t("tooltip_theme"))
        self._knob_x = self._target_x()
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(12)
        self._anim_timer.timeout.connect(self._animate_step)

    def _target_x(self) -> float:
        return float(self.width() - self.height() + 2) if THEME.is_dark else 2.0

    def _animate_step(self):
        target = self._target_x()
        diff = target - self._knob_x
        if abs(diff) < 0.5:
            self._knob_x = target
            self._anim_timer.stop()
        else:
            self._knob_x += diff * 0.25
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        knob_d = h - 4

        track_col = QColor("#334155") if THEME.is_dark else QColor("#CBD5E1")
        p.setBrush(track_col)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, w, h, h // 2, h // 2)

        if THEME.is_dark:
            p.setBrush(QColor(255, 255, 255, 40))
            p.drawEllipse(8, 7, 3, 3)
            p.drawEllipse(14, 14, 2, 2)
            p.drawEllipse(11, 19, 2, 2)
        else:
            p.setBrush(QColor(251, 191, 36, 50))
            p.drawEllipse(34, 8, 3, 3)
            p.drawEllipse(38, 15, 2, 2)
            p.drawEllipse(32, 18, 2, 2)

        kx = int(self._knob_x)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(kx, 2, knob_d, knob_d)

        icon_font = QFont("Segoe UI", 11)
        p.setFont(icon_font)
        if THEME.is_dark:
            p.setPen(QColor("#1E293B"))
            p.drawText(kx, 2, knob_d, knob_d, Qt.AlignmentFlag.AlignCenter, "🌙")
        else:
            p.setPen(QColor("#92400E"))
            p.drawText(kx, 2, knob_d, knob_d, Qt.AlignmentFlag.AlignCenter, "☀")

        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            THEME.cycle()
        else:
            THEME.toggle()
        self._anim_timer.start()
        self.theme_toggled.emit()

    def _update_text(self):
        self._knob_x = self._target_x()
        self.update()
