"""
app/ui/dialogs/admin/part_types_panel.py — Professional part types + barcodes panel.
"""
from __future__ import annotations
import re

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QLineEdit, QPushButton, QLabel, QFrame,
    QDialog, QMessageBox, QToolButton, QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor

from app.repositories.category_repo import CategoryRepository
from app.repositories.item_repo import ItemRepository
from app.core.icon_utils import load_svg_icon, get_colored_icon, get_button_icon
from app.models.category import CategoryConfig, PartTypeConfig
from app.ui.dialogs.admin.color_picker_widget import ColorPickerWidget
from app.core.theme import THEME
from app.core.i18n import t

_cat_repo = CategoryRepository()
_item_repo = ItemRepository()
_KEY_RE = re.compile(r'^[A-Z0-9_]+$')

_FONT_MONO = QFont("JetBrains Mono", 10)
_FONT_MONO.setStyleHint(QFont.StyleHint.Monospace)


# ── KPI Card ────────────────────────────────────────────────────────────────

class _KpiCard(QFrame):
    """Small KPI metric card."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("admin_kpi")
        self.setFixedHeight(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)
        self._label = QLabel()
        self._label.setObjectName("admin_kpi_label")
        self._value = QLabel()
        self._value.setObjectName("admin_kpi_value")
        self._sub = QLabel()
        self._sub.setObjectName("admin_kpi_sub")
        lay.addWidget(self._label)
        lay.addWidget(self._value)
        lay.addWidget(self._sub)

    def set_data(self, label: str, value: str, sub: str = "") -> None:
        self._label.setText(label)
        self._value.setText(value)
        self._sub.setText(sub)


# ── Part Type Form Dialog ────────────────────────────────────────────────────

class _PartTypeFormDialog(QDialog):
    def __init__(self, existing_keys: list[str], pt: PartTypeConfig | None = None,
                 parent=None):
        super().__init__(parent)
        self._existing_keys = [k for k in existing_keys if k != (pt.key if pt else "")]
        self.setWindowTitle(t("pt_btn_edit") if pt else t("pt_btn_add"))
        self.setModal(True)
        self.setMinimumWidth(380)
        THEME.apply(self)

        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.setContentsMargins(24, 24, 24, 20)

        # Header
        hdr_row = QHBoxLayout()
        hdr = QLabel(t("pt_btn_edit") if pt else t("pt_btn_add"))
        hdr.setObjectName("dlg_header")
        close_btn = QPushButton("×")
        close_btn.setObjectName("btn_close_x")
        close_btn.setFixedSize(32, 32)
        close_btn.clicked.connect(self.reject)
        hdr_row.addWidget(hdr)
        hdr_row.addStretch()
        hdr_row.addWidget(close_btn)
        lay.addLayout(hdr_row)

        form = QFormLayout()
        form.setSpacing(12)
        self._key_edit = QLineEdit(pt.key if pt else "")
        self._key_edit.setMinimumHeight(36)
        self._key_edit.setPlaceholderText("e.g. DISPLAY, BATTERY")
        self._name_edit = QLineEdit(pt.name if pt else "")
        self._name_edit.setMinimumHeight(36)
        self._name_edit.setPlaceholderText("e.g. Display, Battery")
        self._color_btn = ColorPickerWidget(pt.accent_color if pt else "#4A9EFF")
        form.addRow(t("pt_lbl_key"), self._key_edit)
        form.addRow(t("pt_lbl_name"), self._name_edit)
        form.addRow(t("pt_lbl_color"), self._color_btn)
        lay.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        cancel = QPushButton(t("op_cancel"))
        cancel.setObjectName("btn_ghost")
        cancel.setMinimumHeight(38)
        cancel.clicked.connect(self.reject)
        save = QPushButton("OK")
        save.setObjectName("btn_primary")
        save.setMinimumHeight(38)
        save.clicked.connect(self._validate)
        btn_row.addStretch()
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        lay.addLayout(btn_row)

    def _validate(self) -> None:
        key = self._key_edit.text().strip().upper()
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


# ── Part Types Panel ─────────────────────────────────────────────────────────

class PartTypesPanel(QWidget):
    """Professional part type management with inline barcode editing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cat: CategoryConfig | None = None
        self._build_ui()
        self._load_categories()

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setObjectName("analytics_scroll")
        inner = QWidget()
        scroll.setWidget(inner)
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.addWidget(scroll)

        outer = QVBoxLayout(inner)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        # ── Header ──
        hdr_frame = QFrame()
        hdr_frame.setObjectName("admin_panel_header")
        hdr_lay = QHBoxLayout(hdr_frame)
        hdr_lay.setContentsMargins(0, 0, 0, 0)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel(t("admin_tab_part_types"))
        title.setObjectName("admin_content_title")
        title_col.addWidget(title)
        subtitle = QLabel(
            t("pt_panel_subtitle") if t("pt_panel_subtitle") != "pt_panel_subtitle"
            else "Manage part types, colors, and barcode assignments per category"
        )
        subtitle.setObjectName("admin_content_desc")
        title_col.addWidget(subtitle)
        hdr_lay.addLayout(title_col)
        hdr_lay.addStretch()
        outer.addWidget(hdr_frame)

        # ── KPI Row ──
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)
        self._kpi_total = _KpiCard()
        self._kpi_colors = _KpiCard()
        self._kpi_barcodes = _KpiCard()
        for card in (self._kpi_total, self._kpi_colors, self._kpi_barcodes):
            kpi_row.addWidget(card)
        outer.addLayout(kpi_row)

        # ── Category selector ──
        sel_row = QHBoxLayout()
        sel_row.setSpacing(8)
        lbl = QLabel(
            t("pt_lbl_category") if t("pt_lbl_category") != "pt_lbl_category"
            else "Category"
        )
        lbl.setObjectName("admin_form_card_title")
        sel_row.addWidget(lbl)
        self._cat_combo = QComboBox()
        self._cat_combo.setMinimumWidth(240)
        self._cat_combo.setMinimumHeight(36)
        self._cat_combo.currentIndexChanged.connect(self._on_cat_change)
        sel_row.addWidget(self._cat_combo)
        sel_row.addStretch()
        outer.addLayout(sel_row)

        # ── Part types + colors + barcodes (stacked, no splitter) ──

        # ── Part types table + buttons ──
        top_card = QFrame()
        top_card.setObjectName("admin_form_card")
        top_lay = QVBoxLayout(top_card)
        top_lay.setContentsMargins(16, 12, 16, 12)
        top_lay.setSpacing(8)

        top_hdr = QHBoxLayout()
        top_title = QLabel(
            t("pt_section_types") if t("pt_section_types") != "pt_section_types"
            else "Part Types"
        )
        top_title.setObjectName("admin_form_card_title")
        top_hdr.addWidget(top_title)
        top_hdr.addStretch()

        self._add_btn = QPushButton(t('pt_btn_add'))
        self._add_btn.setObjectName("admin_action_btn")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self._add)
        top_hdr.addWidget(self._add_btn)
        top_lay.addLayout(top_hdr)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            t("pt_col_key"), t("pt_col_name"), t("pt_col_color"), "",
        ])
        hh = self._table.horizontalHeader()
        hh.setMinimumSectionSize(40)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 80)
        self._table.setColumnWidth(2, 70)
        self._table.setColumnWidth(3, 220)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setMinimumHeight(200)
        self._table.itemSelectionChanged.connect(self._on_pt_select)
        top_lay.addWidget(self._table, 1)
        outer.addWidget(top_card)

        # ── Middle: Colors for selected part type ──
        color_card = QFrame()
        color_card.setObjectName("admin_form_card")
        color_lay = QVBoxLayout(color_card)
        color_lay.setContentsMargins(16, 12, 16, 12)
        color_lay.setSpacing(6)

        clr_hdr_row = QHBoxLayout()
        self._clr_hdr = QLabel(t("clr_title"))
        self._clr_hdr.setObjectName("admin_form_card_title")
        clr_hdr_row.addWidget(self._clr_hdr)
        clr_hdr_row.addStretch()
        self._clr_add_btn = QPushButton(t('clr_add'))
        self._clr_add_btn.setObjectName("admin_action_btn")
        self._clr_add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clr_add_btn.setFixedHeight(28)
        self._clr_add_btn.clicked.connect(self._add_color)
        clr_hdr_row.addWidget(self._clr_add_btn)
        color_lay.addLayout(clr_hdr_row)

        self._clr_hint = QLabel(t("clr_hint"))
        self._clr_hint.setObjectName("admin_form_card_desc")
        color_lay.addWidget(self._clr_hint)

        self._clr_container = QWidget()
        self._clr_flow = QHBoxLayout(self._clr_container)
        self._clr_flow.setContentsMargins(0, 0, 0, 0)
        self._clr_flow.setSpacing(6)
        self._clr_flow.addStretch()
        color_lay.addWidget(self._clr_container)

        self._clr_data: list[dict] = []
        outer.addWidget(color_card)

        # ── Bottom: Barcodes for selected part type ──
        btm_card = QFrame()
        btm_card.setObjectName("admin_form_card")
        btm_lay = QVBoxLayout(btm_card)
        btm_lay.setContentsMargins(16, 12, 16, 12)
        btm_lay.setSpacing(6)

        bc_hdr_row = QHBoxLayout()
        self._bc_hdr = QLabel(t("barcode_assign_title"))
        self._bc_hdr.setObjectName("admin_form_card_title")
        self._bc_save_all = QPushButton(f"  {t('shop_btn_save')}")
        self._bc_save_all.setObjectName("admin_action_btn")
        self._bc_save_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self._bc_save_all.setFixedHeight(28)
        self._bc_save_all.clicked.connect(self._save_all_barcodes)
        bc_hdr_row.addWidget(self._bc_hdr)
        bc_hdr_row.addStretch()
        bc_hdr_row.addWidget(self._bc_save_all)
        btm_lay.addLayout(bc_hdr_row)

        self._bc_hint = QLabel(t("barcode_none"))
        self._bc_hint.setObjectName("admin_form_card_desc")
        btm_lay.addWidget(self._bc_hint)

        self._bc_table = QTableWidget(0, 2)
        self._bc_table.setHorizontalHeaderLabels([t("mdl_col_model"), t("dlg_lbl_barcode")])
        bh = self._bc_table.horizontalHeader()
        bh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        bh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._bc_table.verticalHeader().setVisible(False)
        self._bc_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._bc_table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.SelectedClicked
        )
        self._bc_table.setAlternatingRowColors(True)
        self._bc_table.setMinimumHeight(200)
        btm_lay.addWidget(self._bc_table, 1)

        self._bc_item_ids: list[int] = []
        outer.addWidget(btm_card)

    # ── Category handling ────────────────────────────────────────────────────

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
            self._cat = None
            self._table.setRowCount(0)
            self._update_kpis()
            return
        self._cat = _cat_repo.get_by_id(cat_id)
        self._refresh_table()
        self._update_kpis()

    def _on_pt_select(self) -> None:
        pt = self._current_pt()
        self._refresh_colors(pt)
        self._refresh_barcodes(pt)

    def _update_kpis(self) -> None:
        """Update KPI cards with current data."""
        if not self._cat:
            self._kpi_total.set_data("PART TYPES", "0")
            self._kpi_colors.set_data("COLORS", "0")
            self._kpi_barcodes.set_data("BARCODES", "0")
            return

        total = len(self._cat.part_types)
        self._kpi_total.set_data(
            t("pt_kpi_total") if t("pt_kpi_total") != "pt_kpi_total" else "PART TYPES",
            str(total),
        )

        total_colors = 0
        for pt in self._cat.part_types:
            total_colors += len(_cat_repo.get_pt_colors(pt.id))
        self._kpi_colors.set_data(
            t("pt_kpi_colors") if t("pt_kpi_colors") != "pt_kpi_colors" else "COLORS",
            str(total_colors),
        )

        self._kpi_barcodes.set_data(
            t("pt_kpi_barcodes") if t("pt_kpi_barcodes") != "pt_kpi_barcodes" else "BARCODES",
            "—",
        )

    # ── Part types table ─────────────────────────────────────────────────────

    def _refresh_table(self) -> None:
        self._table.setRowCount(0)
        if not self._cat:
            return

        tk = THEME.tokens

        for pt in self._cat.part_types:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, self._ro(pt.key, pt.id))
            self._table.setItem(row, 1, self._ro(pt.name, pt.id))

            # Color swatch
            color_it = QTableWidgetItem(pt.accent_color)
            color_it.setBackground(QColor(pt.accent_color))
            color_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            color_it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._table.setItem(row, 2, color_it)

            # Action buttons in a single cell widget
            action_w = QWidget()
            action_w.setFixedSize(196, 40)
            action_lay = QHBoxLayout(action_w)
            action_lay.setContentsMargins(4, 2, 4, 2)
            action_lay.setSpacing(8)

            for icon_name, obj_name, tip, cb in [
                ("edit",   "admin_edit_btn", t("pt_btn_edit"),
                 lambda _, p=pt: self._edit_pt(p)),
                ("up",     "admin_edit_btn",
                 t("cat_btn_move_up") if t("cat_btn_move_up") != "cat_btn_move_up" else "Move Up",
                 lambda _, r=row: self._move_row_up(r)),
                ("down",   "admin_edit_btn",
                 t("cat_btn_move_down") if t("cat_btn_move_down") != "cat_btn_move_down" else "Move Down",
                 lambda _, r=row: self._move_row_down(r)),
                ("delete", "admin_del_btn", t("pt_btn_delete"),
                 lambda _, p=pt: self._delete_pt(p)),
            ]:
                btn = QPushButton()
                btn.setObjectName(obj_name)
                if icon_name in ("up", "down"):
                    btn.setIcon(get_button_icon(icon_name))
                else:
                    color = tk.blue if icon_name == "edit" else tk.red
                    btn.setIcon(get_colored_icon(icon_name, color))
                btn.setIconSize(QSize(15, 15))
                btn.setToolTip(tip)
                btn.setFixedSize(36, 36)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(cb)
                action_lay.addWidget(btn)

            self._table.setCellWidget(row, 3, action_w)
            self._table.setRowHeight(row, 48)

        self._refresh_barcodes(None)

    # ── Barcode table ────────────────────────────────────────────────────────

    def _refresh_barcodes(self, pt: PartTypeConfig | None) -> None:
        self._bc_table.setRowCount(0)
        self._bc_item_ids.clear()
        if not pt:
            self._bc_hdr.setText(t("barcode_assign_title"))
            self._bc_hint.setText(t("pt_no_selection"))
            self._bc_hint.show()
            return

        self._bc_hdr.setText(f"{t('barcode_assign_title')}  —  {pt.name}")
        all_items = _item_repo.get_by_part_type(pt.id)
        items = [i for i in all_items if not i.color]
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

            model_it = QTableWidgetItem(item.model_name or item.display_name)
            model_it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._bc_table.setItem(row, 0, model_it)

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
                bc_item.setForeground(QColor(tk.green))
                saved += 1
            except Exception as e:
                bc_item.setForeground(QColor(tk.red))
                errors += 1

        if errors:
            QMessageBox.warning(
                self, t("barcode_assign_title"),
                f"{saved} saved, {errors} failed (duplicate barcodes)",
            )
        else:
            self._bc_hint.setText(t("barcode_saved"))
            self._bc_hint.show()

    # ── Color management ─────────────────────────────────────────────────────

    def _refresh_colors(self, pt: PartTypeConfig | None) -> None:
        while self._clr_flow.count() > 1:
            item = self._clr_flow.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._clr_data.clear()
        if not pt:
            self._clr_hdr.setText(
                t("clr_title") if t("clr_title") != "clr_title" else "COLORS"
            )
            self._clr_hint.setText("Select a part type to manage colors")
            self._clr_hint.show()
            return

        colors = _cat_repo.get_pt_colors(pt.id)
        self._clr_data = colors
        self._clr_hdr.setText(f"{t('clr_title')} — {pt.name}")

        if not colors:
            self._clr_hint.setText(t("clr_none"))
            self._clr_hint.show()
        else:
            self._clr_hint.hide()

        tk = THEME.tokens
        for clr in colors:
            hex_color = self._ALL_COLORS.get(clr["color_name"], "#888888")
            is_light = QColor(hex_color).lightness() > 180

            chip = QFrame()
            chip_lay = QHBoxLayout(chip)
            chip_lay.setContentsMargins(6, 4, 4, 4)
            chip_lay.setSpacing(4)

            swatch = QLabel()
            swatch.setFixedSize(20, 20)
            border = "#666" if is_light else "transparent"
            swatch.setStyleSheet(
                f"background:{hex_color}; border-radius:4px; border:1px solid {border};"
            )
            chip_lay.addWidget(swatch)

            name_lbl = QLabel(clr["color_name"])
            name_lbl.setStyleSheet(f"font-size:11px; font-weight:600; color:{tk.t1};")
            chip_lay.addWidget(name_lbl)

            rm_btn = QToolButton()
            rm_btn.setText("×")
            rm_btn.setFixedSize(18, 18)
            rm_btn.setStyleSheet(
                f"QToolButton {{ color:{tk.red}; background:transparent; border:none; font-size:13px; }}"
                f"QToolButton:hover {{ background:{tk.card2}; border-radius:3px; }}"
            )
            rm_btn.clicked.connect(lambda _=False, cid=clr["id"]: self._remove_color(cid))
            chip_lay.addWidget(rm_btn)

            chip.setStyleSheet(
                f"QFrame {{ background:{tk.card2}; border:1px solid {tk.border}; border-radius:6px; }}"
            )
            self._clr_flow.insertWidget(self._clr_flow.count() - 1, chip)

    _ALL_COLORS = {
        "Black": "#333333",
        "Blue": "#2563EB",
        "Silver": "#A0A0B0",
        "Gold": "#D4A520",
        "Green": "#10B981",
        "Purple": "#8B5CF6",
        "White": "#E0E0E0",
    }

    def _add_color(self) -> None:
        pt = self._current_pt()
        if not pt:
            QMessageBox.information(self, "Colors", t("pt_no_selection"))
            return

        existing = {c["color_name"] for c in self._clr_data}
        available = {k: v for k, v in self._ALL_COLORS.items() if k not in existing}
        if not available:
            QMessageBox.information(self, "Colors", t("clr_all_added"))
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(t("clr_select_title"))
        dlg.setMinimumWidth(320)
        from app.core.theme import THEME as _T
        _T.apply(dlg)

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 16)
        lay.setSpacing(12)

        hdr = QLabel(t("clr_select_hdr"))
        hdr.setObjectName("dlg_header")
        lay.addWidget(hdr)

        grid = QHBoxLayout()
        grid.setSpacing(8)
        selected: dict[str, bool] = {}
        btn_map: dict[str, QPushButton] = {}

        for color_name, hex_val in available.items():
            btn = QPushButton()
            btn.setFixedSize(44, 44)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(color_name)
            is_light = QColor(hex_val).lightness() > 180
            border = "#666" if is_light else "transparent"
            selected[color_name] = False
            btn_map[color_name] = btn

            def _toggle(_, c=color_name, b=btn, h=hex_val, il=is_light):
                selected[c] = not selected[c]
                brd = "#666" if il else "transparent"
                if selected[c]:
                    b.setStyleSheet(
                        f"QPushButton {{ background:{h}; border:3px solid {_T.tokens.green}; border-radius:8px; }}"
                    )
                else:
                    b.setStyleSheet(
                        f"QPushButton {{ background:{h}; border:2px solid {brd}; border-radius:8px; }}"
                        f"QPushButton:hover {{ border:3px solid {_T.tokens.green}; }}"
                    )

            btn.setStyleSheet(
                f"QPushButton {{ background:{hex_val}; border:2px solid {border}; border-radius:8px; }}"
                f"QPushButton:hover {{ border:3px solid {_T.tokens.green}; }}"
            )
            btn.clicked.connect(_toggle)
            grid.addWidget(btn)

        grid.addStretch()
        lay.addLayout(grid)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        sel_all = QPushButton(t("clr_select_all"))
        sel_all.setObjectName("btn_ghost")
        sel_all.setFixedHeight(32)

        def _select_all():
            for c in selected:
                selected[c] = True
                b = btn_map[c]
                h = available[c]
                b.setStyleSheet(
                    f"QPushButton {{ background:{h}; border:3px solid {_T.tokens.green}; border-radius:8px; }}"
                )

        sel_all.clicked.connect(_select_all)
        btn_row.addWidget(sel_all)
        btn_row.addStretch()

        cancel = QPushButton(t("op_cancel"))
        cancel.setObjectName("btn_ghost")
        cancel.setFixedHeight(32)
        cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel)

        confirm = QPushButton(t("clr_add_selected"))
        confirm.setObjectName("btn_primary")
        confirm.setFixedHeight(32)
        confirm.clicked.connect(dlg.accept)
        btn_row.addWidget(confirm)
        lay.addLayout(btn_row)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            added = [c for c, v in selected.items() if v]
            if added:
                for color in added:
                    _cat_repo.add_pt_color(pt.id, color, color[:3].upper())
                from app.core.database import ensure_matrix_entries
                ensure_matrix_entries()
                self._refresh_colors(pt)

    def _remove_color(self, color_id: int) -> None:
        pt = self._current_pt()
        _cat_repo.remove_pt_color(color_id)
        if pt:
            self._refresh_colors(pt)

    # ── CRUD ─────────────────────────────────────────────────────────────────

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
            self._update_kpis()

    def _edit_pt(self, pt: PartTypeConfig) -> None:
        if not self._cat:
            return
        existing = [p.key for p in self._cat.part_types]
        dlg = _PartTypeFormDialog(existing, pt=pt, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            key, name, color = dlg.values()
            _cat_repo.update_part_type(pt.id, key, name, color)
            self._cat = _cat_repo.get_by_id(self._cat.id)
            self._refresh_table()

    def _edit(self) -> None:
        pt = self._current_pt()
        if not pt or not self._cat:
            QMessageBox.information(self, t("pt_btn_edit"), t("pt_no_selection"))
            return
        self._edit_pt(pt)

    def _delete_pt(self, pt: PartTypeConfig) -> None:
        if not _cat_repo.delete_part_type(pt.id):
            QMessageBox.warning(self, t("pt_btn_delete"), t("pt_delete_blocked"))
            return
        self._cat = _cat_repo.get_by_id(self._cat.id)
        self._refresh_table()
        self._update_kpis()

    def _delete(self) -> None:
        pt = self._current_pt()
        if not pt:
            QMessageBox.information(self, t("pt_btn_delete"), t("pt_no_selection"))
            return
        self._delete_pt(pt)

    def _move_row_up(self, row: int) -> None:
        if row <= 0 or not self._cat:
            return
        ids = [pt.id for pt in self._cat.part_types]
        ids[row - 1], ids[row] = ids[row], ids[row - 1]
        _cat_repo.reorder_part_types(ids)
        self._cat = _cat_repo.get_by_id(self._cat.id)
        self._refresh_table()
        self._table.setCurrentCell(row - 1, 0)

    def _move_row_down(self, row: int) -> None:
        if not self._cat or row < 0 or row >= len(self._cat.part_types) - 1:
            return
        ids = [pt.id for pt in self._cat.part_types]
        ids[row], ids[row + 1] = ids[row + 1], ids[row]
        _cat_repo.reorder_part_types(ids)
        self._cat = _cat_repo.get_by_id(self._cat.id)
        self._refresh_table()
        self._table.setCurrentCell(row + 1, 0)

    def _move_up(self) -> None:
        self._move_row_up(self._table.currentRow())

    def _move_down(self) -> None:
        self._move_row_down(self._table.currentRow())

    def reload(self) -> None:
        self._load_categories()

    @staticmethod
    def _ro(text: str, pt_id: int) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        it.setData(Qt.ItemDataRole.UserRole, pt_id)
        return it
