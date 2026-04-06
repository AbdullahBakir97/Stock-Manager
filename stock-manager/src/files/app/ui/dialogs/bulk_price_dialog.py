"""
app/ui/dialogs/bulk_price_dialog.py — Bulk price update dialog.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDoubleSpinBox, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt

from app.core.i18n import t
from app.core.theme import THEME


class BulkPriceDialog(QDialog):
    """Modal dialog for bulk updating prices of selected items."""

    def __init__(self, parent=None, count: int = 0):
        super().__init__(parent)
        self.setWindowTitle(t("bulk_price_title"))
        self.setMinimumWidth(380)
        self._result: dict | None = None
        self._build(count)
        THEME.apply(self)

    def _build(self, count: int) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        # Header
        hdr = QLabel(t("bulk_price_title"))
        hdr.setObjectName("dlg_header")
        lay.addWidget(hdr)

        info = QLabel(t("bulk_price_confirm", n=count))
        info.setObjectName("card_meta")
        info.setWordWrap(True)
        lay.addWidget(info)

        # Mode selector
        mode_row = QHBoxLayout()
        mode_lbl = QLabel(t("bulk_price_mode"))
        mode_lbl.setObjectName("dlg_label")
        self._mode = QComboBox()
        self._mode.addItems([
            t("bulk_price_set"),
            t("bulk_price_increase_pct"),
            t("bulk_price_decrease_pct"),
        ])
        mode_row.addWidget(mode_lbl)
        mode_row.addWidget(self._mode, 1)
        lay.addLayout(mode_row)

        # Value input
        val_row = QHBoxLayout()
        val_lbl = QLabel(t("bulk_price_value"))
        val_lbl.setObjectName("dlg_label")
        self._value = QDoubleSpinBox()
        self._value.setRange(0, 999999.99)
        self._value.setDecimals(2)
        self._value.setSingleStep(0.50)
        self._value.setValue(0)
        val_row.addWidget(val_lbl)
        val_row.addWidget(self._value, 1)
        lay.addLayout(val_row)

        # Buttons
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("dlg_separator")
        lay.addWidget(sep)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton(t("btn_cancel"))
        cancel.setObjectName("btn_secondary")
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)

        apply_btn = QPushButton(t("bulk_price_title"))
        apply_btn.setObjectName("btn_primary")
        apply_btn.clicked.connect(self._on_apply)
        btn_row.addWidget(apply_btn)
        lay.addLayout(btn_row)

    def _on_apply(self) -> None:
        mode_idx = self._mode.currentIndex()
        val = self._value.value()
        # mode: 0=set, 1=increase%, 2=decrease%
        self._result = {"mode": mode_idx, "value": val}
        self.accept()

    def get_result(self) -> dict | None:
        return self._result
