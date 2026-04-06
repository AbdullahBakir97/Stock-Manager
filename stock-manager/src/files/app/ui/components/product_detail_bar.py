"""
app/ui/components/product_detail_bar.py — Compact horizontal product detail bar.
Replaces the right-side detail panel to give the table more room.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QScrollArea,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor

from app.core.config import ShopConfig
from app.core.theme import THEME, _rgba
from app.core.i18n import t
from app.core import colors as clr
from app.core.icon_utils import get_button_icon
from app.models.item import InventoryItem
from app.ui.helpers import _sc, _sl
from app.ui.components.product_detail import _StockSparkline


class ProductDetailBar(QFrame):
    """Compact horizontal bar showing selected product info + quick actions."""

    request_in = pyqtSignal()
    request_out = pyqtSignal()
    request_adj = pyqtSignal()
    request_edit = pyqtSignal()
    request_del = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._item: InventoryItem | None = None
        self.setObjectName("detail_bar")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(0)  # Hidden initially
        self._build()

    def _build(self):
        tk = THEME.tokens

        self.setStyleSheet(
            f"QFrame#detail_bar {{"
            f"  background:{tk.card}; border:1px solid {tk.border};"
            f"  border-radius:10px;"
            f"}}"
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 8, 14, 8)
        root.setSpacing(16)

        # ── Identity section ──
        id_col = QVBoxLayout()
        id_col.setSpacing(1)

        # Row 1: Name
        self._name_lbl = QLabel()
        self._name_lbl.setStyleSheet(
            f"font-size:13px; font-weight:700; color:{tk.t1};"
        )
        id_col.addWidget(self._name_lbl)

        # Row 2: BC: xxxx
        self._bc_lbl = QLabel()
        self._bc_lbl.setStyleSheet(
            f"font-size:9px; font-family:'JetBrains Mono',monospace; color:{tk.t3};"
        )
        id_col.addWidget(self._bc_lbl)

        # Row 3: [color dot] color · date
        meta_row = QHBoxLayout()
        meta_row.setSpacing(4)
        meta_row.setContentsMargins(0, 0, 0, 0)

        self._color_dot = QLabel()
        self._color_dot.setFixedSize(10, 10)
        self._color_dot.hide()
        meta_row.addWidget(self._color_dot)

        self._color_name = QLabel()
        self._color_name.setStyleSheet(f"font-size:9px; color:{tk.t2}; font-weight:600;")
        self._color_name.hide()
        meta_row.addWidget(self._color_name)

        self._meta_lbl = QLabel()
        self._meta_lbl.setStyleSheet(f"font-size:9px; color:{tk.t3};")
        meta_row.addWidget(self._meta_lbl)
        meta_row.addStretch()

        id_col.addLayout(meta_row)
        root.addLayout(id_col)

        # ── Separator ──
        root.addWidget(self._sep())

        # ── Stock section ──
        stock_col = QVBoxLayout()
        stock_col.setSpacing(0)
        stock_col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._stock_val = QLabel("—")
        self._stock_val.setStyleSheet(
            f"font-size:18px; font-weight:800; color:{tk.green};"
        )
        self._stock_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stock_col.addWidget(self._stock_val)

        self._stock_badge = QLabel()
        self._stock_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._stock_badge.setFixedHeight(18)
        stock_col.addWidget(self._stock_badge)
        root.addLayout(stock_col)

        # ── Separator ──
        root.addWidget(self._sep())

        # ── Price section ──
        price_col = QVBoxLayout()
        price_col.setSpacing(1)
        price_col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        price_hdr = QLabel(t("col_price"))
        price_hdr.setStyleSheet(f"font-size:9px; color:{tk.t3}; text-transform:uppercase;")
        price_hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        price_col.addWidget(price_hdr)

        self._price_val = QLabel("—")
        self._price_val.setStyleSheet(f"font-size:14px; font-weight:700; color:{tk.t1};")
        self._price_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        price_col.addWidget(self._price_val)
        root.addLayout(price_col)

        # ── Separator ──
        root.addWidget(self._sep())

        # ── Min / Diff section ──
        diff_col = QVBoxLayout()
        diff_col.setSpacing(1)
        diff_col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        diff_hdr = QLabel(t("col_min") + " / " + t("col_best_bung"))
        diff_hdr.setStyleSheet(f"font-size:9px; color:{tk.t3};")
        diff_hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        diff_col.addWidget(diff_hdr)

        self._diff_val = QLabel("—")
        self._diff_val.setStyleSheet(f"font-size:12px; font-weight:600; color:{tk.t2};")
        self._diff_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        diff_col.addWidget(self._diff_val)
        root.addLayout(diff_col)

        # ── Separator ──
        root.addWidget(self._sep())

        # ── Trend sparkline ──
        trend_col = QVBoxLayout()
        trend_col.setSpacing(1)
        trend_col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        trend_hdr = QLabel(t("detail_stock_trend"))
        trend_hdr.setStyleSheet(f"font-size:9px; color:{tk.t3};")
        trend_hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        trend_col.addWidget(trend_hdr)

        self._sparkline = _StockSparkline()
        self._sparkline.setFixedSize(110, 38)
        trend_col.addWidget(self._sparkline, 0, Qt.AlignmentFlag.AlignCenter)
        root.addLayout(trend_col)

        root.addStretch()

        # ── Quick action buttons ──
        _btn_h = 26
        _btn_font = "font-size:10px;"
        btn_ss_in = (
            f"background:{_rgba(tk.green, '15')}; color:{tk.green};"
            f"border:1px solid {_rgba(tk.green, '30')}; border-radius:5px;"
            f"font-weight:700; {_btn_font} padding:2px 6px;"
        )
        btn_ss_out = (
            f"background:{_rgba(tk.red, '15')}; color:{tk.red};"
            f"border:1px solid {_rgba(tk.red, '30')}; border-radius:5px;"
            f"font-weight:700; {_btn_font} padding:2px 6px;"
        )
        btn_ss_adj = (
            f"background:{_rgba(tk.orange, '15')}; color:{tk.orange};"
            f"border:1px solid {_rgba(tk.orange, '30')}; border-radius:5px;"
            f"font-weight:600; {_btn_font} padding:2px 6px;"
        )
        btn_ss_edit = (
            f"background:{_rgba(tk.blue, '15')}; color:{tk.blue};"
            f"border:1px solid {_rgba(tk.blue, '30')}; border-radius:5px;"
            f"font-weight:600; {_btn_font} padding:2px 6px;"
        )
        btn_ss_del = (
            f"background:{_rgba(tk.red, '10')}; color:{tk.red};"
            f"border:1px solid {_rgba(tk.red, '20')}; border-radius:5px;"
            f"font-weight:600; {_btn_font} padding:2px 4px;"
        )

        self._btn_in = QPushButton(t("btn_stock_in"))
        self._btn_in.setFixedHeight(_btn_h)
        self._btn_in.setMaximumWidth(70)
        self._btn_in.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_in.setStyleSheet(btn_ss_in)
        self._btn_in.clicked.connect(self.request_in)
        root.addWidget(self._btn_in)

        self._btn_out = QPushButton(t("btn_stock_out"))
        self._btn_out.setFixedHeight(_btn_h)
        self._btn_out.setMaximumWidth(70)
        self._btn_out.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_out.setStyleSheet(btn_ss_out)
        self._btn_out.clicked.connect(self.request_out)
        root.addWidget(self._btn_out)

        self._btn_adj = QPushButton(t("btn_adjust"))
        self._btn_adj.setFixedHeight(_btn_h)
        self._btn_adj.setMaximumWidth(60)
        self._btn_adj.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_adj.setStyleSheet(btn_ss_adj)
        self._btn_adj.clicked.connect(self.request_adj)
        root.addWidget(self._btn_adj)

        self._btn_edit = QPushButton(t("btn_edit"))
        self._btn_edit.setFixedHeight(_btn_h)
        self._btn_edit.setMaximumWidth(50)
        self._btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_edit.setStyleSheet(btn_ss_edit)
        self._btn_edit.setIcon(get_button_icon("edit"))
        self._btn_edit.setIconSize(QSize(14, 14))
        self._btn_edit.clicked.connect(self.request_edit)
        root.addWidget(self._btn_edit)

        self._btn_del = QPushButton()
        self._btn_del.setFixedSize(26, _btn_h)
        self._btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_del.setStyleSheet(btn_ss_del)
        self._btn_del.setIcon(get_button_icon("delete"))
        self._btn_del.setIconSize(QSize(14, 14))
        self._btn_del.setToolTip(t("ctx_delete"))
        self._btn_del.clicked.connect(self.request_del)
        root.addWidget(self._btn_del)

    def _sep(self) -> QFrame:
        """Create a thin vertical separator."""
        tk = THEME.tokens
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background:{tk.border}; border:none;")
        return sep

    # ── Public API ──────────────────────────────────────────────────────────

    # ── Sparkline helpers ────────────────────────────────────────────────────

    def _load_sparkline(self, item_id: int) -> None:
        """Populate the sparkline from the last 20 stock transactions."""
        try:
            from app.repositories.transaction_repo import TransactionRepository
            txns = TransactionRepository().get_transactions(item_id=item_id, limit=20)
            if not txns:
                self._sparkline.set_data([])
                return
            txns.reverse()                          # oldest → newest
            self._sparkline.set_data([t.stock_after for t in txns])
        except Exception:
            self._sparkline.set_data([])

    def set_product(self, item: InventoryItem | None):
        """Update the bar with selected product info, or hide if None."""
        self._item = item
        if not item:
            self._sparkline.set_data([])
            self.setFixedHeight(0)
            return

        self.setFixedHeight(64)
        tk = THEME.tokens
        cfg = ShopConfig.get()

        # Name
        self._name_lbl.setText(item.display_name)

        # Barcode — inline in meta row between name and color
        self._bc_lbl.setText(f"BC: {item.barcode}" if item.barcode else "")

        # Color — show product color, or part type color for matrix items
        color_text = item.color or ""
        hex_color = ""
        if color_text and color_text != "—":
            hex_color = clr.hex_for(color_text)
        elif item.part_type_color:
            hex_color = item.part_type_color
            color_text = item.part_type_name or ""

        if hex_color:
            brd = "rgba(102,102,102,153)" if clr.is_light(hex_color) else "transparent"
            self._color_dot.setStyleSheet(
                f"background:{hex_color}; border-radius:5px; border:1px solid {brd};"
            )
            self._color_dot.show()
            self._color_name.setText(color_text)
            self._color_name.show()
        else:
            self._color_dot.hide()
            self._color_name.hide()

        # Meta — date and SKU only (barcode moved above)
        meta_parts = []
        if item.sku:
            meta_parts.append(f"SKU: {item.sku}")
        if item.updated_at:
            meta_parts.append(str(item.updated_at)[:10])
        self._meta_lbl.setText("  ·  ".join(meta_parts) if meta_parts else "")

        # Stock
        stk = item.stock
        thr = item.min_stock
        sc = _sc(stk, thr)
        sl_str = _sl(stk, thr)
        self._stock_val.setText(str(stk))
        self._stock_val.setStyleSheet(
            f"font-size:18px; font-weight:800; color:{sc.name()};"
        )

        badge_map = {
            "OK": (tk.green, _rgba(tk.green, "28")),
            "LOW": (tk.yellow, _rgba(tk.yellow, "30")),
            "CRITICAL": (tk.orange, _rgba(tk.orange, "28")),
            "OUT": (tk.red, _rgba(tk.red, "28")),
        }
        fg, bg = badge_map.get(sl_str, (tk.t3, tk.border))
        badge_labels = {
            "OK": t("badge_ok"), "LOW": t("badge_low"),
            "CRITICAL": t("badge_critical"), "OUT": t("badge_out"),
        }
        self._stock_badge.setText(badge_labels.get(sl_str, sl_str))
        self._stock_badge.setStyleSheet(
            f"color:{fg}; background:{bg}; border-radius:4px;"
            "font-weight:700; font-size:9px; padding:1px 6px;"
        )

        # Price
        price_display = cfg.format_currency(item.sell_price) if item.sell_price else "—"
        self._price_val.setText(price_display)

        # Min / Diff
        diff = stk - thr
        diff_str = f"{thr} / Δ{diff:+d}" if thr > 0 else f"{thr} / —"
        self._diff_val.setText(diff_str)

        # Trend sparkline (async-safe: uses its own DB connection)
        self._load_sparkline(item.id)

        # All buttons always enabled — main_window handles product vs matrix logic
        self._btn_edit.setEnabled(True)
        self._btn_del.setEnabled(True)

    def retranslate(self):
        self._btn_in.setText(t("btn_stock_in"))
        self._btn_out.setText(t("btn_stock_out"))
        self._btn_adj.setText(t("btn_adjust"))
        self._btn_edit.setText(t("btn_edit"))
        if self._item:
            self.set_product(self._item)
