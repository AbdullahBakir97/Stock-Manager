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
        from PyQt6.QtWidgets import QScrollArea, QWidget as _W
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = _W()
        scroll.setWidget(inner)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        outer = QVBoxLayout(inner)
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

        # Color barcodes section
        clr_hdr = QLabel(t("clr_barcodes_hdr"))
        clr_hdr.setObjectName("detail_section_hdr")
        outer.addWidget(clr_hdr)

        clr_hint = QLabel(t("clr_barcodes_hint"))
        clr_hint.setObjectName("section_caption")
        clr_hint.setWordWrap(True)
        outer.addWidget(clr_hint)

        clr_form = QFormLayout()
        clr_form.setSpacing(8)
        self._color_edits: dict[str, QLineEdit] = {}
        default_colors = ["Black", "Blue", "Silver", "Gold", "Green", "Purple", "White"]
        for color in default_colors:
            edit = QLineEdit()
            edit.setFont(mono)
            edit.setMinimumHeight(32)
            clr_form.addRow(f"{color}:", edit)
            self._color_edits[color] = edit
        outer.addLayout(clr_form)

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
        for color_name, edit in self._color_edits.items():
            edit.setText(cfg.color_barcodes.get(color_name, f"CLR-{color_name.upper()}"))

    def _save(self) -> None:
        cfg = ScanConfig()
        cfg.cmd_takeout = self._takeout.text().strip() or "CMD-TAKEOUT"
        cfg.cmd_insert  = self._insert.text().strip() or "CMD-INSERT"
        cfg.cmd_confirm = self._confirm.text().strip() or "CMD-CONFIRM"
        for color_name, edit in self._color_edits.items():
            cfg.color_barcodes[color_name] = edit.text().strip() or f"CLR-{color_name.upper()}"
        cfg.save()
        self._feedback.setText(t("scan_cfg_saved"))
        self.settings_saved.emit()

    def reload(self) -> None:
        self._load()
        self._feedback.setText("")
