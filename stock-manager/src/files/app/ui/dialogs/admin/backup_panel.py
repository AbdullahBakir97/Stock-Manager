"""app/ui/dialogs/admin/backup_panel.py — Database backup and restore admin panel."""
from __future__ import annotations

import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QMessageBox, QFrame, QScrollArea, QSizePolicy, QHeaderView,
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
        title = QLabel(t("backup_title") if t("backup_title") != "backup_title" else "Backup & Restore")
        title.setObjectName("admin_content_title")
        outer.addWidget(title)

        subtitle = QLabel(
            t("backup_desc") if t("backup_desc") != "backup_desc" else "Protect your data with automatic backups"
        )
        subtitle.setObjectName("admin_content_desc")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        # ── KPI Row ──
        kpi_lay = QHBoxLayout()
        kpi_lay.setContentsMargins(0, 0, 0, 0)
        kpi_lay.setSpacing(12)

        # Total Backups KPI
        self._kpi_count = self._create_kpi("0")
        kpi_lay.addWidget(self._kpi_count)

        # Latest Backup KPI
        self._kpi_latest = self._create_kpi("—")
        kpi_lay.addWidget(self._kpi_latest)

        # Storage Used KPI
        self._kpi_storage = self._create_kpi("0 MB")
        kpi_lay.addWidget(self._kpi_storage)

        kpi_lay.addStretch()
        outer.addLayout(kpi_lay)

        # ── Create Backup Card ──
        create_card = QFrame()
        create_card.setObjectName("admin_form_card")
        create_lay = QVBoxLayout(create_card)
        create_lay.setContentsMargins(20, 16, 20, 16)
        create_lay.setSpacing(12)

        create_title = QLabel(
            t("backup_create_btn") if t("backup_create_btn") != "backup_create_btn" else "Create Backup"
        )
        create_title.setObjectName("admin_form_card_title")
        create_lay.addWidget(create_title)

        create_desc = QLabel(
            t("backup_create_desc") if t("backup_create_desc") != "backup_create_desc"
            else "Create a snapshot of your database to protect against data loss"
        )
        create_desc.setObjectName("admin_form_card_desc")
        create_desc.setWordWrap(True)
        create_lay.addWidget(create_desc)

        create_btn_row = QHBoxLayout()
        create_btn_row.setContentsMargins(0, 0, 0, 0)
        self._create_btn = QPushButton(
            t("backup_create_btn") if t("backup_create_btn") != "backup_create_btn" else "Create Backup"
        )
        self._create_btn.setObjectName("btn_primary")
        self._create_btn.setMinimumHeight(40)
        self._create_btn.clicked.connect(self._on_create_backup)
        create_btn_row.addWidget(self._create_btn)
        create_btn_row.addStretch()
        create_lay.addLayout(create_btn_row)

        outer.addWidget(create_card)

        # ── Backup History Card ──
        history_card = QFrame()
        history_card.setObjectName("admin_form_card")
        history_lay = QVBoxLayout(history_card)
        history_lay.setContentsMargins(20, 16, 20, 16)
        history_lay.setSpacing(12)

        history_title = QLabel(
            t("backup_list_label") if t("backup_list_label") != "backup_list_label" else "Backup History"
        )
        history_title.setObjectName("admin_form_card_title")
        history_lay.addWidget(history_title)

        history_desc = QLabel(
            t("backup_history_desc") if t("backup_history_desc") != "backup_history_desc"
            else "Recent backups with file size and creation date"
        )
        history_desc.setObjectName("admin_form_card_desc")
        history_desc.setWordWrap(True)
        history_lay.addWidget(history_desc)

        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels([
            t("backup_col_date") if t("backup_col_date") != "backup_col_date" else "Date",
            t("backup_col_size") if t("backup_col_size") != "backup_col_size" else "Size",
            t("backup_col_file") if t("backup_col_file") != "backup_col_file" else "Filename",
        ])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(0, 150)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(1, 80)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setMinimumHeight(200)
        history_lay.addWidget(self._table)

        outer.addWidget(history_card)

        # ── Actions Card ──
        actions_card = QFrame()
        actions_card.setObjectName("admin_form_card")
        actions_lay = QVBoxLayout(actions_card)
        actions_lay.setContentsMargins(20, 16, 20, 16)
        actions_lay.setSpacing(12)

        actions_title = QLabel(
            t("backup_actions_title") if t("backup_actions_title") != "backup_actions_title" else "Actions"
        )
        actions_title.setObjectName("admin_form_card_title")
        actions_lay.addWidget(actions_title)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(12)

        self._restore_btn = QPushButton(
            t("backup_restore_btn") if t("backup_restore_btn") != "backup_restore_btn" else "Restore"
        )
        self._restore_btn.setObjectName("btn_primary")
        self._restore_btn.setMinimumWidth(140)
        self._restore_btn.clicked.connect(self._on_restore)
        btn_row.addWidget(self._restore_btn)

        self._delete_btn = QPushButton(
            t("backup_delete_btn") if t("backup_delete_btn") != "backup_delete_btn" else "Delete"
        )
        self._delete_btn.setObjectName("admin_del_btn")
        self._delete_btn.setMinimumWidth(130)
        self._delete_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(self._delete_btn)

        self._folder_btn = QPushButton(
            t("backup_open_folder_btn") if t("backup_open_folder_btn") != "backup_open_folder_btn" else "Open Folder"
        )
        self._folder_btn.setObjectName("btn_ghost")
        self._folder_btn.setMinimumWidth(120)
        self._folder_btn.clicked.connect(self._on_open_folder)
        btn_row.addWidget(self._folder_btn)

        btn_row.addStretch()
        actions_lay.addLayout(btn_row)

        outer.addWidget(actions_card)

        # ── Status Label ──
        self._status = QLabel("")
        self._status.setObjectName("admin_kpi_sub")
        self._status.setWordWrap(True)
        outer.addWidget(self._status)

        outer.addStretch()

    def _create_kpi(self, value: str) -> QFrame:
        """Create a KPI card widget."""
        card = QFrame()
        card.setObjectName("admin_kpi")
        card.setMinimumHeight(80)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(4)

        val_lbl = QLabel(value)
        val_lbl.setObjectName("admin_kpi_value")
        lay.addWidget(val_lbl)

        lay.addStretch()
        return card

    def _load_backups(self) -> None:
        """Load and display all backups in the table."""
        self._table.setRowCount(0)
        backups = self._backup_svc.list_backups()

        # Update KPI cards
        total_count = len(backups)
        total_size = sum(b["size"] for b in backups) / (1024 * 1024)
        latest_date = "—"

        if backups:
            latest_mtime = backups[0]["date"]
            latest_dt = datetime.fromtimestamp(latest_mtime)
            latest_date = latest_dt.strftime("%Y-%m-%d %H:%M")

        self._update_kpi_value(self._kpi_count, str(total_count))
        self._update_kpi_value(self._kpi_latest, latest_date)
        self._update_kpi_value(self._kpi_storage, f"{total_size:.1f} MB")

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

    def _update_kpi_value(self, card: QFrame, value: str) -> None:
        """Update a KPI card's value label."""
        for i in range(card.layout().count()):
            widget = card.layout().itemAt(i).widget()
            if widget and widget.objectName() == "admin_kpi_value":
                widget.setText(value)
                break

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
