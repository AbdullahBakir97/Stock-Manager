"""
app/ui/dialogs/admin/models_panel.py — Phone model CRUD (add / rename / delete).
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QLineEdit, QPushButton, QLabel, QFrame,
    QInputDialog, QMessageBox, QDialog,
)
from PyQt6.QtCore import Qt

from app.repositories.model_repo import ModelRepository
from app.models.phone_model import PhoneModel
from app.ui.dialogs.matrix_dialogs import AddModelDialog
from app.core.icon_utils import get_colored_icon
from app.core.theme import THEME
from app.core.i18n import t

_model_repo = ModelRepository()


class ModelsPanel(QWidget):
    """Professional phone model management with header, KPIs, filtering, and table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._models: list[PhoneModel] = []
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        # ── Root scroll area ───────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setObjectName("analytics_scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        scroll.setWidget(inner)
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.addWidget(scroll)

        outer = QVBoxLayout(inner)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(16)

        # ── Header ─────────────────────────────────────────────────────────────
        header_lay = QHBoxLayout()
        header_lay.setSpacing(12)
        title = QLabel(t("mdl_page_title") or "Phone Models")
        title.setObjectName("admin_content_title")
        desc = QLabel(t("mdl_page_desc") or "Manage device brands and model names")
        desc.setObjectName("admin_content_desc")
        header_lay.addWidget(title)
        header_lay.addStretch()
        add_btn = QPushButton(t("mdl_btn_add"))
        add_btn.setObjectName("admin_action_btn")
        add_btn.clicked.connect(self._add)
        header_lay.addWidget(add_btn)
        outer.addLayout(header_lay)

        # ── KPI Row ────────────────────────────────────────────────────────────
        kpi_lay = QHBoxLayout()
        kpi_lay.setSpacing(12)
        self._kpi_models = self._make_kpi(t("stat_total_models") or "Total Models", "0")
        self._kpi_brands = self._make_kpi(t("stat_total_brands") or "Total Brands", "0")
        kpi_lay.addWidget(self._kpi_models)
        kpi_lay.addWidget(self._kpi_brands)
        kpi_lay.addStretch()
        outer.addLayout(kpi_lay)

        # ── Main card ──────────────────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("admin_form_card")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(16, 16, 16, 16)
        card_lay.setSpacing(12)

        # ── Toolbar: brand filter + search ─────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.addWidget(QLabel(t("disp_filter_brand")))
        self._brand_combo = QComboBox()
        self._brand_combo.setMinimumWidth(150)
        self._brand_combo.currentIndexChanged.connect(self._refresh)
        toolbar.addWidget(self._brand_combo)
        toolbar.addWidget(QLabel("  "))
        self._search = QLineEdit()
        self._search.setPlaceholderText(t("placeholder_filter") or "Filter…")
        self._search.setMinimumWidth(180)
        self._search.textChanged.connect(self._refresh)
        toolbar.addWidget(self._search)
        toolbar.addStretch()
        card_lay.addLayout(toolbar)

        # ── Table ──────────────────────────────────────────────────────────────
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            t("mdl_col_brand"),
            t("mdl_col_model"),
            t("mdl_col_edit") or "",
            t("mdl_col_delete") or "",
        ])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setColumnWidth(0, 140)
        self._table.setColumnWidth(2, 44)
        self._table.setColumnWidth(3, 44)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self._table.setRowHeight(0, 48)
        card_lay.addWidget(self._table)

        outer.addWidget(card)

    def _make_kpi(self, label: str, value: str) -> QFrame:
        """Create a KPI card frame."""
        frame = QFrame()
        frame.setObjectName("admin_kpi")
        frame.setFixedHeight(80)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(4)

        lbl = QLabel(label)
        lbl.setObjectName("admin_kpi_label")
        val = QLabel(value)
        val.setObjectName("admin_kpi_value")
        sub = QLabel("")
        sub.setObjectName("admin_kpi_sub")

        lay.addWidget(lbl)
        lay.addWidget(val)
        lay.addWidget(sub)

        # Store ref for updates
        frame._value_label = val
        return frame

    def _update_kpis(self) -> None:
        """Update KPI displays."""
        brands = _model_repo.get_brands()
        self._kpi_models._value_label.setText(str(len(self._models)))
        self._kpi_brands._value_label.setText(str(len(brands)))

    # ── Data operations ────────────────────────────────────────────────────────

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
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setRowHeight(row, 48)

            # Brand and model cells (read-only)
            self._table.setItem(row, 0, self._ro(model.brand, model.id))
            self._table.setItem(row, 1, self._ro(model.name, model.id))

            # Edit button
            edit_btn = QPushButton()
            edit_btn.setObjectName("admin_edit_btn")
            edit_btn.setIcon(get_colored_icon("edit", THEME.tokens.blue))
            edit_btn.setToolTip(t("mdl_btn_rename"))
            edit_btn.setFixedSize(40, 40)
            edit_btn.clicked.connect(lambda checked, mid=model.id: self._rename_by_id(mid))
            self._table.setCellWidget(row, 2, edit_btn)

            # Delete button
            del_btn = QPushButton()
            del_btn.setObjectName("admin_del_btn")
            del_btn.setIcon(get_colored_icon("delete", THEME.tokens.red))
            del_btn.setToolTip(t("mdl_btn_delete"))
            del_btn.setFixedSize(40, 40)
            del_btn.clicked.connect(lambda checked, mid=model.id: self._delete_by_id(mid))
            self._table.setCellWidget(row, 3, del_btn)

        self._update_kpis()

    def _selected_models(self) -> list[PhoneModel]:
        rows = {idx.row() for idx in self._table.selectedIndexes()}
        return [self._models[r] for r in sorted(rows) if r < len(self._models)]

    def _add(self) -> None:
        brands = _model_repo.get_brands()
        dlg = AddModelDialog(brands, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            _model_repo.add(dlg.brand(), dlg.model_name())
            self._refresh()

    def _rename_by_id(self, model_id: int) -> None:
        """Rename a model by its ID."""
        model = next((m for m in self._models if m.id == model_id), None)
        if not model:
            return
        new_name, ok = QInputDialog.getText(
            self, t("mdl_btn_rename"), t("mdl_rename_lbl"),
            text=model.name,
        )
        if ok and new_name.strip():
            _model_repo.rename(model.id, new_name)
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

    def _delete_by_id(self, model_id: int) -> None:
        """Delete a model by its ID."""
        model = next((m for m in self._models if m.id == model_id), None)
        if not model:
            return
        ok = QMessageBox.question(
            self, t("mdl_btn_delete"),
            t("mdl_delete_confirm_single", name=model.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ok != QMessageBox.StandardButton.Yes:
            return
        if not _model_repo.delete(model.id):
            QMessageBox.warning(self, t("mdl_btn_delete"), t("mdl_delete_blocked"))
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
        """Create a read-only table item."""
        it = QTableWidgetItem(text)
        it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        it.setData(Qt.ItemDataRole.UserRole, model_id)
        return it
