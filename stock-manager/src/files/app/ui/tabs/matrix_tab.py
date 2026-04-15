"""
app/ui/tabs/matrix_tab.py — Generic matrix inventory tab.

One class drives every category tab: Displays, Batteries, Cases, Cameras,
Charging Ports, Back Covers — whatever is active in the DB.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QWidget,
    QPushButton, QDialog, QMessageBox, QFrame,
)
from app.core.theme import THEME

from app.models.category import CategoryConfig
from app.repositories.category_repo import CategoryRepository
from app.repositories.model_repo import ModelRepository
from app.repositories.item_repo import ItemRepository
from app.ui.components.matrix_widget import FrozenMatrixContainer
from app.ui.dialogs.matrix_dialogs import AddModelDialog
from app.core.icon_utils import get_button_icon
from app.ui.tabs.base_tab import BaseTab
from app.core.i18n import t

_cat_repo   = CategoryRepository()
_model_repo = ModelRepository()
_item_repo  = ItemRepository()


class _MatrixSectionHeader(QWidget):
    """Clickable row: label + chevron — click anywhere to expand/collapse.
    Same style as inventory page section headers."""

    toggled = pyqtSignal(bool)

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._expanded = True
        self.setFixedHeight(24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 0, 6, 0)
        lay.setSpacing(4)

        self._lbl = QLabel(title.upper())
        self._lbl.setObjectName("inv_section_lbl")
        lay.addWidget(self._lbl)
        lay.addStretch()

        self._btn = QPushButton("▾")
        self._btn.setObjectName("inv_section_btn")
        self._btn.setFixedSize(20, 20)
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn.clicked.connect(self._on_click)
        lay.addWidget(self._btn)

        self._apply_style()

    def _apply_style(self):
        tk = THEME.tokens
        self._lbl.setStyleSheet(
            f"font-size:10px; font-weight:700; color:{tk.t4}; letter-spacing:0.8px;"
        )
        self._btn.setStyleSheet(f"""
            QPushButton#inv_section_btn {{
                background: transparent; color: {tk.t4};
                border: none; font-size: 11px; border-radius: 4px;
            }}
            QPushButton#inv_section_btn:hover {{
                background: {tk.border}; color: {tk.t1};
            }}
        """)

    def _on_click(self):
        self._expanded = not self._expanded
        self._btn.setText("▾" if self._expanded else "▸")
        self.toggled.emit(self._expanded)

    def mousePressEvent(self, _event):
        self._on_click()

    def apply_theme(self):
        self._apply_style()


class MatrixTab(BaseTab):
    """
    Generic inventory tab for any part category.
    Instantiate with the DB category key: MatrixTab("displays").
    """

    def __init__(self, category_key: str, parent=None):
        super().__init__(parent)
        self._cat_key = category_key
        self._cat: CategoryConfig | None = _cat_repo.get_by_key(category_key)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(4)

        # ── Collapsible toolbar header (same style as inventory sections) ─────
        self._tb_header = _MatrixSectionHeader(t("disp_filter_brand").upper() + " & LEGEND")
        self._tb_header.toggled.connect(self._on_toolbar_toggle)
        lay.addWidget(self._tb_header)

        self._toolbar_widget = QWidget()
        tb = QHBoxLayout(self._toolbar_widget)
        tb.setContentsMargins(4, 4, 4, 4)
        tb.setSpacing(8)

        self._brand_lbl = QLabel(t("disp_filter_brand"))
        self._brand_lbl.setObjectName("card_label")

        self._brand_combo = QComboBox()
        self._brand_combo.setMinimumHeight(32)
        self._brand_combo.setMinimumWidth(140)
        self._brand_combo.currentIndexChanged.connect(self.refresh)

        self._add_btn = QPushButton(t("disp_add_model"))
        self._add_btn.setObjectName("btn_primary")
        self._add_btn.setMaximumHeight(32)
        self._add_btn.clicked.connect(self._add_model)

        self._ref_btn = QPushButton(); self._ref_btn.setObjectName("btn_secondary")
        self._ref_btn.setIcon(get_button_icon("refresh"))
        self._ref_btn.setIconSize(QSize(14, 14))
        self._ref_btn.setMaximumHeight(32)
        self._ref_btn.clicked.connect(self.refresh)

        tb.addWidget(self._brand_lbl)
        tb.addWidget(self._brand_combo)
        tb.addStretch()

        # Compact legend — part type color chips
        self._legend_chips: list[QLabel] = []
        if self._cat:
            for pt in self._cat.part_types:
                rv = int(pt.accent_color[1:3], 16)
                gv = int(pt.accent_color[3:5], 16)
                bv = int(pt.accent_color[5:7], 16)
                chip = QLabel(pt.name)
                chip.setStyleSheet(
                    f"color:{pt.accent_color}; font-size:7pt; font-weight:700; "
                    f"background:rgba({rv},{gv},{bv},35); border-radius:3px; padding:1px 5px;"
                )
                tb.addWidget(chip)
                self._legend_chips.append(chip)

        tb.addWidget(self._add_btn)
        tb.addWidget(self._ref_btn)
        lay.addWidget(self._toolbar_widget)

        # ── Content area ──────────────────────────────────────────────────────
        from PyQt6.QtWidgets import QStackedWidget, QScrollArea

        self._content_stack = QStackedWidget()

        # Page 0: single brand — full height, table scrolls internally
        self._single_container = FrozenMatrixContainer(refresh_cb=self.refresh, parent=self)
        self._content_stack.addWidget(self._single_container)

        # Page 1: all brands — outer scroll, each section full-sized
        self._multi_scroll = QScrollArea()
        self._multi_scroll.setWidgetResizable(True)
        self._multi_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._multi_inner = QWidget()
        self._multi_lay = QVBoxLayout(self._multi_inner)
        self._multi_lay.setContentsMargins(0, 0, 0, 0)
        self._multi_lay.setSpacing(6)
        self._multi_scroll.setWidget(self._multi_inner)
        self._content_stack.addWidget(self._multi_scroll)

        self._brand_widgets: list[QWidget] = []
        self._container = self._single_container
        self._table = self._single_container.data_table
        lay.addWidget(self._content_stack, 1)

        self._populate_brand_combo()
        self.refresh()

    def _on_toolbar_toggle(self, expanded: bool) -> None:
        """Collapse/expand the toolbar widget — table takes freed space."""
        self._toolbar_widget.setVisible(expanded)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _populate_brand_combo(self) -> None:
        self._brand_combo.blockSignals(True)
        prev = self._brand_combo.currentText()
        self._brand_combo.clear()
        self._brand_combo.addItem(t("disp_all_brands"), userData=None)
        for brand in _model_repo.get_brands():
            self._brand_combo.addItem(brand, userData=brand)
        idx = self._brand_combo.findText(prev)
        if idx >= 0:
            self._brand_combo.setCurrentIndex(idx)
        self._brand_combo.blockSignals(False)

    def _selected_brand(self) -> str | None:
        return self._brand_combo.currentData()

    def _add_model(self) -> None:
        brands = _model_repo.get_brands()
        dlg = AddModelDialog(brands, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        brand = dlg.brand()
        name  = dlg.model_name()
        if _model_repo.exists(name):
            QMessageBox.warning(
                self, t("dlg_required_title"),
                f"'{name}' " + t("disp_model_empty"),
            )
            return
        _model_repo.add(brand, name)
        self._populate_brand_combo()
        idx = self._brand_combo.findText(brand)
        if idx >= 0:
            self._brand_combo.setCurrentIndex(idx)
        else:
            self.refresh()

    # ── BaseTab interface ─────────────────────────────────────────────────────

    def refresh(self) -> None:
        if not self._cat:
            self._cat = _cat_repo.get_by_key(self._cat_key)
        if not self._cat:
            return

        from app.models.category import CategoryConfig
        brand = self._selected_brand()

        if brand:
            # ── Single brand: full height, table scrolls internally ──
            self._content_stack.setCurrentIndex(0)

            models = _model_repo.get_all(brand=brand)
            item_map = _item_repo.get_matrix_items(self._cat.id, brand=brand)
            used_pt_keys = {key[1] for key in item_map.keys()}
            filtered_pts = [pt for pt in self._cat.part_types if pt.key in used_pt_keys]

            filtered_cat = CategoryConfig(
                id=self._cat.id, key=self._cat.key,
                name_en=self._cat.name_en, name_de=self._cat.name_de,
                name_ar=self._cat.name_ar, sort_order=self._cat.sort_order,
                icon=self._cat.icon, is_active=self._cat.is_active,
                part_types=filtered_pts or self._cat.part_types,
            )
            self._single_container.load(filtered_cat, models, item_map)
            self._container = self._single_container
            self._table = self._single_container.data_table
        else:
            # ── All brands: outer scroll, each section full-sized ──
            self._content_stack.setCurrentIndex(1)

            # Clear old sections
            for w in self._brand_widgets:
                w.deleteLater()
            self._brand_widgets.clear()
            while self._multi_lay.count():
                item = self._multi_lay.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            for b in _model_repo.get_brands():
                self._add_brand_section(b)

            self._multi_lay.addStretch()

    def _add_brand_section(self, brand: str) -> None:
        """Add one full-sized brand section to the scrollable all-brands page."""
        from app.models.category import CategoryConfig

        models = _model_repo.get_all(brand=brand)
        if not models:
            return

        item_map = _item_repo.get_matrix_items(self._cat.id, brand=brand)
        used_pt_keys = {key[1] for key in item_map.keys()}
        filtered_pts = [pt for pt in self._cat.part_types if pt.key in used_pt_keys]

        filtered_cat = CategoryConfig(
            id=self._cat.id, key=self._cat.key,
            name_en=self._cat.name_en, name_de=self._cat.name_de,
            name_ar=self._cat.name_ar, sort_order=self._cat.sort_order,
            icon=self._cat.icon, is_active=self._cat.is_active,
            part_types=filtered_pts or self._cat.part_types,
        )

        # Brand header
        tk = THEME.tokens
        header = QLabel(f"  {brand}")
        header.setFixedHeight(28)
        header.setStyleSheet(
            f"background:{tk.card2}; color:{tk.t1}; "
            f"font-size:12px; font-weight:700; "
            f"border-left:3px solid {tk.green}; padding-left:10px;"
        )
        self._multi_lay.addWidget(header)
        self._brand_widgets.append(header)

        # Matrix container — large minimum height, scrolls internally
        # so banner + column headers stay STICKY at top of each section
        container = FrozenMatrixContainer(refresh_cb=self.refresh, parent=self)
        container.load(filtered_cat, models, item_map)

        # Set height: full content if small, or a generous minimum if large
        tbl = container.data_table
        banner_h = 30
        header_h = tbl.horizontalHeader().height()
        rows_h = sum(tbl.rowHeight(r) for r in range(tbl.rowCount()))
        content_h = banner_h + header_h + rows_h + 16

        # If content fits in 500px, show it all; otherwise cap at 500
        # and let internal scroll handle the rest (headers stay sticky)
        container.setFixedHeight(min(content_h, 500))

        self._multi_lay.addWidget(container)
        self._brand_widgets.append(container)

        self._container = container
        self._table = container.data_table

    def apply_theme(self) -> None:
        """Rebuild legend chip inline styles with current theme colors."""
        if self._cat:
            for i, chip in enumerate(self._legend_chips):
                if i < len(self._cat.part_types):
                    pt = self._cat.part_types[i]
                    rv = int(pt.accent_color[1:3], 16)
                    gv = int(pt.accent_color[3:5], 16)
                    bv = int(pt.accent_color[5:7], 16)
                    chip.setStyleSheet(
                        f"color:{pt.accent_color}; font-size:7pt; font-weight:700; "
                        f"background:rgba({rv},{gv},{bv},35); border-radius:3px; padding:1px 5px;"
                    )
        # Refresh the matrix table to pick up new theme colors
        self.refresh()

    def retranslate(self) -> None:
        self._brand_lbl.setText(t("disp_filter_brand"))
        self._add_btn.setText(t("disp_add_model"))
        self._brand_combo.blockSignals(True)
        self._brand_combo.setItemText(0, t("disp_all_brands"))
        self._brand_combo.blockSignals(False)
        self._container.retranslate()
        self.refresh()
