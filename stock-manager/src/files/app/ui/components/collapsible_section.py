"""
app/ui/components/collapsible_section.py — Collapsible section widget.
"""
from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt


class CollapsibleSection(QWidget):
    """A section with a clickable header that shows/hides its content."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._expanded = True
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._header = QPushButton(f"  ▾  {title}")
        self._header.setObjectName("sidebar_section_toggle")
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.clicked.connect(self._toggle)
        lay.addWidget(self._header)

        self._content = QWidget()
        self._content_lay = QVBoxLayout(self._content)
        self._content_lay.setContentsMargins(0, 2, 0, 0)
        self._content_lay.setSpacing(2)
        lay.addWidget(self._content)

        self._title = title

    def add_widget(self, w: QWidget):
        self._content_lay.addWidget(w)

    def _toggle(self):
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        arrow = "▾" if self._expanded else "▸"
        self._header.setText(f"  {arrow}  {self._title}")

    def set_title(self, title: str):
        self._title = title
        arrow = "▾" if self._expanded else "▸"
        self._header.setText(f"  {arrow}  {title}")
