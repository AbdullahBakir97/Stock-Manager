"""
app/ui/pages/sales_page.py — Professional sales history page and POS dialog.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QPushButton, QLabel, QSpinBox, QDoubleSpinBox, QComboBox,
    QDialog, QDialogButtonBox, QMessageBox, QFrame,
    QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from app.core.icon_utils import get_colored_icon

from app.core.theme import THEME, _rgba
from app.repositories.sale_repo import SaleRepository
from app.repositories.item_repo import ItemRepository
from app.services.sale_service import SaleService
from app.services.customer_service import CustomerService
from app.services.receipt_service import ReceiptService
from app.models.sale import Sale
from app.models.item import InventoryItem
from app.core.i18n import t
from app.core.config import ShopConfig
from app.ui.components.responsive_table import make_table_responsive
from app.ui.workers.worker_pool import POOL

_sale_repo = SaleRepository()
_item_repo = ItemRepository()
_sale_svc = SaleService()
_cust_svc = CustomerService()
_receipt_svc = ReceiptService()


# ── KPI Card ────────────────────────────────────────────────────────────────

class _SalesKpiCard(QFrame):
    """Single KPI metric card for the sales page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sales_kpi")
        self.setMinimumHeight(70)
        self.setMaximumHeight(96)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(4)
        self._label = QLabel()
        self._label.setObjectName("sales_kpi_label")
        self._value = QLabel()
        self._value.setObjectName("sales_kpi_value")
        self._sub = QLabel()
        self._sub.setObjectName("sales_kpi_sub")
        lay.addWidget(self._label)
        lay.addWidget(self._value)
        lay.addWidget(self._sub)

    def set_data(self, label: str, value: str, sub: str = "") -> None:
        self._label.setText(label)
        self._value.setText(value)
        self._sub.setText(sub)


# ── POS Dialog ───────────────────────────────────────────────────────────────

class POSDialog(QDialog):
    """Professional point-of-sale dialog with product picker and cart."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pos_dialog")
        self.setWindowTitle(t("pos_title"))
        self.setMinimumSize(1000, 620)
        THEME.apply(self)
        self._cart: list[dict] = []
        self._products: list[InventoryItem] = []
        self._build()
        self._load_products()
        self.result_sale_id: int | None = None

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ── Main split: products | cart ──
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── LEFT: Product picker ─────────────────────────────────────────
        left_frame = QFrame()
        left_frame.setObjectName("pos_panel")
        left_lay = QVBoxLayout(left_frame)
        left_lay.setContentsMargins(16, 14, 16, 14)
        left_lay.setSpacing(10)

        left_header = QLabel(t("pos_products") if t("pos_products") != "pos_products"
                             else "Products")
        left_header.setObjectName("pos_panel_title")
        left_lay.addWidget(left_header)

        self._search = QLineEdit()
        self._search.setPlaceholderText(f"  🔍  {t('pos_scan_or_search')}")
        self._search.setObjectName("search_bar")
        self._search.textChanged.connect(self._filter_products)
        self._search.returnPressed.connect(self._add_first_result)
        left_lay.addWidget(self._search)

        self._prod_table = QTableWidget(0, 4)
        self._prod_table.setHorizontalHeaderLabels([
            t("pos_col_item"), t("pos_col_price"),
            t("pos_col_stock") if t("pos_col_stock") != "pos_col_stock" else "Stock", "",
        ])
        ph = self._prod_table.horizontalHeader()
        ph.setMinimumSectionSize(30)
        ph.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        ph.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        ph.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        ph.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._prod_table.verticalHeader().setVisible(False)
        self._prod_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._prod_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._prod_table.setAlternatingRowColors(True)
        self._prod_table.doubleClicked.connect(self._add_selected_product)
        left_lay.addWidget(self._prod_table, 1)

        hint = QLabel(t("pos_add_hint") if t("pos_add_hint") != "pos_add_hint"
                      else "Double-click or press + to add")
        hint.setObjectName("pos_hint")
        left_lay.addWidget(hint)

        splitter.addWidget(left_frame)

        # ── RIGHT: Cart + checkout ───────────────────────────────────────
        right_frame = QFrame()
        right_frame.setObjectName("pos_panel")
        right_lay = QVBoxLayout(right_frame)
        right_lay.setContentsMargins(16, 14, 16, 14)
        right_lay.setSpacing(10)

        right_header = QLabel(t("pos_cart") if t("pos_cart") != "pos_cart" else "Cart")
        right_header.setObjectName("pos_panel_title")
        right_lay.addWidget(right_header)

        self._cart_table = QTableWidget(0, 4)
        self._cart_table.setHorizontalHeaderLabels([
            t("pos_col_item"), t("pos_col_price"),
            t("pos_col_qty"), t("pos_col_subtotal"),
        ])
        ch = self._cart_table.horizontalHeader()
        ch.setMinimumSectionSize(40)
        ch.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in (1, 2, 3):
            ch.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self._cart_table.verticalHeader().setVisible(False)
        self._cart_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._cart_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._cart_table.setAlternatingRowColors(True)
        right_lay.addWidget(self._cart_table, 1)

        # Remove button
        rm_row = QHBoxLayout()
        self._rm_btn = QPushButton(t("pos_remove_item"))
        self._rm_btn.setObjectName("pos_remove_btn")
        self._rm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._rm_btn.clicked.connect(self._remove_selected)
        rm_row.addWidget(self._rm_btn)
        rm_row.addStretch()
        right_lay.addLayout(rm_row)

        # Customer, discount, note
        footer = QFormLayout()
        footer.setSpacing(6)
        self._customer_combo = QComboBox()
        self._customer_combo.setEditable(True)
        self._customer_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._customer_combo.lineEdit().setPlaceholderText(t("cust_select_customer"))
        self._customer_combo.setMinimumWidth(140)
        self._load_customers()
        footer.addRow(t("sales_col_customer"), self._customer_combo)

        self._discount_spin = QDoubleSpinBox()
        self._discount_spin.setRange(0, 99999)
        self._discount_spin.setDecimals(2)
        self._discount_spin.valueChanged.connect(self._update_total)
        cfg = ShopConfig.get()
        self._discount_spin.setSuffix(f" {cfg.currency}")
        footer.addRow(t("pos_discount"), self._discount_spin)

        self._note_edit = QLineEdit()
        self._note_edit.setPlaceholderText(t("pos_note"))
        footer.addRow(t("pos_note"), self._note_edit)
        right_lay.addLayout(footer)

        # ── Total bar ──
        total_bar = QFrame()
        total_bar.setObjectName("pos_total_bar")
        total_lay = QHBoxLayout(total_bar)
        total_lay.setContentsMargins(16, 8, 16, 8)
        total_lbl = QLabel(t("pos_total") + ":")
        total_lbl.setObjectName("pos_total_label")
        total_lay.addWidget(total_lbl)
        total_lay.addStretch()
        self._total_lbl = QLabel("0.00")
        self._total_lbl.setObjectName("pos_total_value")
        total_lay.addWidget(self._total_lbl)
        right_lay.addWidget(total_bar)

        splitter.addWidget(right_frame)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        # ── Bottom action buttons ────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()
        cancel_btn = QPushButton(t("alert_cancel") if t("alert_cancel") != "alert_cancel" else "Cancel")
        cancel_btn.setObjectName("pos_cancel_btn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        self._complete_btn = QPushButton(f"  ✓  {t('pos_complete_sale')}")
        self._complete_btn.setObjectName("pos_complete_btn")
        self._complete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._complete_btn.clicked.connect(self._complete_sale)
        btn_row.addWidget(self._complete_btn)
        root.addLayout(btn_row)

    # ── Product list ─────────────────────────────────────────────────────────

    def _load_customers(self) -> None:
        """Populate customer combo with walk-in + all active customers."""
        self._customer_combo.clear()
        self._customer_combo.addItem(t("cust_walk_in"), None)
        customers = _cust_svc.get_all(active_only=True)
        for c in customers:
            label = c.name
            if c.phone:
                label += f"  ({c.phone})"
            self._customer_combo.addItem(label, c.id)

    def _load_products(self) -> None:
        """Fetch all in-stock items off the UI thread, render on return."""
        def _fetch():
            return [item for item in _item_repo.get_all_items() if item.stock > 0]
        def _apply(items):
            self._products = items
            self._render_products(self._products)
        POOL.submit("sales_products", _fetch, _apply)

    def _filter_products(self) -> None:
        query = self._search.text().strip().lower()
        if not query:
            self._render_products(self._products)
            return
        filtered = [
            p for p in self._products
            if query in p.display_name.lower()
            or (p.barcode and query in p.barcode.lower())
            or query in p.brand.lower()
            or query in p.name.lower()
        ]
        self._render_products(filtered)

    def _render_products(self, items: list[InventoryItem]) -> None:
        cfg = ShopConfig.get()
        self._prod_table.setRowCount(0)
        for item in items:
            row = self._prod_table.rowCount()
            self._prod_table.insertRow(row)

            name_it = QTableWidgetItem(item.display_name)
            name_it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            name_it.setData(Qt.ItemDataRole.UserRole, item.id)
            self._prod_table.setItem(row, 0, name_it)

            price_str = f"{cfg.currency} {item.sell_price:.2f}" if item.sell_price else "—"
            self._prod_table.setItem(row, 1, self._ro(price_str))
            self._prod_table.setItem(row, 2, self._ro(str(item.stock)))

            add_btn = QPushButton("+")
            add_btn.setObjectName("pos_add_btn")
            add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            add_btn.clicked.connect(lambda _, iid=item.id: self._add_item_by_id(iid))
            self._prod_table.setCellWidget(row, 3, add_btn)
            self._prod_table.setRowHeight(row, 38)

    def _add_first_result(self) -> None:
        if self._prod_table.rowCount() > 0:
            item_id = self._prod_table.item(0, 0).data(Qt.ItemDataRole.UserRole)
            self._add_item_by_id(item_id)

    def _add_selected_product(self) -> None:
        rows = {idx.row() for idx in self._prod_table.selectedIndexes()}
        if not rows:
            return
        row = min(rows)
        item_id = self._prod_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self._add_item_by_id(item_id)

    def _add_item_by_id(self, item_id: int) -> None:
        item = next((p for p in self._products if p.id == item_id), None)
        if not item:
            return

        for cart_item in self._cart:
            if cart_item["item_id"] == item.id:
                if cart_item["qty"] + 1 > cart_item["stock"]:
                    QMessageBox.warning(
                        self, t("pos_title"),
                        t("pos_insufficient_stock",
                          name=item.display_name, available=item.stock),
                    )
                    return
                cart_item["qty"] += 1
                self._refresh_cart()
                return

        price = item.sell_price or 0.0
        self._cart.append({
            "item_id": item.id,
            "name": item.display_name,
            "qty": 1,
            "price": price,
            "stock": item.stock,
        })
        self._refresh_cart()

    # ── Cart ─────────────────────────────────────────────────────────────────

    def _remove_selected(self) -> None:
        rows = {idx.row() for idx in self._cart_table.selectedIndexes()}
        if not rows:
            return
        for r in sorted(rows, reverse=True):
            if r < len(self._cart):
                self._cart.pop(r)
        self._refresh_cart()

    def _refresh_cart(self) -> None:
        cfg = ShopConfig.get()
        self._cart_table.setRowCount(0)
        for item in self._cart:
            row = self._cart_table.rowCount()
            self._cart_table.insertRow(row)
            self._cart_table.setItem(row, 0, self._ro(item["name"]))
            self._cart_table.setItem(row, 1, self._ro(
                f"{cfg.currency} {item['price']:.2f}"
            ))
            self._cart_table.setItem(row, 2, self._ro(str(item["qty"])))
            subtotal = item["qty"] * item["price"]
            self._cart_table.setItem(row, 3, self._ro(
                f"{cfg.currency} {subtotal:.2f}"
            ))
        self._update_total()

    def _update_total(self) -> None:
        subtotal = sum(c["qty"] * c["price"] for c in self._cart)
        discount = self._discount_spin.value()
        total = max(0, subtotal - discount)
        cfg = ShopConfig.get()
        self._total_lbl.setText(f"{cfg.currency} {total:.2f}")

    def _complete_sale(self) -> None:
        if not self._cart:
            QMessageBox.warning(self, t("pos_title"), t("sales_no_items"))
            return

        items = [
            {
                "item_id": c["item_id"],
                "quantity": c["qty"],
                "unit_price": c["price"],
            }
            for c in self._cart
        ]

        # Resolve customer from combo
        cust_id = self._customer_combo.currentData()
        cust_name = self._customer_combo.currentText().strip()
        if cust_id is not None:
            # Strip phone suffix if present
            cust_name = cust_name.split("  (")[0].strip()

        try:
            sale_id = _sale_svc.create_sale(
                customer_name=cust_name,
                discount=self._discount_spin.value(),
                note=self._note_edit.text().strip(),
                items=items,
                customer_id=cust_id,
            )
            self.result_sale_id = sale_id
            # Offer receipt generation
            reply = QMessageBox.question(
                self, t("pos_title"),
                t("pos_sale_success", id=sale_id) + "\n\nGenerate receipt?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    path = _receipt_svc.generate_receipt(sale_id)
                    import os
                    os.startfile(path) if hasattr(os, "startfile") else None
                except Exception:
                    pass
            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, t("pos_title"), str(e))

    @staticmethod
    def _ro(text: str) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        return it


# ── Sales History Page ───────────────────────────────────────────────────────

class SalesPage(QWidget):
    """Professional sales history page with KPI summary cards."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sales: list[Sale] = []
        self._build_ui()

    def _build_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setObjectName("analytics_scroll")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        # ── Header row ──
        header = QHBoxLayout()
        title = QLabel(t("sales_title"))
        title.setObjectName("sales_page_title")
        header.addWidget(title)
        header.addStretch()

        self._new_btn = QPushButton(f"  💰  {t('sales_new')}")
        self._new_btn.setObjectName("sales_new_btn")
        self._new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._new_btn.clicked.connect(self._new_sale)
        header.addWidget(self._new_btn)
        lay.addLayout(header)

        # ── KPI Row ──
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)
        self._kpi_count = _SalesKpiCard()
        self._kpi_revenue = _SalesKpiCard()
        self._kpi_avg = _SalesKpiCard()
        self._kpi_items = _SalesKpiCard()
        for card in (self._kpi_count, self._kpi_revenue, self._kpi_avg, self._kpi_items):
            kpi_row.addWidget(card)
        lay.addLayout(kpi_row)

        # ── Filter row ──
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        self._search = QLineEdit()
        self._search.setPlaceholderText(f"  🔍  {t('sales_filter_customer') if t('sales_filter_customer') != 'sales_filter_customer' else 'Filter by customer…'}")
        self._search.setObjectName("search_bar")
        self._search.setMaximumWidth(300)
        self._search.textChanged.connect(self._refresh)
        filter_row.addWidget(self._search)
        filter_row.addStretch()
        lay.addLayout(filter_row)

        # ── Table ──
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels([
            t("sales_col_date"), t("sales_col_customer"),
            t("sales_col_total"), t("sales_col_discount"),
            t("sales_col_net"), "",
        ])
        sh = self._table.horizontalHeader()
        sh.setMinimumSectionSize(40)
        sh.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(0, 130)
        sh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        sh.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(2, 110)
        sh.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(3, 100)
        sh.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(4, 110)
        sh.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(5, 50)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        # Cols: 0=Date  1=Customer  2=Total  3=Discount  4=Net  5=Actions
        make_table_responsive(self._table, [
            (3, 750),   # Discount — hide when viewport < 750 px
            (4, 650),   # Net      — hide when viewport < 650 px
            (0, 500),   # Date     — hide when viewport < 500 px
        ])
        lay.addWidget(self._table, 1)

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _new_sale(self) -> None:
        dlg = POSDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh()

    def _refresh(self) -> None:
        """Fetch all sales off the UI thread, then render KPIs + table."""
        search = self._search.text().strip().lower()
        def _fetch():
            return _sale_repo.get_all(limit=500)
        def _apply(sales):
            self._apply_sales(sales, search)
        POOL.submit("sales_refresh", _fetch, _apply)

    def _apply_sales(self, sales, search: str) -> None:
        """Main-thread render of sales KPIs + table with pre-fetched data."""
        self._sales = sales

        # KPIs (from all sales, before filtering)
        cfg = ShopConfig.get()
        count = len(self._sales)
        revenue = sum(s.net_total for s in self._sales)
        avg_sale = revenue / count if count > 0 else 0
        total_items = sum(s.item_count for s in self._sales)

        self._kpi_count.set_data(
            t("sales_kpi_count") if t("sales_kpi_count") != "sales_kpi_count" else "TOTAL SALES",
            str(count), "")
        self._kpi_revenue.set_data(
            t("sales_kpi_revenue") if t("sales_kpi_revenue") != "sales_kpi_revenue" else "REVENUE",
            cfg.format_currency(revenue) if hasattr(cfg, 'format_currency') else f"{cfg.currency} {revenue:.2f}",
            "")
        self._kpi_avg.set_data(
            t("sales_kpi_avg") if t("sales_kpi_avg") != "sales_kpi_avg" else "AVG. SALE",
            cfg.format_currency(avg_sale) if hasattr(cfg, 'format_currency') else f"{cfg.currency} {avg_sale:.2f}",
            "")
        self._kpi_items.set_data(
            t("sales_kpi_items") if t("sales_kpi_items") != "sales_kpi_items" else "ITEMS SOLD",
            str(total_items), "")

        # Apply search filter
        if search:
            self._sales = [
                s for s in self._sales if search in s.customer_name.lower()
            ]

        # Render table
        tk = THEME.tokens
        self._table.setRowCount(0)
        for sale in self._sales:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, self._ro(sale.timestamp))
            self._table.setItem(row, 1, self._ro(sale.customer_name or "—"))
            self._table.setItem(row, 2, self._ro(
                f"{cfg.currency} {sale.total_amount:.2f}"
            ))
            self._table.setItem(row, 3, self._ro(
                f"{cfg.currency} {sale.discount:.2f}" if sale.discount else "—"
            ))
            self._table.setItem(row, 4, self._ro(
                f"{cfg.currency} {sale.net_total:.2f}"
            ))
            # Receipt button — direct cell widget (no wrapper)
            rcpt_btn = QPushButton()
            rcpt_btn.setObjectName("admin_edit_btn")
            rcpt_btn.setIcon(get_colored_icon("receipt", tk.green))
            rcpt_btn.setIconSize(QSize(16, 16))
            rcpt_btn.setToolTip("Generate Receipt")
            rcpt_btn.setFixedSize(36, 36)
            rcpt_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            rcpt_btn.clicked.connect(lambda _, sid=sale.id: self._gen_receipt(sid))
            self._table.setCellWidget(row, 5, rcpt_btn)
            self._table.setRowHeight(row, 44)

    def _gen_receipt(self, sale_id: int) -> None:
        """Generate and open a receipt PDF for the given sale."""
        try:
            path = _receipt_svc.generate_receipt(sale_id)
            import os
            os.startfile(path) if hasattr(os, "startfile") else None
            QMessageBox.information(
                self, "Receipt",
                f"Receipt saved:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Receipt", f"Failed to generate receipt:\n{e}")

    def refresh(self) -> None:
        self._refresh()

    def retranslate(self) -> None:
        self.refresh()

    @staticmethod
    def _ro(text: str) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        return it
