"""app/ui/dialogs/admin/import_export_panel.py — CSV import and export admin panel."""
from __future__ import annotations

import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox,
    QFileDialog, QTableWidget, QTableWidgetItem, QComboBox, QCheckBox,
)
from PyQt6.QtCore import Qt

from app.services.export_service import ExportService
from app.services.import_service import ImportService
from app.core.theme import THEME
from app.core.i18n import t


class ImportExportPanel(QWidget):
    """Admin panel for CSV export and product import operations."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._export_svc = ExportService()
        self._import_svc = ImportService()
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(20)

        # Header
        hdr = QLabel(t("import_export_title"))
        hdr.setObjectName("dlg_header")
        outer.addWidget(hdr)

        # ── Export Section ──
        export_hdr = QLabel(t("export_section_label"))
        export_hdr.setObjectName("section_subheader")
        outer.addWidget(export_hdr)

        export_layout = QVBoxLayout()
        export_layout.setContentsMargins(0, 0, 0, 0)
        export_layout.setSpacing(8)

        export_btn_row = QHBoxLayout()
        export_btn_row.setContentsMargins(0, 0, 0, 0)
        export_btn_row.setSpacing(8)

        btn_inv = QPushButton(t("export_inventory_btn"))
        btn_inv.setObjectName("btn_secondary")
        btn_inv.clicked.connect(self._on_export_inventory)
        export_btn_row.addWidget(btn_inv)

        btn_txn = QPushButton(t("export_transactions_btn"))
        btn_txn.setObjectName("btn_secondary")
        btn_txn.clicked.connect(self._on_export_transactions)
        export_btn_row.addWidget(btn_txn)

        btn_low = QPushButton(t("export_low_stock_btn"))
        btn_low.setObjectName("btn_secondary")
        btn_low.clicked.connect(self._on_export_low_stock)
        export_btn_row.addWidget(btn_low)

        export_btn_row.addStretch()
        export_layout.addLayout(export_btn_row)

        self._export_status = QLabel("")
        self._export_status.setObjectName("card_meta_dim")
        self._export_status.setWordWrap(True)
        export_layout.addWidget(self._export_status)

        outer.addLayout(export_layout)

        # ── Import Section ──
        import_hdr = QLabel(t("import_section_label"))
        import_hdr.setObjectName("section_subheader")
        outer.addWidget(import_hdr)

        import_layout = QVBoxLayout()
        import_layout.setContentsMargins(0, 0, 0, 0)
        import_layout.setSpacing(12)

        # Select file and preview
        file_row = QHBoxLayout()
        file_row.setContentsMargins(0, 0, 0, 0)
        file_row.setSpacing(8)

        self._select_file_btn = QPushButton(t("import_select_file_btn"))
        self._select_file_btn.setObjectName("btn_secondary")
        self._select_file_btn.clicked.connect(self._on_select_import_file)
        file_row.addWidget(self._select_file_btn)

        self._file_label = QLabel(t("import_no_file"))
        self._file_label.setObjectName("card_meta_dim")
        file_row.addWidget(self._file_label)
        file_row.addStretch()
        import_layout.addLayout(file_row)

        # Preview table
        preview_lbl = QLabel(t("import_preview_label"))
        preview_lbl.setObjectName("section_caption")
        import_layout.addWidget(preview_lbl)

        self._preview_table = QTableWidget()
        self._preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._preview_table.setMaximumHeight(150)
        import_layout.addWidget(self._preview_table)

        # Column mapping
        mapping_lbl = QLabel(t("import_column_mapping_label"))
        mapping_lbl.setObjectName("section_caption")
        import_layout.addWidget(mapping_lbl)

        # Create column mapping form
        self._col_combos = {}
        mapping_row = QHBoxLayout()
        mapping_row.setContentsMargins(0, 0, 0, 0)
        mapping_row.setSpacing(12)

        for field_name, label_key in [
            ("brand", "import_col_brand"),
            ("name", "import_col_name"),
            ("color", "import_col_color"),
            ("barcode", "import_col_barcode"),
            ("stock", "import_col_stock"),
            ("min_stock", "import_col_min_stock"),
            ("price", "import_col_price"),
        ]:
            col_layout = QVBoxLayout()
            col_layout.setContentsMargins(0, 0, 0, 0)
            col_layout.setSpacing(4)
            lbl = QLabel(t(label_key))
            lbl.setObjectName("section_caption")
            col_layout.addWidget(lbl)
            combo = QComboBox()
            combo.setMinimumWidth(80)
            self._col_combos[field_name] = combo
            col_layout.addWidget(combo)
            mapping_row.addLayout(col_layout)

        mapping_row.addStretch()
        import_layout.addLayout(mapping_row)

        # Skip header checkbox
        self._skip_header_cb = QCheckBox(t("import_skip_header_cb"))
        self._skip_header_cb.setChecked(True)
        import_layout.addWidget(self._skip_header_cb)

        # Import button and result
        import_btn_row = QHBoxLayout()
        import_btn_row.setContentsMargins(0, 0, 0, 0)
        import_btn_row.setSpacing(8)

        self._import_btn = QPushButton(t("import_execute_btn"))
        self._import_btn.setObjectName("btn_primary")
        self._import_btn.clicked.connect(self._on_import_products)
        self._import_btn.setEnabled(False)
        import_btn_row.addWidget(self._import_btn)

        self._import_status = QLabel("")
        self._import_status.setObjectName("card_meta_dim")
        import_btn_row.addWidget(self._import_status)
        import_btn_row.addStretch()
        import_layout.addLayout(import_btn_row)

        outer.addLayout(import_layout)
        outer.addStretch()

        # Store file path for import
        self._import_file_path = None

    # ── Export Methods ────────────────────────────────────────────────────────

    def _on_export_inventory(self) -> None:
        """Export inventory to CSV."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            t("export_inventory_dialog"),
            "",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not file_path:
            return

        try:
            self._export_svc.export_inventory_csv(file_path)
            self._export_status.setText(
                t("export_success", filename=os.path.basename(file_path))
            )
            QMessageBox.information(
                self,
                t("export_success_title"),
                t("export_file_saved", path=file_path),
            )
        except Exception as e:
            self._export_status.setText(t("export_error"))
            QMessageBox.critical(
                self,
                t("export_error_title"),
                t("export_error_msg", error=str(e)),
            )

    def _on_export_transactions(self) -> None:
        """Export transactions to CSV."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            t("export_transactions_dialog"),
            "",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not file_path:
            return

        try:
            self._export_svc.export_transactions_csv(file_path)
            self._export_status.setText(
                t("export_success", filename=os.path.basename(file_path))
            )
            QMessageBox.information(
                self,
                t("export_success_title"),
                t("export_file_saved", path=file_path),
            )
        except Exception as e:
            self._export_status.setText(t("export_error"))
            QMessageBox.critical(
                self,
                t("export_error_title"),
                t("export_error_msg", error=str(e)),
            )

    def _on_export_low_stock(self) -> None:
        """Export low stock items to CSV."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            t("export_low_stock_dialog"),
            "",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not file_path:
            return

        try:
            self._export_svc.export_low_stock_csv(file_path)
            self._export_status.setText(
                t("export_success", filename=os.path.basename(file_path))
            )
            QMessageBox.information(
                self,
                t("export_success_title"),
                t("export_file_saved", path=file_path),
            )
        except Exception as e:
            self._export_status.setText(t("export_error"))
            QMessageBox.critical(
                self,
                t("export_error_title"),
                t("export_error_msg", error=str(e)),
            )

    # ── Import Methods ────────────────────────────────────────────────────────

    def _on_select_import_file(self) -> None:
        """Select a CSV file for import."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t("import_select_file_dialog"),
            "",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not file_path:
            return

        self._import_file_path = file_path
        self._file_label.setText(os.path.basename(file_path))

        # Preview the file
        self._load_preview()

    def _load_preview(self) -> None:
        """Load and display file preview."""
        if not self._import_file_path:
            return

        preview_data = self._import_svc.preview_csv(self._import_file_path, max_rows=10)
        headers = preview_data["headers"]
        rows = preview_data["rows"]

        # Populate table
        self._preview_table.setRowCount(0)
        self._preview_table.setColumnCount(len(headers))
        self._preview_table.setHorizontalHeaderLabels(headers)

        for i, row in enumerate(rows):
            self._preview_table.insertRow(i)
            for j, cell_value in enumerate(row):
                item = QTableWidgetItem(str(cell_value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._preview_table.setItem(i, j, item)

        # Auto-fit columns
        self._preview_table.resizeColumnsToContents()

        # Populate column mapping dropdowns
        self._populate_column_mappings(headers)

        # Enable import button
        self._import_btn.setEnabled(True)
        self._import_status.setText("")

    def _populate_column_mappings(self, headers: list) -> None:
        """Populate column mapping dropdowns with header options."""
        # Add option to skip column
        options = ["<skip>"] + headers

        for field_name, combo in self._col_combos.items():
            combo.clear()
            combo.addItems(options)

            # Try to auto-select based on field name
            idx = combo.findText(field_name, Qt.MatchFlag.MatchContains)
            if idx >= 0:
                combo.setCurrentIndex(idx)

    def _on_import_products(self) -> None:
        """Import products from CSV."""
        if not self._import_file_path:
            QMessageBox.warning(
                self,
                t("import_warning_title"),
                t("import_select_file_first"),
            )
            return

        # Build column mapping from combos
        preview_data = self._import_svc.preview_csv(self._import_file_path)
        headers = preview_data["headers"]
        column_map = {}

        for field_name, combo in self._col_combos.items():
            selected = combo.currentText()
            if selected != "<skip>" and selected in headers:
                column_map[field_name] = headers.index(selected)

        # Validate required fields
        if "brand" not in column_map or "name" not in column_map:
            QMessageBox.warning(
                self,
                t("import_warning_title"),
                t("import_missing_required_cols"),
            )
            return

        # Perform import
        skip_header = self._skip_header_cb.isChecked()

        try:
            result = self._import_svc.import_products_csv(
                self._import_file_path,
                column_map,
                skip_header=skip_header,
            )

            imported = result.get("imported", 0)
            skipped = result.get("skipped", 0)
            errors_list = result.get("errors", [])
            error_count = len(errors_list)

            # Show result summary
            summary = t(
                "import_result_summary",
                imported=imported,
                skipped=skipped,
                errors=error_count,
            )
            self._import_status.setText(summary)

            # Show detailed dialog
            if error_count > 0:
                error_msg = "\n".join(errors_list[:10])  # Show first 10 errors
                if error_count > 10:
                    error_msg += f"\n... and {error_count - 10} more errors"

                QMessageBox.warning(
                    self,
                    t("import_partial_title"),
                    t("import_partial_msg", imported=imported, errors=error_count)
                    + "\n\n" + error_msg,
                )
            else:
                QMessageBox.information(
                    self,
                    t("import_success_title"),
                    t("import_success_msg", count=imported),
                )

            # Reset for next import
            self._import_file_path = None
            self._file_label.setText(t("import_no_file"))
            self._preview_table.setRowCount(0)
            self._import_btn.setEnabled(False)

        except Exception as e:
            QMessageBox.critical(
                self,
                t("import_error_title"),
                t("import_error_msg", error=str(e)),
            )

    def reload(self) -> None:
        """Reload the panel."""
        self._export_status.setText("")
        self._import_status.setText("")
