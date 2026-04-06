"""app/ui/dialogs/admin/db_tools_panel.py — Database tools and maintenance admin panel."""
from __future__ import annotations

import os
import sqlite3
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox,
    QProgressBar, QTextEdit, QGroupBox,
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
        self.progress.emit(10, "Running optimizer...")
        conn = get_connection()
        try:
            conn.execute("PRAGMA optimize;")
            self.progress.emit(50, "Optimizing...")
            conn.execute("VACUUM;")
            self.progress.emit(100, "Complete")
            self.finished.emit(True, t("db_tools_result_optimized"))
        finally:
            conn.close()

    def _do_integrity_check(self) -> None:
        """Run PRAGMA integrity_check and report results."""
        self.progress.emit(50, "Checking integrity...")
        conn = get_connection()
        try:
            cursor = conn.execute("PRAGMA integrity_check;")
            result = cursor.fetchall()

            # integrity_check returns a single row with "ok" or error messages
            if result and result[0][0] == "ok":
                self.progress.emit(100, "Complete")
                self.finished.emit(True, t("db_tools_result_ok"))
            else:
                error_msg = "\n".join([row[0] for row in result])
                self.finished.emit(False, f"Integrity issues found:\n{error_msg}")
        finally:
            conn.close()

    def _do_vacuum(self) -> None:
        """Run VACUUM to reclaim space."""
        self.progress.emit(50, "Compacting database...")
        conn = get_connection()
        try:
            conn.execute("VACUUM;")
            self.progress.emit(100, "Complete")
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
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)

        # Header
        hdr = QLabel(t("db_tools_info_title"))
        hdr.setObjectName("dlg_header")
        outer.addWidget(hdr)

        # ── Database Info Section ──
        info_grp = QGroupBox(t("db_tools_info_title"))
        info_lay = QVBoxLayout(info_grp)
        info_lay.setContentsMargins(12, 12, 12, 12)
        info_lay.setSpacing(8)

        self._info_text = QLabel("")
        self._info_text.setObjectName("card_meta")
        self._info_text.setWordWrap(True)
        info_lay.addWidget(self._info_text)

        outer.addWidget(info_grp)

        # ── Operations Section ──
        ops_lbl = QLabel("Operations")
        ops_lbl.setObjectName("section_subheader")
        outer.addWidget(ops_lbl)

        # Optimize button
        opt_row = QHBoxLayout()
        opt_row.setContentsMargins(0, 0, 0, 0)
        opt_row.setSpacing(12)

        opt_btn_col = QVBoxLayout()
        opt_btn_col.setContentsMargins(0, 0, 0, 0)
        opt_btn_col.setSpacing(4)

        self._optimize_btn = QPushButton(t("db_tools_optimize"))
        self._optimize_btn.setObjectName("btn_primary")
        self._optimize_btn.setMinimumHeight(40)
        self._optimize_btn.clicked.connect(self._on_optimize)
        opt_btn_col.addWidget(self._optimize_btn)

        opt_desc = QLabel(t("db_tools_optimize_desc"))
        opt_desc.setObjectName("section_caption")
        opt_desc.setWordWrap(True)
        opt_btn_col.addWidget(opt_desc)

        opt_row.addLayout(opt_btn_col)
        opt_row.addStretch()
        outer.addLayout(opt_row)

        # Integrity check button
        int_row = QHBoxLayout()
        int_row.setContentsMargins(0, 0, 0, 0)
        int_row.setSpacing(12)

        int_btn_col = QVBoxLayout()
        int_btn_col.setContentsMargins(0, 0, 0, 0)
        int_btn_col.setSpacing(4)

        self._integrity_btn = QPushButton(t("db_tools_integrity"))
        self._integrity_btn.setObjectName("btn_secondary")
        self._integrity_btn.setMinimumHeight(40)
        self._integrity_btn.clicked.connect(self._on_integrity_check)
        int_btn_col.addWidget(self._integrity_btn)

        int_desc = QLabel(t("db_tools_integrity_desc"))
        int_desc.setObjectName("section_caption")
        int_desc.setWordWrap(True)
        int_btn_col.addWidget(int_desc)

        int_row.addLayout(int_btn_col)
        int_row.addStretch()
        outer.addLayout(int_row)

        # ── Progress Bar ──
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        outer.addWidget(self._progress)

        # ── Result Display ──
        self._result_display = QTextEdit()
        self._result_display.setReadOnly(True)
        self._result_display.setMaximumHeight(150)
        self._result_display.setVisible(False)
        outer.addWidget(self._result_display)

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
                schema_version = row[0] if row else "Unknown"

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

            # Format display text
            info_lines = [
                f"<b>{t('db_tools_file_path')}:</b> {DB_PATH}",
                f"<b>{t('db_tools_file_size')}:</b> {file_size_mb:.2f} MB",
                f"<b>{t('db_tools_schema_ver')}:</b> {schema_version}",
                f"<b>Tables:</b> {table_count}",
                f"<b>Total Rows:</b> {total_rows}",
            ]

            self._info_text.setText("<br>".join(info_lines))

        except Exception as e:
            self._info_text.setText(f"Error loading database info: {str(e)}")

    def _on_optimize(self) -> None:
        """Handle optimize button click."""
        reply = QMessageBox.question(
            self,
            t("db_tools_optimize"),
            "This will optimize the database and may take a moment. Continue?",
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
        self._result_display.setVisible(True)

        if success:
            self._result_display.setStyleSheet("color: green;")
            QMessageBox.information(
                self,
                "Success",
                message,
            )
        else:
            self._result_display.setStyleSheet("color: red;")
            QMessageBox.warning(
                self,
                "Error",
                message,
            )

        self._result_display.setPlainText(message)

        # Re-enable buttons
        self._optimize_btn.setEnabled(True)
        self._integrity_btn.setEnabled(True)

        # Reload DB info in case size changed
        self._load_db_info()
