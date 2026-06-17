"""seed_voltedge.py — Populate a fresh DB with VoltEdge Electronics demo data.

Run from the project root:
    cd src/files && python seed_voltedge.py

Creates a complete, internally-consistent dataset for professional screenshots.
Backs up any existing DB first (stock_manager.db.pre-voltedge.bak).
"""
from __future__ import annotations

import os
import sys
import random
from datetime import datetime, timedelta

# Windows consoles default to cp1252, which can't encode the €/→/— glyphs in
# this script's progress output. Force UTF-8 so the run doesn't crash on print.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import app.core.database as db  # noqa: E402 — must import before any service

DB_FILE = db.DB_PATH
RNG = random.Random(20260616)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _round99(value: float) -> float:
    """Convert a raw price float to the nearest X.99 retail price."""
    return max(0.99, round(value) - 0.01)


def _ts(days_ago: float, hour: int = 10, minute: int = 0) -> str:
    dt = datetime.now() - timedelta(days=days_ago,
                                    hours=-(hour - 10),
                                    minutes=minute)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# ── Category pricing parameters ───────────────────────────────────────────────

CATEGORY_PARAMS: dict[str, dict] = {
    "displays":       {"price": (28.0, 96.0),  "cost_ratio": (0.45, 0.60), "min_stock": 5},
    "batteries":      {"price": (8.0,  20.0),  "cost_ratio": (0.40, 0.55), "min_stock": 8},
    "cases":          {"price": (4.0,  16.0),  "cost_ratio": (0.35, 0.50), "min_stock": 10},
    "cameras":        {"price": (9.0,  30.0),  "cost_ratio": (0.40, 0.58), "min_stock": 4},
    "charging_ports": {"price": (5.0,  14.0),  "cost_ratio": (0.38, 0.55), "min_stock": 6},
    "back_covers":    {"price": (8.0,  24.0),  "cost_ratio": (0.38, 0.55), "min_stock": 6},
    "screen_protectors": {"price": (3.0, 12.0),  "cost_ratio": (0.30, 0.45), "min_stock": 15},
    "audio":          {"price": (15.0, 250.0), "cost_ratio": (0.45, 0.58), "min_stock": 3},
    "wearables":      {"price": (25.0, 800.0), "cost_ratio": (0.50, 0.65), "min_stock": 2},
    "storage":        {"price": (8.0,  140.0), "cost_ratio": (0.35, 0.52), "min_stock": 8},
    "power_banks":    {"price": (15.0, 55.0),  "cost_ratio": (0.40, 0.55), "min_stock": 5},
    "smart_home":     {"price": (25.0, 130.0), "cost_ratio": (0.40, 0.55), "min_stock": 3},
    "mounts":         {"price": (12.0, 90.0),  "cost_ratio": (0.38, 0.52), "min_stock": 5},
    "repair_tools":   {"price": (5.0,  70.0),  "cost_ratio": (0.40, 0.55), "min_stock": 3},
    "gaming":         {"price": (30.0, 200.0), "cost_ratio": (0.42, 0.58), "min_stock": 3},
    "network":        {"price": (80.0, 200.0), "cost_ratio": (0.45, 0.58), "min_stock": 2},
    "cables":         {"price": (5.0,  50.0),  "cost_ratio": (0.30, 0.45), "min_stock": 12},
    "adapters":       {"price": (8.0,  80.0),  "cost_ratio": (0.35, 0.50), "min_stock": 6},
}

SUPPLIER_BY_CATEGORY: dict[str, str] = {
    "displays":       "ScreenSource EU",
    "batteries":      "PowerCell Distribution",
    "cases":          "CaseCraft Supplies",
    "cameras":        "MobileParts Direct",
    "charging_ports": "MobileParts Direct",
    "back_covers":    "CaseCraft Supplies",
    "screen_protectors": "CaseCraft Supplies",
    "audio":          "AudioMax Wholesale",
    "wearables":      "WearTech Distribution",
    "storage":        "TechDistro GmbH",
    "power_banks":    "TechDistro GmbH",
    "smart_home":     "TechDistro GmbH",
    "mounts":         "TechDistro GmbH",
    "repair_tools":   "MobileParts Direct",
    "gaming":         "AudioMax Wholesale",
    "network":        "TechDistro GmbH",
    "cables":         "TechDistro GmbH",
    "adapters":       "TechDistro GmbH",
}


# ── Multi-Location Setup ────────────────────────────────────────────────────────

LOCATIONS = [
    ("Main Warehouse", "Primary storage location - central distribution hub", True),
    ("Retail Store Front", "Customer-facing stock - high visibility items", False),
    ("Repair Workshop", "Technician access stock - frequently used parts", False),
    ("Backup Storage", "Overflow/backup stock - slow-moving items", False),
]


# ── Customer Segmentation ───────────────────────────────────────────────────────

CUSTOMER_SEGMENTS = {
    "VIP_B2B": {"discount": 0.15, "payment_terms": "NET30", "min_order": 500},
    "Regular": {"discount": 0.0, "payment_terms": "COD", "min_order": 0},
    "Walk-in": {"discount": 0.0, "payment_terms": "Cash", "min_order": 0},
}


# ── Extended Part Types for Matrix Stock ─────────────────────────────────────

PART_TYPES: dict[str, list[tuple[str, str, str, int]]] = {
    "displays": [
        ("JK_INCELL_FHD",     "(JK) incell FHD",          "#4A9EFF", 1),
        ("DD_SOFT_OLED",      "(D.D) Soft-OLED",           "#32D583", 2),
        ("DD_SOFT_OLED_DIAG", "(D.D) Soft-OLED Diagnose",  "#C17BFF", 3),
        ("ORG_PULLED",        "ORG-Pulled",                "#FF9F3A", 4),
        ("ORG_DIAGNOSE_USED", "ORG-Diagnose USED",         "#FF5A52", 5),
        ("SM_ORG_SERVICE",    "ORG Service Pack",          "#10B981", 6),
        ("SM_OLED",           "OLED",                      "#3B82F6", 7),
        ("COPY_INCELL",       "Copy incell",               "#6B7280", 8),
        ("REFURBISHED",       "Refurbished OEM",           "#F59E0B", 9),
        ("AFTERMARKET_LCD",   "Aftermarket LCD",           "#8B5CF6", 10),
    ],
    "batteries": [
        ("ORG_AKKU",        "Org Akku",        "#32D583", 1),
        ("ORG_AKKU_DECODE", "Org Akku Decode", "#4A9EFF", 2),
        ("COPY_AKKU",       "Copy Akku",       "#6B7280", 3),
        ("REFURB_BATTERY",  "Refurbished Battery", "#F59E0B", 4),
        ("HIGH_CAPACITY",   "High Capacity",   "#10B981", 5),
    ],
    "cases": [
        ("BLACK",    "Black",    "#555555", 1),
        ("GOLD",     "Gold",     "#FFD700", 2),
        ("BLUE",     "Blue",     "#4A9EFF", 3),
        ("TITANIUM", "Titanium", "#A0A8B0", 4),
        ("PURPLE",   "Purple",   "#C17BFF", 5),
        ("WHITE",    "White",    "#D0D0D0", 6),
        ("SILVER",   "Silver",   "#C0C0C0", 7),
        ("ROSE_GOLD", "Rose Gold", "#B76E79", 8),
        ("MIDNIGHT_GREEN", "Midnight Green", "#1A3A3A", 9),
        ("PRODUCT_RED", "Product Red", "#FF3B30", 10),
    ],
    "cameras": [
        ("BACK_CAMERA",      "ORG-Back Camera",      "#32D583", 1),
        ("ORG_FULL_BCAMERA", "ORG-full Back Camera", "#FF9F3A", 2),
        ("FRONT_CAMERA",     "Front Camera",         "#4A9EFF", 3),
        ("ORG_FRONT_CAM",   "ORG Front Camera",     "#10B981", 4),
        ("TELEPHOTO_CAM",   "Telephoto Camera",     "#C17BFF", 5),
        ("ULTRA_WIDE_CAM",  "Ultra Wide Camera",     "#F59E0B", 6),
        ("COPY_CAMERA",     "Copy Camera",          "#6B7280", 7),
    ],
    "charging_ports": [
        ("LADEBUCHSE", "Ladebuchse", "#4A9EFF", 1),
        ("USB_C_PORT", "USB-C Port", "#10B981", 2),
        ("LIGHTNING_PORT", "Lightning Port", "#32D583", 3),
        ("WIRELESS_COIL", "Wireless Coil", "#C17BFF", 4),
        ("FLEX_CABLE", "Flex Cable", "#F59E0B", 5),
    ],
    "back_covers": [
        ("BACK_COVER", "Back Cover", "#FF9F3A", 1),
        ("NFC",        "NFC",        "#32D583", 2),
        ("WIRELESS_CHARGING", "Wireless Charging", "#4A9EFF", 3),
        ("GLASS_BACK", "Glass Back", "#C17BFF", 4),
        ("MATTE_BACK", "Matte Back", "#6B7280", 5),
        ("CARBON_FIBER", "Carbon Fiber", "#1A1A1A", 6),
    ],
    "screen_protectors": [
        ("TEMPERED_GLASS", "Tempered Glass", "#4A9EFF", 1),
        ("HYDROGEL", "Hydrogel Film", "#32D583", 2),
        ("PET_FILM", "PET Film", "#6B7280", 3),
        ("PRIVACY_SCREEN", "Privacy Screen", "#1A1A1A", 4),
        ("MATTE_ANTI_GLARE", "Matte Anti-Glare", "#A0A8B0", 5),
        ("BLUE_LIGHT_FILTER", "Blue Light Filter", "#3B82F6", 6),
    ],
}


# ── Part Type Colors (for Samsung displays and other multi-color part types) ──

PART_TYPE_COLORS: dict[str, list[tuple[str, str, int]]] = {
    "SM_ORG_SERVICE": [
        ("Black",  "BLK", 1),
        ("Blue",   "BLU", 2),
        ("Silver", "SLV", 3),
        ("Gold",   "GLD", 4),
        ("Green",  "GRN", 5),
        ("Purple", "PRP", 6),
        ("White",  "WHT", 7),
        ("Pink",   "PNK", 8),
        ("Red",    "RED", 9),
    ],
    "SM_OLED": [
        ("Black",  "BLK", 1),
        ("Blue",   "BLU", 2),
        ("Silver", "SLV", 3),
        ("Gold",   "GLD", 4),
        ("Green",  "GRN", 5),
        ("Purple", "PRP", 6),
        ("White",  "WHT", 7),
    ],
    "COPY_INCELL": [
        ("Black",  "BLK", 1),
        ("White",  "WHT", 2),
    ],
    "ORG_PULLED": [
        ("Black",  "BLK", 1),
        ("White",  "WHT", 2),
        ("Red",    "RED", 3),
    ],
}


# ── Brand-Specific Part Type Mappings ─────────────────────────────────────────

DISPLAY_BRAND_MAP: dict[str, list[str]] = {
    "Apple":   ["JK_INCELL_FHD", "DD_SOFT_OLED", "DD_SOFT_OLED_DIAG", "ORG_PULLED",
                "ORG_DIAGNOSE_USED", "COPY_INCELL", "REFURBISHED", "AFTERMARKET_LCD"],
    "Samsung": ["SM_ORG_SERVICE", "SM_OLED", "COPY_INCELL", "REFURBISHED", "AFTERMARKET_LCD"],
    "Xiaomi":  ["SM_ORG_SERVICE", "SM_OLED", "COPY_INCELL", "REFURBISHED", "AFTERMARKET_LCD"],
}


# ── Step 0: reset database ───────────────────────────────────────────────────

def reset_database() -> None:
    if os.path.exists(DB_FILE):
        bak = DB_FILE + ".pre-voltedge.bak"
        if os.path.exists(bak):
            os.remove(bak)
        os.rename(DB_FILE, bak)
        print(f"  Backed up existing DB → {os.path.basename(bak)}")
    db.init_db()
    db.load_demo_data()
    print("  Fresh DB initialised (V21 schema + demo skeleton)")


# ── Step 1: shop config ───────────────────────────────────────────────────────

def configure_shop() -> None:
    from app.core.config import ShopConfig
    cfg = ShopConfig.get()
    cfg.name = "VoltEdge Electronics"
    cfg.currency = "€"
    cfg.currency_position = "before"
    cfg.theme = "pro_dark"
    cfg.default_language = "en"
    cfg.save()
    ShopConfig.invalidate()
    print("  Shop config: VoltEdge Electronics · Pro Dark · €")


# ── Step 1.5: locations ─────────────────────────────────────────────────────────

def seed_locations() -> dict[str, int]:
    """Create multiple inventory locations."""
    from app.services.location_service import LocationService
    svc = LocationService()
    conn = db.get_connection()
    ids: dict[str, int] = {}
    
    for name, description, is_default in LOCATIONS:
        lid = svc.add(name, description)
        if is_default:
            conn.execute("UPDATE locations SET is_default=1 WHERE id=?", (lid,))
        ids[name] = lid
    
    conn.commit()
    print(f"  Seeded {len(ids)} locations")
    return ids


# ── Step 1.6: extended part types ───────────────────────────────────────────────

def seed_extended_part_types() -> None:
    """Add extended part types to existing categories."""
    conn = db.get_connection()
    
    # Get category IDs
    cat_ids = {row[0]: row[1] for row in conn.execute("SELECT key, id FROM categories").fetchall()}
    
    # Get existing part types to avoid duplicates
    existing_pt = {(row[0], row[1]) for row in conn.execute(
        "SELECT c.key, pt.key FROM part_types pt JOIN categories c ON c.id = pt.category_id"
    ).fetchall()}
    
    # Add new part types
    for cat_key, part_types in PART_TYPES.items():
        if cat_key not in cat_ids:
            continue
        
        cat_id = cat_ids[cat_key]
        for pt_key, pt_name, accent_color, sort_order in part_types:
            if (cat_key, pt_key) in existing_pt:
                continue
            
            conn.execute(
                """INSERT INTO part_types (category_id, key, name, accent_color, sort_order)
                   VALUES (?, ?, ?, ?, ?)""",
                (cat_id, pt_key, pt_name, accent_color, sort_order)
            )
    
    # Add part type colors
    for pt_key, colors in PART_TYPE_COLORS.items():
        # Get part type ID
        pt_row = conn.execute("SELECT id FROM part_types WHERE key=?", (pt_key,)).fetchone()
        if not pt_row:
            continue
        
        pt_id = pt_row[0]
        
        for color_name, color_code, sort_order in colors:
            conn.execute(
                """INSERT OR IGNORE INTO part_type_colors
                   (part_type_id, color_name, color_code, sort_order)
                   VALUES (?, ?, ?, ?)""",
                (pt_id, color_name, color_code, sort_order)
            )

    conn.commit()
    # Matrix items (incl. per-colour rows) are built by materialize_matrix_items()
    # in the next step, once all part types and colours are in place.
    print(f"  Extended part types seeded across {len(PART_TYPES)} categories")


# ── Step 3.5: materialize matrix items (per-colour + colourless parent) ────────

def materialize_matrix_items() -> None:
    """Create every matrix inventory row the grid needs.

    For a part type WITH colours → one row per (model, colour) plus a
    colourless parent row (the parent is scan-only and hidden from the grid
    when coloured siblings exist — see item_repo.get_matrix_items). For a
    colourless part type → a single (model, '') row. Display part types are
    brand-scoped via DISPLAY_BRAND_MAP; all other categories apply to every
    model. Idempotent via INSERT OR IGNORE, so it layers cleanly on top of the
    rows load_demo_data() already created.
    """
    conn = db.get_connection()

    cat_key_by_id = {r[0]: r[1] for r in conn.execute("SELECT id, key FROM categories")}
    displays_cat_id = next((cid for cid, k in cat_key_by_id.items() if k == "displays"), None)

    part_types = conn.execute(
        "SELECT id, key, category_id FROM part_types"
    ).fetchall()

    colors_by_pt: dict[int, list[str]] = {}
    for pt_id, color_name in conn.execute(
        "SELECT part_type_id, color_name FROM part_type_colors ORDER BY sort_order"
    ):
        colors_by_pt.setdefault(pt_id, []).append(color_name)

    models = conn.execute("SELECT id, brand FROM phone_models").fetchall()

    inserts: list[tuple] = []
    for pt_id, pt_key, cat_id in part_types:
        is_display = (cat_id == displays_cat_id)
        colors = colors_by_pt.get(pt_id, [])
        for mid, brand in models:
            if is_display and pt_key not in DISPLAY_BRAND_MAP.get(brand, []):
                continue
            if colors:
                for color in colors:
                    inserts.append((mid, pt_id, color))
                inserts.append((mid, pt_id, ""))  # colourless scan-only parent
            else:
                inserts.append((mid, pt_id, ""))

    conn.executemany(
        """INSERT OR IGNORE INTO inventory_items
               (model_id, part_type_id, color, brand, name,
                stock, min_stock, is_active)
           VALUES (?, ?, ?, '', '', 0, 0, 1)""",
        inserts,
    )
    conn.commit()

    total = conn.execute(
        "SELECT COUNT(*) FROM inventory_items WHERE model_id IS NOT NULL"
    ).fetchone()[0]
    colored = sum(1 for pt_id, _, _ in part_types if colors_by_pt.get(pt_id))
    print(f"  Matrix materialized: {total} items "
          f"({colored} coloured part types expanded into colour rows)")


# ── Step 2: suppliers ─────────────────────────────────────────────────────────

# rating is an integer 1–5 star count (the UI renders it as "★" * rating).
SUPPLIERS = [
    ("ScreenSource EU",       "Thomas Bauer",   "+49 30 2345678",  "orders@screensource.eu",     "Technologiepark 12, Berlin",    5),
    ("PowerCell Distribution","Lisa Hoffmann",  "+49 69 7654321",  "supply@powercell-dist.de",   "Industriestr. 44, Frankfurt",   5),
    ("CaseCraft Supplies",    "Marco Ricci",    "+39 02 9876543",  "b2b@casecraft-supplies.com", "Via Industria 88, Milan",       4),
    ("MobileParts Direct",    "Sandra Klein",   "+49 89 1234567",  "orders@mobilepartsdirect.de","Gewerbepark 7, Munich",         5),
    ("TechDistro GmbH",       "Klaus Werner",   "+49 221 3456789", "sales@techdistro.de",        "Hansaring 100, Cologne",        4),
    ("AudioMax Wholesale",    "Elena Müller",   "+49 40 8765432",  "wholesale@audiomax.de",      "Hafenstr. 22, Hamburg",         4),
    ("WearTech Distribution", "Anna Schmidt",   "+49 30 9988776",  "info@weartech-dist.eu",      "Alexanderplatz 5, Berlin",      4),
]


def seed_suppliers() -> dict[str, int]:
    from app.services.supplier_service import SupplierService
    svc = SupplierService()
    conn = db.get_connection()
    ids: dict[str, int] = {}
    for name, contact, phone, email, address, rating in SUPPLIERS:
        sid = svc.add(name)
        svc.update(sid, name)
        conn.execute(
            "UPDATE suppliers SET contact_name=?,phone=?,email=?,address=?,rating=? WHERE id=?",
            (contact, phone, email, address, rating, sid),
        )
        ids[name] = sid
    conn.commit()
    print(f"  Seeded {len(ids)} suppliers")
    return ids


# ── Step 3: customers ─────────────────────────────────────────────────────────

CUSTOMERS = [
    ("Markus Becker",       "+49 172 4561234", "m.becker@email.de",         "Kaiserstr. 18, Frankfurt",  "Regular repair customer", "Regular"),
    ("Julia Schneider",     "+49 151 7892345", "julia.s@gmail.com",          "Goethestr. 7, Frankfurt",   "Bought cases + screen protectors", "Regular"),
    ("Ahmed Al-Rashidi",    "+49 176 3214567", "a.rashidi@web.de",           "Sachsenhäuser Ufer 3, Frankfurt", "iPhone display repair", "Regular"),
    ("Petra Zimmermann",    "+49 160 8901234", "petra.z@hotmail.de",         "Berger Str. 55, Frankfurt", "Wearables buyer", "Regular"),
    ("Tobias Krause",       "+49 179 5678901", "tobias.krause@gmail.com",    "Römerberg 12, Frankfurt",   "Samsung parts customer", "Regular"),
    ("Sarah Weber",         "+49 155 2345678", "s.weber@yahoo.de",           "Zeil 88, Frankfurt",        "Accessories + chargers", "Regular"),
    ("Daniel Fischer",      "+49 162 6789012", "d.fischer@outlook.de",       "Hanauer Landstr. 200, Frankfurt", "Smart home buyer", "Regular"),
    ("Lena Hartmann",       "+49 173 0123456", "lena.h@email.de",            "Eschersheimer Landstr. 30, Frankfurt", "Audio equipment fan", "Regular"),
    ("Kevin Schulz",        "+49 158 9012345", "k.schulz@gmail.com",         "Friedberger Anlage 9, Frankfurt", "Gaming accessories", "Regular"),
    ("Monika Braun",        "+49 177 3456789", "monika.b@web.de",            "Bockenheimer Landstr. 100, Frankfurt", "Regular customer", "Walk-in"),
    ("TechFix Solutions GmbH", "+49 69 11223344", "orders@techfix-solutions.de","Mainzer Landstr. 50, Frankfurt", "B2B repair shop partner", "VIP_B2B"),
    ("Mobile Repair Frankfurt", "+49 69 99887766", "parts@mrf.de",            "Konstablerwache 5, Frankfurt", "B2B wholesale buyer", "VIP_B2B"),
]


def seed_customers() -> tuple[list[int], dict[int, str]]:
    """Seed customers and return (ids, segment_map)."""
    from app.services.customer_service import CustomerService
    svc = CustomerService()
    ids: list[int] = []
    segment_map: dict[int, str] = {}
    for name, phone, email, address, notes, segment in CUSTOMERS:
        cid = svc.add_customer(name=name, phone=phone, email=email,
                                address=address, notes=notes)
        ids.append(cid)
        segment_map[cid] = segment
    print(f"  Seeded {len(ids)} customers (segmented)")
    return ids, segment_map


# ── Step 4: matrix stock (bulk SQL — all 2553 items) ─────────────────────────

def _get_location_distribution(cat_key: str, total_stock: int) -> dict[str, int]:
    """Calculate realistic stock distribution across locations based on category."""
    # Fast-moving items: distribute across multiple locations
    fast_moving = {"displays", "batteries", "charging_ports", "screen_protectors"}
    # Medium-moving: main warehouse + retail
    medium_moving = {"cases", "cameras", "back_covers"}
    # Slow-moving: mainly warehouse
    slow_moving = {"repair_tools"}
    
    if cat_key in fast_moving:
        # 60% warehouse, 25% retail, 10% workshop, 5% backup
        return {
            "Main Warehouse": int(total_stock * 0.60),
            "Retail Store Front": int(total_stock * 0.25),
            "Repair Workshop": int(total_stock * 0.10),
            "Backup Storage": total_stock - int(total_stock * 0.60) - int(total_stock * 0.25) - int(total_stock * 0.10),
        }
    elif cat_key in medium_moving:
        # 70% warehouse, 20% retail, 10% backup
        return {
            "Main Warehouse": int(total_stock * 0.70),
            "Retail Store Front": int(total_stock * 0.20),
            "Backup Storage": total_stock - int(total_stock * 0.70) - int(total_stock * 0.20),
        }
    elif cat_key in slow_moving:
        # 90% warehouse, 10% backup
        return {
            "Main Warehouse": int(total_stock * 0.90),
            "Backup Storage": total_stock - int(total_stock * 0.90),
        }
    else:
        # Default: 80% warehouse, 20% retail
        return {
            "Main Warehouse": int(total_stock * 0.80),
            "Retail Store Front": total_stock - int(total_stock * 0.80),
        }


def seed_matrix_stock(supplier_ids: dict[str, int]) -> list[dict]:
    """Price and stock ALL matrix items in bulk; return pool of stocked items.

    Location distribution is NOT built here — it's rebuilt from final stock
    levels by rebuild_location_distribution() after sales/audit/returns have
    mutated stock, so per-location quantities always reconcile with item.stock.
    """
    conn = db.get_connection()
    opening_ts = _ts(52, hour=8, minute=30)

    # Resolve part_type → category key
    pt_to_cat = {
        row[0]: row[1]
        for row in conn.execute("""
            SELECT pt.id, c.key
            FROM part_types pt JOIN categories c ON c.id = pt.category_id
        """)
    }

    # Part types that have colours — their stock lives in the per-colour rows,
    # NOT the colourless parent (which the grid hides; it's scan-only).
    colored_pts = {
        row[0] for row in conn.execute(
            "SELECT DISTINCT part_type_id FROM part_type_colors"
        )
    }

    # Group rows by (model, part_type) so every colour of the same part shares
    # one consistent price/cost (a blue screen costs the same as a black one).
    rows = conn.execute(
        """SELECT id, part_type_id, model_id, color
           FROM inventory_items WHERE model_id IS NOT NULL"""
    ).fetchall()
    groups: dict[tuple[int, int], list[tuple[int, str]]] = {}
    for iid, pt_id, model_id, color in rows:
        groups.setdefault((model_id, pt_id), []).append((iid, color or ""))

    item_updates: list[tuple] = []     # (sell_price, min_stock, stock, item_id)
    supplier_rows: list[tuple] = []
    pool: list[dict] = []

    def _roll_qty(ms: int) -> int:
        roll = RNG.random()
        if roll < 0.05:
            return 0
        if roll < 0.12:
            return RNG.randint(1, max(1, ms - 1))
        return RNG.randint(ms, ms * 4)

    for (model_id, pt_id), members in groups.items():
        cat_key = pt_to_cat.get(pt_id)
        params = CATEGORY_PARAMS.get(cat_key)
        if not params:
            continue

        price = _round99(RNG.uniform(*params["price"]))
        cost  = round(price * RNG.uniform(*params["cost_ratio"]), 2)
        ms    = params["min_stock"]
        has_colors = pt_id in colored_pts

        for iid, color in members:
            # Colourless parent of a coloured part type: priced for scanning
            # but holds no stock (the grid shows the colour rows instead).
            if has_colors and color == "":
                item_updates.append((price, 0, 0, iid))
                continue

            qty = _roll_qty(ms)
            item_updates.append((price, ms, qty, iid))

            sup_id = supplier_ids.get(SUPPLIER_BY_CATEGORY.get(cat_key, ""))
            if sup_id:
                supplier_rows.append((sup_id, iid, cost, RNG.randint(3, 10)))

            if qty > 0:
                pool.append({"item_id": iid, "price": price, "stock": qty,
                             "cat_key": cat_key,
                             "supplier": SUPPLIER_BY_CATEGORY.get(cat_key, "")})

    conn.executemany(
        "UPDATE inventory_items SET sell_price=?, min_stock=?, stock=? WHERE id=?",
        item_updates,
    )
    conn.executemany(
        """INSERT OR IGNORE INTO supplier_items
           (supplier_id, item_id, cost_price, lead_days, supplier_sku, is_preferred)
           VALUES (?, ?, ?, ?, '', 1)""",
        supplier_rows,
    )
    conn.commit()

    # Bulk-log opening stock-in transactions (one row per stocked item)
    conn.execute(
        """
        INSERT INTO inventory_transactions
               (item_id, operation, quantity, stock_before, stock_after, note, timestamp)
        SELECT id, 'IN', stock, 0, stock,
               'Initial stock — opening inventory', ?
        FROM   inventory_items
        WHERE  model_id IS NOT NULL AND stock > 0
        """,
        (opening_ts,),
    )
    conn.commit()

    stocked = sum(1 for price, ms, q, iid in item_updates if q > 0)
    print(f"  Matrix: {len(item_updates)} items priced; {stocked} stocked; "
          f"{len(supplier_rows)} supplier links")
    return pool


# ── Step 5: standalone electronics products ───────────────────────────────────

ELECTRONICS: list[dict] = [
    # Chargers & cables
    {"brand": "Anker",    "name": "65W GaN USB-C Charger",         "color": "Black", "price": 39.99, "cost": 18.50, "stock": 24, "min_stock": 8,  "sku": "ANK-65W-GAN"},
    {"brand": "Anker",    "name": "20W USB-C PD Charger",          "color": "White", "price": 19.99, "cost": 8.20,  "stock": 35, "min_stock": 10, "sku": "ANK-20W-PD"},
    {"brand": "Baseus",   "name": "100W 4-Port USB Hub Charger",   "color": "Black", "price": 49.99, "cost": 22.00, "stock": 12, "min_stock": 4,  "sku": "BAS-100W-4P"},
    {"brand": "Belkin",   "name": "USB-C to Lightning Cable 1m",   "color": "White", "price": 14.99, "cost": 4.80,  "stock": 50, "min_stock": 15, "sku": "BEL-CTOL-1M"},
    {"brand": "Belkin",   "name": "USB-C to USB-C Cable 2m",       "color": "Black", "price": 12.99, "cost": 4.20,  "stock": 45, "min_stock": 15, "sku": "BEL-CTOC-2M"},
    {"brand": "Ugreen",   "name": "USB-A to Micro-USB Cable 2m",   "color": "Black", "price": 7.99,  "cost": 2.50,  "stock": 60, "min_stock": 20, "sku": "UGR-ATOM-2M"},
    {"brand": "Ugreen",   "name": "10-in-1 USB-C Hub",             "color": "Gray",  "price": 44.99, "cost": 19.80, "stock": 15, "min_stock": 5,  "sku": "UGR-10IN1-HUB"},
    # Screen protection
    {"brand": "Spigen",   "name": "iPhone 16 Pro Tempered Glass",  "color": "Clear", "price": 11.99, "cost": 3.50,  "stock": 30, "min_stock": 10, "sku": "SPG-IP16P-TG"},
    {"brand": "Spigen",   "name": "Samsung S25 Ultra Screen Guard","color": "Clear", "price": 9.99,  "cost": 3.10,  "stock": 28, "min_stock": 10, "sku": "SPG-S25U-SG"},
    {"brand": "Ringke",   "name": "Universal Tempered Glass 2-Pack","color":"Clear", "price": 6.99,  "cost": 2.00,  "stock": 40, "min_stock": 12, "sku": "RNG-UNIV-TG2"},
    # Cases
    {"brand": "Spigen",   "name": "iPhone 16 Pro Max Rugged Case", "color": "Black", "price": 19.99, "cost": 7.50,  "stock": 18, "min_stock": 6,  "sku": "SPG-IP16PM-RG"},
    {"brand": "Spigen",   "name": "Samsung S25 Ultra Slim Case",   "color": "Navy",  "price": 16.99, "cost": 6.20,  "stock": 20, "min_stock": 6,  "sku": "SPG-S25U-SL"},
    {"brand": "OtterBox", "name": "Commuter Series iPhone 16 Case","color": "Black", "price": 29.99, "cost": 12.00, "stock": 10, "min_stock": 4,  "sku": "OTB-COM-IP16"},
    # Audio
    {"brand": "Sony",     "name": "WF-1000XM5 True Wireless Earbuds","color":"Black","price":179.99,"cost": 95.00, "stock": 8,  "min_stock": 3,  "sku": "SNY-WF1000XM5"},
    {"brand": "Sony",     "name": "WH-1000XM5 Headphones",          "color":"Black","price":249.99,"cost":130.00, "stock": 6,  "min_stock": 2,  "sku": "SNY-WH1000XM5"},
    {"brand": "JBL",      "name": "Clip 5 Portable Speaker",        "color":"Blue", "price": 59.99, "cost": 28.00, "stock": 14, "min_stock": 4,  "sku": "JBL-CLIP5-BL"},
    {"brand": "JBL",      "name": "Flip 6 Portable Speaker",        "color":"Black","price": 99.99, "cost": 48.00, "stock": 10, "min_stock": 3,  "sku": "JBL-FLIP6-BK"},
    {"brand": "Anker",    "name": "Soundcore Liberty 4 NC Earbuds", "color":"White","price": 79.99, "cost": 36.00, "stock": 12, "min_stock": 4,  "sku": "ANK-LIB4NC-WH"},
    # Wearables
    {"brand": "Apple",    "name": "Apple Watch Ultra 2 49mm",       "color":"Titanium","price":799.99,"cost":520.00,"stock": 4,  "min_stock": 2,  "sku": "APL-WU2-49TI"},
    {"brand": "Samsung",  "name": "Galaxy Watch 7 44mm",            "color":"Cream", "price":299.99, "cost":165.00, "stock": 7,  "min_stock": 2,  "sku": "SAM-GW7-44CR"},
    {"brand": "Garmin",   "name": "Forerunner 265 GPS Watch",       "color":"Black", "price":349.99, "cost":192.00, "stock": 5,  "min_stock": 2,  "sku": "GRM-FR265-BK"},
    {"brand": "Xiaomi",   "name": "Smart Band 8 Pro",               "color":"Black", "price": 49.99, "cost": 22.00, "stock": 18, "min_stock": 5,  "sku": "XMI-SB8P-BK"},
    # Storage
    {"brand": "Samsung",  "name": "T9 Portable SSD 2TB",           "color":"Black", "price":139.99, "cost": 72.00, "stock": 9,  "min_stock": 3,  "sku": "SAM-T9-2TB"},
    {"brand": "SanDisk",  "name": "Ultra 256GB microSD Card",       "color":"Red",   "price": 22.99, "cost": 8.50,  "stock": 30, "min_stock": 10, "sku": "SND-256-MSD"},
    {"brand": "Kingston", "name": "DataTraveler 128GB USB-A 3.2",  "color":"Silver","price": 12.99, "cost": 4.80,  "stock": 40, "min_stock": 12, "sku": "KNG-DT128-3A"},
    # Power banks
    {"brand": "Anker",    "name": "PowerCore 26800 mAh",           "color":"Black", "price": 54.99, "cost": 25.00, "stock": 14, "min_stock": 4,  "sku": "ANK-PC26800"},
    {"brand": "Baseus",   "name": "20000 mAh 65W Power Bank",      "color":"White", "price": 44.99, "cost": 19.50, "stock": 16, "min_stock": 5,  "sku": "BAS-PB20K65"},
    {"brand": "Xiaomi",   "name": "Mi Power Bank 3 10000 mAh",     "color":"White", "price": 19.99, "cost": 8.00,  "stock": 22, "min_stock": 8,  "sku": "XMI-PB3-10K"},
    # Smart home
    {"brand": "Philips Hue","name":"Starter Kit E27 3-Pack + Bridge","color":"White","price":129.99,"cost": 66.00, "stock": 7,  "min_stock": 2,  "sku": "HUE-SK3-E27"},
    {"brand": "TP-Link",  "name": "Tapo P115 Smart Plug 4-Pack",   "color":"White", "price": 39.99, "cost": 16.00, "stock": 12, "min_stock": 4,  "sku": "TPL-P115-4PK"},
    {"brand": "Meross",   "name": "Smart WLAN Power Strip 4-Outlet","color":"White","price": 34.99, "cost": 13.50, "stock": 9,  "min_stock": 3,  "sku": "MRS-WLAN-4PS"},
    # Mounts / accessories
    {"brand": "Belkin",   "name": "MagSafe 3-in-1 Wireless Charger","color":"White","price": 89.99, "cost": 42.00, "stock": 11, "min_stock": 3,  "sku": "BEL-MAG3IN1"},
    {"brand": "iOttie",   "name": "Easy One Touch 5 Car Mount",    "color":"Black", "price": 24.99, "cost": 9.50,  "stock": 15, "min_stock": 5,  "sku": "IOT-EOT5-CM"},
    {"brand": "Lamicall",  "name": "Adjustable Tablet Stand",      "color":"Silver","price": 17.99, "cost": 6.80,  "stock": 20, "min_stock": 6,  "sku": "LAM-ADJ-TST"},
    # Repair tools
    {"brand": "iFixit",   "name": "Pro Tech Toolkit 64-Bit",       "color": "Red",  "price": 69.99, "cost": 34.00, "stock": 8,  "min_stock": 2,  "sku": "IFX-PROTECH64"},
    {"brand": "iFixit",   "name": "iPhone 16 Screen Adhesive Strips","color":"Clear","price": 5.99,  "cost": 1.80, "stock": 40, "min_stock": 15, "sku": "IFX-IP16-ADH"},
    {"brand": "MECHANIC", "name": "Precision Screwdriver Set 25pc","color":"Black", "price": 22.99, "cost": 8.00,  "stock": 10, "min_stock": 3,  "sku": "MCH-PREC25"},
    # Gaming
    {"brand": "8BitDo",   "name": "Ultimate 2 Bluetooth Controller","color":"Black","price": 49.99, "cost": 24.00, "stock": 9,  "min_stock": 3,  "sku": "8BD-ULT2-BT"},
    {"brand": "Razer",    "name": "Kraken V3 X Gaming Headset",    "color":"Black", "price": 49.99, "cost": 23.00, "stock": 7,  "min_stock": 2,  "sku": "RZR-KV3X-BK"},
    # Network
    {"brand": "TP-Link",  "name": "Deco XE75 AXE5400 Mesh System","color":"White", "price":199.99, "cost":105.00, "stock": 5,  "min_stock": 2,  "sku": "TPL-XE75-MESH"},
    {"brand": "Netgear",  "name": "Nighthawk AX3000 Wi-Fi 6 Router","color":"Black","price":129.99, "cost": 65.00, "stock": 6,  "min_stock": 2,  "sku": "NGR-AX3K-R6"},
    # Misc
    {"brand": "VoltEdge", "name": "Privacy Screen 15.6\" Laptop",  "color":"Clear", "price": 29.99, "cost": 10.00, "stock": 0,  "min_stock": 3,  "sku": "VE-PRIV-156"},
    {"brand": "Ugreen",   "name": "4K HDMI 2.1 Cable 2m",         "color":"Black", "price": 14.99, "cost": 5.20,  "stock": 25, "min_stock": 8,  "sku": "UGR-HDMI21-2M"},
    {"brand": "Ugreen",   "name": "USB-C Docking Station 12-in-1","color":"Gray",  "price": 79.99, "cost": 36.00, "stock": 11, "min_stock": 4,  "sku": "UGR-DOCK12"},
    {"brand": "Ringke",   "name": "5-in-1 Cable Organiser Pack",   "color":"Black", "price": 8.99,  "cost": 2.80,  "stock": 35, "min_stock": 10, "sku": "RNG-5IN1-CO"},
]

ELEC_SUPPLIER: dict[str, str] = {
    "Anker": "TechDistro GmbH",
    "Baseus": "TechDistro GmbH",
    "Belkin": "TechDistro GmbH",
    "Ugreen": "TechDistro GmbH",
    "Spigen": "CaseCraft Supplies",
    "OtterBox": "CaseCraft Supplies",
    "Ringke": "CaseCraft Supplies",
    "Sony": "AudioMax Wholesale",
    "JBL": "AudioMax Wholesale",
    "Apple": "WearTech Distribution",
    "Samsung": "WearTech Distribution",
    "Garmin": "WearTech Distribution",
    "Xiaomi": "WearTech Distribution",
    "SanDisk": "TechDistro GmbH",
    "Kingston": "TechDistro GmbH",
    "Philips Hue": "TechDistro GmbH",
    "TP-Link": "TechDistro GmbH",
    "Netgear": "TechDistro GmbH",
    "Meross": "TechDistro GmbH",
    "iOttie": "TechDistro GmbH",
    "Lamicall": "TechDistro GmbH",
    "iFixit": "MobileParts Direct",
    "MECHANIC": "MobileParts Direct",
    "8BitDo": "TechDistro GmbH",
    "Razer": "AudioMax Wholesale",
    "VoltEdge": "TechDistro GmbH",
}


def seed_electronics(supplier_ids: dict[str, int]) -> list[dict]:
    from app.repositories.item_repo import ItemRepository
    item_repo = ItemRepository()
    conn = db.get_connection()
    opening_ts = _ts(52, hour=9, minute=0)

    pool: list[dict] = []

    for p in ELECTRONICS:
        iid = item_repo.add_product(
            brand=p["brand"],
            name=p["name"],
            color=p["color"],
            stock=0,
            barcode=None,
            min_stock=p["min_stock"],
            sell_price=p["price"],
        )
        # Set price (add_product may not set it directly)
        item_repo.update_price(iid, p["price"])
        item_repo.update_min_stock(iid, p["min_stock"])

        # Backdate the CREATE transaction
        conn.execute(
            "UPDATE inventory_transactions SET timestamp=? WHERE item_id=? AND operation='CREATE'",
            (_ts(52, hour=8, minute=0), iid),
        )

        # Stock in if qty > 0
        if p["stock"] > 0:
            conn.execute(
                "UPDATE inventory_items SET stock=? WHERE id=?",
                (p["stock"], iid),
            )
            conn.execute(
                """INSERT INTO inventory_transactions
                   (item_id, operation, quantity, stock_before, stock_after, note, timestamp)
                   VALUES (?, 'IN', ?, 0, ?, 'Initial stock — opening inventory', ?)""",
                (iid, p["stock"], p["stock"], opening_ts),
            )

        sup_name = ELEC_SUPPLIER.get(p["brand"], "TechDistro GmbH")
        sup_id = supplier_ids.get(sup_name)
        if sup_id:
            conn.execute(
                """INSERT OR IGNORE INTO supplier_items
                   (supplier_id, item_id, cost_price, lead_days, supplier_sku, is_preferred)
                   VALUES (?, ?, ?, ?, ?, 1)""",
                (sup_id, iid, p["cost"], RNG.randint(3, 7), p["sku"]),
            )

        conn.commit()

        if p["stock"] > 0:
            pool.append({
                "item_id": iid, "price": p["price"],
                "stock": p["stock"], "cat_key": "electronics",
                "supplier": sup_name,
            })

    print(f"  Seeded {len(ELECTRONICS)} electronics products "
          f"({len(pool)} with stock > 0)")
    return pool


# ── Step 6: sales ─────────────────────────────────────────────────────────────

def seed_sales(customer_ids: list[int],
               segment_map: dict[int, str],
               matrix_pool: list[dict],
               electronics_pool: list[dict]) -> list[int]:
    from app.services.sale_service import SaleService
    svc = SaleService()
    conn = db.get_connection()

    matrix_sell   = [dict(p, remaining=p["stock"]) for p in matrix_pool if p["stock"] > 0]
    elec_sell     = [dict(p, remaining=p["stock"]) for p in electronics_pool if p["stock"] > 0]

    sale_ids: list[int] = []
    for _ in range(60):
        days_ago = int(RNG.triangular(0, 44, 3))
        hour     = RNG.randint(9, 19)
        minute   = RNG.randint(0, 59)
        ts = _ts(days_ago, hour, minute)

        n_lines = RNG.choices([1, 2, 3], weights=[55, 30, 15])[0]
        lines: list[dict] = []
        used: set[int] = set()

        for _ in range(n_lines):
            use_elec = RNG.random() < 0.5
            for src in ([elec_sell, matrix_sell] if use_elec else [matrix_sell, elec_sell]):
                candidates = [s for s in src if s["remaining"] > 0 and s["item_id"] not in used]
                if candidates:
                    break
            else:
                continue
            c = RNG.choice(candidates)
            max_qty = min(c["remaining"], 3)
            qty = RNG.randint(1, max_qty)
            c["remaining"] -= qty
            used.add(c["item_id"])
            lines.append({"item_id": c["item_id"], "quantity": qty, "unit_price": c["price"]})

        if not lines:
            continue

        # Calculate discount based on customer segment
        discount = 0.0
        cid = RNG.choice(customer_ids) if RNG.random() < 0.65 else None
        if cid:
            segment = segment_map.get(cid, "Regular")
            segment_config = CUSTOMER_SEGMENTS.get(segment, CUSTOMER_SEGMENTS["Regular"])
            # Apply segment discount with some randomness
            if segment_config["discount"] > 0 and RNG.random() < 0.8:
                subtotal = sum(l["quantity"] * l["unit_price"] for l in lines)
                discount = round(subtotal * segment_config["discount"], 2)
        elif RNG.random() < 0.15:
            # Random discount for walk-in customers
            subtotal = sum(l["quantity"] * l["unit_price"] for l in lines)
            discount = round(subtotal * RNG.uniform(0.02, 0.08), 2)

        sid = svc.create_sale(customer_name="", discount=discount,
                               note="", items=lines, customer_id=cid)
        conn.execute("UPDATE sales SET timestamp=? WHERE id=?", (ts, sid))
        conn.execute(
            "UPDATE inventory_transactions SET timestamp=? WHERE note=?",
            (ts, f"Sale #{sid}"),
        )
        conn.commit()
        sale_ids.append(sid)

    print(f"  Seeded {len(sale_ids)} sales")
    return sale_ids


# ── Step 7: purchase orders ───────────────────────────────────────────────────

PO_PLAN = [
    ("RECEIVED", 32), ("RECEIVED", 27),
    ("PARTIAL",  14), ("PARTIAL",   9),
    ("SENT",      4), ("SENT",       2),
    ("DRAFT",     1), ("DRAFT",      0),
]


def seed_purchase_orders(supplier_ids: dict[str, int],
                         matrix_pool: list[dict],
                         electronics_pool: list[dict]) -> None:
    from app.services.purchase_order_service import PurchaseOrderService
    po_svc = PurchaseOrderService()
    conn = db.get_connection()

    pool = matrix_pool + electronics_pool
    by_supplier: dict[str, list[dict]] = {}
    for p in pool:
        by_supplier.setdefault(p["supplier"], []).append(p)

    supplier_names = list(supplier_ids.keys())

    for idx, (status, days_ago) in enumerate(PO_PLAN):
        sup_name = supplier_names[idx % len(supplier_names)]
        candidates = by_supplier.get(sup_name) or pool
        n = min(RNG.randint(3, 5), len(candidates))
        chosen = RNG.sample(candidates, n)

        po_id = po_svc.create_order(supplier_id=supplier_ids[sup_name],
                                     notes="Restock order")
        line_ids: list[tuple[int, int]] = []
        for item in chosen:
            qty  = RNG.randint(8, 30)
            cost = round(item["price"] * RNG.uniform(0.48, 0.58), 2)
            lid  = po_svc.add_item(po_id, item["item_id"],
                                    quantity=qty, cost_price=cost)
            line_ids.append((lid, qty))

        po_number = conn.execute(
            "SELECT po_number FROM purchase_orders WHERE id=?", (po_id,)
        ).fetchone()[0]

        if status in ("SENT", "PARTIAL", "RECEIVED"):
            po_svc.send_order(po_id)
        if status == "PARTIAL":
            received = {lid: max(1, qty // 2) for lid, qty in line_ids}
            po_svc.receive_order(po_id, received=received)
        elif status == "RECEIVED":
            po_svc.receive_order(po_id)

        ts = _ts(days_ago, hour=RNG.randint(8, 17))
        conn.execute(
            "UPDATE purchase_orders SET created_at=?, updated_at=? WHERE id=?",
            (ts, ts, po_id),
        )
        if status in ("PARTIAL", "RECEIVED"):
            conn.execute(
                "UPDATE inventory_transactions SET timestamp=? WHERE note=?",
                (ts, f"PO {po_number} received"),
            )
        conn.commit()

    print(f"  Seeded {len(PO_PLAN)} purchase orders (2 DRAFT, 2 SENT, 2 PARTIAL, 2 RECEIVED)")


# ── Step 8: returns ───────────────────────────────────────────────────────────

RETURN_REASONS = [
    "Screen flickering after repair",
    "Customer changed mind",
    "Wrong part installed",
    "Defective unit on arrival",
    "Purchased duplicate by mistake",
]


def seed_returns(sale_ids: list[int],
                 matrix_pool: list[dict],
                 electronics_pool: list[dict]) -> None:
    from app.services.return_service import ReturnService
    svc = ReturnService()
    conn = db.get_connection()

    pool = matrix_pool + electronics_pool
    stocked_pool = [p for p in pool if p["stock"] > 0]

    for i in range(5):
        item = RNG.choice(stocked_pool)
        reason = RNG.choice(RETURN_REASONS)
        action = "RESTOCK" if RNG.random() < 0.8 else "WRITEOFF"
        refund = round(item["price"] * RNG.uniform(0.85, 1.0), 2)
        sid = RNG.choice(sale_ids) if sale_ids else None

        ret_id = svc.process_return(
            item_id=item["item_id"],
            quantity=1,
            reason=reason,
            action=action,
            refund_amount=refund,
            sale_id=sid,
        )

        days_ago = RNG.randint(2, 20)
        ts = _ts(days_ago, hour=RNG.randint(10, 16))
        conn.execute("UPDATE returns SET created_at=? WHERE id=?", (ts, ret_id))
        if action == "RESTOCK":
            conn.execute(
                "UPDATE inventory_transactions SET timestamp=? WHERE note=?",
                (ts, f"Return #{ret_id}: {reason}"),
            )
        conn.commit()

    print("  Seeded 5 returns (4 RESTOCK, 1 WRITEOFF)")


# ── Step 9.5: stock transfers ───────────────────────────────────────────────────

def seed_stock_transfers(location_ids: dict[str, int]) -> None:
    """Create realistic inter-location stock transfers."""
    conn = db.get_connection()
    
    # Transfer types: replenishment, balancing, emergency
    # (from, to, note, number_of_transfers) — deterministic counts so the
    # transfers view is always populated (no probabilistic skipping).
    transfer_scenarios = [
        ("Main Warehouse", "Retail Store Front", "Replenishment", 5),
        ("Main Warehouse", "Repair Workshop", "Replenishment", 4),
        ("Retail Store Front", "Main Warehouse", "Return unsold", 2),
        ("Main Warehouse", "Backup Storage", "Overflow storage", 2),
    ]

    # Sample a varied pool of stocked items (randomised, not just the first 50).
    items_with_stock = conn.execute(
        "SELECT id, stock FROM inventory_items WHERE stock > 1 ORDER BY RANDOM() LIMIT 120"
    ).fetchall()

    transfer_count = 0
    for from_loc, to_loc, note_type, n_transfers in transfer_scenarios:
        if from_loc not in location_ids or to_loc not in location_ids:
            continue

        from_id = location_ids[from_loc]
        to_id = location_ids[to_loc]

        for _ in range(n_transfers):
            if not items_with_stock:
                break

            item = RNG.choice(items_with_stock)
            iid, total_stock = item[0], item[1]

            # Transfer a reasonable quantity (10-30% of stock, at least 1).
            qty = max(1, int(total_stock * RNG.uniform(0.10, 0.30)))

            note = f"{note_type} - {from_loc} to {to_loc}"

            conn.execute(
                """INSERT INTO stock_transfers
                   (item_id, from_location_id, to_location_id, quantity, note, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (iid, from_id, to_id, qty, note, _ts(RNG.randint(10, 40), hour=RNG.randint(9, 16)))
            )
            transfer_count += 1

    conn.commit()
    print(f"  Seeded {transfer_count} stock transfers between locations")


# ── Step 10: inventory audit ───────────────────────────────────────────────────

def _scope_audit_lines(audit_id: int, scope_sql: str, params: tuple) -> None:
    """Trim a freshly-created audit down to a meaningful subset.

    create_audit() populates every inventory item; a real cycle count covers
    one area at a time. Delete the lines whose item_id isn't in the scope query
    so the audit reads as a focused, realistic stocktake.
    """
    conn = db.get_connection()
    conn.execute(
        f"DELETE FROM audit_lines WHERE audit_id=? AND item_id NOT IN ({scope_sql})",
        (audit_id, *params),
    )
    conn.commit()


def _count_lines(svc, audit_id: int, fraction: float) -> tuple[int, int]:
    """Record physical counts for a fraction of an audit's lines.

    Returns (counted, discrepancies). Most counts match the system qty; a
    realistic minority drift by ±1–2 (miscount, shrinkage, mis-scan).
    """
    lines = svc.get_audit_lines(audit_id)
    n = max(1, int(len(lines) * fraction))
    to_count = lines[:n] if fraction >= 1.0 else RNG.sample(lines, n)
    discrepancies = 0
    for line in to_count:
        variance = RNG.choices([-2, -1, 0, 1, 2], weights=[4, 12, 66, 11, 7])[0]
        counted = max(0, line.system_qty + variance)
        note = "Counted — matches system" if variance == 0 else (
            "Short on shelf" if variance < 0 else "Extra found on shelf")
        svc.record_count(line.id, counted, note)
        if variance != 0:
            discrepancies += 1
    return len(to_count), discrepancies


def seed_audit() -> None:
    from app.services.audit_service import AuditService
    svc = AuditService()

    # ── Audit 1: COMPLETED cycle count of electronics & accessories ──────────
    # Standalone products (model_id IS NULL) carry real names, so this reads as
    # a clear, finished stocktake with applied adjustments.
    a1 = svc.create_audit(
        name="Q2 2026 Cycle Count — Electronics & Accessories",
        notes="Quarterly count of standalone accessories, audio & wearables.",
    )
    _scope_audit_lines(
        a1, "SELECT id FROM inventory_items WHERE model_id IS NULL AND is_active=1", ()
    )
    counted1, disc1 = _count_lines(svc, a1, fraction=1.0)
    svc.complete_audit(a1)
    svc.apply_adjustments(a1)

    conn = db.get_connection()  # service calls close the shared connection
    conn.execute(
        "UPDATE inventory_audits SET started_at=?, completed_at=? WHERE id=?",
        (_ts(9, hour=8, minute=0), _ts(9, hour=12, minute=30), a1),
    )
    conn.commit()

    # ── Audit 2: IN-PROGRESS stocktake of Samsung displays ───────────────────
    # A focused, still-open count of a single high-value area — shows what an
    # active audit looks like (partially counted, not yet applied).
    a2 = svc.create_audit(
        name="Stocktake — Samsung Displays (Repair Workshop)",
        notes="Spot count of Samsung service-pack & OLED screens, by colour.",
    )
    _scope_audit_lines(
        a2,
        """SELECT ii.id FROM inventory_items ii
             JOIN part_types pt ON pt.id = ii.part_type_id
             JOIN categories c  ON c.id  = pt.category_id
             JOIN phone_models pm ON pm.id = ii.model_id
            WHERE c.key='displays' AND pm.brand='Samsung'
              AND ii.color != '' AND ii.stock > 0
            ORDER BY RANDOM() LIMIT 60""",
        (),
    )
    counted2, disc2 = _count_lines(svc, a2, fraction=0.6)

    conn = db.get_connection()
    conn.execute(
        "UPDATE inventory_audits SET started_at=? WHERE id=?",
        (_ts(1, hour=9, minute=0), a2),
    )
    conn.commit()

    print(f"  Audit 1 (completed): {counted1} counted, {disc1} discrepancies applied")
    print(f"  Audit 2 (in progress): {counted2} of 60 counted, {disc2} discrepancies pending")


# ── Step 10: price lists ──────────────────────────────────────────────────────

# Scan-only colourless parent rows of coloured part types — never real
# sellable SKUs, so they're stripped out of every price list.
_PARENT_ITEMS_SQL = """
    item_id IN (
        SELECT ii.id FROM inventory_items ii
        WHERE ii.color = ''
          AND ii.part_type_id IN (SELECT DISTINCT part_type_id FROM part_type_colors)
    )
"""

# Categories that a repair-shop partner actually buys (spare parts), used to
# scope the B2B list. Accessories/electronics are retail-only.
_REPAIR_CATEGORIES = (
    "displays", "batteries", "cameras", "charging_ports", "back_covers",
)


def seed_price_lists() -> None:
    from app.services.price_list_service import PriceListService
    svc = PriceListService()

    # ── Standard Retail: every real sellable SKU at its shelf price ──────────
    retail_id = svc.create_list(
        name="Standard Retail Price List",
        description="Consumer shelf prices for all sellable products.",
    )
    svc.bulk_populate(retail_id)
    svc.update_list(retail_id, "Standard Retail Price List",
                    "Consumer shelf prices for all sellable products.",
                    is_active=True)
    # Strip scan-only parent rows so the list is real products only.
    conn = db.get_connection()
    conn.execute(
        f"DELETE FROM price_list_items WHERE price_list_id=? AND {_PARENT_ITEMS_SQL}",
        (retail_id,),
    )
    conn.commit()

    # ── Repair Shop Partner Pricing: spare parts only, 12% trade discount ────
    partner_id = svc.create_list(
        name="Repair Shop Partner Pricing",
        description="B2B trade pricing for repair partners — spare parts at 12% off.",
    )
    svc.bulk_populate(partner_id)
    svc.update_list(partner_id, "Repair Shop Partner Pricing",
                    "B2B trade pricing for repair partners — spare parts at 12% off.",
                    is_active=True)
    conn = db.get_connection()
    # Keep only real sellable SKUs in repair-part categories: per-colour rows
    # for coloured part types, or the single row for colourless ones. Drops
    # accessories/electronics and scan-only parents in one pass.
    cat_placeholders = ",".join("?" * len(_REPAIR_CATEGORIES))
    conn.execute(
        f"""DELETE FROM price_list_items
            WHERE price_list_id=? AND item_id NOT IN (
                SELECT ii.id FROM inventory_items ii
                JOIN part_types pt ON pt.id = ii.part_type_id
                JOIN categories c  ON c.id  = pt.category_id
                WHERE c.key IN ({cat_placeholders})
                  AND (
                      ii.color != ''
                      OR ii.part_type_id NOT IN
                         (SELECT DISTINCT part_type_id FROM part_type_colors)
                  )
            )""",
        (partner_id, *_REPAIR_CATEGORIES),
    )
    # bulk_markup rejects negative pct, so apply the 12% discount via SQL.
    conn.execute(
        "UPDATE price_list_items SET price = ROUND(price * 0.88, 2) WHERE price_list_id=?",
        (partner_id,),
    )
    conn.commit()

    retail_count = conn.execute(
        "SELECT COUNT(*) FROM price_list_items WHERE price_list_id=?", (retail_id,)
    ).fetchone()[0]
    partner_count = conn.execute(
        "SELECT COUNT(*) FROM price_list_items WHERE price_list_id=?", (partner_id,)
    ).fetchone()[0]
    print(f"  Price lists: Retail ({retail_count} SKUs) + "
          f"Partner repair parts ({partner_count} SKUs, 12% off)")


# ── Step 13: rebuild location distribution (final, from settled stock) ─────────

def rebuild_location_distribution(location_ids: dict[str, int]) -> None:
    """Rebuild location_stock from each item's FINAL stock.

    Runs after sales/audit/returns have settled, so per-location quantities
    always sum exactly to inventory_items.stock. Matrix items are distributed
    by category; standalone electronics (model_id IS NULL) use the default
    warehouse/retail split.
    """
    conn = db.get_connection()
    conn.execute("DELETE FROM location_stock")

    pt_to_cat = {
        row[0]: row[1]
        for row in conn.execute("""
            SELECT pt.id, c.key
            FROM part_types pt JOIN categories c ON c.id = pt.category_id
        """)
    }

    rows = conn.execute(
        "SELECT id, part_type_id, model_id, stock FROM inventory_items WHERE stock > 0"
    ).fetchall()

    loc_rows: list[tuple] = []
    for iid, pt_id, model_id, stock in rows:
        cat_key = pt_to_cat.get(pt_id, "electronics") if model_id is not None else "electronics"
        for loc_name, qty in _get_location_distribution(cat_key, stock).items():
            if qty > 0 and loc_name in location_ids:
                loc_rows.append((iid, location_ids[loc_name], qty))

    conn.executemany(
        """INSERT OR IGNORE INTO location_stock (item_id, location_id, quantity)
           VALUES (?, ?, ?)""",
        loc_rows,
    )
    conn.commit()

    # Verify reconciliation: per-location sums must equal item stock.
    drift = conn.execute("""
        SELECT COUNT(*) FROM (
            SELECT ii.id
            FROM inventory_items ii
            LEFT JOIN location_stock ls ON ls.item_id = ii.id
            WHERE ii.stock > 0
            GROUP BY ii.id
            HAVING ii.stock != COALESCE(SUM(ls.quantity), 0)
        )
    """).fetchone()[0]
    print(f"  Location stock rebuilt: {len(loc_rows)} entries; drift={drift}")


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary() -> None:
    conn = db.get_connection()

    def q(sql: str) -> int:
        return conn.execute(sql).fetchone()[0]

    total_items   = q("SELECT COUNT(*) FROM inventory_items")
    stocked_items = q("SELECT COUNT(*) FROM inventory_items WHERE stock > 0")
    low_stock     = q("SELECT COUNT(*) FROM inventory_items WHERE stock > 0 AND stock <= min_stock")
    out_of_stock  = q("SELECT COUNT(*) FROM inventory_items WHERE stock = 0 AND is_active=1")
    total_value   = conn.execute(
        "SELECT COALESCE(SUM(stock * sell_price), 0) FROM inventory_items"
    ).fetchone()[0]
    sales_count   = q("SELECT COUNT(*) FROM sales")
    sales_revenue = conn.execute(
        "SELECT COALESCE(SUM(total_amount), 0) FROM sales"
    ).fetchone()[0]
    po_count      = q("SELECT COUNT(*) FROM purchase_orders")
    ret_count     = q("SELECT COUNT(*) FROM returns")
    cust_count    = q("SELECT COUNT(*) FROM customers")
    sup_count     = q("SELECT COUNT(*) FROM suppliers")
    txn_count     = q("SELECT COUNT(*) FROM inventory_transactions")

    print()
    print("=================================================")
    print("  VoltEdge Electronics -- Seed Summary")
    print("=================================================")
    print(f"  Inventory items : {total_items:>6,}  (stocked: {stocked_items:,})")
    print(f"  Low stock alerts: {low_stock:>6,}")
    print(f"  Out of stock    : {out_of_stock:>6,}")
    print(f"  Stock value     : €{total_value:>10,.2f}")
    print(f"  Suppliers       : {sup_count:>6,}")
    print(f"  Customers       : {cust_count:>6,}")
    print(f"  Sales           : {sales_count:>6,}  (revenue: €{sales_revenue:,.2f})")
    print(f"  Purchase orders : {po_count:>6,}")
    print(f"  Returns         : {ret_count:>6,}")
    print(f"  Txn log entries : {txn_count:>6,}")
    print("=================================================")
    print(f"  DB: {db.DB_PATH}")
    print()


# ── Phone Models & Units ───────────────────────────────────────────────────────────

PHONE_MODELS = [
    {"brand": "Apple", "name": "iPhone 16 Pro", "release_year": 2024},
    {"brand": "Apple", "name": "iPhone 16 Pro Max", "release_year": 2024},
    {"brand": "Apple", "name": "iPhone 16", "release_year": 2024},
    {"brand": "Apple", "name": "iPhone 16 Plus", "release_year": 2024},
    {"brand": "Apple", "name": "iPhone 15 Pro", "release_year": 2023},
    {"brand": "Apple", "name": "iPhone 15 Pro Max", "release_year": 2023},
    {"brand": "Samsung", "name": "Galaxy S25 Ultra", "release_year": 2025},
    {"brand": "Samsung", "name": "Galaxy S25+", "release_year": 2025},
    {"brand": "Samsung", "name": "Galaxy S25", "release_year": 2025},
    {"brand": "Samsung", "name": "Galaxy S24 Ultra", "release_year": 2024},
    {"brand": "Samsung", "name": "Galaxy S24+", "release_year": 2024},
    {"brand": "Samsung", "name": "Galaxy Z Fold 6", "release_year": 2024},
    {"brand": "Samsung", "name": "Galaxy Z Flip 6", "release_year": 2024},
    {"brand": "Google", "name": "Pixel 9 Pro", "release_year": 2024},
    {"brand": "Google", "name": "Pixel 9 Pro XL", "release_year": 2024},
    {"brand": "Google", "name": "Pixel 8 Pro", "release_year": 2023},
    {"brand": "Xiaomi", "name": "14 Ultra", "release_year": 2024},
    {"brand": "Xiaomi", "name": "14 Pro", "release_year": 2024},
    {"brand": "OnePlus", "name": "12", "release_year": 2024},
    {"brand": "OnePlus", "name": "12R", "release_year": 2024},
]


def seed_phones() -> None:
    """Seed phone models and generate realistic phone units with IMEIs."""
    conn = db.get_connection()

    # Insert phone models
    model_ids: dict[str, int] = {}
    for model in PHONE_MODELS:
        cursor = conn.execute(
            "INSERT INTO phone_models (brand, name, release_year) VALUES (?, ?, ?)",
            (model["brand"], model["name"], model["release_year"])
        )
        model_ids[f"{model['brand']} {model['name']}"] = cursor.lastrowid
    print(f"  → Inserted {len(PHONE_MODELS)} phone models")

    # Generate phone units with realistic IMEIs
    STORAGE_OPTIONS = ["64GB", "128GB", "256GB", "512GB", "1TB"]
    CONDITION_OPTIONS = ["new", "like_new", "used", "refurbished"]
    STATUS_OPTIONS = ["in_stock", "reserved", "sold", "repair"]

    phone_units: list[tuple] = []
    total_units = 0

    for model_key, model_id in model_ids.items():
        # Generate 5-15 units per model
        num_units = RNG.randint(5, 15)
        for i in range(num_units):
            storage = RNG.choice(STORAGE_OPTIONS)
            condition = RNG.choice(CONDITION_OPTIONS)
            status = RNG.choice(STATUS_OPTIONS, weights=[0.5, 0.1, 0.3, 0.1])[0]

            # Generate realistic IMEI (15 digits, starts with valid TAC)
            # Real IMEIs start with manufacturer-specific TAC codes
            tac = "35" + str(RNG.randint(100000, 999999))  # Valid TAC format
            serial = str(RNG.randint(100000, 999999))
            imei = tac + serial + str(RNG.randint(0, 9))  # 15 digits total

            # Generate sell price based on model and storage
            base_price = {
                "iPhone 16 Pro": 999, "iPhone 16 Pro Max": 1099,
                "iPhone 16": 799, "iPhone 16 Plus": 899,
                "iPhone 15 Pro": 899, "iPhone 15 Pro Max": 999,
                "Galaxy S25 Ultra": 1299, "Galaxy S25+": 999,
                "Galaxy S25": 799, "Galaxy S24 Ultra": 1199,
                "Galaxy S24+": 899, "Galaxy Z Fold 6": 1799,
                "Galaxy Z Flip 6": 999, "Pixel 9 Pro": 999,
                "Pixel 9 Pro XL": 1099, "Pixel 8 Pro": 899,
                "Xiaomi 14 Ultra": 999, "Xiaomi 14 Pro": 799,
                "OnePlus 12": 799, "OnePlus 12R": 599,
            }.get(model_key, 699)

            storage_multiplier = {"64GB": 1.0, "128GB": 1.1, "256GB": 1.2, "512GB": 1.35, "1TB": 1.5}[storage]
            condition_multiplier = {"new": 1.0, "like_new": 0.95, "used": 0.85, "refurbished": 0.8}[condition]
            sell_price = round(base_price * storage_multiplier * condition_multiplier, 2)

            battery_health = RNG.randint(75, 100) if condition != "new" else 100

            phone_units.append((
                model_id, imei, storage, condition, status,
                sell_price, battery_health, "",  # notes
            ))
            total_units += 1

    # Batch insert phone units
    conn.executemany(
        """INSERT INTO phones (model_id, imei, storage, condition, status, sell_price, battery_health, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        phone_units
    )
    conn.commit()
    print(f"  → Inserted {total_units} phone units with IMEIs")

    # Link some inventory items to phone models for parts compatibility
    # Get display part types
    display_pt_id = conn.execute("SELECT id FROM part_types WHERE key='displays'").fetchone()
    if display_pt_id:
        display_pt_id = display_pt_id[0]

        # Link iPhone models to specific display colors
        iphone_models = [mid for key, mid in model_ids.items() if "iPhone" in key]
        for model_id in iphone_models[:3]:  # Link first 3 iPhone models
            conn.execute(
                """INSERT INTO model_part_type_colors (model_id, part_type_id, color_name)
                   VALUES (?, ?, ?)""",
                (model_id, display_pt_id, "Black")
            )
            conn.execute(
                """INSERT INTO model_part_type_colors (model_id, part_type_id, color_name)
                   VALUES (?, ?, ?)""",
                (model_id, display_pt_id, "White")
            )
        conn.commit()
        print(f"  → Linked phone models to display parts")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n>>  VoltEdge Electronics -- seeding demo database")
    print("-------------------------------------------------")

    print("[0/14] Resetting database...")
    reset_database()

    print("[1/14] Configuring shop...")
    configure_shop()

    print("[2/14] Seeding locations...")
    location_ids = seed_locations()

    print("[3/14] Seeding extended part types...")
    seed_extended_part_types()
    materialize_matrix_items()

    print("[4/14] Seeding suppliers...")
    supplier_ids = seed_suppliers()

    print("[5/14] Seeding customers...")
    customer_ids, segment_map = seed_customers()

    print("[6/14] Pricing & stocking all matrix items...")
    matrix_pool = seed_matrix_stock(supplier_ids)

    print("[7/14] Seeding electronics products...")
    electronics_pool = seed_electronics(supplier_ids)

    print("[8/14] Creating sales history...")
    sale_ids = seed_sales(customer_ids, segment_map, matrix_pool, electronics_pool)

    print("[9/14] Creating purchase orders...")
    seed_purchase_orders(supplier_ids, matrix_pool, electronics_pool)

    print("[10/14] Processing returns...")
    seed_returns(sale_ids, matrix_pool, electronics_pool)

    print("[11/14] Completing inventory audit & price lists...")
    seed_audit()
    seed_price_lists()

    print("[12/14] Creating stock transfers...")
    seed_stock_transfers(location_ids)

    print("[13/14] Rebuilding location distribution from final stock...")
    rebuild_location_distribution(location_ids)

    print("[14/14] Seeding phone models and units...")
    seed_phones()

    print_summary()
    print("[OK] Seed complete -- launch the app and capture screenshots\n")


if __name__ == "__main__":
    main()
