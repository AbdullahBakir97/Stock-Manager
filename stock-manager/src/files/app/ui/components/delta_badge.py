"""app/ui/components/delta_badge.py — Small ▲/▼ percentage pill.

Used inside KPI tiles. Green when value went up, red when down, grey when
flat. Set via `set_delta(pct: float, direction: str)`.
"""
from __future__ import annotations

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt

from app.core.theme import THEME


class DeltaBadge(QLabel):
    """Tiny pill with an arrow + percentage."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("delta_flat")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("—")
        self._apply_style("flat")

    def set_delta(self, pct: float, direction: str = "") -> None:
        if direction not in ("up", "down", "flat"):
            direction = "up" if pct > 0 else ("down" if pct < 0 else "flat")
        if direction == "flat":
            self.setText("—")
        else:
            arrow = "▲" if direction == "up" else "▼"
            # Cap very large deltas for display sanity
            pct_s = f"{abs(pct):.1f}%" if abs(pct) < 1000 else "999%+"
            self.setText(f"{arrow}  {pct_s}")
        self._apply_style(direction)

    def _apply_style(self, direction: str) -> None:
        """Rebuild inline style so the colour updates even without a QSS refresh."""
        tk = THEME.tokens
        if direction == "up":
            fg = tk.green
            bg_rgba = self._rgba(tk.green, 32)
        elif direction == "down":
            fg = tk.red
            bg_rgba = self._rgba(tk.red, 32)
        else:
            fg = tk.t3
            bg_rgba = self._rgba(tk.t4, 24)
        self.setStyleSheet(
            f"background: {bg_rgba}; color: {fg};"
            f" font-size: 10px; font-weight: 700;"
            f" border-radius: 8px; padding: 2px 8px;"
        )
        self.setObjectName(f"delta_{direction}")

    @staticmethod
    def _rgba(hex6: str, alpha: int) -> str:
        h = hex6.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"
