"""
app/core/demo_data.py — Optional Galaxy@Phone demo seed data.

Imported ONLY when the user explicitly requests demo data
(setup wizard or Admin → Load Demo Data). Never imported during schema init.
"""
from __future__ import annotations

DEMO_CATEGORIES: list[tuple] = [
    # (key, name_en, name_de, name_ar, sort_order, icon)
    ("displays",       "Displays",       "Displays",      "الشاشات",         1, "🖥"),
    ("batteries",      "Batteries",      "Akkus",         "البطاريات",       2, "⚡"),
    ("cases",          "Cases",          "Gehäuse",       "الأغطية",         3, "📱"),
    ("cameras",        "Cameras",        "Kameras",       "الكاميرات",       4, "📷"),
    ("charging_ports", "Charging Ports", "Ladebuchsen",   "منافذ الشحن",     5, "🔌"),
    ("back_covers",    "Back Covers",    "Rückdeckel",    "الأغطية الخلفية", 6, "🔲"),
]

DEMO_PART_TYPES: dict[str, list[tuple]] = {
    # category_key → [(key, name, accent_color, sort_order), ...]
    "displays": [
        ("JK_INCELL_FHD",     "(JK) incell FHD",          "#4A9EFF", 1),
        ("DD_SOFT_OLED",      "(D.D) Soft-OLED",           "#32D583", 2),
        ("DD_SOFT_OLED_DIAG", "(D.D) Soft-OLED Diagnose",  "#C17BFF", 3),
        ("ORG_PULLED",        "ORG-Pulled",                "#FF9F3A", 4),
        ("ORG_DIAGNOSE_USED", "ORG-Diagnose USED",         "#FF5A52", 5),
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

DEMO_PHONE_MODELS: list[tuple] = [
    # (brand, name, sort_order)
    ("Apple", "X",              1),  ("Apple", "XS",             2),
    ("Apple", "XS max",         3),  ("Apple", "XR",             4),
    ("Apple", "11 Pro",         5),  ("Apple", "11 Pro max",     6),
    ("Apple", "12 mini",        7),  ("Apple", "12 / 12 Pro",    8),
    ("Apple", "12 Pro max",     9),  ("Apple", "13 mini",       10),
    ("Apple", "13",            11),  ("Apple", "13 Pro",        12),
    ("Apple", "13 Pro max",    13),  ("Apple", "14",            14),
    ("Apple", "14 Plus",       15),  ("Apple", "14 Pro",        16),
    ("Apple", "14 Pro max",    17),  ("Apple", "15",            18),
    ("Apple", "15 Plus",       19),  ("Apple", "15 Pro",        20),
    ("Apple", "15 Pro max",    21),  ("Apple", "16",            22),
    ("Apple", "16 Plus",       23),  ("Apple", "16 Pro",        24),
    ("Apple", "16 Pro max",    25),
    ("Samsung", "Galaxy S21",        1), ("Samsung", "Galaxy S21+",       2),
    ("Samsung", "Galaxy S21 Ultra",  3), ("Samsung", "Galaxy S22",        4),
    ("Samsung", "Galaxy S22+",       5), ("Samsung", "Galaxy S22 Ultra",  6),
    ("Samsung", "Galaxy S23",        7), ("Samsung", "Galaxy S23+",       8),
    ("Samsung", "Galaxy S23 Ultra",  9), ("Samsung", "Galaxy S24",       10),
    ("Samsung", "Galaxy S24+",      11), ("Samsung", "Galaxy S24 Ultra", 12),
    ("Samsung", "Galaxy A32",       13), ("Samsung", "Galaxy A52",       14),
    ("Samsung", "Galaxy A53",       15), ("Samsung", "Galaxy A54",       16),
    ("Samsung", "Galaxy A72",       17),
]
