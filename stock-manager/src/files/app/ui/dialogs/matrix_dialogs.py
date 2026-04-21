"""
app/ui/dialogs/matrix_dialogs.py — Modal dialogs for matrix stock operations.

Each dialog shows the item's barcode and allows editing it inline.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QComboBox, QLineEdit,
    QDialogButtonBox, QMessageBox, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.models.item import InventoryItem
from app.repositories.model_repo import ModelRepository
from app.repositories.item_repo import ItemRepository
from app.core.theme import THEME
from app.core.i18n import t
from app.ui.dialogs.product_dialogs import QuantitySpin

_model_repo = ModelRepository()
_item_repo  = ItemRepository()

_FONT_MONO = QFont("JetBrains Mono", 10)
_FONT_MONO.setStyleHint(QFont.StyleHint.Monospace)


def _apply(dlg: QDialog) -> None:
    THEME.apply(dlg)


class _BarcodeEdit(QLineEdit):
    """QLineEdit that swallows Enter/Return so barcode scanners don't close the dialog."""
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            event.accept()  # eat the Enter key — don't propagate to dialog
            return
        super().keyPressEvent(event)


def _barcode_row(entry: InventoryItem, layout: QVBoxLayout) -> QLineEdit:
    """Add a barcode display/edit row to a dialog. Returns the QLineEdit."""
    bc_frame = QFrame()
    bc_frame.setObjectName("op_card")
    bc_lay = QHBoxLayout(bc_frame)
    bc_lay.setContentsMargins(12, 8, 12, 8)
    bc_lay.setSpacing(8)

    bc_label = QLabel(t("dlg_lbl_barcode"))
    bc_label.setObjectName("card_meta_dim")
    bc_lay.addWidget(bc_label)

    bc_edit = _BarcodeEdit(entry.barcode or "")
    bc_edit.setPlaceholderText("Scan or type barcode…")
    bc_edit.setFont(_FONT_MONO)
    bc_edit.setMinimumHeight(32)
    bc_lay.addWidget(bc_edit, 1)

    layout.addWidget(bc_frame)
    return bc_edit


def _save_barcode(item_id: int, bc_edit: QLineEdit, parent: QDialog) -> None:
    """Save barcode from edit field if it changed."""
    new_bc = bc_edit.text().strip() or None
    try:
        _item_repo.update_barcode(item_id, new_bc)
    except Exception as e:
        if "UNIQUE" in str(e):
            QMessageBox.warning(parent, t("barcode_assign_title"), t("barcode_duplicate"))
        # Don't block the dialog from closing for barcode errors


# ── Stock IN / OUT / Set-Exact ─────────────────────────────────────────────────

class StockOpDialog(QDialog):
    """Stock IN / OUT / Set-Exact for one matrix cell, with inline barcode edit."""

    def __init__(self, entry: InventoryItem, part_type_name: str, parent=None):
        super().__init__(parent)
        self._entry = entry
        self.setWindowTitle(f"{entry.model_name}  ·  {part_type_name}")
        self.setModal(True); self.setMinimumWidth(420)
        _apply(self)
        tk = THEME.tokens
        lay = QVBoxLayout(self); lay.setSpacing(14); lay.setContentsMargins(24, 24, 24, 20)

        # Header
        hdr_row = QHBoxLayout()
        title = QLabel(f"{entry.model_name}  ·  {part_type_name}")
        title.setObjectName("dlg_header")
        close_btn = QPushButton("×"); close_btn.setObjectName("btn_close_x")
        close_btn.setFixedSize(32, 32); close_btn.clicked.connect(self.reject)
        hdr_row.addWidget(title); hdr_row.addStretch(); hdr_row.addWidget(close_btn)
        lay.addLayout(hdr_row)

        # Context line
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

        # Barcode field
        self._bc_edit = _barcode_row(entry, lay)

        # Operation toggle
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

        # Quantity — always start at 0 so the user just types the new
        # amount. The inner QLineEdit is auto-focused + all-selected on
        # show, so typing replaces the 0 with no extra click.
        form = QFormLayout(); form.setSpacing(12)
        self.qty_spin = QuantitySpin(0, 9999, 0)
        form.addRow(t("disp_qty_lbl"), self.qty_spin)
        lay.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        cancel = QPushButton(t("op_cancel")); cancel.setObjectName("btn_ghost")
        cancel.setMinimumHeight(40); cancel.clicked.connect(self.reject)
        ok = QPushButton("OK"); ok.setObjectName("btn_primary")
        ok.setMinimumHeight(40); ok.clicked.connect(self._on_accept)
        btn_row.addStretch(); btn_row.addWidget(cancel); btn_row.addWidget(ok)
        lay.addLayout(btn_row)

    def _set_op(self, op: str) -> None:
        self._op = op
        self._btn_in.setChecked(op == "IN")
        self._btn_out.setChecked(op == "OUT")
        self._btn_set.setChecked(op == "ADJUST")

    def _on_accept(self):
        _save_barcode(self._entry.id, self._bc_edit, self)
        self.accept()

    def result_data(self) -> tuple[str, int]:
        return self._op, self.qty_spin.value()


# ── Set Stamm-Zahl / min_stock ────────────────────────────────────────────────

class ThresholdDialog(QDialog):
    """Set min stock threshold, with inline barcode edit."""

    def __init__(self, model_name: str, part_type_name: str,
                 current: int, parent=None, item_id: int = 0):
        super().__init__(parent)
        self._item_id = item_id
        self.setWindowTitle(f"{model_name}  ·  {part_type_name}")
        self.setModal(True); self.setMinimumWidth(340)
        _apply(self)
        lay = QVBoxLayout(self); lay.setSpacing(14); lay.setContentsMargins(24, 24, 24, 20)

        # Header
        hdr_row = QHBoxLayout()
        title = QLabel(f"{model_name}  ·  {part_type_name}")
        title.setObjectName("dlg_header")
        close_btn = QPushButton("×"); close_btn.setObjectName("btn_close_x")
        close_btn.setFixedSize(32, 32); close_btn.clicked.connect(self.reject)
        hdr_row.addWidget(title); hdr_row.addStretch(); hdr_row.addWidget(close_btn)
        lay.addLayout(hdr_row)

        hint = QLabel(t("disp_stamm_hint"))
        hint.setObjectName("section_caption"); hint.setWordWrap(True)
        lay.addWidget(hint)

        # Barcode field (if item_id provided)
        self._bc_edit = None
        if item_id:
            item = _item_repo.get_by_id(item_id)
            if item:
                self._bc_edit = _barcode_row(item, lay)

        form = QFormLayout(); form.setSpacing(12)
        # Always open at 0 — user types the new value immediately.
        # Current value is shown in the dialog's info/context row, not
        # pre-filled here (would need an extra click to clear).
        self._spin = QuantitySpin(0, 9999, 0)
        form.addRow(t("lbl_stamm_zahl"), self._spin)
        lay.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        cancel = QPushButton(t("op_cancel")); cancel.setObjectName("btn_ghost")
        cancel.setMinimumHeight(40); cancel.clicked.connect(self.reject)
        ok = QPushButton("OK"); ok.setObjectName("btn_primary")
        ok.setMinimumHeight(40); ok.clicked.connect(self._on_accept)
        btn_row.addStretch(); btn_row.addWidget(cancel); btn_row.addWidget(ok)
        lay.addLayout(btn_row)

    def _on_accept(self):
        if self._bc_edit and self._item_id:
            _save_barcode(self._item_id, self._bc_edit, self)
        self.accept()

    def value(self) -> int:
        return self._spin.value()


# ── Record Order amount (was Inventur) ────────────────────────────────────────

class InventurDialog(QDialog):
    """Set order amount, with inline barcode edit."""

    def __init__(self, model_name: str, part_type_name: str,
                 current_stock: int, parent=None, item_id: int = 0):
        super().__init__(parent)
        self._item_id = item_id
        self.setWindowTitle(f"{model_name}  ·  {part_type_name}")
        self.setModal(True); self.setMinimumWidth(340)
        _apply(self)
        lay = QVBoxLayout(self); lay.setSpacing(14); lay.setContentsMargins(24, 24, 24, 20)

        # Header
        hdr_row = QHBoxLayout()
        title = QLabel(f"{model_name}  ·  {part_type_name}")
        title.setObjectName("dlg_header")
        close_btn = QPushButton("×"); close_btn.setObjectName("btn_close_x")
        close_btn.setFixedSize(32, 32); close_btn.clicked.connect(self.reject)
        hdr_row.addWidget(title); hdr_row.addStretch(); hdr_row.addWidget(close_btn)
        lay.addLayout(hdr_row)

        hint = QLabel(t("disp_order_hint"))
        hint.setObjectName("section_caption"); hint.setWordWrap(True)
        lay.addWidget(hint)

        sys_lbl = QLabel(t("disp_sys_stock", n=current_stock))
        sys_lbl.setObjectName("card_meta")
        lay.addWidget(sys_lbl)

        # Barcode field
        self._bc_edit = None
        if item_id:
            item = _item_repo.get_by_id(item_id)
            if item:
                self._bc_edit = _barcode_row(item, lay)

        form = QFormLayout(); form.setSpacing(12)
        # Always open at 0 — current stock shown in the sys_lbl above.
        self._spin = QuantitySpin(0, 9999, 0)
        form.addRow(t("col_inventur"), self._spin)
        lay.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        cancel = QPushButton(t("op_cancel")); cancel.setObjectName("btn_ghost")
        cancel.setMinimumHeight(40); cancel.clicked.connect(self.reject)
        ok = QPushButton("OK"); ok.setObjectName("btn_primary")
        ok.setMinimumHeight(40); ok.clicked.connect(self._on_accept)
        btn_row.addStretch(); btn_row.addWidget(cancel); btn_row.addWidget(ok)
        lay.addLayout(btn_row)

    def _on_accept(self):
        if self._bc_edit and self._item_id:
            _save_barcode(self._item_id, self._bc_edit, self)
        self.accept()

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

        hdr_row = QHBoxLayout()
        title = QLabel(t("disp_dlg_add_model"))
        title.setObjectName("dlg_header")
        close_btn = QPushButton("×"); close_btn.setObjectName("btn_close_x")
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
