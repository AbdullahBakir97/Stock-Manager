"""
app/ui/dialogs/admin/categories_panel.py — Add / edit / reorder / toggle categories.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFormLayout,
    QListWidget, QListWidgetItem, QLineEdit, QCheckBox,
    QPushButton, QLabel, QMessageBox,
)

from app.repositories.category_repo import CategoryRepository
from app.core.icon_utils import load_svg_icon
from PyQt6.QtCore import Qt, pyqtSignal

from app.models.category import CategoryConfig
from app.core.database import load_demo_data
from app.core.i18n import t

_cat_repo = CategoryRepository()


class CategoriesPanel(QWidget):
    """Left: category list (checkable = active). Right: edit form."""

    categories_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cats: list[CategoryConfig] = []
        self._current_id: int | None = None
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left: list ────────────────────────────────────────────────────────
        left = QWidget()
        llay = QVBoxLayout(left)
        llay.setContentsMargins(0, 0, 0, 0); llay.setSpacing(6)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_select)
        llay.addWidget(self._list)

        btn_row = QHBoxLayout(); btn_row.setSpacing(4)
        self._add_btn  = QPushButton(t("cat_btn_add"));       self._add_btn.clicked.connect(self._add)
        self._del_btn  = QPushButton(t("cat_btn_delete"));    self._del_btn.clicked.connect(self._delete)
        self._up_btn   = QPushButton(t("cat_btn_move_up"));   self._up_btn.clicked.connect(self._move_up)
        self._down_btn = QPushButton(t("cat_btn_move_down")); self._down_btn.clicked.connect(self._move_down)
        for b in (self._add_btn, self._del_btn, self._up_btn, self._down_btn):
            btn_row.addWidget(b)
        llay.addLayout(btn_row)

        self._demo_btn = QPushButton(t("demo_load_title"))
        self._demo_btn.setObjectName("btn_ghost")
        self._demo_btn.clicked.connect(self._load_demo)
        llay.addWidget(self._demo_btn)
        splitter.addWidget(left)

        # ── Right: edit form ──────────────────────────────────────────────────
        right = QWidget()
        rlay = QVBoxLayout(right)
        rlay.setContentsMargins(12, 0, 0, 0); rlay.setSpacing(10)

        self._placeholder = QLabel(t("cat_no_selection"))
        self._placeholder.setObjectName("card_meta_dim")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._form_widget = QWidget()
        form = QFormLayout(self._form_widget); form.setSpacing(10)

        self._en = QLineEdit(); form.addRow(t("cat_lbl_name_en"), self._en)
        self._de = QLineEdit(); form.addRow(t("cat_lbl_name_de"), self._de)
        self._ar = QLineEdit(); form.addRow(t("cat_lbl_name_ar"), self._ar)
        self._icon = QLineEdit(); self._icon.setMaxLength(4)
        form.addRow(t("cat_lbl_icon"), self._icon)
        self._active = QCheckBox(t("cat_lbl_active"))
        form.addRow("", self._active)

        self._save_btn = QPushButton(t("cat_btn_save"))
        self._save_btn.setObjectName("btn_primary")
        self._save_btn.clicked.connect(self._save_edit)

        rlay.addWidget(self._placeholder)
        rlay.addWidget(self._form_widget)
        rlay.addWidget(self._save_btn)
        rlay.addStretch()
        self._form_widget.hide()
        self._save_btn.hide()

        splitter.addWidget(right)
        splitter.setSizes([220, 400])
        outer.addWidget(splitter)

    # ── Data operations ───────────────────────────────────────────────────────

    def _refresh(self) -> None:
        self._cats = _cat_repo.get_all()
        self._list.clear()
        for cat in self._cats:
            icon = load_svg_icon(cat.icon) if cat.icon else "📁"
            item = QListWidgetItem(f"{icon}  {cat.name_en}")
            item.setData(Qt.ItemDataRole.UserRole, cat.id)
            self._list.addItem(item)
        self._form_widget.hide()
        self._save_btn.hide()
        self._placeholder.show()
        self._current_id = None

    def _on_select(self, row: int) -> None:
        if row < 0 or row >= len(self._cats):
            self._form_widget.hide(); self._save_btn.hide()
            self._placeholder.show(); self._current_id = None
            return
        cat = self._cats[row]
        self._current_id = cat.id
        self._en.setText(cat.name_en)
        self._de.setText(cat.name_de)
        self._ar.setText(cat.name_ar)
        self._icon.setText(cat.icon)
        self._active.setChecked(cat.is_active)
        self._placeholder.hide()
        self._form_widget.show(); self._save_btn.show()

    def _save_edit(self) -> None:
        if self._current_id is None:
            return
        _cat_repo.update_category(
            self._current_id,
            self._en.text().strip(),
            self._de.text().strip(),
            self._ar.text().strip(),
            self._icon.text().strip(),
            self._active.isChecked(),
        )
        self._refresh()
        self.categories_changed.emit()

    def _add(self) -> None:
        key = f"category_{len(self._cats) + 1}"
        _cat_repo.add_category(key, "New Category", "", "")
        self._refresh()
        self._list.setCurrentRow(len(self._cats) - 1)
        self.categories_changed.emit()

    def _delete(self) -> None:
        row = self._list.currentRow()
        if row < 0 or row >= len(self._cats):
            return
        cat = self._cats[row]
        ok = QMessageBox.question(
            self, t("cat_btn_delete"),
            t("cat_delete_confirm", name=cat.name_en),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ok != QMessageBox.StandardButton.Yes:
            return
        if not _cat_repo.delete_category(cat.id):
            QMessageBox.warning(self, t("cat_btn_delete"), t("cat_delete_blocked"))
            return
        self._refresh()
        self.categories_changed.emit()

    def _move_up(self) -> None:
        row = self._list.currentRow()
        if row <= 0:
            return
        ids = [c.id for c in self._cats]
        ids[row - 1], ids[row] = ids[row], ids[row - 1]
        _cat_repo.reorder(ids)
        self._refresh()
        self._list.setCurrentRow(row - 1)
        self.categories_changed.emit()

    def _move_down(self) -> None:
        row = self._list.currentRow()
        if row < 0 or row >= len(self._cats) - 1:
            return
        ids = [c.id for c in self._cats]
        ids[row], ids[row + 1] = ids[row + 1], ids[row]
        _cat_repo.reorder(ids)
        self._refresh()
        self._list.setCurrentRow(row + 1)
        self.categories_changed.emit()

    def _load_demo(self) -> None:
        ok = QMessageBox.question(
            self, t("demo_load_title"), t("demo_load_body"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ok == QMessageBox.StandardButton.Yes:
            load_demo_data()
            self._refresh()
            self.categories_changed.emit()
            QMessageBox.information(self, t("demo_load_title"), t("demo_loaded"))

    def reload(self) -> None:
        self._refresh()
