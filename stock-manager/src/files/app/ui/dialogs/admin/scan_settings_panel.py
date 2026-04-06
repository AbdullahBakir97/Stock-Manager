"""app/ui/dialogs/admin/scan_settings_panel.py — Configure command barcodes."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QScrollArea, QFrame,
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
        title = QLabel(t("scan_cfg_header") if t("scan_cfg_header") != "scan_cfg_header" else "Quick Scan Configuration")
        title.setObjectName("admin_content_title")
        outer.addWidget(title)

        subtitle = QLabel(t("scan_cfg_hint") if t("scan_cfg_hint") != "scan_cfg_hint" else "Configure command and color barcodes")
        subtitle.setObjectName("admin_content_desc")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        # ── Command Barcodes Card ──
        cmd_card = QFrame()
        cmd_card.setObjectName("admin_form_card")
        cmd_layout = QVBoxLayout(cmd_card)
        cmd_layout.setContentsMargins(16, 12, 16, 12)
        cmd_layout.setSpacing(12)

        cmd_title = QLabel(t("scan_cfg_header") if t("scan_cfg_header") != "scan_cfg_header" else "Command Barcodes")
        cmd_title.setObjectName("admin_form_card_title")
        cmd_layout.addWidget(cmd_title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setContentsMargins(0, 0, 0, 0)

        mono = QFont("JetBrains Mono", 11)

        self._takeout = QLineEdit()
        self._takeout.setFont(mono)
        self._takeout.setMinimumHeight(38)
        form.addRow(t("scan_cfg_takeout") if t("scan_cfg_takeout") != "scan_cfg_takeout" else "Takeout:", self._takeout)

        self._insert = QLineEdit()
        self._insert.setFont(mono)
        self._insert.setMinimumHeight(38)
        form.addRow(t("scan_cfg_insert") if t("scan_cfg_insert") != "scan_cfg_insert" else "Insert:", self._insert)

        self._confirm = QLineEdit()
        self._confirm.setFont(mono)
        self._confirm.setMinimumHeight(38)
        form.addRow(t("scan_cfg_confirm") if t("scan_cfg_confirm") != "scan_cfg_confirm" else "Confirm:", self._confirm)

        cmd_layout.addLayout(form)
        outer.addWidget(cmd_card)

        # ── Color Barcodes Card ──
        clr_card = QFrame()
        clr_card.setObjectName("admin_form_card")
        clr_layout = QVBoxLayout(clr_card)
        clr_layout.setContentsMargins(16, 12, 16, 12)
        clr_layout.setSpacing(12)

        clr_title = QLabel(t("clr_barcodes_hdr") if t("clr_barcodes_hdr") != "clr_barcodes_hdr" else "Color Barcodes")
        clr_title.setObjectName("admin_form_card_title")
        clr_layout.addWidget(clr_title)

        clr_desc = QLabel(t("clr_barcodes_hint") if t("clr_barcodes_hint") != "clr_barcodes_hint" else "Assign barcode strings to colors")
        clr_desc.setObjectName("admin_form_card_desc")
        clr_desc.setWordWrap(True)
        clr_layout.addWidget(clr_desc)

        clr_form = QFormLayout()
        clr_form.setSpacing(8)
        clr_form.setContentsMargins(0, 0, 0, 0)
        self._color_edits: dict[str, QLineEdit] = {}
        default_colors = ["Black", "Blue", "Silver", "Gold", "Green", "Purple", "White"]
        for color in default_colors:
            edit = QLineEdit()
            edit.setFont(mono)
            edit.setMinimumHeight(32)
            clr_form.addRow(f"{color}:", edit)
            self._color_edits[color] = edit
        clr_layout.addLayout(clr_form)
        outer.addWidget(clr_card)

        outer.addStretch()

        # ── Save Button ──
        btn_row = QHBoxLayout()
        self._feedback = QLabel("")
        self._feedback.setObjectName("card_meta_dim")
        self._save_btn = QPushButton(t("shop_btn_save") if t("shop_btn_save") != "shop_btn_save" else "Save")
        self._save_btn.setObjectName("admin_action_btn")
        self._save_btn.clicked.connect(self._save)
        btn_row.addStretch()
        btn_row.addWidget(self._feedback)
        btn_row.addWidget(self._save_btn)
        outer.addLayout(btn_row)

    # ── Load & Save ──

    def _load(self) -> None:
        """Load scan configuration from storage."""
        cfg = ScanConfig.get()
        self._takeout.setText(cfg.cmd_takeout)
        self._insert.setText(cfg.cmd_insert)
        self._confirm.setText(cfg.cmd_confirm)
        for color_name, edit in self._color_edits.items():
            edit.setText(cfg.color_barcodes.get(color_name, f"CLR-{color_name.upper()}"))

    def _save(self) -> None:
        """Save scan configuration."""
        cfg = ScanConfig()
        cfg.cmd_takeout = self._takeout.text().strip() or "CMD-TAKEOUT"
        cfg.cmd_insert = self._insert.text().strip() or "CMD-INSERT"
        cfg.cmd_confirm = self._confirm.text().strip() or "CMD-CONFIRM"
        for color_name, edit in self._color_edits.items():
            cfg.color_barcodes[color_name] = edit.text().strip() or f"CLR-{color_name.upper()}"
        cfg.save()
        self._feedback.setText(t("scan_cfg_saved") if t("scan_cfg_saved") != "scan_cfg_saved" else "Settings saved")
        self.settings_saved.emit()

    def reload(self) -> None:
        """Reload the panel."""
        self._load()
        self._feedback.setText("")
