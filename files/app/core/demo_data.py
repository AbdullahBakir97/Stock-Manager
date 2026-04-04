"""
app/core/demo_data.py — Optional Galaxy@Phone demo seed data.

Display part types are brand-specific:
  Apple  → JK incell, DD Soft-OLED, DD Diagnose, ORG-Pulled, ORG-Diagnose USED
  Samsung/Xiaomi → ORG Service Pack, OLED
"""
from __future__ import annotations

DEMO_CATEGORIES: list[tuple] = [
    ("displays",       "Displays",       "Displays",      "الشاشات",         1, "🖼"),
    ("batteries",      "Batteries",      "Akkus",         "البطاريات",       2, "🔋"),
    ("cases",          "Cases",          "Gehäuse",       "الأغطية",         3, "📱"),
    ("cameras",        "Cameras",        "Kameras",       "الكاميرات",       4, "📷"),
    ("charging_ports", "Charging Ports", "Ladebuchsen",   "منافذ الشحن",     5, "🔌"),
    ("back_covers",    "Back Covers",    "Rückdeckel",    "الأغطية الخلفية", 6, "🛡"),
]

DEMO_PART_TYPES: dict[str, list[tuple]] = {
    "displays": [
        ("JK_INCELL_FHD",     "(JK) incell FHD",          "#4A9EFF", 1),
        ("DD_SOFT_OLED",      "(D.D) Soft-OLED",           "#32D583", 2),
        ("DD_SOFT_OLED_DIAG", "(D.D) Soft-OLED Diagnose",  "#C17BFF", 3),
        ("ORG_PULLED",        "ORG-Pulled",                "#FF9F3A", 4),
        ("ORG_DIAGNOSE_USED", "ORG-Diagnose USED",         "#FF5A52", 5),
        ("SM_ORG_SERVICE",    "ORG Service Pack",          "#10B981", 6),
        ("SM_OLED",           "OLED",                      "#3B82F6", 7),
    ],
    "batteries": [
        ("ORG_AKKU",        "Org Akku",        "#32D583", 1),
        ("ORG_AKKU_DECODE", "Org Akku Decode", "#4A9EFF", 2),
    ],
    "cases": [
        ("BLACK",    "Black",    "#555555", 1),
        ("GOLD",     "Gold",     "#FFD700", 2),
        ("BLUE",     "Blue",     "#4A9EFF", 3),
        ("TITANIUM", "Titanium", "#A0A8B0", 4),
        ("PURPLE",   "Purple",   "#C17BFF", 5),
        ("WHITE",    "White",    "#D0D0D0", 6),
    ],
    "cameras": [
        ("BACK_CAMERA",      "ORG-Back Camera",      "#32D583", 1),
        ("ORG_FULL_BCAMERA", "ORG-full Back Camera", "#FF9F3A", 2),
    ],
    "charging_ports": [
        ("LADEBUCHSE", "Ladebuchse", "#4A9EFF", 1),
    ],
    "back_covers": [
        ("BACK_COVER", "Back Cover", "#FF9F3A", 1),
        ("NFC",        "NFC",        "#32D583", 2),
    ],
}

DISPLAY_BRAND_MAP: dict[str, list[str]] = {
    "Apple":   ["JK_INCELL_FHD", "DD_SOFT_OLED", "DD_SOFT_OLED_DIAG", "ORG_PULLED", "ORG_DIAGNOSE_USED"],
    "Samsung": ["SM_ORG_SERVICE", "SM_OLED"],
    "Xiaomi":  ["SM_ORG_SERVICE", "SM_OLED"],
}

# Models to EXCLUDE from specific Apple display part types
# part_type_key → list of model names that should NOT have this type
DISPLAY_EXCLUSIONS: dict[str, list[str]] = {
    "JK_INCELL_FHD": [
        "17", "17 Pro", "17 Pro max",
    ],
    "DD_SOFT_OLED": [
        "11",
    ],
    "DD_SOFT_OLED_DIAG": [
        "X", "XS", "XS max", "XR",
        "11", "11 Pro", "11 Pro max",
        "12 mini", "12 / 12 Pro", "12 Pro max", "13 mini",
        "13", "14 Plus", "15 Plus",
        "16", "16 Pro", "16 Pro max",
        "17", "17 Pro", "17 Pro max",
    ],
    "ORG_DIAGNOSE_USED": [
        "X", "XS", "XS max", "XR",
        "11", "11 Pro", "11 Pro max",
        "12 mini", "12 / 12 Pro", "12 Pro max",
        "13", "13 mini",
        "14", "14 Plus",
        "15 Plus",  "16 Plus",
    ],
}

# Colors available per part type (only for Samsung display types)
# part_type_key → [(color_name, barcode_code, sort_order), ...]
DEMO_PART_TYPE_COLORS: dict[str, list[tuple[str, str, int]]] = {
    "SM_ORG_SERVICE": [
        ("Black",  "BLK", 1),
        ("Blue",   "BLU", 2),
        ("Silver", "SLV", 3),
        ("Gold",   "GLD", 4),
        ("Green",  "GRN", 5),
        ("Purple", "PRP", 6),
        ("White",  "WHT", 7),
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
}

DEMO_PHONE_MODELS: list[tuple] = [
    # ── Apple (sorted: X, XS, XR, then 11→17) ───────────────────────────────
    ("Apple", "X",              1),
    ("Apple", "XS",             2),
    ("Apple", "XS max",         3),
    ("Apple", "XR",             4),
    ("Apple", "11",             5),
    ("Apple", "11 Pro",         6),
    ("Apple", "11 Pro max",     7),
    ("Apple", "12 mini",        8),
    ("Apple", "12 / 12 Pro",    9),
    ("Apple", "12 Pro max",    10),
    ("Apple", "13 mini",       11),
    ("Apple", "13",            12),
    ("Apple", "13 Pro",        13),
    ("Apple", "13 Pro max",    14),
    ("Apple", "14",            15),
    ("Apple", "14 Plus",       16),
    ("Apple", "14 Pro",        17),
    ("Apple", "14 Pro max",    18),
    ("Apple", "15",            19),
    ("Apple", "15 Plus",       20),
    ("Apple", "15 Pro",        21),
    ("Apple", "15 Pro max",    22),
    ("Apple", "16",            23),
    ("Apple", "16 Pro",        24),
    ("Apple", "16 Pro max",    25),
    ("Apple", "17",            26),
    ("Apple", "17 Pro",        27),
    ("Apple", "17 Pro max",    28),
    # ── Samsung Series A (with 4G/5G variants) ─────────────────────────────────
    ("Samsung", "Galaxy A04 (A045F)",          101),
    ("Samsung", "Galaxy A04e (A042F)",         102),
    ("Samsung", "Galaxy A04s (A047F)",         103),
    ("Samsung", "Galaxy A05 (A055F)",          104),
    ("Samsung", "Galaxy A05s (A057F)",         105),
    ("Samsung", "Galaxy A06",                  106),
    ("Samsung", "Galaxy A07",                  107),
    ("Samsung", "Galaxy A12 (A125F)",          108),
    ("Samsung", "Galaxy A12 Nacho (A127F)",    109),
    ("Samsung", "Galaxy A13 4G (A135F)",       110),
    ("Samsung", "Galaxy A13 5G (A136B)",       111),
    ("Samsung", "Galaxy A14 4G (A145F)",       112),
    ("Samsung", "Galaxy A14 5G (A146B)",       113),
    ("Samsung", "Galaxy A15 4G (A155F)",       114),
    ("Samsung", "Galaxy A15 5G (A156B)",       115),
    ("Samsung", "Galaxy A16 4G",               116),
    ("Samsung", "Galaxy A16 5G",               117),
    ("Samsung", "Galaxy A17 4G",               118),
    ("Samsung", "Galaxy A17 5G",               119),
    ("Samsung", "Galaxy A23 4G (A235F)",       120),
    ("Samsung", "Galaxy A23 5G (A236B)",       121),
    ("Samsung", "Galaxy A24 (A245F)",          122),
    ("Samsung", "Galaxy A25 5G (A256B)",       123),
    ("Samsung", "Galaxy A32 4G (A325F)",       124),
    ("Samsung", "Galaxy A32 5G (A326B)",       125),
    ("Samsung", "Galaxy A33 5G (A336B)",       126),
    ("Samsung", "Galaxy A34 5G (A346B)",       127),
    ("Samsung", "Galaxy A35 5G (A356B)",       128),
    ("Samsung", "Galaxy A36",                  129),
    ("Samsung", "Galaxy A52 (A525F)",          130),
    ("Samsung", "Galaxy A52 5G (A526B)",       131),
    ("Samsung", "Galaxy A52s 5G (A528B)",      132),
    ("Samsung", "Galaxy A53 5G (A536B)",       133),
    ("Samsung", "Galaxy A54 5G (A546B)",       134),
    ("Samsung", "Galaxy A55 5G (A556B)",       135),
    ("Samsung", "Galaxy A56 5G",               136),
    # ── Samsung Series S / Note (sorted S10→S25, Note) ───────────────────────
    ("Samsung", "Galaxy S10",         201),
    ("Samsung", "Galaxy S10+",        202),
    ("Samsung", "Galaxy S20 FE",      203),
    ("Samsung", "Galaxy S20 Ultra",   204),
    ("Samsung", "Galaxy S21",         205),
    ("Samsung", "Galaxy S21 FE",      206),
    ("Samsung", "Galaxy S21 Ultra",   207),
    ("Samsung", "Galaxy S22",         208),
    ("Samsung", "Galaxy S22 FE",      209),
    ("Samsung", "Galaxy S22 Ultra",   210),
    ("Samsung", "Galaxy S23",         211),
    ("Samsung", "Galaxy S23 FE",      212),
    ("Samsung", "Galaxy S23 Ultra",   213),
    ("Samsung", "Galaxy S24",         214),
    ("Samsung", "Galaxy S24 FE",      215),
    ("Samsung", "Galaxy S24 Ultra",   216),
    ("Samsung", "Galaxy S25",         217),
    ("Samsung", "Galaxy S25 Ultra",   218),
    ("Samsung", "Galaxy Note10+",     219),
    ("Samsung", "Galaxy Note20 Ultra", 220),
    # ── Xiaomi / Redmi ───────────────────────────────────────────────────────
    ("Xiaomi", "Redmi A5",              301),
    ("Xiaomi", "Redmi 13C",             302),
    ("Xiaomi", "Redmi 14C",             303),
    ("Xiaomi", "Redmi 15C",             304),
    ("Xiaomi", "Redmi Note 11",         305),
    ("Xiaomi", "Redmi Note 11 Pro",     306),
    ("Xiaomi", "Redmi Note 11 Pro+",    307),
    ("Xiaomi", "Redmi Note 12",         308),
    ("Xiaomi", "Redmi Note 12 Pro",     309),
    ("Xiaomi", "Redmi Note 12 Pro+",    310),
    ("Xiaomi", "Redmi Note 13",         311),
    ("Xiaomi", "Redmi Note 13 Pro",     312),
    ("Xiaomi", "Redmi Note 13 Pro+",    313),
    ("Xiaomi", "Redmi Note 14",         314),
    ("Xiaomi", "Redmi Note 14 Pro",     315),
    ("Xiaomi", "Redmi Note 14 Pro+",    316),
]
