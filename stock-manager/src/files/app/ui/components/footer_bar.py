"""
app/ui/components/footer_bar.py — 32px status footer bar.

Shows: status message, active-filter indicator, last-action timestamp,
app version, and DB connection status dot.
"""
from __future__ import annotations

from datetime import datetime

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QSizePolicy, QWidget,
)
from PyQt6.QtCore import QTimer

from app.core.i18n import t
from app.core.version import APP_VERSION


class FooterBar(QFrame):
    """32px footer: status | filter indicator · · · timestamp  v{ver}  ● connected."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("footer_bar")
        self.setFixedHeight(32)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._build()

    # ── Build ────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(12)

        self._status = QLabel(t("statusbar_ready"))
        self._status.setObjectName("footer_status")
        lay.addWidget(self._status)

        self._filter_lbl = QLabel()
        self._filter_lbl.setObjectName("footer_filter_indicator")
        self._filter_lbl.hide()
        lay.addWidget(self._filter_lbl)

        lay.addStretch()

        self._timestamp = QLabel()
        self._timestamp.setObjectName("footer_timestamp")
        lay.addWidget(self._timestamp)

        self._version = QLabel(f"v{APP_VERSION}")
        self._version.setObjectName("footer_version")
        lay.addWidget(self._version)

        self._sync = QLabel(f"●  {t('footer_connected')}")
        self._sync.setObjectName("footer_sync")
        lay.addWidget(self._sync)

    # ── Public API ───────────────────────────────────────────────────────────

    def show_status(self, msg: str, timeout: int = 0, level: str = "") -> None:
        """Display a status message, optionally reverting after *timeout* ms."""
        icon = {"ok": "✓ ", "warn": "⚠ ", "err": "✕ "}.get(level, "")
        self._status.setText(f"{icon}{msg}")
        obj = {
            "ok":   "footer_status_ok",
            "warn": "footer_status_warn",
            "err":  "footer_status_err",
        }.get(level, "footer_status")
        self._status.setObjectName(obj)
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)
        if timeout > 0:
            QTimer.singleShot(timeout, lambda: self.show_status(t("statusbar_ready")))
        self._timestamp.setText(datetime.now().strftime("%H:%M:%S"))

    def show_filter(self, text: str) -> None:
        """Show the filter indicator with *text* (e.g. '12 / 200')."""
        self._filter_lbl.setText(text)
        self._filter_lbl.show()

    def hide_filter(self) -> None:
        """Hide the filter indicator."""
        self._filter_lbl.hide()

    def retranslate(self) -> None:
        self._sync.setText(f"●  {t('footer_connected')}")
