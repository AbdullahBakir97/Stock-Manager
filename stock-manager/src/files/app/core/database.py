"""
app/core/database.py — Connection, schema init, and seed data.

Schema versioning via app_config table.
V1 → V2 migration handled automatically.
"""
from __future__ import annotations

import os
import sys
import sqlite3
from typing import Optional
from app.core.logger import get_logger

_log = get_logger(__name__)


# ── DB path resolution ────────────────────────────────────────────────────────

def _db_path() -> str:
    if getattr(sys, "frozen", False):
        # PyInstaller bundle — use user's AppData (Windows) / equivalent
        try:
            from platformdirs import user_data_dir
            base = user_data_dir("StockManagerPro", "StockPro")
        except ImportError:
            base = os.path.join(
                os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                "StockPro", "StockManagerPro",
            )
        os.makedirs(base, exist_ok=True)
        db_path = os.path.join(base, "stock_manager.db")
        _log.info(f"DB path (production): {db_path}")
        return db_path
    # Development: DB next to source files (two levels up from app/core/)
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(root, "stock_manager.db")
    _log.debug(f"DB path (development): {db_path}")
    return db_path


DB_PATH: str = _db_path()


# ── Connection (thread-local pool) ────────────────────────────────────────────

import json
import threading
import urllib.request
import urllib.error

_sqlite_local = threading.local()
_sync_lock    = threading.Lock()


# ── Row factory ──────────────────────────────────────────────────────────────

class _DictRow(dict):
    """dict subclass that also supports integer index access, matching sqlite3.Row."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


def _dict_row_factory(cursor, row):
    return _DictRow(zip([d[0] for d in cursor.description], row))


# ── Turso HTTP API wrapper ────────────────────────────────────────────────────
# Pure Python stdlib — no Rust, no compilation, no extra packages.
# Presents the same execute()/executemany()/executescript() interface as
# sqlite3 so all 14+ repositories work without modification.

class _TursoCursor:
    """Minimal cursor-like object returned by TursoHTTPConnection.execute()."""

    def __init__(self, rows: list[dict], lastrowid: Optional[int] = None) -> None:
        self._rows = [_DictRow(r) for r in rows]
        self.lastrowid: int = lastrowid or 0
        self.rowcount: int = len(self._rows)

    def fetchall(self) -> list[_DictRow]:
        return self._rows

    def fetchone(self) -> Optional[_DictRow]:
        return self._rows[0] if self._rows else None


class _TursoHTTPConnection:
    """Minimal sqlite3-compatible wrapper over the Turso HTTP pipeline API.

    Uses only Python's stdlib urllib — no pip packages required.
    All queries are auto-committed (Turso's HTTP API is implicitly transactional).
    """

    def __init__(self, url: str, token: str) -> None:
        # Normalise libsql:// → https://
        self._url = url.replace("libsql://", "https://") + "/v2/pipeline"
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self.row_factory = None  # ignored; we always return _DictRow

    # ── Internal HTTP POST ────────────────────────────────────────────────

    def _post(self, stmts: list[dict]) -> list[dict]:
        """POST a pipeline of SQL statements to Turso.  Returns one result dict per statement."""
        payload = {
            "requests": [{"type": "execute", "stmt": s} for s in stmts] + [{"type": "close"}]
        }
        body = json.dumps(payload).encode()
        req = urllib.request.Request(self._url, data=body, headers=self._headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode(errors="replace")
            raise RuntimeError(f"Turso HTTP {exc.code}: {body_text}") from exc

        results = []
        for item in data.get("results", []):
            if item.get("type") == "error":
                msg = item.get("error", {}).get("message", str(item))
                # Raise the sqlite3 exception type, not a bare RuntimeError, so
                # callers that handle sqlite3.OperationalError (e.g. "no such
                # column" fallbacks) behave the same over the cloud connection
                # as they do against local SQLite.
                raise sqlite3.OperationalError(f"Turso SQL error: {msg}")
            if item.get("type") == "ok":
                results.append(item.get("response", {}).get("result", {}))
        return results

    # ── Arg / row codec ───────────────────────────────────────────────────

    @staticmethod
    def _enc(v) -> dict:
        if v is None:               return {"type": "null"}
        if isinstance(v, bool):     return {"type": "integer", "value": str(int(v))}
        if isinstance(v, int):      return {"type": "integer", "value": str(v)}
        if isinstance(v, float):    return {"type": "float",   "value": v}
        if isinstance(v, bytes):    return {"type": "blob",    "base64": v.hex()}
        return {"type": "text", "value": str(v)}

    @staticmethod
    def _decode_rows(result: dict) -> tuple[list[_DictRow], Optional[int]]:
        cols = [c["name"] for c in result.get("cols", [])]
        rows: list[_DictRow] = []
        for raw_row in result.get("rows", []):
            d: dict = {}
            for col, cell in zip(cols, raw_row):
                t = cell.get("type", "text")
                v = cell.get("value")
                if   t == "null":    v = None
                elif t == "integer": v = int(v)
                elif t == "float":   v = float(v)
                d[col] = v
            rows.append(_DictRow(d))
        last = result.get("last_insert_rowid")
        return rows, (int(last) if last else None)

    # ── Public sqlite3-compatible interface ───────────────────────────────

    def execute(self, sql: str, params=()) -> _TursoCursor:
        # Skip PRAGMA statements — they don't apply over HTTP
        if sql.strip().upper().startswith("PRAGMA"):
            return _TursoCursor([])
        stmt = {"sql": sql, "args": [self._enc(p) for p in params]}
        results = self._post([stmt])
        rows, lastrowid = self._decode_rows(results[0] if results else {})
        return _TursoCursor(rows, lastrowid)

    def executemany(self, sql: str, seq) -> None:
        stmts = [{"sql": sql, "args": [self._enc(p) for p in params]} for params in seq]
        if stmts:
            self._post(stmts)

    def executescript(self, script: str) -> None:
        # Strip SQL line comments BEFORE splitting on ';'. The schema has a
        # ';' inside a '-- ...' comment; splitting first would cut a statement
        # in half, and Turso parses each ';'-separated chunk independently —
        # the comment-only fragment fails with "unexpected end of input".
        # (Safe here: the DDL never contains '--' inside a string literal.)
        cleaned = "\n".join(
            line.split("--", 1)[0] for line in script.splitlines()
        )
        stmts = [
            {"sql": s.strip()}
            for s in cleaned.split(";")
            if s.strip() and not s.strip().upper().startswith("PRAGMA")
        ]
        if stmts:
            self._post(stmts)

    def ping(self) -> bool:
        """Return True if the cloud database is reachable."""
        try:
            self._post([{"sql": "SELECT 1"}])
            return True
        except Exception:
            return False

    # Context manager — no-op (HTTP is stateless)
    def commit(self) -> None: pass
    def close(self)  -> None: pass
    def __enter__(self):      return self
    def __exit__(self, *_):   pass


# Module-level Turso connection — HTTP is stateless so no thread-local needed.
_turso_conn: Optional[_TursoHTTPConnection] = None


def _get_turso_connection() -> _TursoHTTPConnection:
    """Return the cached Turso HTTP connection, rebuilding if credentials changed."""
    global _turso_conn
    from app.core.config import ShopConfig
    cfg = ShopConfig.get()
    if _turso_conn is None or _turso_conn._url != (cfg.turso_url.replace("libsql://", "https://") + "/v2/pipeline"):
        _turso_conn = _TursoHTTPConnection(cfg.turso_url, cfg.turso_auth_token)
    return _turso_conn


# ── DDL script executor ───────────────────────────────────────────────────────

def _executescript(conn, script: str) -> None:
    """Execute a SQL script on any connection type."""
    if isinstance(conn, _TursoHTTPConnection):
        conn.executescript(script)
    elif hasattr(conn, "executescript"):
        conn.executescript(script)
    else:
        for stmt in script.split(";"):
            stmt = stmt.strip()
            if stmt:
                try:
                    conn.execute(stmt)
                except Exception as exc:
                    _log.warning("DDL statement skipped: %s — %s", stmt[:80], exc)


def _apply_pragmas(conn) -> None:
    """Apply standard performance PRAGMAs (sqlite3 only — skipped for HTTP)."""
    if isinstance(conn, _TursoHTTPConnection):
        return  # pragmas don't apply over HTTP API
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA cache_size = -32768")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA mmap_size = 134217728")


def _get_sqlite_connection() -> sqlite3.Connection:
    """Return a thread-local cached plain sqlite3 connection."""
    conn = getattr(_sqlite_local, "conn", None)
    if conn is not None:
        try:
            conn.execute("SELECT 1")
            return conn
        except (sqlite3.ProgrammingError, sqlite3.OperationalError):
            conn = None

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _apply_pragmas(conn)
    _sqlite_local.conn = conn
    return conn


def get_connection():
    """Dispatcher: returns Turso HTTP connection when cloud sync is enabled
    and the user is in replica mode (cloud as primary), otherwise returns a
    plain sqlite3 connection.

    All repositories call this via BaseRepository._conn() and are unaffected
    by which connection type is returned.
    """
    try:
        from app.core.config import ShopConfig
        cfg = ShopConfig.get()
        # Only use cloud connection if sync is enabled AND role is replica
        # (primary mode uses local DB and pushes to cloud on-demand)
        if cfg.cloud_sync_enabled == "1" and cfg.turso_url and cfg.sync_role == "replica":
            return _get_turso_connection()
    except Exception:
        pass  # config unavailable before init_db — use sqlite3
    return _get_sqlite_connection()


def get_local_connection():
    """Always return the LOCAL SQLite connection, regardless of cloud-sync
    settings.

    Bootstrap config (ShopConfig — including the cloud-sync on/off flag and
    Turso credentials) MUST live on this PC: it's what decides whether data is
    routed to the cloud at all. Reading/writing it through get_connection()
    would be circular — enabling cloud sync would route the very 'enabled' flag
    to the cloud, while the next reload reads the local DB and never sees it,
    so the setting appears to never take effect. ShopConfig therefore persists
    here, locally, always.
    """
    return _get_sqlite_connection()


def sync_to_remote() -> str:
    """Health-check ping to Turso.  With the HTTP API each write already goes
    directly to the cloud, so there is nothing to 'sync' — we just verify
    the connection is alive and return an ISO timestamp.
    """
    from datetime import datetime, timezone
    with _sync_lock:
        try:
            from app.core.config import ShopConfig
            cfg = ShopConfig.get()
            if cfg.cloud_sync_enabled == "1" and cfg.turso_url:
                conn = _get_turso_connection()
                conn.ping()
        except Exception as exc:
            raise RuntimeError(f"Turso ping failed: {exc}") from exc
    return datetime.now(timezone.utc).isoformat()


# Tables in dependency order (parents before children) — used by
# push_local_to_turso() for both schema creation order and bulk insert order.
_SYNCED_TABLES = (
    "app_config", "categories", "part_types", "part_type_colors",
    "model_part_type_colors", "phone_models", "inventory_items",
    "inventory_transactions", "suppliers", "supplier_items",
    "locations", "location_stock", "stock_transfers",
    "customers", "sales", "sale_items",
    "purchase_orders", "purchase_order_lines", "returns",
    "inventory_audits", "audit_lines",
    "price_lists", "price_list_items",
    "scan_invoices", "scan_invoice_items",
    "phones", "phone_transactions",
)


def push_local_to_turso(progress_cb=None) -> dict:
    """One-time bulk push of all local SQLite data into the Turso cloud DB.

    Used by 'Initialize as Primary' in the Cloud Sync admin panel — the PC
    that already holds the shop's data exports it to the (empty) Turso
    database so every other PC can start reading/writing the same dataset
    over the HTTP API.

    Existing rows in each Turso table are deleted first (the cloud DB is
    assumed to be freshly created / empty). Returns a dict of
    {table: row_count} for the tables that were pushed.

    Raises RuntimeError if local database is empty to prevent data loss.
    """
    local = _get_sqlite_connection()
    remote = _get_turso_connection()

    # Safety check: verify local database has meaningful data before wiping cloud
    total_local_rows = 0
    for table in _SYNCED_TABLES:
        exists = local.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if exists:
            count = local.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            total_local_rows += count

    if total_local_rows == 0:
        raise RuntimeError(
            "Cannot push to cloud: local database is empty. "
            "This would wipe your cloud database. "
            "Ensure your local database contains your data before running 'Initialize as Primary'."
        )

    counts: dict[str, int] = {}

    # Drop all tables first to avoid FK constraints (Turso HTTP ignores PRAGMA)
    # This is safer than DELETE because it completely removes FK constraints
    for table in _SYNCED_TABLES:
        try:
            remote.execute(f"DROP TABLE IF EXISTS {table}")
        except Exception as e:
            _log.warning(f"Failed to drop table {table}: {e}")

    # Recreate schema with all tables
    _executescript(remote, _DDL)

    # Insert in forward order (parents before children) to satisfy FK constraints
    for table in _SYNCED_TABLES:
        # Skip tables that don't exist locally (e.g. older DBs pre-migration).
        exists = local.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not exists:
            continue

        rows = local.execute(f"SELECT * FROM {table}").fetchall()
        cols = [d[0] for d in local.execute(f"SELECT * FROM {table} LIMIT 0").description]

        if progress_cb:
            progress_cb(table, len(rows))

        if rows:
            placeholders = ",".join("?" * len(cols))
            seq = [tuple(r[c] for c in cols) for r in rows]
            try:
                remote.executemany(
                    f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})", seq
                )
            except Exception as e:
                _log.error(f"Failed to insert into {table}: {e}")
                raise RuntimeError(f"Failed to insert data into {table}: {e}")
        counts[table] = len(rows)

    return counts


def close_all_connections() -> None:
    """Close thread-local sqlite3 connection and reset Turso HTTP handle."""
    global _turso_conn
    conn = getattr(_sqlite_local, "conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
        _sqlite_local.conn = None
    _turso_conn = None


# ── Schema DDL ────────────────────────────────────────────────────────────────

_DDL = """
    -- Version tracking
    CREATE TABLE IF NOT EXISTS app_config (
        key   TEXT PRIMARY KEY,
        value TEXT
    );

    -- Inventory categories (tabs)
    CREATE TABLE IF NOT EXISTS categories (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        key        TEXT NOT NULL UNIQUE,
        name_en    TEXT NOT NULL,
        name_de    TEXT NOT NULL DEFAULT '',
        name_ar    TEXT NOT NULL DEFAULT '',
        sort_order INTEGER NOT NULL DEFAULT 0,
        icon       TEXT NOT NULL DEFAULT '',
        is_active  INTEGER NOT NULL DEFAULT 1
    );

    -- Part types within a category (column groups in the matrix)
    CREATE TABLE IF NOT EXISTS part_types (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id   INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
        key           TEXT NOT NULL,
        name          TEXT NOT NULL,
        accent_color  TEXT NOT NULL DEFAULT '#4A9EFF',
        sort_order    INTEGER NOT NULL DEFAULT 0,
        default_price REAL,   -- default price per item; per-item sell_price overrides
        UNIQUE(category_id, key)
    );

    -- Scan Invoice header: one per confirmed Quick Scan session
    CREATE TABLE IF NOT EXISTS scan_invoices (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number  TEXT NOT NULL UNIQUE,
        operation       TEXT NOT NULL,          -- 'IN' | 'OUT'
        layout          TEXT NOT NULL,          -- 'a4' | 'thermal'
        customer_name   TEXT NOT NULL DEFAULT '',
        subtotal        REAL NOT NULL DEFAULT 0,
        total           REAL NOT NULL DEFAULT 0,
        currency        TEXT NOT NULL DEFAULT '€',
        note            TEXT NOT NULL DEFAULT '',
        pdf_path        TEXT NOT NULL DEFAULT '',
        created_at      TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS scan_invoice_items (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id      INTEGER NOT NULL REFERENCES scan_invoices(id) ON DELETE CASCADE,
        item_id         INTEGER NOT NULL REFERENCES inventory_items(id),
        item_snapshot   TEXT NOT NULL,
        barcode         TEXT NOT NULL DEFAULT '',
        quantity        INTEGER NOT NULL,
        unit_price      REAL NOT NULL,
        line_total      REAL NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_scan_invoices_date
        ON scan_invoices(created_at);
    CREATE INDEX IF NOT EXISTS idx_scan_invoice_items_inv
        ON scan_invoice_items(invoice_id);

    -- Colors available for a part type (e.g., ORG Service Pack → Black, Blue, Silver)
    CREATE TABLE IF NOT EXISTS part_type_colors (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        part_type_id INTEGER NOT NULL REFERENCES part_types(id) ON DELETE CASCADE,
        color_name   TEXT NOT NULL,
        color_code   TEXT NOT NULL DEFAULT '',
        sort_order   INTEGER NOT NULL DEFAULT 0,
        UNIQUE(part_type_id, color_name)
    );

    -- Per-model part type product-color overrides.
    -- When rows exist for (model_id, part_type_id) they REPLACE the global
    -- part_type_colors for that model; when absent, global colors apply.
    CREATE TABLE IF NOT EXISTS model_part_type_colors (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        model_id     INTEGER NOT NULL REFERENCES phone_models(id) ON DELETE CASCADE,
        part_type_id INTEGER NOT NULL REFERENCES part_types(id) ON DELETE CASCADE,
        color_name   TEXT NOT NULL,
        UNIQUE(model_id, part_type_id, color_name)
    );

    -- Phone models (shared across all categories)
    CREATE TABLE IF NOT EXISTS phone_models (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        brand      TEXT NOT NULL,
        name       TEXT NOT NULL UNIQUE,
        sort_order INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Unified inventory
    -- color is part of unique key: model × part_type × color
    CREATE TABLE IF NOT EXISTS inventory_items (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        brand        TEXT    NOT NULL DEFAULT '',
        name         TEXT    NOT NULL DEFAULT '',
        color        TEXT    NOT NULL DEFAULT '',
        sku          TEXT,
        barcode      TEXT    UNIQUE,
        sell_price   REAL,
        cost_price   REAL,
        stock        INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
        min_stock    INTEGER NOT NULL DEFAULT 0,
        inventur     INTEGER,
        image_path   TEXT,
        expiry_date  TEXT,
        warranty_date TEXT,
        model_id     INTEGER REFERENCES phone_models(id) ON DELETE CASCADE,
        part_type_id INTEGER REFERENCES part_types(id)   ON DELETE CASCADE,
        is_active    INTEGER NOT NULL DEFAULT 1,
        created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
        updated_at   TEXT    NOT NULL DEFAULT (datetime('now')),
        UNIQUE(model_id, part_type_id, color)
    );

    -- Unified audit log (replaces product_transactions + stock_transactions in V4)
    CREATE TABLE IF NOT EXISTS inventory_transactions (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id      INTEGER NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
        operation    TEXT    NOT NULL CHECK(operation IN ('IN','OUT','ADJUST','CREATE')),
        quantity     INTEGER NOT NULL,
        stock_before INTEGER NOT NULL,
        stock_after  INTEGER NOT NULL,
        note         TEXT,
        timestamp    TEXT    NOT NULL DEFAULT (datetime('now'))
    );

    -- Suppliers  (columns must match the canonical V12 definition below — a
    -- fresh/cloud DB builds from THIS one, so rating/updated_at live here too)
    CREATE TABLE IF NOT EXISTS suppliers (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        name         TEXT NOT NULL,
        contact_name TEXT NOT NULL DEFAULT '',
        phone        TEXT NOT NULL DEFAULT '',
        email        TEXT NOT NULL DEFAULT '',
        address      TEXT NOT NULL DEFAULT '',
        notes        TEXT NOT NULL DEFAULT '',
        rating       INTEGER NOT NULL DEFAULT 0,
        is_active    INTEGER NOT NULL DEFAULT 1,
        created_at   TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Supplier ↔ Item price mapping
    CREATE TABLE IF NOT EXISTS supplier_items (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_id  INTEGER NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
        item_id      INTEGER NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
        cost_price   REAL    NOT NULL DEFAULT 0,
        lead_days    INTEGER NOT NULL DEFAULT 0,
        supplier_sku TEXT    NOT NULL DEFAULT '',
        is_preferred INTEGER NOT NULL DEFAULT 0,
        UNIQUE(supplier_id, item_id)
    );

    -- Inventory locations
    CREATE TABLE IF NOT EXISTS locations (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL DEFAULT '',
        is_default  INTEGER NOT NULL DEFAULT 0,
        is_active   INTEGER NOT NULL DEFAULT 1,
        created_at  TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Per-location stock (replaces single stock column for multi-location)
    CREATE TABLE IF NOT EXISTS location_stock (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id     INTEGER NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
        location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
        quantity    INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
        UNIQUE(item_id, location_id)
    );

    -- Stock transfers between locations
    CREATE TABLE IF NOT EXISTS stock_transfers (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id         INTEGER NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
        from_location_id INTEGER NOT NULL REFERENCES locations(id),
        to_location_id   INTEGER NOT NULL REFERENCES locations(id),
        quantity         INTEGER NOT NULL CHECK(quantity > 0),
        note             TEXT,
        timestamp        TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Sales transactions (POS)
    -- Customers
    CREATE TABLE IF NOT EXISTS customers (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT    NOT NULL,
        phone       TEXT    DEFAULT '',
        email       TEXT    DEFAULT '',
        address     TEXT    DEFAULT '',
        notes       TEXT    DEFAULT '',
        is_active   INTEGER DEFAULT 1,
        created_at  TEXT    DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_customers_name  ON customers(name);
    CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);

    CREATE TABLE IF NOT EXISTS sales (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT NOT NULL DEFAULT '',
        customer_id   INTEGER REFERENCES customers(id),
        total_amount  REAL NOT NULL DEFAULT 0,
        discount      REAL NOT NULL DEFAULT 0,
        note          TEXT NOT NULL DEFAULT '',
        timestamp     TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Items in each sale
    CREATE TABLE IF NOT EXISTS sale_items (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id      INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
        item_id      INTEGER NOT NULL REFERENCES inventory_items(id),
        quantity     INTEGER NOT NULL CHECK(quantity > 0),
        unit_price   REAL    NOT NULL,
        cost_price   REAL    NOT NULL DEFAULT 0,
        line_total   REAL    NOT NULL
    );

    -- Indexes
    CREATE INDEX IF NOT EXISTS idx_part_types_category    ON part_types(category_id);
    CREATE INDEX IF NOT EXISTS idx_inv_items_model        ON inventory_items(model_id);
    CREATE INDEX IF NOT EXISTS idx_inv_items_barcode      ON inventory_items(barcode);
    CREATE INDEX IF NOT EXISTS idx_inv_txn_item           ON inventory_transactions(item_id);
    CREATE INDEX IF NOT EXISTS idx_inv_txn_time           ON inventory_transactions(timestamp);
    CREATE INDEX IF NOT EXISTS idx_phone_models_brand     ON phone_models(brand);
    CREATE INDEX IF NOT EXISTS idx_part_type_colors_pt    ON part_type_colors(part_type_id);
    CREATE INDEX IF NOT EXISTS idx_mptc_model_pt          ON model_part_type_colors(model_id, part_type_id);
    CREATE INDEX IF NOT EXISTS idx_inv_txn_item_time      ON inventory_transactions(item_id, timestamp DESC);
    CREATE INDEX IF NOT EXISTS idx_supplier_items_supplier ON supplier_items(supplier_id);
    CREATE INDEX IF NOT EXISTS idx_supplier_items_item     ON supplier_items(item_id);
    CREATE INDEX IF NOT EXISTS idx_location_stock_item     ON location_stock(item_id);
    CREATE INDEX IF NOT EXISTS idx_location_stock_loc      ON location_stock(location_id);
    CREATE INDEX IF NOT EXISTS idx_sale_items_sale         ON sale_items(sale_id);
    CREATE INDEX IF NOT EXISTS idx_sales_time              ON sales(timestamp);
    CREATE INDEX IF NOT EXISTS idx_transfers_item          ON stock_transfers(item_id);

    -- Purchase orders (V11)
    CREATE TABLE IF NOT EXISTS purchase_orders (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        po_number   TEXT    NOT NULL UNIQUE,
        supplier_id INTEGER REFERENCES suppliers(id),
        status      TEXT    NOT NULL DEFAULT 'DRAFT',
        notes       TEXT    DEFAULT '',
        created_at  TEXT    DEFAULT (datetime('now')),
        updated_at  TEXT    DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_po_supplier ON purchase_orders(supplier_id);
    CREATE INDEX IF NOT EXISTS idx_po_status   ON purchase_orders(status);

    CREATE TABLE IF NOT EXISTS purchase_order_lines (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        po_id        INTEGER NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
        item_id      INTEGER NOT NULL REFERENCES inventory_items(id),
        quantity     INTEGER NOT NULL DEFAULT 1,
        cost_price   REAL    NOT NULL DEFAULT 0,
        received_qty INTEGER NOT NULL DEFAULT 0
    );
    CREATE INDEX IF NOT EXISTS idx_po_lines_po ON purchase_order_lines(po_id);

    -- Returns (V11)
    CREATE TABLE IF NOT EXISTS returns (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id       INTEGER REFERENCES sales(id),
        item_id       INTEGER NOT NULL REFERENCES inventory_items(id),
        quantity      INTEGER NOT NULL DEFAULT 1,
        reason        TEXT    DEFAULT '',
        action        TEXT    NOT NULL DEFAULT 'RESTOCK',
        refund_amount REAL    DEFAULT 0,
        created_at    TEXT    DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_returns_sale ON returns(sale_id);
    CREATE INDEX IF NOT EXISTS idx_returns_item ON returns(item_id);

    -- Suppliers detail (V12)
    CREATE TABLE IF NOT EXISTS suppliers (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        name         TEXT    NOT NULL,
        contact_name TEXT    DEFAULT '',
        phone        TEXT    DEFAULT '',
        email        TEXT    DEFAULT '',
        address      TEXT    DEFAULT '',
        notes        TEXT    DEFAULT '',
        rating       INTEGER DEFAULT 0,
        is_active    INTEGER DEFAULT 1,
        created_at   TEXT    DEFAULT (datetime('now')),
        updated_at   TEXT    DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_suppliers_active ON suppliers(is_active);

    -- Supplier-item link (V12)
    CREATE TABLE IF NOT EXISTS supplier_items (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_id INTEGER NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
        item_id     INTEGER NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
        cost_price  REAL    DEFAULT 0,
        lead_days   INTEGER DEFAULT 0,
        sku         TEXT    DEFAULT '',
        UNIQUE(supplier_id, item_id)
    );
    CREATE INDEX IF NOT EXISTS idx_si_supplier ON supplier_items(supplier_id);
    CREATE INDEX IF NOT EXISTS idx_si_item     ON supplier_items(item_id);

    -- Inventory audits / stocktakes (V12)
    CREATE TABLE IF NOT EXISTS inventory_audits (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT    NOT NULL,
        status      TEXT    NOT NULL DEFAULT 'IN_PROGRESS',
        notes       TEXT    DEFAULT '',
        started_at  TEXT    DEFAULT (datetime('now')),
        completed_at TEXT   DEFAULT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_audit_status ON inventory_audits(status);

    CREATE TABLE IF NOT EXISTS audit_lines (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        audit_id     INTEGER NOT NULL REFERENCES inventory_audits(id) ON DELETE CASCADE,
        item_id      INTEGER NOT NULL REFERENCES inventory_items(id),
        system_qty   INTEGER NOT NULL DEFAULT 0,
        counted_qty  INTEGER DEFAULT NULL,
        difference   INTEGER DEFAULT NULL,
        note         TEXT    DEFAULT ''
    );
    CREATE INDEX IF NOT EXISTS idx_al_audit ON audit_lines(audit_id);
    CREATE INDEX IF NOT EXISTS idx_al_item  ON audit_lines(item_id);

    -- Price lists (V12)
    CREATE TABLE IF NOT EXISTS price_lists (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT    NOT NULL,
        description TEXT    DEFAULT '',
        is_active   INTEGER DEFAULT 1,
        created_at  TEXT    DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS price_list_items (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        price_list_id INTEGER NOT NULL REFERENCES price_lists(id) ON DELETE CASCADE,
        item_id       INTEGER NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
        price         REAL    NOT NULL DEFAULT 0,
        UNIQUE(price_list_id, item_id)
    );
    CREATE INDEX IF NOT EXISTS idx_pli_list ON price_list_items(price_list_id);
    CREATE INDEX IF NOT EXISTS idx_pli_item ON price_list_items(item_id);

    -- Phone units inventory (V22)
    CREATE TABLE IF NOT EXISTS phones (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        model_id    INTEGER NOT NULL REFERENCES phone_models(id) ON DELETE RESTRICT,
        imei        TEXT UNIQUE,
        storage     TEXT NOT NULL DEFAULT '',
        condition   TEXT NOT NULL DEFAULT 'used',
        battery_pct INTEGER,
        buy_price   REAL,
        sell_price  REAL,
        status      TEXT NOT NULL DEFAULT 'in_stock',
        notes       TEXT NOT NULL DEFAULT '',
        created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
    );
    CREATE INDEX IF NOT EXISTS idx_phones_model  ON phones(model_id);
    CREATE INDEX IF NOT EXISTS idx_phones_status ON phones(status);
    CREATE INDEX IF NOT EXISTS idx_phones_imei   ON phones(imei);

    -- Phone unit transaction / audit log (V23) — mirrors inventory_transactions
    -- but for individual IMEI-tracked phone units. Denormalized snapshot
    -- columns (imei/model_brand/model_name/storage/sell_price) keep the
    -- history readable even after the phone unit itself is deleted.
    CREATE TABLE IF NOT EXISTS phone_transactions (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        phone_id      INTEGER NOT NULL,
        operation     TEXT NOT NULL,   -- CREATE | EDIT | SOLD | RESERVED | IN_STOCK | DELETE
        status_before TEXT NOT NULL DEFAULT '',
        status_after  TEXT NOT NULL DEFAULT '',
        imei          TEXT NOT NULL DEFAULT '',
        model_brand   TEXT NOT NULL DEFAULT '',
        model_name    TEXT NOT NULL DEFAULT '',
        storage       TEXT NOT NULL DEFAULT '',
        sell_price    REAL,
        note          TEXT NOT NULL DEFAULT '',
        timestamp     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
    );
    CREATE INDEX IF NOT EXISTS idx_phone_tx_phone ON phone_transactions(phone_id);
    CREATE INDEX IF NOT EXISTS idx_phone_tx_op    ON phone_transactions(operation);
    CREATE INDEX IF NOT EXISTS idx_phone_tx_ts    ON phone_transactions(timestamp);
"""

_SCHEMA_VERSION = "23"


# ── V2 → V3 migration ────────────────────────────────────────────────────────

def _migrate_v2_to_v3(conn: sqlite3.Connection) -> None:
    """V3 adds new ShopConfig keys and setup_complete flag. No new tables."""
    _log.info("Migrating database schema from V2 to V3")
    defaults = {
        "currency_position": "prefix",
        "logo_path":         "",
        "admin_pin":         "",
        "contact_info":      "",
        "setup_complete":    "1",   # existing installs skip the setup wizard
    }
    for k, v in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO app_config (key, value) VALUES (?,?)", (k, v)
        )
    _log.info("V2 to V3 migration completed")


# ── V3 → V4 migration ────────────────────────────────────────────────────────

def _migrate_v4_to_v5(conn: sqlite3.Connection) -> None:
    """Seed default command barcodes for Quick Scan."""
    _log.info("Migrating database schema from V4 to V5")
    defaults = [
        ("scan_cmd_takeout", "CMD-TAKEOUT"),
        ("scan_cmd_insert",  "CMD-INSERT"),
        ("scan_cmd_confirm", "CMD-CONFIRM"),
    ]
    for key, val in defaults:
        conn.execute(
            "INSERT OR IGNORE INTO app_config (key, value) VALUES (?,?)",
            (key, val),
        )
    _log.info("V4 to V5 migration completed")


def _migrate_v5_to_v6(conn: sqlite3.Connection) -> None:
    """V6: Add part_type_colors, rebuild inventory_items with color constraint,
    and drop legacy tables now that data is fully in inventory_items."""
    _log.info("Migrating database schema from V5 to V6")

    # 1. Create part_type_colors table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS part_type_colors (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            part_type_id INTEGER NOT NULL REFERENCES part_types(id) ON DELETE CASCADE,
            color_name   TEXT NOT NULL,
            color_code   TEXT NOT NULL DEFAULT '',
            sort_order   INTEGER NOT NULL DEFAULT 0,
            UNIQUE(part_type_id, color_name)
        )
    """)

    # 2. Rebuild inventory_items with UNIQUE(model_id, part_type_id, color)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory_items_new (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            brand        TEXT    NOT NULL DEFAULT '',
            name         TEXT    NOT NULL DEFAULT '',
            color        TEXT    NOT NULL DEFAULT '',
            sku          TEXT,
            barcode      TEXT    UNIQUE,
            sell_price   REAL,
            stock        INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
            min_stock    INTEGER NOT NULL DEFAULT 0,
            inventur     INTEGER,
            model_id     INTEGER REFERENCES phone_models(id) ON DELETE CASCADE,
            part_type_id INTEGER REFERENCES part_types(id)   ON DELETE CASCADE,
            is_active    INTEGER NOT NULL DEFAULT 1,
            created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at   TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE(model_id, part_type_id, color)
        )
    """)
    conn.execute("""
        INSERT OR IGNORE INTO inventory_items_new
            (id, brand, name, color, sku, barcode, sell_price, stock, min_stock,
             inventur, model_id, part_type_id, is_active, created_at, updated_at)
        SELECT id, brand, name, color, sku, barcode, sell_price, stock, min_stock,
               inventur, model_id, part_type_id, is_active, created_at, updated_at
        FROM inventory_items
    """)
    conn.execute("DROP TABLE inventory_items")
    conn.execute("ALTER TABLE inventory_items_new RENAME TO inventory_items")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_inv_items_model ON inventory_items(model_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_inv_items_barcode ON inventory_items(barcode)")

    # 3. Drop legacy tables
    conn.execute("DROP TABLE IF EXISTS product_transactions")
    conn.execute("DROP TABLE IF EXISTS stock_transactions")
    conn.execute("DROP TABLE IF EXISTS products")
    conn.execute("DROP TABLE IF EXISTS stock_entries")

    # 4. Drop legacy indexes
    conn.execute("DROP INDEX IF EXISTS idx_products_barcode")
    conn.execute("DROP INDEX IF EXISTS idx_product_txn_product")
    conn.execute("DROP INDEX IF EXISTS idx_product_txn_time")
    conn.execute("DROP INDEX IF EXISTS idx_stock_entries_model")
    conn.execute("DROP INDEX IF EXISTS idx_stock_entries_part")
    conn.execute("DROP INDEX IF EXISTS idx_stock_txn_entry")

    _log.info("V5 to V6 migration completed")


def _migrate_v6_to_v7(conn: sqlite3.Connection) -> None:
    """V7: Add image_path column to inventory_items for product photos."""
    _log.info("Migrating database schema from V6 to V7 (add image_path)")
    cols = {r[1] for r in conn.execute("PRAGMA table_info(inventory_items)").fetchall()}
    if "image_path" not in cols:
        conn.execute("ALTER TABLE inventory_items ADD COLUMN image_path TEXT")
    _log.info("V6 to V7 migration completed")


def _migrate_v7_to_v8(conn: sqlite3.Connection) -> None:
    """V8: Add expiry/warranty columns, create default location, populate location_stock."""
    _log.info("Migrating database schema from V7 to V8")

    # 1. Add expiry_date and warranty_date to inventory_items
    cols = {r[1] for r in conn.execute("PRAGMA table_info(inventory_items)").fetchall()}
    if "expiry_date" not in cols:
        conn.execute("ALTER TABLE inventory_items ADD COLUMN expiry_date TEXT")
    if "warranty_date" not in cols:
        conn.execute("ALTER TABLE inventory_items ADD COLUMN warranty_date TEXT")

    # 2. Tables (suppliers, supplier_items, locations, location_stock, stock_transfers)
    #    are already created by _DDL via CREATE TABLE IF NOT EXISTS.

    # 3. Create a default "Main" location for existing single-location data
    existing = conn.execute("SELECT id FROM locations LIMIT 1").fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO locations (name, description, is_default, is_active) "
            "VALUES ('Main', 'Default location', 1, 1)"
        )
    default_loc = conn.execute(
        "SELECT id FROM locations WHERE is_default = 1 LIMIT 1"
    ).fetchone()
    if default_loc:
        loc_id = default_loc["id"]
        # 4. Populate location_stock from existing inventory_items.stock
        conn.execute(
            """INSERT OR IGNORE INTO location_stock (item_id, location_id, quantity)
               SELECT id, ?, stock FROM inventory_items WHERE stock > 0""",
            (loc_id,),
        )

    _log.info("V7 to V8 migration completed")


def _migrate_v8_to_v9(conn: sqlite3.Connection) -> None:
    """V9: Sales tables (created by DDL). Just bump version."""
    _log.info("Migrating database schema from V8 to V9")
    # sales and sale_items tables already created by _DDL
    _log.info("V8 to V9 migration completed")


def _migrate_v9_to_v10(conn: sqlite3.Connection) -> None:
    """V10: Customers table + link sales to customers."""
    _log.info("Migrating database schema from V9 to V10")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS customers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            phone       TEXT    DEFAULT '',
            email       TEXT    DEFAULT '',
            address     TEXT    DEFAULT '',
            notes       TEXT    DEFAULT '',
            is_active   INTEGER DEFAULT 1,
            created_at  TEXT    DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_customers_name
            ON customers(name);
        CREATE INDEX IF NOT EXISTS idx_customers_phone
            ON customers(phone);
    """)
    # Add customer_id column to sales table if not present
    cols = {r[1] for r in conn.execute("PRAGMA table_info(sales)").fetchall()}
    if "customer_id" not in cols:
        conn.execute(
            "ALTER TABLE sales ADD COLUMN customer_id INTEGER REFERENCES customers(id)"
        )
    _log.info("V9 to V10 migration completed")


def _migrate_v10_to_v11(conn: sqlite3.Connection) -> None:
    """V11: Purchase orders + line items + returns."""
    _log.info("Migrating database schema from V10 to V11")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS purchase_orders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            po_number   TEXT    NOT NULL UNIQUE,
            supplier_id INTEGER REFERENCES suppliers(id),
            status      TEXT    NOT NULL DEFAULT 'DRAFT',
            notes       TEXT    DEFAULT '',
            created_at  TEXT    DEFAULT (datetime('now')),
            updated_at  TEXT    DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_po_supplier
            ON purchase_orders(supplier_id);
        CREATE INDEX IF NOT EXISTS idx_po_status
            ON purchase_orders(status);

        CREATE TABLE IF NOT EXISTS purchase_order_lines (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            po_id        INTEGER NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
            item_id      INTEGER NOT NULL REFERENCES inventory_items(id),
            quantity     INTEGER NOT NULL DEFAULT 1,
            cost_price   REAL    NOT NULL DEFAULT 0,
            received_qty INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_po_lines_po
            ON purchase_order_lines(po_id);

        CREATE TABLE IF NOT EXISTS returns (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id       INTEGER REFERENCES sales(id),
            item_id       INTEGER NOT NULL REFERENCES inventory_items(id),
            quantity      INTEGER NOT NULL DEFAULT 1,
            reason        TEXT    DEFAULT '',
            action        TEXT    NOT NULL DEFAULT 'RESTOCK',
            refund_amount REAL    DEFAULT 0,
            created_at    TEXT    DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_returns_sale
            ON returns(sale_id);
        CREATE INDEX IF NOT EXISTS idx_returns_item
            ON returns(item_id);
    """)
    _log.info("V10 to V11 migration completed")


def _migrate_v11_to_v12(conn: sqlite3.Connection) -> None:
    """V12: Suppliers detail, supplier_items, inventory_audits, audit_lines, price_lists, price_list_items."""
    _log.info("Migrating database schema from V11 to V12")
    
    # Check if suppliers table exists and has rating column
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if 'suppliers' in tables:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(suppliers)").fetchall()}
        if 'rating' not in cols:
            conn.execute("ALTER TABLE suppliers ADD COLUMN rating INTEGER DEFAULT 0")
    
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL,
            contact_name TEXT    DEFAULT '',
            phone        TEXT    DEFAULT '',
            email        TEXT    DEFAULT '',
            address      TEXT    DEFAULT '',
            notes        TEXT    DEFAULT '',
            rating       INTEGER DEFAULT 0,
            is_active    INTEGER DEFAULT 1,
            created_at   TEXT    DEFAULT (datetime('now')),
            updated_at   TEXT    DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_suppliers_active ON suppliers(is_active);

        CREATE TABLE IF NOT EXISTS supplier_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
            item_id     INTEGER NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
            cost_price  REAL    DEFAULT 0,
            lead_days   INTEGER DEFAULT 0,
            sku         TEXT    DEFAULT '',
            UNIQUE(supplier_id, item_id)
        );
        CREATE INDEX IF NOT EXISTS idx_si_supplier ON supplier_items(supplier_id);
        CREATE INDEX IF NOT EXISTS idx_si_item     ON supplier_items(item_id);

        CREATE TABLE IF NOT EXISTS inventory_audits (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL,
            status       TEXT    NOT NULL DEFAULT 'IN_PROGRESS',
            notes        TEXT    DEFAULT '',
            started_at   TEXT    DEFAULT (datetime('now')),
            completed_at TEXT    DEFAULT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_audit_status ON inventory_audits(status);

        CREATE TABLE IF NOT EXISTS audit_lines (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_id     INTEGER NOT NULL REFERENCES inventory_audits(id) ON DELETE CASCADE,
            item_id      INTEGER NOT NULL REFERENCES inventory_items(id),
            system_qty   INTEGER NOT NULL DEFAULT 0,
            counted_qty  INTEGER DEFAULT NULL,
            difference   INTEGER DEFAULT NULL,
            note         TEXT    DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_al_audit ON audit_lines(audit_id);
        CREATE INDEX IF NOT EXISTS idx_al_item  ON audit_lines(item_id);

        CREATE TABLE IF NOT EXISTS price_lists (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            description TEXT    DEFAULT '',
            is_active   INTEGER DEFAULT 1,
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS price_list_items (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            price_list_id INTEGER NOT NULL REFERENCES price_lists(id) ON DELETE CASCADE,
            item_id       INTEGER NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
            price         REAL    NOT NULL DEFAULT 0,
            UNIQUE(price_list_id, item_id)
        );
        CREATE INDEX IF NOT EXISTS idx_pli_list ON price_list_items(price_list_id);
        CREATE INDEX IF NOT EXISTS idx_pli_item ON price_list_items(item_id);
    """)
    _log.info("V11 to V12 migration completed")


def _migrate_v12_to_v13(conn: sqlite3.Connection) -> None:
    """V13: Recreate model_part_type_colors with color_name column
    (replaces old accent_color column)."""
    _log.info("Migrating database schema from V12 to V13")
    conn.execute("DROP TABLE IF EXISTS model_part_type_colors")
    conn.execute("""
        CREATE TABLE model_part_type_colors (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id     INTEGER NOT NULL REFERENCES phone_models(id) ON DELETE CASCADE,
            part_type_id INTEGER NOT NULL REFERENCES part_types(id) ON DELETE CASCADE,
            color_name   TEXT NOT NULL,
            UNIQUE(model_id, part_type_id, color_name)
        )
    """)
    _log.info("V12 to V13 migration completed")


def _migrate_v13_to_v14(conn: sqlite3.Connection) -> None:
    """V14: Performance indexes for inventory queries."""
    _log.info("Migrating database schema from V13 to V14")
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_inv_items_active
            ON inventory_items(is_active);
        CREATE INDEX IF NOT EXISTS idx_inv_items_stock
            ON inventory_items(stock);
        CREATE INDEX IF NOT EXISTS idx_inv_items_pt_id
            ON inventory_items(part_type_id);
        CREATE INDEX IF NOT EXISTS idx_inv_items_model_pt
            ON inventory_items(model_id, part_type_id);
        CREATE INDEX IF NOT EXISTS idx_inv_items_model_pt_color
            ON inventory_items(model_id, part_type_id, color);
    """)
    _log.info("V13 to V14 migration completed")


def _migrate_v14_to_v15(conn: sqlite3.Connection) -> None:
    """V15: Part-type default_price + scan_invoices / scan_invoice_items."""
    _log.info("Migrating database schema from V14 to V15")
    # Add default_price to part_types if missing
    cols = {r[1] for r in conn.execute("PRAGMA table_info(part_types)").fetchall()}
    if "default_price" not in cols:
        conn.execute("ALTER TABLE part_types ADD COLUMN default_price REAL")
    # Create invoice tables
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS scan_invoices (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number  TEXT NOT NULL UNIQUE,
            operation       TEXT NOT NULL,
            layout          TEXT NOT NULL,
            customer_name   TEXT NOT NULL DEFAULT '',
            subtotal        REAL NOT NULL DEFAULT 0,
            total           REAL NOT NULL DEFAULT 0,
            currency        TEXT NOT NULL DEFAULT '€',
            note            TEXT NOT NULL DEFAULT '',
            pdf_path        TEXT NOT NULL DEFAULT '',
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS scan_invoice_items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id      INTEGER NOT NULL REFERENCES scan_invoices(id) ON DELETE CASCADE,
            item_id         INTEGER NOT NULL REFERENCES inventory_items(id),
            item_snapshot   TEXT NOT NULL,
            barcode         TEXT NOT NULL DEFAULT '',
            quantity        INTEGER NOT NULL,
            unit_price      REAL NOT NULL,
            line_total      REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_scan_invoices_date
            ON scan_invoices(created_at);
        CREATE INDEX IF NOT EXISTS idx_scan_invoice_items_inv
            ON scan_invoice_items(invoice_id);
    """)
    _log.info("V14 to V15 migration completed")


def _migrate_v15_to_v16(conn: sqlite3.Connection) -> None:
    """V16: Add cost_price (purchase / buy price) to inventory_items.

    Hidden by default in the matrix UI and PIN-gated — used for
    cost-based valuation alongside the visible sell_price.
    """
    _log.info("Migrating database schema from V15 to V16")
    cols = {r[1] for r in conn.execute("PRAGMA table_info(inventory_items)").fetchall()}
    if "cost_price" not in cols:
        conn.execute("ALTER TABLE inventory_items ADD COLUMN cost_price REAL")
    _log.info("V15 to V16 migration completed")


def _migrate_v17_to_v18(conn: sqlite3.Connection) -> None:
    """V18: Add missing hot-path indexes.

    Performance audit (April 2026) found four queries doing full table
    scans because their predicate columns weren't indexed:
      - ``phone_models(brand)`` — every brand-filtered fetch scans 100+
        models. Used by the matrix refresh, barcode generator, model
        repo, and the part-types panel's brand filter.
      - ``part_type_colors(part_type_id)`` — colour lookups per part type
        run on every Part-Type panel selection and on every refresh of
        the colour-barcode sheet.
      - ``model_part_type_colors(model_id, part_type_id)`` — composite
        key used by ``ensure_matrix_entries`` and the matrix-exclusion
        filter we added in 2.4.4. Compound index avoids two index seeks.
      - ``inventory_transactions(item_id, timestamp DESC)`` — history /
        audit lookups for a single item; covering composite avoids a
        sort after the seek.

    All indexes are created ``IF NOT EXISTS`` so re-running the migration
    on a system that already has them (e.g. dev fixtures) is a no-op.
    """
    _log.info("Migrating database schema from V17 to V18 (add hot-path indexes)")
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_phone_models_brand
            ON phone_models(brand);
        CREATE INDEX IF NOT EXISTS idx_part_type_colors_pt
            ON part_type_colors(part_type_id);
        CREATE INDEX IF NOT EXISTS idx_mptc_model_pt
            ON model_part_type_colors(model_id, part_type_id);
        CREATE INDEX IF NOT EXISTS idx_inv_txn_item_time
            ON inventory_transactions(item_id, timestamp DESC);
        """
    )
    # Refresh SQLite's stat tables so the planner picks the new indexes.
    conn.execute("ANALYZE")
    _log.info("V17 to V18 migration completed")


def _migrate_v18_to_v19(conn: sqlite3.Connection) -> None:
    """V19: Re-canonicalise barcodes after fixing the scan-to-add bug.

    Two distinct corrections, applied in one migration so v2.5.2 ships a
    consistent DB regardless of how the existing rows were authored:

    1. **Re-strip scanner-mark prefix on rows added since V17.** V16→V17
       cleaned legacy ``f``-prefixed rows, but ``ItemRepository.add_product``
       and ``update_product`` were still storing whatever the caller
       passed in — so any item created via the scan-to-add flow since V17
       silently re-introduced the prefix bug. v2.5.2 fixes the write
       path; this migration cleans the rows that leaked through.

    2. **Substitute ``+`` → ``P``.** The K30F + YunPrint Code 128 renderer
       produces overlapping bars on the ``+`` character, so any barcode
       containing ``+`` (OnePlus brand "1+", PRO+ marker "P+", literal
       model "S10+" / "Note 14 Pro+") prints as a sticker that won't
       scan. v2.5.2 generates barcodes without ``+`` from now on; this
       migration brings existing rows into the same form so old labels
       (which encode ``+``) keep matching against canonicalised lookups
       (which substitute ``+`` → ``P``).

    Touches: ``inventory_items.barcode`` and ``app_config`` rows whose
    keys start with ``scan_cmd_`` or ``scan_clr_`` (command barcodes).
    """
    _log.info("Migrating database schema from V18 to V19 (re-canonicalise barcodes)")

    # Step 1: strip leading [a-z][A-Z0-9]... scanner-mark prefix.
    # Same heuristic as V17 — applied again because the write-path bug
    # let new rows in with the prefix.
    items_stripped = conn.execute(
        """
        UPDATE inventory_items
           SET barcode = SUBSTR(barcode, 2)
         WHERE barcode IS NOT NULL
           AND LENGTH(barcode) > 1
           AND SUBSTR(barcode, 1, 1) GLOB '[a-z]'
           AND SUBSTR(barcode, 2, 1) GLOB '[A-Z0-9]'
        """
    ).rowcount
    cfg_stripped = conn.execute(
        """
        UPDATE app_config
           SET value = SUBSTR(value, 2)
         WHERE (key LIKE 'scan_cmd_%' OR key LIKE 'scan_clr_%')
           AND value IS NOT NULL
           AND LENGTH(value) > 1
           AND SUBSTR(value, 1, 1) GLOB '[a-z]'
           AND SUBSTR(value, 2, 1) GLOB '[A-Z0-9]'
        """
    ).rowcount

    # Step 2: substitute every '+' with 'P' in stored barcodes.
    items_plus = conn.execute(
        """
        UPDATE inventory_items
           SET barcode = REPLACE(barcode, '+', 'P')
         WHERE barcode IS NOT NULL AND barcode LIKE '%+%'
        """
    ).rowcount
    cfg_plus = conn.execute(
        """
        UPDATE app_config
           SET value = REPLACE(value, '+', 'P')
         WHERE (key LIKE 'scan_cmd_%' OR key LIKE 'scan_clr_%')
           AND value IS NOT NULL AND value LIKE '%+%'
        """
    ).rowcount

    _log.info(
        "V18 to V19 migration completed (items_stripped=%s, cfg_stripped=%s, "
        "items_plus_to_P=%s, cfg_plus_to_P=%s)",
        items_stripped, cfg_stripped, items_plus, cfg_plus,
    )


def _migrate_v19_to_v20(conn: sqlite3.Connection) -> None:
    """V20: Swap Y/Z in stored barcodes (DE-keyboard QWERTZ quirk).

    Same family of bug as the V17 prefix-strip and the V19 ``+ → P``
    substitution: the DB form should match what the user's barcode
    scanner actually outputs through Windows, not what the printed
    barcode encodes. On a German-layout machine, the physical Y key
    sits in the US-Z position (and vice versa), so a scanner emitting
    HID code 0x1C (US-Y) produces the character ``Z`` through Windows.
    Pre-V20 the DB stored ``Y`` (the encoded character), so any item
    with Y or Z in its barcode — notably colour ``Yellow`` → ``YL`` —
    failed to match scanner output. Reported by the user against
    iPhone 15 / 15 Plus Yellow rows: printed sticker said ``...-YL``,
    scanner produced ``...-ZL``, lookup missed.

    Python-side translation rather than chained SQL REPLACE because
    SQLite has no built-in ``TRANSLATE`` and a Y → marker → Z → Y
    chain in pure SQL is fiddly to get right. The row count is small
    (only items with Y/Z somewhere in the barcode), so iterating in
    Python costs negligible time.
    """
    _log.info("Migrating database schema from V19 to V20 (Y/Z swap for DE keyboard)")
    swap = str.maketrans("YZyz", "ZYzy")

    rows = conn.execute(
        "SELECT id, barcode FROM inventory_items "
        "WHERE barcode IS NOT NULL "
        "AND (barcode LIKE '%Y%' OR barcode LIKE '%Z%' "
        "OR barcode LIKE '%y%' OR barcode LIKE '%z%')"
    ).fetchall()
    item_updates = [(b.translate(swap), rid) for rid, b in rows]
    conn.executemany(
        "UPDATE inventory_items SET barcode=? WHERE id=?",
        item_updates,
    )

    cfg_rows = conn.execute(
        "SELECT key, value FROM app_config "
        "WHERE (key LIKE 'scan_cmd_%' OR key LIKE 'scan_clr_%') "
        "AND value IS NOT NULL "
        "AND (value LIKE '%Y%' OR value LIKE '%Z%' "
        "OR value LIKE '%y%' OR value LIKE '%z%')"
    ).fetchall()
    cfg_updates = [(v.translate(swap), k) for k, v in cfg_rows]
    conn.executemany(
        "UPDATE app_config SET value=? WHERE key=?",
        cfg_updates,
    )

    _log.info(
        "V19 to V20 migration completed (items_swapped=%s, cfg_swapped=%s)",
        len(item_updates), len(cfg_updates),
    )


def _migrate_v20_to_v21(conn: sqlite3.Connection) -> None:
    """V21: Substitute ``/`` → ``-`` in stored barcodes.

    The user's handheld scanner runs in keyboard-wedge mode against a
    German (QWERTZ) OS layout. A scanned character is replayed as the
    US-physical-key scancode and then re-interpreted by the German layout;
    the US ``/`` key lands where German has ``-`` (bottom row, right of
    ``.``), so a printed ``/`` is received by the app as ``-`` — exactly
    like the ``-`` separator, which the German layout in turn reads as
    ``ß``.

    Combined models written "12 / 12 Pro" (one SKU that fits both iPhone
    12 and 12 Pro) and part types like "Soft/Hard OLED" therefore stored a
    payload containing ``/`` while every scan produced ``-`` in that
    position, so the barcode never matched itself and "didn't scan".

    v2.5.x generates barcodes with ``-`` instead of ``/`` from now on (see
    _make_barcode_text); this migration rewrites already-stored rows to the
    same form so labels printed before the change keep matching against
    canonicalised lookups (which also substitute ``/`` → ``-``).

    Touches: ``inventory_items.barcode`` and ``app_config`` command-barcode
    rows (keys ``scan_cmd_%`` / ``scan_clr_%``), mirroring V19's surface.
    """
    _log.info("Migrating database schema from V20 to V21 (slash to dash in barcodes)")

    items_slash = conn.execute(
        """
        UPDATE inventory_items
           SET barcode = REPLACE(barcode, '/', '-')
         WHERE barcode IS NOT NULL AND barcode LIKE '%/%'
        """
    ).rowcount
    cfg_slash = conn.execute(
        """
        UPDATE app_config
           SET value = REPLACE(value, '/', '-')
         WHERE (key LIKE 'scan_cmd_%' OR key LIKE 'scan_clr_%')
           AND value IS NOT NULL AND value LIKE '%/%'
        """
    ).rowcount

    _log.info(
        "V20 to V21 migration completed (items_slash_to_dash=%s, cfg_slash_to_dash=%s)",
        items_slash, cfg_slash,
    )


def _migrate_v21_to_v22(conn) -> None:
    """V22: Add the phones table for tracking individual phone units by IMEI."""
    _log.info("Migrating database schema from V21 to V22 (phones table)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS phones (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id    INTEGER NOT NULL REFERENCES phone_models(id) ON DELETE RESTRICT,
            imei        TEXT UNIQUE,
            storage     TEXT NOT NULL DEFAULT '',
            condition   TEXT NOT NULL DEFAULT 'used',
            battery_pct INTEGER,
            buy_price   REAL,
            sell_price  REAL,
            status      TEXT NOT NULL DEFAULT 'in_stock',
            notes       TEXT NOT NULL DEFAULT '',
            created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_phones_model  ON phones(model_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_phones_status ON phones(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_phones_imei   ON phones(imei)")
    _log.info("V21 to V22 migration completed")


def _migrate_v22_to_v23(conn) -> None:
    """V23: Add phone_transactions audit log for phone unit history."""
    _log.info("Migrating database schema from V22 to V23 (phone_transactions table)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS phone_transactions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_id      INTEGER NOT NULL,
            operation     TEXT NOT NULL,
            status_before TEXT NOT NULL DEFAULT '',
            status_after  TEXT NOT NULL DEFAULT '',
            imei          TEXT NOT NULL DEFAULT '',
            model_brand   TEXT NOT NULL DEFAULT '',
            model_name    TEXT NOT NULL DEFAULT '',
            storage       TEXT NOT NULL DEFAULT '',
            sell_price    REAL,
            note          TEXT NOT NULL DEFAULT '',
            timestamp     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_phone_tx_phone ON phone_transactions(phone_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_phone_tx_op    ON phone_transactions(operation)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_phone_tx_ts    ON phone_transactions(timestamp)")
    _log.info("V22 to V23 migration completed")


def _migrate_v16_to_v17(conn: sqlite3.Connection) -> None:
    """V17: Drop the scanner-mark prefix from saved barcodes.

    Pre-V17 the system hardcoded a leading ``f`` on every saved barcode
    because that's the prefix the original developer's German-keyboard
    scanner emitted. Real-world testing on the K30F + YunPrint combo
    revealed scanners can emit a different lowercase letter (``a`` was
    observed) depending on the renderer / firmware, breaking lookups
    against the ``f``-prefixed DB rows. Going forward the DB stores
    barcodes in their canonical (prefix-less) form and the lookup paths
    strip whatever lowercase prefix the scanner happens to emit before
    matching. This migration brings existing rows into that canonical form.

    Touches:
      - inventory_items.barcode
      - app_config.value where key starts with scan_cmd_ or scan_clr_

    Heuristic: a leading ASCII a-z followed by an uppercase letter or
    digit is always a scanner-mark, never part of the payload (canonical
    barcodes start with a brand letter or digit, never lowercase).
    """
    _log.info("Migrating database schema from V16 to V17 (strip scanner-mark prefix)")
    items_updated = conn.execute(
        """
        UPDATE inventory_items
           SET barcode = SUBSTR(barcode, 2)
         WHERE barcode IS NOT NULL
           AND LENGTH(barcode) > 1
           AND SUBSTR(barcode, 1, 1) GLOB '[a-z]'
           AND SUBSTR(barcode, 2, 1) GLOB '[A-Z0-9]'
        """
    ).rowcount
    cfg_updated = conn.execute(
        """
        UPDATE app_config
           SET value = SUBSTR(value, 2)
         WHERE (key LIKE 'scan_cmd_%' OR key LIKE 'scan_clr_%')
           AND value IS NOT NULL
           AND LENGTH(value) > 1
           AND SUBSTR(value, 1, 1) GLOB '[a-z]'
           AND SUBSTR(value, 2, 1) GLOB '[A-Z0-9]'
        """
    ).rowcount
    _log.info(
        "V16 to V17 migration completed (items_stripped=%s, scan_cfg_stripped=%s)",
        items_updated, cfg_updated,
    )


def _migrate_v3_to_v4(conn: sqlite3.Connection) -> None:
    """Consolidate products + stock_entries into inventory_items."""
    _log.info("Migrating database schema from V3 to V4 (consolidate products + stock_entries)")
    # 1. Products → inventory_items (preserve IDs so product_id refs stay valid)
    conn.execute("""
        INSERT OR IGNORE INTO inventory_items
            (id, brand, name, color, barcode, stock, min_stock, created_at, updated_at)
        SELECT id, brand, type, color, barcode, stock, low_stock_threshold,
               created_at, updated_at
        FROM products
    """)
    _log.debug("V3->V4: Migrated products to inventory_items")

    # 2. stock_entries → inventory_items (new IDs, build a mapping for transaction migration)
    conn.execute("CREATE TEMP TABLE _se_map (old_id INTEGER, new_id INTEGER)")
    entries = conn.execute("SELECT * FROM stock_entries").fetchall()
    for e in entries:
        conn.execute("""
            INSERT OR IGNORE INTO inventory_items
                (model_id, part_type_id, stock, min_stock, inventur, updated_at)
            VALUES (?,?,?,?,?,?)
        """, (e["model_id"], e["part_type_id"], e["stock"],
              e["stamm_zahl"], e["inventur"], e["updated_at"]))
        row = conn.execute(
            "SELECT id FROM inventory_items WHERE model_id=? AND part_type_id=?",
            (e["model_id"], e["part_type_id"]),
        ).fetchone()
        if row:
            conn.execute("INSERT INTO _se_map VALUES (?,?)", (e["id"], row["id"]))

    # 3. product_transactions → inventory_transactions
    conn.execute("""
        INSERT OR IGNORE INTO inventory_transactions
            (item_id, operation, quantity, stock_before, stock_after, note, timestamp)
        SELECT product_id, operation, quantity, stock_before, stock_after, note, timestamp
        FROM product_transactions
    """)

    # 4. stock_transactions → inventory_transactions (remap entry_id via mapping table)
    txns = conn.execute("SELECT * FROM stock_transactions").fetchall()
    for tx in txns:
        mapping = conn.execute(
            "SELECT new_id FROM _se_map WHERE old_id=?", (tx["entry_id"],)
        ).fetchone()
        if mapping:
            conn.execute("""
                INSERT INTO inventory_transactions
                    (item_id, operation, quantity, stock_before, stock_after, note, timestamp)
                VALUES (?,?,?,?,?,?,?)
            """, (mapping["new_id"], tx["operation"], tx["quantity"],
                  tx["stock_before"], tx["stock_after"], tx["note"], tx["timestamp"]))

    conn.execute("DROP TABLE _se_map")
    _log.info("V3 to V4 migration completed")


# ── V1 → V2 migration helpers ─────────────────────────────────────────────────

def _has_table(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return bool(row and row[0])


def _migrate_v1_display_stock(conn: sqlite3.Connection) -> None:
    """Copy v1 display_stock rows into the new stock_entries table."""
    if not _has_table(conn, "display_stock"):
        return

    # Build display_type_key → part_type_id mapping
    pt_rows = conn.execute(
        "SELECT pt.id, pt.key FROM part_types pt "
        "JOIN categories c ON c.id = pt.category_id WHERE c.key = 'displays'"
    ).fetchall()
    key_to_pt_id = {r["key"]: r["id"] for r in pt_rows}

    # Build old model name → new model id mapping
    old_models = conn.execute("SELECT id, name FROM phone_models").fetchall()
    name_to_id = {r["name"]: r["id"] for r in old_models}

    rows = conn.execute(
        "SELECT model_id, display_type, stamm_zahl, stock, inventur FROM display_stock"
    ).fetchall()

    for row in rows:
        model_id   = row["model_id"]
        pt_id      = key_to_pt_id.get(row["display_type"])
        if pt_id is None:
            continue
        conn.execute(
            """INSERT OR IGNORE INTO stock_entries
               (model_id, part_type_id, stamm_zahl, stock, inventur)
               VALUES (?, ?, ?, ?, ?)""",
            (model_id, pt_id, row["stamm_zahl"], row["stock"], row["inventur"]),
        )


def _migrate_v1_transactions(conn: sqlite3.Connection) -> None:
    """Copy v1 transactions table into product_transactions."""
    if not _has_table(conn, "transactions"):
        return
    if not _has_table(conn, "product_transactions"):
        return
    existing = conn.execute("SELECT COUNT(*) FROM product_transactions").fetchone()[0]
    if existing > 0:
        return  # already migrated
    conn.execute("""
        INSERT OR IGNORE INTO product_transactions
            (id, product_id, operation, quantity, stock_before, stock_after, note, timestamp)
        SELECT id, product_id, operation, quantity, stock_before, stock_after, note, timestamp
        FROM transactions
    """)


# ── Public init ───────────────────────────────────────────────────────────────

def _ensure_columns(conn) -> None:
    """Idempotently add migration-introduced columns that may be missing on a
    DB whose schema_version already says they should exist — e.g. a database
    created directly from _DDL (a fresh cloud DB, or an inconsistent local one)
    rather than walking the migration chain. Cheap and safe to run on every
    startup — including over the Turso HTTP connection, where PRAGMA returns
    nothing, so we attempt the ALTER directly and ignore the 'duplicate column'
    error that means the column was already present."""
    ensure = {
        "inventory_items": [("cost_price", "REAL")],
    }
    for table, columns in ensure.items():
        try:
            existing = {r[1] for r in conn.execute(
                f"PRAGMA table_info({table})").fetchall()}
        except Exception:
            existing = set()
        for col, decl in columns:
            if existing and col in existing:
                continue  # introspected and already present
            # Either the column is missing, or we couldn't introspect (Turso
            # HTTP ignores PRAGMA). Attempt the ALTER; ignore the benign
            # "duplicate column" error that means it already exists.
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
                _log.info("Ensured %s.%s column", table, col)
            except Exception as exc:
                m = str(exc).lower()
                if "duplicate column" not in m and "already exists" not in m:
                    _log.warning("Could not add %s.%s: %s", table, col, exc)


def init_db() -> None:
    """Create schema, run migrations, seed reference data."""
    _log.info("Initializing database")
    with get_connection() as conn:
        _executescript(conn, _DDL)
        _ensure_columns(conn)

        # Detect schema version
        version = conn.execute(
            "SELECT value FROM app_config WHERE key='schema_version'"
        ).fetchone()
        is_fresh = version is None

        if is_fresh:
            _log.info("Database is fresh, initializing new schema")
            # Check if this is a v1 upgrade or truly fresh
            is_v1_upgrade = _has_table(conn, "display_stock")

            if is_v1_upgrade:
                # V1 upgrade: migrate existing data into v2 schema
                from app.core.demo_data import (
                    DEMO_CATEGORIES, DEMO_PART_TYPES,
                )
                # Seed categories and part types (needed for migration mapping)
                conn.executemany(
                    """INSERT OR IGNORE INTO categories
                       (key, name_en, name_de, name_ar, sort_order, icon)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    DEMO_CATEGORIES,
                )
                cat_rows = conn.execute("SELECT id, key FROM categories").fetchall()
                cat_key_to_id = {r["key"]: r["id"] for r in cat_rows}
                for cat_key, parts in DEMO_PART_TYPES.items():
                    cat_id = cat_key_to_id.get(cat_key)
                    if cat_id is None:
                        continue
                    conn.executemany(
                        """INSERT OR IGNORE INTO part_types
                           (category_id, key, name, accent_color, sort_order)
                           VALUES (?, ?, ?, ?, ?)""",
                        [(cat_id, k, n, c, s) for k, n, c, s in parts],
                    )
                # Migrate existing phone_models brand column if needed
                cols = {r[1] for r in conn.execute("PRAGMA table_info(phone_models)").fetchall()}
                if "brand" not in cols:
                    conn.execute(
                        "ALTER TABLE phone_models ADD COLUMN brand TEXT NOT NULL DEFAULT 'Apple'"
                    )
                _migrate_v1_display_stock(conn)
                _migrate_v1_transactions(conn)
                # Mark setup as complete for V1 upgrades
                conn.execute(
                    "INSERT OR IGNORE INTO app_config (key, value) VALUES ('setup_complete', '1')"
                )
            # Fresh installs: no seed data — setup wizard will handle it

            conn.execute(
                "INSERT OR REPLACE INTO app_config (key, value) VALUES ('schema_version', ?)",
                (_SCHEMA_VERSION,),
            )

        # Incremental migrations for existing installs
        if not is_fresh:
            ver_row = conn.execute(
                "SELECT value FROM app_config WHERE key='schema_version'"
            ).fetchone()
            current = ver_row["value"] if ver_row else "1"
            _log.info(f"Current schema version: {current}, target: {_SCHEMA_VERSION}")

            if current == "2":
                _migrate_v2_to_v3(conn)
                current = "3"

            if current == "3":
                _migrate_v3_to_v4(conn)
                current = "4"

            if current == "4":
                _migrate_v4_to_v5(conn)
                current = "5"

            if current == "5":
                _migrate_v5_to_v6(conn)
                current = "6"

            if current == "6":
                _migrate_v6_to_v7(conn)
                current = "7"

            if current == "7":
                _migrate_v7_to_v8(conn)
                current = "8"

            if current == "8":
                _migrate_v8_to_v9(conn)
                current = "9"

            if current == "9":
                _migrate_v9_to_v10(conn)
                current = "10"

            if current == "10":
                _migrate_v10_to_v11(conn)
                current = "11"

            if current == "11":
                _migrate_v11_to_v12(conn)
                current = "12"

            if current == "12":
                _migrate_v12_to_v13(conn)
                current = "13"

            if current == "13":
                _migrate_v13_to_v14(conn)
                current = "14"

            if current == "14":
                _migrate_v14_to_v15(conn)
                current = "15"

            if current == "15":
                _migrate_v15_to_v16(conn)
                current = "16"

            if current == "16":
                _migrate_v16_to_v17(conn)
                current = "17"

            if current == "17":
                _migrate_v17_to_v18(conn)
                current = "18"

            if current == "18":
                _migrate_v18_to_v19(conn)
                current = "19"

            if current == "19":
                _migrate_v19_to_v20(conn)
                current = "20"

            if current == "20":
                _migrate_v20_to_v21(conn)
                current = "21"

            if current == "21":
                _migrate_v21_to_v22(conn)
                current = "22"

            if current == "22":
                _migrate_v22_to_v23(conn)
                current = "23"

            # Always persist the final version after migrations
            conn.execute(
                "INSERT OR REPLACE INTO app_config (key, value) VALUES ('schema_version', ?)",
                (current,),
            )

        # Ensure all (model × part_type) entries exist so matrix is fully populated
        _ensure_all_entries(conn)
        _log.info("Database initialization complete")


def load_demo_data() -> None:
    """
    Seed the Galaxy@Phone demo data.
    Safe to call multiple times — uses INSERT OR IGNORE.
    Display part types are brand-specific (Apple has 5 types, Samsung has 2).
    """
    from app.core.demo_data import (
        DEMO_CATEGORIES, DEMO_PART_TYPES, DEMO_PHONE_MODELS, DISPLAY_BRAND_MAP,
        DEMO_PART_TYPE_COLORS,
    )
    with get_connection() as conn:
        conn.executemany(
            """INSERT OR IGNORE INTO categories
               (key, name_en, name_de, name_ar, sort_order, icon)
               VALUES (?,?,?,?,?,?)""",
            DEMO_CATEGORIES,
        )
        cat_rows = conn.execute("SELECT id, key FROM categories").fetchall()
        cat_key_to_id = {r["key"]: r["id"] for r in cat_rows}
        for cat_key, parts in DEMO_PART_TYPES.items():
            cat_id = cat_key_to_id.get(cat_key)
            if cat_id is None:
                continue
            conn.executemany(
                """INSERT OR IGNORE INTO part_types
                   (category_id, key, name, accent_color, sort_order)
                   VALUES (?,?,?,?,?)""",
                [(cat_id, k, n, c, s) for k, n, c, s in parts],
            )
        conn.executemany(
            "INSERT OR IGNORE INTO phone_models (brand, name, sort_order) VALUES (?,?,?)",
            DEMO_PHONE_MODELS,
        )

        # Seed part type colors
        pt_rows_all = conn.execute("SELECT id, key FROM part_types").fetchall()
        pt_key_to_id_all = {r["key"]: r["id"] for r in pt_rows_all}
        for pt_key, colors in DEMO_PART_TYPE_COLORS.items():
            pt_id = pt_key_to_id_all.get(pt_key)
            if pt_id:
                for color_name, color_code, sort_order in colors:
                    conn.execute(
                        "INSERT OR IGNORE INTO part_type_colors (part_type_id, color_name, color_code, sort_order) VALUES (?,?,?,?)",
                        (pt_id, color_name, color_code, sort_order),
                    )

        # Brand-aware matrix entries for displays
        # Delete wrong brand × display combos (e.g., Samsung + JK incell)
        displays_cat_id = cat_key_to_id.get("displays")
        if displays_cat_id:
            # Get all display part types with their keys
            pt_rows = conn.execute(
                "SELECT id, key FROM part_types WHERE category_id=?",
                (displays_cat_id,),
            ).fetchall()
            pt_key_to_id = {r["key"]: r["id"] for r in pt_rows}

            # Get all models with their brands
            models = conn.execute("SELECT id, brand FROM phone_models").fetchall()

            # Clean up: delete display entries where brand doesn't match
            for model in models:
                brand = model["brand"]
                allowed_keys = DISPLAY_BRAND_MAP.get(brand, [])
                disallowed_pt_ids = [pt_key_to_id[k] for k in pt_key_to_id if k not in allowed_keys]
                if disallowed_pt_ids:
                    placeholders = ",".join("?" * len(disallowed_pt_ids))
                    # Only delete if stock is 0 (don't lose actual data)
                    conn.execute(
                        f"DELETE FROM inventory_items WHERE model_id=? AND part_type_id IN ({placeholders}) "
                        f"AND (stock IS NULL OR stock = 0) AND (min_stock IS NULL OR min_stock = 0)",
                        [model["id"]] + disallowed_pt_ids,
                    )

            # Create display entries only for matching brands
            for model in models:
                brand = model["brand"]
                allowed_keys = DISPLAY_BRAND_MAP.get(brand, [])
                for pt_key in allowed_keys:
                    pt_id = pt_key_to_id.get(pt_key)
                    if pt_id:
                        conn.execute(
                            "INSERT OR IGNORE INTO inventory_items (model_id, part_type_id) VALUES (?,?)",
                            (model["id"], pt_id),
                        )

            # For non-display categories, create all model × part_type entries
            non_display_pts = conn.execute(
                "SELECT id FROM part_types WHERE category_id != ?",
                (displays_cat_id,),
            ).fetchall()
            for model in models:
                for pt in non_display_pts:
                    conn.execute(
                        "INSERT OR IGNORE INTO inventory_items (model_id, part_type_id) VALUES (?,?)",
                        (model["id"], pt["id"]),
                    )
        else:
            # No displays category — use default ensure_all
            _ensure_all_entries(conn)


def _matrix_fingerprint(conn: sqlite3.Connection) -> str:
    """Hash the inputs ``_ensure_all_entries`` consumes — when this string
    is unchanged since the last successful run we can skip the work
    entirely. Counts + max(updated_at) over each contributing table covers
    every realistic mutation path (model add/rename, part-type add/edit,
    colour add/remove, per-model colour override toggle). Reading these
    counters is a single-digit-millisecond aggregate query against the
    indexes we already maintain, so the check itself is essentially free.
    """
    parts: list[str] = []
    for tbl in ("phone_models", "part_types", "part_type_colors",
                "model_part_type_colors", "categories"):
        try:
            row = conn.execute(
                f"SELECT COUNT(*), COALESCE(MAX(updated_at), '') FROM {tbl}"
            ).fetchone()
            parts.append(f"{row[0]}:{row[1]}")
        except sqlite3.OperationalError:
            # Table without an updated_at column — fall back to count only
            row = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()
            parts.append(str(row[0]))
    return "|".join(parts)


def _ensure_all_entries(conn: sqlite3.Connection) -> None:
    """Insert missing inventory_items rows, respecting brand-specific display rules.

    Idempotent fast-path: if the input tables (models / part_types /
    colours / overrides) haven't changed since the last successful run,
    skip the full scan entirely. The legacy code re-walked every
    (model × part_type × colour) combination on every startup and every
    admin-dialog close, then issued an `INSERT OR IGNORE` for ~3000
    tuples that all already existed — SQLite still pays the constraint
    check per tuple, which costs ~75ms of pure waste per call. Skipping
    via fingerprint drops that to a single digit millisecond aggregate
    query when nothing actually changed.
    """
    try:
        from app.core.demo_data import DISPLAY_BRAND_MAP, DISPLAY_EXCLUSIONS
    except ImportError:
        DISPLAY_BRAND_MAP = {}
        DISPLAY_EXCLUSIONS = {}

    fingerprint = _matrix_fingerprint(conn)
    cached_row = conn.execute(
        "SELECT value FROM app_config WHERE key='matrix_fingerprint'"
    ).fetchone()
    if cached_row and cached_row[0] == fingerprint:
        # Nothing changed since last successful ensure_all_entries — skip.
        # Saves ~200-300ms on every app startup and every admin-save where
        # the user didn't actually change models/part-types/colours.
        return

    models = conn.execute("SELECT id, brand, name FROM phone_models").fetchall()

    # Find the displays category
    displays_row = conn.execute(
        "SELECT id FROM categories WHERE key='displays'"
    ).fetchone()
    displays_cat_id = displays_row["id"] if displays_row else None

    # Build display part type key→id map
    display_pt_map: dict[str, int] = {}
    display_pt_ids: set[int] = set()
    if displays_cat_id:
        for r in conn.execute(
            "SELECT id, key FROM part_types WHERE category_id=?",
            (displays_cat_id,),
        ).fetchall():
            display_pt_map[r["key"]] = r["id"]
            display_pt_ids.add(r["id"])

    # Load colors per part type from part_type_colors table (global defaults)
    pt_colors: dict[int, list[str]] = {}  # pt_id → [color_name, ...]
    try:
        for r in conn.execute("SELECT part_type_id, color_name FROM part_type_colors ORDER BY sort_order").fetchall():
            pt_colors.setdefault(r["part_type_id"], []).append(r["color_name"])
    except Exception:
        pass  # table might not exist yet during initial schema creation

    # Load per-model color overrides: (model_id, pt_id) → [color_name, ...]
    model_pt_colors: dict[tuple[int, int], list[str]] = {}
    try:
        for r in conn.execute("SELECT model_id, part_type_id, color_name FROM model_part_type_colors").fetchall():
            model_pt_colors.setdefault((r["model_id"], r["part_type_id"]), []).append(r["color_name"])
    except Exception:
        pass

    # Collect all inserts into a batch list for executemany()
    _batch_inserts: list[tuple[int, int, str]] = []
    # Collect per-row DELETEs into a single batched IN clause at the end —
    # a 100-model × 15-PT inventory used to issue thousands of individual
    # DELETEs from inside the loop; one IN-clause statement is dramatically
    # faster (~10-30x on a cold cache) and keeps the function under one
    # implicit transaction so partial state can't be observed by concurrent
    # readers.
    _batch_delete_ids: list[int] = []

    # Pre-fetch every "stale colour" candidate in one query, grouped by
    # (model_id, part_type_id), instead of one SELECT per (mid, pt_id) call
    # inside _queue_item. This eliminates N small SELECTs (one per non-
    # excluded combo) that the legacy code issued from the per-row hot path.
    _stale_color_rows: dict[tuple[int, int], list[tuple[int, str]]] = {}
    try:
        for r in conn.execute(
            "SELECT id, model_id, part_type_id, color FROM inventory_items "
            "WHERE color != '' AND stock=0 AND min_stock=0 "
            "AND (inventur IS NULL OR inventur=0)"
        ).fetchall():
            _stale_color_rows.setdefault(
                (r["model_id"], r["part_type_id"]), []
            ).append((r["id"], r["color"]))
    except Exception:
        pass

    def _queue_item(mid: int, pt_id: int):
        """Queue inventory items for batch insert."""
        override = model_pt_colors.get((mid, pt_id))
        # "__EXCLUDED__" means this model does not have this part type at all
        if override and "__EXCLUDED__" in override:
            return  # skip completely, don't create any rows
        # "__NONE__" marker means explicitly no colors for this model
        if override and "__NONE__" in override:
            _batch_inserts.append((mid, pt_id, ""))  # only colorless parent
            return
        # "__USER_INCLUDED__" is a protection marker — the user manually
        # toggled the model into this part type, so we must include the
        # default colorless parent row and let global colors apply.
        if override and "__USER_INCLUDED__" in override:
            _batch_inserts.append((mid, pt_id, ""))
            for color in pt_colors.get(pt_id, []):
                _batch_inserts.append((mid, pt_id, color))
            return
        colors = override if override is not None else pt_colors.get(pt_id, [])
        if colors:
            color_set = set(colors)
            for color in colors:
                _batch_inserts.append((mid, pt_id, color))
            _batch_inserts.append((mid, pt_id, ""))  # colorless parent row
            # Queue zero-stock rows for colors NOT in the active set into
            # the batched delete list (executed once at the end of the
            # function instead of per-row from inside this hot path).
            for row_id, row_color in _stale_color_rows.get((mid, pt_id), ()):
                if row_color not in color_set:
                    _batch_delete_ids.append(row_id)
        else:
            _batch_inserts.append((mid, pt_id, ""))

    # All non-display part types
    all_pts = conn.execute("SELECT id FROM part_types").fetchall()
    non_display_pt_ids = [r["id"] for r in all_pts if r["id"] not in display_pt_ids]

    for model in models:
        brand = model["brand"]
        model_name = model["name"]
        mid = model["id"]

        # Non-display part types: create for ALL models
        for pt_id in non_display_pt_ids:
            _queue_item(mid, pt_id)

        # Display part types: brand-aware + model-specific exclusions.
        # CRITICAL: hardcoded DISPLAY_EXCLUSIONS are ONLY applied when the
        # user has not manually overridden that (model, part_type) pair.
        # Any row in model_part_type_colors (including __USER_INCLUDED__,
        # __EXCLUDED__, __NONE__, or explicit colors) signals user intent
        # and must be respected over the demo-data defaults.
        if DISPLAY_BRAND_MAP and display_pt_map:
            allowed_keys = DISPLAY_BRAND_MAP.get(brand)
            if allowed_keys is not None:
                for key in allowed_keys:
                    pt_id = display_pt_map.get(key)
                    excluded_models = DISPLAY_EXCLUSIONS.get(key, [])
                    user_override = None
                    if pt_id:
                        user_override = model_pt_colors.get((mid, pt_id))
                    if model_name in excluded_models and not user_override:
                        # Demo-data exclusion AND user hasn't touched this —
                        # delete zero-stock rows to keep the matrix clean
                        if pt_id:
                            conn.execute(
                                "DELETE FROM inventory_items WHERE model_id=? AND part_type_id=? "
                                "AND (stock IS NULL OR stock=0) AND (min_stock IS NULL OR min_stock=0)",
                                (mid, pt_id),
                            )
                        continue
                    # User override OR not in exclusion list → materialise rows
                    if pt_id:
                        _queue_item(mid, pt_id)
            else:
                for pt_id in display_pt_ids:
                    _queue_item(mid, pt_id)
        else:
            for pt_id in display_pt_ids:
                _batch_inserts.append((mid, pt_id, ""))

    # Execute all queued inserts in a single batch (10-50x faster than individual INSERTs)
    if _batch_inserts:
        conn.executemany(
            "INSERT OR IGNORE INTO inventory_items (model_id, part_type_id, color) VALUES (?,?,?)",
            _batch_inserts,
        )

    # Flush the queued stale-colour DELETEs as one IN-clause statement.
    # Chunked at 500 IDs per statement to stay well clear of SQLite's
    # default 999-parameter limit (SQLITE_MAX_VARIABLE_NUMBER).
    if _batch_delete_ids:
        for i in range(0, len(_batch_delete_ids), 500):
            chunk = _batch_delete_ids[i:i + 500]
            placeholders = ",".join("?" * len(chunk))
            conn.execute(
                f"DELETE FROM inventory_items WHERE id IN ({placeholders})",
                chunk,
            )

    # Clean up stale inventory items: remove display items for brands that
    # shouldn't have them (e.g. Samsung models with Apple-only part types).
    # Only deletes zero-stock rows to avoid data loss, and ONLY when the
    # user has NOT explicitly managed that (model, part_type) pair —
    # any row in model_part_type_colors signals user intent to keep.
    # Per-(model, pt_id) DELETEs are collected here and executed via
    # ``executemany`` once at the end so the disk hits one fsync instead
    # of N (where N could exceed 1000 on a busy install).
    if DISPLAY_BRAND_MAP and display_pt_map:
        _cleanup_pairs: list[tuple[int, int]] = []
        for model in models:
            brand = model["brand"]
            mid = model["id"]
            allowed_keys = DISPLAY_BRAND_MAP.get(brand)
            if allowed_keys is None:
                continue
            allowed_pt_ids = {display_pt_map[k] for k in allowed_keys if k in display_pt_map}
            disallowed_pt_ids = display_pt_ids - allowed_pt_ids
            for pt_id in disallowed_pt_ids:
                # Skip if the user has toggled this pair in any way
                # (__USER_INCLUDED__, __EXCLUDED__, __NONE__, explicit colors)
                if model_pt_colors.get((mid, pt_id)):
                    continue
                _cleanup_pairs.append((mid, pt_id))
        if _cleanup_pairs:
            conn.executemany(
                "DELETE FROM inventory_items "
                "WHERE model_id=? AND part_type_id=? "
                "AND stock=0 AND min_stock=0 "
                "AND (inventur IS NULL OR inventur=0)",
                _cleanup_pairs,
            )

    # Cache the fingerprint we just satisfied so the next call can take
    # the fast-path skip if the inputs haven't changed.
    conn.execute(
        "INSERT OR REPLACE INTO app_config (key, value) "
        "VALUES ('matrix_fingerprint', ?)",
        (fingerprint,),
    )


def ensure_matrix_entries() -> None:
    """Public helper — call after adding new models or part types via admin UI."""
    with get_connection() as conn:
        _ensure_all_entries(conn)
