"""app/ui/components/kpi_tile.py — Professional KPI card.

Layout:
    +------------------------------------+
    | LABEL                   ▲ 14.2%   |
    | €12,340.00                         |
    | (sparkline, 28 px tall)            |
    +------------------------------------+

API:
    tile = KpiTile()
    tile.set_data(label="REVENUE", value="€3,120.50",
                  delta_pct=8.7, delta_dir="up",
                  sparkline=[1,2,3,...], accent="#10B981")
    tile.clicked.connect(lambda: open_detail())
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import (
    QFont, QPainter, QPen, QColor, QLinearGradient, QPainterPath,
)

from app.core.theme import THEME
from app.ui.components.delta_badge import DeltaBadge


class _Sparkline(QWidget):
    """Tiny area line inside the KPI card."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._values: list[float] = []
        self._color = "#10B981"
        self.setFixedHeight(28)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_values(self, values: list[float], color_hex: str = "#10B981") -> None:
        self._values = list(values) if values else []
        self._color = color_hex
        self.update()

    def paintEvent(self, _evt) -> None:
        if not self._values or len(self._values) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w, h = self.width(), self.height()
        pad = 2
        inner_w = max(1, w - pad * 2)
        inner_h = max(1, h - pad * 2)

        vmax = max(self._values) or 1.0
        vmin = min(self._values)
        vrange = (vmax - vmin) or 1.0
        n = len(self._values)
        dx = inner_w / max(1, (n - 1))

        def _pt(i: int) -> QPointF:
            v = self._values[i]
            y = pad + inner_h - ((v - vmin) / vrange) * inner_h
            x = pad + i * dx
            return QPointF(x, y)

        # Gradient fill under the line
        path = QPainterPath()
        path.moveTo(_pt(0).x(), pad + inner_h)
        for i in range(n):
            pt = _pt(i)
            if i == 0:
                path.lineTo(pt)
            else:
                path.lineTo(pt)
        path.lineTo(_pt(n - 1).x(), pad + inner_h)
        path.closeSubpath()

        color = QColor(self._color)
        fill_top = QColor(color); fill_top.setAlpha(70)
        fill_bot = QColor(color); fill_bot.setAlpha(0)
        grad = QLinearGradient(0, pad, 0, pad + inner_h)
        grad.setColorAt(0, fill_top)
        grad.setColorAt(1, fill_bot)
        p.setBrush(grad); p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(path)

        # Line on top
        pen = QPen(color, 1.6)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
        line = QPainterPath()
        line.moveTo(_pt(0))
        for i in range(1, n):
            line.lineTo(_pt(i))
        p.drawPath(line)
        p.end()


class KpiTile(QFrame):
    """KPI card: label · delta · value · sparkline. Clickable."""

    clicked = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("kpi_tile")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(104)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(2)

        # Row 1: label (left) + delta badge (right)
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        self._label = QLabel("—")
        self._label.setObjectName("kpi_tile_label")
        self._label.setStyleSheet(
            f"color: {THEME.tokens.t3}; font-size: 10px; "
            f"font-weight: 700; letter-spacing: 0.08em;"
        )
        top_row.addWidget(self._label)
        top_row.addStretch()

        self._delta = DeltaBadge()
        self._delta.setFixedHeight(18)
        top_row.addWidget(self._delta)
        root.addLayout(top_row)

        # Row 2: large value
        self._value = QLabel("—")
        self._value.setObjectName("kpi_tile_value")
        self._value.setStyleSheet(
            f"color: {THEME.tokens.t1}; font-size: 20px;"
            f" font-weight: 800; font-family: 'Segoe UI', sans-serif;"
        )
        self._value.setFont(QFont("Segoe UI", 18, QFont.Weight.Black))
        root.addWidget(self._value)

        # Spacer so sparkline hugs the bottom
        root.addStretch()

        self._spark = _Sparkline(self)
        root.addWidget(self._spark)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def set_data(self, *, label: str, value: str,
                 delta_pct: float = 0.0, delta_dir: str = "flat",
                 sparkline: list[float] | None = None,
                 accent: str = "") -> None:
        self._label.setText(label.upper())
        self._value.setText(value)
        self._delta.set_delta(delta_pct, delta_dir)
        color = accent or THEME.tokens.green
        self._spark.set_values(sparkline or [], color)
