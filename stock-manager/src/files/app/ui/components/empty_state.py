"""app/ui/components/empty_state.py — Empty state placeholder component.

Centered icon + title + subtitle. Optional retry button for error tiles
(emits `retry_clicked` when pressed).
"""
from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from app.core.theme import THEME


class EmptyState(QWidget):
    """Empty state display with title, subtitle, and optional icon/retry."""

    retry_clicked = pyqtSignal()

    def __init__(
        self,
        title: str = "No items",
        subtitle: str = "Start by creating something",
        icon: str = "",
        with_retry: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.title = title
        self.subtitle = subtitle
        self._icon = icon
        self._with_retry = with_retry
        self._setup_ui()

    def _setup_ui(self) -> None:
        tk = THEME.tokens
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)

        layout.addStretch()

        if self._icon:
            self._icon_lbl = QLabel(self._icon)
            self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._icon_lbl.setFont(QFont("Segoe UI Emoji", 28))
            self._icon_lbl.setStyleSheet(f"color: {tk.t3};")
            layout.addWidget(self._icon_lbl)

        self._lbl_title = QLabel(self.title)
        self._lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_title.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {tk.t2};"
        )
        self._lbl_title.setWordWrap(True)
        layout.addWidget(self._lbl_title)

        self._lbl_subtitle = QLabel(self.subtitle)
        self._lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_subtitle.setStyleSheet(
            f"font-size: 11px; color: {tk.t4};"
        )
        self._lbl_subtitle.setWordWrap(True)
        layout.addWidget(self._lbl_subtitle)

        if self._with_retry:
            self._retry_btn = QPushButton("Retry")
            self._retry_btn.setObjectName("btn_secondary")
            self._retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._retry_btn.setFixedHeight(28)
            self._retry_btn.clicked.connect(self.retry_clicked.emit)
            layout.addWidget(self._retry_btn, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()
        self.setLayout(layout)

    def set_text(self, title: str, subtitle: str = "") -> None:
        self._lbl_title.setText(title)
        if subtitle:
            self._lbl_subtitle.setText(subtitle)
