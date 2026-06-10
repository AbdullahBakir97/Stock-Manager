"""
app/ui/dialogs/admin/cloud_sync_panel.py — Cloud sync (Turso) admin panel.

Lets the user configure Turso credentials, enable/disable sync, set the sync
interval, test the connection, and initialize the primary or replica role.
"""
from __future__ import annotations

import logging
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFrame, QScrollArea, QSizePolicy, QCheckBox, QComboBox, QListWidget,
    QListWidgetItem, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer

from app.core.config import ShopConfig
from app.core.i18n import t

_log = logging.getLogger(__name__)


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("admin_section_title")
    return lbl


def _card() -> QFrame:
    f = QFrame()
    f.setObjectName("admin_form_card")
    return f


class CloudSyncPanel(QWidget):
    """Admin panel for configuring Turso cloud sync."""

    def __init__(self, sync_service=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._svc = sync_service
        self._build_ui()
        self._load()
        if self._svc is not None:
            self._svc.sync_started.connect(self._on_sync_started)
            self._svc.sync_completed.connect(self._on_sync_done)
            self._svc.sync_failed.connect(self._on_sync_error)

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
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
        title = QLabel("Cloud Sync")
        title.setObjectName("admin_content_title")
        outer.addWidget(title)

        desc = QLabel("Sync your data across multiple PCs in real time using Turso — free, no server required.")
        desc.setObjectName("admin_content_desc")
        desc.setWordWrap(True)
        outer.addWidget(desc)

        # ── Status card ──
        outer.addWidget(_section_label("Status"))
        status_card = _card()
        status_lay = QVBoxLayout(status_card)

        self._status_lbl = QLabel("Loading…")
        self._status_lbl.setObjectName("admin_content_desc")
        status_lay.addWidget(self._status_lbl)

        self._last_sync_lbl = QLabel("Last sync: Never")
        self._last_sync_lbl.setObjectName("admin_content_desc")
        status_lay.addWidget(self._last_sync_lbl)

        outer.addWidget(status_card)

        # ── Credentials card ──
        outer.addWidget(_section_label("Turso Credentials"))
        cred_card = _card()
        cred_lay = QVBoxLayout(cred_card)
        cred_lay.setSpacing(10)

        url_row = QHBoxLayout()
        url_lbl = QLabel("Database URL:")
        url_lbl.setFixedWidth(120)
        url_row.addWidget(url_lbl)
        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("libsql://your-database.turso.io  (or https://...)")
        url_row.addWidget(self._url_edit)
        cred_lay.addLayout(url_row)

        token_row = QHBoxLayout()
        token_lbl = QLabel("Auth Token:")
        token_lbl.setFixedWidth(120)
        token_row.addWidget(token_lbl)
        self._token_edit = QLineEdit()
        self._token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._token_edit.setPlaceholderText("eyJ…")
        token_row.addWidget(self._token_edit)
        cred_lay.addLayout(token_row)

        test_row = QHBoxLayout()
        self._test_btn = QPushButton("Test Connection")
        self._test_btn.setObjectName("action_btn")
        self._test_btn.clicked.connect(self._test_connection)
        test_row.addWidget(self._test_btn)
        self._test_result_lbl = QLabel("")
        self._test_result_lbl.setObjectName("admin_content_desc")
        test_row.addWidget(self._test_result_lbl)
        test_row.addStretch()
        cred_lay.addLayout(test_row)

        outer.addWidget(cred_card)

        # ── Settings card ──
        outer.addWidget(_section_label("Sync Settings"))
        settings_card = _card()
        settings_lay = QVBoxLayout(settings_card)
        settings_lay.setSpacing(10)

        self._enabled_cb = QCheckBox("Enable cloud sync")
        settings_lay.addWidget(self._enabled_cb)

        interval_row = QHBoxLayout()
        interval_lbl = QLabel("Sync every:")
        interval_lbl.setFixedWidth(120)
        interval_row.addWidget(interval_lbl)
        self._interval_combo = QComboBox()
        for label, val in [("1 minute", "1"), ("5 minutes", "5"),
                           ("15 minutes", "15"), ("30 minutes", "30")]:
            self._interval_combo.addItem(label, val)
        interval_row.addWidget(self._interval_combo)
        interval_row.addStretch()
        settings_lay.addLayout(interval_row)

        save_row = QHBoxLayout()
        self._save_btn = QPushButton("Save Settings")
        self._save_btn.setObjectName("primary_btn")
        self._save_btn.clicked.connect(self._save)
        save_row.addWidget(self._save_btn)
        save_row.addStretch()
        settings_lay.addLayout(save_row)

        outer.addWidget(settings_card)

        # ── Actions card ──
        outer.addWidget(_section_label("Actions"))
        actions_card = _card()
        actions_lay = QVBoxLayout(actions_card)
        actions_lay.setSpacing(8)

        sync_row = QHBoxLayout()
        self._sync_now_btn = QPushButton("↻  Sync Now")
        self._sync_now_btn.setObjectName("action_btn")
        self._sync_now_btn.clicked.connect(self._sync_now)
        sync_row.addWidget(self._sync_now_btn)
        sync_row.addStretch()
        actions_lay.addLayout(sync_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("admin_nav_separator")
        actions_lay.addWidget(sep)

        init_lbl = QLabel(
            "Initialize Sync Role  —  Choose which PC has the master data.\n"
            "Run this once per PC when setting up cloud sync for the first time."
        )
        init_lbl.setObjectName("admin_content_desc")
        init_lbl.setWordWrap(True)
        actions_lay.addWidget(init_lbl)

        init_row = QHBoxLayout()
        self._init_primary_btn = QPushButton("⬆  Initialize as Primary (push local data to cloud)")
        self._init_primary_btn.setObjectName("action_btn")
        self._init_primary_btn.clicked.connect(self._init_primary)
        init_row.addWidget(self._init_primary_btn)

        self._init_replica_btn = QPushButton("⬇  Initialize as Replica (pull cloud data to this PC)")
        self._init_replica_btn.setObjectName("action_btn")
        self._init_replica_btn.clicked.connect(self._init_replica)
        init_row.addWidget(self._init_replica_btn)

        init_row.addStretch()
        actions_lay.addLayout(init_row)

        outer.addWidget(actions_card)

        # ── Error log card ──
        outer.addWidget(_section_label("Recent Sync Errors"))
        errors_card = _card()
        errors_lay = QVBoxLayout(errors_card)
        self._error_list = QListWidget()
        self._error_list.setFixedHeight(100)
        self._error_list.setObjectName("admin_table")
        errors_lay.addWidget(self._error_list)
        outer.addWidget(errors_card)

        # ── Help card ──
        outer.addWidget(_section_label("How to Set Up Turso (Free)"))
        help_card = _card()
        help_lay = QVBoxLayout(help_card)
        help_text = QLabel(
            "1.  Go to  turso.tech  and create a free account.\n"
            "2.  Click  Create Database  and choose a name and region.\n"
            "3.  Copy the  Database URL  (starts with  libsql://).\n"
            "4.  Go to  Database → Tokens → Create Token  and copy it.\n"
            "5.  Paste both values above, click  Test Connection, then  Save.\n"
            "6.  On the PC that already has your data, click  Initialize as Primary\n"
            "     — this uploads everything to the cloud database (one time).\n"
            "7.  On every other PC, just enable Cloud Sync with the same URL\n"
            "     and Token — click  Initialize as Replica  to confirm. From then\n"
            "     on every change on either PC is written straight to Turso.\n\n"
            "Free tier:  5 GB storage · 500 M row reads/month · 100 databases."
        )
        help_text.setObjectName("admin_content_desc")
        help_text.setWordWrap(True)
        help_lay.addWidget(help_text)
        outer.addWidget(help_card)

        outer.addStretch()

    # ── Load / Save ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        cfg = ShopConfig.get()
        self._url_edit.setText(cfg.turso_url)
        self._token_edit.setText(cfg.turso_auth_token)
        self._enabled_cb.setChecked(cfg.cloud_sync_enabled == "1")
        idx = self._interval_combo.findData(cfg.sync_interval_minutes)
        if idx >= 0:
            self._interval_combo.setCurrentIndex(idx)
        self._refresh_status()
        self._refresh_errors()

    def _save(self) -> None:
        cfg = ShopConfig.get()
        cfg.turso_url            = self._url_edit.text().strip()
        cfg.turso_auth_token     = self._token_edit.text().strip()
        cfg.cloud_sync_enabled   = "1" if self._enabled_cb.isChecked() else "0"
        cfg.sync_interval_minutes = self._interval_combo.currentData() or "5"
        cfg.save()
        ShopConfig.invalidate()
        if self._svc is not None:
            cfg2 = ShopConfig.get()
            if cfg2.is_cloud_sync_enabled:
                self._svc.reconfigure()
                self._svc.start()
            else:
                self._svc.stop()
        self._refresh_status()
        self._test_result_lbl.setText("✓  Settings saved")
        self._test_result_lbl.setStyleSheet("color: #27AE60;")
        QTimer.singleShot(3000, lambda: self._test_result_lbl.setText(""))

    # ── Actions ───────────────────────────────────────────────────────────────

    def _test_connection(self) -> None:
        url   = self._url_edit.text().strip()
        token = self._token_edit.text().strip()
        if not url:
            self._set_test_result("✕  Please enter a Database URL", error=True)
            return
        self._test_btn.setEnabled(False)
        self._set_test_result("Testing…", error=False)
        try:
            from app.core.database import _TursoHTTPConnection
            conn = _TursoHTTPConnection(url, token)
            conn.execute("SELECT 1")
            self._set_test_result("✓  Connection successful", error=False)
        except Exception as exc:
            self._set_test_result(f"✕  {exc}", error=True)
        finally:
            self._test_btn.setEnabled(True)

    def _sync_now(self) -> None:
        if self._svc is None:
            return
        if not ShopConfig.get().is_cloud_sync_enabled:
            QMessageBox.information(self, "Cloud Sync", "Cloud sync is not enabled. Save your settings first.")
            return
        self._sync_now_btn.setEnabled(False)
        self._svc.sync_now()

    def _init_primary(self) -> None:
        if not ShopConfig.get().is_cloud_sync_enabled:
            QMessageBox.information(self, "Cloud Sync", "Save and enable cloud sync settings first.")
            return
        reply = QMessageBox.question(
            self, "Initialize as Primary",
            "This will UPLOAD all local data to the cloud database.\n\n"
            "Any data already in the cloud database will be REPLACED with "
            "this PC's data.\n\n"
            "Use this on the PC that already holds the shop's data — do "
            "this only ONCE.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._init_primary_btn.setEnabled(False)
        self._set_test_result("Uploading local data to cloud…", error=False)
        try:
            from app.core.database import push_local_to_turso
            counts = push_local_to_turso()
            cfg = ShopConfig.get()
            cfg.sync_role = "primary"
            cfg.save()
            ShopConfig.invalidate()
            total = sum(counts.values())
            self._set_test_result(f"✓  Uploaded {total} rows across {len(counts)} tables", error=False)
            self._refresh_status()
        except Exception as exc:
            self._set_test_result(f"✕  Upload failed: {exc}", error=True)
        finally:
            self._init_primary_btn.setEnabled(True)

    def _init_replica(self) -> None:
        if not ShopConfig.get().is_cloud_sync_enabled:
            QMessageBox.information(self, "Cloud Sync", "Save and enable cloud sync settings first.")
            return
        reply = QMessageBox.question(
            self, "Initialize as Replica",
            "From now on, this PC will read and write directly to the "
            "shared cloud database — its own local data will no longer be "
            "used while Cloud Sync is enabled.\n\n"
            "Use this on every PC EXCEPT the one that ran "
            "'Initialize as Primary'.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._init_replica_btn.setEnabled(False)
        try:
            from app.core.database import _get_turso_connection
            conn = _get_turso_connection()
            if not conn.ping():
                raise RuntimeError("Could not reach the cloud database")
            cfg = ShopConfig.get()
            cfg.sync_role = "replica"
            cfg.save()
            ShopConfig.invalidate()
            self._set_test_result("✓  Connected — this PC now uses the cloud database", error=False)
            self._refresh_status()
        except Exception as exc:
            self._set_test_result(f"✕  {exc}", error=True)
        finally:
            self._init_replica_btn.setEnabled(True)

    # ── Service signal handlers ───────────────────────────────────────────────

    def _on_sync_started(self) -> None:
        self._status_lbl.setText("● Syncing…")
        self._status_lbl.setStyleSheet("color: #F5A623;")

    def _on_sync_done(self, timestamp: str) -> None:
        try:
            t = datetime.fromisoformat(timestamp).strftime("%H:%M:%S")
        except Exception:
            t = timestamp
        self._status_lbl.setText(f"● Cloud sync active")
        self._status_lbl.setStyleSheet("color: #27AE60;")
        self._last_sync_lbl.setText(f"Last sync: {t}")
        self._sync_now_btn.setEnabled(True)
        self._init_primary_btn.setEnabled(True)
        self._init_replica_btn.setEnabled(True)

    def _on_sync_error(self, msg: str) -> None:
        self._status_lbl.setText("● Sync error — check credentials or network")
        self._status_lbl.setStyleSheet("color: #E74C3C;")
        self._sync_now_btn.setEnabled(True)
        self._init_primary_btn.setEnabled(True)
        self._init_replica_btn.setEnabled(True)
        self._refresh_errors()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _refresh_status(self) -> None:
        cfg = ShopConfig.get()
        if cfg.is_cloud_sync_enabled:
            self._status_lbl.setText("● Cloud sync enabled")
            self._status_lbl.setStyleSheet("color: #27AE60;")
        else:
            self._status_lbl.setText("○ Cloud sync disabled")
            self._status_lbl.setStyleSheet("color: #888888;")
        if self._svc and self._svc.last_sync_time:
            t = self._svc.last_sync_time.strftime("%H:%M:%S")
            self._last_sync_lbl.setText(f"Last sync: {t}")
        else:
            self._last_sync_lbl.setText("Last sync: Never")

    def _refresh_errors(self) -> None:
        self._error_list.clear()
        if self._svc:
            for err in self._svc.error_log:
                self._error_list.addItem(QListWidgetItem(err))

    def _set_test_result(self, msg: str, error: bool) -> None:
        self._test_result_lbl.setText(msg)
        color = "#E74C3C" if error else "#27AE60"
        self._test_result_lbl.setStyleSheet(f"color: {color};")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._load()
