"""app/ui/dialogs/phone_scan_action_dialog.py — popup shown when a phone
unit barcode (IMEI or PHN-code) is scanned from the header search bar.

Mirrors the ScanActionDialog pattern for inventory items, but surfaces
phone-specific actions:
  - Stock OUT  → Mark as Sold   (device leaves the shop)
  - Reserve    → hold for a customer
  - Back to Stock → undo sold/reserved back to in_stock
  - Edit       → open full AddEditPhoneDialog
  - View       → navigate to Phones page

Phone units are individual IMEI-tracked devices, not quantity pools.
"Stock In" = adding a new phone via the Phones page.
"Stock Out" = marking the unit Sold via this dialog.
There is no "Adjust Qty" because each IMEI is always quantity 1.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
    QSizePolicy,
)

from app.core.theme import THEME, _rgba
from app.models.phone_unit import PhoneUnit
from app.ui.dialogs.dialog_base import DialogBase


class PhoneScanActionDialog(DialogBase):
    """Action popup for a barcode that resolved to a phone unit.

    Signals (caller wires these to repo / nav calls):
      request_mark_sold     — mark unit status = 'sold'
      request_mark_reserved — mark unit status = 'reserved'
      request_back_stock    — mark unit status = 'in_stock'
      request_edit          — open AddEditPhoneDialog for this unit
      request_view          — navigate to Phones page
    """

    request_mark_sold     = pyqtSignal()
    request_mark_reserved = pyqtSignal()
    request_back_stock    = pyqtSignal()
    request_edit          = pyqtSignal()
    request_view          = pyqtSignal()

    def __init__(self, phone: PhoneUnit, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._phone = phone
        self.setWindowTitle("Scanned Phone Unit")
        self.setModal(True)
        self.setMinimumWidth(460)
        THEME.apply(self)
        self._build()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        tk = THEME.tokens
        p  = self._phone

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)

        # ── Header: model name + status badge ─────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        name_lbl = QLabel(f"📱  {p.model_brand} {p.model_name}".strip())
        name_f = QFont("Segoe UI", 14, QFont.Weight.Bold)
        name_lbl.setFont(name_f)
        name_lbl.setStyleSheet(f"color:{tk.t1}; background:transparent;")
        name_lbl.setWordWrap(True)
        header_row.addWidget(name_lbl, 1)

        _status_style = {
            "in_stock": ("IN STOCK",   tk.green,  "20"),
            "sold":     ("SOLD",        tk.red,    "20"),
            "reserved": ("RESERVED",    tk.orange, "20"),
        }
        badge_text, badge_fg, alpha = _status_style.get(
            p.status, (p.status.upper(), tk.t2, "20")
        )
        badge = QLabel(badge_text)
        badge.setStyleSheet(
            f"background:{_rgba(badge_fg, alpha)}; color:{badge_fg};"
            f"border:1px solid {_rgba(badge_fg,'40')}; border-radius:6px;"
            f"padding:3px 10px; font-size:10pt; font-weight:700;"
        )
        badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        header_row.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(header_row)

        # ── IMEI / barcode line ────────────────────────────────────────────────
        from app.services.barcode_gen_service import phone_barcode_text
        bc_lbl = QLabel(phone_barcode_text(p))
        bc_lbl.setStyleSheet(
            f"font-family:'JetBrains Mono','Consolas',monospace;"
            f"font-size:10pt; color:{tk.t3}; background:transparent;"
        )
        root.addWidget(bc_lbl)

        # ── Stats grid ────────────────────────────────────────────────────────
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        def _stat_card(label: str, value: str, accent: str) -> QFrame:
            card = QFrame()
            card.setStyleSheet(
                f"QFrame {{ background:{tk.card2}; border:1px solid {tk.border};"
                f"border-radius:8px; }}"
            )
            lay = QVBoxLayout(card)
            lay.setContentsMargins(12, 8, 12, 8)
            lay.setSpacing(2)
            lbl = QLabel(label)
            lbl.setStyleSheet(
                f"font-size:9pt; color:{tk.t4}; background:transparent;"
                f"text-transform:uppercase; letter-spacing:0.5px;"
            )
            val = QLabel(value)
            val.setStyleSheet(
                f"font-size:13pt; font-weight:700; color:{accent}; background:transparent;"
            )
            lay.addWidget(lbl)
            lay.addWidget(val)
            return card

        if p.storage:
            stats_row.addWidget(_stat_card("Storage", p.storage_label, tk.t1))
        stats_row.addWidget(_stat_card("Condition", p.condition_label, tk.t2))

        batt_color = (tk.green  if (p.battery_pct or 0) >= 70 else
                      tk.orange if (p.battery_pct or 0) >= 40 else tk.red)
        stats_row.addWidget(_stat_card("Battery", p.battery_label, batt_color))

        if p.sell_price is not None:
            stats_row.addWidget(_stat_card("Sell Price", f"€{p.sell_price:.2f}", tk.t1))

        root.addLayout(stats_row)

        # ── Primary action buttons (context-sensitive) ────────────────────────
        def _action_btn(label: str, accent: str, slot) -> QPushButton:
            btn = QPushButton(label)
            btn.setMinimumHeight(40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{"
                f"  background:{_rgba(accent,'15')}; color:{accent};"
                f"  border:1px solid {_rgba(accent,'40')};"
                f"  border-radius:6px; font-size:11pt; font-weight:700; padding:6px 14px;"
                f"}}"
                f"QPushButton:hover {{ background:{_rgba(accent,'25')}; border-color:{accent}; }}"
                f"QPushButton:pressed {{ background:{_rgba(accent,'35')}; }}"
            )
            btn.clicked.connect(slot)
            return btn

        actions = QHBoxLayout()
        actions.setSpacing(8)

        if p.status == "in_stock":
            # Primary: Stock Out = Mark Sold; secondary: Reserve
            sold_btn = _action_btn("✓ Stock OUT  (Mark Sold)", tk.red,    self._on_sold)
            res_btn  = _action_btn("⏸ Reserve",                 tk.orange, self._on_reserve)
            actions.addWidget(sold_btn, 2)
            actions.addWidget(res_btn,  1)
            sold_btn.setFocus()
        elif p.status == "reserved":
            actions.addWidget(_action_btn("✓ Stock OUT  (Mark Sold)", tk.red,   self._on_sold), 2)
            actions.addWidget(_action_btn("↩ Back to Stock",           tk.green, self._on_back), 1)
        else:  # sold
            actions.addWidget(_action_btn("↩ Back to Stock", tk.green, self._on_back), 1)

        root.addLayout(actions)

        # ── Secondary row: Edit + View + Cancel ───────────────────────────────
        sec = QHBoxLayout()
        sec.setSpacing(8)

        def _sec_btn(label: str, color: str, slot) -> QPushButton:
            btn = QPushButton(label)
            btn.setMinimumHeight(34)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ background:{_rgba(color,'12')}; color:{color};"
                f"  border:1px solid {_rgba(color,'30')}; border-radius:6px;"
                f"  font-weight:600; padding:5px 12px; }}"
                f"QPushButton:hover {{ background:{_rgba(color,'20')}; }}"
            )
            btn.clicked.connect(slot)
            return btn

        sec.addWidget(_sec_btn("✎ Edit",        tk.blue, self._on_edit))
        sec.addWidget(_sec_btn("↗ View in Phones", tk.t2,  self._on_view))
        sec.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(34)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; color:{tk.t2};"
            f"  border:1px solid {tk.border}; border-radius:6px; padding:5px 14px; }}"
            f"QPushButton:hover {{ background:{tk.card2}; color:{tk.t1}; }}"
        )
        cancel_btn.clicked.connect(self.reject)
        sec.addWidget(cancel_btn)
        root.addLayout(sec)

        # ── Footer note ───────────────────────────────────────────────────────
        note = QLabel(
            "ℹ  Each phone unit is 1 unique device (IMEI-tracked). "
            "Stock OUT = Mark Sold.  Add new units via the Phones page."
        )
        note.setStyleSheet(f"color:{tk.t4}; font-size:9pt; background:transparent;")
        note.setWordWrap(True)
        root.addWidget(note)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_sold(self) -> None:
        self.request_mark_sold.emit()
        self.accept()

    def _on_reserve(self) -> None:
        self.request_mark_reserved.emit()
        self.accept()

    def _on_back(self) -> None:
        self.request_back_stock.emit()
        self.accept()

    def _on_edit(self) -> None:
        self.request_edit.emit()
        self.accept()

    def _on_view(self) -> None:
        self.request_view.emit()
        self.accept()
