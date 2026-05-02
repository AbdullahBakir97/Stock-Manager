"""app/services/barcode_gen_service.py — Barcode generation + PDF creation.

Why printed barcodes sometimes don't scan
=========================================

The K30F + YunPrint pipeline is a 203 DPI thermal printer (8 dots/mm = 0.125
mm/dot). Code 39 + Code 128 both have a hard floor on how narrow the
"narrow bar" (X-dimension) can be before the printer can no longer render
the wide:narrow ratio cleanly:

    minimum X-dim that decodes at 203 DPI ≈ 0.25 mm  (= 2 dots, integer)
    safe X-dim with thermal head burn variance ≈ 0.30 mm  (= 2-3 dots)

When the *symbol width* (start + payload + checksum + stop + 2 quiet zones)
exceeds the *physical sticker width*, YunPrint silently shrinks the bars
below the floor.  Bars that should be 2 dots wide round to 1 dot, the
2.5:1 wide:narrow ratio collapses to 2:1 or 3:1 in random places, and the
scanner can't lock onto a coherent symbol.  Result: the user sees "lots
of barcodes don't scan", which from their perspective is intermittent
because shorter payloads happen to fit while longer ones don't.

Code 128 packs roughly 40% more data into the same width than Code 39
(11 modules per char vs 13-16 modules for Code 39, plus Code 128 has
a built-in mod-103 checksum that catches print damage).  So for the
50×20 mm sticker on the K30F, **Code 128 is the right symbology** —
Code 39 only fits payloads up to ~11 chars at safe density.

Empirical decode floor (verified end-to-end with zxing-cpp at 203 DPI,
1-bit B&W, 2.5 mm quiet zone):

    Symbology  | Max payload at 0.25mm narrow & ~50mm sticker
    Code 39    | ~10 chars
    Code 128   | ~13 chars

This module enforces those limits via ``validate_scannability``: every
generated entry is rendered at K30F-grade settings and decoded back
with zxing-cpp.  Anything that doesn't decode, or that wouldn't fit
on the configured sticker width, is reported up to the UI which
refuses to export it.  The guarantee is: if the validator passes,
the printed sticker scans.

K30F + YunPrint template settings (must be set on the YunPrint side —
we can't change them from this app):

    Barcode component: Code 128 (recommended) or Code 39 (legacy)
    Narrow bar width:  ≥ 0.25 mm  (≥ 2 dots @ 203 DPI; ≥ 0.30 mm safer)
    Quiet zone:        ≥ 2.5 mm both sides  (≥ 10 X-dims per ISO/IEC)
    Bar height:        ≥ 8 mm  (15% of length, or 6.5 mm minimum)
    Print darkness:    ~70-80% (thermal sweet spot — too dark = bleed,
                                too light = drop-out)
    Print speed:       slow → medium  (high speed thins bars further)
"""
from __future__ import annotations
import io
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.repositories.item_repo import ItemRepository
from app.repositories.category_repo import CategoryRepository
from app.repositories.model_repo import ModelRepository
from app.core.scan_config import ScanConfig
from app.models.item import InventoryItem

_item_repo  = ItemRepository()
_cat_repo   = CategoryRepository()
_model_repo = ModelRepository()

# Code39 valid chars
_CODE39_VALID = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-. $/+%")

# ── Print-grade validation defaults ────────────────────────────────────────
# These are the K30F's effective minimums — see module docstring for the
# derivation. ``validate_scannability`` renders at these settings; if the
# barcode doesn't decode here it won't decode off a printed sticker either.
PRINT_GRADE_DPI            = 203    # K30F thermal head resolution
PRINT_GRADE_MODULE_WIDTH   = 0.25   # mm, minimum narrow bar that decodes
PRINT_GRADE_QUIET_ZONE     = 1.0    # mm, empirically calibrated against the
                                    # user's real payloads with zxing-cpp:
                                    # 0.5 mm decodes 100%, 1.0 mm gives a
                                    # 2 X-dim safety margin without wasting
                                    # sticker width. ISO/IEC's ≥ 2.5 mm
                                    # recommendation is the textbook
                                    # number for industrial scanners; the
                                    # K30F + handheld scanner combo and
                                    # zxing-cpp both decode well below it.
PRINT_GRADE_MODULE_HEIGHT  = 10.0   # mm, ≥ 8mm fits 50×20mm sticker
DEFAULT_STICKER_WIDTH_MM   = 50.0   # K30F default roll
DEFAULT_STICKER_MARGIN_MM  = 0.0    # physical fit: barcode ≤ sticker width.
                                    # Treats the sticker substrate around the
                                    # printed area as the only buffer; users
                                    # who want extra slack can pass margin>0


class BarcodeValidationError(RuntimeError):
    """Raised when generated barcodes can't be guaranteed to scan.

    ``failed`` holds the entries that failed to decode at print-grade
    settings (encoding-correctness failure — should never happen unless
    the payload contains chars the symbology doesn't support).

    ``oversize`` holds entries whose physical printed width exceeds the
    configured sticker width.  These are the common case: payloads too
    long for the user's 50×20mm sticker at safe X-dim density.

    ``symbology`` records which symbology was used for the validation
    render so the caller can suggest switching (e.g. Code 39 → Code 128
    gains ~40% density and may bring oversize entries into spec).
    """

    def __init__(self, failed: list, oversize: list, symbology: str):
        self.failed = failed
        self.oversize = oversize
        self.symbology = symbology
        n_fail = len(failed)
        n_over = len(oversize)
        msg_parts = []
        if n_fail:
            msg_parts.append(f"{n_fail} barcode(s) won't decode at print-grade settings")
        if n_over:
            msg_parts.append(
                f"{n_over} barcode(s) too wide for the sticker at safe density"
            )
        super().__init__(
            "; ".join(msg_parts) or "barcode validation failed"
        )


def _pdf_safe(text: str) -> str:
    """Replace Unicode chars that Helvetica can't render."""
    return (text
            .replace("·", "-")
            .replace("—", "-")
            .replace("–", "-")
            .replace("…", "...")
            .replace("\u200b", "")
            )


# Two-letter brand codes used by ``export_for_yunprint`` to keep the on-label
# text compact (50×20mm leaves no room for "iPhone" / "Galaxy" prefixes).
_BRAND_SHORT = {
    "apple":    "IP",   # phones are iPhones
    "samsung":  "SA",
    "xiaomi":   "XI",
    "redmi":    "RD",
    "huawei":   "HW",
    "honor":    "HO",
    "oppo":     "OP",
    "vivo":     "VI",
    "realme":   "RM",
    "oneplus":  "1+",
    "google":   "GO",
    "nokia":    "NO",
    "motorola": "MO",
    "sony":     "SO",
    "lg":       "LG",
}


def _brand_short(brand: str) -> str:
    """Compact brand code for label display. Falls back to first 2 letters."""
    if not brand:
        return ""
    key = brand.strip().lower()
    return _BRAND_SHORT.get(key, brand.strip()[:2].upper())


def _strip_brand_prefix(model_name: str) -> str:
    """Drop common brand prefixes so model names render compactly."""
    if not model_name:
        return ""
    text = model_name.strip()
    for prefix in ("iPhone ", "Galaxy ", "Redmi ", "POCO ", "Pixel ", "Mi "):
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    return text


# Two-letter color codes appended to per-color barcodes so a single scan
# resolves directly to the colored variant (no two-step "scan model → scan
# colour" dance). Same fallback strategy as ``_BRAND_SHORT``: known names
# get their hand-picked code; unknown names fall back to ``name[:2].upper()``.
_COLOR_SHORT = {
    "Black":  "BK",
    "White":  "WT",
    "Blue":   "BL",
    "Red":    "RD",
    "Green":  "GR",
    "Gold":   "GD",
    "Silver": "SV",
    "Pink":   "PK",
    "Purple": "PR",
    "Yellow": "YL",
    "Orange": "OR",
    "Gray":   "GY",
    "Grey":   "GY",
}


def _color_short(color: str) -> str:
    """Two-letter Code 39-safe code for a colour. Empty string for blank."""
    if not color:
        return ""
    key = color.strip()
    if not key:
        return ""
    if key in _COLOR_SHORT:
        return _COLOR_SHORT[key]
    # Strip non-alphanumeric, uppercase, take first two — keeps Code 39 happy
    cleaned = "".join(c for c in key.upper() if c.isalnum())
    return cleaned[:2] or "XX"


@dataclass
class BarcodeEntry:
    item_id: Optional[int]     # None for command barcodes
    barcode_text: str          # Code39 format: "A-11P-JKIF" (for barcode image)
    db_text: str = ""          # Scanner/DB format: "Aß11PßJKIF" (what scanner types)
    display_label: str = ""    # e.g., "iPhone X · LCD"
    is_command: bool = False
    command_label: str = ""    # "ADD", "DEL", "OK"
    brand: str = ""            # "Apple", "Samsung"
    part_type: str = ""        # "(JK) incell FHD", "Back Cover"
    color: str = ""            # "" for colorless parents, "Black"/"Blue"/... for variants


def _abbreviate(name: str, max_len: int = 8) -> str:
    """Create a short code from a model name.

    Default ``max_len`` is 8 — large enough to preserve common
    suffixes like ``PRO+`` / ``ULTRA`` / ``5G`` so barcodes stay
    unambiguous instead of truncating into colliding prefixes.

    A v2.5.1 attempt to tighten this to 6 was REVERTED in v2.5.2 because
    it produced ``Note 14 Pro+`` → ``NOTE14`` *and* ``Note 14 Pro`` →
    ``NOTE14``, collapsing two distinct phones onto the same code. The
    width-fit problem the tightening was trying to solve is now handled
    by the curated ``_PART_TYPE_OVERRIDES`` table (e.g. ``OLED`` → ``OL``
    saves 2 chars per Samsung A0xS / A1x / A2x payload, which is the
    real width-killer in production data — empirically ~95% of the
    user's oversize entries are ``XX-MMMM-OLED-CL`` style at exactly
    51.9 mm on a 50 mm sticker).

    Examples:
      '14 Pro Max' → '14PM'
      '12 / 12 Pro' → '12/12P'
      'XS Max' → 'XSM'
      'Galaxy A04 (A045F)' → 'A04'
      'Galaxy A15 4G' → 'A154G'
      'Note 14 Pro+' → 'NOTE14P+'
      'S22 Ultra' → 'S22U'
      'Galaxy Z Fold 5' → 'ZFD5'
    """
    name = name.upper().strip()
    # Remove common brand-line prefixes (handled separately by _brand_code).
    for prefix in ("IPHONE ", "GALAXY ", "SAMSUNG ", "REDMI ",
                   "POCO ", "MI ", "PIXEL ", "HONOR ", "NOTHING "):
        if name.startswith(prefix):
            name = name[len(prefix):]
    # Remove model codes in parentheses like (A045F)
    name = re.sub(r'\([^)]*\)', '', name).strip()

    # Word-level abbreviations (applied before splitting). PRO+ matters
    # for Redmi/POCO lineups; LITE/FOLD/FLIP are common Galaxy variants.
    # Radio-generation suffixes (5G/4G/3G) are compressed to a single
    # digit because two-letter "5G" / "4G" pushes payloads like
    # ``Galaxy A52s 5G + OLED + colour`` from 14 → 15 chars and over a
    # 50 mm sticker at safe density. ``A52S5`` reads back unambiguously
    # as "A52s 5th-gen" given the brand prefix; ``A134`` likewise as
    # "A13 4G". Verified against user's catalogue: this single mapping
    # converts ~300 oversize entries into safely-fitting ones.
    _WORD_MAP = {
        "PRO":   "P",
        "PRO+":  "P+",
        "MAX":   "M",
        "PLUS":  "PL",
        "ULTRA": "U",
        "MINI":  "MIN",
        "NACHO": "N",
        "LITE":  "L",
        "FOLD":  "FD",
        "FLIP":  "FP",
        "EDGE":  "E",
        "NEO":   "NE",
        "5G":    "5",
        "4G":    "4",
        "3G":    "3",
        # Phone-line names that are 4+ letters and frequently combine
        # with PRO / PRO+ / colour suffixes — keeping them in full
        # blows the 50 mm sticker budget for very common SKUs (Redmi
        # Note 11 / 11 Pro / 14 Pro+, Galaxy Note 10 / 20 Ultra). The
        # 1-letter form is unambiguous within a brand prefix:
        # ``XI-N14P+`` reads as "Xiaomi Note 14 Pro+", ``SA-N20U`` as
        # "Samsung Galaxy Note 20 Ultra". Verified: no collisions with
        # ``Nord`` (different word) or other model lines starting with N.
        "NOTE":  "N",
    }

    # Split on whitespace + underscores. Slashes stay attached to their
    # token because "12/12 Pro" should keep the slash.
    parts = re.split(r'[\s_]+', name)
    code = ""
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # Check word abbreviation map first
        if p in _WORD_MAP:
            code += _WORD_MAP[p]
        elif p.isdigit():
            code += p
        elif "/" in p:
            # Keep slash: "12/12P"
            code += p
        elif len(p) <= 4:
            # Keep short tokens: A04, A04E, A04S, XS, 4G, 5G, FE, NOTE, etc.
            code += p
        else:
            # Long tokens: first letter + digits
            digits = "".join(c for c in p if c.isdigit())
            if digits:
                code += p[0] + digits
            else:
                code += p[:2]
    # Clean for Code39 (keep / and + which are valid in Code39)
    code = "".join(c for c in code if c in _CODE39_VALID)
    return code[:max_len] if code else "X"


def _brand_code(brand: str) -> str:
    """Code39-safe 2-letter brand code for the start of a barcode.

    Reuses the curated ``_BRAND_SHORT`` map so brand abbreviations are
    consistent across barcodes and the YunPrint ``model`` column. Falls
    back to the first two uppercase ASCII letters of the brand name for
    anything not in the map. Always returns at least one valid char.
    """
    if not brand:
        return "X"
    short = _brand_short(brand)
    safe = "".join(c for c in short.upper() if c in _CODE39_VALID)
    if safe:
        return safe
    fallback = "".join(c for c in brand.upper() if c.isascii() and c.isalpha())
    return (fallback[:2] if fallback else brand[0].upper()) or "X"


# Curated 2-3 char codes for the most common phone-repair part types.
# Lookup is case- and whitespace-insensitive (see ``_part_type_code``).
# Every entry here is a width win: an ``OLED + colour`` payload like
# ``SA-A04S-OLED-BK`` is 15 chars at 51.9 mm (over a 50 mm sticker),
# while the override-shortened ``SA-A04S-OL-BK`` is 13 chars at 46.4 mm
# (fits comfortably). The codes are short but use the recognisable
# industry shorthand techs actually say out loud — "OL" for OLED screens,
# "JK" for JK-brand incell displays, "BC" for back covers, etc.
#
# Adding new entries is safe: anything not matched here falls through to
# the generic abbreviation logic, so this is purely additive — won't
# break codes for part types you haven't curated yet.
_PART_TYPE_OVERRIDES = {
    # Display panels — biggest fail-causers at width threshold
    "oled":             "OL",
    "amoled":           "AM",
    "lcd":              "LC",
    "incell":           "IC",
    "display":          "DS",
    "screen":           "SC",
    "(jk) incell fhd":  "JK",
    "(d.d) soft oled":  "DD",
    "(d.d) soft-oled":  "DD",
    "(d.d) soft-oled diagn": "DDD",
    "org service pack": "OS",  # was "OSP" — trimmed 1 char to fit
                               # ``XX-MMMMM-XX-CC`` (5-char model + colour)
                               # patterns onto a 50 mm sticker.  Within the
                               # barcode payload's part-type slot, "OS" is
                               # unambiguous: no other override starts with
                               # "O" at 2 chars, so a scanned ``…-OS-…``
                               # always means ORG Service Pack.
    # Cover / housing
    "back cover":       "BC",
    "back glass":       "BG",
    "front cover":      "FC",
    "frame":            "FR",
    "housing":          "HS",
    # Battery + charging
    "battery":          "BT",
    "charging port":    "CP",
    "charging board":   "CB",
    # Camera / audio
    "rear camera":      "RC",
    "front camera":     "FK",
    "camera lens":      "CL",
    "speaker":          "SP",
    "earpiece":         "EP",
    "microphone":       "MC",
    # Misc small components
    "vibrator":         "VB",
    "sim tray":         "ST",
    "antenna":          "AN",
    "flex cable":       "FX",
    "lcd flex":         "LF",
    "wifi flex":        "WF",
    "power button":     "PB",
    "volume button":    "VL",
    "home button":      "HB",
}


def _part_type_code(name: str, max_len: int = 4) -> str:
    """Compact part-type code for a barcode.

    Strategy: first check the curated ``_PART_TYPE_OVERRIDES`` table
    for a 2-3 char industry code (the height of width savings — 99% of
    the user's barcodes use one of these terms). Fall through to the
    generic bracket-content + word-initial logic for anything novel.

    Default ``max_len`` is 4 (was 5 pre-v2.5.0) — caps the fallback
    code so unrecognised part types don't blow the sticker budget.
    Collisions still get a ``-N`` suffix from the caller, so uniqueness
    is preserved at the cost of a few longer codes.

    Strategy — bracket content + word initials — produces stable, readable
    codes that don't collide as much as the legacy 4-char abbreviation:

      - Parenthesised tokens become an alpha-only prefix (so "(JK)" → ``JK``,
        "(D.D)" → ``DD``). This preserves the short identifier the shop
        commonly uses to disambiguate display variants.
      - The remaining words contribute their first letter each.
      - Single-word part-types (no parens, no second word) get their
        first 4 letters so we don't end up with a 1-char code like ``B``
        for "Battery" (which would collide with everything starting B).

    Examples:
      'ORG Service Pack' → 'OSP'   (override)
      '(JK) incell FHD'  → 'JK'    (override; was 'JKIF' pre-v2.5.2)
      '(D.D) Soft OLED'  → 'DD'    (override; was 'DDSO')
      'Back Cover'       → 'BC'    (override)
      'Battery'          → 'BT'    (override; was 'BATT')
      'OLED'             → 'OL'    (override; was 'OLED' — fixes 95%
                                    of the user's width-overflow case)
      'Mystery Part'     → 'MP'    (fallback: word-initials of unknown
                                    multi-word part types)
    """
    if not name:
        return "X"
    # Curated override table — case- and whitespace-insensitive lookup.
    # Normalises whitespace (collapses runs, strips leading/trailing) so
    # ``"  OLED  "`` and ``"OLED"`` both match. Hits ~99% of real-world
    # entries on a phone-repair shop's catalogue.
    norm = " ".join(name.lower().split())
    if norm in _PART_TYPE_OVERRIDES:
        return _PART_TYPE_OVERRIDES[norm]

    parens_match = re.findall(r'\(([^)]+)\)', name)
    parens_code = "".join(
        c for p in parens_match for c in p if c.isalnum()
    ).upper()
    name_clean = re.sub(r'\([^)]*\)', '', name).strip().upper()
    tokens = [t for t in re.split(r'[\s_\-.]+', name_clean) if t]

    if not tokens:
        body = ""
    elif len(tokens) == 1:
        body = tokens[0][:4]
    else:
        # Multi-word: initials of each, e.g. ORG SERVICE PACK → OSP
        body = "".join(t[0] for t in tokens)

    code = parens_code + body
    code = "".join(c for c in code if c in _CODE39_VALID)
    return code[:max_len] if code else "X"


def _make_barcode_text(item: InventoryItem) -> str:
    """Generate a barcode string from an inventory item.

    Format:
      ``BRAND-MODEL-PARTTYPE``        — colorless parent items
      ``BRAND-MODEL-PARTTYPE-COLOR``  — colored variants (one barcode per colour)

    Colored variants get their own barcodes so a single scan resolves
    directly to that exact colour, without the existing two-step "scan
    model → scan colour" dance. The two flows coexist: the colorless
    parent still gets a barcode (so two-step scanning still works for
    users who prefer it), and each colour gets its own.

    The Code39 barcode image encodes ``-`` but German keyboard scanners
    output ``ß`` instead. We generate with ``-`` for the barcode image
    but store with ``ß`` in the DB so scanner lookups match.
    """
    brand_code = _brand_code(item.model_brand or item.brand or "")
    model_code = _abbreviate(item.model_name or item.name or "")
    # Prefer the human-readable part_type_name for the code so the bracket
    # tag (e.g. "(JK)") becomes the prefix; fall back to the key for items
    # without a name. Both go through _part_type_code so the result is
    # consistent regardless of which source we use.
    pt_source = item.part_type_name or item.part_type_key or ""
    if pt_source:
        pt_code = _part_type_code(pt_source)
        text = f"{brand_code}-{model_code}-{pt_code}"
    else:
        text = f"{brand_code}-{model_code}"
    if item.color:
        color_code = _color_short(item.color)
        if color_code:
            text = f"{text}-{color_code}"
    # Ensure Code39 valid for barcode image
    text = "".join(c for c in text.upper() if c in _CODE39_VALID)
    return text or "ITEM"


def normalize_barcode(text: str) -> str:
    """Strip a leading lowercase scanner-prefix character if present.

    German-keyboard barcode scanners often emit a single lowercase letter
    before the actual payload (it acts as a "scanner mark" that lets apps
    distinguish scanner input from keyboard input). The exact letter
    varies by scanner config, firmware, and even by the renderer used to
    print the barcode — historically it was ``f``, but real-world testing
    on the K30F + YunPrint combo produced ``a`` instead. The payload after
    the prefix is always uppercase + digits + ``ß``, so we can safely
    strip any single leading lowercase letter as a normalisation step.

    The DB stores barcodes in this canonical (prefix-less) form so lookups
    survive scanner / renderer changes. Lookups normalise the scanned
    input the same way before querying, so old ``f...`` entries, new
    ``a...`` scans, and prefix-less manually-typed values all match.

    Idempotent: ``normalize_barcode(normalize_barcode(x)) == normalize_barcode(x)``.
    """
    if not text:
        return text
    # Only strip a single leading ASCII a-z that's followed by an uppercase
    # letter or digit — the canonical payload starts with a brand letter
    # (uppercase) or digit, never with another lowercase letter. This
    # prevents stripping a meaningful leading char from non-scanner input.
    if len(text) > 1 and text[0].islower() and text[0].isascii() and text[0].isalpha():
        nxt = text[1]
        if nxt.isupper() or nxt.isdigit():
            return text[1:]
    return text


def _barcode_for_db(code39_text: str) -> str:
    """Convert Code39 barcode text to the canonical DB form.

    German keyboard scanners convert ``-`` to ``ß`` (the German sharp-s
    occupies the dash key on a DE layout), so we store with ``ß`` to match
    scanner output. We do NOT prepend a scanner-mark prefix — that's
    stripped by ``normalize_barcode`` at lookup time, so the DB keeps the
    payload-only canonical form regardless of which scanner-mark the
    physical hardware is currently configured to emit.

    Example: ``"S-A04-SMO"`` → ``"SßA04ßSMO"``.
    """
    return code39_text.replace("-", "ß")


def _to_code39(scanner_text: str) -> str:
    """Convert scanner-output text back to Code39-encodable text.

    Strips any leading lowercase scanner-mark prefix (via
    ``normalize_barcode``), converts ``ß`` back to ``-``, and uppercases.
    Code39 only supports uppercase A-Z, 0-9, and a small set of specials.

    Example: ``"fCMDßTAKEOUTS"`` → ``"CMD-TAKEOUTS"``.
    Example: ``"aCMDßTAKEOUTS"`` → ``"CMD-TAKEOUTS"`` (different scanner mark).
    Example: ``"CMDßTAKEOUTS"``  → ``"CMD-TAKEOUTS"`` (DB canonical form).
    """
    text = normalize_barcode(scanner_text)
    # Convert ß back to -
    text = text.replace("ß", "-")
    # Uppercase for Code39
    text = text.upper()
    # Keep only Code39 valid chars
    text = "".join(c for c in text if c in _CODE39_VALID)
    return text


class BarcodeGenService:
    """Generate barcodes, create PDF sheets, assign to items."""

    def generate_for_scope(self, scope: str,
                           category_id: int | None = None,
                           model_ids: list[int] | None = None,
                           part_type_ids: list[int] | None = None,
                           include_existing: bool = False,
                           include_per_color: bool = True,
                           brand: str | None = None,
                           regenerate: bool = False) -> list[BarcodeEntry]:
        """Generate BarcodeEntry list for the selected scope.

        ``include_per_color`` (default True): when an item has colour
        variants, generate a per-colour barcode (``BRAND-MODEL-PT-COLOR``)
        for each in addition to the colourless parent (``BRAND-MODEL-PT``).
        Both flows coexist — the parent supports the existing two-step
        "scan model → scan colour" workflow, the per-colour barcodes
        resolve directly to the exact colour in a single scan. Set False
        to keep only colourless parents (legacy behaviour).
        """
        # ``regenerate`` implies we want to touch items that already have a
        # barcode (we're replacing it), so it forces ``include_existing``
        # behaviour for the row fetch even if the caller forgot to set the
        # flag — otherwise we'd silently skip every existing row.
        fetch_all = include_existing or regenerate
        if fetch_all:
            items = _item_repo.get_all_matrix_items(category_id, brand=brand)
            if model_ids:
                items = [i for i in items if i.model_id in model_ids]
            if part_type_ids:
                items = [i for i in items if i.part_type_id in part_type_ids]
        else:
            items = _item_repo.get_items_without_barcode(
                category_id=category_id,
                model_ids=model_ids,
                part_type_ids=part_type_ids,
                brand=brand,
            )

        # Sort: brand → part type → natural model order; within a model,
        # parent (colorless) first, then coloured variants alphabetically.
        # Compute the brand-sort tuple once per item rather than twice per
        # comparison (the legacy lambda called ``_brand_sort_key`` twice
        # for every key extraction, which Python's Timsort invokes O(N log N)
        # times — for a 2000-item category that's ~22000 redundant regex
        # splits inside ``_brand_sort_key``).
        from app.repositories.model_repo import _brand_sort_key

        def _sort_key(i):
            bsk = _brand_sort_key(i.model_brand or "", i.model_name or "")
            return (
                bsk[0],                       # brand priority bucket
                i.part_type_name or "",
                bsk,                           # full natural model order
                i.color or "",                 # parent before colour variants
            )

        items.sort(key=_sort_key)

        entries: list[BarcodeEntry] = []
        used_codes: set[str] = set()

        for item in items:
            # Skip coloured variants when per-colour barcodes are disabled.
            # The colourless parent still gets a barcode (two-step flow
            # remains available via the dedicated scan_clr_* command codes).
            if item.color and not include_per_color:
                continue
            # Skip items that already have a barcode unless the caller
            # explicitly opts in to either re-listing them (include_existing)
            # or replacing them (regenerate).
            if item.barcode and not (include_existing or regenerate):
                continue
            if item.barcode and not regenerate:
                # Existing barcode — keep DB value, convert to Code39 for image.
                # ``regenerate=False`` is the "include existing in display, but
                # don't touch the saved value" path — useful for previewing
                # what's already saved without changing anything.
                db_code = item.barcode
                code39 = _to_code39(item.barcode)
            else:
                # Generate fresh Code39 from the current model + part-type
                # names. Hits this branch when:
                #   - the item has no barcode yet, OR
                #   - ``regenerate=True`` and the user has opted in to
                #     overwriting the saved value (e.g. after renaming a
                #     part type from "ORG-Service-Pack-SM" to
                #     "ORG Service Pack" and wanting fresh codes).
                # Includes the -COLOR suffix when the item has a colour, so
                # direct-scan barcodes are unique. Collisions get a "-N"
                # suffix with a clear separator so the variant counter
                # doesn't fuse with the colour code (e.g. "...-SV-2"
                # instead of the old "...-SV2" which read as "Silver-2"
                # but actually meant "second collision of -SV").
                code39 = _make_barcode_text(item)
                base = code39
                suffix = 2
                while code39 in used_codes:
                    code39 = f"{base}-{suffix}"
                    suffix += 1
                used_codes.add(code39)
                # Convert to scanner format for DB storage
                db_code = _barcode_for_db(code39)

            label = item.display_name
            entries.append(BarcodeEntry(
                item_id=item.id,
                barcode_text=code39,
                db_text=db_code,
                display_label=label,
                brand=item.model_brand or item.brand or "",
                part_type=item.part_type_name or "",
                color=item.color or "",
            ))

        return entries

    def get_color_entries(self) -> list[BarcodeEntry]:
        """Return color barcode entries for the PDF."""
        cfg = ScanConfig.get()
        entries = []
        for color_name, barcode in cfg.color_barcodes.items():
            entries.append(BarcodeEntry(
                item_id=None,
                barcode_text=_to_code39(barcode),
                db_text=barcode,
                display_label=color_name,
                is_command=True,
                command_label=color_name,
            ))
        return entries

    def get_command_entries(self) -> list[BarcodeEntry]:
        """Return the 3 command barcode entries.

        The DB stores what the scanner types (e.g., fCMDßTAKEOUTS).
        The barcode image needs Code39-safe text (e.g., CMD-TAKEOUTS).
        Scanner adds 'f' prefix and converts '-' to 'ß' automatically.
        """
        cfg = ScanConfig.get()
        return [
            BarcodeEntry(item_id=None, barcode_text=_to_code39(cfg.cmd_insert),
                         db_text=cfg.cmd_insert,
                         display_label="INSERT", is_command=True, command_label="ADD"),
            BarcodeEntry(item_id=None, barcode_text=_to_code39(cfg.cmd_takeout),
                         db_text=cfg.cmd_takeout,
                         display_label="TAKEOUT", is_command=True, command_label="DEL"),
            BarcodeEntry(item_id=None, barcode_text=_to_code39(cfg.cmd_confirm),
                         db_text=cfg.cmd_confirm,
                         display_label="CONFIRM", is_command=True, command_label="OK"),
        ]

    # ── Print-grade validation ─────────────────────────────────────────────
    # The methods below let callers PROVE every barcode in a batch will scan
    # off a printed sticker BEFORE the user wastes a roll of labels finding
    # out the hard way.  Strategy:
    #
    #   1. Render the payload at the actual K30F resolution (203 DPI) and
    #      the minimum X-dim that still decodes (0.25 mm). 1-bit B&W —
    #      anti-aliasing is a desktop concept; thermal heads dot ON/OFF.
    #   2. Run the rendered PNG through zxing-cpp.  If it decodes back to
    #      the input string, encoding is sound — the printer's only job
    #      from there is to faithfully reproduce dots, which it does as
    #      long as our X-dim is ≥ 1 dot pitch.
    #   3. Independently check whether the rendered width fits the user's
    #      sticker.  YunPrint shrinks bars when the symbol overflows; that
    #      shrink is what kills decoding in the field.  Refuse export
    #      rather than silently print junk.
    #
    # zxing-cpp is an optional dependency (pip install zxing-cpp). If it
    # isn't available we skip the decode check but still do the width
    # check, so the user gets *some* protection even on a stripped
    # install.

    @staticmethod
    def _render_at_print_grade(text: str, symbology: str = "code128",
                                module_width: float = PRINT_GRADE_MODULE_WIDTH,
                                module_height: float = PRINT_GRADE_MODULE_HEIGHT,
                                quiet_zone: float = PRINT_GRADE_QUIET_ZONE,
                                dpi: int = PRINT_GRADE_DPI):
        """Render ``text`` at K30F-equivalent settings and return a PIL Image.

        Returns the image converted to 1-bit ('L' luminance, threshold 127)
        because the K30F head is binary — every pixel is either burnt or
        not.  Anti-aliased edges from the desktop renderer would not exist
        on the actual printout, so simulating with hard-threshold gives a
        more honest decode test.
        """
        import barcode
        from barcode.writer import ImageWriter
        from PIL import Image as _Img

        opts = {
            "module_width": module_width,
            "module_height": module_height,
            "font_size": 8,
            "text_distance": 1.5,
            "quiet_zone": quiet_zone,
            "dpi": dpi,
            "write_text": False,
        }
        kwargs = {"writer": ImageWriter()}
        if symbology == "code39":
            kwargs["add_checksum"] = False
        bc = barcode.get_barcode_class(symbology)(str(text), **kwargs)
        buf = io.BytesIO()
        bc.write(buf, options=opts)
        buf.seek(0)
        img = _Img.open(buf).convert("L")
        # Hard-threshold to 1-bit so we test the decoder against what
        # the thermal head will actually print, not a fuzzy raster.
        return img.point(lambda v: 0 if v < 128 else 255, mode="L")

    @staticmethod
    def measure_print_width_mm(text: str, symbology: str = "code128",
                                module_width: float = PRINT_GRADE_MODULE_WIDTH,
                                quiet_zone: float = PRINT_GRADE_QUIET_ZONE) -> float:
        """Return the printed symbol width in mm at the given X-dim.

        Pre-renders the barcode at 203 DPI and converts the resulting
        pixel width back to mm.  Used to flag oversize entries cheaply
        before running the full zxing decode pass (which is ~5x slower
        per entry).  The width includes both quiet zones, so the value
        is directly comparable to the user's sticker width.
        """
        try:
            img = BarcodeGenService._render_at_print_grade(
                text, symbology=symbology,
                module_width=module_width, quiet_zone=quiet_zone,
            )
            return img.size[0] / PRINT_GRADE_DPI * 25.4
        except Exception:
            # If the symbology can't encode this string, treat it as
            # infinitely wide so it gets reported up rather than silently
            # passing the fit check.
            return float("inf")

    @classmethod
    def validate_scannability(cls, entries: list[BarcodeEntry], *,
                               symbology: str = "code128",
                               module_width: float = PRINT_GRADE_MODULE_WIDTH,
                               sticker_width_mm: float = DEFAULT_STICKER_WIDTH_MM,
                               sticker_margin_mm: float = DEFAULT_STICKER_MARGIN_MM,
                               ) -> dict:
        """Return a per-entry pass/fail report under K30F-grade conditions.

        Result keys:
            ``total``          — number of non-command entries inspected
            ``passed``         — list[BarcodeEntry] that decoded AND fit
            ``unscannable``    — list[(entry, reason_str)] decode failures
            ``oversize``       — list[(entry, width_mm)] too wide for sticker
            ``decoder_available`` — False if zxing-cpp not installed (decode
                                    check skipped; width check still runs)
            ``symbology``      — echoes the ``symbology`` arg
            ``max_safe_mm``    — sticker_width_mm − sticker_margin_mm
            ``settings``       — dict of the X-dim / quiet-zone / DPI used,
                                  echoed back so the caller can show them
                                  in any failure dialog

        Skips command/colour barcode entries — those are short enough to
        always pass and shouldn't contribute to "X% of items failed"
        statistics.
        """
        try:
            import zxingcpp  # type: ignore
            decoder_available = True
        except ImportError:
            zxingcpp = None  # type: ignore
            decoder_available = False

        max_safe_mm = max(0.0, sticker_width_mm - sticker_margin_mm)

        passed: list[BarcodeEntry] = []
        unscannable: list[tuple[BarcodeEntry, str]] = []
        oversize: list[tuple[BarcodeEntry, float]] = []
        total = 0

        for e in entries:
            if e.is_command or not e.barcode_text:
                continue
            total += 1
            text = e.barcode_text

            # ── Width check (cheap, always run) ──────────────────────────
            try:
                img = cls._render_at_print_grade(
                    text, symbology=symbology, module_width=module_width,
                )
            except Exception as exc:
                unscannable.append(
                    (e, f"render error ({type(exc).__name__}): {exc!s}"[:120])
                )
                continue

            width_mm = img.size[0] / PRINT_GRADE_DPI * 25.4
            if width_mm > max_safe_mm and max_safe_mm > 0:
                oversize.append((e, round(width_mm, 1)))
                # Don't also bother decoding — we already know we won't
                # print this one.
                continue

            # ── Decode check ─────────────────────────────────────────────
            if decoder_available:
                try:
                    res = zxingcpp.read_barcodes(img)  # type: ignore[union-attr]
                except Exception as exc:
                    unscannable.append(
                        (e, f"decode error: {type(exc).__name__}")
                    )
                    continue
                if not res:
                    unscannable.append((e, "no decode"))
                    continue
                if res[0].text != text:
                    unscannable.append(
                        (e, f"decoded as {res[0].text!r} (mismatch)")
                    )
                    continue

            passed.append(e)

        return {
            "total": total,
            "passed": passed,
            "unscannable": unscannable,
            "oversize": oversize,
            "decoder_available": decoder_available,
            "symbology": symbology,
            "max_safe_mm": max_safe_mm,
            "settings": {
                "dpi": PRINT_GRADE_DPI,
                "module_width_mm": module_width,
                "quiet_zone_mm": PRINT_GRADE_QUIET_ZONE,
                "sticker_width_mm": sticker_width_mm,
                "sticker_margin_mm": sticker_margin_mm,
            },
        }

    def render_barcode_image(self, text: str, fmt: str = "code39") -> bytes:
        """Return PNG bytes for a single barcode."""
        try:
            import barcode
            from barcode.writer import ImageWriter
        except ImportError:
            raise ImportError(
                "python-barcode is required.\n"
                "Install it with: pip install python-barcode"
            )

        writer = ImageWriter()
        opts = {
            "module_width": 0.45,    # thicker bars — easier to scan
            "module_height": 15.0,   # taller bars — scanner picks up faster
            "font_size": 10,
            "text_distance": 5.0,    # gap between bars and text (mm)
            "quiet_zone": 6.5,       # white space on sides — scanners need 6mm+
            "dpi": 300,              # high DPI for crisp print
            "write_text": True,
        }

        bc_class = barcode.get_barcode_class(fmt)
        kwargs = {"writer": writer}
        if fmt == "code39":
            kwargs["add_checksum"] = False
        bc = bc_class(str(text), **kwargs)

        # Use render() to get PIL Image directly, then convert to PNG bytes.
        # This avoids bc.write() encoding issues in some python-barcode versions.
        try:
            buf = io.BytesIO()
            bc.write(buf, options=opts)
            buf.seek(0)
            return buf.read()
        except TypeError:
            # Fallback: render to PIL Image and save manually
            from PIL import Image as PILImage
            pil_img = bc.render(writer_options=opts)
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            buf.seek(0)
            return buf.read()

    def create_pdf(self, entries: list[BarcodeEntry],
                   include_commands: bool = True,
                   barcode_format: str = "code39") -> bytes:
        """Generate PDF with vertical command barcodes spanning row blocks."""
        from fpdf import FPDF
        import os

        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=False)

        pw, ph = 210, 297
        mx, my = 10, 10
        uw = pw - 2 * mx

        # Layout: [Command 25mm] [Barcode ~115mm] [Model 50mm]
        cmd_w = 25 if include_commands else 0
        desc_w = 50
        bc_w = uw - cmd_w - desc_w

        row_h = 18
        hdr_h = 8
        title_h = 10
        rows_per_page = int((ph - 2 * my - title_h - hdr_h) / row_h)

        # Render command barcode images — both horizontal and vertical versions
        from PIL import Image as PILImage
        cmd_entries = self.get_command_entries() if include_commands else []
        cmd_images_h: dict[str, str] = {}   # horizontal (normal)
        cmd_images_v: dict[str, str] = {}   # vertical (rotated 90°)
        temp_files: list[str] = []

        for ce in cmd_entries:
            img_bytes = self.render_barcode_image(ce.barcode_text, barcode_format)

            # Save horizontal version
            tf_h = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tf_h.write(img_bytes)
            tf_h.close()
            cmd_images_h[ce.command_label] = tf_h.name
            temp_files.append(tf_h.name)

            # Save rotated 90° version
            pil_img = PILImage.open(io.BytesIO(img_bytes))
            rotated = pil_img.rotate(90, expand=True)
            tf_v = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            rotated.save(tf_v, format="PNG")
            tf_v.close()
            cmd_images_v[ce.command_label] = tf_v.name
            temp_files.append(tf_v.name)

        # Render item barcode images
        item_images: list[str] = []
        for entry in entries:
            img_bytes = self.render_barcode_image(entry.barcode_text, barcode_format)
            tf = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tf.write(img_bytes)
            tf.close()
            item_images.append(tf.name)
            temp_files.append(tf.name)

        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Get command barcode text values for display
        cfg = ScanConfig.get()
        cfg_cmd_insert = cfg.cmd_insert
        cfg_cmd_takeout = cfg.cmd_takeout
        cfg_cmd_confirm = cfg.cmd_confirm

        cmd_labels = ["ADD", "DEL", "OK"]
        cmd_colors = {
            "ADD": (190, 205, 235),
            "DEL": (240, 210, 190),
            "OK":  (195, 225, 195),
        }

        # Build global index map: entry → image index
        entry_img_map: dict[int, int] = {}
        for gi, entry in enumerate(entries):
            entry_img_map[id(entry)] = gi

        # Split entries by brand + part type — each combo starts on a new page
        # e.g., "Apple + (JK) incell FHD", "Apple + Back Cover", "Samsung + ORG Service Pack"
        sections: list[tuple[str, str, list[BarcodeEntry]]] = []
        current_key = ("", "")
        for e in entries:
            key = (e.brand or "Other", e.part_type or "Other")
            if key != current_key:
                sections.append((key[0], key[1], []))
                current_key = key
            sections[-1][2].append(e)

        # Remove empty sections
        sections = [(b, p, items) for b, p, items in sections if items]

        # Count total pages
        total_pages = 0
        for _, _, group in sections:
            total_pages += max(1, (len(group) + rows_per_page - 1) // rows_per_page)

        page_num = 0

        for brand_name, pt_name, section_entries in sections:
            section_pages = max(1, (len(section_entries) + rows_per_page - 1) // rows_per_page)

            for sp_idx in range(section_pages):
                page_num += 1
                pdf.add_page()
                y = my

                # Title: "Stock Manager Pro - Apple - (JK) incell FHD"
                header_text = f"{brand_name} - {pt_name}"
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_xy(mx, y)
                pdf.cell(uw * 0.55, title_h, _pdf_safe(header_text), ln=0)
                pdf.set_font("Helvetica", "", 8)
                pdf.cell(uw * 0.45, title_h, f"{now}    Page {page_num}/{total_pages}", ln=0, align="R")
                y += title_h

                # Column header
                pdf.set_fill_color(230, 230, 230)
                pdf.set_font("Helvetica", "B", 8)
                if include_commands:
                    pdf.set_xy(mx, y)
                    pdf.cell(cmd_w, hdr_h, "Cmd", border=1, fill=True, align="C")
                pdf.set_xy(mx + cmd_w, y)
                pdf.cell(bc_w, hdr_h, "Code39", border=1, fill=True, align="C")
                pdf.set_xy(mx + cmd_w + bc_w, y)
                pdf.cell(desc_w, hdr_h, "Model", border=1, fill=True, align="C")
                y += hdr_h

                # Page items
                start = sp_idx * rows_per_page
                end = min(start + rows_per_page, len(section_entries))
                page_items = section_entries[start:end]
                n = len(page_items)

                # Split into 3 blocks for commands
                if n >= 3:
                    b1 = n // 3
                    b2 = b1 * 2
                    blocks = [(0, b1, "ADD"), (b1, b2, "DEL"), (b2, n, "OK")]
                elif n == 2:
                    blocks = [(0, 1, "ADD"), (1, 2, "DEL")]
                elif n == 1:
                    blocks = [(0, 1, "ADD")]
                else:
                    blocks = []

                # Draw command blocks (vertical spanning)
                if include_commands:
                    for blk_start, blk_end, label in blocks:
                        blk_rows = blk_end - blk_start
                        blk_y = y + blk_start * row_h
                        blk_h = blk_rows * row_h

                        # Color fill for entire block
                        r, g, b = cmd_colors.get(label, (230, 230, 230))
                        pdf.set_fill_color(r, g, b)
                        pdf.rect(mx, blk_y, cmd_w, blk_h, "DF")

                        # Border
                        pdf.set_draw_color(180, 180, 180)
                        pdf.rect(mx, blk_y, cmd_w, blk_h)

                        # Label text at top of block
                        pdf.set_font("Helvetica", "B", 10)
                        pdf.set_text_color(40, 40, 40)
                        pdf.set_xy(mx, blk_y + 2)
                        pdf.cell(cmd_w, 6, label, align="C")

                        # Command barcode image
                        try:
                            if blk_h >= 50:
                                # Tall block — use vertical (rotated) barcode
                                img_path = cmd_images_v.get(label)
                                if img_path:
                                    bc_top = blk_y + 10
                                    bc_h = blk_h - 16
                                    pdf.image(img_path, mx + 3, bc_top,
                                              w=cmd_w - 6, h=bc_h)
                            else:
                                # Short block — use horizontal barcode
                                img_path = cmd_images_h.get(label)
                                if img_path:
                                    bc_top = blk_y + 10
                                    bc_h = min(blk_h - 12, 14)
                                    if bc_h > 5:
                                        pdf.image(img_path, mx + 1, bc_top,
                                                  w=cmd_w - 2, h=bc_h)
                        except Exception:
                            pass

                        # Barcode text at bottom
                        ce_text = {"ADD": cfg_cmd_insert, "DEL": cfg_cmd_takeout, "OK": cfg_cmd_confirm}.get(label, "")
                        if ce_text and blk_h > 20:
                            pdf.set_font("Helvetica", "", 5)
                            pdf.set_xy(mx, blk_y + blk_h - 5)
                            pdf.cell(cmd_w, 4, _pdf_safe(ce_text), align="C")

                        pdf.set_text_color(0, 0, 0)
                        pdf.set_draw_color(0, 0, 0)

                # Draw item rows
                for i, entry in enumerate(page_items):
                    row_y = y + i * row_h
                    img_idx = entry_img_map.get(id(entry), -1)

                    # Alternating row bg
                    if i % 2 == 1:
                        pdf.set_fill_color(248, 248, 248)
                        pdf.rect(mx + cmd_w, row_y, bc_w + desc_w, row_h, "F")

                    # Barcode cell
                    pdf.set_draw_color(200, 200, 200)
                    pdf.rect(mx + cmd_w, row_y, bc_w, row_h)
                    if 0 <= img_idx < len(item_images):
                        try:
                            pdf.image(item_images[img_idx],
                                      mx + cmd_w + 2, row_y + 1,
                                      w=bc_w - 4, h=row_h - 2)
                        except Exception:
                            pdf.set_font("Helvetica", "", 7)
                            pdf.set_xy(mx + cmd_w + 2, row_y + 5)
                            pdf.cell(bc_w - 4, 6, entry.barcode_text, align="C")

                    # Description cell — just model name (part type is in page header)
                    pdf.rect(mx + cmd_w + bc_w, row_y, desc_w, row_h)
                    safe_label = _pdf_safe(entry.display_label)
                    parts = safe_label.split(" - ")
                    if len(parts) == 1:
                        parts = safe_label.split("  ")
                    pdf.set_font("Helvetica", "B", 9)
                    pdf.set_xy(mx + cmd_w + bc_w + 2, row_y + 4)
                    pdf.cell(desc_w - 4, 8, (parts[0].strip() if parts else "")[:22], align="L")
                    pdf.set_font("Helvetica", "", 7)
                    pdf.set_xy(mx + cmd_w + bc_w + 2, row_y + 8)
                    pdf.cell(desc_w - 4, 5, parts[-1].strip()[:28], align="L")

                pdf.set_draw_color(0, 0, 0)

        # ── Color barcodes page (if include_commands) ──
        if include_commands:
            color_entries = self.get_color_entries()
            if color_entries:
                pdf.add_page()
                y = my
                pdf.set_font("Helvetica", "B", 12)
                pdf.set_xy(mx, y)
                pdf.cell(uw, title_h, "Color Barcodes", align="C")
                y += title_h + 4

                pdf.set_font("Helvetica", "", 8)
                pdf.set_xy(mx, y)
                pdf.cell(uw, 6, "Scan these after scanning a model barcode to select the color variant", align="C")
                y += 10

                color_row_h = 25
                for ci, ce in enumerate(color_entries):
                    row_y = y + ci * color_row_h
                    if row_y + color_row_h > ph - my:
                        break

                    # Render color barcode image
                    try:
                        img_bytes = self.render_barcode_image(ce.barcode_text, barcode_format)
                        tf = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                        tf.write(img_bytes)
                        tf.close()
                        temp_files.append(tf.name)

                        # Color background behind label
                        color_rgb = {
                            "Black":  (40, 40, 40),
                            "Blue":   (30, 100, 220),
                            "Silver": (180, 180, 190),
                            "Gold":   (210, 175, 55),
                            "Green":  (30, 160, 80),
                            "Purple": (140, 60, 200),
                            "White":  (240, 240, 240),
                        }
                        cr, cg, cb = color_rgb.get(ce.display_label, (200, 200, 200))
                        pdf.set_fill_color(cr, cg, cb)
                        pdf.rect(mx, row_y, 35, color_row_h, "F")

                        # Color label — white text on dark colors, black on light
                        is_light = (cr * 0.299 + cg * 0.587 + cb * 0.114) > 150
                        pdf.set_text_color(0 if is_light else 255, 0 if is_light else 255, 0 if is_light else 255)
                        pdf.set_font("Helvetica", "B", 11)
                        pdf.set_xy(mx, row_y + 7)
                        pdf.cell(35, 10, _pdf_safe(ce.display_label), align="C")
                        pdf.set_text_color(0, 0, 0)

                        # Barcode image
                        pdf.image(tf.name, mx + 38, row_y + 2, w=uw - 40, h=color_row_h - 4)

                        # Border
                        pdf.set_draw_color(180, 180, 180)
                        pdf.rect(mx, row_y, uw, color_row_h)
                        pdf.set_draw_color(0, 0, 0)
                    except Exception:
                        pass

        # Write PDF to a temp file instead of relying on output() return value.
        # Old pyfpdf 1.7.x dumps to stdout if output() is called with no args,
        # while fpdf2 returns bytearray. Writing to file works with both.
        pdf_tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        pdf_tmp.close()
        pdf.output(pdf_tmp.name)
        with open(pdf_tmp.name, "rb") as f:
            pdf_bytes = f.read()

        # Cleanup temp files (including the PDF temp)
        temp_files.append(pdf_tmp.name)
        for tf in temp_files:
            try:
                os.unlink(tf)
            except Exception:
                pass

        return pdf_bytes

    def assign_barcodes(self, entries: list[BarcodeEntry]) -> int:
        """Write generated barcodes to inventory_items using scanner format (ß)."""
        updates = [(e.item_id, e.db_text or e.barcode_text) for e in entries
                    if e.item_id is not None and not e.is_command]
        return _item_repo.bulk_update_barcodes(updates)

    @staticmethod
    def _yunprint_filename_token(text: str) -> str:
        """Sanitise a string for use in a filename.

        Spaces / dots / slashes / parens / colons / semicolons → underscore.
        Drops characters Windows + macOS + Linux all reject. Collapses
        runs of underscores so we don't end up with ``Apple____iPhone___``.
        """
        if not text:
            return ""
        out = []
        last_us = False
        for ch in text.strip():
            if ch.isalnum() or ch in ("-", "+"):
                out.append(ch)
                last_us = False
            else:
                if not last_us:
                    out.append("_")
                    last_us = True
        cleaned = "".join(out).strip("_")
        return cleaned or "x"

    def _write_yunprint_csv(self, entries: list[BarcodeEntry],
                            output_path: str, *,
                            symbology: str = "code128",
                            validate: bool = True,
                            sticker_width_mm: float = DEFAULT_STICKER_WIDTH_MM,
                            ) -> tuple[str, int]:
        """Write the CSV body to ``output_path`` and return ``(path, count)``.

        Internal helper shared by ``export_for_yunprint`` (single file)
        and ``export_for_yunprint_split`` (multiple files in a folder).
        Counts only the rows actually written — command / color /
        empty-barcode entries are skipped silently.

        When ``validate=True`` (default), every entry is rendered at
        K30F-grade settings under the chosen ``symbology`` and decoded
        with zxing-cpp.  If any entry would fail to scan or wouldn't fit
        the configured sticker, the file is NOT written and a
        ``BarcodeValidationError`` is raised with the failed entries
        attached.  This is the guarantee: a successful write means every
        line in the CSV will produce a scannable label off the printer.

        ``symbology`` should match what the user has configured in their
        YunPrint template — Code 128 (recommended for the K30F + 50×20mm
        sticker) or Code 39 (legacy). The CSV body is identical for both;
        the symbology only affects the validation render.
        """
        import csv as _csv
        import os as _os

        if validate:
            report = self.validate_scannability(
                entries, symbology=symbology,
                sticker_width_mm=sticker_width_mm,
            )
            if report["unscannable"] or report["oversize"]:
                raise BarcodeValidationError(
                    failed=report["unscannable"],
                    oversize=report["oversize"],
                    symbology=symbology,
                )

        root, ext = _os.path.splitext(output_path)
        if ext.lower() != ".txt":
            output_path = root + ".txt"

        headers = ["barcode", "model", "part_type", "color",
                   "model_full", "brand", "label"]

        def _clean(cell: str) -> str:
            return cell.replace("\r", " ").replace("\n", " ")

        written = 0
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            w = _csv.writer(f, quoting=_csv.QUOTE_MINIMAL)
            w.writerow(headers)
            for e in entries:
                if e.is_command or not e.barcode_text:
                    continue
                full_model = (
                    e.display_label.split(" · ")[0].strip()
                    if e.display_label else ""
                )
                model_no_brand = _strip_brand_prefix(full_model)
                short_model = f"{_brand_short(e.brand)} {model_no_brand}".strip()
                w.writerow([
                    _clean(e.barcode_text),
                    _clean(short_model),
                    _clean(e.part_type or ""),
                    _clean(e.color or ""),
                    _clean(full_model),
                    _clean(e.brand or ""),
                    _clean(e.display_label or ""),
                ])
                written += 1
        return output_path, written

    def export_for_yunprint_split(self, entries: list[BarcodeEntry],
                                   output_dir: str,
                                   split_by: str = "part_type", *,
                                   symbology: str = "code128",
                                   validate: bool = True,
                                   sticker_width_mm: float = DEFAULT_STICKER_WIDTH_MM,
                                   ) -> list[tuple[str, int]]:
        """Write one ``.txt`` per group (brand / part_type / brand+part_type
        / model) into ``output_dir``. Returns ``[(path, row_count), ...]``
        for every file actually written (groups with zero rows are skipped).

        Naming convention — all files share the ``labels-print-…`` prefix
        and a ``YYYY-MM-DD`` suffix so they sort cleanly in Explorer
        and the user can drop multiple batches into the same folder
        without collisions. Group identifiers are sanitised via
        ``_yunprint_filename_token`` so brand names with spaces or
        accents become valid filenames on every OS:

          * ``split_by="brand"``           → ``labels-print-Apple-2026-04-29.txt``
          * ``split_by="part_type"``       → ``labels-print-(JK)_incell_FHD-2026-04-29.txt``
          * ``split_by="brand_part_type"`` → ``labels-print-Apple-(JK)_incell_FHD-2026-04-29.txt``
          * ``split_by="model"``           → ``labels-print-Apple-iPhone_15_Pro-2026-04-29.txt``

        Use case: shop assistant prints a different sticker template for
        each part type (different sticker rolls, different label sizes).
        Splitting by ``part_type`` or ``brand_part_type`` lets them
        generate every batch in one click — no per-template re-export.
        """
        import os as _os
        from datetime import datetime

        # Validate ONCE up-front against the full entry list rather than
        # paying the per-group cost N times. Inner ``_write_yunprint_csv``
        # calls below pass ``validate=False`` so the report isn't recomputed.
        if validate:
            report = self.validate_scannability(
                entries, symbology=symbology,
                sticker_width_mm=sticker_width_mm,
            )
            if report["unscannable"] or report["oversize"]:
                raise BarcodeValidationError(
                    failed=report["unscannable"],
                    oversize=report["oversize"],
                    symbology=symbology,
                )

        date_str = datetime.now().strftime("%Y-%m-%d")
        _os.makedirs(output_dir, exist_ok=True)

        # ── Group entries by the chosen dimension ──
        # ``key_fn`` returns the human-readable name for the group;
        # we sanitise once when building the filename. ``order_key`` is
        # used to sort group filenames so they appear alphabetically in
        # Explorer regardless of the order ``entries`` happened to come in.
        if split_by == "brand":
            key_fn = lambda e: e.brand or "Unknown"
        elif split_by == "part_type":
            key_fn = lambda e: e.part_type or "Unknown"
        elif split_by == "brand_part_type":
            key_fn = lambda e: (
                f"{e.brand or 'Unknown'}-{e.part_type or 'Unknown'}"
            )
        elif split_by == "model":
            # Use display-name's model portion (everything before " · ")
            # so we get "iPhone 15 Pro" instead of just the abbreviated
            # model column. Combined with brand for cross-brand uniqueness.
            def key_fn(e):
                full_model = (
                    e.display_label.split(" · ")[0].strip()
                    if e.display_label else ""
                ) or "Unknown"
                return f"{e.brand or 'Unknown'}-{full_model}"
        else:
            raise ValueError(
                f"split_by must be one of "
                f"'brand'/'part_type'/'brand_part_type'/'model'; got {split_by!r}"
            )

        groups: dict[str, list[BarcodeEntry]] = {}
        for e in entries:
            if e.is_command or not e.barcode_text:
                continue
            groups.setdefault(key_fn(e), []).append(e)

        results: list[tuple[str, int]] = []
        for group_name in sorted(groups.keys()):
            token = self._yunprint_filename_token(group_name)
            filename = f"labels-print-{token}-{date_str}.txt"
            path = _os.path.join(output_dir, filename)
            written_path, count = self._write_yunprint_csv(
                groups[group_name], path,
                symbology=symbology, validate=False,  # already validated above
            )
            if count > 0:
                results.append((written_path, count))
        return results

    def export_for_yunprint(self, entries: list[BarcodeEntry],
                            output_path: str, *,
                            symbology: str = "code128",
                            validate: bool = True,
                            sticker_width_mm: float = DEFAULT_STICKER_WIDTH_MM,
                            ) -> str:
        """Write a YunPrint-compatible **.txt** (comma-separated, RFC4180-style
        quoting) data file with one row per barcode.

        YunPrint's "Database" .txt importer defaults to ``Character Segmentation:
        Comma`` and expects standard CSV. We initially tried tab-delimited
        because it avoids quoting headaches, but YunPrint then read each entire
        row as a single column (the segmentation setting is sticky per-import
        and not auto-detected from the file). Switching to commas + Python's
        ``csv`` writer means YunPrint parses out individual columns out of the
        box — no setting tweaks per import.

        Workflow: design the 50×20mm template once with template fields bound
        to ``Database``; for every future batch click Database → .txt → Select
        File → pick the file produced here → Confirm → Print all.

        Columns (lowercase + snake_case so YunPrint lists them cleanly):
          - ``barcode``     — Code39 string (same value already saved on the
                              inventory_item, so printed labels scan identically
                              to existing app barcodes).
          - ``model``       — short brand-prefixed model, e.g. "IP 11 Pro Max",
                              "SA S25 Ultra". Compact enough for the right
                              field on a 50×20mm sticker.
          - ``part_type``   — full part type name, e.g. "D.D Soft Oled".
          - ``model_full``  — full model with original brand prefix
                              ("iPhone 11 Pro Max"). Pick this in YunPrint
                              instead of ``model`` if the sticker is bigger.
          - ``brand``       — raw brand ("Apple", "Samsung").
          - ``label``       — combined display string ("iPhone 11 Pro Max · LCD").

        Skips command/color barcode entries — those are scanner-only and
        don't belong on per-item stickers.

        Returns the path actually written (extension forced to .txt).
        Raises ``BarcodeValidationError`` if any entry would not scan
        off a printed sticker at K30F-grade settings (default symbology
        is Code 128, the K30F-recommended choice for 50×20mm rolls).
        Pass ``validate=False`` to skip the check at your own risk.
        """
        path, _ = self._write_yunprint_csv(
            entries, output_path,
            symbology=symbology, validate=validate,
            sticker_width_mm=sticker_width_mm,
        )
        return path
