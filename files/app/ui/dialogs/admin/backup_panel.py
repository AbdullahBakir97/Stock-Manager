"""app/ui/dialogs/admin/backup_panel.py — Database backup and restore admin panel."""
from __future__ import annotations

import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, Qt

from app.services.backup_service import BackupService
from app.core.theme import THEME
from app.core.i18n import t


class BackupPanel(QWidget):
    """Admin panel for database backup and restore operations."""

    backup_restored = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._backup_svc = BackupService()
        self._build_ui()
        self._load_backups()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)

        # Header
        hdr = QLabel(t("backup_title"))
        hdr.setObjectName("dlg_header")
        outer.addWidget(hdr)

        hint = QLabel(t("backup_desc"))
        hint.setObjectName("section_caption")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        # ── Create Backup Section ──
        create_row = QHBoxLayout()
        create_row.setContentsMargins(0, 0, 0, 0)
        self._create_btn = QPushButton(t("backup_create_btn"))
        self._create_btn.setObjectName("btn_primary")
        self._create_btn.setMinimumHeight(40)
        self._create_btn.clicked.connect(self._on_create_backup)
        create_row.addWidget(self._create_btn)
        create_row.addStretch()
        outer.addLayout(create_row)

        # ── Backup List Table ──
        list_lbl = QLabel(t("backup_list_label"))
        list_lbl.setObjectName("section_subheader")
        outer.addWidget(list_lbl)

        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels([
            t("backup_col_date"),
            t("backup_col_size"),
            t("backup_col_file"),
        ])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setColumnWidth(0, 150)
        self._table.setColumnWidth(1, 100)
        self._table.setColumnWidth(2, 200)
        outer.addWidget(self._table)

        # ── Action Buttons ──
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(8)

        self._restore_btn = QPushButton(t("backup_restore_btn"))
        self._restore_btn.setObjectName("btn_secondary")
        self._restore_btn.clicked.connect(self._on_restore)
        btn_row.addWidget(self._restore_btn)

        self._delete_btn = QPushButton(t("backup_delete_btn"))
        self._delete_btn.setObjectName("btn_danger")
        self._delete_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(self._delete_btn)

        self._folder_btn = QPushButton(t("backup_open_folder_btn"))
        self._folder_btn.setObjectName("btn_secondary")
        self._folder_btn.clicked.connect(self._on_open_folder)
        btn_row.addWidget(self._folder_btn)

        btn_row.addStretch()
        outer.addLayout(btn_row)

        # ── Status Label ──
        self._status = QLabel("")
        self._status.setObjectName("card_meta_dim")
        self._status.setWordWrap(True)
        outer.addWidget(self._status)

        outer.addStretch()

    def _load_backups(self) -> None:
        """Load and display all backups in the table."""
        self._table.setRowCount(0)
        backups = self._backup_svc.list_backups()

        for i, backup in enumerate(backups):
            self._table.insertRow(i)

            # Date column
            mtime = backup["date"]
            dt = datetime.fromtimestamp(mtime)
            date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            date_item = QTableWidgetItem(date_str)
            date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(i, 0, date_item)

            # Size column
            size = backup["size"]
            size_mb = size / (1024 * 1024)
            size_str = f"{size_mb:.1f} MB"
            size_item = QTableWidgetItem(size_str)
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(i, 1, size_item)

            # Filename column
            filename = backup["filename"]
            file_item = QTableWidgetItem(filename)
            file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(i, 2, file_item)

            # Store the path as user data for later reference
            date_item.setData(Qt.ItemDataRole.UserRole, backup["path"])

    def _on_create_backup(self) -> None:
        """Create a new backup."""
        try:
            backup_path = self._backup_svc.create_backup()
            # Auto-cleanup: keep only 10 most recent
            self._backup_svc.auto_cleanup(keep=10)
            self._status.setText(t("backup_created", path=os.path.basename(backup_path)))
            self._load_backups()
        except IOError as e:
            QMessageBox.critical(
                self,
                t("backup_error_title"),
                t("backup_error_create", error=str(e)),
            )

    def _on_restore(self) -> None:
        """Restore the selected backup."""
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.warning(
                self,
                t("backup_warning_title"),
                t("backup_select_to_restore"),
            )
            return

        # Get the backup path from the first column's user data
        item = self._table.item(row, 0)
        backup_path = item.data(Qt.ItemDataRole.UserRole)
        filename = self._table.item(row, 2).text()

        # Confirm action
        reply = QMessageBox.question(
            self,
            t("backup_confirm_restore_title"),
            t("backup_confirm_restore_msg", filename=filename),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self._backup_svc.restore_backup(backup_path)
            self._status.setText(t("backup_restored_msg"))
            self.backup_restored.emit()
            QMessageBox.information(
                self,
                t("backup_success_title"),
                t("backup_restored_success", filename=filename),
            )
        except (IOError, FileNotFoundError) as e:
            QMessageBox.critical(
                self,
                t("backup_error_title"),
                t("backup_error_restore", error=str(e)),
            )

    def _on_delete(self) -> None:
        """Delete the selected backup."""
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.warning(
                self,
                t("backup_warning_title"),
                t("backup_select_to_delete"),
            )
            return

        # Get the backup path from the first column's user data
        item = self._table.item(row, 0)
        backup_path = item.data(Qt.ItemDataRole.UserRole)
        filename = self._table.item(row, 2).text()

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            t("backup_confirm_delete_title"),
            t("backup_confirm_delete_msg", filename=filename),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self._backup_svc.delete_backup(backup_path)
            self._status.setText(t("backup_deleted_msg"))
            self._load_backups()
        except (OSError, FileNotFoundError) as e:
            QMessageBox.critical(
                self,
                t("backup_error_title"),
                t("backup_error_delete", error=str(e)),
            )

    def _on_open_folder(self) -> None:
        """Open the backup folder in file explorer."""
        backup_dir = self._backup_svc.get_backup_dir()
        os.makedirs(backup_dir, exist_ok=True)

        # Open folder based on OS
        import sys
        import subprocess
        if sys.platform == "win32":
            os.startfile(backup_dir)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", backup_dir])
        else:
            subprocess.Popen(["xdg-open", backup_dir])

    def reload(self) -> None:
        """Reload the backup list."""
        self._load_backups()
        self._status.setText("")
