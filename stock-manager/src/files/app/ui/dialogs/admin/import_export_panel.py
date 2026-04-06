"""app/ui/dialogs/admin/import_export_panel.py — CSV import and export admin panel."""
from __future__ import annotations

import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox,
    QFileDialog, QTableWidget, QTableWidgetItem, QComboBox, QCheckBox,
    QScrollArea, QFrame,
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
        self._import_file_path = None
        self._build_ui()

    def _build_ui(self) -> None:
        # ── Scroll Container ──
        scroll = QScrollArea()
        scroll.setObjectName("analytics_scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        inner = QWidget()
        scroll.setWidget(inner)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        outer = QVBoxLayout(inner)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(20)

        # ── Header ──
        title = QLabel(t("import_export_title") if t("import_export_title") != "import_export_title" else "Import & Export")
        title.setObjectName("admin_content_title")
        outer.addWidget(title)

        subtitle = QLabel(t("import_export_subtitle") if t("import_export_subtitle") != "import_export_subtitle" else "Manage data import and export operations")
        subtitle.setObjectName("admin_content_desc")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        # ── Export Data Card ──
        export_card = QFrame()
        export_card.setObjectName("admin_form_card")
        export_layout = QVBoxLayout(export_card)
        export_layout.setContentsMargins(16, 12, 16, 12)
        export_layout.setSpacing(12)

        export_title = QLabel(t("export_section_label") if t("export_section_label") != "export_section_label" else "Export Data")
        export_title.setObjectName("admin_form_card_title")
        export_layout.addWidget(export_title)

        export_desc = QLabel(t("export_description") if t("export_description") != "export_description" else "Download your inventory, transactions, and reports")
        export_desc.setObjectName("admin_form_card_desc")
        export_desc.setWordWrap(True)
        export_layout.addWidget(export_desc)

        export_btn_row = QHBoxLayout()
        export_btn_row.setContentsMargins(0, 0, 0, 0)
        export_btn_row.setSpacing(8)

        btn_inv = QPushButton(t("export_inventory_btn") if t("export_inventory_btn") != "export_inventory_btn" else "Export Inventory")
        btn_inv.setObjectName("btn_ghost")
        btn_inv.clicked.connect(self._on_export_inventory)
        export_btn_row.addWidget(btn_inv)

        btn_txn = QPushButton(t("export_transactions_btn") if t("export_transactions_btn") != "export_transactions_btn" else "Export Transactions")
        btn_txn.setObjectName("btn_ghost")
        btn_txn.clicked.connect(self._on_export_transactions)
        export_btn_row.addWidget(btn_txn)

        btn_low = QPushButton(t("export_low_stock_btn") if t("export_low_stock_btn") != "export_low_stock_btn" else "Low Stock")
        btn_low.setObjectName("btn_ghost")
        btn_low.clicked.connect(self._on_export_low_stock)
        export_btn_row.addWidget(btn_low)

        btn_xlsx = QPushButton(t("export_excel") if t("export_excel") != "export_excel" else "Excel Export")
        btn_xlsx.setObjectName("admin_action_btn")
        btn_xlsx.clicked.connect(self._on_export_excel)
        export_btn_row.addWidget(btn_xlsx)

        export_btn_row.addStretch()
        export_layout.addLayout(export_btn_row)

        self._export_status = QLabel("")
        self._export_status.setObjectName("card_meta_dim")
        self._export_status.setWordWrap(True)
        export_layout.addWidget(self._export_status)

        outer.addWidget(export_card)

        # ── Import Data Card ──
        import_card = QFrame()
        import_card.setObjectName("admin_form_card")
        import_layout = QVBoxLayout(import_card)
        import_layout.setContentsMargins(16, 12, 16, 12)
        import_layout.setSpacing(12)

        import_title = QLabel(t("import_section_label") if t("import_section_label") != "import_section_label" else "Import Data")
        import_title.setObjectName("admin_form_card_title")
        import_layout.addWidget(import_title)

        import_desc = QLabel(t("import_description") if t("import_description") != "import_description" else "Import products and inventory from CSV or Excel")
        import_desc.setObjectName("admin_form_card_desc")
        import_desc.setWordWrap(True)
        import_layout.addWidget(import_desc)

        # File selector row
        file_row = QHBoxLayout()
        file_row.setContentsMargins(0, 0, 0, 0)
        file_row.setSpacing(8)

        self._select_file_btn = QPushButton(t("import_select_file_btn") if t("import_select_file_btn") != "import_select_file_btn" else "Select File")
        self._select_file_btn.setObjectName("btn_primary")
        self._select_file_btn.clicked.connect(self._on_select_import_file)
        file_row.addWidget(self._select_file_btn)

        self._file_label = QLabel(t("import_no_file") if t("import_no_file") != "import_no_file" else "No file selected")
        self._file_label.setObjectName("card_meta_dim")
        file_row.addWidget(self._file_label)
        file_row.addStretch()
        import_layout.addLayout(file_row)

        # Preview table
        preview_lbl = QLabel(t("import_preview_label") if t("import_preview_label") != "import_preview_label" else "Data Preview")
        preview_lbl.setObjectName("admin_form_card_desc")
        import_layout.addWidget(preview_lbl)

        self._preview_table = QTableWidget()
        self._preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._preview_table.setMaximumHeight(150)
        import_layout.addWidget(self._preview_table)

        # Column mapping
        mapping_lbl = QLabel(t("import_column_mapping_label") if t("import_column_mapping_label") != "import_column_mapping_label" else "Column Mapping")
        mapping_lbl.setObjectName("admin_form_card_desc")
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
            lbl = QLabel(t(label_key) if t(label_key) != label_key else label_key.replace("import_col_", "").title())
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
        self._skip_header_cb = QCheckBox(t("import_skip_header_cb") if t("import_skip_header_cb") != "import_skip_header_cb" else "Skip first row (header)")
        self._skip_header_cb.setChecked(True)
        import_layout.addWidget(self._skip_header_cb)

        # Import button and result
        import_btn_row = QHBoxLayout()
        import_btn_row.setContentsMargins(0, 0, 0, 0)
        import_btn_row.setSpacing(8)

        self._import_btn = QPushButton(t("import_execute_btn") if t("import_execute_btn") != "import_execute_btn" else "Import Products")
        self._import_btn.setObjectName("admin_action_btn")
        self._import_btn.clicked.connect(self._on_import_products)
        self._import_btn.setEnabled(False)
        import_btn_row.addWidget(self._import_btn)

        self._import_status = QLabel("")
        self._import_status.setObjectName("card_meta_dim")
        import_btn_row.addWidget(self._import_status)
        import_btn_row.addStretch()
        import_layout.addLayout(import_btn_row)

        outer.addWidget(import_card)
        outer.addStretch()

    # ── Export Methods ──

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

    def _on_export_excel(self) -> None:
        """Export inventory to Excel (.xlsx)."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            t("export_excel"),
            "",
            "Excel Files (*.xlsx);;All Files (*)",
        )
        if not file_path:
            return
        if not file_path.endswith(".xlsx"):
            file_path += ".xlsx"

        try:
            self._export_svc.export_inventory_xlsx(file_path)
            self._export_status.setText(
                t("export_excel_success", path=os.path.basename(file_path))
            )
            QMessageBox.information(
                self,
                t("export_success_title"),
                t("export_file_saved", path=file_path),
            )
        except Exception as e:
            self._export_status.setText(t("export_excel_failed"))
            QMessageBox.critical(
                self,
                t("export_error_title"),
                t("export_error_msg", error=str(e)),
            )

    # ── Import Methods ──

    def _on_select_import_file(self) -> None:
        """Select a CSV or Excel file for import."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t("import_select_file_dialog"),
            "",
            "Spreadsheets (*.csv *.xlsx);;CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*)",
        )
        if not file_path:
            return

        self._import_file_path = file_path
        self._file_label.setText(os.path.basename(file_path))

        # Preview the file
        self._load_preview()

    @property
    def _is_xlsx(self) -> bool:
        """Check if the selected import file is an Excel file."""
        return bool(self._import_file_path
                     and self._import_file_path.lower().endswith(".xlsx"))

    def _load_preview(self) -> None:
        """Load and display file preview."""
        if not self._import_file_path:
            return

        if self._is_xlsx:
            preview_data = self._import_svc.preview_xlsx(self._import_file_path, max_rows=10)
        else:
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
        if self._is_xlsx:
            preview_data = self._import_svc.preview_xlsx(self._import_file_path)
        else:
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
            if self._is_xlsx:
                result = self._import_svc.import_products_xlsx(
                    self._import_file_path,
                    column_map,
                    skip_header=skip_header,
                )
            else:
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
