"""app/services/cost_visibility.py — Session-local toggle for cost (valuation)
columns + cost-based card metrics in matrix tabs.

Hidden by default on every app start for privacy / professionalism. Can be
flipped only after entering ShopConfig.admin_pin (if one is configured).

The matrix UI subscribes to `COST_VIS.changed` and re-applies column
visibility + rebuilds the top info cards (flipping between sell-valuation
and cost-valuation totals).
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal


class _CostVisibility(QObject):
    """Session-local flag controlling cost-column + cost-card-metric visibility."""

    # Emitted whenever `visible` toggles. All subscribers re-render.
    changed = pyqtSignal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._visible: bool = False  # always hidden on fresh session

    @property
    def visible(self) -> bool:
        return self._visible

    def set_visible(self, v: bool) -> None:
        v = bool(v)
        if v == self._visible:
            return
        self._visible = v
        self.changed.emit(v)

    def toggle(self) -> bool:
        """Flip visibility and return the new state."""
        self.set_visible(not self._visible)
        return self._visible


# Module-level singleton — import and use directly.
COST_VIS = _CostVisibility()
