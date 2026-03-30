"""
app/ui/dialogs/admin/part_types_panel.py — Add / edit / delete part types per category.
"""
from __future__ import annotations
import re

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QLineEdit, QPushButton, QLabel,
    QDialog, QDialogButtonBox, QMessageBox,
)
from PyQt6.QtCore import Qt, QSize

from app.repositories.category_repo import CategoryRepository
from app.core.icon_utils import load_svg_icon, get_button_icon
from app.models.category import CategoryConfig, PartTypeConfig
from app.ui.dialogs.admin.color_picker_widget import ColorPickerWidget
from app.core.i18n import t

_cat_repo = CategoryRepository()
_KEY_RE = re.compile(r'^[A-Z0-9_]+$')


class _PartTypeFormDialog(QDialog):
    """Small dialog for add / edit a part type."""

    def __init__(self, existing_keys: list[str], pt: PartTypeConfig | None = None,
                 parent=None):
        super().__init__(parent)
        self._existing_keys = [k for k in existing_keys if k != (pt.key if pt else "")]
        self.setWindowTitle(t("pt_btn_edit") if pt else t("pt_btn_add"))
        self.setModal(True); self.setMinimumWidth(360)

        from app.core.theme import THEME
        THEME.apply(self)

        lay = QVBoxLayout(self); lay.setSpacing(12); lay.setContentsMargins(20, 20, 20, 16)

        form = QFormLayout(); form.setSpacing(10)
        self._key_edit  = QLineEdit(pt.key  if pt else "")
        self._name_edit = QLineEdit(pt.name if pt else "")
        self._color_btn = ColorPickerWidget(pt.accent_color if pt else "#4A9EFF")
        form.addRow(t("pt_lbl_key"),   self._key_edit)
        form.addRow(t("pt_lbl_name"),  self._name_edit)
        form.addRow(t("pt_lbl_color"), self._color_btn)
        lay.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._validate)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _validate(self) -> None:
        key  = self._key_edit.text().strip().upper()
        name = self._name_edit.text().strip()
        if not key or not name:
            QMessageBox.warning(self, t("dlg_required_title"), t("disp_model_empty"))
            return
        if not _KEY_RE.match(key):
            QMessageBox.warning(self, t("dlg_required_title"), t("pt_lbl_key"))
            return
        if key in self._existing_keys:
            QMessageBox.warning(self, t("dlg_required_title"), t("pt_key_exists", key=key))
            return
        self.accept()

    def values(self) -> tuple[str, str, str]:
        return (
            self._key_edit.text().strip().upper(),
            self._name_edit.text().strip(),
            self._color_btn.hex_color(),
        )


class PartTypesPanel(QWidget):
    """Top: category selector. Table: key | name | color. CRUD buttons."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cat: CategoryConfig | None = None
        self._build_ui()
        self._load_categories()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12); outer.setSpacing(8)

        # Category selector
        sel_row = QHBoxLayout(); sel_row.setSpacing(8)
        sel_row.addWidget(QLabel(t("pt_lbl_category")))
        self._cat_combo = QComboBox(); self._cat_combo.setMinimumWidth(200)
        self._cat_combo.currentIndexChanged.connect(self._on_cat_change)
        sel_row.addWidget(self._cat_combo); sel_row.addStretch()
        outer.addLayout(sel_row)

        # Table
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels([t("pt_col_key"), t("pt_col_name"), t("pt_col_color")])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(2, 120)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        outer.addWidget(self._table)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(6)
        self._add_btn  = QPushButton(t("pt_btn_add"));    self._add_btn.clicked.connect(self._add)
        self._edit_btn = QPushButton(t("pt_btn_edit"));   self._edit_btn.clicked.connect(self._edit)
        self._del_btn  = QPushButton(t("pt_btn_delete")); self._del_btn.clicked.connect(self._delete)
        self._up_btn   = QPushButton(); self._up_btn.clicked.connect(self._move_up)
        self._up_btn.setIcon(get_button_icon("up"))
        self._up_btn.setIconSize(QSize(16, 16))
        self._down_btn = QPushButton(); self._down_btn.clicked.connect(self._move_down)
        self._down_btn.setIcon(get_button_icon("down"))
        self._down_btn.setIconSize(QSize(16, 16))
        for b in (self._add_btn, self._edit_btn, self._del_btn, self._up_btn, self._down_btn):
            btn_row.addWidget(b)
        btn_row.addStretch()
        outer.addLayout(btn_row)

    def _load_categories(self) -> None:
        self._cat_combo.blockSignals(True)
        self._cat_combo.clear()
        for cat in _cat_repo.get_all():
            icon = load_svg_icon(cat.icon) if cat.icon else "📁"
            self._cat_combo.addItem(f"{icon}  {cat.name_en}", cat.id)
        self._cat_combo.blockSignals(False)
        self._on_cat_change(0)

    def _on_cat_change(self, _index: int) -> None:
        cat_id = self._cat_combo.currentData()
        if cat_id is None:
            self._cat = None; self._table.setRowCount(0); return
        self._cat = _cat_repo.get_by_id(cat_id)
        self._refresh_table()

    def _refresh_table(self) -> None:
        self._table.setRowCount(0)
        if not self._cat:
            return
        for pt in self._cat.part_types:
            row = self._table.rowCount(); self._table.insertRow(row)
            self._table.setItem(row, 0, self._ro(pt.key, pt.id))
            self._table.setItem(row, 1, self._ro(pt.name, pt.id))
            color_lbl = QTableWidgetItem(pt.accent_color)
            color_lbl.setBackground(__import__('PyQt6.QtGui', fromlist=['QColor']).QColor(pt.accent_color))
            color_lbl.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 2, color_lbl)

    def _current_pt(self) -> PartTypeConfig | None:
        row = self._table.currentRow()
        if row < 0 or not self._cat or row >= len(self._cat.part_types):
            return None
        return self._cat.part_types[row]

    def _add(self) -> None:
        if not self._cat:
            return
        existing = [pt.key for pt in self._cat.part_types]
        dlg = _PartTypeFormDialog(existing, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            key, name, color = dlg.values()
            _cat_repo.add_part_type(self._cat.id, key, name, color)
            self._cat = _cat_repo.get_by_id(self._cat.id)
            self._refresh_table()

    def _edit(self) -> None:
        pt = self._current_pt()
        if not pt or not self._cat:
            QMessageBox.information(self, t("pt_btn_edit"), t("pt_no_selection"))
            return
        existing = [p.key for p in self._cat.part_types]
        dlg = _PartTypeFormDialog(existing, pt=pt, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            key, name, color = dlg.values()
            _cat_repo.update_part_type(pt.id, key, name, color)
            self._cat = _cat_repo.get_by_id(self._cat.id)
            self._refresh_table()

    def _delete(self) -> None:
        pt = self._current_pt()
        if not pt:
            QMessageBox.information(self, t("pt_btn_delete"), t("pt_no_selection"))
            return
        if not _cat_repo.delete_part_type(pt.id):
            QMessageBox.warning(self, t("pt_btn_delete"), t("pt_delete_blocked"))
            return
        self._cat = _cat_repo.get_by_id(self._cat.id)
        self._refresh_table()

    def _move_up(self) -> None:
        row = self._table.currentRow()
        if row <= 0 or not self._cat:
            return
        ids = [pt.id for pt in self._cat.part_types]
        ids[row - 1], ids[row] = ids[row], ids[row - 1]
        _cat_repo.reorder_part_types(ids)
        self._cat = _cat_repo.get_by_id(self._cat.id)
        self._refresh_table()
        self._table.setCurrentCell(row - 1, 0)

    def _move_down(self) -> None:
        row = self._table.currentRow()
        if not self._cat or row < 0 or row >= len(self._cat.part_types) - 1:
            return
        ids = [pt.id for pt in self._cat.part_types]
        ids[row], ids[row + 1] = ids[row + 1], ids[row]
        _cat_repo.reorder_part_types(ids)
        self._cat = _cat_repo.get_by_id(self._cat.id)
        self._refresh_table()
        self._table.setCurrentCell(row + 1, 0)

    def reload(self) -> None:
        self._load_categories()

    @staticmethod
    def _ro(text: str, pt_id: int) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        it.setData(Qt.ItemDataRole.UserRole, pt_id)
        return it
