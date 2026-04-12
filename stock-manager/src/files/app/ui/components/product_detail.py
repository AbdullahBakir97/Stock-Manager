"""
app/ui/components/product_detail.py — Product detail side panel.
"""
from __future__ import annotations

import io

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont, QPainter, QPen, QColor

from app.core.config import ShopConfig
from app.core.theme import THEME, _rgba
from app.core.i18n import t
from app.core import colors as clr
from app.core.icon_utils import get_button_icon
from app.models.item import InventoryItem
from app.ui.components.mini_txn_list import MiniTxnList
from app.ui.helpers import _sc, _sl


# ── Sparkline widget ────────────────────────────────────────────────────────

class _StockSparkline(QFrame):
    """Tiny line chart showing recent stock transaction history."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("detail_sparkline")
        self.setFixedHeight(52)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._points: list[int] = []

    def set_data(self, points: list[int]) -> None:
        self._points = points
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if len(self._points) < 2:
            return
        tk = THEME.tokens
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width() - 16   # padding
        h = self.height() - 16
        x0, y0 = 8, 8

        mn = min(self._points)
        mx = max(self._points)
        rng = mx - mn or 1

        # Draw line
        pen = QPen(QColor(tk.green if tk.grad_top in ("#0A0A0A", "#FFFFFF") else tk.blue), 2)
        painter.setPen(pen)
        pts = []
        for i, v in enumerate(self._points):
            px = x0 + (i / (len(self._points) - 1)) * w
            py = y0 + h - ((v - mn) / rng) * h
            pts.append((px, py))

        for i in range(len(pts) - 1):
            painter.drawLine(int(pts[i][0]), int(pts[i][1]),
                             int(pts[i + 1][0]), int(pts[i + 1][1]))

        # Draw endpoint dot
        if pts:
            last = pts[-1]
            painter.setBrush(QColor(tk.green if tk.grad_top in ("#0A0A0A", "#FFFFFF") else tk.blue))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(last[0]) - 3, int(last[1]) - 3, 6, 6)

        painter.end()


# ── Detail panel ────────────────────────────────────────────────────────────

class ProductDetail(QWidget):
    """Side panel showing detailed product info, operations, and recent transactions."""
    request_in   = pyqtSignal()
    request_out  = pyqtSignal()
    request_adj  = pyqtSignal()
    request_edit = pyqtSignal()
    request_del  = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._item: InventoryItem | None = None
        self._build(); self._empty()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(12, 12, 12, 12); root.setSpacing(10)

        # ── Identity Card ──
        self.ic = QFrame(); self.ic.setObjectName("detail_card")
        il = QVBoxLayout(self.ic); il.setContentsMargins(16, 14, 16, 14); il.setSpacing(6)
        cr = QHBoxLayout(); cr.setSpacing(8)
        self.dot = QLabel(); self.dot.setFixedSize(18, 18)
        self.cnm = QLabel(); self.cnm.setObjectName("detail_color_name")
        cr.addWidget(self.dot); cr.addWidget(self.cnm); cr.addStretch()
        self.nm = QLabel(); self.nm.setObjectName("detail_product_name"); self.nm.setWordWrap(True)
        self.bc = QLabel(); self.bc.setObjectName("detail_barcode")
        self.pr = QLabel(); self.pr.setObjectName("detail_barcode")
        self.sku_lbl = QLabel(); self.sku_lbl.setObjectName("detail_barcode")
        self.up = QLabel(); self.up.setObjectName("detail_updated")

        # Category badge
        self.cat_lbl = QLabel(); self.cat_lbl.setObjectName("detail_category")
        self.cat_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)

        il.addWidget(self.nm); il.addLayout(cr)
        il.addWidget(self.cat_lbl)
        il.addWidget(self.bc); il.addWidget(self.sku_lbl)
        il.addWidget(self.pr); il.addWidget(self.up)
        root.addWidget(self.ic)

        # ── Product Image ──
        self._img_frame = QFrame(); self._img_frame.setObjectName("detail_card")
        img_lay = QVBoxLayout(self._img_frame)
        img_lay.setContentsMargins(8, 8, 8, 8); img_lay.setSpacing(0)
        self._img_lbl = QLabel()
        self._img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_lbl.setFixedHeight(160)
        self._img_lbl.setScaledContents(False)
        img_lay.addWidget(self._img_lbl)
        self._img_frame.hide()
        root.addWidget(self._img_frame)

        # ── Barcode Preview ──
        self.bc_frame = QFrame(); self.bc_frame.setObjectName("detail_barcode_frame")
        bc_lay = QVBoxLayout(self.bc_frame)
        bc_lay.setContentsMargins(6, 6, 6, 6); bc_lay.setSpacing(0)
        self.bc_img = QLabel()
        self.bc_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bc_img.setFixedHeight(60)
        bc_lay.addWidget(self.bc_img)
        self.bc_frame.hide()
        root.addWidget(self.bc_frame)

        # ── Stock Card ──
        sc = QFrame(); sc.setObjectName("detail_card")
        sl = QVBoxLayout(sc); sl.setContentsMargins(16, 12, 16, 12); sl.setSpacing(2)
        self._sh = QLabel(t("detail_current_stock")); self._sh.setObjectName("detail_section_hdr")
        self.sv = QLabel("—"); self.sv.setObjectName("big_stock")
        self.sv.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sb = QLabel(); self.sb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.st = QLabel(); self.st.setObjectName("detail_threshold")
        self.st.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl.addWidget(self._sh); sl.addWidget(self.sv); sl.addWidget(self.sb); sl.addWidget(self.st)
        root.addWidget(sc)

        # ── Stock Trend Sparkline ──
        self._spark_hdr = QLabel(t("detail_stock_trend"))
        self._spark_hdr.setObjectName("detail_section_hdr")
        root.addWidget(self._spark_hdr)
        self.sparkline = _StockSparkline()
        root.addWidget(self.sparkline)

        # ── Operations Card ──
        oc = QFrame(); oc.setObjectName("detail_card")
        ol = QVBoxLayout(oc); ol.setContentsMargins(16, 14, 16, 14); ol.setSpacing(8)
        self._oh = QLabel(t("detail_operations")); self._oh.setObjectName("detail_section_hdr")
        ol.addWidget(self._oh)
        self.bin = QPushButton(); self.bin.setObjectName("op_in")
        self.bot = QPushButton(); self.bot.setObjectName("op_out")
        self.bad = QPushButton(); self.bad.setObjectName("op_adj")
        self._set_op_btn_text()
        for b in (self.bin, self.bot, self.bad): ol.addWidget(b)
        self.bin.clicked.connect(self.request_in)
        self.bot.clicked.connect(self.request_out)
        self.bad.clicked.connect(self.request_adj)
        root.addWidget(oc)

        # ── Management Buttons ──
        mr = QHBoxLayout(); mr.setSpacing(8)
        self.bed = QPushButton(); self.bed.setObjectName("mgmt_edit")
        self.bed.setIcon(get_button_icon("edit"))
        self.bed.setIconSize(QSize(16, 16))
        self.bdl = QPushButton(); self.bdl.setObjectName("mgmt_del")
        self.bdl.setIcon(get_button_icon("delete"))
        self.bdl.setIconSize(QSize(16, 16))
        mr.addWidget(self.bed); mr.addWidget(self.bdl)
        self.bed.clicked.connect(self.request_edit)
        self.bdl.clicked.connect(self.request_del)
        root.addLayout(mr)

        # ── Recent Transactions ──
        self._th = QLabel(t("detail_recent_txns")); self._th.setObjectName("detail_section_hdr")
        root.addWidget(self._th)
        ts = QScrollArea(); ts.setWidgetResizable(True); ts.setObjectName("txn_scroll_area")
        ts.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        ts.setMinimumHeight(180)
        self.mt = MiniTxnList(); ts.setWidget(self.mt); root.addWidget(ts, 1)

    def _set_op_btn_text(self):
        self.bin.setText(t("btn_stock_in"))
        self.bot.setText(t("btn_stock_out"))
        self.bad.setText(t("btn_adjust"))
        self.bin.setToolTip(t("tooltip_stock_in"))
        self.bot.setToolTip(t("tooltip_stock_out"))
        self.bad.setToolTip(t("tooltip_adjust"))

    def retranslate(self):
        self._sh.setText(t("detail_current_stock"))
        self._oh.setText(t("detail_operations"))
        self._th.setText(t("detail_recent_txns"))
        self._spark_hdr.setText(t("detail_stock_trend"))
        self._set_op_btn_text()
        if self._item: self.set_product(self._item)
        else:           self._empty()

    # ── Barcode rendering ───────────────────────────────────────────────────

    def _render_barcode(self, code: str) -> bool:
        """Try to render a barcode image. Return True on success."""
        try:
            from app.services.barcode_gen_service import BarcodeGenService
            svc = BarcodeGenService()
            png_bytes = svc.render_barcode_image(code, "code128")
            pix = QPixmap()
            pix.loadFromData(png_bytes)
            if pix.isNull():
                return False
            scaled = pix.scaledToHeight(52, Qt.TransformationMode.SmoothTransformation)
            self.bc_img.setPixmap(scaled)
            return True
        except Exception:
            return False

    # ── Product image display ────────────────────────────────────────────────

    def _show_image(self, item: InventoryItem) -> None:
        """Show the product image if one is assigned."""
        if item.image_path:
            from app.services.image_service import ImageService
            svc = ImageService()
            full_path = svc.get_image_path(item.image_path)
            if full_path:
                pix = QPixmap(full_path)
                if not pix.isNull():
                    scaled = pix.scaledToHeight(
                        150, Qt.TransformationMode.SmoothTransformation)
                    self._img_lbl.setPixmap(scaled)
                    self._img_frame.show()
                    return
        self._img_lbl.clear()
        self._img_frame.hide()

    # ── Sparkline data from transactions ────────────────────────────────────

    def _load_sparkline(self, item_id: int) -> None:
        """Load last ~20 stock levels from transaction history."""
        try:
            from app.repositories.transaction_repo import TransactionRepository
            repo = TransactionRepository()
            txns = repo.get_transactions(item_id=item_id, limit=20)
            if not txns:
                self.sparkline.set_data([])
                return
            # txns come newest-first — reverse to chronological order
            txns.reverse()
            # Use stock_after from each transaction as data points
            points = [txn.stock_after for txn in txns]
            self.sparkline.set_data(points)
        except Exception:
            self.sparkline.set_data([])

    # ── Main update ─────────────────────────────────────────────────────────

    def set_product(self, item: InventoryItem | None):
        self._item = item
        if not item: self._empty(); return
        self._set_op_btn_text()

        if item.is_product:
            hc  = clr.hex_for(item.color)
            brd = "rgba(102,102,102,153)" if clr.is_light(hc) else "transparent"
            self.nm.setText(f"<b>{item.brand}</b>  ·  {item.name}")
            self.dot.setStyleSheet(f"background:{hc}; border-radius:9px; border:1.5px solid {brd};")
            self.cnm.setText(item.color)
            self.cat_lbl.setText("")
            self.cat_lbl.hide()
        else:
            self.nm.setText(item.display_name)
            hc = item.part_type_color or ""
            if hc:
                brd = "rgba(102,102,102,153)" if clr.is_light(hc) else "transparent"
                self.dot.setStyleSheet(f"background:{hc}; border-radius:9px; border:1.5px solid {brd};")
                self.cnm.setText(item.part_type_name)
            else:
                self.dot.setStyleSheet(""); self.cnm.setText("")
            # Show category/part type badge for matrix items
            if item.part_type_name:
                self.cat_lbl.setText(item.part_type_name)
                self.cat_lbl.show()
            else:
                self.cat_lbl.setText("")
                self.cat_lbl.hide()

        # Product image
        self._show_image(item)

        # SKU
        if item.sku:
            self.sku_lbl.setText(t("detail_sku", val=item.sku))
            self.sku_lbl.show()
        else:
            self.sku_lbl.setText("")
            self.sku_lbl.hide()

        self.bc.setText(t("detail_barcode", val=item.barcode or t("dlg_color_none")))
        cfg = ShopConfig.get()
        price_display = cfg.format_currency(item.sell_price) if item.sell_price else "—"
        self.pr.setText(t("detail_sell_price", val=price_display))
        self.up.setText(t("detail_updated", val=str(item.updated_at or "")[:16]))

        # Barcode preview
        if item.barcode:
            if self._render_barcode(item.barcode):
                self.bc_frame.show()
            else:
                self.bc_frame.hide()
        else:
            self.bc_frame.hide()

        # Stock card
        tk  = THEME.tokens
        stk = item.stock
        thr = item.min_stock
        sc  = _sc(stk, thr); sl_str = _sl(stk, thr)
        self.sv.setText(str(stk)); self.sv.setStyleSheet(f"color:{sc.name()};")

        badge_map = {
            "OK":       (tk.green,  _rgba(tk.green,  "28")),
            "LOW":      (tk.yellow, _rgba(tk.yellow, "30")),
            "CRITICAL": (tk.orange, _rgba(tk.orange, "28")),
            "OUT":      (tk.red,    _rgba(tk.red,    "28")),
        }
        fg, bg = badge_map.get(sl_str, (tk.t3, tk.border))
        badge_labels = {
            "OK": t("badge_ok"), "LOW": t("badge_low"),
            "CRITICAL": t("badge_critical"), "OUT": t("badge_out"),
        }
        self.sb.setText(badge_labels.get(sl_str, sl_str))
        self.sb.setStyleSheet(
            f"color:{fg}; background:{bg}; border:1px solid {_rgba(fg, '40')};"
            "border-radius:10px; font-weight:800; font-size:9pt; padding:5px 14px;"
        )
        self.st.setText(t("detail_alert_at", n=thr))

        # Sparkline
        self._load_sparkline(item.id)

        # Recent transactions
        self.mt.load(item.id)

        for b in (self.bin, self.bot, self.bad): b.setEnabled(True)
        self.bed.setEnabled(item.is_product)
        self.bdl.setEnabled(item.is_product)

    def _empty(self):
        self.nm.setText(f"<i style='color:#7A7FA8'>{t('detail_select_prompt')}</i>")
        self.dot.setStyleSheet(""); self.cnm.setText("")
        self.bc.setText(""); self.pr.setText(""); self.up.setText("")
        self.sku_lbl.setText(""); self.sku_lbl.hide()
        self.cat_lbl.setText(""); self.cat_lbl.hide()
        self.bc_frame.hide()
        self.sv.setText("—"); self.sv.setStyleSheet("")
        self.sb.setText(""); self.sb.setStyleSheet(""); self.st.setText("")
        self.sparkline.set_data([])
        for b in (self.bin, self.bot, self.bad, self.bed, self.bdl): b.setEnabled(False)
