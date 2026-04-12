"""
web_server.py — Full web interface for Stock Manager Pro.

Covers every major feature of the desktop app:
  Inventory · Sales · Purchase Orders · Suppliers · Customers
  Returns · Transactions · Barcode Generator · Reports · Admin

Run standalone:  python web_server.py
Access from tablet: http://<PC-IP>:5000
"""
from __future__ import annotations

import os
import sys
import sqlite3
import threading
from datetime import datetime, date, timedelta

# ── Make sure app packages are importable ─────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# ── Mock PyQt6 so app modules load without a Qt installation ──────────────────
import types as _types

def _mock_pyqt6():
    """Provide stub PyQt6 modules so i18n.py imports without crashing."""
    _Qt = _types.SimpleNamespace(
        LayoutDirection=_types.SimpleNamespace(LeftToRight=0, RightToLeft=1),
        AlignmentFlag=_types.SimpleNamespace(AlignLeft=1, AlignRight=2, AlignCenter=4),
    )
    _QtCore = _types.ModuleType("PyQt6.QtCore")
    _QtCore.Qt = _Qt
    _QtWidgets = _types.ModuleType("PyQt6.QtWidgets")
    _QtWidgets.QApplication = _types.SimpleNamespace(
        setLayoutDirection=lambda *a: None,
        instance=lambda: None,
    )
    _PyQt6 = _types.ModuleType("PyQt6")
    _PyQt6.QtCore    = _QtCore
    _PyQt6.QtWidgets = _QtWidgets
    sys.modules.setdefault("PyQt6",           _PyQt6)
    sys.modules.setdefault("PyQt6.QtCore",    _QtCore)
    sys.modules.setdefault("PyQt6.QtWidgets", _QtWidgets)

_mock_pyqt6()

from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, flash, session,
)
from app.core.database import DB_PATH, get_connection
from app.repositories.item_repo import ItemRepository
from app.repositories.category_repo import CategoryRepository
from app.repositories.supplier_repo import SupplierRepository
from app.repositories.customer_repo import CustomerRepository
from app.repositories.sale_repo import SaleRepository
from app.repositories.purchase_order_repo import PurchaseOrderRepository
from app.repositories.return_repo import ReturnRepository
from app.repositories.transaction_repo import TransactionRepository
from app.services.stock_service import StockService
from app.services.sale_service import SaleService
from app.services.supplier_service import SupplierService
from app.services.customer_service import CustomerService
from app.services.purchase_order_service import PurchaseOrderService
from app.services.return_service import ReturnService
from app.services.alert_service import AlertService
from app.repositories.price_list_repo import PriceListRepository
from app.services.price_list_service import PriceListService

app = Flask(__name__, template_folder="web_templates")
app.secret_key = "stockpro-web-2024"

# ── Singletons ────────────────────────────────────────────────────────────────
_item_repo   = ItemRepository()
_cat_repo    = CategoryRepository()
_sup_repo    = SupplierRepository()
_cust_repo   = CustomerRepository()
_sale_repo   = SaleRepository()
_po_repo     = PurchaseOrderRepository()
_ret_repo    = ReturnRepository()
_txn_repo    = TransactionRepository()

_stock_svc   = StockService()
_sale_svc    = SaleService()
_sup_svc     = SupplierService()
_cust_svc    = CustomerService()
_po_svc      = PurchaseOrderService()
_ret_svc     = ReturnService()
_alert_svc   = AlertService()
_pl_repo     = PriceListRepository()
_pl_svc      = PriceListService()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _dashboard_stats() -> dict:
    """Aggregate numbers for dashboard."""
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM inventory_items WHERE is_active=1"
        ).fetchone()[0]
        low = conn.execute(
            "SELECT COUNT(*) FROM inventory_items "
            "WHERE is_active=1 AND min_stock>0 AND stock<=min_stock AND stock>0"
        ).fetchone()[0]
        out = conn.execute(
            "SELECT COUNT(*) FROM inventory_items WHERE is_active=1 AND stock=0"
        ).fetchone()[0]
        today = date.today().isoformat()
        sales_today = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(total_amount-discount),0) FROM sales "
            "WHERE date(timestamp)=?", (today,)
        ).fetchone()
        pending_pos = conn.execute(
            "SELECT COUNT(*) FROM purchase_orders WHERE status IN ('DRAFT','SENT')"
        ).fetchone()[0]
        recent = conn.execute("""
            SELECT t.id, t.operation, t.quantity, t.timestamp, t.note,
                   t.stock_after, i.brand, i.name, i.color, i.id AS item_id
            FROM inventory_transactions t
            JOIN inventory_items i ON i.id = t.item_id
            ORDER BY t.timestamp DESC LIMIT 8
        """).fetchall()
        recent_sales = conn.execute("""
            SELECT s.id, s.timestamp,
                   COALESCE(s.total_amount - s.discount, s.total_amount, 0) AS net_total,
                   c.name AS customer_name
            FROM sales s
            LEFT JOIN customers c ON c.id = s.customer_id
            ORDER BY s.timestamp DESC LIMIT 5
        """).fetchall()
    return {
        "total": total, "low": low, "out": out,
        "sales_today": sales_today[0],
        "revenue_today": round(sales_today[1], 2),
        "pending_pos": pending_pos,
        "recent": [dict(r) for r in recent],
        "recent_sales": [dict(r) for r in recent_sales],
    }


def _fmt_price(v) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.2f}"
    except (TypeError, ValueError):
        return str(v)


app.jinja_env.globals["fmt_price"] = _fmt_price


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def dashboard():
    alerts = _item_repo.get_all_items(filter_low_stock=True)
    return render_template("dashboard.html", stats=_dashboard_stats(), alerts=alerts)


# ══════════════════════════════════════════════════════════════════════════════
# INVENTORY
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/inventory")
def inventory():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "")   # ok / low / out / ""
    cat    = request.args.get("cat", "")       # category key or "products" or ""
    sort   = request.args.get("sort", "")

    # Build filter flags for repo
    low_only = (status == "low")
    items = _item_repo.get_all_items(search=search, filter_low_stock=low_only)

    # Apply status filter in Python (repo only has low-stock flag)
    if status == "ok":
        items = [i for i in items if i.stock > i.min_stock or i.min_stock == 0]
    elif status == "out":
        items = [i for i in items if i.stock == 0]

    # Apply category filter
    if cat == "products":
        items = [i for i in items if i.is_product]
    elif cat:
        items = [i for i in items if i.part_type_key == cat or
                 (hasattr(i, 'part_type_name') and
                  any(pt.key == cat for c in _cat_repo.get_all_active()
                      for pt in c.part_types if pt.key == cat))]

    # Sort
    if sort == "name_asc":
        items.sort(key=lambda i: i.display_name.lower())
    elif sort == "name_desc":
        items.sort(key=lambda i: i.display_name.lower(), reverse=True)
    elif sort == "stock_asc":
        items.sort(key=lambda i: i.stock)
    elif sort == "stock_desc":
        items.sort(key=lambda i: i.stock, reverse=True)
    elif sort == "price_desc":
        items.sort(key=lambda i: i.sell_price or 0, reverse=True)
    elif sort == "updated":
        items.sort(key=lambda i: i.updated_at or "", reverse=True)

    categories = _cat_repo.get_all_active()
    return render_template("inventory.html", items=items,
                           search=search, status=status,
                           cat=cat, sort=sort,
                           categories=categories,
                           count=len(items))


@app.route("/inventory/add", methods=["GET", "POST"])
def item_add():
    categories = _cat_repo.get_all_active()
    suppliers  = _sup_repo.get_all()
    brands     = _item_repo.get_distinct_brands()
    if request.method == "POST":
        try:
            item_id = _item_repo.add_product(
                brand=request.form.get("brand", "").strip(),
                name=request.form.get("name", "").strip(),
                color=request.form.get("color", "").strip(),
                stock=int(request.form.get("stock", 0) or 0),
                min_stock=int(request.form.get("min_stock", 0) or 0),
                sell_price=float(request.form.get("sell_price", 0) or 0) or None,
                barcode=request.form.get("barcode", "").strip() or None,
            )
            flash(f"Item added successfully (ID: {item_id})", "ok")
            return redirect(url_for("item_detail", item_id=item_id))
        except Exception as e:
            flash(str(e), "err")
    return render_template("item_form.html", item=None,
                           categories=categories, suppliers=suppliers,
                           brands=brands, mode="add")


@app.route("/item/<int:item_id>")
def item_detail(item_id: int):
    item = _item_repo.get_by_id(item_id)
    if not item:
        return redirect(url_for("inventory"))
    with get_connection() as conn:
        txns = conn.execute("""
            SELECT operation, quantity, stock_after, note, timestamp
            FROM inventory_transactions
            WHERE item_id=?
            ORDER BY timestamp DESC LIMIT 20
        """, (item_id,)).fetchall()
    error = request.args.get("error", "")
    ok    = request.args.get("ok", "")
    return render_template("item.html", item=item,
                           txns=[dict(t) for t in txns],
                           error=error, ok=ok)


@app.route("/item/<int:item_id>/edit", methods=["GET", "POST"])
def item_edit(item_id: int):
    item = _item_repo.get_by_id(item_id)
    if not item:
        return redirect(url_for("inventory"))
    categories = _cat_repo.get_all_active()
    suppliers  = _sup_repo.get_all()
    brands     = _item_repo.get_distinct_brands()
    if request.method == "POST":
        try:
            _item_repo.update_product(
                item_id=item_id,
                brand=request.form.get("brand", "").strip(),
                name=request.form.get("name", "").strip(),
                color=request.form.get("color", "").strip(),
                min_stock=int(request.form.get("min_stock", 0) or 0),
                sell_price=float(request.form.get("sell_price", 0) or 0) or None,
                sku=request.form.get("sku", "").strip() or None,
                barcode=request.form.get("barcode", "").strip() or None,
            )
            flash("Item updated successfully", "ok")
            return redirect(url_for("item_detail", item_id=item_id))
        except Exception as e:
            flash(str(e), "err")
    return render_template("item_form.html", item=item,
                           categories=categories, suppliers=suppliers,
                           brands=brands, mode="edit")


@app.route("/item/<int:item_id>/delete", methods=["POST"])
def item_delete(item_id: int):
    try:
        _item_repo.delete(item_id)
        flash("Item deleted", "ok")
    except Exception as e:
        flash(str(e), "err")
    return redirect(url_for("inventory"))


@app.route("/item/<int:item_id>/stock", methods=["POST"])
def stock_op(item_id: int):
    op    = request.form.get("op", "in")
    note  = request.form.get("note", "").strip()
    error = None
    try:
        qty = int(request.form.get("qty", 0))
        if op == "in":
            _stock_svc.stock_in(item_id, qty, note)
        elif op == "out":
            _stock_svc.stock_out(item_id, qty, note)
        elif op == "adjust":
            # Set stock directly to qty value
            with get_connection() as conn:
                conn.execute(
                    "UPDATE inventory_items SET stock=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (qty, item_id)
                )
                conn.execute(
                    "INSERT INTO inventory_transactions (item_id, operation, quantity, note, timestamp) "
                    "VALUES (?,?,?,?,CURRENT_TIMESTAMP)",
                    (item_id, "ADJUST", qty, note or "Manual adjustment")
                )
    except (ValueError, TypeError) as e:
        error = str(e)
    return redirect(url_for("item_detail", item_id=item_id,
                            error=error or "", ok="1" if not error else ""))


@app.route("/alerts")
def alerts():
    low = _item_repo.get_all_items(filter_low_stock=True)
    out = [i for i in _item_repo.get_all_items() if i.stock == 0 and i.is_active]
    return render_template("alerts.html", low=low, out=out)


# ══════════════════════════════════════════════════════════════════════════════
# SALES / POS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/sales")
def sales():
    date_from = request.args.get("from", "")
    date_to   = request.args.get("to", "")
    search    = request.args.get("q", "").strip()
    limit     = int(request.args.get("limit", 50))
    sales_list = _sale_repo.get_all(limit=limit, date_from=date_from, date_to=date_to)
    # Optional client-side search filter by customer name or id
    if search:
        q_lower = search.lower()
        sales_list = [s for s in sales_list if
                      q_lower in str(s.id) or
                      (s.customer_name and q_lower in s.customer_name.lower())]
    # Summary (over filtered list)
    total_rev  = sum(s.net_total for s in sales_list)
    total_cnt  = len(sales_list)
    return render_template("sales.html", sales=sales_list,
                           total_rev=total_rev, total_cnt=total_cnt,
                           date_from=date_from, date_to=date_to, search=search)


@app.route("/sales/<int:sale_id>")
def sale_detail(sale_id: int):
    sale = _sale_svc.get_sale(sale_id)
    if not sale:
        return redirect(url_for("sales"))
    return render_template("sale_detail.html", sale=sale)


@app.route("/sales/<int:sale_id>/delete", methods=["POST"])
def sale_delete(sale_id: int):
    try:
        _sale_svc.delete_sale(sale_id)
        flash("Sale deleted", "ok")
    except Exception as e:
        flash(str(e), "err")
    return redirect(url_for("sales"))


@app.route("/sales/new", methods=["GET", "POST"])
def sale_new():
    customers = _cust_repo.get_all(active_only=True)
    if request.method == "POST":
        try:
            import json
            raw_items = request.form.get("items_json", "[]")
            items = json.loads(raw_items)
            if not items:
                raise ValueError("Add at least one item to the sale")
            sale_id = _sale_svc.create_sale(
                customer_name=request.form.get("customer_name", "").strip(),
                discount=float(request.form.get("discount", 0) or 0),
                note=request.form.get("note", "").strip(),
                items=items,
                customer_id=int(request.form.get("customer_id") or 0) or None,
            )
            flash(f"Sale #{sale_id} created", "ok")
            return redirect(url_for("sale_detail", sale_id=sale_id))
        except Exception as e:
            flash(str(e), "err")
    return render_template("sale_new.html", customers=customers)


# ── API for POS item search ────────────────────────────────────────────────

@app.route("/api/items/search")
def api_items_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    items = _item_repo.search(q, limit=15)
    return jsonify([{
        "id": i.id,
        "name": i.display_name,
        "barcode": i.barcode or "",
        "stock": i.stock,
        "sell_price": i.sell_price or 0,
    } for i in items if i.stock > 0])


# ══════════════════════════════════════════════════════════════════════════════
# PURCHASE ORDERS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/purchase-orders")
def purchase_orders():
    status = request.args.get("status", "")
    search = request.args.get("q", "").strip()
    pos = _po_repo.get_all(status=status, search=search)
    summary = _po_repo.get_summary()
    return render_template("purchase_orders.html", pos=pos,
                           summary=summary, status=status, search=search)


@app.route("/purchase-orders/<int:po_id>")
def po_detail(po_id: int):
    po = _po_repo.get_by_id(po_id)
    if not po:
        return redirect(url_for("purchase_orders"))
    suppliers = _sup_repo.get_all()
    return render_template("po_detail.html", po=po, suppliers=suppliers)


@app.route("/purchase-orders/new", methods=["GET", "POST"])
def po_new():
    suppliers = _sup_repo.get_all()
    items = _item_repo.get_all_items()
    if request.method == "POST":
        try:
            import json
            lines = json.loads(request.form.get("lines_json", "[]"))
            supplier_id = int(request.form.get("supplier_id") or 0) or None
            po_id = _po_svc.create_order(
                supplier_id=supplier_id,
                notes=request.form.get("notes", "").strip(),
                lines=[{
                    "item_id": l["item_id"],
                    "quantity": int(l["quantity"]),
                    "cost_price": float(l["cost_price"]),
                } for l in lines],
            )
            flash(f"Purchase Order created", "ok")
            return redirect(url_for("po_detail", po_id=po_id))
        except Exception as e:
            flash(str(e), "err")
    return render_template("po_new.html", suppliers=suppliers, items=items)


@app.route("/purchase-orders/<int:po_id>/status", methods=["POST"])
def po_update_status(po_id: int):
    new_status = request.form.get("status", "")
    try:
        if new_status == "SENT":
            _po_svc.send_order(po_id)
            flash("Order marked as sent", "ok")
        elif new_status == "RECEIVED":
            _po_svc.receive_order(po_id)
            flash("Order received — stock updated", "ok")
        elif new_status == "CLOSED":
            _po_svc.close_order(po_id)
            flash("Order closed", "ok")
        elif new_status == "CANCELLED":
            _po_svc.cancel_order(po_id)
            flash("Order cancelled", "ok")
        else:
            flash(f"Unknown status: {new_status}", "err")
    except Exception as e:
        flash(str(e), "err")
    return redirect(url_for("po_detail", po_id=po_id))


@app.route("/purchase-orders/<int:po_id>/delete", methods=["POST"])
def po_delete(po_id: int):
    try:
        _po_svc.cancel_order(po_id)
        flash("Purchase order cancelled", "ok")
    except Exception as e:
        flash(str(e), "err")
    return redirect(url_for("purchase_orders"))


# ══════════════════════════════════════════════════════════════════════════════
# SUPPLIERS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/suppliers")
def suppliers():
    search = request.args.get("q", "").strip()
    sups = _sup_repo.get_all(search=search, active_only=False)
    return render_template("suppliers.html", suppliers=sups, search=search)


@app.route("/suppliers/<int:supplier_id>")
def supplier_detail(supplier_id: int):
    sup = _sup_repo.get_by_id(supplier_id)
    if not sup:
        return redirect(url_for("suppliers"))
    return render_template("supplier_detail.html", supplier=sup)


@app.route("/suppliers/new", methods=["GET", "POST"])
def supplier_new():
    if request.method == "POST":
        try:
            sid = _sup_repo.add(
                name=request.form.get("name", "").strip(),
                contact_name=request.form.get("contact_name", "").strip(),
                phone=request.form.get("phone", "").strip(),
                email=request.form.get("email", "").strip(),
                address=request.form.get("address", "").strip(),
                notes=request.form.get("notes", "").strip(),
            )
            flash("Supplier added", "ok")
            return redirect(url_for("supplier_detail", supplier_id=sid))
        except Exception as e:
            flash(str(e), "err")
    return render_template("supplier_form.html", supplier=None, mode="add")


@app.route("/suppliers/<int:supplier_id>/edit", methods=["GET", "POST"])
def supplier_edit(supplier_id: int):
    sup = _sup_repo.get_by_id(supplier_id)
    if not sup:
        return redirect(url_for("suppliers"))
    if request.method == "POST":
        try:
            _sup_repo.update(
                supplier_id=supplier_id,
                name=request.form.get("name", "").strip(),
                contact_name=request.form.get("contact_name", "").strip(),
                phone=request.form.get("phone", "").strip(),
                email=request.form.get("email", "").strip(),
                address=request.form.get("address", "").strip(),
                notes=request.form.get("notes", "").strip(),
            )
            flash("Supplier updated", "ok")
            return redirect(url_for("supplier_detail", supplier_id=supplier_id))
        except Exception as e:
            flash(str(e), "err")
    return render_template("supplier_form.html", supplier=sup, mode="edit")


# ══════════════════════════════════════════════════════════════════════════════
# CUSTOMERS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/customers")
def customers():
    search = request.args.get("q", "").strip()
    custs = _cust_repo.get_all()
    if search:
        sl = search.lower()
        custs = [c for c in custs
                 if sl in c.name.lower()
                 or sl in c.phone.lower()
                 or sl in c.email.lower()]
    return render_template("customers.html", customers=custs, search=search)


@app.route("/customers/<int:customer_id>")
def customer_detail(customer_id: int):
    cust = _cust_repo.get_by_id(customer_id)
    if not cust:
        return redirect(url_for("customers"))
    sales = _sale_repo.get_by_customer(customer_id, limit=20)
    return render_template("customer_detail.html", customer=cust, sales=sales)


@app.route("/customers/new", methods=["GET", "POST"])
def customer_new():
    if request.method == "POST":
        try:
            cid = _cust_svc.add_customer(
                name=request.form.get("name", "").strip(),
                phone=request.form.get("phone", "").strip(),
                email=request.form.get("email", "").strip(),
                address=request.form.get("address", "").strip(),
                notes=request.form.get("notes", "").strip(),
            )
            flash("Customer added", "ok")
            return redirect(url_for("customer_detail", customer_id=cid))
        except Exception as e:
            flash(str(e), "err")
    return render_template("customer_form.html", customer=None, mode="add")


@app.route("/customers/<int:customer_id>/edit", methods=["GET", "POST"])
def customer_edit(customer_id: int):
    cust = _cust_repo.get_by_id(customer_id)
    if not cust:
        return redirect(url_for("customers"))
    if request.method == "POST":
        try:
            _cust_svc.update_customer(
                customer_id=customer_id,
                name=request.form.get("name", "").strip(),
                phone=request.form.get("phone", "").strip(),
                email=request.form.get("email", "").strip(),
                address=request.form.get("address", "").strip(),
                notes=request.form.get("notes", "").strip(),
            )
            flash("Customer updated", "ok")
            return redirect(url_for("customer_detail", customer_id=customer_id))
        except Exception as e:
            flash(str(e), "err")
    return render_template("customer_form.html", customer=cust, mode="edit")


# ══════════════════════════════════════════════════════════════════════════════
# RETURNS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/returns")
def returns():
    ret_list = _ret_repo.get_all(limit=200)
    summary  = _ret_repo.get_summary()
    return render_template("returns.html", returns=ret_list, summary=summary)


@app.route("/returns/new", methods=["GET", "POST"])
def return_new():
    items = _item_repo.get_all_items()
    if request.method == "POST":
        try:
            ret_id = _ret_svc.process_return(
                item_id=int(request.form.get("item_id", 0)),
                quantity=int(request.form.get("quantity", 1) or 1),
                reason=request.form.get("reason", "").strip(),
                action=request.form.get("action", "RESTOCK"),
                refund_amount=float(request.form.get("refund_amount", 0) or 0),
                sale_id=int(request.form.get("sale_id") or 0) or None,
            )
            flash("Return processed successfully", "ok")
            return redirect(url_for("returns"))
        except Exception as e:
            flash(str(e), "err")
    return render_template("return_form.html", items=items)


# ══════════════════════════════════════════════════════════════════════════════
# TRANSACTIONS (AUDIT LOG)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/transactions")
def transactions():
    search    = request.args.get("q", "").strip()
    op_filter = request.args.get("op", "")
    limit     = int(request.args.get("limit", 100))
    date_from = request.args.get("from", "")
    date_to   = request.args.get("to", "")
    with get_connection() as conn:
        sql = """
            SELECT t.id, t.operation, t.quantity, t.stock_before,
                   t.stock_after, t.note, t.timestamp,
                   i.brand, i.name, i.color, i.id AS item_id
            FROM inventory_transactions t
            JOIN inventory_items i ON i.id = t.item_id
            WHERE 1=1
        """
        params: list = []
        if op_filter:
            sql += " AND t.operation = ?"
            params.append(op_filter.upper())
        if search:
            sql += " AND (i.brand LIKE ? OR i.name LIKE ? OR i.color LIKE ? OR t.note LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s, s])
        if date_from:
            sql += " AND DATE(t.timestamp) >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND DATE(t.timestamp) <= ?"
            params.append(date_to)
        sql += f" ORDER BY t.timestamp DESC LIMIT {limit}"
        rows = conn.execute(sql, params).fetchall()
    txns = [dict(r) for r in rows]
    return render_template("transactions.html", txns=txns,
                           search=search, op_filter=op_filter, limit=limit,
                           date_from=date_from, date_to=date_to)


# ══════════════════════════════════════════════════════════════════════════════
# BARCODE SCANNER & GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/scan")
def scan():
    return render_template("scan.html")


@app.route("/barcodes")
def barcodes():
    """Barcode generation — list items and print barcodes."""
    search = request.args.get("q", "").strip()
    items  = _item_repo.get_all_items(search=search)
    return render_template("barcodes.html", items=items, search=search)


@app.route("/api/barcode/<barcode>")
def api_barcode(barcode: str):
    item = _item_repo.get_by_barcode(barcode)
    if item:
        return jsonify({"found": True, "id": item.id,
                        "name": item.display_name,
                        "stock": item.stock,
                        "sell_price": item.sell_price})
    return jsonify({"found": False})


# ══════════════════════════════════════════════════════════════════════════════
# REPORTS / ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/reports")
def reports():
    # Date range — default last 30 days
    date_to   = request.args.get("to", date.today().isoformat())
    date_from = request.args.get("from",
                                 (date.today() - timedelta(days=30)).isoformat())
    with get_connection() as conn:
        # Revenue by day
        rev_rows = conn.execute("""
            SELECT date(timestamp) AS day,
                   COUNT(*) AS sales_count,
                   ROUND(SUM(total_amount - discount), 2) AS revenue
            FROM sales
            WHERE date(timestamp) BETWEEN ? AND ?
            GROUP BY day ORDER BY day
        """, (date_from, date_to)).fetchall()

        # Top selling items
        top_items = conn.execute("""
            SELECT i.brand, i.name, i.color,
                   SUM(si.quantity) AS units_sold,
                   ROUND(SUM(si.line_total), 2) AS revenue
            FROM sale_items si
            JOIN inventory_items i ON i.id = si.item_id
            JOIN sales s ON s.id = si.sale_id
            WHERE date(s.timestamp) BETWEEN ? AND ?
            GROUP BY si.item_id
            ORDER BY revenue DESC LIMIT 10
        """, (date_from, date_to)).fetchall()

        # Stock movement summary
        stock_ops = conn.execute("""
            SELECT operation,
                   COUNT(*) AS op_count,
                   SUM(quantity) AS total_qty
            FROM inventory_transactions
            WHERE date(timestamp) BETWEEN ? AND ?
            GROUP BY operation
        """, (date_from, date_to)).fetchall()

        # Category stock summary
        cat_summary = conn.execute("""
            SELECT c.name_en AS category,
                   COUNT(DISTINCT ii.id) AS item_count,
                   SUM(ii.stock) AS total_stock,
                   SUM(CASE WHEN ii.stock=0 THEN 1 ELSE 0 END) AS out_count
            FROM categories c
            JOIN part_types pt ON pt.category_id = c.id
            JOIN inventory_items ii ON ii.part_type_id = pt.id
            WHERE ii.is_active=1
            GROUP BY c.id ORDER BY total_stock DESC
        """).fetchall()

        total_revenue = sum(r["revenue"] or 0 for r in rev_rows)
        total_orders  = sum(r["sales_count"] for r in rev_rows)

    return render_template("reports.html",
                           date_from=date_from, date_to=date_to,
                           rev_rows=[dict(r) for r in rev_rows],
                           top_items=[dict(r) for r in top_items],
                           stock_ops=[dict(r) for r in stock_ops],
                           cat_summary=[dict(r) for r in cat_summary],
                           total_revenue=round(total_revenue, 2),
                           total_orders=total_orders)


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN SETTINGS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/admin")
def admin():
    categories = _cat_repo.get_all()
    with get_connection() as conn:
        config = dict(conn.execute("SELECT key, value FROM app_config").fetchall())
    return render_template("admin.html", categories=categories, config=config)


@app.route("/admin/category/add", methods=["POST"])
def admin_category_add():
    try:
        _cat_repo.add_category(
            key=request.form.get("key", "").strip(),
            name_en=request.form.get("name_en", "").strip(),
            name_de=request.form.get("name_de", "").strip(),
            name_ar=request.form.get("name_ar", "").strip(),
        )
        flash("Category added", "ok")
    except Exception as e:
        flash(str(e), "err")
    return redirect(url_for("admin") + "#categories")


@app.route("/admin/category/<int:cat_id>/toggle", methods=["POST"])
def admin_category_toggle(cat_id: int):
    cat = _cat_repo.get_by_id(cat_id)
    if cat:
        _cat_repo.set_active(cat_id, not cat.is_active)
    return redirect(url_for("admin") + "#categories")


@app.route("/admin/parttype/add", methods=["POST"])
def admin_parttype_add():
    try:
        cat_id = int(request.form.get("category_id", 0))
        _cat_repo.add_part_type(
            category_id=cat_id,
            key=request.form.get("key", "").strip(),
            name=request.form.get("name", "").strip(),
            accent_color=request.form.get("accent_color", "#4A9EFF").strip(),
        )
        flash("Part type added", "ok")
    except Exception as e:
        flash(str(e), "err")
    return redirect(url_for("admin") + "#categories")


@app.route("/admin/settings/save", methods=["POST"])
def admin_settings_save():
    try:
        keys = ["shop_name", "shop_phone", "shop_address", "currency"]
        with get_connection() as conn:
            for k in keys:
                v = request.form.get(k, "").strip()
                if v:
                    conn.execute(
                        "INSERT OR REPLACE INTO app_config (key, value) VALUES (?,?)",
                        (k, v),
                    )
        flash("Settings saved", "ok")
    except Exception as e:
        flash(str(e), "err")
    return redirect(url_for("admin") + "#settings")


# ══════════════════════════════════════════════════════════════════════════════
# PRICE LISTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/price-lists")
def price_lists():
    lists   = _pl_repo.get_all()
    summary = _pl_repo.get_summary()
    return render_template("price_lists.html", lists=lists, summary=summary)


@app.route("/price-lists/<int:list_id>")
def price_list_detail(list_id: int):
    pl    = _pl_repo.get_by_id(list_id)
    if not pl:
        return redirect(url_for("price_lists"))
    items     = _pl_repo.get_items(list_id)
    all_items = _item_repo.get_all_items()
    return render_template("price_list_detail.html", pl=pl, items=items, all_items=all_items)


@app.route("/price-lists/new", methods=["GET", "POST"])
def price_list_new():
    customers = _cust_repo.get_all() if hasattr(_cust_repo, 'get_all') else []
    if request.method == "POST":
        try:
            lid = _pl_repo.create(
                name=request.form.get("name", "").strip(),
                description=request.form.get("description", "").strip(),
            )
            flash("Price list created", "ok")
            return redirect(url_for("price_list_detail", list_id=lid))
        except Exception as e:
            flash(str(e), "err")
    return render_template("price_list_form.html", pl=None, customers=customers)


@app.route("/price-lists/<int:list_id>/edit", methods=["GET", "POST"])
def price_list_edit(list_id: int):
    pl = _pl_repo.get_by_id(list_id)
    if not pl:
        return redirect(url_for("price_lists"))
    customers = _cust_repo.get_all() if hasattr(_cust_repo, 'get_all') else []
    if request.method == "POST":
        try:
            _pl_repo.update(list_id,
                name=request.form.get("name", "").strip(),
                description=request.form.get("description", "").strip(),
                is_active=bool(request.form.get("is_active")),
            )
            flash("Price list updated", "ok")
            return redirect(url_for("price_list_detail", list_id=list_id))
        except Exception as e:
            flash(str(e), "err")
    return render_template("price_list_form.html", pl=pl, customers=customers)


@app.route("/price-lists/<int:list_id>/item/add", methods=["POST"])
def price_list_add_item(list_id: int):
    try:
        item_id = int(request.form.get("item_id", 0))
        price   = float(request.form.get("price", 0) or 0)
        _pl_repo.add_item(list_id, item_id, price)
        flash("Item added to price list", "ok")
    except Exception as e:
        flash(str(e), "err")
    return redirect(url_for("price_list_detail", list_id=list_id))


@app.route("/price-lists/<int:list_id>/item/<int:pli_id>/update", methods=["POST"])
def price_list_update_item(list_id: int, pli_id: int):
    try:
        price = float(request.form.get("price", 0) or 0)
        _pl_repo.update_item_price(pli_id, price)
        flash("Price updated", "ok")
    except Exception as e:
        flash(str(e), "err")
    return redirect(url_for("price_list_detail", list_id=list_id))


@app.route("/price-lists/<int:list_id>/item/<int:pli_id>/remove", methods=["POST"])
def price_list_remove_item(list_id: int, pli_id: int):
    try:
        _pl_repo.remove_item(pli_id)
        flash("Item removed", "ok")
    except Exception as e:
        flash(str(e), "err")
    return redirect(url_for("price_list_detail", list_id=list_id))


@app.route("/price-lists/<int:list_id>/delete", methods=["POST"])
def price_list_delete(list_id: int):
    try:
        _pl_repo.delete(list_id)
        flash("Price list deleted", "ok")
    except Exception as e:
        flash(str(e), "err")
    return redirect(url_for("price_lists"))


@app.route("/price-lists/margin-analysis")
def margin_analysis():
    analysis = _pl_repo.get_margin_analysis()
    return render_template("margin_analysis.html", analysis=analysis)


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS API (JSON — for charts)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/analytics")
def api_analytics():
    """Return all chart data in one JSON response."""
    days = int(request.args.get("days", 30))
    date_from = (date.today() - timedelta(days=days)).isoformat()
    date_to   = date.today().isoformat()

    with get_connection() as conn:
        # ── Inventory KPIs ────────────────────────────────────────────────
        inv = conn.execute("""
            SELECT
              COUNT(*) AS total_products,
              SUM(stock) AS total_units,
              ROUND(SUM(stock * COALESCE(sell_price, 0)), 2) AS inv_value,
              SUM(CASE WHEN stock=0 THEN 1 ELSE 0 END) AS out_count,
              SUM(CASE WHEN min_stock>0 AND stock>0 AND stock<=min_stock THEN 1 ELSE 0 END) AS low_count,
              SUM(CASE WHEN stock>min_stock OR min_stock=0 THEN 1 ELSE 0 END) AS ok_count
            FROM inventory_items WHERE is_active=1
        """).fetchone()

        # ── 30-day activity trend ─────────────────────────────────────────
        trend = conn.execute("""
            SELECT date(timestamp) AS day, COUNT(*) AS ops
            FROM inventory_transactions
            WHERE date(timestamp) >= ?
            GROUP BY day ORDER BY day
        """, (date_from,)).fetchall()

        # Fill missing days
        trend_map = {r["day"]: r["ops"] for r in trend}
        trend_full = []
        for i in range(days):
            d = (date.today() - timedelta(days=days - 1 - i)).isoformat()
            trend_full.append({"day": d[-5:], "ops": trend_map.get(d, 0)})

        # ── Category distribution ─────────────────────────────────────────
        cats = conn.execute("""
            SELECT c.name_en AS cat, SUM(ii.stock) AS units
            FROM categories c
            JOIN part_types pt ON pt.category_id=c.id
            JOIN inventory_items ii ON ii.part_type_id=pt.id
            WHERE ii.is_active=1
            GROUP BY c.id ORDER BY units DESC LIMIT 8
        """).fetchall()

        # ── Sales this period ─────────────────────────────────────────────
        sales_stats = conn.execute("""
            SELECT COUNT(*) AS cnt,
                   COALESCE(SUM(total_amount-discount),0) AS revenue,
                   COALESCE(AVG(total_amount-discount),0) AS avg_sale,
                   COALESCE(SUM(si.qty_sum),0) AS items_sold
            FROM sales s
            LEFT JOIN (
                SELECT sale_id, SUM(quantity) AS qty_sum FROM sale_items GROUP BY sale_id
            ) si ON si.sale_id=s.id
            WHERE date(s.timestamp) BETWEEN ? AND ?
        """, (date_from, date_to)).fetchone()

        # ── Top customers ─────────────────────────────────────────────────
        top_customers = conn.execute("""
            SELECT COALESCE(customer_name,'Walk-in') AS name,
                   ROUND(SUM(total_amount-discount),2) AS spent
            FROM sales
            WHERE date(timestamp) BETWEEN ? AND ?
            GROUP BY COALESCE(customer_name,'Walk-in')
            ORDER BY spent DESC LIMIT 8
        """, (date_from, date_to)).fetchall()

        # ── Daily revenue ─────────────────────────────────────────────────
        rev_trend = conn.execute("""
            SELECT date(timestamp) AS day,
                   COUNT(*) AS sales_count,
                   ROUND(SUM(total_amount-discount),2) AS revenue
            FROM sales
            WHERE date(timestamp) BETWEEN ? AND ?
            GROUP BY day ORDER BY day
        """, (date_from, date_to)).fetchall()

        rev_map = {r["day"]: r["revenue"] for r in rev_trend}
        rev_full = []
        for i in range(days):
            d = (date.today() - timedelta(days=days - 1 - i)).isoformat()
            rev_full.append({"day": d[-5:], "revenue": rev_map.get(d, 0)})

        # ── Total customers ───────────────────────────────────────────────
        total_customers = conn.execute(
            "SELECT COUNT(*) FROM customers WHERE is_active=1"
        ).fetchone()[0]

    return jsonify({
        "inventory": dict(inv) if inv else {},
        "trend": trend_full,
        "rev_trend": rev_full,
        "categories": [dict(r) for r in cats],
        "sales_stats": dict(sales_stats) if sales_stats else {},
        "top_customers": [dict(r) for r in top_customers],
        "total_customers": total_customers,
    })


# ══════════════════════════════════════════════════════════════════════════════
# CSV EXPORTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/export/inventory.csv")
def export_inventory_csv():
    import csv, io
    items = _item_repo.get_all_items()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["ID", "Brand", "Name", "Color", "SKU", "Barcode",
                "Stock", "Min Stock", "Sell Price", "Active"])
    for i in items:
        w.writerow([i.id, i.brand, i.name, i.color, i.sku or "",
                    i.barcode or "", i.stock, i.min_stock,
                    i.sell_price or "", int(i.is_active)])
    from flask import Response
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=inventory.csv"})


@app.route("/export/transactions.csv")
def export_transactions_csv():
    import csv, io
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT t.id, t.operation, t.quantity, t.stock_before,
                   t.stock_after, t.note, t.timestamp,
                   i.brand, i.name, i.color
            FROM inventory_transactions t
            JOIN inventory_items i ON i.id=t.item_id
            ORDER BY t.timestamp DESC LIMIT 5000
        """).fetchall()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["ID", "Operation", "Qty", "Before", "After", "Note",
                "Timestamp", "Brand", "Name", "Color"])
    for r in rows:
        w.writerow(list(r))
    from flask import Response
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=transactions.csv"})


@app.route("/export/sales.csv")
def export_sales_csv():
    import csv, io
    sales = _sale_repo.get_all(limit=5000)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["ID", "Customer", "Total", "Discount", "Net Total",
                "Note", "Timestamp"])
    for s in sales:
        w.writerow([s.id, s.customer_name, s.total_amount,
                    s.discount, s.net_total, s.note, s.timestamp])
    from flask import Response
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=sales.csv"})


# ══════════════════════════════════════════════════════════════════════════════
# INVENTORY STATS API (for KPI cards)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/inventory/stats")
def api_inventory_stats():
    with get_connection() as conn:
        row = conn.execute("""
            SELECT
              COUNT(*) AS total_products,
              COALESCE(SUM(stock),0) AS total_units,
              ROUND(COALESCE(SUM(stock * COALESCE(sell_price,0)),0),2) AS inv_value,
              SUM(CASE WHEN stock=0 THEN 1 ELSE 0 END) AS out_count,
              SUM(CASE WHEN min_stock>0 AND stock>0 AND stock<=min_stock THEN 1 ELSE 0 END) AS low_count
            FROM inventory_items WHERE is_active=1
        """).fetchone()
        cats = conn.execute(
            "SELECT id, name_en AS name FROM categories WHERE is_active=1 ORDER BY sort_order"
        ).fetchall()
    return jsonify({
        "stats": dict(row) if row else {},
        "categories": [dict(c) for c in cats],
    })


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/audits")
def audits():
    """Inventory audit list."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT a.id, a.name, a.notes, a.status, a.created_at,
                   COUNT(al.id) AS line_count,
                   SUM(CASE WHEN al.actual_qty IS NOT NULL AND al.actual_qty != al.expected_qty THEN 1 ELSE 0 END) AS discrepancy_count
            FROM inventory_audits a
            LEFT JOIN audit_lines al ON al.audit_id = a.id
            GROUP BY a.id
            ORDER BY a.created_at DESC
        """).fetchall() if _table_exists(conn, 'inventory_audits') else []
    return render_template("audits.html", audits=[dict(r) for r in rows])


@app.route("/audits/new", methods=["GET", "POST"])
def audit_new():
    if request.method == "POST":
        name  = request.form.get("name", "").strip()
        notes = request.form.get("notes", "").strip()
        scope = request.form.get("scope", "all")
        if not name:
            flash("Audit name is required", "err")
            return redirect(url_for("audit_new"))
        try:
            with get_connection() as conn:
                if not _table_exists(conn, 'inventory_audits'):
                    conn.executescript("""
                        CREATE TABLE IF NOT EXISTS inventory_audits (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL, notes TEXT,
                            status TEXT DEFAULT 'OPEN',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                        CREATE TABLE IF NOT EXISTS audit_lines (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            audit_id INTEGER NOT NULL,
                            item_id INTEGER NOT NULL,
                            expected_qty INTEGER DEFAULT 0,
                            actual_qty INTEGER,
                            notes TEXT,
                            FOREIGN KEY (audit_id) REFERENCES inventory_audits(id) ON DELETE CASCADE,
                            FOREIGN KEY (item_id) REFERENCES inventory_items(id)
                        );
                    """)
                cur = conn.execute(
                    "INSERT INTO inventory_audits (name, notes) VALUES (?,?)", (name, notes)
                )
                audit_id = cur.lastrowid
                # Auto-populate based on scope
                if scope != "manual":
                    if scope == "all":
                        items = conn.execute(
                            "SELECT id, stock FROM inventory_items WHERE is_active=1"
                        ).fetchall()
                    elif scope == "low":
                        items = conn.execute(
                            "SELECT id, stock FROM inventory_items WHERE is_active=1 AND min_stock>0 AND stock>0 AND stock<=min_stock"
                        ).fetchall()
                    elif scope == "out":
                        items = conn.execute(
                            "SELECT id, stock FROM inventory_items WHERE is_active=1 AND stock=0"
                        ).fetchall()
                    else:
                        items = []
                    conn.executemany(
                        "INSERT INTO audit_lines (audit_id, item_id, expected_qty) VALUES (?,?,?)",
                        [(audit_id, r[0], r[1]) for r in items]
                    )
            flash(f"Audit '{name}' created", "ok")
            return redirect(url_for("audit_detail", audit_id=audit_id))
        except Exception as e:
            flash(str(e), "err")
    return render_template("audit_form.html")


@app.route("/audits/<int:audit_id>")
def audit_detail(audit_id: int):
    with get_connection() as conn:
        if not _table_exists(conn, 'inventory_audits'):
            return redirect(url_for("audits"))
        audit = conn.execute(
            "SELECT * FROM inventory_audits WHERE id=?", (audit_id,)
        ).fetchone()
        if not audit:
            return redirect(url_for("audits"))
        lines = conn.execute("""
            SELECT al.*, i.brand, i.name || COALESCE(' (' || i.color || ')','') AS item_name,
                   i.color, al.actual_qty - al.expected_qty AS discrepancy
            FROM audit_lines al
            JOIN inventory_items i ON i.id = al.item_id
            WHERE al.audit_id = ?
            ORDER BY i.brand, i.name
        """, (audit_id,)).fetchall()
        all_items = conn.execute(
            "SELECT id, brand, name, color, stock FROM inventory_items WHERE is_active=1 ORDER BY brand,name"
        ).fetchall()
    return render_template("audit_detail.html",
                           audit=dict(audit),
                           lines=[dict(r) for r in lines],
                           all_items=[dict(r) for r in all_items])


@app.route("/audits/<int:audit_id>/add-item", methods=["POST"])
def audit_add_item(audit_id: int):
    item_id = int(request.form.get("item_id", 0))
    expected = request.form.get("expected_qty", "").strip()
    try:
        with get_connection() as conn:
            if not expected:
                row = conn.execute("SELECT stock FROM inventory_items WHERE id=?", (item_id,)).fetchone()
                expected = row[0] if row else 0
            conn.execute(
                "INSERT OR IGNORE INTO audit_lines (audit_id, item_id, expected_qty) VALUES (?,?,?)",
                (audit_id, item_id, int(expected))
            )
        flash("Item added to audit", "ok")
    except Exception as e:
        flash(str(e), "err")
    return redirect(url_for("audit_detail", audit_id=audit_id))


@app.route("/audits/<int:audit_id>/count/<int:line_id>", methods=["POST"])
def audit_count(audit_id: int, line_id: int):
    actual = request.form.get("actual_qty", "").strip()
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE audit_lines SET actual_qty=? WHERE id=? AND audit_id=?",
                (int(actual) if actual else None, line_id, audit_id)
            )
        flash("Count saved", "ok")
    except Exception as e:
        flash(str(e), "err")
    return redirect(url_for("audit_detail", audit_id=audit_id))


@app.route("/audits/<int:audit_id>/close", methods=["POST"])
def audit_close(audit_id: int):
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE inventory_audits SET status='DONE', updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (audit_id,)
            )
        flash("Audit closed", "ok")
    except Exception as e:
        flash(str(e), "err")
    return redirect(url_for("audit_detail", audit_id=audit_id))


@app.route("/audits/<int:audit_id>/delete", methods=["POST"])
def audit_delete(audit_id: int):
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM inventory_audits WHERE id=?", (audit_id,))
        flash("Audit deleted", "ok")
    except Exception as e:
        flash(str(e), "err")
    return redirect(url_for("audits"))


def _table_exists(conn, name: str) -> bool:
    r = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return r is not None


# ══════════════════════════════════════════════════════════════════════════════
# CSV IMPORT & TEMPLATE
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/admin/import/csv", methods=["POST"])
def admin_import_csv():
    import csv, io
    f = request.files.get("csv_file")
    if not f or not f.filename.endswith(".csv"):
        flash("Please upload a .csv file", "err")
        return redirect(url_for("admin"))
    try:
        content = f.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content))
        added = 0
        for row in reader:
            name = row.get("name", "").strip()
            if not name:
                continue
            _item_repo.add_product(
                brand=row.get("brand", "").strip(),
                name=name,
                color=row.get("color", "").strip(),
                stock=int(row.get("stock", 0) or 0),
                min_stock=int(row.get("min_stock", 0) or 0),
                sell_price=float(row.get("sell_price", 0) or 0) or None,
                barcode=row.get("barcode", "").strip() or None,
            )
            added += 1
        flash(f"Imported {added} items successfully", "ok")
    except Exception as e:
        flash(f"Import error: {e}", "err")
    return redirect(url_for("admin"))


@app.route("/admin/import/template")
def admin_import_template():
    import csv, io
    from flask import Response
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["name", "brand", "color", "sku", "stock", "min_stock", "sell_price", "cost_price"])
    w.writerow(["iPhone 15 Screen", "Apple", "Black", "SKU001", "10", "5", "89.99", "45.00"])
    w.writerow(["Samsung S24 Battery", "Samsung", "", "SKU002", "20", "3", "34.99", "18.00"])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=import_template.csv"})


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def run(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    app.run(host=host, port=port, debug=debug, use_reloader=False)


def run_in_thread(port: int = 5000) -> threading.Thread:
    t = threading.Thread(target=run, kwargs={"port": port}, daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    print(f"\n Stock Manager Pro — Web Interface (Full)")
    print(f" Open on tablet: http://<your-PC-IP>:5000")
    print(f" Database: {DB_PATH}\n")
    run(debug=True)
