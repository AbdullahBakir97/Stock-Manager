"""
app/ui/tabs/matrix_tab.py — Generic matrix inventory tab.

One class drives every category tab: Displays, Batteries, Cases, Cameras,
Charging Ports, Back Covers — whatever is active in the DB.
"""
from __future__ import annotations

from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QComboBox, QLabel,
    QPushButton, QDialog, QMessageBox,
)

from app.models.category import CategoryConfig
from app.repositories.category_repo import CategoryRepository
from app.repositories.model_repo import ModelRepository
from app.repositories.item_repo import ItemRepository
from app.ui.components.matrix_widget import MatrixWidget
from app.ui.dialogs.matrix_dialogs import AddModelDialog
from app.core.icon_utils import get_button_icon
from app.ui.tabs.base_tab import BaseTab
from app.core.i18n import t

_cat_repo   = CategoryRepository()
_model_repo = ModelRepository()
_item_repo  = ItemRepository()


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

        # ── Compact toolbar ───────────────────────────────────────────────────
        tb = QHBoxLayout()
        tb.setContentsMargins(4, 0, 4, 0)
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
        lay.addLayout(tb)

        # ── Matrix (takes maximum space) ──────────────────────────────────────
        self._table = MatrixWidget(refresh_cb=self.refresh, parent=self)
        lay.addWidget(self._table, 1)

        self._populate_brand_combo()
        self.refresh()

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
        brand    = self._selected_brand()
        models   = _model_repo.get_all(brand=brand)
        item_map = _item_repo.get_matrix_items(self._cat.id, brand=brand)
        self._table.load(self._cat, models, item_map)

    def retranslate(self) -> None:
        self._brand_lbl.setText(t("disp_filter_brand"))
        self._add_btn.setText(t("disp_add_model"))
        self._brand_combo.blockSignals(True)
        self._brand_combo.setItemText(0, t("disp_all_brands"))
        self._brand_combo.blockSignals(False)
        self._table.retranslate()
        self.refresh()
