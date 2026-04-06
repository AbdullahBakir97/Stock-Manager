"""app/ui/dialogs/dialog_base.py — Base dialog class for consistent styling."""
from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QWidget


class DialogBase(QDialog):
    """Base dialog with consistent theming and result handling."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize base dialog."""
        super().__init__(parent)
        self.result = None
        self.setWindowTitle("Dialog")
