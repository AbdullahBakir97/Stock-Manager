"""
app/ui/pages/analytics_page.py — Interactive analytics dashboard with charts.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QSizePolicy, QGridLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal
from app.ui.workers.worker_pool import POOL

from app.core.theme import THEME, _rgba
from app.core.i18n import t
from app.core.config import ShopConfig
from app.repositories.item_repo import ItemRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.category_repo import CategoryRepository
from app.repositories.sale_repo import SaleRepository
from app.services.customer_service import CustomerService
from app.ui.components.charts import (
    DonutChart, HBarChart, AreaLineChart,
    PieSlice, BarItem, LinePoint,
)


_item_repo = ItemRepository()
_txn_repo  = TransactionRepository()
_cat_repo  = CategoryRepository()
_sale_repo = SaleRepository()
_cust_svc  = CustomerService()


class _KpiCard(QFrame):
    """Single KPI metric card."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("analytics_kpi")
        self.setFixedHeight(90)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(4)
        self._label = QLabel()
        self._label.setObjectName("analytics_kpi_label")
        self._value = QLabel()
        self._value.setObjectName("analytics_kpi_value")
        self._sub = QLabel()
        self._sub.setObjectName("analytics_kpi_sub")
        lay.addWidget(self._label)
        lay.addWidget(self._value)
        lay.addWidget(self._sub)

    def set_data(self, label: str, value: str, sub: str = "") -> None:
        self._label.setText(label)
        self._value.setText(value)
        self._sub.setText(sub)


class _ClickableFrame(QFrame):
    """QFrame that emits a signal when clicked."""
    clicked = pyqtSignal(str)

    def __init__(self, key: str, parent=None):
        super().__init__(parent)
        self._key = key

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._key)
        super().mousePressEvent(event)


class AnalyticsPage(QWidget):
    """Full analytics dashboard with KPIs, donut chart, bar chart, and trend line."""

    navigate_to = pyqtSignal(str)  # emits nav key like "nav_inventory"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setObjectName("analytics_scroll")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(20)

        # ── Title ──
        self._title = QLabel(t("analytics_title"))
        self._title.setObjectName("analytics_page_title")
        root.addWidget(self._title)

        # ── KPI Row ──
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)
        self._kpi_total    = _KpiCard()
        self._kpi_units    = _KpiCard()
        self._kpi_value    = _KpiCard()
        self._kpi_health   = _KpiCard()
        for card in (self._kpi_total, self._kpi_units, self._kpi_value, self._kpi_health):
            kpi_row.addWidget(card)
        root.addLayout(kpi_row)

        # ── Quick Actions + Recent Activity Row ──
        qa_row = QHBoxLayout()
        qa_row.setSpacing(12)

        # Quick actions card
        qa_frame = QFrame()
        qa_frame.setObjectName("analytics_chart_card")
        qa_lay = QVBoxLayout(qa_frame)
        qa_lay.setContentsMargins(16, 14, 16, 14)
        qa_lay.setSpacing(8)
        qa_hdr = QLabel(t("analytics_quick_actions"))
        qa_hdr.setObjectName("analytics_chart_title")
        qa_lay.addWidget(qa_hdr)
        self._qa_hdr = qa_hdr

        qa_btns_lay = QGridLayout()
        qa_btns_lay.setSpacing(8)
        qa_actions = [
            ("📦", t("nav_inventory"), "nav_inventory"),
            ("🏭", t("nav_suppliers"), "nav_suppliers"),
            ("🛒", t("nav_purchase_orders"), "nav_purchase_orders"),
            ("↩", t("nav_returns"), "nav_returns"),
            ("💰", t("nav_sales") if t("nav_sales") != "nav_sales" else "Sales", "nav_sales"),
            ("📊", t("nav_reports") if t("nav_reports") != "nav_reports" else "Reports", "nav_reports"),
        ]
        for idx, (icon, label, nav_key) in enumerate(qa_actions):
            btn = _ClickableFrame(nav_key)
            btn.setObjectName("scan_feed_item")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(self.navigate_to.emit)
            btn_lay = QHBoxLayout(btn)
            btn_lay.setContentsMargins(10, 8, 10, 8)
            btn_lay.setSpacing(8)
            icon_l = QLabel(icon)
            icon_l.setStyleSheet("font-size: 16px;")
            icon_l.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            btn_lay.addWidget(icon_l)
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 12px; font-weight: 500;")
            lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            btn_lay.addWidget(lbl, 1)
            qa_btns_lay.addWidget(btn, idx // 3, idx % 3)
        qa_lay.addLayout(qa_btns_lay)
        qa_row.addWidget(qa_frame, 1)

        # Recent activity feed
        ra_frame = QFrame()
        ra_frame.setObjectName("analytics_chart_card")
        ra_lay = QVBoxLayout(ra_frame)
        ra_lay.setContentsMargins(16, 14, 16, 14)
        ra_lay.setSpacing(6)
        ra_hdr = QLabel(t("analytics_recent_activity"))
        ra_hdr.setObjectName("analytics_chart_title")
        ra_lay.addWidget(ra_hdr)
        self._ra_hdr = ra_hdr
        self._ra_container = QVBoxLayout()
        self._ra_container.setSpacing(4)
        ra_lay.addLayout(self._ra_container)
        ra_lay.addStretch()
        qa_row.addWidget(ra_frame, 1)

        root.addLayout(qa_row)

        # ── Charts Row 1: Donut + Bar ──
        charts1 = QHBoxLayout()
        charts1.setSpacing(16)

        # Stock Health Donut
        donut_frame = QFrame()
        donut_frame.setObjectName("analytics_chart_card")
        donut_lay = QVBoxLayout(donut_frame)
        donut_lay.setContentsMargins(16, 14, 16, 14)
        donut_lay.setSpacing(8)
        self._donut_hdr = QLabel(t("analytics_stock_health"))
        self._donut_hdr.setObjectName("analytics_chart_title")
        donut_lay.addWidget(self._donut_hdr)
        self._donut = DonutChart()
        self._donut.setMinimumHeight(220)
        donut_lay.addWidget(self._donut, 1)
        charts1.addWidget(donut_frame, 1)

        # Category Distribution Bar
        bar_frame = QFrame()
        bar_frame.setObjectName("analytics_chart_card")
        bar_lay = QVBoxLayout(bar_frame)
        bar_lay.setContentsMargins(16, 14, 16, 14)
        bar_lay.setSpacing(8)
        self._bar_hdr = QLabel(t("analytics_by_category"))
        self._bar_hdr.setObjectName("analytics_chart_title")
        bar_lay.addWidget(self._bar_hdr)
        self._bar = HBarChart()
        self._bar.setMinimumHeight(220)
        bar_lay.addWidget(self._bar, 1)
        charts1.addWidget(bar_frame, 1)

        root.addLayout(charts1)

        # ── Charts Row 2: Activity trend (full width) ──
        trend_frame = QFrame()
        trend_frame.setObjectName("analytics_chart_card")
        trend_lay = QVBoxLayout(trend_frame)
        trend_lay.setContentsMargins(16, 14, 16, 14)
        trend_lay.setSpacing(8)
        self._trend_hdr = QLabel(t("analytics_activity_trend"))
        self._trend_hdr.setObjectName("analytics_chart_title")
        trend_lay.addWidget(self._trend_hdr)
        self._trend = AreaLineChart()
        self._trend.setMinimumHeight(200)
        trend_lay.addWidget(self._trend, 1)
        root.addWidget(trend_frame)

        # ── Top Low-Stock Items ──
        low_frame = QFrame()
        low_frame.setObjectName("analytics_chart_card")
        low_lay = QVBoxLayout(low_frame)
        low_lay.setContentsMargins(16, 14, 16, 14)
        low_lay.setSpacing(8)
        self._low_hdr = QLabel(t("analytics_top_low_stock"))
        self._low_hdr.setObjectName("analytics_chart_title")
        low_lay.addWidget(self._low_hdr)
        self._low_bar = HBarChart()
        self._low_bar.setMinimumHeight(180)
        low_lay.addWidget(self._low_bar, 1)
        root.addWidget(low_frame)

        # ── Sales & Customers Section ──
        sc_title = QLabel(t("analytics_sales_customers")
                          if t("analytics_sales_customers") != "analytics_sales_customers"
                          else "Sales & Customers")
        sc_title.setObjectName("analytics_chart_title")
        root.addWidget(sc_title)

        # Sales KPI Row
        sales_kpi_row = QHBoxLayout()
        sales_kpi_row.setSpacing(12)
        self._kpi_sales_today  = _KpiCard()
        self._kpi_revenue      = _KpiCard()
        self._kpi_customers    = _KpiCard()
        self._kpi_avg_order    = _KpiCard()
        for card in (self._kpi_sales_today, self._kpi_revenue,
                     self._kpi_customers, self._kpi_avg_order):
            sales_kpi_row.addWidget(card)
        root.addLayout(sales_kpi_row)

        # Top customers chart
        top_cust_frame = QFrame()
        top_cust_frame.setObjectName("analytics_chart_card")
        tc_lay = QVBoxLayout(top_cust_frame)
        tc_lay.setContentsMargins(16, 14, 16, 14)
        tc_lay.setSpacing(8)
        self._top_cust_hdr = QLabel("Top Customers by Spend")
        self._top_cust_hdr.setObjectName("analytics_chart_title")
        tc_lay.addWidget(self._top_cust_hdr)
        self._top_cust_bar = HBarChart()
        self._top_cust_bar.setMinimumHeight(180)
        tc_lay.addWidget(self._top_cust_bar, 1)
        root.addWidget(top_cust_frame)

        root.addStretch()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ── Data Loading ────────────────────────────────────────────────────────

    # ── Public API ────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Async: collect all DB data in one background job, then apply to widgets."""
        POOL.submit("analytics_refresh", self._fetch_all_data, self._apply_all_data)

    # ── Background fetch (NO Qt widget access) ────────────────────────────────

    def _fetch_all_data(self) -> dict:
        """Run every DB query needed by the dashboard — called off the main thread."""
        from app.core.database import get_connection
        from datetime import date

        # Single summary call shared by KPIs, donut, category bars
        summary = _item_repo.get_summary()

        # Recent transactions
        txns = _txn_repo.get_transactions(limit=5)

        # Category unit counts
        cats = _cat_repo.get_all_active()
        cat_data: list[tuple[str, int]] = []
        for cat in cats:
            s = _item_repo.get_summary_for_category(cat.id)
            cat_data.append((cat.name_en, s.get("total_units", 0) or 0))

        # 30-day activity trend
        try:
            with get_connection() as conn:
                trend_rows = conn.execute("""
                    SELECT DATE(timestamp) AS day, COUNT(*) AS cnt
                    FROM inventory_transactions
                    WHERE timestamp >= DATE('now', '-30 days')
                    GROUP BY DATE(timestamp) ORDER BY day
                """).fetchall()
            trend = [(r["day"][-5:], r["cnt"]) for r in trend_rows]
        except Exception:
            trend = []

        # Low-stock items (sorted by urgency)
        try:
            all_items = _item_repo.get_all_items()
            low = [it for it in all_items if it.min_stock > 0 and it.stock <= it.min_stock]
            low.sort(key=lambda x: (x.stock > 0, x.stock / max(x.min_stock, 1)))
            low_data = [
                (it.display_name[:18] + "…" if len(it.display_name) > 20 else it.display_name,
                 it.stock,
                 "out" if it.stock == 0 else "warn" if it.stock < it.min_stock * 0.5 else "low")
                for it in low[:8]
            ]
        except Exception:
            low_data = []

        # Sales KPIs
        try:
            today   = date.today().isoformat()
            daily   = _sale_repo.daily_totals(today)
            cust_s  = _cust_svc.get_summary()
        except Exception:
            daily  = {"count": 0, "revenue": 0, "profit": 0}
            cust_s = {"total": 0, "active": 0, "with_purchases": 0}

        # Top customers by spend
        try:
            customers  = _cust_svc.get_all()
            with_spend = sorted([c for c in customers if c.total_spent > 0],
                                 key=lambda c: c.total_spent, reverse=True)
            top_custs  = [
                (c.name[:18] + "…" if len(c.name) > 20 else c.name, c.total_spent)
                for c in with_spend[:8]
            ]
        except Exception:
            top_custs = []

        return {
            "summary":   summary,
            "txns":      txns,
            "cat_data":  cat_data,
            "trend":     trend,
            "low_data":  low_data,
            "daily":     daily,
            "cust_s":    cust_s,
            "top_custs": top_custs,
        }

    # ── Main-thread apply (widget access only — no DB) ────────────────────────

    def _apply_all_data(self, data: dict) -> None:
        self._apply_kpis(data["summary"])
        self._apply_recent_activity(data["txns"])
        self._apply_health_donut(data["summary"])
        self._apply_category_bars(data["cat_data"], data["summary"])
        self._apply_activity_trend(data["trend"])
        self._apply_low_stock_bars(data["low_data"])
        self._apply_sales_kpis(data["daily"], data["cust_s"])
        self._apply_top_customers(data["top_custs"])

    def _apply_kpis(self, summary: dict) -> None:
        total = summary.get("total_products", 0) or 0
        units = summary.get("total_units", 0) or 0
        low   = summary.get("low_stock_count", 0) or 0
        out   = summary.get("out_of_stock_count", 0) or 0
        value = summary.get("inventory_value", 0) or 0
        cfg   = ShopConfig.get()
        val_str    = cfg.format_currency(value) if value else "0"
        health_pct = ((total - low - out) / total * 100) if total > 0 else 0
        self._kpi_total.set_data(t("analytics_kpi_total_items"), str(total),
                                 t("analytics_kpi_products_matrix"))
        self._kpi_units.set_data(t("analytics_kpi_total_units"), str(units),
                                 t("analytics_kpi_across_items", n=total))
        self._kpi_value.set_data(t("analytics_kpi_inventory_value"), val_str,
                                 t("analytics_kpi_at_sell_price"))
        self._kpi_health.set_data(t("analytics_kpi_stock_health"), f"{health_pct:.0f}%",
                                  t("analytics_kpi_items_ok", n=total - low - out))

    def _apply_recent_activity(self, txns: list) -> None:
        while self._ra_container.count():
            w = self._ra_container.takeAt(0).widget()
            if w: w.deleteLater()
        tk = THEME.tokens
        op_colors = {"IN": tk.green, "OUT": tk.red, "ADJUST": tk.blue, "CREATE": tk.purple}
        for txn in txns:
            row = QFrame()
            row.setStyleSheet(
                f"background:{tk.card}; border-bottom:1px solid {tk.border};"
                "border-radius:4px; padding:4px 8px;"
            )
            rl = QHBoxLayout(row)
            rl.setContentsMargins(8, 4, 8, 4); rl.setSpacing(8)
            op_fg  = op_colors.get(txn.operation, tk.t3)
            op_lbl = QLabel(txn.operation)
            op_lbl.setFixedWidth(50)
            op_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            op_lbl.setStyleSheet(
                f"color:{op_fg}; background:{_rgba(op_fg,'20')};"
                "border-radius:4px; font-weight:700; font-size:8pt; padding:2px 4px;"
            )
            rl.addWidget(op_lbl)
            name_parts = [txn.model_name or txn.brand, txn.part_type_name or txn.name]
            name = " · ".join(p for p in name_parts if p) or f"Item #{txn.item_id}"
            name_lbl = QLabel(name); name_lbl.setStyleSheet("font-size:11px;")
            rl.addWidget(name_lbl, 1)
            d  = txn.stock_after - txn.stock_before
            ds = f"+{d}" if d >= 0 else str(d)
            delta_lbl = QLabel(ds)
            delta_lbl.setStyleSheet(
                f"color:{tk.green if d >= 0 else tk.red}; font-weight:700; font-size:10px;"
            )
            rl.addWidget(delta_lbl)
            time_lbl = QLabel(txn.timestamp[5:16] if txn.timestamp else "")
            time_lbl.setStyleSheet(f"color:{tk.t4}; font-size:10px;")
            rl.addWidget(time_lbl)
            self._ra_container.addWidget(row)
        if not txns:
            empty = QLabel(t("analytics_no_activity"))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color:{tk.t4}; font-size:12px; padding:16px;")
            self._ra_container.addWidget(empty)

    def _apply_health_donut(self, summary: dict) -> None:
        total = summary.get("total_products", 0) or 0
        low   = summary.get("low_stock_count", 0) or 0
        out   = summary.get("out_of_stock_count", 0) or 0
        ok    = max(0, total - low - out)
        tk    = THEME.tokens
        self._donut.set_data([
            PieSlice(t("badge_ok"),  ok,  tk.green),
            PieSlice(t("badge_low"), low, tk.yellow),
            PieSlice(t("badge_out"), out, tk.red),
        ], t("analytics_total"), str(total))

    @staticmethod
    def _accent() -> str:
        tk = THEME.tokens
        return tk.green if tk.grad_top in ("#0A0A0A", "#FFFFFF") else tk.blue

    def _apply_category_bars(self, cat_data: list, summary: dict) -> None:
        tk  = THEME.tokens
        acc = self._accent()
        palette = [acc, tk.blue, tk.purple, tk.orange, tk.green, tk.yellow, tk.red]
        bars: list[BarItem] = []
        for i, (name, units) in enumerate(cat_data):
            bars.append(BarItem(name, units, palette[i % len(palette)]))
        total_units = summary.get("total_units", 0) or 0
        cat_units   = sum(b.value for b in bars)
        product_units = total_units - cat_units
        if product_units > 0:
            bars.insert(0, BarItem(t("analytics_products"), product_units, acc))
        self._bar.set_data(bars)

    def _apply_activity_trend(self, trend: list) -> None:
        if not trend:
            self._trend.set_data([]); return
        self._trend.set_data(
            [LinePoint(day, cnt) for day, cnt in trend],
            line_color=self._accent(),
        )

    def _apply_low_stock_bars(self, low_data: list) -> None:
        tk = THEME.tokens
        color_map = {"out": tk.red, "warn": tk.orange, "low": tk.yellow}
        bars = [BarItem(name, stock, color_map[level]) for name, stock, level in low_data]
        self._low_bar.set_data(bars)

    def _apply_sales_kpis(self, daily: dict, cust_s: dict) -> None:
        try:
            cfg = ShopConfig.get()
            avg = daily["revenue"] / daily["count"] if daily["count"] > 0 else 0
            self._kpi_sales_today.set_data("TODAY'S SALES", str(daily["count"]),
                                           f"Revenue: {cfg.format_currency(daily['revenue'])}")
            self._kpi_revenue.set_data("TODAY'S REVENUE", cfg.format_currency(daily["revenue"]),
                                       f"Profit: {cfg.format_currency(daily['profit'])}")
            self._kpi_customers.set_data("CUSTOMERS", str(cust_s["total"]),
                                         f"Active: {cust_s['active']}")
            self._kpi_avg_order.set_data("AVG ORDER", cfg.format_currency(avg),
                                         f"With purchases: {cust_s['with_purchases']}")
        except Exception:
            for kpi in (self._kpi_sales_today, self._kpi_revenue,
                        self._kpi_customers, self._kpi_avg_order):
                kpi.set_data(kpi._title_lbl.text(), "—", "")

    def _apply_top_customers(self, top_custs: list) -> None:
        tk  = THEME.tokens
        acc = self._accent()
        colors = [acc, tk.blue, tk.green, tk.purple, tk.orange, tk.yellow, tk.red, acc]
        bars = [BarItem(name, spend, colors[i % len(colors)])
                for i, (name, spend) in enumerate(top_custs)]
        self._top_cust_bar.set_data(bars)

    def retranslate(self) -> None:
        # Labels only — no DB.  Data refresh is deferred by main_window via POOL.
        self._title.setText(t("analytics_title"))
        self._donut_hdr.setText(t("analytics_stock_health"))
        self._bar_hdr.setText(t("analytics_by_category"))
        self._trend_hdr.setText(t("analytics_activity_trend"))
        self._low_hdr.setText(t("analytics_top_low_stock"))

    # Zoom is a table-only feature; analytics has no tables so no apply_zoom.
