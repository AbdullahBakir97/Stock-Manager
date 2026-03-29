"""app/ui/tabs/base_tab.py — Abstract base class for all inventory tabs."""
from __future__ import annotations

from abc import abstractmethod
from PyQt6.QtWidgets import QWidget


class BaseTab(QWidget):
    """All tab widgets must implement refresh() and retranslate()."""

    @abstractmethod
    def refresh(self) -> None: ...

    @abstractmethod
    def retranslate(self) -> None: ...
