"""app/ui/dialogs/barcode_assign_dialog.py — Assign barcode to inventory item."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from app.core.theme import THEME
from app.core.i18n import t
from app.repositories.item_repo import ItemRepository


class _BarcodeEdit(QLineEdit):
    """QLineEdit that swallows Enter so barcode scanners don't close the dialog."""
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            event.accept()
            return
        super().keyPressEvent(event)

_item_repo = ItemRepository()


class BarcodeAssignDialog(QDialog):
    """Assign or change a barcode on an inventory item."""

    def __init__(self, item_id: int, item_name: str,
                 current_barcode: str | None = None, parent=None):
        super().__init__(parent)
        self._item_id = item_id
        self.setWindowTitle(t("barcode_assign_title"))
        self.setModal(True)
        self.setMinimumWidth(400)
        THEME.apply(self)

        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(24, 24, 24, 20)

        # Header
        hdr_row = QHBoxLayout()
        hdr = QLabel(t("barcode_assign_title"))
        hdr.setObjectName("dlg_header")
        close_btn = QPushButton("×")
        close_btn.setObjectName("btn_close_x")
        close_btn.setFixedSize(32, 32)
        close_btn.clicked.connect(self.reject)
        hdr_row.addWidget(hdr)
        hdr_row.addStretch()
        hdr_row.addWidget(close_btn)
        lay.addLayout(hdr_row)

        # Item name
        name_lbl = QLabel(f"<b>{item_name}</b>")
        name_lbl.setObjectName("card_name")
        lay.addWidget(name_lbl)

        # Current barcode
        form = QFormLayout()
        form.setSpacing(12)
        cur_text = current_barcode or t("barcode_none")
        cur_lbl = QLabel(cur_text)
        cur_lbl.setFont(QFont("JetBrains Mono", 11))
        cur_lbl.setObjectName("card_barcode")
        form.addRow(t("barcode_current"), cur_lbl)

        # New barcode input
        self._barcode_edit = _BarcodeEdit()
        self._barcode_edit.setPlaceholderText("Scan or type barcode…")
        self._barcode_edit.setFont(QFont("JetBrains Mono", 11))
        self._barcode_edit.setMinimumHeight(40)
        self._barcode_edit.setText(current_barcode or "")
        form.addRow(t("barcode_new"), self._barcode_edit)
        lay.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        clear_btn = QPushButton(t("disp_order_clear"))
        clear_btn.setObjectName("btn_ghost")
        clear_btn.setFixedHeight(36)
        clear_btn.clicked.connect(lambda: self._barcode_edit.clear())
        btn_row.addWidget(clear_btn)

        btn_row.addStretch()

        cancel = QPushButton(t("op_cancel"))
        cancel.setObjectName("btn_ghost")
        cancel.setFixedHeight(36)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)

        save = QPushButton(t("barcode_saved"))
        save.setObjectName("btn_primary")
        save.setFixedHeight(36)
        save.clicked.connect(self._save)
        btn_row.addWidget(save)

        lay.addLayout(btn_row)

    def _save(self):
        bc = self._barcode_edit.text().strip() or None
        try:
            _item_repo.update_barcode(self._item_id, bc)
            self.accept()
        except Exception as e:
            if "UNIQUE" in str(e):
                QMessageBox.warning(self, t("barcode_assign_title"),
                                    t("barcode_duplicate"))
            else:
                QMessageBox.critical(self, t("msg_error"), str(e))
