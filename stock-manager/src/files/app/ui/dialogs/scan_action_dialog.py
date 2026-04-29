"""app/ui/dialogs/scan_action_dialog.py — popup shown when a known
barcode is scanned from the header search bar.

Replaces the legacy "scan -> navigate to inventory + select row" flow
for known items: the user wanted to act on the scanned item directly
without leaving the current page. The popup surfaces the same actions
that the inventory detail bar exposes (Stock In / Stock Out / Adjust /
Edit) so a shop assistant can complete a transaction in one keystroke.

Architecture: the dialog itself is a pure view — it emits
``request_in`` / ``request_out`` / ``request_adjust`` / ``request_edit``
signals that ``MainWindow._barcode`` wires up to the existing
``ctx_stock_op`` controller. No new business logic lives here, so the
dialog can be retired or replaced without touching the stock-ops flow.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
    QSizePolicy,
)

from app.core.config import ShopConfig
from app.core.i18n import t
from app.core.theme import THEME, _rgba
from app.models.item import InventoryItem
from app.ui.dialogs.dialog_base import DialogBase


class ScanActionDialog(DialogBase):
    """Action popup for a barcode that resolved to an inventory item.

    Five user-driven exits — pick one and the dialog closes:
      - Stock In  → ``request_in``     emits, dialog accepts
      - Stock Out → ``request_out``    emits, dialog accepts
      - Adjust    → ``request_adjust`` emits, dialog accepts (exact value)
      - Edit      → ``request_edit``   emits, dialog accepts
      - Cancel / Esc / X → dialog rejects, no signal

    The caller (``MainWindow._barcode``) routes each signal to the
    existing ``ctx_stock_op`` controller so this popup shares the
    underlying op flow with the inventory page's right-side detail bar
    and the matrix tab's right-click context menu.
    """

    request_in = pyqtSignal()
    request_out = pyqtSignal()
    request_adjust = pyqtSignal()
    request_edit = pyqtSignal()

    def __init__(self, item: InventoryItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._item = item
        self.setWindowTitle(t("scan_dlg_title")
                            if t("scan_dlg_title") != "scan_dlg_title"
                            else "Scanned Item")
        self.setModal(True)
        self.setMinimumWidth(440)
        # Use the shared theme stylesheet so this popup matches the
        # rest of the app and refreshes on theme toggle automatically.
        THEME.apply(self)
        self._build()

    # ── UI ────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        tk = THEME.tokens
        cfg = ShopConfig.get()
        item = self._item

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)

        # ── Header: item identity ──
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        # Item name (large)
        name_lbl = QLabel(item.display_name)
        name_f = QFont("Segoe UI", 14, QFont.Weight.Bold)
        name_lbl.setFont(name_f)
        name_lbl.setStyleSheet(f"color:{tk.t1}; background:transparent;")
        name_lbl.setWordWrap(True)
        header_row.addWidget(name_lbl, 1)

        # Status badge — big, color-coded so a shop assistant can read
        # the stock state from across the room.
        if item.stock <= 0:
            badge_text = t("badge_out") if t("badge_out") != "badge_out" else "OUT OF STOCK"
            badge_fg, badge_bg = tk.red, _rgba(tk.red, "20")
        elif item.min_stock > 0 and item.stock <= item.min_stock:
            badge_text = t("badge_low") if t("badge_low") != "badge_low" else "LOW STOCK"
            badge_fg, badge_bg = tk.orange, _rgba(tk.orange, "20")
        else:
            badge_text = t("badge_ok") if t("badge_ok") != "badge_ok" else "IN STOCK"
            badge_fg, badge_bg = tk.green, _rgba(tk.green, "20")
        badge = QLabel(badge_text)
        badge.setStyleSheet(
            f"background:{badge_bg}; color:{badge_fg};"
            f"border:1px solid {_rgba(badge_fg, '40')}; border-radius:6px;"
            f"padding:3px 10px; font-size:10pt; font-weight:700;"
        )
        badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        header_row.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(header_row)

        # ── Barcode (mono) ──
        bc_lbl = QLabel(item.barcode or "")
        bc_lbl.setStyleSheet(
            f"font-family:'JetBrains Mono', 'Consolas', monospace;"
            f"font-size:10pt; color:{tk.t3}; background:transparent;"
        )
        root.addWidget(bc_lbl)

        # ── Stats grid: stock / min / price ──
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
            l_lbl = QLabel(label)
            l_lbl.setStyleSheet(
                f"font-size:9pt; color:{tk.t4}; background:transparent;"
                f"text-transform:uppercase; letter-spacing:0.5px;"
            )
            v_lbl = QLabel(value)
            v_lbl.setStyleSheet(
                f"font-size:14pt; font-weight:700; color:{accent}; background:transparent;"
            )
            lay.addWidget(l_lbl)
            lay.addWidget(v_lbl)
            return card

        stock_color = tk.green if item.stock > item.min_stock else (
            tk.orange if item.stock > 0 else tk.red
        )
        stats_row.addWidget(_stat_card(
            t("col_stock") if t("col_stock") != "col_stock" else "Stock",
            str(item.stock), stock_color,
        ))
        stats_row.addWidget(_stat_card(
            t("col_min") if t("col_min") != "col_min" else "Min",
            str(item.min_stock), tk.t2,
        ))
        if item.sell_price is not None:
            try:
                price_text = cfg.format_currency(f"{float(item.sell_price):,.2f}")
            except Exception:
                price_text = f"{float(item.sell_price):,.2f}"
            stats_row.addWidget(_stat_card(
                t("col_price") if t("col_price") != "col_price" else "Price",
                price_text, tk.t1,
            ))
        root.addLayout(stats_row)

        # ── Action buttons row ──
        # Three primary stock ops: In / Out / Adjust. Each closes the
        # dialog with the matching signal — caller routes to ctx_stock_op.
        actions = QHBoxLayout()
        actions.setSpacing(8)

        def _action_btn(label: str, accent_hex: str, slot):
            btn = QPushButton(label)
            btn.setMinimumHeight(40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{"
                f"  background:{_rgba(accent_hex, '15')}; color:{accent_hex};"
                f"  border:1px solid {_rgba(accent_hex, '40')};"
                f"  border-radius:6px; font-size:11pt; font-weight:700;"
                f"  padding:6px 14px;"
                f"}}"
                f"QPushButton:hover {{"
                f"  background:{_rgba(accent_hex, '25')};"
                f"  border-color:{accent_hex};"
                f"}}"
                f"QPushButton:pressed {{"
                f"  background:{_rgba(accent_hex, '35')};"
                f"}}"
            )
            btn.clicked.connect(slot)
            return btn

        actions.addWidget(_action_btn(
            t("btn_stock_in") if t("btn_stock_in") != "btn_stock_in" else "Stock In",
            tk.green, self._on_in,
        ), 1)
        actions.addWidget(_action_btn(
            t("btn_stock_out") if t("btn_stock_out") != "btn_stock_out" else "Stock Out",
            tk.red, self._on_out,
        ), 1)
        actions.addWidget(_action_btn(
            t("btn_adjust") if t("btn_adjust") != "btn_adjust" else "Adjust",
            tk.orange, self._on_adjust,
        ), 1)
        root.addLayout(actions)

        # ── Secondary row: Edit + Cancel ──
        sec_row = QHBoxLayout()
        sec_row.setSpacing(8)

        edit_btn = QPushButton(
            t("btn_edit") if t("btn_edit") != "btn_edit" else "Edit"
        )
        edit_btn.setObjectName("btn_secondary")
        edit_btn.setMinimumHeight(34)
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background:{_rgba(tk.blue, '12')}; color:{tk.blue};"
            f"  border:1px solid {_rgba(tk.blue, '30')};"
            f"  border-radius:6px; font-weight:600; padding:5px 12px;"
            f"}}"
            f"QPushButton:hover {{ background:{_rgba(tk.blue, '20')}; }}"
        )
        edit_btn.clicked.connect(self._on_edit)
        sec_row.addWidget(edit_btn)

        sec_row.addStretch()

        cancel_btn = QPushButton(
            t("op_cancel") if t("op_cancel") != "op_cancel" else "Cancel"
        )
        cancel_btn.setMinimumHeight(34)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background:transparent; color:{tk.t2};"
            f"  border:1px solid {tk.border}; border-radius:6px;"
            f"  padding:5px 14px;"
            f"}}"
            f"QPushButton:hover {{ background:{tk.card2}; color:{tk.t1}; }}"
        )
        cancel_btn.clicked.connect(self.reject)
        sec_row.addWidget(cancel_btn)

        root.addLayout(sec_row)

        # Default focus on Stock In — most common op when scanning
        # incoming inventory from a delivery.
        self._stock_in_btn = actions.itemAt(0).widget()
        if self._stock_in_btn:
            self._stock_in_btn.setFocus()

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_in(self) -> None:
        self.request_in.emit()
        self.accept()

    def _on_out(self) -> None:
        self.request_out.emit()
        self.accept()

    def _on_adjust(self) -> None:
        self.request_adjust.emit()
        self.accept()

    def _on_edit(self) -> None:
        self.request_edit.emit()
        self.accept()
