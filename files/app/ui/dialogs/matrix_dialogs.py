"""
app/ui/dialogs/matrix_dialogs.py — Modal dialogs for matrix stock operations.

Used by every MatrixTab regardless of category.
Modern design with consistent spacing and close buttons.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QComboBox, QLineEdit,
    QDialogButtonBox, QMessageBox,
)
from PyQt6.QtCore import Qt

from app.models.item import InventoryItem
from app.repositories.model_repo import ModelRepository
from app.core.theme import THEME
from app.core.i18n import t
from app.ui.dialogs.product_dialogs import QuantitySpin

_model_repo = ModelRepository()


# ── Dialog base ──────────────────────────────────────────────────────────────

def _apply(dlg: QDialog) -> None:
    THEME.apply(dlg)


# ── Stock IN / OUT / Set-Exact ─────────────────────────────────────────────────

class StockOpDialog(QDialog):
    """Stock IN / OUT / Set-Exact for one matrix cell."""

    def __init__(self, entry: InventoryItem, part_type_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{entry.model_name}  ·  {part_type_name}")
        self.setModal(True); self.setMinimumWidth(400)
        _apply(self)
        tk  = THEME.tokens
        lay = QVBoxLayout(self); lay.setSpacing(16); lay.setContentsMargins(24, 24, 24, 20)

        # Header with close
        hdr_row = QHBoxLayout()
        title = QLabel(f"{entry.model_name}  ·  {part_type_name}")
        title.setObjectName("dlg_header")
        close_btn = QPushButton("✕"); close_btn.setObjectName("btn_ghost")
        close_btn.setFixedSize(32, 32); close_btn.clicked.connect(self.reject)
        hdr_row.addWidget(title); hdr_row.addStretch(); hdr_row.addWidget(close_btn)
        lay.addLayout(hdr_row)

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
        form = QFormLayout(); form.setSpacing(12)
        self._qty_lbl = QLabel(t("disp_qty_lbl"))
        self.qty_spin = QuantitySpin(0, 9999, max(1, needed) if needed > 0 else 1)
        form.addRow(self._qty_lbl, self.qty_spin); lay.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        cancel = QPushButton(t("op_cancel")); cancel.setObjectName("btn_ghost")
        cancel.setMinimumHeight(40); cancel.clicked.connect(self.reject)
        ok = QPushButton("OK"); ok.setObjectName("btn_primary")
        ok.setMinimumHeight(40); ok.clicked.connect(self.accept)
        btn_row.addStretch(); btn_row.addWidget(cancel); btn_row.addWidget(ok)
        lay.addLayout(btn_row)

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
        self.setModal(True); self.setMinimumWidth(320)
        _apply(self)
        lay = QVBoxLayout(self); lay.setSpacing(16); lay.setContentsMargins(24, 24, 24, 20)

        # Header with close
        hdr_row = QHBoxLayout()
        title = QLabel(f"{model_name}  ·  {part_type_name}")
        title.setObjectName("dlg_header")
        close_btn = QPushButton("✕"); close_btn.setObjectName("btn_ghost")
        close_btn.setFixedSize(32, 32); close_btn.clicked.connect(self.reject)
        hdr_row.addWidget(title); hdr_row.addStretch(); hdr_row.addWidget(close_btn)
        lay.addLayout(hdr_row)

        hint = QLabel(t("disp_stamm_hint"))
        hint.setObjectName("section_caption")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        form = QFormLayout(); form.setSpacing(12)
        self._spin = QuantitySpin(0, 9999, current)
        form.addRow(t("lbl_stamm_zahl"), self._spin)
        lay.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        cancel = QPushButton(t("op_cancel")); cancel.setObjectName("btn_ghost")
        cancel.setMinimumHeight(40); cancel.clicked.connect(self.reject)
        ok = QPushButton("OK"); ok.setObjectName("btn_primary")
        ok.setMinimumHeight(40); ok.clicked.connect(self.accept)
        btn_row.addStretch(); btn_row.addWidget(cancel); btn_row.addWidget(ok)
        lay.addLayout(btn_row)

    def value(self) -> int:
        return self._spin.value()


# ── Record Order amount (was Inventur) ────────────────────────────────────────

class InventurDialog(QDialog):
    """Record order amount for a matrix cell."""

    def __init__(self, model_name: str, part_type_name: str,
                 current_stock: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{model_name}  ·  {part_type_name}")
        self.setModal(True); self.setMinimumWidth(320)
        _apply(self)
        lay = QVBoxLayout(self); lay.setSpacing(16); lay.setContentsMargins(24, 24, 24, 20)

        # Header with close
        hdr_row = QHBoxLayout()
        title = QLabel(f"{model_name}  ·  {part_type_name}")
        title.setObjectName("dlg_header")
        close_btn = QPushButton("✕"); close_btn.setObjectName("btn_ghost")
        close_btn.setFixedSize(32, 32); close_btn.clicked.connect(self.reject)
        hdr_row.addWidget(title); hdr_row.addStretch(); hdr_row.addWidget(close_btn)
        lay.addLayout(hdr_row)

        hint = QLabel(t("disp_order_hint"))
        hint.setObjectName("section_caption")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        sys_lbl = QLabel(t("disp_sys_stock", n=current_stock))
        sys_lbl.setObjectName("card_meta")
        lay.addWidget(sys_lbl)

        form = QFormLayout(); form.setSpacing(12)
        self._spin = QuantitySpin(0, 9999, current_stock)
        form.addRow(t("col_inventur"), self._spin)
        lay.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        cancel = QPushButton(t("op_cancel")); cancel.setObjectName("btn_ghost")
        cancel.setMinimumHeight(40); cancel.clicked.connect(self.reject)
        ok = QPushButton("OK"); ok.setObjectName("btn_primary")
        ok.setMinimumHeight(40); ok.clicked.connect(self.accept)
        btn_row.addStretch(); btn_row.addWidget(cancel); btn_row.addWidget(ok)
        lay.addLayout(btn_row)

    def value(self) -> int:
        return self._spin.value()


# ── Add model ─────────────────────────────────────────────────────────────────

class AddModelDialog(QDialog):
    """Add a new phone model (brand + model name)."""

    def __init__(self, existing_brands: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("disp_dlg_add_model"))
        self.setModal(True); self.setMinimumWidth(380)
        _apply(self)
        lay = QVBoxLayout(self); lay.setSpacing(16); lay.setContentsMargins(24, 24, 24, 20)

        # Header with close
        hdr_row = QHBoxLayout()
        title = QLabel(t("disp_dlg_add_model"))
        title.setObjectName("dlg_header")
        close_btn = QPushButton("✕"); close_btn.setObjectName("btn_ghost")
        close_btn.setFixedSize(32, 32); close_btn.clicked.connect(self.reject)
        hdr_row.addWidget(title); hdr_row.addStretch(); hdr_row.addWidget(close_btn)
        lay.addLayout(hdr_row)

        form = QFormLayout(); form.setSpacing(12)

        self._brand_combo = QComboBox()
        self._brand_combo.setEditable(True)
        for b in existing_brands:
            self._brand_combo.addItem(b)
        self._brand_combo.setCurrentText("")

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(t("disp_ph_model"))
        self._name_edit.setMinimumHeight(38)

        form.addRow(t("disp_lbl_brand"), self._brand_combo)
        form.addRow(t("disp_lbl_model_name"), self._name_edit)
        lay.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        cancel = QPushButton(t("op_cancel")); cancel.setObjectName("btn_ghost")
        cancel.setMinimumHeight(40); cancel.clicked.connect(self.reject)
        save = QPushButton(t("disp_save_model")); save.setObjectName("btn_primary")
        save.setMinimumHeight(40); save.clicked.connect(self._validate)
        btn_row.addStretch(); btn_row.addWidget(cancel); btn_row.addWidget(save)
        lay.addLayout(btn_row)

    def _validate(self) -> None:
        if not self._name_edit.text().strip():
            QMessageBox.warning(self, t("dlg_required_title"), t("disp_model_empty"))
            return
        if not self._brand_combo.currentText().strip():
            QMessageBox.warning(self, t("dlg_required_title"), t("disp_model_empty"))
            return
        self.accept()

    def brand(self) -> str:
        return self._brand_combo.currentText().strip()

    def model_name(self) -> str:
        return self._name_edit.text().strip()
