"""app/ui/pages/price_lists_page.py — Price lists and margins management."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
    QPushButton, QTableWidget, QTableWidgetItem, QStackedWidget, QAbstractItemView,
    QLineEdit, QHeaderView, QDialog, QSizePolicy, QMessageBox, QMenu,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from app.core.theme import THEME, _rgba
from app.core.i18n import t
from app.core.config import ShopConfig
from app.models.price_list import PriceList, PriceListItem, MarginAnalysis
from app.services.price_list_service import PriceListService
from app.ui.dialogs.price_list_dialogs import (
    NewPriceListDialog, EditPriceListDialog, BulkMarkupDialog
)
from app.ui.components.responsive_table import make_table_responsive


_price_list_svc = PriceListService()


# ── KPI Card ────────────────────────────────────────────────────────────────

class _KpiCard(QFrame):
    """Single KPI metric card."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("summary_card")
        self.setMinimumHeight(70)
        self.setMaximumHeight(96)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(4)
        self._label = QLabel()
        self._label.setObjectName("card_label")
        self._value = QLabel()
        self._value.setObjectName("card_value")
        lay.addWidget(self._label)
        lay.addWidget(self._value)

    def set_data(self, label: str, value: str) -> None:
        self._label.setText(label)
        self._value.setText(value)


# ── Overview View ───────────────────────────────────────────────────────────

class _PriceListsOverviewView(QWidget):
    """View showing all price lists and margin analysis."""

    list_opened = pyqtSignal(int)  # emits list_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        self._refresh_data()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Header ──
        header = QFrame()
        hdr_lay = QVBoxLayout(header)
        hdr_lay.setContentsMargins(24, 20, 24, 16)
        hdr_lay.setSpacing(8)

        title = QLabel(t("pl_title"))
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {THEME.tokens.t1};")
        hdr_lay.addWidget(title)

        sub = QLabel(t("pl_subtitle"))
        sub.setStyleSheet(f"font-size: 12px; color: {THEME.tokens.t2};")
        hdr_lay.addWidget(sub)

        lay.addWidget(header)

        # ── Scroll content ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(24, 12, 24, 20)
        root.setSpacing(20)

        # ── KPI Row ──
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)
        self._kpi_total = _KpiCard()
        self._kpi_active = _KpiCard()
        self._kpi_items = _KpiCard()
        self._kpi_margin = _KpiCard()
        for card in (self._kpi_total, self._kpi_active, self._kpi_items, self._kpi_margin):
            kpi_row.addWidget(card)
        root.addLayout(kpi_row)

        # ── Tab bar ──
        tab_frame = QWidget()
        tab_lay = QHBoxLayout(tab_frame)
        tab_lay.setContentsMargins(0, 0, 0, 0)
        tab_lay.setSpacing(4)

        tk = THEME.tokens
        self._tab_lists = QPushButton(t("pl_tab_lists"))
        self._tab_lists.setCursor(Qt.CursorShape.PointingHandCursor)
        self._tab_lists.clicked.connect(lambda: self._switch_tab(0))

        self._tab_margins = QPushButton(t("pl_tab_margins"))
        self._tab_margins.setCursor(Qt.CursorShape.PointingHandCursor)
        self._tab_margins.clicked.connect(lambda: self._switch_tab(1))

        tab_lay.addWidget(self._tab_lists)
        tab_lay.addWidget(self._tab_margins)
        tab_lay.addStretch()
        root.addWidget(tab_frame)

        # ── Stacked views ──
        self._stacked = QStackedWidget()
        self._lists_view = self._build_price_lists_view()
        self._stacked.addWidget(self._lists_view)
        self._margins_view = self._build_margin_analysis_view()
        self._stacked.addWidget(self._margins_view)
        root.addWidget(self._stacked, 1)

        scroll.setWidget(container)
        lay.addWidget(scroll, 1)

        self._update_tab_styles(0)

    def _build_price_lists_view(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        search = QLineEdit()
        search.setPlaceholderText(t("pl_search_ph"))
        search.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._search_lists = search
        search.textChanged.connect(self._refresh_lists)
        toolbar.addWidget(search, 1)
        toolbar.addStretch()

        btn_new = QPushButton(f"  +  {t('pl_btn_new')}")
        btn_new.setObjectName("btn_primary")
        btn_new.setFixedHeight(36)
        btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new.clicked.connect(self._on_new_list)
        toolbar.addWidget(btn_new)
        lay.addLayout(toolbar)

        self._table_lists = QTableWidget()
        self._table_lists.setColumnCount(6)
        self._table_lists.setHorizontalHeaderLabels([
            t("pl_col_name"), t("pl_col_desc"), t("pl_col_items"),
            t("pl_col_status"), t("pl_col_created"), t("pl_col_actions"),
        ])
        hh = self._table_lists.horizontalHeader()
        hh.setMinimumSectionSize(40)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self._table_lists.setColumnWidth(2, 60)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self._table_lists.setColumnWidth(3, 70)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self._table_lists.setColumnWidth(4, 90)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self._table_lists.setColumnWidth(5, 170)
        self._table_lists.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table_lists.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table_lists.verticalHeader().setVisible(False)
        self._table_lists.setAlternatingRowColors(True)
        self._table_lists.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table_lists.customContextMenuRequested.connect(self._show_list_context_menu)
        self._table_lists.doubleClicked.connect(self._on_list_double_click)
        lay.addWidget(self._table_lists, 1)
        # Cols: 0=Name  1=Desc  2=Items  3=Status  4=Created  5=Actions
        make_table_responsive(self._table_lists, [
            (4, 820),   # Created — hide when viewport < 820 px
            (2, 650),   # Items   — hide when viewport < 650 px
        ])
        return w

    def _build_margin_analysis_view(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        search = QLineEdit()
        search.setPlaceholderText(t("pl_search_ph"))
        search.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._search_margins = search
        search.textChanged.connect(self._filter_margins)
        lay.addWidget(search)

        self._table_margins = QTableWidget()
        self._table_margins.setColumnCount(8)
        self._table_margins.setHorizontalHeaderLabels([
            t("pl_col_item"), t("pl_col_barcode"), t("pl_col_current"),
            t("pl_col_cost"), t("pl_col_margin_amt"), t("pl_col_margin_pct"),
            t("pl_col_stock"), t("pl_col_profit"),
        ])
        hh = self._table_margins.horizontalHeader()
        hh.setMinimumSectionSize(50)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, 8):
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self._table_margins.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table_margins.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table_margins.verticalHeader().setVisible(False)
        self._table_margins.setAlternatingRowColors(True)
        lay.addWidget(self._table_margins, 1)
        # Cols: 0=Item  1=Barcode  2=Current  3=Cost  4=Margin Amt  5=Margin%  6=Stock  7=Profit
        make_table_responsive(self._table_margins, [
            (7, 1200),  # Profit     — hide when viewport < 1200 px
            (4, 1050),  # Margin Amt — hide when viewport < 1050 px
            (6,  900),  # Stock      — hide when viewport <  900 px
            (1,  750),  # Barcode    — hide when viewport <  750 px
        ])
        return w

    # ── Tab switching ──

    def _switch_tab(self, idx: int) -> None:
        self._stacked.setCurrentIndex(idx)
        self._update_tab_styles(idx)
        if idx == 1:
            self._refresh_margins()

    def _update_tab_styles(self, active: int) -> None:
        # Use theme object names: btn_secondary (accent tint) for active,
        # btn_ghost (transparent) for inactive — avoids inline setStyleSheet
        self._tab_lists.setObjectName("btn_secondary" if active == 0 else "btn_ghost")
        self._tab_margins.setObjectName("btn_secondary" if active == 1 else "btn_ghost")
        # Force style recalculation after objectName change
        for btn in (self._tab_lists, self._tab_margins):
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    # ── Actions ──

    def _on_new_list(self) -> None:
        dlg = NewPriceListDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_data()

    def _on_list_double_click(self) -> None:
        row = self._table_lists.currentRow()
        if row < 0:
            return
        list_id = self._table_lists.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if list_id:
            self.list_opened.emit(list_id)

    def _show_list_context_menu(self, pos) -> None:
        row = self._table_lists.rowAt(pos.y())
        if row < 0:
            return
        list_id = self._table_lists.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not list_id:
            return

        menu = QMenu(self)
        act_open = menu.addAction(f"📂  {t('pl_ctx_open')}")
        act_edit = menu.addAction(f"✏  {t('pl_ctx_edit')}")
        menu.addSeparator()
        act_apply = menu.addAction(f"✓  {t('pl_ctx_apply')}")
        menu.addSeparator()
        act_delete = menu.addAction(f"🗑  {t('pl_ctx_delete')}")

        action = menu.exec(self._table_lists.viewport().mapToGlobal(pos))
        if action == act_open:
            self.list_opened.emit(list_id)
        elif action == act_edit:
            self._edit_list(list_id)
        elif action == act_apply:
            self._apply_list(list_id)
        elif action == act_delete:
            self._delete_list(list_id)

    def _edit_list(self, list_id: int) -> None:
        pl = _price_list_svc.get_list(list_id)
        if not pl:
            return
        dlg = EditPriceListDialog(self, pl.id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_data()

    def _apply_list(self, list_id: int) -> None:
        reply = QMessageBox.question(
            self, t("pl_btn_apply"), t("pl_confirm_apply"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            count = _price_list_svc.apply_price_list(list_id)
            QMessageBox.information(self, t("pl_btn_apply"), f"Updated {count} items.")
            self._refresh_data()

    def _delete_list(self, list_id: int) -> None:
        reply = QMessageBox.question(
            self, t("pl_ctx_delete"), t("pl_confirm_delete"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            _price_list_svc.delete_list(list_id)
            self._refresh_data()

    # ── Data loading ──

    def _refresh_data(self) -> None:
        cfg = ShopConfig.get()
        summary = _price_list_svc.get_summary()
        self._kpi_total.set_data(t("pl_kpi_total"), str(summary["total_lists"]))
        self._kpi_active.set_data(t("pl_kpi_active"), str(summary["active_lists"]))
        self._kpi_items.set_data(t("pl_kpi_items"), str(summary["total_items_priced"]))
        self._kpi_margin.set_data(t("pl_kpi_margin"), f"{summary['avg_margin']:.1f}%")
        self._refresh_lists()

    def _refresh_lists(self) -> None:
        cfg = ShopConfig.get()
        lists = _price_list_svc.get_all_lists()
        search = self._search_lists.text().strip().lower()
        if search:
            lists = [pl for pl in lists if search in pl.name.lower()]

        tk = THEME.tokens
        self._table_lists.setUpdatesEnabled(False)
        self._table_lists.setRowCount(len(lists))
        for row, pl in enumerate(lists):
            # Name (store id in UserRole)
            name_item = QTableWidgetItem(pl.name)
            name_item.setData(Qt.ItemDataRole.UserRole, pl.id)
            self._table_lists.setItem(row, 0, name_item)

            self._table_lists.setItem(row, 1, QTableWidgetItem(pl.description or ""))

            items_it = QTableWidgetItem(str(pl.item_count))
            items_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table_lists.setItem(row, 2, items_it)

            # Status badge
            is_active = pl.is_active
            status_text = t("pl_status_active") if is_active else t("pl_status_inactive")
            status_it = QTableWidgetItem(status_text)
            status_it.setForeground(QColor(tk.green if is_active else tk.orange))
            status_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table_lists.setItem(row, 3, status_it)

            self._table_lists.setItem(row, 4, QTableWidgetItem(pl.created_at[:10] if pl.created_at else ""))

            # Actions: Open + Edit buttons
            action_w = QWidget()
            action_lay = QHBoxLayout(action_w)
            action_lay.setContentsMargins(6, 4, 6, 10)
            action_lay.setSpacing(4)

            btn_open = QPushButton("Open")
            btn_open.setObjectName("btn_secondary_sm")
            btn_open.setFixedHeight(26)
            btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_open.clicked.connect(lambda _, lid=pl.id: self.list_opened.emit(lid))
            action_lay.addWidget(btn_open, 1)

            btn_edit = QPushButton("Edit")
            btn_edit.setObjectName("btn_secondary_sm")
            btn_edit.setFixedHeight(26)
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.clicked.connect(lambda _, lid=pl.id: self._edit_list(lid))
            action_lay.addWidget(btn_edit, 1)

            self._table_lists.setCellWidget(row, 5, action_w)
            self._table_lists.setRowHeight(row, 50)
        self._table_lists.setUpdatesEnabled(True)

    def _refresh_margins(self) -> None:
        cfg = ShopConfig.get()
        margins = _price_list_svc.get_margin_analysis()
        self._all_margins = margins
        self._display_margins(margins)

    def _display_margins(self, margins: list[MarginAnalysis]) -> None:
        cfg = ShopConfig.get()
        tk = THEME.tokens
        self._table_margins.setUpdatesEnabled(False)
        self._table_margins.setRowCount(len(margins))
        for row, ma in enumerate(margins):
            self._table_margins.setItem(row, 0, QTableWidgetItem(ma.item_name))
            self._table_margins.setItem(row, 1, QTableWidgetItem(ma.barcode or ""))
            self._table_margins.setItem(row, 2, QTableWidgetItem(cfg.format_currency(ma.sell_price)))
            self._table_margins.setItem(row, 3, QTableWidgetItem(cfg.format_currency(ma.cost_price)))
            self._table_margins.setItem(row, 4, QTableWidgetItem(cfg.format_currency(ma.margin_amount)))

            margin_cell = QTableWidgetItem(f"{ma.margin_pct:.1f}%")
            if ma.margin_pct < 10:
                margin_cell.setForeground(QColor(tk.red))
            elif ma.margin_pct < 30:
                margin_cell.setForeground(QColor(tk.orange))
            else:
                margin_cell.setForeground(QColor(tk.green))
            margin_cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table_margins.setItem(row, 5, margin_cell)

            stock_it = QTableWidgetItem(str(ma.stock))
            stock_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table_margins.setItem(row, 6, stock_it)
            self._table_margins.setItem(row, 7, QTableWidgetItem(cfg.format_currency(ma.potential_profit)))
            self._table_margins.setRowHeight(row, 38)
        self._table_margins.setUpdatesEnabled(True)

    def _filter_margins(self, text: str) -> None:
        if not hasattr(self, '_all_margins'):
            return
        search = text.strip().lower()
        if not search:
            self._display_margins(self._all_margins)
        else:
            filtered = [m for m in self._all_margins
                        if search in m.item_name.lower() or search in (m.barcode or "").lower()]
            self._display_margins(filtered)


# ── Detail View ─────────────────────────────────────────────────────────────

class _PriceListDetailView(QWidget):
    """View showing details of a single price list."""

    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._list_id = 0
        self._list: PriceList | None = None
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Header with back button ──
        header = QFrame()
        hdr_lay = QVBoxLayout(header)
        hdr_lay.setContentsMargins(24, 16, 24, 16)
        hdr_lay.setSpacing(8)

        back_row = QHBoxLayout()
        btn_back = QPushButton(f"← {t('pl_detail_back')}")
        btn_back.setObjectName("btn_secondary")
        btn_back.setFixedHeight(30)
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(self.back_requested.emit)
        back_row.addWidget(btn_back)
        back_row.addStretch()
        hdr_lay.addLayout(back_row)

        self._detail_title = QLabel()
        self._detail_title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {THEME.tokens.t1};")
        hdr_lay.addWidget(self._detail_title)

        lay.addWidget(header)

        # ── Toolbar ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(24, 12, 24, 20)
        root.setSpacing(12)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        search = QLineEdit()
        search.setPlaceholderText(t("pl_search_ph"))
        search.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        search.textChanged.connect(self._filter_items)
        self._detail_search = search
        toolbar.addWidget(search, 1)
        toolbar.addStretch()

        btn_add_all = QPushButton(t("pl_btn_add_all"))
        btn_add_all.setObjectName("btn_secondary_sm")
        btn_add_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_all.clicked.connect(self._on_add_all_items)
        toolbar.addWidget(btn_add_all)

        btn_markup = QPushButton(t("pl_btn_markup"))
        btn_markup.setObjectName("btn_secondary_sm")
        btn_markup.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_markup.clicked.connect(self._on_bulk_markup)
        toolbar.addWidget(btn_markup)

        btn_apply = QPushButton(t("pl_btn_apply"))
        btn_apply.setObjectName("btn_primary_sm")
        btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply.clicked.connect(self._on_apply_list)
        toolbar.addWidget(btn_apply)

        root.addLayout(toolbar)

        # ── Items table ──
        self._table_items = QTableWidget()
        self._table_items.setColumnCount(7)
        self._table_items.setHorizontalHeaderLabels([
            t("pl_col_item"), t("pl_col_barcode"), t("pl_col_current"),
            t("pl_col_list_price"), t("pl_col_cost"), t("pl_col_margin_pct"),
            t("pl_col_actions"),
        ])
        hh = self._table_items.horizontalHeader()
        hh.setMinimumSectionSize(40)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, 6):
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self._table_items.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table_items.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table_items.verticalHeader().setVisible(False)
        self._table_items.setAlternatingRowColors(True)
        root.addWidget(self._table_items, 1)
        # Cols: 0=Item  1=Barcode  2=Current  3=List Price  4=Cost  5=Margin%  6=Actions
        make_table_responsive(self._table_items, [
            (1, 900),   # Barcode    — hide when viewport < 900 px
            (4, 800),   # Cost       — hide when viewport < 800 px
            (2, 680),   # Current    — hide when viewport < 680 px
        ])

        scroll.setWidget(container)
        lay.addWidget(scroll, 1)

    def load_list(self, list_id: int) -> None:
        self._list_id = list_id
        self._list = _price_list_svc.get_list(list_id)
        if self._list:
            self._detail_title.setText(self._list.name)
            self._refresh_items()

    def _refresh_items(self) -> None:
        if not self._list_id:
            return
        cfg = ShopConfig.get()
        tk = THEME.tokens
        items = _price_list_svc.get_list_items(self._list_id)
        self._all_items = items
        self._display_items(items)

    def _display_items(self, items: list[PriceListItem]) -> None:
        cfg = ShopConfig.get()
        tk = THEME.tokens
        self._table_items.setUpdatesEnabled(False)
        self._table_items.setRowCount(len(items))
        for row, item in enumerate(items):
            self._table_items.setItem(row, 0, QTableWidgetItem(item.item_name))
            self._table_items.setItem(row, 1, QTableWidgetItem(item.barcode or ""))
            self._table_items.setItem(row, 2, QTableWidgetItem(cfg.format_currency(item.current_price)))
            self._table_items.setItem(row, 3, QTableWidgetItem(cfg.format_currency(item.list_price)))
            self._table_items.setItem(row, 4, QTableWidgetItem(cfg.format_currency(item.cost_price)))

            margin_it = QTableWidgetItem(f"{item.margin_pct:.1f}%")
            margin_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table_items.setItem(row, 5, margin_it)

            btn = QPushButton("✕")
            btn.setObjectName("mgmt_del")
            btn.setFixedSize(30, 26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(t("pl_ctx_delete"))
            btn.clicked.connect(lambda _, iid=item.id: self._on_remove_item(iid))
            self._table_items.setCellWidget(row, 6, btn)
            self._table_items.setRowHeight(row, 38)
        self._table_items.setUpdatesEnabled(True)

    def _filter_items(self, text: str) -> None:
        if not hasattr(self, '_all_items'):
            return
        search = text.strip().lower()
        if not search:
            self._display_items(self._all_items)
        else:
            filtered = [i for i in self._all_items
                        if search in i.item_name.lower() or search in (i.barcode or "").lower()]
            self._display_items(filtered)

    def _on_add_all_items(self) -> None:
        if not self._list_id:
            return
        count = _price_list_svc.bulk_populate(self._list_id)
        self._refresh_items()

    def _on_bulk_markup(self) -> None:
        if not self._list_id:
            return
        dlg = BulkMarkupDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            pct = dlg.get_percentage()
            _price_list_svc.bulk_markup(self._list_id, pct)
            self._refresh_items()

    def _on_apply_list(self) -> None:
        if not self._list_id:
            return
        reply = QMessageBox.question(
            self, t("pl_btn_apply"), t("pl_confirm_apply"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            count = _price_list_svc.apply_price_list(self._list_id)
            QMessageBox.information(self, t("pl_btn_apply"), f"Updated {count} items.")

    def _on_remove_item(self, item_id: int) -> None:
        _price_list_svc.remove_item(item_id)
        self._refresh_items()


# ── Main Page ───────────────────────────────────────────────────────────────

class PriceListsPage(QWidget):
    """Main page for managing price lists and margins."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._stacked = QStackedWidget()

        self._overview = _PriceListsOverviewView()
        self._stacked.addWidget(self._overview)

        self._detail = _PriceListDetailView()
        self._stacked.addWidget(self._detail)

        lay.addWidget(self._stacked)

        # Wire navigation signals
        self._overview.list_opened.connect(self._open_list)
        self._detail.back_requested.connect(self._back_to_overview)

    def _open_list(self, list_id: int) -> None:
        self._detail.load_list(list_id)
        self._stacked.setCurrentIndex(1)

    def _back_to_overview(self) -> None:
        self._overview._refresh_data()
        self._stacked.setCurrentIndex(0)

    def refresh(self) -> None:
        if self._stacked.currentIndex() == 0:
            self._overview._refresh_data()

    def retranslate(self) -> None:
        self.refresh()
