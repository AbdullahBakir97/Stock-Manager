"""
app/ui/delegates.py — UI delegates for table rendering.
"""
from __future__ import annotations

from PyQt6.QtWidgets import QStyledItemDelegate, QStyle, QStyleOptionViewItem
from PyQt6.QtGui import QPainter, QColor, QFont, QPainterPath
from PyQt6.QtCore import Qt, QSize, QModelIndex, QRectF

from app.core.theme import THEME, qc
from app.core.colors import PALETTE
from app.core.i18n import t, color_t


# ── Alternating Row Delegate ──────────────────────────────────────────────────

class AlternatingRowDelegate(QStyledItemDelegate):
    """Delegate for alternating row colors like Excel."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, qc(THEME.tokens.blue, 0x40))
        elif index.row() % 2 == 0:
            painter.fillRect(option.rect, QColor(THEME.tokens.card))
        else:
            painter.fillRect(option.rect, QColor(THEME.tokens.card2))

        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        if text:
            painter.setPen(QColor(THEME.tokens.t1))
            painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, text)
        else:
            painter.setPen(QColor(THEME.tokens.t4))
            painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, "—")

        painter.restore()


# ── Color Swatch Delegate ────────────────────────────────────────────────────

class ColorSwatchDelegate(QStyledItemDelegate):
    """Renders a color circle + translated color name."""

    def paint(self, painter: QPainter, opt: QStyleOptionViewItem, idx: QModelIndex):
        o = QStyleOptionViewItem(opt); self.initStyleOption(o, idx)
        painter.save(); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tk = THEME.tokens

        if o.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(o.rect, qc(tk.blue, 0x40))
        elif idx.row() % 2 == 0:
            painter.fillRect(o.rect, QColor(tk.card))
        else:
            painter.fillRect(o.rect, QColor(tk.card2))

        hx      = idx.data(Qt.ItemDataRole.UserRole)
        en_name = idx.data(Qt.ItemDataRole.DisplayRole) or ""
        name    = color_t(en_name)
        r       = o.rect

        if hx:
            R = 9; cx = r.left() + 28; cy = r.center().y()
            painter.setBrush(QColor(tk.border2)); painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(cx-R-1, cy-R-1, 2*R+2, 2*R+2)
            painter.setBrush(QColor(hx))
            painter.drawEllipse(cx-R, cy-R, 2*R, 2*R)
            tr = r.adjusted(48, 0, -6, 0)
            painter.setPen(QColor(tk.t1)); painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(tr, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, name)
        else:
            painter.setPen(QColor(tk.t3))
            painter.drawText(r, Qt.AlignmentFlag.AlignCenter, name)

        painter.restore()

    def sizeHint(self, o, i):
        return QSize(super().sizeHint(o, i).width(), 44)


# ── Status Badge Delegate ────────────────────────────────────────────────────

class StatusBadgeDelegate(QStyledItemDelegate):
    """Renders a colored pill-shaped status badge."""

    def paint(self, painter: QPainter, opt: QStyleOptionViewItem, idx: QModelIndex):
        o = QStyleOptionViewItem(opt); self.initStyleOption(o, idx)
        painter.save(); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tk = THEME.tokens

        if o.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(o.rect, qc(tk.blue, 0x40))
        elif idx.row() % 2 == 0:
            painter.fillRect(o.rect, QColor(tk.card))
        else:
            painter.fillRect(o.rect, QColor(tk.card2))

        key  = idx.data(Qt.ItemDataRole.DisplayRole) or ""
        text = {
            "OK": t("status_ok_lbl"), "LOW": t("status_low_lbl"),
            "CRITICAL": t("status_critical_lbl"), "OUT": t("status_out_lbl"),
        }.get(key, key)

        pal = {
            "OK":       (tk.green,  qc(tk.green,  0x28)),
            "LOW":      (tk.yellow, qc(tk.yellow, 0x30)),
            "CRITICAL": (tk.orange, qc(tk.orange, 0x28)),
            "OUT":      (tk.red,    qc(tk.red,    0x28)),
        }
        pair = pal.get(key)
        fg   = pair[0] if pair else tk.t3
        bg_c = pair[1] if pair else QColor(tk.border)

        r  = o.rect
        f  = QFont("Segoe UI", 8, QFont.Weight.Bold); painter.setFont(f)
        fm = painter.fontMetrics(); tw = fm.horizontalAdvance(text)
        ph, pv = 12, 5; pw = tw + ph*2; phh = fm.height() + pv*2
        px = r.left() + (r.width() - pw)//2; py = r.top() + (r.height() - phh)//2

        path = QPainterPath()
        path.addRoundedRect(QRectF(px, py, pw, phh), phh/2, phh/2)
        painter.setBrush(bg_c); painter.setPen(Qt.PenStyle.NoPen); painter.drawPath(path)
        painter.setPen(QColor(fg))
        painter.drawText(px, py, pw, phh, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()

    def sizeHint(self, o, i):
        return QSize(super().sizeHint(o, i).width(), 44)


# ── Color Dot Delegate ───────────────────────────────────────────────────────

class ColorDotDelegate(QStyledItemDelegate):
    """Renders a simple color dot from the palette."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        color_name = index.data(Qt.ItemDataRole.DisplayRole)
        if not color_name or color_name == "—":
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            if option.state & QStyle.StateFlag.State_Selected:
                painter.fillRect(option.rect, qc(THEME.tokens.blue, 0x40))
            elif index.row() % 2 == 0:
                painter.fillRect(option.rect, QColor(THEME.tokens.card))
            else:
                painter.fillRect(option.rect, QColor(THEME.tokens.card2))
            painter.setPen(QColor(THEME.tokens.t4))
            painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, "—")
            painter.restore()
            return

        hex_color = PALETTE.get(color_name, color_name)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tk = THEME.tokens

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, qc(tk.blue, 0x40))
        elif index.row() % 2 == 0:
            painter.fillRect(option.rect, QColor(tk.card))
        else:
            painter.fillRect(option.rect, QColor(tk.card2))

        rect = option.rect
        R = 9; cx = rect.center().x(); cy = rect.center().y()
        painter.setBrush(QColor(tk.border2)); painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx-R-1, cy-R-1, 2*R+2, 2*R+2)
        painter.setBrush(QColor(hex_color))
        painter.drawEllipse(cx-R, cy-R, 2*R, 2*R)
        painter.restore()


# ── Difference Delegate ──────────────────────────────────────────────────────

class DifferenceDelegate(QStyledItemDelegate):
    """Renders stock difference with color-coded text."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        painter.save()
        tk = THEME.tokens

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, qc(tk.blue, 0x40))
        elif index.row() % 2 == 0:
            painter.fillRect(option.rect, QColor(tk.card))
        else:
            painter.fillRect(option.rect, QColor(tk.card2))

        item = self.parent().item(index.row(), index.column())
        if item:
            text = item.text()
            if text and text != "—":
                painter.setPen(item.foreground().color())
                font = QFont("Segoe UI", 10, QFont.Weight.Bold)
                painter.setFont(font)
                painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, text)
            else:
                painter.setPen(QColor(THEME.tokens.t4))
                painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, "—")
        painter.restore()
