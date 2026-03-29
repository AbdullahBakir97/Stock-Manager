"""
app/ui/dialogs/admin/models_panel.py — Phone model CRUD (add / rename / delete).
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QLineEdit, QPushButton, QLabel,
    QInputDialog, QMessageBox, QDialog,
)
from PyQt6.QtCore import Qt

from app.repositories.model_repo import ModelRepository
from app.models.phone_model import PhoneModel
from app.ui.dialogs.matrix_dialogs import AddModelDialog
from app.core.i18n import t

_model_repo = ModelRepository()


class ModelsPanel(QWidget):
    """Brand filter + table of models. Add / Delete / Rename."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._models: list[PhoneModel] = []
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12); outer.setSpacing(8)

        # Top toolbar: brand filter + search
        toolbar = QHBoxLayout(); toolbar.setSpacing(8)
        toolbar.addWidget(QLabel(t("disp_filter_brand")))
        self._brand_combo = QComboBox(); self._brand_combo.setMinimumWidth(150)
        self._brand_combo.currentIndexChanged.connect(self._refresh)
        toolbar.addWidget(self._brand_combo)
        toolbar.addWidget(QLabel("  "))
        self._search = QLineEdit(); self._search.setPlaceholderText("  Filter…")
        self._search.setMinimumWidth(180)
        self._search.textChanged.connect(self._refresh)
        toolbar.addWidget(self._search)
        toolbar.addStretch()
        outer.addLayout(toolbar)

        # Table
        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels([t("mdl_col_brand"), t("mdl_col_model")])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 140)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        outer.addWidget(self._table)

        # Action buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(6)
        self._add_btn    = QPushButton(t("mdl_btn_add"));    self._add_btn.clicked.connect(self._add)
        self._rename_btn = QPushButton(t("mdl_btn_rename")); self._rename_btn.clicked.connect(self._rename)
        self._del_btn    = QPushButton(t("mdl_btn_delete")); self._del_btn.clicked.connect(self._delete)
        for b in (self._add_btn, self._rename_btn, self._del_btn):
            btn_row.addWidget(b)
        btn_row.addStretch()
        outer.addLayout(btn_row)

    def _refresh(self) -> None:
        # Reload brands
        brands = _model_repo.get_brands()
        current_brand = self._brand_combo.currentData()
        self._brand_combo.blockSignals(True)
        self._brand_combo.clear()
        self._brand_combo.addItem(t("disp_all_brands"), None)
        for b in brands:
            self._brand_combo.addItem(b, b)
        idx = self._brand_combo.findData(current_brand)
        self._brand_combo.setCurrentIndex(max(0, idx))
        self._brand_combo.blockSignals(False)

        brand_filter = self._brand_combo.currentData()
        search = self._search.text().strip().lower()
        self._models = _model_repo.get_all(brand=brand_filter)
        if search:
            self._models = [m for m in self._models if search in m.name.lower()
                            or search in m.brand.lower()]

        self._table.setRowCount(0)
        for model in self._models:
            row = self._table.rowCount(); self._table.insertRow(row)
            self._table.setItem(row, 0, self._ro(model.brand, model.id))
            self._table.setItem(row, 1, self._ro(model.name,  model.id))

    def _selected_models(self) -> list[PhoneModel]:
        rows = {idx.row() for idx in self._table.selectedIndexes()}
        return [self._models[r] for r in sorted(rows) if r < len(self._models)]

    def _add(self) -> None:
        brands = _model_repo.get_brands()
        dlg = AddModelDialog(brands, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            _model_repo.add(dlg.brand(), dlg.model_name())
            self._refresh()

    def _rename(self) -> None:
        selected = self._selected_models()
        if len(selected) != 1:
            QMessageBox.information(self, t("mdl_btn_rename"), t("pt_no_selection"))
            return
        model = selected[0]
        new_name, ok = QInputDialog.getText(
            self, t("mdl_rename_title"), t("mdl_rename_lbl"),
            text=model.name,
        )
        if ok and new_name.strip():
            _model_repo.rename(model.id, new_name)
            self._refresh()

    def _delete(self) -> None:
        selected = self._selected_models()
        if not selected:
            return
        ok = QMessageBox.question(
            self, t("mdl_btn_delete"),
            t("mdl_delete_confirm", n=len(selected)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ok != QMessageBox.StandardButton.Yes:
            return
        blocked = [m for m in selected if not _model_repo.delete(m.id)]
        if blocked:
            names = ", ".join(m.name for m in blocked)
            QMessageBox.warning(self, t("mdl_btn_delete"),
                                t("mdl_delete_blocked") + f"\n{names}")
        self._refresh()

    def reload(self) -> None:
        self._refresh()

    @staticmethod
    def _ro(text: str, model_id: int) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        it.setData(Qt.ItemDataRole.UserRole, model_id)
        return it
