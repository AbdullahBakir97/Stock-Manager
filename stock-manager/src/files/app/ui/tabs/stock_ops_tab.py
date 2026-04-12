"""
app/ui/tabs/stock_ops_tab.py — Professional stock operations panel (Phase 5A redesign).

Modern layout with KPI summary, filterable item table, inline quick operations,
and a detail/history side panel.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QSizePolicy, QMessageBox, QLineEdit,
    QComboBox, QStackedWidget,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor

from app.core.config import ShopConfig
from app.core.theme import THEME, _rgba
from app.core.i18n import t, color_t
from app.core.icon_utils import get_colored_icon, get_button_icon
from app.core import colors as clr
from app.models.item import InventoryItem
from app.repositories.item_repo import ItemRepository
from app.services.stock_service import StockService
from app.ui.components.barcode_line_edit import BarcodeLineEdit
from app.ui.components.mini_txn_list import MiniTxnList
from app.ui.helpers import _sc, _sl

_item_repo = ItemRepository()
_stock_svc = StockService()


# ── KPI Card ──────────────────────────────────────────────────────────────────

class _KpiCard(QFrame):
    """Summary KPI metric card for the Stock Ops header."""

    def __init__(self, accent: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("summary_card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(88)
        self.setMaximumHeight(96)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(4)

        self._label = QLabel()
        self._label.setObjectName("card_label")
        self._value = QLabel("0")
        self._value.setObjectName("card_value")
        self._sub = QLabel()
        self._sub.setObjectName("detail_threshold")
        lay.addWidget(self._label)
        lay.addWidget(self._value)
        lay.addWidget(self._sub)

    def set_data(self, label: str, value: str, sub: str = "") -> None:
        self._label.setText(label)
        self._value.setText(value)
        self._sub.setText(sub)


# ── Filter Chip ───────────────────────────────────────────────────────────────

class _FilterChip(QPushButton):
    """Clickable filter pill — toggles between active/inactive."""

    def __init__(self, text: str, key: str, parent=None):
        super().__init__(text, parent)
        self.key = key
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("filter_chip")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(32)


# ── Empty State Widget ────────────────────────────────────────────────────────

class _EmptyState(QWidget):
    """Professional empty state placeholder."""

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(8)

        icon_lbl = QLabel("📦")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 48px;")
        lay.addWidget(icon_lbl)

        self._title = QLabel(t("stockops_empty_title"))
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setStyleSheet("font-size: 16px; font-weight: 600;")
        lay.addWidget(self._title)

        self._sub = QLabel(t("stockops_empty_sub"))
        self._sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub.setObjectName("detail_threshold")
        lay.addWidget(self._sub)


# ── Detail Panel ──────────────────────────────────────────────────────────────

class _DetailPanel(QWidget):
    """Right-side detail panel: item info + quick operation + history."""

    op_performed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._item: InventoryItem | None = None
        self._build()

    def _build(self):
        from app.ui.dialogs.product_dialogs import QuantitySpin

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        # ── Prompt (shown when no item selected) ──
        self._prompt_w = QWidget()
        prompt_lay = QVBoxLayout(self._prompt_w)
        prompt_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prompt_lay.setSpacing(8)
        prompt_icon = QLabel("🔍")
        prompt_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prompt_icon.setStyleSheet("font-size: 40px;")
        prompt_lay.addWidget(prompt_icon)
        self._prompt_lbl = QLabel(t("stockops_select_prompt"))
        self._prompt_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._prompt_lbl.setWordWrap(True)
        self._prompt_lbl.setObjectName("detail_threshold")
        self._prompt_lbl.setStyleSheet("font-size: 13px;")
        prompt_lay.addWidget(self._prompt_lbl)
        lay.addWidget(self._prompt_w)

        # ── Detail content (hidden until item selected) ──
        self._detail_w = QWidget()
        self._detail_w.setVisible(False)
        dl = QVBoxLayout(self._detail_w)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(12)

        # ── Selected item card ──
        self._sel_card = QFrame()
        self._sel_card.setObjectName("detail_card")
        scl = QVBoxLayout(self._sel_card)
        scl.setContentsMargins(16, 14, 16, 14)
        scl.setSpacing(6)

        # Detail header
        detail_hdr = QLabel(t("stockops_detail_title"))
        detail_hdr.setObjectName("detail_section_hdr")
        scl.addWidget(detail_hdr)
        self._detail_hdr_lbl = detail_hdr

        self._sel_name = QLabel()
        self._sel_name.setObjectName("detail_product_name")
        self._sel_name.setWordWrap(True)
        scl.addWidget(self._sel_name)

        # Color row
        cr = QHBoxLayout()
        cr.setSpacing(8)
        self._sel_dot = QLabel()
        self._sel_dot.setFixedSize(16, 16)
        self._sel_color_name = QLabel("")
        self._sel_color_name.setObjectName("detail_color_name")
        cr.addWidget(self._sel_dot)
        cr.addWidget(self._sel_color_name)
        cr.addStretch()
        scl.addLayout(cr)

        self._sel_barcode = QLabel("")
        self._sel_barcode.setObjectName("detail_barcode")
        scl.addWidget(self._sel_barcode)
        self._sel_price = QLabel("")
        self._sel_price.setObjectName("detail_barcode")
        scl.addWidget(self._sel_price)

        # Big stock number
        self._sel_stock = QLabel("")
        self._sel_stock.setObjectName("big_stock")
        self._sel_stock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scl.addWidget(self._sel_stock)

        # Status badge
        self._sel_badge = QLabel("")
        self._sel_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scl.addWidget(self._sel_badge)

        # Threshold info
        self._sel_info = QLabel("")
        self._sel_info.setObjectName("detail_threshold")
        self._sel_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scl.addWidget(self._sel_info)

        dl.addWidget(self._sel_card)

        # ── Quick Operation card ──
        ops_card = QFrame()
        ops_card.setObjectName("stockops_card")
        ocl = QVBoxLayout(ops_card)
        ocl.setContentsMargins(16, 14, 16, 14)
        ocl.setSpacing(10)

        self._ops_hdr = QLabel(t("stockops_quick_op"))
        self._ops_hdr.setObjectName("detail_section_hdr")
        ocl.addWidget(self._ops_hdr)

        # Quantity row
        qty_row = QHBoxLayout()
        qty_row.setSpacing(8)
        self._qty_lbl = QLabel(t("stockops_qty_label"))
        self._qty_spin = QuantitySpin(1, 99999, 1)
        qty_row.addWidget(self._qty_lbl)
        qty_row.addWidget(self._qty_spin, 1)
        ocl.addLayout(qty_row)

        # Note
        self._note_lbl = QLabel(t("stockops_note_label"))
        ocl.addWidget(self._note_lbl)
        self._note_edit = QLineEdit()
        self._note_edit.setPlaceholderText(t("op_note_ph"))
        ocl.addWidget(self._note_edit)

        # Operation buttons
        self._btn_in = QPushButton(t("btn_stock_in"))
        self._btn_in.setObjectName("op_in")
        self._btn_in.clicked.connect(lambda: self._do_op("IN"))

        self._btn_out = QPushButton(t("btn_stock_out"))
        self._btn_out.setObjectName("op_out")
        self._btn_out.clicked.connect(lambda: self._do_op("OUT"))

        self._btn_adj = QPushButton(t("btn_adjust"))
        self._btn_adj.setObjectName("op_adj")
        self._btn_adj.clicked.connect(lambda: self._do_op("ADJUST"))

        for b in (self._btn_in, self._btn_out, self._btn_adj):
            b.setEnabled(False)
            ocl.addWidget(b)

        dl.addWidget(ops_card)

        # ── Recent activity ──
        self._txn_hdr = QLabel(t("stockops_history"))
        self._txn_hdr.setObjectName("detail_section_hdr")
        dl.addWidget(self._txn_hdr)

        txn_scroll = QScrollArea()
        txn_scroll.setWidgetResizable(True)
        txn_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        txn_scroll.setObjectName("txn_scroll_area")
        self._mini_txn = MiniTxnList()
        txn_scroll.setWidget(self._mini_txn)
        dl.addWidget(txn_scroll, 1)

        lay.addWidget(self._detail_w, 1)
        scroll.setWidget(inner)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def set_item(self, item: InventoryItem | None):
        """Update the panel with the selected item."""
        self._item = item
        if not item:
            self._prompt_w.setVisible(True)
            self._detail_w.setVisible(False)
            for b in (self._btn_in, self._btn_out, self._btn_adj):
                b.setEnabled(False)
            return

        self._prompt_w.setVisible(False)
        self._detail_w.setVisible(True)

        tk = THEME.tokens
        sc = _sc(item.stock, item.min_stock)
        sl = _sl(item.stock, item.min_stock)

        self._sel_name.setText(f"<b>{item.display_name}</b>")

        # Color dot
        if item.is_product and item.color:
            hc = clr.hex_for(item.color)
            brd = "rgba(102,102,102,153)" if clr.is_light(hc) else "transparent"
            self._sel_dot.setStyleSheet(f"background:{hc}; border-radius:8px; border:1px solid {brd};")
            self._sel_color_name.setText(color_t(item.color))
        elif item.part_type_color:
            hc = item.part_type_color
            self._sel_dot.setStyleSheet(f"background:{hc}; border-radius:8px;")
            self._sel_color_name.setText(item.part_type_name or "")
        else:
            self._sel_dot.setStyleSheet("")
            self._sel_color_name.setText("")

        self._sel_barcode.setText(
            t("detail_barcode", val=item.barcode or t("dlg_color_none"))
        )
        cfg = ShopConfig.get()
        price_display = cfg.format_currency(item.sell_price) if item.sell_price else "—"
        self._sel_price.setText(t("detail_sell_price", val=price_display))

        self._sel_stock.setText(str(item.stock))
        self._sel_stock.setStyleSheet(f"color:{sc.name()};")

        # Badge
        badge_map = {
            "OK":       (tk.green,  _rgba(tk.green,  "28")),
            "LOW":      (tk.yellow, _rgba(tk.yellow, "30")),
            "CRITICAL": (tk.orange, _rgba(tk.orange, "28")),
            "OUT":      (tk.red,    _rgba(tk.red,    "28")),
        }
        badge_labels = {
            "OK": t("badge_ok"), "LOW": t("badge_low"),
            "CRITICAL": t("badge_critical"), "OUT": t("badge_out"),
        }
        fg, bg = badge_map.get(sl, (tk.t3, tk.border))
        self._sel_badge.setText(badge_labels.get(sl, sl))
        self._sel_badge.setStyleSheet(
            f"color:{fg}; background:{bg}; border:1px solid {_rgba(fg, '40')};"
            "border-radius:10px; font-weight:800; font-size:9pt; padding:5px 14px;"
        )

        diff = item.stock - item.min_stock
        diff_str = f"Δ{diff:+d}" if item.min_stock > 0 else ""
        self._sel_info.setText(
            f"{t('detail_alert_at', n=item.min_stock)}   {diff_str}"
        )

        for b in (self._btn_in, self._btn_out, self._btn_adj):
            b.setEnabled(True)
        self._mini_txn.load(item.id)

    def _do_op(self, op: str):
        if not self._item:
            return
        item = _item_repo.get_by_id(self._item.id)
        if not item:
            QMessageBox.warning(self, t("msg_not_found_title"), t("msg_not_found_body"))
            return
        qty = self._qty_spin.value()
        note = self._note_edit.text().strip() or ""
        try:
            if op == "IN":
                res = _stock_svc.stock_in(item.id, qty, note)
            elif op == "OUT":
                res = _stock_svc.stock_out(item.id, qty, note)
            else:
                res = _stock_svc.stock_adjust(item.id, qty, note)

            updated = _item_repo.get_by_id(item.id)
            if updated:
                self.set_item(updated)
            self._note_edit.clear()
            self._qty_spin.setValue(1)
            self.op_performed.emit()
        except ValueError as e:
            QMessageBox.warning(self, t("msg_op_failed"), str(e))
        except Exception as e:
            QMessageBox.critical(self, t("msg_error"), str(e))

    def retranslate(self):
        self._prompt_lbl.setText(t("stockops_select_prompt"))
        self._detail_hdr_lbl.setText(t("stockops_detail_title"))
        self._ops_hdr.setText(t("stockops_quick_op"))
        self._qty_lbl.setText(t("stockops_qty_label"))
        self._note_lbl.setText(t("stockops_note_label"))
        self._note_edit.setPlaceholderText(t("op_note_ph"))
        self._btn_in.setText(t("btn_stock_in"))
        self._btn_out.setText(t("btn_stock_out"))
        self._btn_adj.setText(t("btn_adjust"))
        self._txn_hdr.setText(t("stockops_history"))


# ── Main Stock Ops Tab ────────────────────────────────────────────────────────

class StockOpsTab(QWidget):
    """Professional stock operations panel with KPI summary, filters, and operations."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._items_data: list[InventoryItem] = []
        self._active_filter = "all"
        self._loaded = False
        self._build()
        # Defer initial data load so UI builds instantly
        QTimer.singleShot(0, self._initial_load)

    def _initial_load(self):
        """Deferred first load — runs after the event loop starts."""
        if not self._loaded:
            self._loaded = True
            self._load_items()
            self._update_kpis()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)

        # ── Page header ──
        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self._title_lbl = QLabel(t("stockops_title"))
        self._title_lbl.setObjectName("admin_panel_title")
        self._title_lbl.setStyleSheet("font-size: 20px; font-weight: 700;")
        title_col.addWidget(self._title_lbl)
        self._subtitle_lbl = QLabel(t("stockops_subtitle"))
        self._subtitle_lbl.setObjectName("admin_panel_subtitle")
        self._subtitle_lbl.setStyleSheet("font-size: 12px;")
        title_col.addWidget(self._subtitle_lbl)
        hdr_row.addLayout(title_col)
        hdr_row.addStretch()

        # Refresh button
        self._refresh_btn = QPushButton()
        self._refresh_btn.setObjectName("icon_btn")
        self._refresh_btn.setIcon(get_button_icon("refresh"))
        self._refresh_btn.setIconSize(QSize(18, 18))
        self._refresh_btn.setToolTip(t("action_refresh"))
        self._refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_btn.clicked.connect(self.refresh)
        hdr_row.addWidget(self._refresh_btn)
        root.addLayout(hdr_row)

        # ── KPI row ──
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)
        self._kpi_total = _KpiCard()
        self._kpi_units = _KpiCard()
        self._kpi_low = _KpiCard()
        self._kpi_out = _KpiCard()
        self._kpi_value = _KpiCard()
        for card in (self._kpi_total, self._kpi_units, self._kpi_low,
                     self._kpi_out, self._kpi_value):
            kpi_row.addWidget(card)
        root.addLayout(kpi_row)

        # ── Search + filter bar ──
        bar_row = QHBoxLayout()
        bar_row.setSpacing(10)

        self._search = BarcodeLineEdit()
        self._search.setObjectName("search_bar")
        self._search.setPlaceholderText(t("stockops_search"))
        self._search.setMinimumHeight(38)
        self._search.setMaximumHeight(38)
        self._search.textChanged.connect(self._on_search)
        self._search.barcode_scanned.connect(self._on_barcode)
        bar_row.addWidget(self._search, 1)

        # Filter chips
        self._chips: list[_FilterChip] = []
        for label_key, key in [
            ("stockops_filter_all", "all"),
            ("stockops_filter_low", "low"),
            ("stockops_filter_out", "out"),
            ("stockops_filter_products", "products"),
        ]:
            chip = _FilterChip(t(label_key), key)
            chip.clicked.connect(lambda checked, k=key: self._set_filter(k))
            bar_row.addWidget(chip)
            self._chips.append(chip)
        self._chips[0].setChecked(True)

        root.addLayout(bar_row)

        # ── Main content: splitter (table | detail panel) ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # Left — item table
        left_w = QWidget()
        left_lay = QVBoxLayout(left_w)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(0)

        # Stacked widget: table or empty state
        self._stack = QStackedWidget()

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            t("stockops_col_product"), t("stockops_col_barcode"),
            t("stockops_col_stock"), t("stockops_col_min"),
            t("stockops_col_status"), t("stockops_col_actions"),
        ])
        hh = self._table.horizontalHeader()
        hh.setMinimumSectionSize(40)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(5, 130)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.itemSelectionChanged.connect(self._on_select)

        self._empty = _EmptyState()
        self._stack.addWidget(self._table)
        self._stack.addWidget(self._empty)
        left_lay.addWidget(self._stack)

        # Right — detail panel
        self._detail = _DetailPanel()
        self._detail.op_performed.connect(self._on_op_performed)

        splitter.addWidget(left_w)
        splitter.addWidget(self._detail)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([600, 350])
        root.addWidget(splitter, 1)

    # ── KPI ───────────────────────────────────────────────────────────────────

    def _update_kpis(self):
        summary = _item_repo.get_summary()
        cfg = ShopConfig.get()
        total = summary.get("total_products", 0) or 0
        units = summary.get("total_units", 0) or 0
        low = summary.get("low_stock_count", 0) or 0
        out = summary.get("out_of_stock_count", 0) or 0
        value = summary.get("inventory_value", 0) or 0

        self._kpi_total.set_data(t("stockops_kpi_total"), str(total))
        self._kpi_units.set_data(t("stockops_kpi_units"), f"{units:,}")
        self._kpi_low.set_data(t("stockops_kpi_low"), str(low))
        self._kpi_out.set_data(t("stockops_kpi_out"), str(out))
        self._kpi_value.set_data(
            t("stockops_kpi_value"),
            cfg.format_currency(value) if value else "—"
        )

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load_items(self, search: str = ""):
        f = self._active_filter
        s = search if len(search) >= 2 else ""
        if f == "products":
            items = _item_repo.get_all_products(search=s)
        elif f == "low":
            items = _item_repo.get_all_items(search=s, filter_low_stock=True)
            # filter_low_stock includes stock==0; for "low" we want only 0 < stock <= min
            items = [i for i in items if i.stock > 0]
        elif f == "out":
            items = _item_repo.get_all_items(search=s)
            items = [i for i in items if i.stock == 0]
        else:
            items = _item_repo.get_all_items(search=s)

        self._items_data = items
        # Cap display at 200 rows for performance; search narrows further
        display = items[:200]
        self._render_table(display)

    def _render_table(self, items: list[InventoryItem]):
        if not items:
            self._stack.setCurrentIndex(1)
            return
        self._stack.setCurrentIndex(0)

        tk = THEME.tokens

        # Pre-compute shared resources once (not per-row)
        mono_sm = QFont("JetBrains Mono", 9)
        mono_lg = QFont("JetBrains Mono", 10, QFont.Weight.Bold)
        t3_color = QColor(tk.t3)
        sl_labels = {
            "OK": t("status_ok_lbl"), "LOW": t("status_low_lbl"),
            "CRITICAL": t("status_critical_lbl"), "OUT": t("status_out_lbl"),
        }
        badge_styles = {
            "OK":       f"color:{tk.green}; background:{_rgba(tk.green, '20')}; border-radius:8px; font-weight:700; font-size:9px; padding:3px 8px;",
            "LOW":      f"color:{tk.yellow}; background:{_rgba(tk.yellow, '20')}; border-radius:8px; font-weight:700; font-size:9px; padding:3px 8px;",
            "CRITICAL": f"color:{tk.orange}; background:{_rgba(tk.orange, '20')}; border-radius:8px; font-weight:700; font-size:9px; padding:3px 8px;",
            "OUT":      f"color:{tk.red}; background:{_rgba(tk.red, '20')}; border-radius:8px; font-weight:700; font-size:9px; padding:3px 8px;",
        }
        btn_in_ss = (
            f"background:{_rgba(tk.green, '20')}; color:{tk.green};"
            f"border:1px solid {_rgba(tk.green, '40')}; border-radius:6px;"
            "font-weight:700; font-size:11px; padding:0; margin:0;"
        )
        btn_out_ss = (
            f"background:{_rgba(tk.red, '20')}; color:{tk.red};"
            f"border:1px solid {_rgba(tk.red, '40')}; border-radius:6px;"
            "font-weight:700; font-size:11px; padding:0; margin:0;"
        )
        edit_icon = get_colored_icon("edit", tk.blue)
        icon_sz = QSize(14, 14)
        tip_in = t("btn_stock_in")
        tip_out = t("btn_stock_out")
        tip_detail = t("stockops_detail_title")

        # Freeze UI updates during bulk insert
        self._table.setUpdatesEnabled(False)
        self._table.blockSignals(True)
        try:
            self._table.setRowCount(len(items))
            for i, item in enumerate(items):
                # Product name
                name_it = QTableWidgetItem(item.display_name)
                name_it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self._table.setItem(i, 0, name_it)

                # Barcode
                bc_it = QTableWidgetItem(item.barcode or "—")
                bc_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                bc_it.setFont(mono_sm)
                self._table.setItem(i, 1, bc_it)

                # Stock
                sc = _sc(item.stock, item.min_stock)
                stk_it = QTableWidgetItem(str(item.stock))
                stk_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                stk_it.setForeground(sc)
                stk_it.setFont(mono_lg)
                self._table.setItem(i, 2, stk_it)

                # Min stock
                min_it = QTableWidgetItem(str(item.min_stock) if item.min_stock > 0 else "—")
                min_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                min_it.setForeground(t3_color)
                self._table.setItem(i, 3, min_it)

                # Status badge
                sl = _sl(item.stock, item.min_stock)
                status_lbl = QLabel(sl_labels.get(sl, sl))
                status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                status_lbl.setStyleSheet(badge_styles.get(sl, ""))
                self._table.setCellWidget(i, 4, status_lbl)

                # Quick action buttons
                action_w = QWidget()
                action_w.setFixedSize(128, 40)
                action_lay = QHBoxLayout(action_w)
                action_lay.setContentsMargins(4, 2, 4, 2)
                action_lay.setSpacing(4)

                btn_in = QPushButton("+1")
                btn_in.setToolTip(tip_in)
                btn_in.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_in.setFixedSize(36, 36)
                btn_in.setStyleSheet(btn_in_ss)
                btn_in.clicked.connect(lambda _, iid=item.id: self._quick_in(iid))
                action_lay.addWidget(btn_in)

                btn_out = QPushButton("-1")
                btn_out.setToolTip(tip_out)
                btn_out.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_out.setFixedSize(36, 36)
                btn_out.setStyleSheet(btn_out_ss)
                btn_out.clicked.connect(lambda _, iid=item.id: self._quick_out(iid))
                action_lay.addWidget(btn_out)

                btn_detail = QPushButton()
                btn_detail.setObjectName("admin_edit_btn")
                btn_detail.setIcon(edit_icon)
                btn_detail.setIconSize(icon_sz)
                btn_detail.setToolTip(tip_detail)
                btn_detail.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_detail.setFixedSize(36, 36)
                btn_detail.clicked.connect(lambda _, idx=i: self._select_row(idx))
                action_lay.addWidget(btn_detail)

                self._table.setCellWidget(i, 5, action_w)
                self._table.setRowHeight(i, 44)
        finally:
            self._table.blockSignals(False)
            self._table.setUpdatesEnabled(True)

    # ── Quick operations from table ───────────────────────────────────────────

    def _quick_in(self, item_id: int):
        try:
            _stock_svc.stock_in(item_id, 1, t("stockops_quick_in"))
            self._after_op(item_id)
        except ValueError as e:
            QMessageBox.warning(self, t("msg_op_failed"), str(e))

    def _quick_out(self, item_id: int):
        try:
            _stock_svc.stock_out(item_id, 1, t("stockops_quick_out"))
            self._after_op(item_id)
        except ValueError as e:
            QMessageBox.warning(self, t("msg_op_failed"), str(e))

    def _after_op(self, item_id: int):
        """Refresh data after a quick operation."""
        self._load_items(self._search.text().strip())
        self._update_kpis()
        # Re-select the item if it was selected
        updated = _item_repo.get_by_id(item_id)
        if updated and self._detail._item and self._detail._item.id == item_id:
            self._detail.set_item(updated)

    def _on_op_performed(self):
        """Called when the detail panel performs an operation."""
        self._load_items(self._search.text().strip())
        self._update_kpis()

    # ── Selection ─────────────────────────────────────────────────────────────

    def _on_select(self):
        row = self._table.currentRow()
        if 0 <= row < len(self._items_data):
            self._detail.set_item(self._items_data[row])

    def _select_row(self, idx: int):
        if 0 <= idx < len(self._items_data):
            self._table.selectRow(idx)
            self._detail.set_item(self._items_data[idx])

    def _on_barcode(self, bc: str):
        item = _item_repo.get_by_barcode(bc)
        if item:
            # Find in current list and select
            for i, it in enumerate(self._items_data):
                if it.id == item.id:
                    self._table.selectRow(i)
                    break
            self._detail.set_item(item)
        else:
            self._search.setText(bc)

    # ── Filtering ─────────────────────────────────────────────────────────────

    def _on_search(self, text: str):
        self._load_items(text.strip())

    def _set_filter(self, key: str):
        self._active_filter = key
        for chip in self._chips:
            chip.setChecked(chip.key == key)
        self._load_items(self._search.text().strip())

    # ── Public API ────────────────────────────────────────────────────────────

    def retranslate(self):
        self._title_lbl.setText(t("stockops_title"))
        self._subtitle_lbl.setText(t("stockops_subtitle"))
        self._search.setPlaceholderText(t("stockops_search"))
        self._table.setHorizontalHeaderLabels([
            t("stockops_col_product"), t("stockops_col_barcode"),
            t("stockops_col_stock"), t("stockops_col_min"),
            t("stockops_col_status"), t("stockops_col_actions"),
        ])
        # Update filter chips
        chip_labels = [
            "stockops_filter_all", "stockops_filter_low",
            "stockops_filter_out", "stockops_filter_products",
        ]
        for chip, key in zip(self._chips, chip_labels):
            chip.setText(t(key))
        self._detail.retranslate()
        self._update_kpis()
        self._load_items(self._search.text().strip())

    def refresh(self):
        self._load_items(self._search.text().strip())
        self._update_kpis()
        if self._detail._item:
            updated = _item_repo.get_by_id(self._detail._item.id)
            if updated:
                self._detail.set_item(updated)
