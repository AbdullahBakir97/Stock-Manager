"""app/ui/tabs/base_tab.py — Abstract base class for all inventory tabs."""
from __future__ import annotations

from abc import abstractmethod
from PyQt6.QtWidgets import QWidget, QSizePolicy

from app.ui.workers.async_refresh import AsyncRefreshMixin


class BaseTab(AsyncRefreshMixin, QWidget):
    """All tab widgets must implement refresh() and retranslate().

    Mixes in :class:`AsyncRefreshMixin` so any subclass can do:

        self.async_refresh(fetch=..., apply=..., key_suffix="items")

    without extra imports.  Subclasses should set a unique
    ``POOL_KEY_PREFIX`` class attribute so their pool keys don't collide
    with other tabs.
    """

    #: Overridden by subclasses with a unique prefix (e.g. "matrix_displays").
    POOL_KEY_PREFIX: str = "base_tab"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    @abstractmethod
    def refresh(self) -> None: ...

    @abstractmethod
    def retranslate(self) -> None: ...
