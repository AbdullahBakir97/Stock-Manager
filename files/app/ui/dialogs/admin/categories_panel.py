"""
app/ui/dialogs/admin/categories_panel.py — Add / edit / reorder / toggle categories.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFormLayout, QGridLayout,
    QListWidget, QListWidgetItem, QLineEdit, QCheckBox,
    QPushButton, QLabel, QMessageBox, QToolButton, QDialog,
)

from app.repositories.category_repo import CategoryRepository
from app.core.icon_utils import load_svg_icon
from app.core.theme import THEME
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from app.models.category import CategoryConfig
from app.core.database import load_demo_data
from app.core.i18n import t

_cat_repo = CategoryRepository()

# Phone parts & accessories icons — curated set
_CATEGORY_ICONS = [
    ("📱", "Phone"),       ("📲", "Smartphone"),   ("💻", "Laptop"),
    ("🖥", "Desktop"),     ("🖨", "Printer"),      ("⌨", "Keyboard"),
    ("🔋", "Battery"),     ("🔌", "Charger"),      ("🔊", "Speaker"),
    ("🎧", "Headphones"),  ("🎤", "Microphone"),   ("📷", "Camera"),
    ("🖼", "Display"),     ("📡", "Antenna"),       ("💡", "LED"),
    ("🔧", "Tool"),        ("🔩", "Screw"),         ("⚙", "Gear"),
    ("🛡", "Shield"),      ("📦", "Package"),       ("🏷", "Tag"),
    ("🔒", "Lock"),        ("🔑", "Key"),           ("💳", "Card"),
    ("📋", "Clipboard"),   ("📊", "Chart"),         ("🗂", "Folder"),
    ("💾", "Storage"),     ("📀", "Disc"),          ("🔗", "Link"),
    ("⚡", "Lightning"),   ("🌐", "Globe"),         ("📶", "Signal"),
    ("🎮", "Gaming"),      ("🕹", "Joystick"),      ("🖱", "Mouse"),
    ("📁", "Files"),       ("🏪", "Store"),         ("🛒", "Cart"),
    ("✏", "Pencil"),      ("📌", "Pin"),            ("🔍", "Search"),
]


class IconPickerButton(QPushButton):
    """Button that shows current icon and opens icon picker dialog."""

    def __init__(self, current: str = "", parent=None):
        super().__init__(parent)
        self._icon = current or "📁"
        self.setMinimumHeight(40)
        self.setMinimumWidth(160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._open)
        self._refresh()

    def _refresh(self):
        self.setText(f"  {self._icon}   Change Icon…")
        self.setStyleSheet(f"text-align:left; font-size:14px; padding-left:8px;")

    def _open(self):
        dlg = _IconPickerDialog(self._icon, self.window())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._icon = dlg.selected()
            self._refresh()

    def icon_text(self) -> str:
        return self._icon

    def set_icon(self, icon: str):
        self._icon = icon or "📁"
        self._refresh()


class _IconPickerDialog(QDialog):
    """Grid dialog to pick a category icon from curated phone-parts set."""

    def __init__(self, current: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("icon_choose_title"))
        self.setModal(True)
        self.setMinimumWidth(420)
        THEME.apply(self)
        self._selected = current or "📁"

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 20)
        lay.setSpacing(16)

        # Header
        hdr_row = QHBoxLayout()
        hdr = QLabel(t("icon_choose_hdr"))
        hdr.setObjectName("dlg_header")
        close_btn = QPushButton("×"); close_btn.setObjectName("btn_close_x")
        close_btn.setFixedSize(32, 32); close_btn.clicked.connect(self.reject)
        hdr_row.addWidget(hdr); hdr_row.addStretch(); hdr_row.addWidget(close_btn)
        lay.addLayout(hdr_row)

        # Icon grid
        grid = QGridLayout()
        grid.setSpacing(6)
        self._btns: list[QToolButton] = []
        cols = 8
        for i, (emoji, tooltip) in enumerate(_CATEGORY_ICONS):
            btn = QToolButton()
            btn.setText(emoji)
            btn.setToolTip(tooltip)
            btn.setFixedSize(44, 44)
            btn.setFont(QFont("Segoe UI", 16))
            btn.setCheckable(True)
            btn.setChecked(emoji == self._selected)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            tk = THEME.tokens
            btn.setStyleSheet(
                f"QToolButton {{ background:transparent; border:2px solid transparent;"
                f"  border-radius:8px; }}"
                f"QToolButton:hover {{ background:{tk.card2}; border-color:{tk.border}; }}"
                f"QToolButton:checked {{ border-color:{tk.green}; background:{tk.card2}; }}"
            )
            btn.clicked.connect(lambda _, e=emoji: self._pick(e))
            grid.addWidget(btn, i // cols, i % cols)
            self._btns.append(btn)
        lay.addLayout(grid)

        # Preview
        self._preview = QLabel(f"Selected:  {self._selected}")
        self._preview.setObjectName("card_meta")
        self._preview.setStyleSheet("font-size:16px;")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._preview)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        cancel = QPushButton(t("op_cancel")); cancel.setObjectName("btn_ghost")
        cancel.setMinimumHeight(36); cancel.clicked.connect(self.reject)
        ok = QPushButton("OK"); ok.setObjectName("btn_primary")
        ok.setMinimumHeight(36); ok.clicked.connect(self.accept)
        btn_row.addStretch(); btn_row.addWidget(cancel); btn_row.addWidget(ok)
        lay.addLayout(btn_row)

    def _pick(self, emoji: str):
        self._selected = emoji
        for btn in self._btns:
            btn.setChecked(btn.text() == emoji)
        self._preview.setText(f"Selected:  {emoji}")

    def selected(self) -> str:
        return self._selected


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
        from PyQt6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        scroll.setWidget(inner)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        outer = QVBoxLayout(inner)
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
        self._icon = IconPickerButton()
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
        self._icon.set_icon(cat.icon)
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
            self._icon.icon_text(),
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
