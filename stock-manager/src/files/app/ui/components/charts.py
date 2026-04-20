"""
app/ui/components/charts.py — Lightweight chart widgets using QPainter.
No external dependencies — pure PyQt6 rendering.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QFontMetrics,
    QPainterPath, QLinearGradient,
)

from app.core.theme import THEME


# ── Data types ──────────────────────────────────────────────────────────────

@dataclass
class PieSlice:
    label: str
    value: float
    color: str       # hex6

@dataclass
class BarItem:
    label: str
    value: float
    color: str       # hex6

@dataclass
class LinePoint:
    label: str
    value: float


# ── Donut / Pie Chart ──────────────────────────────────────────────────────

class DonutChart(QWidget):
    """Donut chart with center label and legend."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._slices: list[PieSlice] = []
        self._center_label = ""
        self._center_value = ""
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, slices: list[PieSlice],
                 center_label: str = "", center_value: str = "") -> None:
        self._slices = slices
        self._center_label = center_label
        self._center_value = center_value
        self.update()

    def paintEvent(self, event) -> None:
        if not self._slices:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tk = THEME.tokens

        w, h = self.width(), self.height()
        legend_w = min(140, w * 0.35)
        chart_area = min(w - legend_w - 20, h - 20)
        diameter = max(80, chart_area)
        cx = (w - legend_w) / 2
        cy = h / 2
        outer_r = diameter / 2
        inner_r = outer_r * 0.6
        rect = QRectF(cx - outer_r, cy - outer_r, diameter, diameter)

        total = sum(s.value for s in self._slices)
        if total == 0:
            painter.end(); return

        # Draw slices
        start_angle = 90 * 16  # top
        for sl in self._slices:
            span = int((sl.value / total) * 360 * 16)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(sl.color))
            painter.drawPie(rect, start_angle, -span)
            start_angle -= span

        # Inner circle (donut hole)
        painter.setBrush(QColor(tk.card))
        painter.setPen(Qt.PenStyle.NoPen)
        inner_rect = QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)
        painter.drawEllipse(inner_rect)

        # Center text
        if self._center_value:
            f_val = QFont("Segoe UI", max(12, int(inner_r * 0.35)), QFont.Weight.Bold)
            painter.setFont(f_val)
            painter.setPen(QColor(tk.t1))
            painter.drawText(inner_rect.adjusted(0, -8, 0, 0),
                             Qt.AlignmentFlag.AlignCenter, self._center_value)
        if self._center_label:
            f_lbl = QFont("Segoe UI", max(8, int(inner_r * 0.16)))
            painter.setFont(f_lbl)
            painter.setPen(QColor(tk.t3))
            painter.drawText(inner_rect.adjusted(0, 16, 0, 0),
                             Qt.AlignmentFlag.AlignCenter, self._center_label)

        # Legend
        lx = w - legend_w
        ly = max(20, cy - len(self._slices) * 22 / 2)
        f_legend = QFont("Segoe UI", 9)
        painter.setFont(f_legend)
        fm = QFontMetrics(f_legend)
        for sl in self._slices:
            # Color dot
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(sl.color))
            painter.drawEllipse(int(lx), int(ly + 2), 10, 10)
            # Label
            painter.setPen(QColor(tk.t2))
            pct = f"{sl.value / total * 100:.0f}%" if total > 0 else "0%"
            text = f"{sl.label}  {pct}"
            painter.drawText(int(lx + 16), int(ly + 12), text)
            ly += 22

        painter.end()


# ── Horizontal Bar Chart ───────────────────────────────────────────────────

class HBarChart(QWidget):
    """Horizontal bar chart with labels and values.

    A `value_format` callable (float -> str) can be supplied via set_data so
    values render with currency symbols, units, decimals, etc. — defaults
    to `str(int(v))` for integer counts.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bars: list[BarItem] = []
        self._title = ""
        self._value_format = lambda v: str(int(v))
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, bars: list[BarItem], title: str = "",
                 value_format=None) -> None:
        self._bars = bars
        self._title = title
        if value_format is not None and callable(value_format):
            self._value_format = value_format
        self.setMinimumHeight(max(120, 32 + len(bars) * 30))
        self.update()

    def paintEvent(self, event) -> None:
        if not self._bars:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tk = THEME.tokens

        w, h = self.width(), self.height()
        margin_l = 110  # space for labels
        margin_r = 96   # wider: fits formatted currency "€12,340.00"
        bar_area = w - margin_l - margin_r
        max_val = max((b.value for b in self._bars), default=1) or 1

        y_offset = 8
        if self._title:
            f_title = QFont("Segoe UI", 10, QFont.Weight.Bold)
            painter.setFont(f_title)
            painter.setPen(QColor(tk.t2))
            painter.drawText(margin_l, y_offset + 14, self._title)
            y_offset += 26

        bar_h = 18
        spacing = 30
        f_label = QFont("Segoe UI", 9)
        f_value = QFont("Segoe UI", 9, QFont.Weight.Bold)

        for bar in self._bars:
            # Label
            painter.setFont(f_label)
            painter.setPen(QColor(tk.t2))
            label_rect = QRectF(4, y_offset, margin_l - 8, spacing)
            painter.drawText(label_rect,
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             bar.label)

            # Bar background track
            track_rect = QRectF(margin_l, y_offset + (spacing - bar_h) / 2,
                                bar_area, bar_h)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(tk.border))
            painter.drawRoundedRect(track_rect, 4, 4)

            # Bar fill
            fill_w = max(4, (bar.value / max_val) * bar_area)
            fill_rect = QRectF(margin_l, y_offset + (spacing - bar_h) / 2,
                                fill_w, bar_h)
            painter.setBrush(QColor(bar.color))
            painter.drawRoundedRect(fill_rect, 4, 4)

            # Value (formatted via set_data.value_format; defaults to int)
            painter.setFont(f_value)
            painter.setPen(QColor(tk.t1))
            val_rect = QRectF(margin_l + bar_area + 6, y_offset,
                               margin_r - 10, spacing)
            try:
                val_text = self._value_format(bar.value)
            except Exception:
                val_text = str(int(bar.value))
            painter.drawText(val_rect,
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                             val_text)

            y_offset += spacing

        painter.end()


# ── Area Line Chart ────────────────────────────────────────────────────────

class AreaLineChart(QWidget):
    """Line chart with gradient fill beneath the line."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._points: list[LinePoint] = []
        self._title = ""
        self._line_color = "#10B981"
        self.setMinimumSize(200, 140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, points: list[LinePoint], title: str = "",
                 line_color: str = "") -> None:
        self._points = points
        self._title = title
        if line_color:
            self._line_color = line_color
        self.update()

    def paintEvent(self, event) -> None:
        if len(self._points) < 2:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tk = THEME.tokens

        w, h = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 50, 16, 30, 30
        cw = w - pad_l - pad_r
        ch = h - pad_t - pad_b

        # Title
        if self._title:
            f_title = QFont("Segoe UI", 10, QFont.Weight.Bold)
            painter.setFont(f_title)
            painter.setPen(QColor(tk.t2))
            painter.drawText(pad_l, 16, self._title)

        vals = [p.value for p in self._points]
        mn, mx = min(vals), max(vals)
        rng = mx - mn or 1

        # Y-axis grid lines
        painter.setPen(QPen(QColor(tk.border), 1, Qt.PenStyle.DashLine))
        f_axis = QFont("Segoe UI", 8)
        painter.setFont(f_axis)
        for i in range(5):
            y = pad_t + ch - (i / 4) * ch
            painter.setPen(QPen(QColor(tk.border), 1, Qt.PenStyle.DashLine))
            painter.drawLine(int(pad_l), int(y), int(w - pad_r), int(y))
            painter.setPen(QColor(tk.t4))
            v = mn + (i / 4) * rng
            painter.drawText(0, int(y - 6), pad_l - 6, 14,
                             Qt.AlignmentFlag.AlignRight, str(int(v)))

        # Build points
        coords: list[QPointF] = []
        for i, pt in enumerate(self._points):
            px = pad_l + (i / (len(self._points) - 1)) * cw
            py = pad_t + ch - ((pt.value - mn) / rng) * ch
            coords.append(QPointF(px, py))

        # Gradient fill
        grad = QLinearGradient(0, pad_t, 0, pad_t + ch)
        lc = QColor(self._line_color)
        lc.setAlpha(80)
        grad.setColorAt(0, lc)
        lc.setAlpha(5)
        grad.setColorAt(1, lc)

        fill_path = QPainterPath()
        fill_path.moveTo(coords[0].x(), pad_t + ch)
        for p in coords:
            fill_path.lineTo(p)
        fill_path.lineTo(coords[-1].x(), pad_t + ch)
        fill_path.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawPath(fill_path)

        # Line
        painter.setPen(QPen(QColor(self._line_color), 2.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(len(coords) - 1):
            painter.drawLine(coords[i], coords[i + 1])

        # Dots
        painter.setBrush(QColor(self._line_color))
        painter.setPen(Qt.PenStyle.NoPen)
        for p in coords:
            painter.drawEllipse(p, 3, 3)

        # X-axis labels (show ~6 evenly spaced)
        painter.setFont(f_axis)
        painter.setPen(QColor(tk.t4))
        step = max(1, len(self._points) // 6)
        for i in range(0, len(self._points), step):
            px = pad_l + (i / (len(self._points) - 1)) * cw
            label = self._points[i].label
            painter.drawText(int(px - 20), int(pad_t + ch + 6), 40, 20,
                             Qt.AlignmentFlag.AlignHCenter, label)

        painter.end()
