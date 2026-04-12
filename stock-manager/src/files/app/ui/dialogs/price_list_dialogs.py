"""app/ui/dialogs/price_list_dialogs.py — Price list dialogs."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QCheckBox, QDoubleSpinBox, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt

from app.core.i18n import t
from app.core.theme import THEME
from app.services.price_list_service import PriceListService


_price_list_svc = PriceListService()


class NewPriceListDialog(QDialog):
    """Dialog to create a new price list."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("pl_dlg_title"))
        self.setMinimumWidth(420)
        self._build()
        THEME.apply(self)

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        # Header
        hdr = QLabel(t("pl_dlg_title"))
        hdr.setObjectName("dlg_header")
        lay.addWidget(hdr)

        # Name
        name_lbl = QLabel(t("pl_dlg_name"))
        name_lbl.setObjectName("dlg_label")
        self._name = QLineEdit()
        self._name.setPlaceholderText("")
        lay.addWidget(name_lbl)
        lay.addWidget(self._name)

        # Description
        desc_lbl = QLabel(t("pl_dlg_desc"))
        desc_lbl.setObjectName("dlg_label")
        self._desc = QTextEdit()
        self._desc.setMaximumHeight(80)
        lay.addWidget(desc_lbl)
        lay.addWidget(self._desc)

        # Active checkbox
        self._active = QCheckBox(t("pl_dlg_active"))
        self._active.setChecked(True)
        lay.addWidget(self._active)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("dlg_separator")
        lay.addWidget(sep)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel = QPushButton(t("btn_cancel"))
        cancel.setObjectName("btn_secondary")
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)

        create = QPushButton(t("btn_create"))
        create.setObjectName("btn_primary")
        create.clicked.connect(self._on_create)
        btn_row.addWidget(create)

        lay.addLayout(btn_row)

    def _on_create(self) -> None:
        """Create the price list."""
        name = self._name.text().strip()
        if not name:
            # Show error (would need toast system)
            return

        desc = self._desc.toPlainText().strip()
        try:
            _price_list_svc.create_list(name, desc)
            self.accept()
        except ValueError:
            # Show error
            pass


class EditPriceListDialog(QDialog):
    """Dialog to edit a price list."""

    def __init__(self, parent=None, list_id: int = 0):
        super().__init__(parent)
        self.setWindowTitle(t("pl_dlg_edit_title"))
        self.setMinimumWidth(420)
        self._list_id = list_id
        self._build()
        self._load_data()
        THEME.apply(self)

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        # Header
        hdr = QLabel(t("pl_dlg_edit_title"))
        hdr.setObjectName("dlg_header")
        lay.addWidget(hdr)

        # Name
        name_lbl = QLabel(t("pl_dlg_name"))
        name_lbl.setObjectName("dlg_label")
        self._name = QLineEdit()
        lay.addWidget(name_lbl)
        lay.addWidget(self._name)

        # Description
        desc_lbl = QLabel(t("pl_dlg_desc"))
        desc_lbl.setObjectName("dlg_label")
        self._desc = QTextEdit()
        self._desc.setMaximumHeight(80)
        lay.addWidget(desc_lbl)
        lay.addWidget(self._desc)

        # Active checkbox
        self._active = QCheckBox(t("pl_dlg_active"))
        lay.addWidget(self._active)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("dlg_separator")
        lay.addWidget(sep)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel = QPushButton(t("btn_cancel"))
        cancel.setObjectName("btn_secondary")
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)

        save = QPushButton(t("btn_save"))
        save.setObjectName("btn_primary")
        save.clicked.connect(self._on_save)
        btn_row.addWidget(save)

        lay.addLayout(btn_row)

    def _load_data(self) -> None:
        """Load the price list data."""
        if not self._list_id:
            return

        pl = _price_list_svc.get_list(self._list_id)
        if pl:
            self._name.setText(pl.name)
            self._desc.setPlainText(pl.description or "")
            self._active.setChecked(pl.is_active)

    def _on_save(self) -> None:
        """Save the price list."""
        name = self._name.text().strip()
        if not name:
            return

        desc = self._desc.toPlainText().strip()
        try:
            _price_list_svc.update_list(self._list_id, name, desc, self._active.isChecked())
            self.accept()
        except ValueError:
            pass


class BulkMarkupDialog(QDialog):
    """Dialog to apply bulk markup to all items in a price list."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("pl_markup_title"))
        self.setMinimumWidth(380)
        self._build()
        THEME.apply(self)

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        # Header
        hdr = QLabel(t("pl_markup_title"))
        hdr.setObjectName("dlg_header")
        lay.addWidget(hdr)

        # Info
        info = QLabel(t("pl_markup_pct"))
        info.setObjectName("card_meta")
        lay.addWidget(info)

        # Percentage input
        pct_row = QHBoxLayout()
        pct_lbl = QLabel("%")
        pct_lbl.setObjectName("dlg_label")
        self._pct = QDoubleSpinBox()
        self._pct.setRange(-99.99, 999.99)
        self._pct.setDecimals(2)
        self._pct.setSingleStep(1.0)
        self._pct.setValue(10.0)
        pct_row.addWidget(pct_lbl)
        pct_row.addWidget(self._pct, 1)
        lay.addLayout(pct_row)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("dlg_separator")
        lay.addWidget(sep)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel = QPushButton(t("btn_cancel"))
        cancel.setObjectName("btn_secondary")
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)

        apply_btn = QPushButton(t("btn_apply"))
        apply_btn.setObjectName("btn_primary")
        apply_btn.clicked.connect(self.accept)
        btn_row.addWidget(apply_btn)

        lay.addLayout(btn_row)

    def get_percentage(self) -> float:
        """Get the entered percentage."""
        return float(self._pct.value())
