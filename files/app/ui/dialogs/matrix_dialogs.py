"""
app/ui/dialogs/matrix_dialogs.py — Modal dialogs for matrix stock operations.

Used by every MatrixTab regardless of category.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QComboBox,
    QDialogButtonBox, QMessageBox,
)
from PyQt6.QtCore import Qt

from app.models.item import InventoryItem
from app.repositories.model_repo import ModelRepository
from app.core.theme import THEME
from app.core.i18n import t
from app.ui.dialogs.product_dialogs import QuantitySpin

_model_repo = ModelRepository()


# ── Stock IN / OUT / Set-Exact ─────────────────────────────────────────────────

class StockOpDialog(QDialog):
    """Stock IN / OUT / Set-Exact for one matrix cell."""

    def __init__(self, entry: InventoryItem, part_type_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{entry.model_name}  ·  {part_type_name}")
        self.setModal(True); self.setMinimumWidth(380)
        THEME.apply(self)
        tk  = THEME.tokens
        lay = QVBoxLayout(self); lay.setSpacing(14); lay.setContentsMargins(24, 24, 24, 20)

        # Header
        title = QLabel(f"{entry.model_name}  ·  {part_type_name}")
        title.setObjectName("dlg_header"); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        # Context line (surplus / deficit)
        needed = entry.min_stock - entry.stock
        if needed > 0:
            html = (f"Stock: <b>{entry.stock}</b>  │  "
                    f"{t('col_stamm_zahl')}: <b>{entry.min_stock}</b>  │  "
                    f"<span style='color:{tk.red}'>{t('disp_need_more', n=needed)}</span>")
        elif needed < 0:
            html = (f"Stock: <b>{entry.stock}</b>  │  "
                    f"{t('col_stamm_zahl')}: <b>{entry.min_stock}</b>  │  "
                    f"<span style='color:{tk.green}'>{t('disp_surplus', n=abs(needed))}</span>")
        else:
            html = (f"Stock: <b>{entry.stock}</b>  │  "
                    f"{t('col_stamm_zahl')}: <b>{entry.min_stock}</b>  │  "
                    f"<span style='color:{tk.yellow}'>{t('disp_tip_bb_zero')}</span>")
        info = QLabel(html); info.setTextFormat(Qt.TextFormat.RichText)
        info.setObjectName("card_meta_dim"); info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(info)

        # Operation toggle buttons
        self._op = "IN"
        op_row = QHBoxLayout(); op_row.setSpacing(6)
        self._btn_in  = QPushButton(t("disp_op_in"));  self._btn_in.setObjectName("btn_confirm_in")
        self._btn_out = QPushButton(t("disp_op_out")); self._btn_out.setObjectName("btn_confirm_out")
        self._btn_set = QPushButton(t("disp_op_set")); self._btn_set.setObjectName("btn_confirm_adj")
        for b in (self._btn_in, self._btn_out, self._btn_set):
            b.setCheckable(True); op_row.addWidget(b)
        self._btn_in.setChecked(True)
        self._btn_in.clicked.connect(lambda: self._set_op("IN"))
        self._btn_out.clicked.connect(lambda: self._set_op("OUT"))
        self._btn_set.clicked.connect(lambda: self._set_op("ADJUST"))
        lay.addLayout(op_row)

        # Quantity spin
        form = QFormLayout(); form.setSpacing(10)
        self._qty_lbl = QLabel(t("disp_qty_lbl"))
        self.qty_spin = QuantitySpin(0, 9999, max(1, needed) if needed > 0 else 1)
        form.addRow(self._qty_lbl, self.qty_spin); lay.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _set_op(self, op: str) -> None:
        self._op = op
        self._btn_in.setChecked(op == "IN")
        self._btn_out.setChecked(op == "OUT")
        self._btn_set.setChecked(op == "ADJUST")

    def result_data(self) -> tuple[str, int]:
        return self._op, self.qty_spin.value()


# ── Set Stamm-Zahl / min_stock ────────────────────────────────────────────────

class ThresholdDialog(QDialog):
    """Set the minimum stock threshold (Stamm-Zahl) for a matrix cell."""

    def __init__(self, model_name: str, part_type_name: str,
                 current: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{model_name}  ·  {part_type_name}")
        self.setModal(True); self.setMinimumWidth(300)
        THEME.apply(self)
        lay = QVBoxLayout(self); lay.setSpacing(12); lay.setContentsMargins(20, 20, 20, 16)

        title = QLabel(f"{model_name}  ·  {part_type_name}")
        title.setObjectName("dlg_header"); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        form = QFormLayout(); form.setSpacing(8)
        self._spin = QuantitySpin(0, 9999, current)
        form.addRow(t("lbl_stamm_zahl"), self._spin)
        lay.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def value(self) -> int:
        return self._spin.value()


# ── Record Inventur count ─────────────────────────────────────────────────────

class InventurDialog(QDialog):
    """Record a physical stock count (Inventur) for a matrix cell."""

    def __init__(self, model_name: str, part_type_name: str,
                 current_stock: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{model_name}  ·  {part_type_name}")
        self.setModal(True); self.setMinimumWidth(300)
        THEME.apply(self)
        lay = QVBoxLayout(self); lay.setSpacing(12); lay.setContentsMargins(20, 20, 20, 16)

        title = QLabel(f"{model_name}  ·  {part_type_name}")
        title.setObjectName("dlg_header"); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        form = QFormLayout(); form.setSpacing(8)
        self._spin = QuantitySpin(0, 9999, current_stock)
        form.addRow(t("col_inventur"), self._spin)
        lay.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def value(self) -> int:
        return self._spin.value()


# ── Add model ─────────────────────────────────────────────────────────────────

class AddModelDialog(QDialog):
    """Add a new phone model (brand + model name)."""

    def __init__(self, existing_brands: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("disp_add_model"))
        self.setModal(True); self.setMinimumWidth(340)
        THEME.apply(self)
        lay = QVBoxLayout(self); lay.setSpacing(12); lay.setContentsMargins(20, 20, 20, 16)

        form = QFormLayout(); form.setSpacing(10)

        self._brand_combo = QComboBox()
        self._brand_combo.setEditable(True)
        for b in existing_brands:
            self._brand_combo.addItem(b)
        self._brand_combo.setCurrentText("")

        from PyQt6.QtWidgets import QLineEdit
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(t("disp_model_ph"))

        form.addRow(t("disp_brand_lbl"), self._brand_combo)
        form.addRow(t("disp_model_lbl"), self._name_edit)
        lay.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._validate)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _validate(self) -> None:
        if not self._name_edit.text().strip():
            QMessageBox.warning(self, t("dlg_required_title"), t("disp_model_empty"))
            return
        if not self._brand_combo.currentText().strip():
            QMessageBox.warning(self, t("dlg_required_title"), t("disp_brand_empty"))
            return
        self.accept()

    def brand(self) -> str:
        return self._brand_combo.currentText().strip()

    def model_name(self) -> str:
        return self._name_edit.text().strip()
