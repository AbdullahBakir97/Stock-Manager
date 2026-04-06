"""app/ui/components/empty_state.py — Empty state placeholder component."""
from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.core.theme import THEME


class EmptyState(QWidget):
    """Empty state display with title and subtitle."""

    def __init__(
        self,
        title: str = "No items",
        subtitle: str = "Start by creating something",
        parent: QWidget | None = None,
    ) -> None:
        """Initialize empty state."""
        super().__init__(parent)
        self.title = title
        self.subtitle = subtitle
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(32, 64, 32, 64)
        layout.setSpacing(12)

        # Title
        lbl_title = QLabel(self.title)
        lbl_title.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {THEME.tokens.t1}; text-align: center;"
        )
        lbl_title.setWordWrap(True)

        # Subtitle
        lbl_subtitle = QLabel(self.subtitle)
        lbl_subtitle.setStyleSheet(
            f"font-size: 12px; color: {THEME.tokens.t2}; text-align: center;"
        )
        lbl_subtitle.setWordWrap(True)

        layout.addStretch()
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_subtitle)
        layout.addStretch()

        self.setLayout(layout)
