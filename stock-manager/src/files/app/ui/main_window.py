"""
main_window.py — Stock Manager Pro v2
Orchestrates sidebar, header, pages, and application logic.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QSizePolicy, QStackedWidget,
    QMessageBox, QSpinBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut

from app.core.database import init_db, get_connection, ensure_matrix_entries
from app.core.health import run_startup_checks
from app.core.config import ShopConfig
from app.core.theme import THEME, GradientBackground
from app.core.i18n import t, set_lang

from app.ui.dialogs.admin.admin_dialog import AdminDialog
from app.ui.dialogs.setup_wizard import SetupWizard
from app.ui.dialogs.help_dialog import HelpDialog

from app.ui.controllers import inventory_ops, stock_ops, bulk_ops
from app.ui.controllers.update_controller import UpdateController
from app.ui.controllers.alert_controller import AlertController
from app.ui.controllers.nav_controller import NavController
from app.ui.controllers.startup_controller import StartupController

from app.repositories.category_repo import CategoryRepository
from app.repositories.item_repo import ItemRepository
from app.services.stock_service import StockService
from app.services.backup_scheduler import BackupScheduler
from app.models.item import InventoryItem

from app.ui.components.header_bar import HeaderBar
from app.ui.components.footer_bar import FooterBar
from app.ui.components.sidebar import Sidebar
from app.ui.pages.inventory_page import InventoryPage
from app.ui.tabs.matrix_tab import MatrixTab
from app.ui.tabs.quick_scan_tab import QuickScanTab
from app.ui.pages.barcode_gen_page import BarcodeGenPage
from app.ui.pages.transactions_page import TransactionsPage
from app.ui.pages.reports_page import ReportsPage
from app.ui.pages.analytics_page import AnalyticsPage
from app.ui.pages.sales_page import SalesPage
from app.ui.pages.purchase_orders_page import PurchaseOrdersPage
from app.ui.pages.returns_page import ReturnsPage
from app.ui.pages.suppliers_page import SuppliersPage
from app.ui.pages.audit_page import AuditPage
from app.ui.pages.price_lists_page import PriceListsPage
from app.ui.dialogs.admin.customers_panel import CustomersPanel
from app.ui.components.toast import ToastManager
from app.ui.workers.worker_pool import POOL

# ── Module-level singletons ─────────────────────────────────────────────────
_cat_repo  = CategoryRepository()
_item_repo = ItemRepository()
_stock_svc = StockService()


class MainWindow(QMainWindow):
    # Page indices (must match addWidget order in _build_ui)
    _PAGE_INVENTORY       = 0
    _PAGE_TRANSACTIONS    = 1
    _PAGE_QUICK_SCAN      = 2
    _PAGE_SALES           = 3
    _PAGE_CUSTOMERS       = 4
    _PAGE_PURCHASE_ORDERS = 5
    _PAGE_RETURNS         = 6
    _PAGE_BARCODE_GEN     = 7
    _PAGE_REPORTS         = 8
    _PAGE_SUPPLIERS       = 9
    _PAGE_ANALYTICS       = 10
    _PAGE_AUDIT           = 11
    _PAGE_PRICE_LISTS     = 12
    _PAGE_MATRIX_START    = 13

    def __init__(self, splash=None):
        super().__init__()

        def _sp(pct: int, label: str) -> None:
            if splash is not None:
                splash.set_progress(pct, label)
                QApplication.processEvents()

        _sp(15, t("startup_db"))
        init_db()
        self._health = run_startup_checks()

        cfg = ShopConfig.get()
        if cfg.theme in ("pro_dark", "pro_light", "dark", "light"):
            THEME.set_theme(cfg.theme)

        _sp(30, t("startup_config"))
        THEME.warm_cache()

        _title = cfg.name if cfg.name else t("app_title")
        self.setWindowTitle(_title)
        self.resize(1280, 800)
        self.setMinimumSize(800, 500)
        self._cp: InventoryItem | None = None

        self._bg = GradientBackground()
        self._bg.setObjectName("gradient_bg")
        self.setCentralWidget(self._bg)
        THEME.apply(self._bg)

        _sp(55, t("startup_ui"))
        self._build_ui()   # creates _header, _sidebar, _nav_ctrl, _content_layout

        # ── Controllers (must exist before _connect wires signals) ────────
        self._upd_ctrl = UpdateController(
            content_layout=self._content_layout,
            parent_widget=self._bg,
            parent=self,
        )
        self._alert_ctrl = AlertController(
            header=self._header,
            sidebar=self._sidebar,
            update_ctrl=self._upd_ctrl,
            parent=self,
        )
        self._upd_ctrl.badge_changed.connect(self._alert_ctrl.refresh)
        self._alert_ctrl.product_selected.connect(self._on_low_stock_product_selected)

        self._startup = StartupController(
            inv_page=self._inv_page,
            analytics_page=self._analytics_page,
            alert_ctrl=self._alert_ctrl,
            on_filters_changed=self._on_filters_changed,
            on_status=self._show_status,
            item_repo=_item_repo,
            parent=self,
        )

        self._connect()

        _sp(80, t("startup_ui"))
        self._toasts = ToastManager(self)

        # 60-second periodic alert refresh
        self._timer = QTimer(self)
        self._timer.setInterval(60_000)
        self._timer.timeout.connect(self._alert_ctrl.refresh)
        self._timer.start()

        self._backup_scheduler = BackupScheduler(parent=self)
        self._backup_scheduler.start()

        self._upd_ctrl.start_auto_check(ShopConfig.get().is_update_auto_check_enabled)

        # Defer all heavy data work until after the window is painted
        QTimer.singleShot(0, self._startup.begin)
        QTimer.singleShot(100, self._check_first_run)

    # ── Build ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self._bg)
        outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        self._header = HeaderBar()
        outer.addWidget(self._header, 0)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0); body.setSpacing(0)

        self._sidebar = Sidebar()
        body.addWidget(self._sidebar)

        content = QVBoxLayout()
        content.setContentsMargins(20, 16, 20, 12); content.setSpacing(0)
        self._content_layout = content   # UpdateController inserts banner here

        self._stack = QStackedWidget()
        self._stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)

        # ── Static pages (order must match _PAGE_* constants) ────────────
        self._inv_page        = InventoryPage();         self._stack.addWidget(self._inv_page)
        self._txn_page        = TransactionsPage();      self._stack.addWidget(self._txn_page)
        self._quick_scan_tab  = QuickScanTab();          self._stack.addWidget(self._quick_scan_tab)
        self._sales_page      = SalesPage();             self._stack.addWidget(self._sales_page)
        self._customers_page  = CustomersPanel();        self._stack.addWidget(self._customers_page)
        self._po_page         = PurchaseOrdersPage();    self._stack.addWidget(self._po_page)
        self._returns_page    = ReturnsPage();           self._stack.addWidget(self._returns_page)
        self._barcode_gen_page= BarcodeGenPage();        self._stack.addWidget(self._barcode_gen_page)
        self._reports_page    = ReportsPage();           self._stack.addWidget(self._reports_page)
        self._suppliers_page  = SuppliersPage();         self._stack.addWidget(self._suppliers_page)
        self._analytics_page  = AnalyticsPage();         self._stack.addWidget(self._analytics_page)
        self._audit_page      = AuditPage();             self._stack.addWidget(self._audit_page)
        self._price_lists_page= PriceListsPage();        self._stack.addWidget(self._price_lists_page)

        self._analytics_page.navigate_to.connect(lambda k: self._nav_ctrl.go(k))

        # ── NavController (created here so matrix tabs wire before connect) ─
        self._nav_ctrl = NavController(
            stack=self._stack,
            sidebar=self._sidebar,
            toggle_btn=self._header.sidebar_toggle,
            cat_repo=_cat_repo,
            matrix_tab_factory=MatrixTab,
            matrix_page_start=self._PAGE_MATRIX_START,
            help_fn=self._open_help,
            parent=self,
        )
        # Register all static pages with their optional refresh callbacks
        self._nav_ctrl.register("nav_inventory",       self._PAGE_INVENTORY)
        self._nav_ctrl.register("nav_transactions",    self._PAGE_TRANSACTIONS,
                                lambda: self._txn_page.refresh())
        self._nav_ctrl.register("nav_quick_scan",      self._PAGE_QUICK_SCAN,
                                lambda: self._quick_scan_tab.focus_input())
        self._nav_ctrl.register("nav_sales",           self._PAGE_SALES,
                                lambda: self._sales_page.refresh())
        self._nav_ctrl.register("nav_customers",       self._PAGE_CUSTOMERS,
                                lambda: self._customers_page.reload())
        self._nav_ctrl.register("nav_purchase_orders", self._PAGE_PURCHASE_ORDERS,
                                lambda: self._po_page.refresh())
        self._nav_ctrl.register("nav_returns",         self._PAGE_RETURNS,
                                lambda: self._returns_page.refresh())
        self._nav_ctrl.register("nav_barcode_gen",     self._PAGE_BARCODE_GEN,
                                lambda: self._barcode_gen_page.refresh())
        self._nav_ctrl.register("nav_reports",         self._PAGE_REPORTS,
                                lambda: self._reports_page.refresh())
        self._nav_ctrl.register("nav_suppliers",       self._PAGE_SUPPLIERS,
                                lambda: self._suppliers_page.refresh())
        self._nav_ctrl.register("nav_analytics",       self._PAGE_ANALYTICS,
                                lambda: self._analytics_page.refresh())
        self._nav_ctrl.register("nav_audit",           self._PAGE_AUDIT,
                                lambda: self._audit_page.refresh())
        self._nav_ctrl.register("nav_price_lists",     self._PAGE_PRICE_LISTS,
                                lambda: self._price_lists_page.refresh())

        # Populate initial dynamic matrix tabs
        self._nav_ctrl.rebuild_matrix_tabs()

        content.addSpacing(12)
        content.addWidget(self._stack, 1)
        content_w = QWidget(); content_w.setLayout(content)
        content_w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        body.addWidget(content_w, 1)

        body_w = QWidget(); body_w.setLayout(body)
        body_w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        outer.addWidget(body_w, 1)

        self._footer = FooterBar()
        outer.addWidget(self._footer, 0)

        # Initial nav: analytics dashboard
        self._nav_ctrl.go("nav_analytics")

    # ── Signals ──────────────────────────────────────────────────────────────

    def _connect(self) -> None:
        # Header
        self._header.sidebar_toggled.connect(self._nav_ctrl.toggle_sidebar)
        self._header.lang_changed.connect(self._set_lang)
        self._header.alerts_clicked.connect(self._alert_ctrl.toggle_panel)
        self._header.refresh_clicked.connect(self._refresh_all)
        self._header.theme_toggled.connect(self._toggle_mode)
        self._header.admin_clicked.connect(self._open_admin)
        self._header.search.barcode_scanned.connect(self._barcode)
        self._header.search.textChanged.connect(self._header_search_changed)

        # Sidebar navigation
        self._sidebar.nav_clicked.connect(self._nav_ctrl.go)

        # Inventory page
        tbl = self._inv_page.table
        det = self._inv_page.detail
        tbl.row_selected.connect(self._sel)
        det.request_in.connect(lambda: self._stock_op("IN"))
        det.request_out.connect(lambda: self._stock_op("OUT"))
        det.request_adj.connect(lambda: self._stock_op("ADJUST"))
        det.request_edit.connect(self._edit)
        det.request_del.connect(self._delete)
        tbl.ctx_stock_in.connect(lambda item: self._ctx_stock_op(item, "IN"))
        tbl.ctx_stock_out.connect(lambda item: self._ctx_stock_op(item, "OUT"))
        tbl.ctx_adjust.connect(lambda item: self._ctx_stock_op(item, "ADJUST"))
        tbl.ctx_edit.connect(self._ctx_edit)
        tbl.ctx_delete.connect(self._ctx_delete)
        tbl.ctx_view_txns.connect(self._ctx_view_txns)
        tbl.ctx_bulk_in.connect(lambda items: self._bulk_op(items, "IN"))
        tbl.ctx_bulk_out.connect(lambda items: self._bulk_op(items, "OUT"))
        tbl.ctx_bulk_delete.connect(self._bulk_delete)
        tbl.ctx_bulk_price.connect(self._bulk_price)
        tbl.quick_in.connect(self._quick_stock_in)
        tbl.quick_out.connect(self._quick_stock_out)
        self._inv_page.dashboard.action_new_product.connect(self._add_product)
        self._inv_page.dashboard.action_export.connect(self._export_csv)
        self._inv_page.filter_bar.filters_changed.connect(self._on_filters_changed)

        # Keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+N"),     self).activated.connect(self._add_product)
        QShortcut(QKeySequence("F5"),         self).activated.connect(self._refresh_all)
        QShortcut(QKeySequence("F1"),         self).activated.connect(self._open_help)
        QShortcut(QKeySequence("Ctrl+I"),     self).activated.connect(lambda: self._stock_op("IN"))
        QShortcut(QKeySequence("Ctrl+O"),     self).activated.connect(lambda: self._stock_op("OUT"))
        QShortcut(QKeySequence("Ctrl+J"),     self).activated.connect(lambda: self._stock_op("ADJUST"))
        QShortcut(QKeySequence("Ctrl+B"),     self).activated.connect(lambda: self._nav_ctrl.go("nav_barcode_gen"))
        QShortcut(QKeySequence("Ctrl+Alt+A"), self).activated.connect(self._open_admin)
        QShortcut(QKeySequence("Ctrl+P"),     self).activated.connect(self._export_csv)
        QShortcut(QKeySequence("Ctrl+F"),     self).activated.connect(self._focus_search)
        QShortcut(QKeySequence("Ctrl+1"),     self).activated.connect(lambda: self._nav_ctrl.go("nav_inventory"))
        QShortcut(QKeySequence("Ctrl+2"),     self).activated.connect(lambda: self._nav_ctrl.go("nav_transactions"))
        QShortcut(QKeySequence("Ctrl+3"),     self).activated.connect(lambda: self._nav_ctrl.go("nav_analytics"))
        QShortcut(QKeySequence("Ctrl+4"),     self).activated.connect(lambda: self._nav_ctrl.go("nav_reports"))
        QShortcut(QKeySequence("Ctrl+5"),     self).activated.connect(lambda: self._nav_ctrl.go("nav_purchase_orders"))
        QShortcut(QKeySequence("Ctrl+6"),     self).activated.connect(lambda: self._nav_ctrl.go("nav_returns"))
        QShortcut(QKeySequence("Ctrl+7"),     self).activated.connect(lambda: self._nav_ctrl.go("nav_suppliers"))
        QShortcut(QKeySequence("Escape"),     self).activated.connect(self._escape_handler)

        # Global barcode buffer
        self._global_bc_buf: list[str] = []
        self._global_bc_timer = QTimer(self)
        self._global_bc_timer.setSingleShot(True)
        self._global_bc_timer.setInterval(100)
        self._global_bc_timer.timeout.connect(self._flush_global_bc)

    def keyPressEvent(self, event):
        focus = self.focusWidget()
        if isinstance(focus, (QLineEdit, QSpinBox)):
            super().keyPressEvent(event); return
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._global_bc_timer.stop()
            bc = "".join(self._global_bc_buf).strip()
            self._global_bc_buf.clear()
            if bc: self._barcode(bc)
        elif event.text() and event.text().isprintable():
            self._global_bc_buf.append(event.text())
            self._global_bc_timer.start()
        else:
            super().keyPressEvent(event)

    def _flush_global_bc(self):
        if len(self._global_bc_buf) >= 3:
            bc = "".join(self._global_bc_buf).strip()
            if bc: self._barcode(bc)
        self._global_bc_buf.clear()

    # ── Admin / First-run ────────────────────────────────────────────────────

    def _check_first_run(self) -> None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM app_config WHERE key='setup_complete'"
            ).fetchone()
        if not row:
            wizard = SetupWizard(self); wizard.exec()
            ShopConfig.invalidate(); ensure_matrix_entries()
            self._nav_ctrl.rebuild_matrix_tabs()
            self._retranslate()

    def _open_admin(self) -> None:
        saved = self._nav_ctrl.current
        cfg_pre = ShopConfig.get()
        if cfg_pre.admin_pin:
            from PyQt6.QtWidgets import QInputDialog, QLineEdit as _LE
            pin, ok = QInputDialog.getText(
                self, t("pin_title"), t("pin_prompt"), _LE.EchoMode.Password,
            )
            if not ok: return
            if pin != cfg_pre.admin_pin:
                QMessageBox.warning(self, t("pin_title"), t("pin_wrong")); return

        dlg = AdminDialog(self)
        dlg.preview_banner_requested.connect(self._upd_ctrl.show_banner)
        dlg.exec()

        ShopConfig.invalidate()
        cfg = ShopConfig.get()
        if cfg.theme in ("pro_dark", "pro_light", "dark", "light"):
            THEME.set_theme(cfg.theme)
            self._header.theme_toggle._update_text()
            self._bg.update()
        ensure_matrix_entries()
        self._nav_ctrl.rebuild_matrix_tabs()
        self._retranslate()
        self._nav_ctrl.go(saved)

    # ── Language ─────────────────────────────────────────────────────────────

    def _set_lang(self, lang: str) -> None:
        set_lang(lang)
        self._header.update_lang_buttons(lang)
        self._retranslate()

    def _retranslate(self) -> None:
        cfg = ShopConfig.get()
        self.setWindowTitle(cfg.name if cfg.name else t("app_title"))
        # Phase 1: visible text — synchronous, no DB
        self._header.retranslate()
        self._footer.retranslate()
        self._sidebar.retranslate()
        self._inv_page.retranslate()
        self._txn_page.retranslate()
        self._quick_scan_tab.retranslate()
        self._po_page.retranslate()
        self._returns_page.retranslate()
        self._reports_page.retranslate()
        self._suppliers_page.retranslate()
        self._audit_page.retranslate()
        self._price_lists_page.retranslate()
        self._analytics_page.retranslate()
        self._nav_ctrl.retranslate_matrix_tabs()
        self._footer.show_status(t("statusbar_ready"))
        # Phase 2: DB data — deferred so Qt paints new labels first
        QTimer.singleShot(0, self._deferred_retranslate_refresh)

    def _deferred_retranslate_refresh(self) -> None:
        """Fires after Qt paints translated labels — now triggers all async refreshes."""
        self._refresh_products()
        self._refresh_summary()
        self._alert_ctrl.refresh()
        POOL.submit("analytics_refresh",
                    self._analytics_page._fetch_all_data,
                    self._analytics_page._apply_all_data)
        POOL.submit_debounced("txn_filter",
                              self._txn_page.fetch_filtered,
                              self._txn_page.load_results,
                              delay_ms=0)

    # ── Status ───────────────────────────────────────────────────────────────

    def _show_status(self, msg: str, timeout: int = 0, level: str = "") -> None:
        self._footer.show_status(msg, timeout, level)

    # ── Refresh (all DB work via POOL) ───────────────────────────────────────

    def _refresh_products(self) -> None:
        self._on_filters_changed(self._inv_page.filter_bar.get_filters())

    def _refresh_summary(self) -> None:
        POOL.submit("summary", _item_repo.get_summary, self._on_summary_ready)

    def _on_summary_ready(self, s: dict) -> None:
        self._inv_page.dashboard.update_data(s)
        self._inv_page._cached_count = s.get("total", 0)

    def _refresh_all(self) -> None:
        """Trigger all async refreshes in parallel — main thread never blocks."""
        self._inv_page.table.reset_column_widths()
        self._refresh_products()
        self._refresh_summary()
        self._alert_ctrl.refresh()
        # Transactions and analytics pages both async via POOL
        POOL.submit_debounced("txn_filter",
                              self._txn_page.fetch_filtered,
                              self._txn_page.load_results,
                              delay_ms=0)
        POOL.submit("analytics_refresh",
                    self._analytics_page._fetch_all_data,
                    self._analytics_page._apply_all_data)
        if self._cp:
            cp_id = self._cp.id
            POOL.submit(
                "refresh_selected",
                lambda: _item_repo.get_by_id(cp_id),
                lambda item: (setattr(self, '_cp', item),
                              self._inv_page.select_product(item)),
            )
        self._show_status(t("status_refreshed"), 2000)

    def _header_search_changed(self, text: str) -> None:
        self._inv_page.filter_bar.set_search(text.strip())

    def _on_filters_changed(self, filters: dict) -> None:
        POOL.submit_debounced(
            "inventory_filter",
            lambda: self._inv_page.fetch_filtered(filters),
            self._on_items_ready,
            delay_ms=150,
        )

    def _on_items_ready(self, items: list) -> None:
        count     = self._inv_page.load_items(items)
        all_count = getattr(self._inv_page, '_cached_count', 0) or count
        self._show_status(t("status_n_products", n=count), 3000)
        filters    = self._inv_page.filter_bar.get_filters()
        search     = filters.get("search", "")
        status     = filters.get("status", "all")
        sort_by    = filters.get("sort_by", "name_asc")
        has_filter = status != "all" or bool(search) or sort_by != "name_asc"
        if has_filter and count != all_count:
            self._footer.show_filter(f"{count} / {all_count}")
        else:
            self._footer.hide_filter()

    def _export_csv(self) -> None:
        try:
            from app.services.export_service import ExportService
            import os
            path = ExportService().export_inventory_csv()
            if path and os.path.exists(path):
                self._show_status(t("status_exported", path=path), 5000, level="ok")
                QMessageBox.information(self, t("msg_export_title"),
                                        t("msg_export_body", path=path))
            else:
                self._show_status(t("msg_export_failed"), 3000, level="err")
        except Exception as e:
            QMessageBox.critical(self, t("msg_error"), str(e))

    # ── Events ───────────────────────────────────────────────────────────────

    def _sel(self, item: InventoryItem | None) -> None:
        self._cp = item; self._inv_page.select_product(item)

    def _on_low_stock_product_selected(self, pid: int) -> None:
        self._nav_ctrl.go("nav_inventory")
        self._inv_page.table.select_by_id(pid)
        self._sel(_item_repo.get_by_id(pid))

    def _barcode(self, bc: str) -> None:
        from app.core.scan_config import ScanConfig
        scan_cfg = ScanConfig.get()
        if scan_cfg.is_command(bc) or self._quick_scan_tab._session.mode:
            self._header.search.clear()
            self._nav_ctrl.go("nav_quick_scan")
            self._quick_scan_tab.process_command_barcode(bc)
            self._quick_scan_tab.focus_input(); return
        item = _item_repo.get_by_barcode(bc)
        if item:
            self._header.search.clear()
            self._nav_ctrl.go("nav_inventory")
            self._inv_page.table.select_by_id(item.id); self._sel(item)
            self._show_status(t("status_scanned", brand=item.display_name, type=""), 5000)
        else:
            self._show_status(t("status_unknown_bc", bc=bc), 4000)
            if QMessageBox.question(
                self, t("msg_unknown_bc_title"), t("msg_unknown_bc_body", bc=bc),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            ) == QMessageBox.StandardButton.Yes:
                self._add_product(preset_barcode=bc)

    def _toggle_mode(self) -> None:
        self._bg.update()
        self._inv_page.table.viewport().update()
        self._inv_page.dashboard.apply_theme()
        if self._cp:
            self._inv_page.select_product(self._cp)

    # ── CRUD (delegated to controllers) ──────────────────────────────────────

    def _add_product(self, checked=False, preset_barcode=""):
        inventory_ops.add_product(self, checked=checked, preset_barcode=preset_barcode)

    def _edit(self):       inventory_ops.edit_product(self)
    def _delete(self):     inventory_ops.delete_product(self)

    def _stock_op(self, op: str):                      stock_ops.stock_op(self, op)
    def _ctx_stock_op(self, item: InventoryItem, op):  stock_ops.ctx_stock_op(self, item, op)
    def _ctx_edit(self, item: InventoryItem):          stock_ops.ctx_edit(self, item)
    def _ctx_delete(self, item: InventoryItem):        stock_ops.ctx_delete(self, item)
    def _ctx_view_txns(self, item: InventoryItem):     stock_ops.ctx_view_txns(self, item)
    def _quick_stock_in(self, item_id: int):           stock_ops.quick_stock_in(self, item_id)
    def _quick_stock_out(self, item_id: int):          stock_ops.quick_stock_out(self, item_id)

    def _bulk_op(self, items: list, op: str):  bulk_ops.bulk_op(self, items, op)
    def _bulk_delete(self, items: list):       bulk_ops.bulk_delete(self, items)
    def _bulk_price(self, items: list):        bulk_ops.bulk_price(self, items)

    # ── Keyboard helpers ─────────────────────────────────────────────────────

    def _focus_search(self) -> None:
        self._nav_ctrl.go("nav_inventory")
        self._header.search.setFocus(); self._header.search.selectAll()

    def _escape_handler(self) -> None:
        if self._header.search.hasFocus() and self._header.search.text():
            self._header.search.clear()
        elif self._cp:
            self._cp = None
            self._inv_page.select_product(None)
            self._inv_page.table.clearSelection()

    def _open_help(self) -> None:
        HelpDialog(self).exec()

    # ── Close ────────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        try: self._timer.stop(); self._global_bc_timer.stop()
        except Exception: pass
        event.accept()
