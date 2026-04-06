"""
app/ui/dialogs/admin/color_picker_widget.py — Colored button that opens QColorDialog.
"""
from __future__ import annotations

from PyQt6.QtWidgets import QPushButton, QColorDialog
from PyQt6.QtGui import QColor
from PyQt6.QtCore import pyqtSignal

from app.core.theme import THEME


class ColorPickerWidget(QPushButton):
    """A QPushButton that shows its hex color and opens QColorDialog on click."""

    color_changed = pyqtSignal(str)   # emits hex string like "#FF5A52"

    def __init__(self, hex_color: str = "#4A9EFF", parent=None):
        super().__init__(parent)
        self._hex = hex_color
        self._apply_style()
        self.clicked.connect(self._pick)
        self.setMinimumWidth(100)
        self.setMinimumHeight(36)

    def hex_color(self) -> str:
        return self._hex

    def set_color(self, hex_color: str) -> None:
        self._hex = hex_color
        self._apply_style()

    def _pick(self) -> None:
        color = QColorDialog.getColor(
            QColor(self._hex), self, options=QColorDialog.ColorDialogOption.ShowAlphaChannel
        )
        if color.isValid():
            self._hex = color.name()
            self._apply_style()
            self.color_changed.emit(self._hex)

    def _apply_style(self) -> None:
        self.setText(self._hex)
        self.setStyleSheet(
            f"background-color: {self._hex}; color: {self._contrast_color()}; "
            f"border-radius: 6px; font-weight: bold; padding: 4px 8px;"
        )

    def _contrast_color(self) -> str:
        c = QColor(self._hex)
        lum = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
        return "#000000" if lum > 140 else "#FFFFFF"
