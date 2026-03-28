"""
displays_tab.py — Displays inventory tab for Stock Manager Pro.

Matrix view: phone models (rows) × display types (column groups).
Each group has 4 columns: Stamm-Zahl | Best-Bung (auto) | Stock | Inventur

  Stamm-Zahl  — minimum/target stock level (editable, double-click)
  Best-Bung   — Stock − Stamm-Zahl (auto-calculated, read-only)
                negative = how many units needed to reach minimum
                positive = surplus above minimum
  Stock       — current stock count (editable, double-click)
  Inventur    — physical count during stock-take (editable, double-click)

Features:
  - Brand filter combobox (All / Apple / Samsung / custom…)
  - Add Model button — brand (select or type), model name (type or select)
  - 3-language translations (EN / DE / AR)
  - Mock data visible on first run
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QPushButton, QDialog, QSpinBox, QComboBox,
    QFormLayout, QDialogButtonBox, QMessageBox, QAbstractItemView, QFrame,
    QLineEdit,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

import database as db
from theme import THEME, qc
from i18n import t


# ── Constants ─────────────────────────────────────────────────────────────────

# (db_key, column-header label, accent hex)  — fixed display types
DISPLAY_TYPES: list[tuple[str, str, str]] = [
    ("JK_INCELL_FHD",     "(JK) incell FHD",          "#4A9EFF"),
    ("DD_SOFT_OLED",      "(D.D) Soft-OLED",           "#32D583"),
    ("DD_SOFT_OLED_DIAG", "(D.D) Soft-OLED Diagnose",  "#C17BFF"),
    ("ORG_PULLED",        "ORG-Pulled",                "#FF9F3A"),
    ("ORG_DIAGNOSE_USED", "ORG-Diagnose USED",         "#FF5A52"),
]

TOTAL_COLS  = 1 + 4 * len(DISPLAY_TYPES)   # 21
HEADER_ROW  = 0                             # row 0 = colour-coded group banner

COL_W = {"model": 140, "stamm": 82, "bestbung": 82, "stock": 72, "inventur": 82}


def _base(ti: int) -> int:
    """First column index for display-type i (Stamm-Zahl column)."""
    return 1 + ti * 4


# ── Dialogs ───────────────────────────────────────────────────────────────────

class _StockOpDialog(QDialog):
    """Stock IN / OUT / Set-Exact dialog for one model × display-type cell."""

    def __init__(self, model_name: str, dtype_lbl: str,
                 current_stock: int, stamm_zahl: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{model_name}  ·  {dtype_lbl}")
        self.setModal(True); self.setMinimumWidth(370)
        THEME.apply(self)
        tk  = THEME.tokens
        lay = QVBoxLayout(self)
        lay.setSpacing(14); lay.setContentsMargins(24, 24, 24, 20)

        # Title
        title = QLabel(f"{model_name}  ·  {dtype_lbl}")
        title.setObjectName("dlg_header")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        # Info line showing Best-Bung context
        needed = stamm_zahl - current_stock
        if needed > 0:
            info_html = (
                f"Stock: <b>{current_stock}</b>  │  Stamm-Zahl: <b>{stamm_zahl}</b>  │  "
                f"<span style='color:{tk.red}'>"
                + t("disp_need_more", n=needed) + "</span>"
            )
        elif needed < 0:
            info_html = (
                f"Stock: <b>{current_stock}</b>  │  Stamm-Zahl: <b>{stamm_zahl}</b>  │  "
                f"<span style='color:{tk.green}'>"
                + t("disp_surplus", n=abs(needed)) + "</span>"
            )
        else:
            info_html = (
                f"Stock: <b>{current_stock}</b>  │  Stamm-Zahl: <b>{stamm_zahl}</b>  │  "
                f"<span style='color:{tk.yellow}'>{t('disp_tip_bb_zero')}</span>"
            )
        info = QLabel(info_html)
        info.setTextFormat(Qt.TextFormat.RichText)
        info.setObjectName("card_meta_dim")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(info)

        # Operation toggle buttons
        self._op = "IN"
        op_row = QHBoxLayout(); op_row.setSpacing(6)
        self._btn_in  = QPushButton(t("disp_op_in"));  self._btn_in.setObjectName("btn_confirm_in")
        self._btn_out = QPushButton(t("disp_op_out")); self._btn_out.setObjectName("btn_confirm_out")
        self._btn_set = QPushButton(t("disp_op_set")); self._btn_set.setObjectName("btn_confirm_adj")
        for b in (self._btn_in, self._btn_out, self._btn_set):
            b.setCheckable(True); op_row.addWidget(b)
        self._btn_in.setChecked(True)
        self._btn_in.clicked.connect(lambda: self._set_op("IN"))
        self._btn_out.clicked.connect(lambda: self._set_op("OUT"))
        self._btn_set.clicked.connect(lambda: self._set_op("ADJUST"))
        lay.addLayout(op_row)

        # Quantity / exact value
        form = QFormLayout(); form.setSpacing(10)
        self._qty_lbl = QLabel(t("disp_qty_lbl"))
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(0, 9999)
        self.qty_spin.setValue(max(1, needed) if needed > 0 else 1)
        form.addRow(self._qty_lbl, self.qty_spin)
        lay.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _set_op(self, op: str):
        self._op = op
        self._btn_in.setChecked(op == "IN")
        self._btn_out.setChecked(op == "OUT")
        self._btn_set.setChecked(op == "ADJUST")
        self._qty_lbl.setText(t("disp_exact_lbl") if op == "ADJUST" else t("disp_qty_lbl"))

    def result_data(self) -> tuple[str, int]:
        return self._op, self.qty_spin.value()


class _ThresholdDialog(QDialog):
    """Set Stamm-Zahl (minimum/target stock level)."""

    def __init__(self, model_name: str, dtype_lbl: str, current_stamm: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{t('disp_dlg_stamm')} — {model_name}")
        self.setModal(True); self.setMinimumWidth(340)
        THEME.apply(self)
        lay = QVBoxLayout(self)
        lay.setSpacing(14); lay.setContentsMargins(24, 24, 24, 20)

        title = QLabel(f"{t('disp_dlg_stamm')}\n{model_name}  ·  {dtype_lbl}")
        title.setObjectName("dlg_header")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        hint = QLabel(t("disp_stamm_hint"))
        hint.setObjectName("card_meta_dim")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        lay.addWidget(hint)

        form = QFormLayout(); form.setSpacing(10)
        self.spin = QSpinBox()
        self.spin.setRange(0, 9999)
        self.spin.setValue(current_stamm)
        form.addRow("Stamm-Zahl:", self.spin)
        lay.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def value(self) -> int:
        return self.spin.value()


class _InventurDialog(QDialog):
    """Record physical inventory count (Inventur)."""

    def __init__(self, model_name: str, dtype_lbl: str, current_stock: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{t('disp_dlg_inv')} — {model_name}")
        self.setModal(True); self.setMinimumWidth(320)
        THEME.apply(self)
        lay = QVBoxLayout(self)
        lay.setSpacing(14); lay.setContentsMargins(24, 24, 24, 20)

        title = QLabel(f"{t('disp_dlg_inv')}\n{model_name}  ·  {dtype_lbl}")
        title.setObjectName("dlg_header")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        info = QLabel(t("disp_sys_stock", n=current_stock))
        info.setObjectName("card_meta_dim")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(info)

        form = QFormLayout(); form.setSpacing(10)
        self.spin = QSpinBox()
        self.spin.setRange(0, 9999)
        self.spin.setValue(current_stock)
        form.addRow(t("disp_phys_count"), self.spin)
        lay.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def value(self) -> int:
        return self.spin.value()


class _AddModelDialog(QDialog):
    """Add a new phone model — brand (select or type new) + model name."""

    def __init__(self, existing_brands: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("disp_dlg_add_model"))
        self.setModal(True); self.setMinimumWidth(400)
        THEME.apply(self)
        lay = QVBoxLayout(self)
        lay.setSpacing(14); lay.setContentsMargins(24, 24, 24, 20)

        title = QLabel(t("disp_dlg_add_model"))
        title.setObjectName("dlg_header")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        form = QFormLayout(); form.setSpacing(12)

        # Brand — editable combobox (select existing or type new)
        self.brand_combo = QComboBox()
        self.brand_combo.setEditable(True)
        self.brand_combo.setMinimumHeight(40)
        self.brand_combo.addItems(existing_brands)
        self.brand_combo.setCurrentText("")
        self.brand_combo.lineEdit().setPlaceholderText(t("disp_ph_brand"))
        form.addRow(t("disp_lbl_brand"), self.brand_combo)

        # Model name — editable combobox (type or pick existing models for selected brand)
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setMinimumHeight(40)
        self.model_combo.lineEdit().setPlaceholderText(t("disp_ph_model"))
        form.addRow(t("disp_lbl_model_name"), self.model_combo)

        lay.addLayout(form)

        # Update model list when brand changes
        self.brand_combo.currentTextChanged.connect(self._on_brand_changed)

        # Save button
        self.save_btn = QPushButton(t("disp_save_model"))
        self.save_btn.setObjectName("btn_primary")
        self.save_btn.clicked.connect(self._validate)

        cancel_btn = QPushButton(t("op_cancel"))
        cancel_btn.setObjectName("btn_ghost")
        cancel_btn.clicked.connect(self.reject)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        btn_row.addWidget(cancel_btn); btn_row.addWidget(self.save_btn)
        lay.addLayout(btn_row)

    def _on_brand_changed(self, brand: str):
        """Populate model list with existing models for this brand."""
        self.model_combo.clear()
        if brand.strip():
            models = db.get_phone_models(brand=brand.strip())
            self.model_combo.addItems([m["name"] for m in models])
            self.model_combo.setCurrentText("")

    def _validate(self):
        brand = self.brand_combo.currentText().strip()
        name  = self.model_combo.currentText().strip()
        if not brand or not name:
            QMessageBox.warning(self, t("dlg_required_title"), t("disp_model_empty"))
            return
        self.accept()

    def brand(self) -> str:
        return self.brand_combo.currentText().strip()

    def model_name(self) -> str:
        return self.model_combo.currentText().strip()


# ── Matrix Table ──────────────────────────────────────────────────────────────

class _DisplayMatrix(QTableWidget):
    """
    Wide matrix table replicating the Excel layout exactly.

    Row 0        — coloured group-name banner (one merged cell per display type)
    Rows 1…n     — one row per phone model

    Column groups (4 cols each × 5 types = 20 data cols + 1 model col = 21):
      Stamm-Zahl | Best-Bung | Stock | Inventur
    """

    def __init__(self, refresh_cb, parent=None):
        super().__init__(parent)
        self._refresh_cb = refresh_cb
        self._build_headers()
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(False)
        self.setShowGrid(True)
        self.cellDoubleClicked.connect(self._on_dbl)

    def _build_headers(self):
        self.setColumnCount(TOTAL_COLS)
        labels = [t("disp_col_model")]
        for _ in DISPLAY_TYPES:
            labels += ["Stamm-Zahl", "Best-Bung", t("disp_col_stock"), "Inventur"]
        self.setHorizontalHeaderLabels(labels)

        hh = self.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.setColumnWidth(0, COL_W["model"])
        for i in range(len(DISPLAY_TYPES)):
            b = _base(i)
            self.setColumnWidth(b,     COL_W["stamm"])
            self.setColumnWidth(b + 1, COL_W["bestbung"])
            self.setColumnWidth(b + 2, COL_W["stock"])
            self.setColumnWidth(b + 3, COL_W["inventur"])

    def retranslate(self):
        """Rebuild column headers in the active language."""
        labels = [t("disp_col_model")]
        for _ in DISPLAY_TYPES:
            labels += ["Stamm-Zahl", "Best-Bung", t("disp_col_stock"), "Inventur"]
        self.setHorizontalHeaderLabels(labels)

    # ── Load data ──────────────────────────────────────────────────────────────

    def load(self, models: list[dict], stock_map: dict):
        """
        models    — [{id, name, brand}]
        stock_map — {(model_id, display_type): {stamm_zahl, stock, inventur}}
        """
        tk = THEME.tokens
        self.clearContents()
        self.setRowCount(1 + len(models))

        # ── Row 0: coloured group-name banner ──────────────────────────────────
        self.setRowHeight(HEADER_ROW, 30)
        corner = self._ro("")
        corner.setBackground(QColor(tk.card2))
        self.setItem(HEADER_ROW, 0, corner)

        for ti, (_, lbl, color) in enumerate(DISPLAY_TYPES):
            b = _base(ti)
            self.setSpan(HEADER_ROW, b, 1, 4)
            it = self._ro(lbl)
            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it.setBackground(qc(color, 0x35))
            it.setForeground(QColor(color))
            it.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.setItem(HEADER_ROW, b, it)

        # ── Model rows ─────────────────────────────────────────────────────────
        for ri, model in enumerate(models):
            r   = ri + 1
            mid = model["id"]
            nm  = model["name"]
            self.setRowHeight(r, 40)

            # Model name
            name_it = self._ro(f"  {nm}")
            name_it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            name_it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            name_it.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            name_it.setForeground(QColor(tk.t1))
            self.setItem(r, 0, name_it)

            # Display-type cells
            for ti, (dtype_key, dtype_lbl, color) in enumerate(DISPLAY_TYPES):
                b     = _base(ti)
                entry = stock_map.get((mid, dtype_key),
                                      {"stamm_zahl": 0, "stock": 0, "inventur": None})
                stamm    = entry.get("stamm_zahl", 0)
                stock    = entry.get("stock",      0)
                inventur = entry.get("inventur")
                best     = stock - stamm

                meta = {
                    "model_id": mid, "model_name": nm,
                    "dtype_key": dtype_key, "dtype_lbl": dtype_lbl,
                    "stamm": stamm, "stock": stock,
                }

                # Stamm-Zahl
                st = self._cell(str(stamm), meta | {"field": "stamm_zahl"})
                st.setForeground(QColor(tk.t2))
                st.setToolTip(t("disp_tip_stamm"))
                self.setItem(r, b, st)

                # Best-Bung (auto, read-only, colour-coded)
                if best == 0:
                    bb_txt, bb_col = "0",       tk.yellow
                    bb_tip = t("disp_tip_bb_zero")
                elif best < 0:
                    bb_txt, bb_col = str(best), tk.red
                    bb_tip = t("disp_tip_bb_neg", n=abs(best))
                else:
                    bb_txt, bb_col = f"+{best}", tk.green
                    bb_tip = t("disp_tip_bb_pos", n=best)
                bb = self._ro(bb_txt)
                bb.setForeground(QColor(bb_col))
                bb.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                bb.setBackground(qc(bb_col, 0x18))
                bb.setToolTip(bb_tip)
                self.setItem(r, b + 1, bb)

                # Stock
                stk_col = tk.red if stock == 0 else (tk.orange if stock < stamm else tk.green)
                stk = self._cell(str(stock), meta | {"field": "stock"})
                stk.setForeground(QColor(stk_col))
                stk.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
                stk.setToolTip(t("disp_tip_stock"))
                self.setItem(r, b + 2, stk)

                # Inventur
                inv_txt = str(inventur) if inventur is not None else "—"
                inv = self._cell(inv_txt, meta | {"field": "inventur"})
                inv.setForeground(QColor(tk.t3))
                inv.setToolTip(t("disp_tip_inv"))
                self.setItem(r, b + 3, inv)

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _ro(text: str) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setFlags(Qt.ItemFlag.ItemIsEnabled)
        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return it

    @staticmethod
    def _cell(text: str, meta: dict) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        it.setData(Qt.ItemDataRole.UserRole, meta)
        return it

    # ── Double-click ───────────────────────────────────────────────────────────

    def _on_dbl(self, row: int, col: int):
        if row == HEADER_ROW or col == 0:
            return
        it = self.item(row, col)
        if not it:
            return
        meta = it.data(Qt.ItemDataRole.UserRole)
        if not isinstance(meta, dict):
            return

        field      = meta.get("field")
        model_id   = meta["model_id"]
        model_name = meta["model_name"]
        dtype_key  = meta["dtype_key"]
        dtype_lbl  = meta["dtype_lbl"]
        stamm      = meta["stamm"]
        stock      = meta["stock"]

        if field == "stamm_zahl":
            dlg = _ThresholdDialog(model_name, dtype_lbl, stamm, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                db.set_display_stamm_zahl(model_id, dtype_key, dlg.value())
                self._refresh_cb()

        elif field == "stock":
            dlg = _StockOpDialog(model_name, dtype_lbl, stock, stamm, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                op, qty = dlg.result_data()
                try:
                    if op == "IN":
                        db.display_stock_in(model_id, dtype_key, qty)
                    elif op == "OUT":
                        db.display_stock_out(model_id, dtype_key, qty)
                    else:
                        db.display_stock_adjust(model_id, dtype_key, qty)
                    self._refresh_cb()
                except ValueError as exc:
                    QMessageBox.warning(self, t("disp_stock_err"), str(exc))

        elif field == "inventur":
            dlg = _InventurDialog(model_name, dtype_lbl, stock, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                db.set_display_inventur(model_id, dtype_key, dlg.value())
                self._refresh_cb()


# ── Displays Tab Widget ───────────────────────────────────────────────────────

class DisplaysTab(QWidget):
    """Top-level tab — toolbar with brand filter, legend, and the matrix table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(6)

        # ── Toolbar ────────────────────────────────────────────────────────────
        tb = QHBoxLayout(); tb.setContentsMargins(6, 0, 6, 0); tb.setSpacing(10)

        # Brand filter label + combobox
        self._brand_lbl = QLabel(t("disp_filter_brand"))
        self._brand_lbl.setObjectName("card_label")
        self._brand_combo = QComboBox()
        self._brand_combo.setMinimumHeight(36)
        self._brand_combo.setMinimumWidth(160)
        self._brand_combo.currentIndexChanged.connect(self.refresh)

        # Caption
        self._caption = QLabel(t("disp_caption"))
        self._caption.setObjectName("section_caption")

        # Buttons
        self._add_btn = QPushButton(t("disp_add_model"))
        self._add_btn.setObjectName("btn_primary")
        self._add_btn.clicked.connect(self._add_model)

        self._ref_btn = QPushButton(t("btn_refresh"))
        self._ref_btn.setObjectName("btn_secondary")
        self._ref_btn.clicked.connect(self.refresh)

        tb.addWidget(self._brand_lbl)
        tb.addWidget(self._brand_combo)
        tb.addWidget(self._caption, 1)
        tb.addWidget(self._add_btn)
        tb.addWidget(self._ref_btn)
        lay.addLayout(tb)

        # ── Legend ─────────────────────────────────────────────────────────────
        leg = QHBoxLayout(); leg.setContentsMargins(6, 0, 6, 4); leg.setSpacing(18)
        for lbl_key, color in [
            ("disp_legend_neg",  "#FF5A52"),
            ("disp_legend_zero", "#C8940A"),
            ("disp_legend_pos",  "#32D583"),
        ]:
            dot = QLabel(f"●  {t(lbl_key)}")
            dot.setStyleSheet(f"color:{color}; font-size:8pt;")
            leg.addWidget(dot)
        leg.addStretch()
        # Display type colour chips
        for _, lbl, color in DISPLAY_TYPES:
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            chip = QLabel(lbl)
            chip.setStyleSheet(
                f"color:{color}; font-size:8pt; font-weight:700; "
                f"background:rgba({r},{g},{b},40); border-radius:4px; padding:1px 6px;"
            )
            leg.addWidget(chip)
        lay.addLayout(leg)

        # ── Separator ──────────────────────────────────────────────────────────
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:rgba(128,128,128,60);")
        lay.addWidget(sep)

        # ── Matrix ─────────────────────────────────────────────────────────────
        self._table = _DisplayMatrix(refresh_cb=self.refresh, parent=self)
        lay.addWidget(self._table, 1)

        self._populate_brand_combo()
        self.refresh()

    # ── Brand combo ────────────────────────────────────────────────────────────

    def _populate_brand_combo(self):
        self._brand_combo.blockSignals(True)
        prev = self._brand_combo.currentText()
        self._brand_combo.clear()
        self._brand_combo.addItem(t("disp_all_brands"), userData=None)
        for brand in db.get_phone_brands():
            self._brand_combo.addItem(brand, userData=brand)
        # Restore previous selection if still present
        idx = self._brand_combo.findText(prev)
        if idx >= 0:
            self._brand_combo.setCurrentIndex(idx)
        self._brand_combo.blockSignals(False)

    def _selected_brand(self) -> str | None:
        return self._brand_combo.currentData()

    # ── Add Model ──────────────────────────────────────────────────────────────

    def _add_model(self):
        brands = db.get_phone_brands()
        dlg = _AddModelDialog(brands, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            brand = dlg.brand()
            name  = dlg.model_name()
            # Check if already exists
            existing = [m["name"] for m in db.get_phone_models(brand=brand)]
            if name in existing:
                QMessageBox.warning(self, t("dlg_required_title"),
                                    f"'{name}' " + t("disp_model_empty"))
                return
            db.add_phone_model(brand, name)
            self._populate_brand_combo()
            # Switch to the new brand filter
            idx = self._brand_combo.findText(brand)
            if idx >= 0:
                self._brand_combo.setCurrentIndex(idx)
            else:
                self.refresh()

    # ── Refresh ────────────────────────────────────────────────────────────────

    def refresh(self):
        brand     = self._selected_brand()
        models    = db.get_phone_models(brand=brand)
        stock_map = db.get_all_display_stock()
        self._table.load(models, stock_map)

    # ── Retranslate (called on language switch) ────────────────────────────────

    def retranslate(self):
        self._brand_lbl.setText(t("disp_filter_brand"))
        self._caption.setText(t("disp_caption"))
        self._add_btn.setText(t("disp_add_model"))
        self._ref_btn.setText(t("btn_refresh"))

        prev_brand = self._brand_combo.currentData()
        self._brand_combo.blockSignals(True)
        self._brand_combo.setItemText(0, t("disp_all_brands"))
        self._brand_combo.blockSignals(False)

        self._table.retranslate()
        self.refresh()
