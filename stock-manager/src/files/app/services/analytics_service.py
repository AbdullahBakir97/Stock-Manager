"""
app/services/analytics_service.py — Facade for the Analytics dashboard.

One class assembles every tile's data block. Called from a worker thread
via `POOL.submit`, its public methods MUST be safe to run off the main
thread (so no Qt widget access here).

Public methods return dict / list payloads tailored to their tile so the
page's `_apply_*` slots can render without further computation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.repositories.item_repo import ItemRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.sale_repo import SaleRepository
from app.repositories.invoice_repo import InvoiceRepository
from app.repositories.category_repo import CategoryRepository


@dataclass
class DateRange:
    """Inclusive date range + its previous equal-length comparison range."""
    current_from: str      # 'YYYY-MM-DD'
    current_to: str
    compare_from: str
    compare_to: str
    preset: str = "30d"


def range_for_preset(preset: str, custom_from: str = "",
                     custom_to: str = "") -> DateRange:
    """Resolve a preset key to a DateRange (current + previous window)."""
    today = datetime.now().date()
    if preset == "today":
        c_from = c_to = today
    elif preset == "7d":
        c_from = today - timedelta(days=6); c_to = today
    elif preset == "30d":
        c_from = today - timedelta(days=29); c_to = today
    elif preset == "90d":
        c_from = today - timedelta(days=89); c_to = today
    elif preset == "year":
        c_from = today.replace(month=1, day=1); c_to = today
    elif preset == "custom":
        try:
            c_from = datetime.strptime(custom_from, "%Y-%m-%d").date()
            c_to = datetime.strptime(custom_to, "%Y-%m-%d").date()
        except Exception:
            c_from = today - timedelta(days=29); c_to = today
        if c_from > c_to:
            c_from, c_to = c_to, c_from
    else:
        c_from = today - timedelta(days=29); c_to = today

    span = (c_to - c_from).days + 1
    p_to = c_from - timedelta(days=1)
    p_from = p_to - timedelta(days=span - 1)
    return DateRange(
        current_from=c_from.strftime("%Y-%m-%d"),
        current_to=c_to.strftime("%Y-%m-%d"),
        compare_from=p_from.strftime("%Y-%m-%d"),
        compare_to=p_to.strftime("%Y-%m-%d"),
        preset=preset,
    )


def _delta(cur: float, prev: float) -> tuple[float, str]:
    """Return (percent_change, direction) where direction is 'up', 'down', or 'flat'."""
    if prev == 0 and cur == 0:
        return 0.0, "flat"
    if prev == 0:
        return 100.0, "up"
    pct = (cur - prev) / abs(prev) * 100.0
    if abs(pct) < 0.01:
        return 0.0, "flat"
    return pct, ("up" if pct > 0 else "down")


def _fill_daily(rows: list[dict], date_from: str, date_to: str,
                value_key: str = "count") -> list[tuple[str, float]]:
    """Return a complete [(date, value), ...] list with missing days = 0."""
    by_date = {r.get("date"): r for r in rows}
    out: list[tuple[str, float]] = []
    d = datetime.strptime(date_from, "%Y-%m-%d").date()
    end = datetime.strptime(date_to, "%Y-%m-%d").date()
    while d <= end:
        key = d.strftime("%Y-%m-%d")
        r = by_date.get(key)
        out.append((key, float(r.get(value_key) or 0) if r else 0.0))
        d += timedelta(days=1)
    return out


class AnalyticsService:
    """Facade — one method per dashboard tile."""

    def __init__(self) -> None:
        self._items = ItemRepository()
        self._txns = TransactionRepository()
        self._sales = SaleRepository()
        self._invoices = InvoiceRepository()
        self._cats = CategoryRepository()

    # ── Executive KPI row ──────────────────────────────────────────────────

    def executive_kpis(self, r: DateRange) -> dict:
        """Four top-line KPIs each with {value, delta_pct, delta_dir,
        sparkline: list[float]}."""
        summary = self._items.get_summary()
        stock_value = float(summary.get("inventory_value") or 0)
        low_stock_count = int(summary.get("low_stock_count") or 0)

        # Revenue & sales count (current + previous range + per-day for spark)
        cur_days = self._sales.revenue_daily(r.current_from, r.current_to)
        prev_days = self._sales.revenue_daily(r.compare_from, r.compare_to)
        rev_cur = sum(float(d.get("revenue") or 0) for d in cur_days)
        rev_prev = sum(float(d.get("revenue") or 0) for d in prev_days)
        rev_pct, rev_dir = _delta(rev_cur, rev_prev)
        rev_spark = [v for _, v in _fill_daily(cur_days, r.current_from,
                                                r.current_to, "revenue")]

        # Transactions — count based
        cur_txns = self._txns.get_daily_aggregates(r.current_from, r.current_to)
        prev_txns = self._txns.get_daily_aggregates(r.compare_from, r.compare_to)
        tx_cur = sum(int(d.get("count") or 0) for d in cur_txns)
        tx_prev = sum(int(d.get("count") or 0) for d in prev_txns)
        tx_pct, tx_dir = _delta(tx_cur, tx_prev)
        tx_spark = [v for _, v in _fill_daily(cur_txns, r.current_from,
                                               r.current_to, "count")]

        # Stock value doesn't have a past snapshot in this schema — fake by
        # summing transactions net change over the period as a proxy.
        net_change = sum(int(d.get("in_qty") or 0) - int(d.get("out_qty") or 0)
                         for d in cur_txns)
        # Sparkline: running daily stock change (delta)
        sv_spark_pairs = _fill_daily(cur_txns, r.current_from, r.current_to,
                                      "in_qty")
        sv_out_pairs = _fill_daily(cur_txns, r.current_from, r.current_to,
                                    "out_qty")
        sv_spark = [iv[1] - ov[1] for iv, ov in zip(sv_spark_pairs,
                                                      sv_out_pairs)]

        # Low-stock delta — compare current count to previous count
        # (approximation: we use transaction net movement as a proxy)
        low_pct, low_dir = _delta(low_stock_count,
                                   max(0, low_stock_count - net_change))

        return {
            "stock_value": {
                "value": stock_value,
                "delta_pct": 0.0, "delta_dir": "flat",
                "sparkline": sv_spark,
            },
            "revenue": {
                "value": rev_cur,
                "delta_pct": rev_pct, "delta_dir": rev_dir,
                "sparkline": rev_spark,
            },
            "transactions": {
                "value": tx_cur,
                "delta_pct": tx_pct, "delta_dir": tx_dir,
                "sparkline": tx_spark,
            },
            "low_stock": {
                "value": low_stock_count,
                "delta_pct": low_pct, "delta_dir": low_dir,
                "sparkline": sv_spark,
            },
        }

    # ── Inventory health block ─────────────────────────────────────────────

    def inventory_block(self) -> dict:
        """Stock health donut + by-brand bars + units-by-category + pivot."""
        summary = self._items.get_summary()
        total = int(summary.get("total_products") or 0)
        low = int(summary.get("low_stock_count") or 0)
        out = int(summary.get("out_of_stock_count") or 0)
        healthy = max(0, total - low)
        # Donut slices
        donut = []
        if healthy:
            donut.append(("Healthy", healthy, "#10B981"))
        if (low - out) > 0:
            donut.append(("Low", low - out, "#F59E0B"))
        if out:
            donut.append(("Out", out, "#EF4444"))

        by_brand = self._items.get_value_by_brand()
        by_pt = self._items.get_value_by_part_type()
        pivot = self._items.get_value_pivot()

        return {
            "donut": donut,
            "total_products": total,
            "by_brand": by_brand,
            "by_part_type": by_pt,
            "pivot": pivot,
        }

    # ── Sales block ────────────────────────────────────────────────────────

    def sales_block(self, r: DateRange) -> dict:
        cur = self._sales.revenue_daily(r.current_from, r.current_to)
        prev = self._sales.revenue_daily(r.compare_from, r.compare_to)
        cur_pairs = _fill_daily(cur, r.current_from, r.current_to, "revenue")
        prev_pairs = _fill_daily(prev, r.compare_from, r.compare_to, "revenue")

        rev_cur = sum(v for _, v in cur_pairs)
        rev_prev = sum(v for _, v in prev_pairs)
        sales_count_cur = sum(int(d.get("count") or 0) for d in cur)
        sales_count_prev = sum(int(d.get("count") or 0) for d in prev)

        rev_pct, rev_dir = _delta(rev_cur, rev_prev)
        count_pct, count_dir = _delta(sales_count_cur, sales_count_prev)

        avg_basket = (rev_cur / sales_count_cur) if sales_count_cur else 0.0

        # Top sellers + top customers
        top_sellers = self._sales.top_items(limit=10,
                                            date_from=r.current_from,
                                            date_to=r.current_to)
        top_customers = self._sales.top_customers(date_from=r.current_from,
                                                    date_to=r.current_to,
                                                    limit=10)

        # Best day
        best_day = max(cur_pairs, key=lambda kv: kv[1], default=("—", 0))

        return {
            "cur_series": cur_pairs,
            "prev_series": prev_pairs,
            "revenue": rev_cur, "revenue_delta": (rev_pct, rev_dir),
            "sales_count": sales_count_cur,
            "sales_count_delta": (count_pct, count_dir),
            "avg_basket": avg_basket,
            "best_day": best_day,
            "top_sellers": top_sellers,
            "top_customers": top_customers,
        }

    # ── Stock-movement block ───────────────────────────────────────────────

    def movement_block(self, r: DateRange) -> dict:
        daily = self._txns.get_daily_aggregates(r.current_from, r.current_to)
        hourly = self._txns.get_hourly_aggregates(r.current_from, r.current_to)

        in_series = _fill_daily(daily, r.current_from, r.current_to, "in_qty")
        out_series = _fill_daily(daily, r.current_from, r.current_to, "out_qty")

        total_in = sum(v for _, v in in_series)
        total_out = sum(v for _, v in out_series)
        net = total_in - total_out

        # Recent activity (latest 10 transactions)
        recent = self._txns.get_transactions(limit=10)

        return {
            "in_series": in_series,
            "out_series": out_series,
            "hourly": hourly,
            "total_in": total_in,
            "total_out": total_out,
            "net": net,
            "recent": recent,
        }

    # ── Scan-invoices block ────────────────────────────────────────────────

    def invoices_block(self, r: DateRange) -> dict:
        totals = self._invoices.get_totals(r.current_from, r.current_to)
        prev_totals = self._invoices.get_totals(r.compare_from, r.compare_to)

        total_pct, total_dir = _delta(float(totals.get("total") or 0),
                                       float(prev_totals.get("total") or 0))

        daily = self._invoices.get_daily(r.current_from, r.current_to)
        in_series: list[tuple[str, float]] = []
        out_series: list[tuple[str, float]] = []
        by_date = {d["date"]: d for d in daily}
        d = datetime.strptime(r.current_from, "%Y-%m-%d").date()
        end = datetime.strptime(r.current_to, "%Y-%m-%d").date()
        while d <= end:
            key = d.strftime("%Y-%m-%d")
            row = by_date.get(key)
            in_series.append((key, float(row.get("in_total") or 0) if row else 0.0))
            out_series.append((key, float(row.get("out_total") or 0) if row else 0.0))
            d += timedelta(days=1)

        top_customers = self._invoices.get_top_customers(
            r.current_from, r.current_to, limit=10,
        )
        avg = (float(totals.get("total") or 0) / int(totals.get("count") or 1)
               if totals.get("count") else 0.0)

        return {
            "totals": totals,
            "total_delta": (total_pct, total_dir),
            "avg_invoice": avg,
            "in_series": in_series,
            "out_series": out_series,
            "top_customers": top_customers,
        }
