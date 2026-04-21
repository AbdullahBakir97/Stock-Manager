"""app/ui/components/dual_line_chart.py — Current + Previous-Period area chart.

Two series on the same canvas:
    - Current period: filled area + solid accent line + dots
    - Previous period: dashed faint line (no fill)

Labels + axis + hover tooltip with the exact value.
"""
from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QSizePolicy, QToolTip
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QLinearGradient, QPainterPath, QFont,
)

from app.core.theme import THEME


class DualLineChart(QWidget):
    """Area line chart with optional previous-period ghost overlay."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

        self._cur: list[tuple[str, float]] = []
        self._prev: list[tuple[str, float]] = []
        self._title: str = ""
        self._line_color = THEME.tokens.green
        self._hover_idx: int = -1

    def set_data(self, current: list[tuple[str, float]],
                 previous: list[tuple[str, float]] | None = None,
                 title: str = "",
                 line_color: str = "") -> None:
        self._cur = list(current or [])
        self._prev = list(previous or [])
        self._title = title
        if line_color:
            self._line_color = line_color
        self.update()

    # ── Hover → tooltip ────────────────────────────────────────────────────

    def mouseMoveEvent(self, e) -> None:
        if not self._cur:
            return super().mouseMoveEvent(e)
        w, h = self.width(), self.height()
        left, right, top, bot = 52, 18, 30, 34
        plot_w = w - left - right
        if plot_w <= 0:
            return super().mouseMoveEvent(e)
        n = len(self._cur)
        dx = plot_w / max(1, n - 1)
        x = e.pos().x() - left
        idx = int(round(x / dx)) if dx > 0 else -1
        if 0 <= idx < n:
            if idx != self._hover_idx:
                self._hover_idx = idx
                self.update()
            date, value = self._cur[idx]
            prev_v = self._prev[idx][1] if idx < len(self._prev) else None
            txt = f"{date}\nCurrent: {value:,.2f}"
            if prev_v is not None:
                txt += f"\nPrevious: {prev_v:,.2f}"
            QToolTip.showText(e.globalPosition().toPoint(), txt, self)
        else:
            if self._hover_idx != -1:
                self._hover_idx = -1
                self.update()
        super().mouseMoveEvent(e)

    def leaveEvent(self, e) -> None:
        if self._hover_idx != -1:
            self._hover_idx = -1
            self.update()
        super().leaveEvent(e)

    # ── Painting ───────────────────────────────────────────────────────────

    def paintEvent(self, _evt) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        tk = THEME.tokens
        w, h = self.width(), self.height()
        left, right, top, bot = 52, 18, 30, 34
        plot_w = max(1, w - left - right)
        plot_h = max(1, h - top - bot)

        # Title
        if self._title:
            p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            p.setPen(QColor(tk.t1))
            p.drawText(QRectF(left, 4, plot_w, 22),
                       Qt.AlignmentFlag.AlignLeft
                       | Qt.AlignmentFlag.AlignVCenter,
                       self._title)

        if not self._cur:
            p.setFont(QFont("Segoe UI", 10))
            p.setPen(QColor(tk.t4))
            p.drawText(self.rect(),
                       Qt.AlignmentFlag.AlignCenter,
                       "No data for this period")
            p.end()
            return

        # Y-axis extrema from BOTH series (so they share the scale)
        all_vals = [v for _, v in self._cur] + [v for _, v in self._prev]
        vmax = max(all_vals) if all_vals else 1.0
        vmin = min(all_vals) if all_vals else 0.0
        if vmax == vmin:
            vmax = vmin + 1
        padv = (vmax - vmin) * 0.12
        vmax += padv

        # Grid + Y labels (5 lines)
        p.setPen(QPen(QColor(tk.border), 1, Qt.PenStyle.DashLine))
        p.setFont(QFont("Segoe UI", 8))
        for i in range(5):
            y = top + plot_h * (i / 4)
            p.setPen(QPen(QColor(tk.border), 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(left, y), QPointF(w - right, y))
            p.setPen(QColor(tk.t4))
            label_v = vmax - (vmax - vmin) * (i / 4)
            p.drawText(QRectF(0, y - 8, left - 6, 16),
                       Qt.AlignmentFlag.AlignRight
                       | Qt.AlignmentFlag.AlignVCenter,
                       f"{int(label_v) if vmax >= 10 else label_v:.1f}"
                       if vmax < 10 else f"{int(label_v)}")

        # Helper to convert a series to points
        def _series_pts(series: list[tuple[str, float]]) -> list[QPointF]:
            n = len(series)
            if n < 2:
                return []
            dx = plot_w / (n - 1)
            pts: list[QPointF] = []
            for i, (_, v) in enumerate(series):
                y = top + plot_h - ((v - vmin) / (vmax - vmin)) * plot_h
                pts.append(QPointF(left + i * dx, y))
            return pts

        # ── Previous series (ghost dashed line) ──
        prev_pts = _series_pts(self._prev)
        if prev_pts:
            prev_pen = QPen(QColor(tk.t4), 1.4, Qt.PenStyle.DashLine)
            p.setPen(prev_pen); p.setBrush(Qt.BrushStyle.NoBrush)
            path = QPainterPath()
            path.moveTo(prev_pts[0])
            for pt in prev_pts[1:]:
                path.lineTo(pt)
            p.drawPath(path)

        # ── Current series (filled area + solid line + dots) ──
        cur_pts = _series_pts(self._cur)
        if cur_pts:
            # Area fill
            area = QPainterPath()
            area.moveTo(cur_pts[0].x(), top + plot_h)
            for pt in cur_pts:
                area.lineTo(pt)
            area.lineTo(cur_pts[-1].x(), top + plot_h)
            area.closeSubpath()

            col = QColor(self._line_color)
            top_fill = QColor(col); top_fill.setAlpha(90)
            bot_fill = QColor(col); bot_fill.setAlpha(0)
            grad = QLinearGradient(0, top, 0, top + plot_h)
            grad.setColorAt(0, top_fill); grad.setColorAt(1, bot_fill)
            p.setBrush(grad); p.setPen(Qt.PenStyle.NoPen)
            p.drawPath(area)

            # Line
            p.setPen(QPen(col, 2.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            line = QPainterPath()
            line.moveTo(cur_pts[0])
            for pt in cur_pts[1:]:
                line.lineTo(pt)
            p.drawPath(line)

            # Dots on each point
            p.setBrush(col); p.setPen(Qt.PenStyle.NoPen)
            for pt in cur_pts:
                p.drawEllipse(pt, 2.4, 2.4)

            # Hover marker
            if 0 <= self._hover_idx < len(cur_pts):
                hp = cur_pts[self._hover_idx]
                p.setPen(QPen(QColor(tk.t1), 1))
                p.setBrush(QColor(tk.card))
                p.drawEllipse(hp, 4.5, 4.5)

        # X-axis labels (up to 6 evenly spaced)
        p.setFont(QFont("Segoe UI", 8))
        p.setPen(QColor(tk.t4))
        step = max(1, len(self._cur) // 6)
        for i in range(0, len(self._cur), step):
            date, _ = self._cur[i]
            x = left + (plot_w * i / max(1, len(self._cur) - 1))
            p.drawText(QRectF(x - 30, h - bot + 8, 60, 14),
                       Qt.AlignmentFlag.AlignCenter,
                       date[5:])   # MM-DD

        p.end()
