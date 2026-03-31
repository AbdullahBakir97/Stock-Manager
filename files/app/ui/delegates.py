"""
UI delegates for table rendering.
"""
from PyQt6.QtWidgets import QStyledItemDelegate, QStyle
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtCore import Qt

from app.core.theme import THEME, qc


class AlternatingRowDelegate(QStyledItemDelegate):
    """Delegate for alternating row colors like Excel."""
    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw alternating row background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, qc(THEME.tokens.blue, 0x40))
        elif index.row() % 2 == 0:
            painter.fillRect(option.rect, QColor(THEME.tokens.card))
        else:
            painter.fillRect(option.rect, QColor(THEME.tokens.card2))
        
        # Draw text or "—" for empty values
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        if text:
            painter.setPen(QColor(THEME.tokens.t1))
            painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, text)
        else:
            # Draw "—" in muted color for empty cells
            painter.setPen(QColor(THEME.tokens.t4))
            painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, "—")
        
        painter.restore()
