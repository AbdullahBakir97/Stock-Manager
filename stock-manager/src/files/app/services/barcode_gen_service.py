"""app/services/barcode_gen_service.py — Barcode generation + PDF creation."""
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

    Default ``max_len`` is 8 (was 5) — large enough to preserve common
    suffixes like ``PRO+`` / ``ULTRA`` / ``5G`` so barcodes stay readable
    instead of truncating into ambiguous prefixes ("Note 14 Pro+" →
    ``NOTE14P+`` rather than the old truncated ``NOTE1``).

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


def _part_type_code(name: str, max_len: int = 5) -> str:
    """Compact part-type code for a barcode.

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
      'ORG Service Pack' → 'OSP'
      '(JK) incell FHD' → 'JKIF'
      '(D.D) Soft OLED' → 'DDSO'
      'Back Cover' → 'BC'
      'Battery' → 'BATT'
      'LCD' → 'LCD'
    """
    if not name:
        return "X"
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

    def export_for_yunprint(self, entries: list[BarcodeEntry],
                            output_path: str) -> str:
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
        """
        import csv
        import os as _os

        # Force a .txt extension so YunPrint's .txt importer matches.
        root, ext = _os.path.splitext(output_path)
        if ext.lower() != ".txt":
            output_path = root + ".txt"

        headers = ["barcode", "model", "part_type", "color",
                   "model_full", "brand", "label"]

        def _clean(cell: str) -> str:
            # Newlines would break the row structure even inside quoted fields
            # for some lightweight CSV parsers. Strip them; commas/quotes are
            # handled by csv.writer's default quoting.
            return cell.replace("\r", " ").replace("\n", " ")

        # UTF-8 with BOM — YunPrint reads the BOM as an encoding hint, so
        # Unicode brand/part-type names ("·", "Ω", localized accents) survive.
        # ``csv.QUOTE_MINIMAL`` only quotes fields that actually contain a
        # comma, quote, or newline — keeps the file diff-friendly when items
        # have plain ASCII names.
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            w.writerow(headers)
            for e in entries:
                if e.is_command or not e.barcode_text:
                    continue

                # display_label is "<Model Name> · <Part Type>" for inventory items
                full_model = e.display_label.split(" · ")[0].strip() if e.display_label else ""
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

        return output_path
