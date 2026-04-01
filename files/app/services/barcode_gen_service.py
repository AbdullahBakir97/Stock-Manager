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


@dataclass
class BarcodeEntry:
    item_id: Optional[int]     # None for command barcodes
    barcode_text: str          # e.g., "AP-X-LCD"
    display_label: str         # e.g., "iPhone X · LCD"
    is_command: bool = False
    command_label: str = ""    # "ADD", "DEL", "OK"
    brand: str = ""            # "Apple", "Samsung"
    part_type: str = ""        # "(JK) incell FHD", "Back Cover"


def _abbreviate(name: str, max_len: int = 6) -> str:
    """Create a short code from a name. E.g., 'iPhone 14 Pro Max' → 'IP14PM'."""
    name = name.upper().strip()
    # Remove common prefixes
    for prefix in ("IPHONE ", "GALAXY ", "SAMSUNG "):
        if name.startswith(prefix):
            name = name[len(prefix):]
    # Split into parts
    parts = re.split(r'[\s_-]+', name)
    code = ""
    for p in parts:
        if p.isdigit():
            code += p
        elif len(p) <= 2:
            code += p
        else:
            code += p[0]
    # Clean for Code39
    code = "".join(c for c in code if c in _CODE39_VALID)
    return code[:max_len] if code else "X"


def _make_barcode_text(item: InventoryItem) -> str:
    """Generate a barcode string from an inventory item."""
    brand_code = _abbreviate(item.model_brand or item.brand or "", 3)
    model_code = _abbreviate(item.model_name or item.name or "", 6)
    if item.part_type_key:
        pt_code = _abbreviate(item.part_type_key, 5)
        text = f"{brand_code}-{model_code}-{pt_code}"
    else:
        text = f"{brand_code}-{model_code}"
    # Ensure Code39 valid
    text = "".join(c for c in text.upper() if c in _CODE39_VALID)
    return text or "ITEM"


class BarcodeGenService:
    """Generate barcodes, create PDF sheets, assign to items."""

    def generate_for_scope(self, scope: str,
                           category_id: int | None = None,
                           model_ids: list[int] | None = None,
                           part_type_ids: list[int] | None = None,
                           include_existing: bool = False) -> list[BarcodeEntry]:
        """Generate BarcodeEntry list for the selected scope."""
        if include_existing:
            items = _item_repo.get_all_matrix_items(category_id)
        else:
            items = _item_repo.get_items_without_barcode(
                category_id=category_id,
                model_ids=model_ids,
                part_type_ids=part_type_ids,
            )

        if model_ids:
            items = [i for i in items if i.model_id in model_ids]
        if part_type_ids:
            items = [i for i in items if i.part_type_id in part_type_ids]

        # Sort by brand first, then part type, then by sort_order (DB order)
        # This preserves the logical order: X, XS, XR, 11, 12... 17
        from app.repositories.model_repo import ModelRepository
        _mr = ModelRepository()
        # Build sort_order lookup from DB
        all_models = _mr.get_all()
        model_order = {m.id: m.sort_order for m in all_models}

        items.sort(key=lambda i: (
            i.model_brand or "",
            i.part_type_name or "",
            model_order.get(i.model_id, 9999),
        ))

        entries: list[BarcodeEntry] = []
        used_codes: set[str] = set()

        for item in items:
            if item.barcode and not include_existing:
                continue
            # Use existing barcode or generate new one
            if item.barcode:
                code = item.barcode
            else:
                code = _make_barcode_text(item)
                # Ensure uniqueness
                base = code
                suffix = 2
                while code in used_codes:
                    code = f"{base}{suffix}"
                    suffix += 1
                used_codes.add(code)

            label = item.display_name
            entries.append(BarcodeEntry(
                item_id=item.id,
                barcode_text=code,
                display_label=label,
                brand=item.model_brand or item.brand or "",
                part_type=item.part_type_name or "",
            ))

        return entries

    def get_command_entries(self) -> list[BarcodeEntry]:
        """Return the 3 command barcode entries."""
        cfg = ScanConfig.get()
        return [
            BarcodeEntry(None, cfg.cmd_insert, "INSERT", True, "ADD"),
            BarcodeEntry(None, cfg.cmd_takeout, "TAKEOUT", True, "DEL"),
            BarcodeEntry(None, cfg.cmd_confirm, "CONFIRM", True, "OK"),
        ]

    def render_barcode_image(self, text: str, fmt: str = "code39") -> bytes:
        """Return PNG bytes for a single barcode."""
        import barcode
        from barcode.writer import ImageWriter

        writer = ImageWriter()
        writer.set_options({
            "module_width": 0.35,
            "module_height": 12.0,
            "font_size": 8,
            "text_distance": 2.0,
            "quiet_zone": 2.0,
        })

        bc_class = barcode.get_barcode_class(fmt)
        kwargs = {"writer": writer}
        if fmt == "code39":
            kwargs["add_checksum"] = False
        bc = bc_class(text, **kwargs)

        buf = io.BytesIO()
        bc.write(buf, options={"write_text": True})
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

        # Render command barcode images — rotated 90° for vertical display
        from PIL import Image as PILImage
        cmd_entries = self.get_command_entries() if include_commands else []
        cmd_images: dict[str, str] = {}
        temp_files: list[str] = []

        for ce in cmd_entries:
            img_bytes = self.render_barcode_image(ce.barcode_text, barcode_format)
            # Rotate 90° counterclockwise so barcode reads bottom-to-top
            pil_img = PILImage.open(io.BytesIO(img_bytes))
            rotated = pil_img.rotate(90, expand=True)
            tf = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            rotated.save(tf, format="PNG")
            tf.close()
            cmd_images[ce.command_label] = tf.name
            temp_files.append(tf.name)

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

                        # Vertical barcode image
                        img_path = cmd_images.get(label)
                        if img_path and blk_h > 25:
                            try:
                                bc_top = blk_y + 10
                                bc_h = blk_h - 18
                                pdf.image(img_path, mx + 4, bc_top,
                                          w=cmd_w - 8, h=bc_h)
                            except Exception:
                                pass

                        # Barcode text at bottom
                        ce_text = {"ADD": cfg_cmd_insert, "DEL": cfg_cmd_takeout, "OK": cfg_cmd_confirm}.get(label, "")
                        if ce_text:
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

        pdf_bytes = pdf.output()

        # Cleanup
        for tf in temp_files:
            try:
                os.unlink(tf)
            except Exception:
                pass

        return bytes(pdf_bytes)

    def assign_barcodes(self, entries: list[BarcodeEntry]) -> int:
        """Write generated barcodes to inventory_items. Returns count."""
        updates = [(e.item_id, e.barcode_text) for e in entries
                    if e.item_id is not None and not e.is_command]
        return _item_repo.bulk_update_barcodes(updates)
