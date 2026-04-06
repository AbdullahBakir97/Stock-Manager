"""app/ui/dialogs/admin/db_tools_panel.py — Database tools and maintenance admin panel."""
from __future__ import annotations

import os
import sqlite3
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox,
    QProgressBar, QTextEdit, QFrame, QScrollArea, QSizePolicy, QGridLayout,
)
from PyQt6.QtCore import pyqtSignal, Qt, QThread, pyqtSignal as Signal

from app.core.database import get_connection, DB_PATH
from app.core.theme import THEME
from app.core.i18n import t


class DatabaseWorkerThread(QThread):
    """Worker thread for database operations to avoid UI blocking."""

    progress = Signal(int, str)  # (progress_percent, message)
    finished = Signal(bool, str)  # (success, result_message)

    def __init__(self, operation: str):
        super().__init__()
        self.operation = operation

    def run(self) -> None:
        """Execute database operation in background thread."""
        try:
            if self.operation == "optimize":
                self._do_optimize()
            elif self.operation == "integrity":
                self._do_integrity_check()
            elif self.operation == "vacuum":
                self._do_vacuum()
        except Exception as e:
            self.finished.emit(False, str(e))

    def _do_optimize(self) -> None:
        """Run PRAGMA optimize and VACUUM."""
        self.progress.emit(10, t("db_tools_running_optimizer"))
        conn = get_connection()
        try:
            conn.execute("PRAGMA optimize;")
            self.progress.emit(50, t("db_tools_optimizing"))
            conn.execute("VACUUM;")
            self.progress.emit(100, t("db_tools_complete"))
            self.finished.emit(True, t("db_tools_result_optimized"))
        finally:
            conn.close()

    def _do_integrity_check(self) -> None:
        """Run PRAGMA integrity_check and report results."""
        self.progress.emit(50, t("db_tools_checking_integrity"))
        conn = get_connection()
        try:
            cursor = conn.execute("PRAGMA integrity_check;")
            result = cursor.fetchall()

            if result and result[0][0] == "ok":
                self.progress.emit(100, t("db_tools_complete"))
                self.finished.emit(True, t("db_tools_result_ok"))
            else:
                error_msg = "\n".join([row[0] for row in result])
                self.finished.emit(False, t("db_tools_integrity_issues", msg=error_msg))
        finally:
            conn.close()

    def _do_vacuum(self) -> None:
        """Run VACUUM to reclaim space."""
        self.progress.emit(50, t("db_tools_compacting"))
        conn = get_connection()
        try:
            conn.execute("VACUUM;")
            self.progress.emit(100, t("db_tools_complete"))
            self.finished.emit(True, t("db_tools_result_optimized"))
        finally:
            conn.close()


class DatabaseToolsPanel(QWidget):
    """Admin panel for database maintenance and diagnostics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._build_ui()
        self._load_db_info()

    def _build_ui(self) -> None:
        """Build the UI layout."""
        # ── Scroll container ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setObjectName("analytics_scroll")
        inner = QWidget()
        scroll.setWidget(inner)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        outer = QVBoxLayout(inner)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)

        # ── Header ──
        title = QLabel(
            t("db_tools_info_title") if t("db_tools_info_title") != "db_tools_info_title" else "Database Tools"
        )
        title.setObjectName("admin_content_title")
        outer.addWidget(title)

        subtitle = QLabel(
            t("db_tools_subtitle") if t("db_tools_subtitle") != "db_tools_subtitle"
            else "Maintain database health and optimize performance"
        )
        subtitle.setObjectName("admin_content_desc")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        # ── Database Info Card ──
        info_card = QFrame()
        info_card.setObjectName("admin_form_card")
        info_lay = QVBoxLayout(info_card)
        info_lay.setContentsMargins(20, 16, 20, 16)
        info_lay.setSpacing(12)

        info_title = QLabel(
            t("db_tools_info_title") if t("db_tools_info_title") != "db_tools_info_title" else "Database Information"
        )
        info_title.setObjectName("admin_form_card_title")
        info_lay.addWidget(info_title)

        # ── Info Grid ──
        info_grid = QGridLayout()
        info_grid.setContentsMargins(0, 0, 0, 0)
        info_grid.setSpacing(16)
        info_grid.setColumnStretch(0, 0)
        info_grid.setColumnStretch(1, 0)
        info_grid.setColumnStretch(2, 0)
        info_grid.setColumnStretch(3, 0)
        info_grid.setColumnStretch(4, 1)

        self._info_labels = {}

        # File Path
        lbl = QLabel(t("db_tools_file_path") if t("db_tools_file_path") != "db_tools_file_path" else "File Path")
        lbl.setObjectName("admin_info_label")
        info_grid.addWidget(lbl, 0, 0)
        val = QLabel("")
        val.setObjectName("admin_info_value")
        val.setWordWrap(True)
        info_grid.addWidget(val, 0, 1, 1, 4)
        self._info_labels["path"] = val

        # File Size
        lbl = QLabel(t("db_tools_file_size") if t("db_tools_file_size") != "db_tools_file_size" else "File Size")
        lbl.setObjectName("admin_info_label")
        info_grid.addWidget(lbl, 1, 0)
        val = QLabel("")
        val.setObjectName("admin_info_value")
        info_grid.addWidget(val, 1, 1)
        self._info_labels["size"] = val

        # Schema Version
        lbl = QLabel(t("db_tools_schema_ver") if t("db_tools_schema_ver") != "db_tools_schema_ver" else "Schema Ver.")
        lbl.setObjectName("admin_info_label")
        info_grid.addWidget(lbl, 1, 2)
        val = QLabel("")
        val.setObjectName("admin_info_value")
        info_grid.addWidget(val, 1, 3)
        self._info_labels["schema"] = val

        # Tables
        lbl = QLabel(t("db_tools_tables") if t("db_tools_tables") != "db_tools_tables" else "Tables")
        lbl.setObjectName("admin_info_label")
        info_grid.addWidget(lbl, 2, 0)
        val = QLabel("")
        val.setObjectName("admin_info_value")
        info_grid.addWidget(val, 2, 1)
        self._info_labels["tables"] = val

        # Total Rows
        lbl = QLabel(t("db_tools_total_rows") if t("db_tools_total_rows") != "db_tools_total_rows" else "Total Rows")
        lbl.setObjectName("admin_info_label")
        info_grid.addWidget(lbl, 2, 2)
        val = QLabel("")
        val.setObjectName("admin_info_value")
        info_grid.addWidget(val, 2, 3)
        self._info_labels["rows"] = val

        info_lay.addLayout(info_grid)
        outer.addWidget(info_card)

        # ── Maintenance Card ──
        maint_card = QFrame()
        maint_card.setObjectName("admin_form_card")
        maint_lay = QVBoxLayout(maint_card)
        maint_lay.setContentsMargins(20, 16, 20, 16)
        maint_lay.setSpacing(12)

        maint_title = QLabel(
            t("db_tools_maintenance") if t("db_tools_maintenance") != "db_tools_maintenance" else "Maintenance"
        )
        maint_title.setObjectName("admin_form_card_title")
        maint_lay.addWidget(maint_title)

        # Optimize section
        opt_row = QVBoxLayout()
        opt_row.setContentsMargins(0, 0, 0, 0)
        opt_row.setSpacing(8)

        opt_lbl = QLabel(
            t("db_tools_optimize") if t("db_tools_optimize") != "db_tools_optimize" else "Optimize Database"
        )
        opt_lbl.setObjectName("admin_form_card_title")
        opt_row.addWidget(opt_lbl)

        opt_desc = QLabel(
            t("db_tools_optimize_desc") if t("db_tools_optimize_desc") != "db_tools_optimize_desc"
            else "Rebuild indexes and recover unused space to improve performance"
        )
        opt_desc.setObjectName("admin_form_card_desc")
        opt_desc.setWordWrap(True)
        opt_row.addWidget(opt_desc)

        opt_btn_row = QHBoxLayout()
        opt_btn_row.setContentsMargins(0, 0, 0, 0)
        self._optimize_btn = QPushButton(
            t("db_tools_optimize") if t("db_tools_optimize") != "db_tools_optimize" else "Optimize"
        )
        self._optimize_btn.setObjectName("btn_primary")
        self._optimize_btn.setMinimumHeight(40)
        self._optimize_btn.clicked.connect(self._on_optimize)
        opt_btn_row.addWidget(self._optimize_btn)
        opt_btn_row.addStretch()
        opt_row.addLayout(opt_btn_row)

        maint_lay.addLayout(opt_row)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("admin_form_card")
        maint_lay.addWidget(sep)

        # Integrity check section
        int_row = QVBoxLayout()
        int_row.setContentsMargins(0, 0, 0, 0)
        int_row.setSpacing(8)

        int_lbl = QLabel(
            t("db_tools_integrity") if t("db_tools_integrity") != "db_tools_integrity" else "Integrity Check"
        )
        int_lbl.setObjectName("admin_form_card_title")
        int_row.addWidget(int_lbl)

        int_desc = QLabel(
            t("db_tools_integrity_desc") if t("db_tools_integrity_desc") != "db_tools_integrity_desc"
            else "Verify database structure and consistency"
        )
        int_desc.setObjectName("admin_form_card_desc")
        int_desc.setWordWrap(True)
        int_row.addWidget(int_desc)

        int_btn_row = QHBoxLayout()
        int_btn_row.setContentsMargins(0, 0, 0, 0)
        self._integrity_btn = QPushButton(
            t("db_tools_integrity") if t("db_tools_integrity") != "db_tools_integrity" else "Check Integrity"
        )
        self._integrity_btn.setObjectName("btn_primary")
        self._integrity_btn.setMinimumHeight(40)
        self._integrity_btn.clicked.connect(self._on_integrity_check)
        int_btn_row.addWidget(self._integrity_btn)
        int_btn_row.addStretch()
        int_row.addLayout(int_btn_row)

        maint_lay.addLayout(int_row)

        outer.addWidget(maint_card)

        # ── Progress Bar ──
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        outer.addWidget(self._progress)

        # ── Result Card ──
        self._result_card = QFrame()
        self._result_card.setObjectName("admin_form_card")
        self._result_card.setVisible(False)
        result_lay = QVBoxLayout(self._result_card)
        result_lay.setContentsMargins(20, 16, 20, 16)
        result_lay.setSpacing(8)

        result_title = QLabel(
            t("db_tools_result") if t("db_tools_result") != "db_tools_result" else "Operation Result"
        )
        result_title.setObjectName("admin_form_card_title")
        result_lay.addWidget(result_title)

        self._result_display = QTextEdit()
        self._result_display.setReadOnly(True)
        self._result_display.setMaximumHeight(150)
        result_lay.addWidget(self._result_display)

        outer.addWidget(self._result_card)

        outer.addStretch()

    def _load_db_info(self) -> None:
        """Load and display database information."""
        try:
            # File info
            if os.path.exists(DB_PATH):
                file_size = os.path.getsize(DB_PATH)
                file_size_mb = file_size / (1024 * 1024)
            else:
                file_size_mb = 0

            # DB info
            conn = get_connection()
            try:
                # Schema version
                cursor = conn.execute(
                    "SELECT value FROM app_config WHERE key = 'schema_version'"
                )
                row = cursor.fetchone()
                schema_version = row[0] if row else t("db_tools_unknown") if t("db_tools_unknown") != "db_tools_unknown" else "Unknown"

                # Table count
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                )
                table_count = cursor.fetchone()[0]

                # Total rows (across all tables)
                cursor = conn.execute("""
                    SELECT SUM(row_count) FROM (
                        SELECT COUNT(*) as row_count FROM inventory_items
                        UNION ALL SELECT COUNT(*) FROM categories
                        UNION ALL SELECT COUNT(*) FROM part_types
                        UNION ALL SELECT COUNT(*) FROM phone_models
                        UNION ALL SELECT COUNT(*) FROM inventory_transactions
                    )
                """)
                total_rows = cursor.fetchone()[0] or 0

            finally:
                conn.close()

            # Update info labels
            self._info_labels["path"].setText(DB_PATH)
            self._info_labels["size"].setText(f"{file_size_mb:.2f} MB")
            self._info_labels["schema"].setText(str(schema_version))
            self._info_labels["tables"].setText(str(table_count))
            self._info_labels["rows"].setText(str(total_rows))

        except Exception as e:
            for label in self._info_labels.values():
                label.setText("—")

    def _on_optimize(self) -> None:
        """Handle optimize button click."""
        reply = QMessageBox.question(
            self,
            t("db_tools_optimize"),
            t("db_tools_confirm_optimize"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self._run_operation("optimize")

    def _on_integrity_check(self) -> None:
        """Handle integrity check button click."""
        self._run_operation("integrity")

    def _run_operation(self, operation: str) -> None:
        """Run a database operation in a worker thread."""
        # Disable buttons
        self._optimize_btn.setEnabled(False)
        self._integrity_btn.setEnabled(False)

        # Show progress bar and clear result display
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._result_display.setVisible(False)
        self._result_display.clear()

        # Create and start worker
        self._worker = DatabaseWorkerThread(operation)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_operation_finished)
        self._worker.start()

    def _on_progress(self, value: int, message: str) -> None:
        """Update progress bar."""
        self._progress.setValue(value)

    def _on_operation_finished(self, success: bool, message: str) -> None:
        """Handle operation completion."""
        self._progress.setVisible(False)
        self._result_card.setVisible(True)

        if success:
            self._result_display.setStyleSheet("color: green;")
            QMessageBox.information(
                self,
                t("db_tools_success") if t("db_tools_success") != "db_tools_success" else "Success",
                message,
            )
        else:
            self._result_display.setStyleSheet("color: red;")
            QMessageBox.warning(
                self,
                t("db_tools_error") if t("db_tools_error") != "db_tools_error" else "Error",
                message,
            )

        self._result_display.setPlainText(message)

        # Re-enable buttons
        self._optimize_btn.setEnabled(True)
        self._integrity_btn.setEnabled(True)

        # Reload DB info in case size changed
        self._load_db_info()
