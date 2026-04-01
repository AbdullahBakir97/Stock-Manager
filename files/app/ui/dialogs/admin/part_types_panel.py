"""
app/ui/dialogs/admin/part_types_panel.py — Manage part types + barcodes per category.
"""
from __future__ import annotations
import re

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QLineEdit, QPushButton, QLabel,
    QDialog, QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from app.repositories.category_repo import CategoryRepository
from app.repositories.item_repo import ItemRepository
from app.core.icon_utils import load_svg_icon
from app.models.category import CategoryConfig, PartTypeConfig
from app.ui.dialogs.admin.color_picker_widget import ColorPickerWidget
from app.core.theme import THEME
from app.core.i18n import t

_cat_repo  = CategoryRepository()
_item_repo = ItemRepository()
_KEY_RE = re.compile(r'^[A-Z0-9_]+$')

_FONT_MONO = QFont("JetBrains Mono", 10)
_FONT_MONO.setStyleHint(QFont.StyleHint.Monospace)


# ── Part Type Form Dialog ─────────────────────────────────────────────────────

class _PartTypeFormDialog(QDialog):
    def __init__(self, existing_keys: list[str], pt: PartTypeConfig | None = None,
                 parent=None):
        super().__init__(parent)
        self._existing_keys = [k for k in existing_keys if k != (pt.key if pt else "")]
        self.setWindowTitle(t("pt_btn_edit") if pt else t("pt_btn_add"))
        self.setModal(True); self.setMinimumWidth(380)
        THEME.apply(self)

        lay = QVBoxLayout(self); lay.setSpacing(14); lay.setContentsMargins(24, 24, 24, 20)

        # Header
        hdr_row = QHBoxLayout()
        hdr = QLabel(t("pt_btn_edit") if pt else t("pt_btn_add"))
        hdr.setObjectName("dlg_header")
        close_btn = QPushButton("×"); close_btn.setObjectName("btn_close_x")
        close_btn.setFixedSize(32, 32); close_btn.clicked.connect(self.reject)
        hdr_row.addWidget(hdr); hdr_row.addStretch(); hdr_row.addWidget(close_btn)
        lay.addLayout(hdr_row)

        form = QFormLayout(); form.setSpacing(12)
        self._key_edit  = QLineEdit(pt.key  if pt else "")
        self._key_edit.setMinimumHeight(36)
        self._name_edit = QLineEdit(pt.name if pt else "")
        self._name_edit.setMinimumHeight(36)
        self._color_btn = ColorPickerWidget(pt.accent_color if pt else "#4A9EFF")
        form.addRow(t("pt_lbl_key"),   self._key_edit)
        form.addRow(t("pt_lbl_name"),  self._name_edit)
        form.addRow(t("pt_lbl_color"), self._color_btn)
        lay.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        cancel = QPushButton(t("op_cancel")); cancel.setObjectName("btn_ghost")
        cancel.setMinimumHeight(38); cancel.clicked.connect(self.reject)
        save = QPushButton("OK"); save.setObjectName("btn_primary")
        save.setMinimumHeight(38); save.clicked.connect(self._validate)
        btn_row.addStretch(); btn_row.addWidget(cancel); btn_row.addWidget(save)
        lay.addLayout(btn_row)

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


# ── Part Types Panel ──────────────────────────────────────────────────────────

class PartTypesPanel(QWidget):
    """Part type management with inline barcode editing for all items."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cat: CategoryConfig | None = None
        self._build_ui()
        self._load_categories()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16); outer.setSpacing(12)

        # Category selector
        sel_row = QHBoxLayout(); sel_row.setSpacing(8)
        lbl = QLabel(t("pt_lbl_category"))
        lbl.setObjectName("detail_section_hdr")
        sel_row.addWidget(lbl)
        self._cat_combo = QComboBox(); self._cat_combo.setMinimumWidth(220)
        self._cat_combo.setMinimumHeight(36)
        self._cat_combo.currentIndexChanged.connect(self._on_cat_change)
        sel_row.addWidget(self._cat_combo); sel_row.addStretch()
        outer.addLayout(sel_row)

        # Splitter: part types (top) + barcodes (bottom)
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(4)

        # ── Top: Part types table + buttons ──
        top_w = QWidget()
        top_lay = QVBoxLayout(top_w)
        top_lay.setContentsMargins(0, 0, 0, 0); top_lay.setSpacing(6)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels([t("pt_col_key"), t("pt_col_name"), t("pt_col_color")])
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 120)
        self._table.setColumnWidth(2, 100)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setShowGrid(False)
        self._table.itemSelectionChanged.connect(self._on_pt_select)
        top_lay.addWidget(self._table)

        btn_row = QHBoxLayout(); btn_row.setSpacing(6)
        self._add_btn  = QPushButton(t("pt_btn_add"));  self._add_btn.setObjectName("btn_primary")
        self._add_btn.clicked.connect(self._add)
        self._edit_btn = QPushButton(t("pt_btn_edit")); self._edit_btn.setObjectName("btn_ghost")
        self._edit_btn.clicked.connect(self._edit)
        self._del_btn  = QPushButton(t("pt_btn_delete")); self._del_btn.setObjectName("btn_ghost")
        self._del_btn.clicked.connect(self._delete)
        self._up_btn   = QPushButton("↑"); self._up_btn.setObjectName("btn_ghost")
        self._up_btn.setFixedWidth(36); self._up_btn.clicked.connect(self._move_up)
        self._down_btn = QPushButton("↓"); self._down_btn.setObjectName("btn_ghost")
        self._down_btn.setFixedWidth(36); self._down_btn.clicked.connect(self._move_down)
        for b in (self._add_btn, self._edit_btn, self._del_btn):
            btn_row.addWidget(b)
        btn_row.addStretch()
        btn_row.addWidget(self._up_btn); btn_row.addWidget(self._down_btn)
        top_lay.addLayout(btn_row)
        splitter.addWidget(top_w)

        # ── Bottom: Barcodes for selected part type ──
        btm_w = QWidget()
        btm_lay = QVBoxLayout(btm_w)
        btm_lay.setContentsMargins(0, 0, 0, 0); btm_lay.setSpacing(6)

        bc_hdr_row = QHBoxLayout()
        self._bc_hdr = QLabel(t("barcode_assign_title"))
        self._bc_hdr.setObjectName("detail_section_hdr")
        self._bc_save_all = QPushButton(t("shop_btn_save"))
        self._bc_save_all.setObjectName("btn_primary")
        self._bc_save_all.setFixedHeight(30)
        self._bc_save_all.clicked.connect(self._save_all_barcodes)
        bc_hdr_row.addWidget(self._bc_hdr); bc_hdr_row.addStretch()
        bc_hdr_row.addWidget(self._bc_save_all)
        btm_lay.addLayout(bc_hdr_row)

        self._bc_hint = QLabel(t("barcode_none"))
        self._bc_hint.setObjectName("section_caption")
        btm_lay.addWidget(self._bc_hint)

        # Barcode table: Model | Barcode (editable)
        self._bc_table = QTableWidget(0, 2)
        self._bc_table.setHorizontalHeaderLabels([t("mdl_col_model"), t("dlg_lbl_barcode")])
        bh = self._bc_table.horizontalHeader()
        bh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        bh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._bc_table.verticalHeader().setVisible(False)
        self._bc_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        # Allow editing on barcode column
        self._bc_table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.SelectedClicked
        )
        self._bc_table.setShowGrid(False)
        btm_lay.addWidget(self._bc_table)

        self._bc_item_ids: list[int] = []
        splitter.addWidget(btm_w)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        outer.addWidget(splitter, 1)

    # ── Category handling ─────────────────────────────────────────────────────

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

    def _on_pt_select(self) -> None:
        pt = self._current_pt()
        self._refresh_barcodes(pt)

    # ── Part types table ──────────────────────────────────────────────────────

    def _refresh_table(self) -> None:
        self._table.setRowCount(0)
        if not self._cat:
            return
        for pt in self._cat.part_types:
            row = self._table.rowCount(); self._table.insertRow(row)
            self._table.setItem(row, 0, self._ro(pt.key, pt.id))
            self._table.setItem(row, 1, self._ro(pt.name, pt.id))
            color_it = QTableWidgetItem(pt.accent_color)
            color_it.setBackground(QColor(pt.accent_color))
            color_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            color_it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._table.setItem(row, 2, color_it)
            self._table.setRowHeight(row, 38)
        self._refresh_barcodes(None)

    # ── Barcode table ─────────────────────────────────────────────────────────

    def _refresh_barcodes(self, pt: PartTypeConfig | None) -> None:
        self._bc_table.setRowCount(0)
        self._bc_item_ids.clear()
        if not pt:
            self._bc_hdr.setText(t("barcode_assign_title"))
            self._bc_hint.setText(t("pt_no_selection"))
            self._bc_hint.show()
            return

        self._bc_hdr.setText(f"{t('barcode_assign_title')}  —  {pt.name}")
        items = _item_repo.get_by_part_type(pt.id)
        if not items:
            self._bc_hint.setText(t("barcode_none"))
            self._bc_hint.show()
            return
        self._bc_hint.hide()

        tk = THEME.tokens
        for item in items:
            row = self._bc_table.rowCount()
            self._bc_table.insertRow(row)
            self._bc_item_ids.append(item.id)

            # Model name — read only
            model_it = QTableWidgetItem(item.model_name or item.display_name)
            model_it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._bc_table.setItem(row, 0, model_it)

            # Barcode — editable, monospace
            bc_it = QTableWidgetItem(item.barcode or "")
            bc_it.setFont(_FONT_MONO)
            bc_it.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable
            )
            if item.barcode:
                bc_it.setForeground(QColor(tk.green))
            else:
                bc_it.setForeground(QColor(tk.t4))
            self._bc_table.setItem(row, 1, bc_it)

            self._bc_table.setRowHeight(row, 36)

    def _save_all_barcodes(self) -> None:
        """Save all edited barcodes in the barcode table."""
        tk = THEME.tokens
        saved = 0
        errors = 0
        for row in range(self._bc_table.rowCount()):
            if row >= len(self._bc_item_ids):
                break
            item_id = self._bc_item_ids[row]
            bc_item = self._bc_table.item(row, 1)
            if not bc_item:
                continue
            new_bc = bc_item.text().strip() or None
            try:
                _item_repo.update_barcode(item_id, new_bc)
                # Green text = saved
                bc_item.setForeground(QColor(tk.green))
                saved += 1
            except Exception as e:
                if "UNIQUE" in str(e):
                    bc_item.setForeground(QColor(tk.red))
                    errors += 1
                else:
                    bc_item.setForeground(QColor(tk.red))
                    errors += 1

        if errors:
            QMessageBox.warning(self, t("barcode_assign_title"),
                                f"{saved} saved, {errors} failed (duplicate barcodes)")
        else:
            self._bc_hint.setText(t("barcode_saved"))
            self._bc_hint.show()

    # ── CRUD ──────────────────────────────────────────────────────────────────

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
