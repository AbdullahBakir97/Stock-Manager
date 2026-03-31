"""app/ui/dialogs/admin/scan_settings_panel.py — Configure command barcodes."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import pyqtSignal

from app.core.scan_config import ScanConfig
from app.core.i18n import t


class ScanSettingsPanel(QWidget):
    """Admin panel for configuring Quick Scan command barcodes."""

    settings_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)

        # Header
        hdr = QLabel(t("scan_cfg_header"))
        hdr.setObjectName("dlg_header")
        outer.addWidget(hdr)

        hint = QLabel(t("scan_cfg_hint"))
        hint.setObjectName("section_caption")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        # Form
        form = QFormLayout()
        form.setSpacing(12)
        form.setContentsMargins(0, 0, 0, 0)

        mono = QFont("JetBrains Mono", 11)

        self._takeout = QLineEdit()
        self._takeout.setFont(mono)
        self._takeout.setMinimumHeight(38)
        form.addRow(t("scan_cfg_takeout"), self._takeout)

        self._insert = QLineEdit()
        self._insert.setFont(mono)
        self._insert.setMinimumHeight(38)
        form.addRow(t("scan_cfg_insert"), self._insert)

        self._confirm = QLineEdit()
        self._confirm.setFont(mono)
        self._confirm.setMinimumHeight(38)
        form.addRow(t("scan_cfg_confirm"), self._confirm)

        outer.addLayout(form)
        outer.addStretch()

        # Save
        btn_row = QHBoxLayout()
        self._feedback = QLabel("")
        self._feedback.setObjectName("card_meta_dim")
        self._save_btn = QPushButton(t("shop_btn_save"))
        self._save_btn.setObjectName("btn_primary")
        self._save_btn.clicked.connect(self._save)
        btn_row.addStretch()
        btn_row.addWidget(self._feedback)
        btn_row.addWidget(self._save_btn)
        outer.addLayout(btn_row)

    def _load(self) -> None:
        cfg = ScanConfig.get()
        self._takeout.setText(cfg.cmd_takeout)
        self._insert.setText(cfg.cmd_insert)
        self._confirm.setText(cfg.cmd_confirm)

    def _save(self) -> None:
        cfg = ScanConfig()
        cfg.cmd_takeout = self._takeout.text().strip() or "CMD-TAKEOUT"
        cfg.cmd_insert  = self._insert.text().strip() or "CMD-INSERT"
        cfg.cmd_confirm = self._confirm.text().strip() or "CMD-CONFIRM"
        cfg.save()
        self._feedback.setText(t("scan_cfg_saved"))
        self.settings_saved.emit()

    def reload(self) -> None:
        self._load()
        self._feedback.setText("")
