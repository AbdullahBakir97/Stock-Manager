"""
app/ui/components/sync_indicator.py — Compact cloud sync status widget.

Shows a colored icon + short status text in the footer bar. Clicking triggers
an immediate manual sync. States: disabled (grey), syncing (amber), synced
(green), error (red).
"""
from __future__ import annotations

from datetime import datetime

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QMouseEvent


_ICONS = {
    "disabled": "○",
    "syncing":  "↻",
    "synced":   "●",
    "error":    "●",
}

_COLORS = {
    "disabled": "#888888",
    "syncing":  "#F5A623",
    "synced":   "#27AE60",
    "error":    "#E74C3C",
}


class SyncIndicator(QWidget):
    """Small cloud sync status pill shown in the footer bar.

    Click to trigger an immediate sync (when configured).
    """

    def __init__(self, sync_service, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._svc = sync_service

        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 0, 4, 0)
        lay.setSpacing(4)

        self._icon_lbl = QLabel()
        self._icon_lbl.setObjectName("sync_indicator_icon")
        lay.addWidget(self._icon_lbl)

        self._text_lbl = QLabel()
        self._text_lbl.setObjectName("sync_indicator_text")
        lay.addWidget(self._text_lbl)

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # Connect service signals
        self._svc.sync_started.connect(self._on_syncing)
        self._svc.sync_completed.connect(self._on_synced)
        self._svc.sync_failed.connect(self._on_error)

        self._refresh()

    # ── Public ────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Re-read service state and update display. Call after config changes."""
        self._refresh()

    # ── Slots ─────────────────────────────────────────────────────────────────

    @pyqtSlot()
    def _on_syncing(self) -> None:
        self._set_state("syncing", "Syncing…")

    @pyqtSlot(str)
    def _on_synced(self, timestamp: str) -> None:
        try:
            t = datetime.fromisoformat(timestamp).strftime("%H:%M")
            self._set_state("synced", f"Synced {t}")
        except Exception:
            self._set_state("synced", "Synced")

    @pyqtSlot(str)
    def _on_error(self, msg: str) -> None:
        self._set_state("error", "Sync error")
        self.setToolTip(f"Last error: {msg}\nClick to retry")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        if not self._svc.is_configured:
            self._set_state("disabled", "Cloud sync off")
            self.setCursor(Qt.CursorShape.ArrowCursor)
        elif self._svc.last_sync_time:
            t = self._svc.last_sync_time.strftime("%H:%M")
            self._set_state("synced", f"Synced {t}")
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self._set_state("synced", "Cloud sync on")
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _set_state(self, state: str, text: str) -> None:
        icon  = _ICONS.get(state, "○")
        color = _COLORS.get(state, "#888888")
        self._icon_lbl.setText(icon)
        self._icon_lbl.setStyleSheet(f"color: {color}; font-size: 10px;")
        self._text_lbl.setText(text)
        self._text_lbl.setStyleSheet(f"color: {color};")
        if state not in ("disabled", "error"):
            self.setToolTip(t("sync_tip_click"))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._svc.is_configured:
            self._svc.sync_now()
        super().mousePressEvent(event)
