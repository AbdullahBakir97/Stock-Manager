"""
app/ui/pages/analytics_page.py — Professional analytics dashboard.

Top bar   : title + date preset buttons + from/to pickers (custom)
Section 1 : Executive KPI tiles (Stock value · Revenue · Transactions · Low stock)
Section 2 : Inventory (donut + by-brand bars + valuation pivot + by-part-type bars)
Section 3 : Sales (dual-line revenue chart + mini KPIs + top sellers + top customers)
Section 4 : Stock movement (IN vs OUT dual line + busiest hours + recent activity)
Section 5 : Scan invoices (KPIs + IN/OUT line + top invoice customers)

Every tile loads async via POOL.submit and is represented by a SkeletonBlock
until its data arrives. Empty data → friendly EmptyState. Errors → retry tile.

Click a bar/slice/KPI/pivot cell to drill down to the relevant page.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QScrollArea, QToolButton, QDateEdit,
    QSizePolicy, QStackedWidget,
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from app.core.theme import THEME, _rgba
from app.core.i18n import t
from app.core.config import ShopConfig
from app.ui.workers.worker_pool import POOL
from app.ui.components.charts import (
    DonutChart, HBarChart, AreaLineChart,
    PieSlice, BarItem, LinePoint,
)
from app.ui.components.dual_line_chart import DualLineChart
from app.ui.components.kpi_tile import KpiTile
from app.ui.components.pivot_table import PivotTable
from app.ui.components.skeleton import SkeletonBlock
from app.ui.components.empty_state import EmptyState

from app.services.analytics_service import (
    AnalyticsService, DateRange, range_for_preset,
)


_BRAND_COLORS = [
    "#10B981", "#3B82F6", "#F59E0B", "#8B5CF6", "#EF4444",
    "#06B6D4", "#EC4899", "#84CC16", "#F97316", "#14B8A6",
]


class AnalyticsPage(QWidget):
    """Root widget. Owns the date controller + all section tiles."""

    # Emitted by drill-downs — main_window wires this to nav_ctrl.go(key)
    navigate_to = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._svc = AnalyticsService()
        self._cfg = ShopConfig.get()
        self._range = range_for_preset("30d")
        self._tiles: dict[str, QStackedWidget] = {}
        self._nav_ctrl = None    # set externally by MainWindow if available
        self._inv_page = None
        self._txn_page = None
        self._build_ui()
        # Defer the first refresh — running it inline during MainWindow's
        # _build_ui blocks the UI thread for several seconds (5 analytics
        # workers + skeleton paint). Let the window paint first, then fire.
        from PyQt6.QtCore import QTimer as _QT
        _QT.singleShot(0, self.refresh)

    # ── External hooks (for drill-down navigation) ─────────────────────────

    def set_drilldown_targets(self, nav_ctrl=None, inv_page=None, txn_page=None):
        self._nav_ctrl = nav_ctrl
        self._inv_page = inv_page
        self._txn_page = txn_page

    # ── Build ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setObjectName("analytics_scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        inner = QWidget()
        scroll.setWidget(inner)
        root = QVBoxLayout(inner)
        root.setContentsMargins(18, 14, 18, 18)
        root.setSpacing(14)

        # ── Title + date bar ──
        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        self._title = QLabel(t("analytics_title"))
        self._title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self._title.setStyleSheet(f"color: {THEME.tokens.t1};")
        title_row.addWidget(self._title)
        title_row.addStretch()

        self._preset_btns: dict[str, QToolButton] = {}
        for key, label in [
            ("today", "Today"), ("7d", "7 days"), ("30d", "30 days"),
            ("90d", "90 days"), ("year", "Year"), ("custom", "Custom"),
        ]:
            b = QToolButton()
            b.setObjectName("analytics_preset_btn")
            b.setText(label)
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedHeight(28)
            b.clicked.connect(lambda _=False, k=key: self._set_preset(k))
            title_row.addWidget(b)
            self._preset_btns[key] = b

        self._from_edit = QDateEdit()
        self._from_edit.setCalendarPopup(True)
        self._from_edit.setDisplayFormat("yyyy-MM-dd")
        self._from_edit.setFixedHeight(28)
        self._from_edit.setDate(QDate.currentDate().addDays(-30))
        self._from_edit.dateChanged.connect(self._on_custom_date)

        self._to_edit = QDateEdit()
        self._to_edit.setCalendarPopup(True)
        self._to_edit.setDisplayFormat("yyyy-MM-dd")
        self._to_edit.setFixedHeight(28)
        self._to_edit.setDate(QDate.currentDate())
        self._to_edit.dateChanged.connect(self._on_custom_date)

        title_row.addWidget(self._from_edit)
        title_row.addWidget(self._to_edit)
        self._from_edit.setVisible(False); self._to_edit.setVisible(False)
        root.addLayout(title_row)

        # Range summary under the title
        self._range_lbl = QLabel("")
        self._range_lbl.setStyleSheet(
            f"color: {THEME.tokens.t4}; font-size: 11px;"
        )
        root.addWidget(self._range_lbl)

        # ── Section 1: Executive KPIs ──
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)
        self._kpi_stock = KpiTile()
        self._kpi_rev = KpiTile()
        self._kpi_tx = KpiTile()
        self._kpi_low = KpiTile()
        for t_ in (self._kpi_stock, self._kpi_rev, self._kpi_tx, self._kpi_low):
            kpi_row.addWidget(t_, 1)
        # Wire drill-downs
        self._kpi_stock.clicked.connect(lambda: self._drill("inventory"))
        self._kpi_rev.clicked.connect(lambda: self._drill("sales"))
        self._kpi_tx.clicked.connect(lambda: self._drill("transactions"))
        self._kpi_low.clicked.connect(lambda: self._drill("low_stock"))
        root.addLayout(kpi_row)

        # ── Section 2: Inventory ──
        root.addLayout(self._section_hdr("INVENTORY HEALTH"))
        inv_row1 = QHBoxLayout(); inv_row1.setSpacing(10)
        self._inv_donut_tile = self._tile("inv_donut", min_h=240)
        self._inv_brand_tile = self._tile("inv_brand", min_h=240)
        inv_row1.addWidget(self._inv_donut_tile, 1)
        inv_row1.addWidget(self._inv_brand_tile, 2)
        root.addLayout(inv_row1)

        root.addLayout(self._section_hdr("VALUATION — BRAND × PART TYPE"))
        self._inv_pivot_tile = self._tile("inv_pivot", min_h=260)
        root.addWidget(self._inv_pivot_tile)

        inv_row2 = QHBoxLayout(); inv_row2.setSpacing(10)
        self._inv_cat_tile = self._tile("inv_cat", min_h=220)
        self._inv_pt_tile = self._tile("inv_pt", min_h=220)
        inv_row2.addWidget(self._inv_cat_tile, 1)
        inv_row2.addWidget(self._inv_pt_tile, 1)
        root.addLayout(inv_row2)

        # ── Section 3: Sales ──
        root.addLayout(self._section_hdr("SALES PERFORMANCE"))
        self._sales_trend_tile = self._tile("sales_trend", min_h=240)
        root.addWidget(self._sales_trend_tile)

        sales_kpis = QHBoxLayout(); sales_kpis.setSpacing(10)
        self._kpi_scount = KpiTile()
        self._kpi_units_sold = KpiTile()
        self._kpi_avg_basket = KpiTile()
        self._kpi_best_day = KpiTile()
        for t_ in (self._kpi_scount, self._kpi_units_sold,
                   self._kpi_avg_basket, self._kpi_best_day):
            sales_kpis.addWidget(t_, 1)
        self._kpi_scount.clicked.connect(lambda: self._drill("sales"))
        self._kpi_avg_basket.clicked.connect(lambda: self._drill("sales"))
        root.addLayout(sales_kpis)

        sales_row = QHBoxLayout(); sales_row.setSpacing(10)
        self._sales_top_sellers_tile = self._tile("sales_top", min_h=240)
        self._sales_top_customers_tile = self._tile("sales_custs", min_h=240)
        sales_row.addWidget(self._sales_top_sellers_tile, 1)
        sales_row.addWidget(self._sales_top_customers_tile, 1)
        root.addLayout(sales_row)

        # ── Section 4: Stock movement ──
        root.addLayout(self._section_hdr("STOCK MOVEMENT"))
        self._mv_trend_tile = self._tile("mv_trend", min_h=240)
        root.addWidget(self._mv_trend_tile)

        mv_row = QHBoxLayout(); mv_row.setSpacing(10)
        self._mv_hourly_tile = self._tile("mv_hourly", min_h=220)
        self._mv_recent_tile = self._tile("mv_recent", min_h=220)
        mv_row.addWidget(self._mv_hourly_tile, 1)
        mv_row.addWidget(self._mv_recent_tile, 1)
        root.addLayout(mv_row)

        # ── Section 5: Scan invoices ──
        root.addLayout(self._section_hdr("SCAN INVOICES"))
        inv_kpis = QHBoxLayout(); inv_kpis.setSpacing(10)
        self._kpi_inv_count = KpiTile()
        self._kpi_inv_in = KpiTile()
        self._kpi_inv_out = KpiTile()
        self._kpi_inv_avg = KpiTile()
        for t_ in (self._kpi_inv_count, self._kpi_inv_in,
                   self._kpi_inv_out, self._kpi_inv_avg):
            inv_kpis.addWidget(t_, 1)
        root.addLayout(inv_kpis)

        inv_row = QHBoxLayout(); inv_row.setSpacing(10)
        self._inv_trend_tile = self._tile("inv_trend", min_h=240)
        self._inv_top_cust_tile = self._tile("inv_top_cust", min_h=240)
        inv_row.addWidget(self._inv_trend_tile, 2)
        inv_row.addWidget(self._inv_top_cust_tile, 1)
        root.addLayout(inv_row)

        root.addStretch()

        # Initial preset highlight
        self._set_preset("30d", push_refresh=False)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _section_hdr(self, text: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        row.setContentsMargins(0, 6, 0, 0)
        lbl = QLabel(text)
        lbl.setObjectName("analytics_section_hdr")
        lbl.setStyleSheet(
            f"color: {THEME.tokens.t3}; font-size: 11px;"
            f" font-weight: 800; letter-spacing: 0.10em;"
        )
        row.addWidget(lbl)
        # Small emerald underline as a decorative element
        underline = QFrame()
        underline.setFixedHeight(2); underline.setMinimumWidth(36)
        underline.setMaximumWidth(36)
        underline.setStyleSheet(f"background: {THEME.tokens.green};")
        row.addWidget(underline)
        row.addStretch()
        return row

    def _tile(self, key: str, min_h: int = 220) -> QStackedWidget:
        """Create a stacked widget (skeleton / empty / content) for a tile.

        Keyed by `key`; store in `self._tiles[key]` for later swaps.
        """
        stack = QStackedWidget()
        stack.setMinimumHeight(min_h)
        sk = SkeletonBlock(height=min_h)
        stack.addWidget(sk)             # index 0 — loading
        # index 1 placeholder: real content (set later)
        # index 2 placeholder: empty state (set later)
        self._tiles[key] = stack
        return stack

    def _swap(self, key: str, widget: QWidget) -> None:
        """Replace a tile's content with `widget`, stopping skeleton animation."""
        stack = self._tiles.get(key)
        if stack is None:
            return
        # Remove everything but keep skeleton for future reloads
        while stack.count() > 1:
            w = stack.widget(1)
            stack.removeWidget(w)
            w.deleteLater()
        stack.addWidget(widget)
        stack.setCurrentIndex(1)

    def _show_skeleton(self, key: str) -> None:
        stack = self._tiles.get(key)
        if stack:
            stack.setCurrentIndex(0)

    def _show_empty(self, key: str, title: str, subtitle: str,
                    icon: str = "📈") -> None:
        es = EmptyState(title=title, subtitle=subtitle, icon=icon)
        self._swap(key, es)

    # ── Date range / preset handling ───────────────────────────────────────

    def _set_preset(self, preset: str, *, push_refresh: bool = True) -> None:
        for k, b in self._preset_btns.items():
            b.setChecked(k == preset)
        is_custom = (preset == "custom")
        self._from_edit.setVisible(is_custom)
        self._to_edit.setVisible(is_custom)

        if preset == "custom":
            cf = self._from_edit.date().toString("yyyy-MM-dd")
            ct = self._to_edit.date().toString("yyyy-MM-dd")
            self._range = range_for_preset("custom", cf, ct)
        else:
            self._range = range_for_preset(preset)

        self._range_lbl.setText(
            f"Period: {self._range.current_from} → {self._range.current_to}  "
            f"·  vs  {self._range.compare_from} → {self._range.compare_to}"
        )
        if push_refresh:
            self.refresh()

    def _on_custom_date(self, *_a) -> None:
        cur = next((k for k, b in self._preset_btns.items()
                    if b.isChecked()), "custom")
        if cur == "custom":
            self._set_preset("custom", push_refresh=True)

    # ── Drill-down ────────────────────────────────────────────────────────

    def _drill(self, kind: str, value=None) -> None:
        key = {
            "inventory": "nav_inventory",
            "low_stock": "nav_inventory",
            "sales": "nav_sales",
            "transactions": "nav_transactions",
        }.get(kind)
        if not key:
            return
        try:
            self.navigate_to.emit(key)
            if self._nav_ctrl is not None:
                self._nav_ctrl.go(key)
        except Exception:
            pass

    # ── Refresh ────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        # Reset every tile to skeleton
        for k in self._tiles:
            self._show_skeleton(k)

        r = self._range
        svc = self._svc

        POOL.submit("an_kpi",       lambda: svc.executive_kpis(r),
                    self._apply_kpis, on_error=lambda e: self._on_block_error("kpi", e))
        POOL.submit("an_inventory", svc.inventory_block,
                    self._apply_inventory,
                    on_error=lambda e: self._on_block_error("inventory", e))
        POOL.submit("an_sales",     lambda: svc.sales_block(r),
                    self._apply_sales,
                    on_error=lambda e: self._on_block_error("sales", e))
        POOL.submit("an_movement",  lambda: svc.movement_block(r),
                    self._apply_movement,
                    on_error=lambda e: self._on_block_error("movement", e))
        POOL.submit("an_invoices",  lambda: svc.invoices_block(r),
                    self._apply_invoices,
                    on_error=lambda e: self._on_block_error("invoices", e))

    def _on_block_error(self, block: str, msg: str) -> None:
        # Swap any tile still showing skeleton with an error empty-state
        err_map = {
            "kpi": [],   # KPI tiles don't use the stack
            "inventory": ["inv_donut", "inv_brand", "inv_pivot",
                          "inv_cat", "inv_pt"],
            "sales": ["sales_trend", "sales_top", "sales_custs"],
            "movement": ["mv_trend", "mv_hourly", "mv_recent"],
            "invoices": ["inv_trend", "inv_top_cust"],
        }
        for k in err_map.get(block, []):
            self._show_empty(k,
                             title="Couldn't load",
                             subtitle=(msg or "Unknown error"),
                             icon="⚠")

    # ── Apply slots (main thread) ──────────────────────────────────────────

    def _apply_kpis(self, data: dict) -> None:
        cfg = self._cfg
        tk = THEME.tokens

        sv = data.get("stock_value", {})
        self._kpi_stock.set_data(
            label="STOCK VALUE",
            value=cfg.format_currency(f"{sv.get('value', 0):,.2f}"),
            delta_pct=sv.get("delta_pct", 0),
            delta_dir=sv.get("delta_dir", "flat"),
            sparkline=sv.get("sparkline"),
            accent=tk.green,
        )
        rv = data.get("revenue", {})
        self._kpi_rev.set_data(
            label="REVENUE",
            value=cfg.format_currency(f"{rv.get('value', 0):,.2f}"),
            delta_pct=rv.get("delta_pct", 0),
            delta_dir=rv.get("delta_dir", "flat"),
            sparkline=rv.get("sparkline"),
            accent=tk.blue,
        )
        tx = data.get("transactions", {})
        self._kpi_tx.set_data(
            label="TRANSACTIONS",
            value=f"{int(tx.get('value', 0)):,}",
            delta_pct=tx.get("delta_pct", 0),
            delta_dir=tx.get("delta_dir", "flat"),
            sparkline=tx.get("sparkline"),
            accent=tk.orange,
        )
        lo = data.get("low_stock", {})
        self._kpi_low.set_data(
            label="LOW STOCK",
            value=f"{int(lo.get('value', 0))} items",
            delta_pct=lo.get("delta_pct", 0),
            delta_dir=lo.get("delta_dir", "flat"),
            sparkline=lo.get("sparkline"),
            accent=tk.red,
        )

    def _apply_inventory(self, data: dict) -> None:
        tk = THEME.tokens
        cfg = self._cfg
        money_fmt = lambda v: cfg.format_currency(f"{v:,.2f}")

        # Donut
        donut_rows = data.get("donut", [])
        if donut_rows:
            dc = DonutChart()
            dc.set_data(
                [PieSlice(label=lbl, value=v, color=c) for (lbl, v, c) in donut_rows],
                center_value=str(int(data.get("total_products", 0))),
                center_label="Products",
            )
            self._swap("inv_donut", self._card("Stock Health", dc))
        else:
            self._show_empty("inv_donut", "No products yet",
                              "Add products to see stock health.", icon="📦")

        # By brand
        by_brand = data.get("by_brand", [])
        if by_brand:
            bc = HBarChart()
            bars = [BarItem(label=r["brand"],
                            value=float(r["value"] or 0),
                            color=_BRAND_COLORS[i % len(_BRAND_COLORS)])
                    for i, r in enumerate(by_brand[:12])]
            bc.set_data(bars, title="Stock value per brand",
                         value_format=money_fmt)
            self._swap("inv_brand", self._card("Value by Brand", bc))
        else:
            self._show_empty("inv_brand", "No brands tracked",
                              "Stock distribution will appear here.", icon="🏷")

        # Pivot
        pivot = data.get("pivot", {})
        if pivot.get("brands") and pivot.get("part_types"):
            pt = PivotTable()
            pt.set_data(pivot)
            pt.cell_clicked_drilldown.connect(self._on_pivot_click)
            self._swap("inv_pivot", self._card("Valuation Pivot", pt))
        else:
            self._show_empty("inv_pivot", "No stock to pivot",
                              "Add inventory with prices to see the pivot.",
                              icon="🧮")

        # Units by Category — bar chart (sum units per category)
        by_pt = data.get("by_part_type", [])
        cats: dict[str, dict] = {}
        for r in by_pt:
            k = r.get("cat_name") or "Uncategorised"
            e = cats.setdefault(k, {"units": 0, "value": 0.0})
            e["units"] += int(r.get("units") or 0)
            e["value"] += float(r.get("value") or 0)
        if cats:
            bc = HBarChart()
            bars = [BarItem(label=k, value=float(v["units"]),
                            color=_BRAND_COLORS[i % len(_BRAND_COLORS)])
                    for i, (k, v) in enumerate(sorted(cats.items(),
                                                        key=lambda kv: kv[1]["units"],
                                                        reverse=True))]
            bc.set_data(bars, title="Units by category")
            self._swap("inv_cat", self._card("Units by Category", bc))
        else:
            self._show_empty("inv_cat", "No categories",
                              "Create categories in Admin.", icon="🗂")

        # Top Part Types by value
        if by_pt:
            top = sorted(by_pt, key=lambda r: float(r.get("value") or 0),
                         reverse=True)[:10]
            bc = HBarChart()
            bars = [BarItem(label=r.get("pt_name") or "—",
                            value=float(r.get("value") or 0),
                            color=tk.blue)
                    for r in top]
            bc.set_data(bars, title="Top 10 part types by value",
                         value_format=money_fmt)
            self._swap("inv_pt", self._card("Top Part Types by Value", bc))
        else:
            self._show_empty("inv_pt", "No part-type values",
                              "Add items and set prices.", icon="💰")

    def _apply_sales(self, data: dict) -> None:
        cfg = self._cfg
        tk = THEME.tokens
        money_fmt = lambda v: cfg.format_currency(f"{v:,.2f}")

        # Revenue trend (dual line)
        cur = data.get("cur_series", [])
        prev = data.get("prev_series", [])
        if cur:
            chart = DualLineChart()
            chart.set_data(cur, prev,
                           title="Revenue · current vs previous period",
                           line_color=tk.green)
            self._swap("sales_trend", self._card("Revenue Trend", chart))
        else:
            self._show_empty("sales_trend",
                              "No sales in this period",
                              "Revenue trend will appear once POS sales begin.",
                              icon="📈")

        # Mini KPIs
        rev = data.get("revenue", 0.0)
        rev_pct, rev_dir = data.get("revenue_delta", (0.0, "flat"))
        sc = data.get("sales_count", 0)
        sc_pct, sc_dir = data.get("sales_count_delta", (0.0, "flat"))
        self._kpi_scount.set_data(label="SALES",
            value=str(sc),
            delta_pct=sc_pct, delta_dir=sc_dir,
            sparkline=[v for _, v in cur],
            accent=tk.blue,
        )
        # "Units sold" ≈ sales_count for now (sale_items.quantity would be exact)
        self._kpi_units_sold.set_data(label="UNITS SOLD",
            value=str(sc),
            delta_pct=0, delta_dir="flat",
            sparkline=[v for _, v in cur],
            accent=tk.green,
        )
        avg = data.get("avg_basket", 0.0)
        self._kpi_avg_basket.set_data(label="AVG BASKET",
            value=cfg.format_currency(f"{avg:,.2f}"),
            delta_pct=0, delta_dir="flat",
            sparkline=[v for _, v in cur],
            accent=tk.orange,
        )
        best_label, best_val = data.get("best_day", ("—", 0))
        self._kpi_best_day.set_data(label="BEST DAY",
            value=cfg.format_currency(f"{float(best_val):,.2f}"),
            delta_pct=0, delta_dir="flat",
            sparkline=[v for _, v in cur],
            accent=tk.purple,
        )

        # Top sellers
        top_sellers = data.get("top_sellers", [])
        if top_sellers:
            bc = HBarChart()
            bars = [BarItem(label=(r.get("item_name") or "—")[:34],
                            value=float(r.get("total_qty") or 0),
                            color=tk.blue)
                    for r in top_sellers[:10]]
            bc.set_data(bars, title="Top 10 by units sold")
            self._swap("sales_top",
                       self._card("Top Sellers", bc))
        else:
            self._show_empty("sales_top", "No sales data",
                              "Best-sellers will show after your first sale.",
                              icon="🛒")

        # Top customers
        top_customers = data.get("top_customers", [])
        if top_customers:
            bc = HBarChart()
            bars = [BarItem(label=(r.get("customer_name") or "—")[:28],
                            value=float(r.get("revenue") or 0),
                            color=tk.purple)
                    for r in top_customers[:10]]
            bc.set_data(bars, title="Top customers by revenue",
                         value_format=money_fmt)
            self._swap("sales_custs",
                       self._card("Top Customers", bc))
        else:
            self._show_empty("sales_custs",
                              "No customer sales yet",
                              "Link sales to customers to see rankings.",
                              icon="👥")

    def _apply_movement(self, data: dict) -> None:
        tk = THEME.tokens

        in_s = data.get("in_series", [])
        out_s = data.get("out_series", [])
        if in_s or out_s:
            # Combine into a single dual-line view: IN (green) vs OUT (red)
            chart = DualLineChart()
            chart.set_data(in_s, out_s, title="IN vs OUT  ·  daily units",
                           line_color=tk.green)
            self._swap("mv_trend", self._card("Stock Movement Trend", chart))
        else:
            self._show_empty("mv_trend",
                              "No transactions in this period",
                              "Stock-in / stock-out activity will appear here.",
                              icon="📊")

        # Busiest hours
        hourly = data.get("hourly", [])
        if hourly:
            bc = HBarChart()
            bars = [BarItem(label=f"{h['hour']:02d}:00",
                            value=float(h["count"] or 0),
                            color=tk.blue)
                    for h in hourly if (h.get("count") or 0) > 0]
            if bars:
                # Keep top 12 busiest hours for readability
                bars = sorted(bars, key=lambda b: b.value, reverse=True)[:12]
                bc.set_data(bars, title="Busiest hours of day")
                self._swap("mv_hourly",
                           self._card("Busiest Hours", bc))
            else:
                self._show_empty("mv_hourly", "No hourly activity",
                                  "Hour-of-day breakdown will show after activity.",
                                  icon="⏰")
        else:
            self._show_empty("mv_hourly", "No hourly activity",
                              "Hour-of-day breakdown will show after activity.",
                              icon="⏰")

        # Recent activity feed — simple stacked labels in a card
        recent = data.get("recent", [])
        if recent:
            feed = QWidget()
            flay = QVBoxLayout(feed)
            flay.setContentsMargins(6, 6, 6, 6)
            flay.setSpacing(4)
            op_colours = {"IN": tk.green, "OUT": tk.red,
                           "ADJUST": tk.blue, "CREATE": tk.purple}
            for tx in recent[:8]:
                row = QFrame()
                row.setStyleSheet(
                    f"background: {_rgba(op_colours.get(tx.operation, tk.t4), '15')};"
                    f" border-radius: 4px;"
                )
                rl = QHBoxLayout(row); rl.setContentsMargins(10, 5, 10, 5)
                op_lbl = QLabel(tx.operation)
                op_lbl.setStyleSheet(
                    f"color: {op_colours.get(tx.operation, tk.t4)};"
                    f" font-weight: 700; font-size: 10px;"
                )
                op_lbl.setFixedWidth(48)
                rl.addWidget(op_lbl)
                name = (tx.display_name or f"Item #{tx.item_id}")[:36]
                nm_lbl = QLabel(name)
                nm_lbl.setStyleSheet(f"color: {tk.t1}; font-size: 11px;")
                rl.addWidget(nm_lbl, 1)
                qty_lbl = QLabel(f"{tx.quantity:+d}")
                qty_lbl.setStyleSheet(
                    f"color: {op_colours.get(tx.operation, tk.t4)};"
                    f" font-family: 'JetBrains Mono'; font-size: 11px;"
                    f" font-weight: 700;"
                )
                rl.addWidget(qty_lbl)
                ts = QLabel((tx.timestamp or "")[:16])
                ts.setStyleSheet(f"color: {tk.t4}; font-size: 10px;")
                rl.addWidget(ts)
                flay.addWidget(row)
            flay.addStretch()
            self._swap("mv_recent", self._card("Recent Activity", feed))
        else:
            self._show_empty("mv_recent", "No recent activity",
                              "Recent transactions will show here.",
                              icon="📋")

    def _apply_invoices(self, data: dict) -> None:
        cfg = self._cfg
        tk = THEME.tokens
        totals = data.get("totals", {})
        count = int(totals.get("count") or 0)
        in_total = float(totals.get("total_in") or 0)
        out_total = float(totals.get("total_out") or 0)
        avg = float(data.get("avg_invoice") or 0)
        dpct, ddir = data.get("total_delta", (0.0, "flat"))

        in_series = data.get("in_series", [])
        out_series = data.get("out_series", [])
        in_spark = [v for _, v in in_series]
        out_spark = [v for _, v in out_series]

        self._kpi_inv_count.set_data(label="INVOICES",
            value=f"{count}",
            delta_pct=dpct, delta_dir=ddir,
            sparkline=[a + b for a, b in zip(in_spark, out_spark)] or None,
            accent=tk.blue,
        )
        self._kpi_inv_in.set_data(label="IN TOTAL",
            value=cfg.format_currency(f"{in_total:,.2f}"),
            sparkline=in_spark or None,
            accent=tk.green,
        )
        self._kpi_inv_out.set_data(label="OUT TOTAL",
            value=cfg.format_currency(f"{out_total:,.2f}"),
            sparkline=out_spark or None,
            accent=tk.red,
        )
        self._kpi_inv_avg.set_data(label="AVG INVOICE",
            value=cfg.format_currency(f"{avg:,.2f}"),
            sparkline=[a + b for a, b in zip(in_spark, out_spark)] or None,
            accent=tk.orange,
        )

        if in_series or out_series:
            chart = DualLineChart()
            chart.set_data(in_series, out_series,
                           title="Invoice volume  ·  IN vs OUT (€)",
                           line_color=tk.green)
            self._swap("inv_trend",
                       self._card("Daily Invoice Volume", chart))
        else:
            self._show_empty("inv_trend", "No invoices in this period",
                              "Quick Scan invoices will appear here.",
                              icon="🧾")

        top = data.get("top_customers", [])
        if top:
            bc = HBarChart()
            money_fmt = lambda v: cfg.format_currency(f"{v:,.2f}")
            bars = [BarItem(label=(r.get("customer_name") or "—")[:24],
                            value=float(r.get("revenue") or 0),
                            color=tk.purple)
                    for r in top[:10]]
            bc.set_data(bars, title="Top invoice customers",
                         value_format=money_fmt)
            self._swap("inv_top_cust", self._card("Top Invoice Customers", bc))
        else:
            self._show_empty("inv_top_cust", "No customer invoices",
                              "Add customers to invoices in Quick Scan.",
                              icon="🧾")

    # ── Drill-down signal from pivot ───────────────────────────────────────

    def _on_pivot_click(self, brand: str, pt_id: int) -> None:
        try:
            if self._inv_page and hasattr(self._inv_page.filter_bar, "set_search"):
                self._inv_page.filter_bar.set_search(brand)
            self.navigate_to.emit("nav_inventory")
            if self._nav_ctrl is not None:
                self._nav_ctrl.go("nav_inventory")
        except Exception:
            pass

    # ── Card wrapper ───────────────────────────────────────────────────────

    def _card(self, title: str, content: QWidget) -> QFrame:
        card = QFrame()
        card.setObjectName("analytics_chart_card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)
        ttl = QLabel(title)
        ttl.setObjectName("analytics_chart_title")
        ttl.setStyleSheet(
            f"color: {THEME.tokens.t2}; font-size: 12px; font-weight: 600;"
        )
        lay.addWidget(ttl)
        lay.addWidget(content, 1)
        return card

    # ── Retranslate ────────────────────────────────────────────────────────

    def retranslate(self) -> None:
        self._title.setText(t("analytics_title"))

    # ── Backward-compat hooks for main_window's existing POOL.submit call ──
    # Old API:
    #   POOL.submit("analytics_refresh", page._fetch_all_data, page._apply_all_data)
    # We satisfy that contract: _fetch_all_data is a no-op on the worker
    # thread (returns a sentinel), _apply_all_data schedules the real
    # multi-tile async refresh from the main thread.

    def _fetch_all_data(self):   # worker thread — must not touch Qt widgets
        return None

    def _apply_all_data(self, _ignored=None):   # main thread
        QTimer.singleShot(0, self.refresh)
