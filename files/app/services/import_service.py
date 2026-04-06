"""
app/services/import_service.py — CSV import service for products.

Handles CSV preview, delimiter detection, validation, and bulk product imports
with duplicate detection and error handling.
"""
from __future__ import annotations

import csv
import os
from typing import Optional

from app.repositories.product_repo import ProductRepository


class ImportService:
    """
    Service for importing product data from CSV files.

    Provides preview, validation, and bulk import with duplicate detection.
    """

    def __init__(self) -> None:
        """Initialize the import service with a ProductRepository instance."""
        self._product_repo = ProductRepository()

    # ── CSV Preview ──

    def preview_csv(self, file_path: str, max_rows: int = 20) -> dict:
        """
        Preview the first N rows of a CSV file with auto-detected delimiter.

        Auto-detects the delimiter by sampling the first few lines:
        tries comma, semicolon, and tab in order.

        Args:
            file_path: Absolute path to the CSV file.
            max_rows: Maximum number of data rows to include in preview (default 20).

        Returns:
            dict with keys:
            - headers: list of column names
            - rows: list of data rows (up to max_rows)
            - total_rows: total number of data rows in file
            - delimiter: detected delimiter character
        """
        if not os.path.isfile(file_path):
            return {
                "headers": [],
                "rows": [],
                "total_rows": 0,
                "delimiter": "",
            }

        delimiter = self._detect_delimiter(file_path)
        headers = []
        preview_rows = []
        total_rows = 0

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter=delimiter)
                # First row is header
                headers = next(reader, [])
                # Collect preview rows
                for i, row in enumerate(reader):
                    if i < max_rows:
                        preview_rows.append(row)
                    total_rows += 1
        except (IOError, OSError) as e:
            return {
                "headers": [],
                "rows": [],
                "total_rows": 0,
                "delimiter": delimiter,
            }

        return {
            "headers": headers,
            "rows": preview_rows,
            "total_rows": total_rows,
            "delimiter": delimiter,
        }

    # ── Delimiter Detection ──

    def _detect_delimiter(self, file_path: str) -> str:
        """
        Detect the delimiter used in a CSV file.

        Samples the first two lines and tries comma, semicolon, tab in order.
        Returns the first delimiter that produces consistent column counts.

        Args:
            file_path: Absolute path to the CSV file.

        Returns:
            Detected delimiter character (comma, semicolon, tab), or comma as default.
        """
        delimiters = [",", ";", "\t"]
        sample_lines = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                sample_lines = [f.readline().rstrip("\n"), f.readline().rstrip("\n")]
        except (IOError, OSError):
            return ","

        for delimiter in delimiters:
            col_counts = []
            for line in sample_lines:
                if line:
                    count = len(line.split(delimiter))
                    col_counts.append(count)
            # If both lines have same column count, this is likely the delimiter
            if col_counts and len(set(col_counts)) == 1:
                return delimiter

        return ","

    # ── Row Validation ──

    def validate_row(
        self, row: list, column_map: dict, row_num: int
    ) -> tuple[Optional[dict], Optional[str]]:
        """
        Validate a single CSV row against the provided column map.

        Checks:
        - brand and name are not empty
        - stock and min_stock (if present) are numeric
        - barcode is not a duplicate (if provided)

        Args:
            row: List of column values from CSV row.
            column_map: Dict mapping field names to column indices.
                        Example: {"brand": 0, "name": 1, "stock": 4}
            row_num: Row number (for error messages).

        Returns:
            Tuple of (parsed_data_dict, error_message).
            On success: (parsed_data, None)
            On failure: (None, error_message)
        """
        parsed = {}

        # ── Extract required fields ──
        brand_idx = column_map.get("brand")
        name_idx = column_map.get("name")

        if brand_idx is None or name_idx is None:
            return (None, f"Row {row_num}: column_map must include 'brand' and 'name'")

        # ── Safe column access ──
        def get_col(idx: int, default: str = "") -> str:
            if idx < len(row):
                return str(row[idx]).strip()
            return default

        brand = get_col(brand_idx)
        name = get_col(name_idx)

        # ── Validate required fields ──
        if not brand:
            return (None, f"Row {row_num}: brand is required and cannot be empty")
        if not name:
            return (None, f"Row {row_num}: name is required and cannot be empty")

        parsed["brand"] = brand
        parsed["name"] = name

        # ── Extract optional fields ──
        color_idx = column_map.get("color")
        if color_idx is not None:
            parsed["color"] = get_col(color_idx)
        else:
            parsed["color"] = ""

        barcode_idx = column_map.get("barcode")
        if barcode_idx is not None:
            barcode_val = get_col(barcode_idx)
            if barcode_val:
                # Check for duplicate
                if self._product_repo.get_by_barcode(barcode_val) is not None:
                    return (
                        None,
                        f"Row {row_num}: barcode '{barcode_val}' already exists",
                    )
                parsed["barcode"] = barcode_val
            else:
                parsed["barcode"] = None
        else:
            parsed["barcode"] = None

        # ── Validate and extract stock ──
        stock_idx = column_map.get("stock")
        if stock_idx is not None:
            stock_str = get_col(stock_idx)
            try:
                parsed["stock"] = int(stock_str) if stock_str else 0
            except ValueError:
                return (
                    None,
                    f"Row {row_num}: stock must be numeric, got '{stock_str}'",
                )
        else:
            parsed["stock"] = 0

        # ── Validate and extract min_stock ──
        min_stock_idx = column_map.get("min_stock")
        if min_stock_idx is not None:
            min_stock_str = get_col(min_stock_idx)
            try:
                parsed["min_stock"] = int(min_stock_str) if min_stock_str else 0
            except ValueError:
                return (
                    None,
                    f"Row {row_num}: min_stock must be numeric, got '{min_stock_str}'",
                )
        else:
            parsed["min_stock"] = 0

        # ── Validate and extract price ──
        price_idx = column_map.get("price")
        if price_idx is not None:
            price_str = get_col(price_idx)
            try:
                parsed["price"] = float(price_str) if price_str else None
            except ValueError:
                return (
                    None,
                    f"Row {row_num}: price must be numeric, got '{price_str}'",
                )
        else:
            parsed["price"] = None

        return (parsed, None)

    # ── Product Import ──

    def import_products_csv(
        self,
        file_path: str,
        column_map: dict,
        skip_header: bool = True,
    ) -> dict:
        """
        Import standalone products from a CSV file.

        Reads products line by line, validates each row, checks for duplicates
        (by barcode if provided), and inserts valid products into the repository.

        Args:
            file_path: Absolute path to the CSV file.
            column_map: Dict mapping field names to column indices.
                        Required: "brand", "name"
                        Optional: "color", "barcode", "stock", "min_stock", "price"
                        Example:
                          {
                              "brand": 0,
                              "name": 1,
                              "color": 2,
                              "barcode": 3,
                              "stock": 4,
                              "min_stock": 5,
                              "price": 6
                          }
            skip_header: If True, skip the first line of the file (default True).

        Returns:
            dict with keys:
            - imported: Number of successfully imported products
            - skipped: Number of rows skipped due to errors
            - errors: List of error messages (one per failed row)
        """
        if not os.path.isfile(file_path):
            return {
                "imported": 0,
                "skipped": 0,
                "errors": [f"File not found: {file_path}"],
            }

        delimiter = self._detect_delimiter(file_path)
        imported = 0
        skipped = 0
        errors = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter=delimiter)

                # Skip header if requested
                start_row = 1
                if skip_header:
                    next(reader, None)
                    start_row = 2

                # Process each row
                for row_idx, row in enumerate(reader, start=start_row):
                    if not row or all(not cell.strip() for cell in row):
                        # Skip empty rows
                        continue

                    # Validate the row
                    parsed, error = self.validate_row(row, column_map, row_idx)
                    if error:
                        errors.append(error)
                        skipped += 1
                        continue

                    # Insert the product
                    try:
                        self._product_repo.add(
                            brand=parsed["brand"],
                            type_=parsed["name"],
                            color=parsed["color"],
                            stock=parsed["stock"],
                            barcode=parsed["barcode"],
                            low_stock_threshold=parsed["min_stock"],
                            sell_price=parsed["price"],
                        )
                        imported += 1
                    except Exception as e:
                        errors.append(f"Row {row_idx}: Database error: {str(e)}")
                        skipped += 1

        except (IOError, OSError) as e:
            return {
                "imported": 0,
                "skipped": 0,
                "errors": [f"Cannot read file: {str(e)}"],
            }
        except Exception as e:
            return {
                "imported": imported,
                "skipped": skipped,
                "errors": errors + [f"Unexpected error: {str(e)}"],
            }

        return {
            "imported": imported,
            "skipped": skipped,
            "errors": errors,
        }
