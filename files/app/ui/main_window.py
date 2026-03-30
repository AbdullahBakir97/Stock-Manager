"""
main_window.py — Stock Manager Pro v2
Gradient dark (indigo-charcoal) / warm light (cream→periwinkle).
All CRUD, stock ops, scanner, alerts, dark/light toggle, i18n (EN/DE/AR).
Now powered by the v2 repository + service layer.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QLineEdit,
    QPushButton, QFrame, QStatusBar, QScrollArea, QCheckBox,
    QTabWidget, QMessageBox, QDialog, QSizePolicy,
    QStyle, QStyleOptionViewItem, QStyledItemDelegate,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize, QRect, QModelIndex, QRectF
from PyQt6.QtGui import (
    QFont, QPainter, QColor, QKeySequence, QShortcut, QPainterPath,
    QPixmap, QIcon, QLinearGradient, QBrush,
)

from app.core.database import init_db, get_connection, ensure_matrix_entries
from app.core.config import ShopConfig
from app.ui.dialogs.admin.admin_dialog import open_admin
from app.ui.dialogs.setup_wizard import SetupWizard
from app.repositories.category_repo import CategoryRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.item_repo import ItemRepository
from app.services.stock_service import StockService
from app.services.alert_service import AlertService
from app.models.item import InventoryItem
from app.ui.tabs.matrix_tab import MatrixTab

from app.core import colors as clr
from app.core.colors import PALETTE
from app.ui.dialogs.product_dialogs import ProductDialog, StockOpDialog, LowStockDialog
from app.core.theme import THEME, GradientBackground, qc, _rgba
from app.core.i18n import t, set_lang, LANG, color_t, note_t
from app.ui.delegates import AlternatingRowDelegate
from app.core.icon_utils import load_svg_icon, get_button_icon

# ── Module-level singletons ───────────────────────────────────────────────────
_cat_repo   = CategoryRepository()
_txn_repo   = TransactionRepository()
_item_repo  = ItemRepository()
_stock_svc  = StockService()
_alert_svc  = AlertService()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_op_dict(item: InventoryItem) -> dict:
    """Build a StockOpDialog-compatible dict from any InventoryItem."""
    return {
        "id":                  item.id,
        "brand":               item.model_brand or item.brand,
        "type":                item.part_type_name or item.name,
        "color":               "" if not item.is_product else item.color,
        "stock":               item.stock,
        "low_stock_threshold": item.min_stock,
        "barcode":             item.barcode,
        "sell_price":          item.sell_price,
        "updated_at":          item.updated_at,
    }


def _to_edit_dict(item: InventoryItem) -> dict:
    """Build a ProductDialog-compatible dict from a standalone InventoryItem."""
    return {
        "brand":               item.brand,
        "type":                item.name,
        "color":               item.color,
        "barcode":             item.barcode,
        "low_stock_threshold": item.min_stock,
        "sell_price":          item.sell_price,
    }


def _sc(s: int, thr: int) -> QColor:
    tk = THEME.tokens
    if s == 0:              return QColor(tk.red)
    if s <= max(1, thr//2): return QColor(tk.orange)
    if s <= thr:            return QColor(tk.yellow)
    return QColor(tk.green)

def _sl(s: int, thr: int) -> str:
    if s == 0:              return "OUT"
    if s <= max(1, thr//2): return "CRITICAL"
    if s <= thr:            return "LOW"
    return "OK"


# ── Delegates ─────────────────────────────────────────────────────────────────

class ColorSwatchDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, opt: QStyleOptionViewItem, idx: QModelIndex):
        o = QStyleOptionViewItem(opt); self.initStyleOption(o, idx)
        painter.save(); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tk  = THEME.tokens
        alt = "#2C304C" if THEME.is_dark else "#E4E2F4"

        if o.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(o.rect, qc(tk.blue, 0x40))
        elif idx.row() % 2 == 0:
            painter.fillRect(o.rect, QColor(tk.card))
        else:
            painter.fillRect(o.rect, QColor(alt))

        hx      = idx.data(Qt.ItemDataRole.UserRole)
        en_name = idx.data(Qt.ItemDataRole.DisplayRole) or ""
        name    = color_t(en_name)
        r       = o.rect

        if hx:
            R = 9; cx = r.left() + 28; cy = r.center().y()
            painter.setBrush(QColor(tk.border2)); painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(cx-R-1, cy-R-1, 2*R+2, 2*R+2)
            painter.setBrush(QColor(hx))
            painter.drawEllipse(cx-R, cy-R, 2*R, 2*R)
            tr = QRect(r.left()+48, r.top(), r.width()-54, r.height())
            painter.setPen(QColor(tk.t1)); painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(tr, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, name)
        else:
            painter.setPen(QColor(tk.t3)); painter.drawText(r, Qt.AlignmentFlag.AlignCenter, name)
        painter.restore()

    def sizeHint(self, o, i): return QSize(super().sizeHint(o, i).width(), 44)


class StatusBadgeDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, opt: QStyleOptionViewItem, idx: QModelIndex):
        o = QStyleOptionViewItem(opt); self.initStyleOption(o, idx)
        painter.save(); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tk  = THEME.tokens
        alt = "#2C304C" if THEME.is_dark else "#E4E2F4"

        if o.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(o.rect, qc(tk.blue, 0x40))
        elif idx.row() % 2 == 0:
            painter.fillRect(o.rect, QColor(tk.card))
        else:
            painter.fillRect(o.rect, QColor(alt))

        key  = idx.data(Qt.ItemDataRole.DisplayRole) or ""
        text = {
            "OK": t("status_ok_lbl"), "LOW": t("status_low_lbl"),
            "CRITICAL": t("status_critical_lbl"), "OUT": t("status_out_lbl"),
        }.get(key, key)

        pal = {
            "OK":       (tk.green,  qc(tk.green,  0x28)),
            "LOW":      (tk.yellow, qc(tk.yellow, 0x30)),
            "CRITICAL": (tk.orange, qc(tk.orange, 0x28)),
            "OUT":      (tk.red,    qc(tk.red,    0x28)),
        }
        pair = pal.get(key)
        fg   = pair[0] if pair else tk.t3
        bg_c = pair[1] if pair else QColor(tk.border)

        r  = o.rect; f = QFont("Segoe UI", 8, QFont.Weight.Bold); painter.setFont(f)
        fm = painter.fontMetrics(); tw = fm.horizontalAdvance(text)
        ph, pv = 12, 5; pw = tw + ph*2; phh = fm.height() + pv*2
        px = r.left() + (r.width() - pw)//2; py = r.top() + (r.height() - phh)//2

        path = QPainterPath()
        path.addRoundedRect(QRectF(px, py, pw, phh), phh/2, phh/2)
        painter.setBrush(bg_c); painter.setPen(Qt.PenStyle.NoPen); painter.drawPath(path)
        painter.setPen(QColor(fg))
        painter.drawText(px, py, pw, phh, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()

    def sizeHint(self, o, i): return QSize(super().sizeHint(o, i).width(), 44)


# ── Barcode / Search input ─────────────────────────────────────────────────────

class BarcodeLineEdit(QLineEdit):
    barcode_scanned = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._t = QTimer(self); self._t.setSingleShot(True); self._t.setInterval(80)
        self._t.timeout.connect(self._flush); self._buf: list[str] = []
        self.setPlaceholderText(t("search_placeholder"))

    def keyPressEvent(self, e):
        super().keyPressEvent(e)
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._commit()
        else:
            self._buf.append(e.text()); self._t.start()

    def _flush(self):
        if len(self._buf) >= 3:  # Reduced from 4 to allow shorter barcodes
            bc = "".join(self._buf).strip()
            if bc: self.barcode_scanned.emit(bc)
        self._buf.clear()

    def _commit(self):
        self._t.stop(); txt = self.text().strip()
        if txt: self.barcode_scanned.emit(txt); self.clear()
        self._buf.clear()


# ── Summary Card ───────────────────────────────────────────────────────────────

class SummaryCard(QFrame):
    def __init__(self, key: str, parent=None):
        super().__init__(parent); self.setObjectName("summary_card")
        self._key = key
        lay = QVBoxLayout(self); lay.setContentsMargins(18, 16, 18, 16); lay.setSpacing(4)
        self.val = QLabel("—"); self.val.setObjectName("card_value")
        self.val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl = QLabel(t(key).upper()); self.lbl.setObjectName("card_label")
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.val); lay.addWidget(self.lbl)

    def set(self, v, color=""):
        self.val.setText(str(v))
        self.val.setStyleSheet(f"color:{color};" if color else "")

    def retranslate(self):
        self.lbl.setText(t(self._key).upper())


# ── Table Delegates ───────────────────────────────────────────────────────
from app.core.theme import THEME

class ColorDotDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        color_name = index.data(Qt.ItemDataRole.DisplayRole)
        if not color_name or color_name == "—":
            # Handle empty color with AlternatingRowDelegate logic
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw alternating row background
            if option.state & QStyle.StateFlag.State_Selected:
                painter.fillRect(option.rect, qc(THEME.tokens.blue, 0x40))
            elif index.row() % 2 == 0:
                painter.fillRect(option.rect, QColor(THEME.tokens.card))
            else:
                painter.fillRect(option.rect, QColor("#2C304C" if THEME.is_dark else "#E4E2F4"))
            
            # Draw "—" in muted color
            painter.setPen(QColor(128, 128, 128))
            painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, "—")
            painter.restore()
            return
            
        # Get hex color from palette
        hex_color = PALETTE.get(color_name, color_name)
        
        # Draw alternating row background like other delegates
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background for alternating rows
        tk = THEME.tokens
        alt = "#2C304C" if THEME.is_dark else "#E4E2F4"
        
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, qc(tk.blue, 0x40))
        elif index.row() % 2 == 0:
            painter.fillRect(option.rect, QColor(tk.card))
        else:
            painter.fillRect(option.rect, QColor(alt))
        
        # Draw brown border circle
        rect = option.rect
        R = 9
        cx = rect.center().x()
        cy = rect.center().y()
        
        painter.setBrush(QColor(tk.border2))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx-R-1, cy-R-1, 2*R+2, 2*R+2)
        
        # Draw color circle with mapped hex color
        painter.setBrush(QColor(hex_color))
        painter.drawEllipse(cx-R, cy-R, 2*R, 2*R)
        
        painter.restore()

class DifferenceDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # Draw alternating row background like Excel
        painter.save()
        tk = THEME.tokens
        alt = "#2C304C" if THEME.is_dark else "#E4E2F4"
        
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, qc(tk.blue, 0x40))
        elif index.row() % 2 == 0:
            painter.fillRect(option.rect, QColor(tk.card))
        else:
            painter.fillRect(option.rect, QColor(alt))
        
        # Get original text and color from item
        item = self.parent().item(index.row(), index.column())
        if item:
            text = item.text()
            if text and text != "—":
                painter.setPen(item.foreground().color())
                font = QFont("Segoe UI", 10, QFont.Weight.Bold)
                painter.setFont(font)
                painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, text)
            else:
                # Draw "—" in muted color
                painter.setPen(QColor(128, 128, 128))
                painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, "—")
        painter.restore()

# ── Product Table ──────────────────────────────────────────────────────────────

class ProductTable(QTableWidget):
    row_selected = pyqtSignal(object)   # emits InventoryItem or None
    _COL_KEYS = ["col_num", "col_item", "col_color", "col_barcode", "col_price",
                 "col_stock", "col_min", "col_best_bung", "col_status"]
    _WIDTHS    = [42, 280, 60, 100, 80, 60, 60, 100, 96]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(len(self._COL_KEYS))
        self.setHorizontalHeaderLabels([t(k) for k in self._COL_KEYS])
        hh = self.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for i, w in enumerate(self._WIDTHS): self.setColumnWidth(i, w)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.setSelectionBehavior(self.SelectionBehavior.SelectRows)
        self.setSelectionMode(self.SelectionMode.SingleSelection)
        self.setEditTriggers(self.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(False); self.setSortingEnabled(True)  # Custom delegates handle alternating
        self.setShowGrid(True)  # Show grid lines like matrix
        self.verticalHeader().setVisible(False); self.setShowGrid(False)
        self.setItemDelegateForColumn(0, AlternatingRowDelegate(self))  # Num column
        self.setItemDelegateForColumn(1, AlternatingRowDelegate(self))  # Item column
        self.setItemDelegateForColumn(2, ColorDotDelegate(self))       # Color column
        self.setItemDelegateForColumn(3, AlternatingRowDelegate(self))  # Barcode column
        self.setItemDelegateForColumn(4, AlternatingRowDelegate(self))  # Price column
        self.setItemDelegateForColumn(5, AlternatingRowDelegate(self))  # Stock column
        self.setItemDelegateForColumn(6, AlternatingRowDelegate(self))  # Min column
        self.setItemDelegateForColumn(7, DifferenceDelegate(self))      # Difference column
        self.setItemDelegateForColumn(8, StatusBadgeDelegate(self))      # Status column
        self._data: list[InventoryItem] = []
        self.itemSelectionChanged.connect(self._emit)
        # Store default widths for reset
        self._default_widths = self._WIDTHS.copy()

    def retranslate(self):
        self.setHorizontalHeaderLabels([t(k) for k in self._COL_KEYS])
    
    def reset_column_widths(self):
        """Reset all column widths to default values."""
        for i, w in enumerate(self._default_widths):
            self.setColumnWidth(i, w)

    def load(self, items: list[InventoryItem]):
        self._data = list(items)
        self.setSortingEnabled(False); self.setRowCount(len(self._data))
        cfg = ShopConfig.get()
        for i, item in enumerate(self._data):
            sc  = _sc(item.stock, item.min_stock)
            sl  = _sl(item.stock, item.min_stock)
            sp  = item.sell_price
            price_str = cfg.format_currency(sp) if sp is not None else "—"
            diff = item.stock - item.min_stock
            diff_str = f"Δ{diff:+d}" if item.min_stock > 0 else "—"
            
            vals = [str(item.id), item.display_name,
                    item.color or "—", item.barcode or "—", price_str,
                    str(item.stock), str(item.min_stock), diff_str, sl]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if j == 5:  # Stock column
                    it.setForeground(sc)
                    it.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
                elif j == 7:  # Difference column
                    it.setForeground(sc)
                    it.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                self.setItem(i, j, it)
            self.setRowHeight(i, 44)
        self.setSortingEnabled(True)

    def _emit(self):
        r = self.currentRow()
        if r < 0: self.row_selected.emit(None); return
        it = self.item(r, 0)
        if it:
            pid = int(it.text())
            for item in self._data:
                if item.id == pid: self.row_selected.emit(item); return
        self.row_selected.emit(None)

    def select_by_id(self, pid: int):
        for r in range(self.rowCount()):
            it = self.item(r, 0)
            if it and int(it.text()) == pid:
                self.selectRow(r); self.scrollToItem(it); return


# ── Transaction Table ──────────────────────────────────────────────────────────

class TransactionTable(QTableWidget):
    _COL_KEYS = ["col_datetime", "txn_col_item",
                 "col_operation", "col_delta", "col_before", "col_after_col", "col_note"]
    _WIDTHS   = [130, 220, 90, 64, 64, 64, 150]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(len(self._COL_KEYS))
        self.setHorizontalHeaderLabels([t(k) for k in self._COL_KEYS])
        hh = self.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for i, w in enumerate(self._WIDTHS): self.setColumnWidth(i, w)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.setSelectionBehavior(self.SelectionBehavior.SelectRows)
        self.setEditTriggers(self.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True); self.verticalHeader().setVisible(False)
        self.setShowGrid(False)

    def retranslate(self):
        self.setHorizontalHeaderLabels([t(k) for k in self._COL_KEYS])

    _OP_LBL = {"IN": "op_in_short", "OUT": "op_out_short",
               "ADJUST": "op_adj_short", "CREATE": "op_create_short"}

    def load(self, rows):
        tk = THEME.tokens
        OP = {"IN": tk.green, "OUT": tk.red, "ADJUST": tk.blue, "CREATE": tk.purple}
        self.setRowCount(len(rows))
        for i, row in enumerate(rows):
            d   = row.stock_after - row.stock_before
            ds  = f"+{d}" if d >= 0 else str(d)
            op_key     = row.operation
            op_display = t(self._OP_LBL.get(op_key, op_key))
            vals = [
                row.timestamp[:16], row.display_name,
                op_display, ds,
                str(row.stock_before), str(row.stock_after),
                note_t(row.note or "") or "—",
            ]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if j == 2:
                    it.setForeground(QColor(OP.get(op_key, tk.t3)))
                    it.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                elif j == 3:
                    it.setForeground(QColor(tk.green if d >= 0 else tk.red))
                    it.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                self.setItem(i, j, it)
            self.setRowHeight(i, 44)


# ── Mini transaction list ──────────────────────────────────────────────────────

class MiniTxnList(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0); self._lay.setSpacing(0)
        self._rows: list[QWidget] = []

    def load(self, pid: int):
        for w in self._rows: self._lay.removeWidget(w); w.deleteLater()
        self._rows.clear()

        txns = _txn_repo.get_transactions(item_id=pid, limit=10)
        if not txns:
            lb = QLabel(t("no_transactions")); lb.setObjectName("txn_empty")
            lb.setAlignment(Qt.AlignmentFlag.AlignCenter); lb.setMinimumHeight(48)
            self._lay.addWidget(lb); self._rows.append(lb); return

        tk = THEME.tokens
        OP     = {"IN": tk.green, "OUT": tk.red, "ADJUST": tk.blue, "CREATE": tk.purple}
        OP_LBL = {"IN": "op_in_short", "OUT": "op_out_short",
                  "ADJUST": "op_adj_short", "CREATE": "op_create_short"}

        for idx, txn in enumerate(txns):
            rf = QFrame()
            rf.setObjectName("txn_row_alt" if idx % 2 else "txn_row")
            rl = QHBoxLayout(rf); rl.setContentsMargins(12, 8, 12, 8); rl.setSpacing(10)

            opfg    = OP.get(txn.operation, tk.t3)
            op_text = t(OP_LBL.get(txn.operation, "op_in_short"))
            d       = txn.stock_after - txn.stock_before
            ds      = f"+{d}" if d >= 0 else str(d)

            ol = QLabel(op_text); ol.setFixedWidth(60)
            ol.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ol.setStyleSheet(
                f"color:{opfg}; background:{_rgba(opfg, '20')}; border-radius:7px;"
                "font-weight:700; font-size:8pt; padding:3px 4px;"
            )
            dl = QLabel(ds); dl.setFixedWidth(40); dl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dl.setStyleSheet(f"color:{tk.green if d >= 0 else tk.red}; font-weight:800; font-size:10pt;")
            al = QLabel(f"→ {txn.stock_after}"); al.setObjectName("txn_after")
            tl = QLabel(txn.timestamp[5:16]);    tl.setObjectName("txn_time")

            rl.addWidget(ol); rl.addWidget(dl); rl.addWidget(al); rl.addStretch(); rl.addWidget(tl)
            self._lay.addWidget(rf); self._rows.append(rf)


# ── Product Detail Panel ───────────────────────────────────────────────────────

class ProductDetail(QWidget):
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

        self.ic = QFrame(); self.ic.setObjectName("detail_card")
        il = QVBoxLayout(self.ic); il.setContentsMargins(16, 14, 16, 14); il.setSpacing(6)
        cr = QHBoxLayout(); cr.setSpacing(8)
        self.dot = QLabel(); self.dot.setFixedSize(18, 18)
        self.cnm = QLabel(); self.cnm.setObjectName("detail_color_name")
        cr.addWidget(self.dot); cr.addWidget(self.cnm); cr.addStretch()
        self.nm = QLabel(); self.nm.setObjectName("detail_product_name"); self.nm.setWordWrap(True)
        self.bc = QLabel(); self.bc.setObjectName("detail_barcode")
        self.pr = QLabel(); self.pr.setObjectName("detail_barcode")
        self.up = QLabel(); self.up.setObjectName("detail_updated")
        il.addWidget(self.nm); il.addLayout(cr); il.addWidget(self.bc); il.addWidget(self.pr); il.addWidget(self.up)
        root.addWidget(self.ic)

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

        self._th = QLabel(t("detail_recent_txns")); self._th.setObjectName("detail_section_hdr")
        root.addWidget(self._th)
        ts = QScrollArea(); ts.setWidgetResizable(True); ts.setObjectName("txn_scroll_area")
        ts.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        ts.setMinimumHeight(220)
        self.mt = MiniTxnList(); ts.setWidget(self.mt); root.addWidget(ts, 1)

    def _set_op_btn_text(self):
        self.bin.setText(t("btn_stock_in"))
        self.bot.setText(t("btn_stock_out"))
        self.bad.setText(t("btn_adjust"))

    def retranslate(self):
        self._sh.setText(t("detail_current_stock"))
        self._oh.setText(t("detail_operations"))
        self._th.setText(t("detail_recent_txns"))
        self._set_op_btn_text()
        # Edit and delete buttons use icons only - don't set text
        if self._item: self.set_product(self._item)
        else:           self._empty()

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
        else:
            self.nm.setText(item.display_name)
            hc = item.part_type_color or ""
            if hc:
                brd = "rgba(102,102,102,153)" if clr.is_light(hc) else "transparent"
                self.dot.setStyleSheet(f"background:{hc}; border-radius:9px; border:1.5px solid {brd};")
                self.cnm.setText(item.part_type_name)
            else:
                self.dot.setStyleSheet(""); self.cnm.setText("")

        self.bc.setText(t("detail_barcode", val=item.barcode or t("dlg_color_none")))
        cfg = ShopConfig.get()
        price_display = cfg.format_currency(item.sell_price) if item.sell_price else "—"
        self.pr.setText(t("detail_sell_price", val=price_display))
        self.up.setText(t("detail_updated", val=str(item.updated_at or "")[:16]))

        tk  = THEME.tokens
        stk = item.stock
        thr = item.min_stock
        sc  = _sc(stk, thr); sl = _sl(stk, thr)
        self.sv.setText(str(stk)); self.sv.setStyleSheet(f"color:{sc.name()};")

        badge_map = {
            "OK":       (tk.green,  _rgba(tk.green,  "28")),
            "LOW":      (tk.yellow, _rgba(tk.yellow, "30")),
            "CRITICAL": (tk.orange, _rgba(tk.orange, "28")),
            "OUT":      (tk.red,    _rgba(tk.red,    "28")),
        }
        fg, bg = badge_map.get(sl, (tk.t3, tk.border))
        badge_labels = {
            "OK": t("badge_ok"), "LOW": t("badge_low"),
            "CRITICAL": t("badge_critical"), "OUT": t("badge_out"),
        }
        self.sb.setText(badge_labels.get(sl, sl))
        self.sb.setStyleSheet(
            f"color:{fg}; background:{bg}; border:1px solid {_rgba(fg, '40')};"
            "border-radius:10px; font-weight:800; font-size:9pt; padding:5px 14px;"
        )
        self.st.setText(t("detail_alert_at", n=thr))
        self.mt.load(item.id)
        for b in (self.bin, self.bot, self.bad): b.setEnabled(True)
        self.bed.setEnabled(item.is_product)
        self.bdl.setEnabled(item.is_product)

    def _empty(self):
        self.nm.setText(f"<i style='color:#7A7FA8'>{t('detail_select_prompt')}</i>")
        self.dot.setStyleSheet(""); self.cnm.setText("")
        self.bc.setText(""); self.pr.setText(""); self.up.setText("")
        self.sv.setText("—"); self.sv.setStyleSheet("")
        self.sb.setText(""); self.sb.setStyleSheet(""); self.st.setText("")
        for b in (self.bin, self.bot, self.bad, self.bed, self.bdl): b.setEnabled(False)


# ── Main Window ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        init_db()
        cfg = ShopConfig.get()
        _title = cfg.name if cfg.name else t("app_title")
        self.setWindowTitle(_title); self.resize(1440, 900)
        self._cp: InventoryItem | None = None
        self._ld: LowStockDialog | None = None

        self._bg = GradientBackground()
        self._bg.setObjectName("gradient_bg")
        self.setCentralWidget(self._bg)
        THEME.apply(self._bg)

        self._build_ui()
        self._connect()
        self._refresh_products()
        self._refresh_summary()
        self._refresh_all_txns()

        self._timer = QTimer(self)
        self._timer.setInterval(60_000)
        self._timer.timeout.connect(self._check_alerts)
        self._timer.start()
        self._check_alerts()

        # Show first-run wizard if setup not yet completed
        QTimer.singleShot(100, self._check_first_run)

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self._bg)
        root.setContentsMargins(18, 16, 18, 16); root.setSpacing(12)

        # Top bar
        top = QHBoxLayout(); top.setSpacing(10)
        cfg = ShopConfig.get()
        _title = cfg.name if cfg.name else t("app_title")
        self._logo_lbl: QLabel | None = None
        self._logo_lbl = self._build_logo_label()
        if self._logo_lbl:
            top.addWidget(self._logo_lbl)
        self._title_lbl = QLabel(_title); self._title_lbl.setObjectName("app_title")
        top.addWidget(self._title_lbl); top.addStretch()

        self.alert_btn = QPushButton(t("alert_ok")); self.alert_btn.setObjectName("alert_ok")
        self.alert_btn.clicked.connect(self._show_alerts)

        self.refresh_btn = QPushButton(); self.refresh_btn.setObjectName("icon_btn")
        self.refresh_btn.setFixedSize(44, 44)
        self.refresh_btn.setIcon(get_button_icon("refresh"))
        self.refresh_btn.setIconSize(QSize(24, 24))
        self.refresh_btn.setToolTip(t("tooltip_refresh"))
        self.refresh_btn.clicked.connect(self._refresh_all)

        self.mode_btn = QPushButton(); self.mode_btn.setObjectName("mode_btn")
        self.mode_btn.setFixedSize(44, 44)
        self.mode_btn.setIcon(get_button_icon("settings"))
        self.mode_btn.setIconSize(QSize(24, 24))
        self.mode_btn.setToolTip(t("tooltip_theme"))
        self.mode_btn.clicked.connect(self._toggle_mode)

        lang_fr = QFrame(); lang_fr.setObjectName("lang_bar")
        lang_lay = QHBoxLayout(lang_fr); lang_lay.setContentsMargins(3, 3, 3, 3); lang_lay.setSpacing(1)
        self._lang_btns: dict[str, QPushButton] = {}
        for code in ("EN", "DE", "AR"):
            b = QPushButton(code); b.setObjectName("lang_btn_active" if code == LANG else "lang_btn")
            b.setFixedSize(40, 30); b.clicked.connect(lambda _, c=code: self._set_lang(c))
            lang_lay.addWidget(b); self._lang_btns[code] = b

        self.admin_btn = QPushButton(); self.admin_btn.setObjectName("icon_btn")
        self.admin_btn.setFixedSize(44, 44)
        self.admin_btn.setIcon(get_button_icon("settings"))
        self.admin_btn.setIconSize(QSize(24, 24))
        self.admin_btn.setToolTip(t("tooltip_admin"))
        self.admin_btn.clicked.connect(self._open_admin)

        top.addWidget(lang_fr); top.addWidget(self.alert_btn)
        top.addWidget(self.refresh_btn); top.addWidget(self.admin_btn); top.addWidget(self.mode_btn)
        root.addLayout(top)

        # Summary cards
        cr = QHBoxLayout(); cr.setSpacing(12)
        self.c_tot = SummaryCard("card_total_products")
        self.c_unt = SummaryCard("card_total_units")
        self.c_low = SummaryCard("card_low_stock")
        self.c_out = SummaryCard("card_out_of_stock")
        self.c_val = SummaryCard("card_inventory_value")
        for c in (self.c_tot, self.c_unt, self.c_low, self.c_out, self.c_val): cr.addWidget(c)
        root.addLayout(cr)

        # Toolbar
        tb = QHBoxLayout(); tb.setSpacing(10)
        self.search = BarcodeLineEdit(); self.search.setObjectName("search_bar")
        self.search.setMinimumHeight(44)
        self.low_cb = QCheckBox(t("low_stock_only"))
        self.low_cb.stateChanged.connect(self._refresh_products)
        self.add_btn = QPushButton(t("btn_new_product")); self.add_btn.setObjectName("btn_primary")
        self.add_btn.clicked.connect(self._add_product)
        tb.addWidget(self.search, 1); tb.addWidget(self.low_cb); tb.addWidget(self.add_btn)
        root.addLayout(tb)

        # Splitter
        sp = QSplitter(Qt.Orientation.Horizontal); sp.setHandleWidth(1)

        # Left — tabs
        self.tabs = QTabWidget(); self.tabs.setObjectName("main_tabs")
        self.prod_tbl = ProductTable()
        self.tabs.addTab(self.prod_tbl, t("tab_products"))

        txn_pg = QWidget()
        tl = QVBoxLayout(txn_pg); tl.setContentsMargins(0, 8, 0, 0); tl.setSpacing(8)
        tbar = QHBoxLayout(); tbar.setContentsMargins(4, 0, 4, 0)
        self._txn_caption = QLabel(t("txn_history_caption")); self._txn_caption.setObjectName("section_caption")
        self._txn_ref_btn = QPushButton(); self._txn_ref_btn.setObjectName("btn_secondary")
        self._txn_ref_btn.setIcon(get_button_icon("refresh"))
        self._txn_ref_btn.setIconSize(QSize(16, 16))
        self._txn_ref_btn.clicked.connect(self._refresh_all_txns)
        tbar.addWidget(self._txn_caption); tbar.addStretch(); tbar.addWidget(self._txn_ref_btn)
        tl.addLayout(tbar)
        self.txn_tbl = TransactionTable(); tl.addWidget(self.txn_tbl)
        self.tabs.addTab(txn_pg, t("tab_transactions"))

        self._matrix_tabs: list[MatrixTab] = []
        for cat in _cat_repo.get_all_active():
            tab = MatrixTab(cat.key)
            self._matrix_tabs.append(tab)
            icon = load_svg_icon(cat.icon) if cat.icon else "📁"
            self.tabs.addTab(tab, f"{icon}  {cat.name('EN')}")

        sp.addWidget(self.tabs)

        # Right — detail
        rs = QScrollArea(); rs.setWidgetResizable(True)
        rs.setMinimumWidth(295); rs.setMaximumWidth(375)
        rs.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        rs.setObjectName("detail_scroll_area")
        self.detail = ProductDetail(); rs.setWidget(self.detail)
        sp.addWidget(rs)
        sp.setStretchFactor(0, 4); sp.setStretchFactor(1, 1)
        root.addWidget(sp, 1)

        self.status = QStatusBar(); self.setStatusBar(self.status)
        self.status.showMessage(t("statusbar_ready"))

    # ── Signals ────────────────────────────────────────────────────────────────

    def _connect(self):
        self.prod_tbl.row_selected.connect(self._sel)
        self.search.barcode_scanned.connect(self._barcode)
        self.search.textChanged.connect(
            lambda txt: self._refresh_products() if txt.strip() else None
        )
        self.detail.request_in.connect(lambda:  self._stock_op("IN"))
        self.detail.request_out.connect(lambda: self._stock_op("OUT"))
        self.detail.request_adj.connect(lambda: self._stock_op("ADJUST"))
        self.detail.request_edit.connect(self._edit)
        self.detail.request_del.connect(self._delete)

        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self._add_product)
        QShortcut(QKeySequence("F5"),     self).activated.connect(self._refresh_all)
        QShortcut(QKeySequence("Ctrl+I"), self).activated.connect(lambda: self._stock_op("IN"))
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(lambda: self._stock_op("OUT"))

    # ── Logo ───────────────────────────────────────────────────────────────────

    def _build_logo_label(self) -> QLabel | None:
        """Return a 36×36 QLabel with the shop logo, or None if not set/valid."""
        import os
        cfg = ShopConfig.get()
        path = cfg.logo_path
        if not path or not os.path.isfile(path):
            return None
        px = QPixmap(path)
        if px.isNull():
            return None
        lbl = QLabel()
        lbl.setPixmap(px.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation))
        lbl.setFixedSize(40, 40)
        return lbl

    def _reload_logo(self) -> None:
        """Remove old logo label and insert a fresh one after admin changes."""
        top_layout = self._title_lbl.parent().layout() if self._title_lbl.parent() else None
        if top_layout is None:
            return
        if self._logo_lbl is not None:
            top_layout.removeWidget(self._logo_lbl)
            self._logo_lbl.deleteLater()
            self._logo_lbl = None
        new_lbl = self._build_logo_label()
        if new_lbl:
            # Insert at position 0 (before title label)
            top_layout.insertWidget(0, new_lbl)
            self._logo_lbl = new_lbl

    # ── Admin / First-run ──────────────────────────────────────────────────────

    def _check_first_run(self) -> None:
        """Show setup wizard if setup_complete flag is absent."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM app_config WHERE key='setup_complete'"
            ).fetchone()
        if not row:
            wizard = SetupWizard(self)
            wizard.exec()
            ShopConfig.invalidate()
            ensure_matrix_entries()
            self._rebuild_matrix_tabs()
            self._retranslate()

    def _open_admin(self) -> None:
        open_admin(self)
        ShopConfig.invalidate()
        ensure_matrix_entries()
        self._rebuild_matrix_tabs()
        self._retranslate()

    def _rebuild_matrix_tabs(self) -> None:
        """Remove all matrix tabs and reload from active categories in DB."""
        while len(self._matrix_tabs) > 0:
            tab = self._matrix_tabs.pop()
            idx = self.tabs.indexOf(tab)
            if idx >= 0:
                self.tabs.removeTab(idx)
        for cat in _cat_repo.get_all_active():
            tab = MatrixTab(cat.key)
            self._matrix_tabs.append(tab)
            icon = load_svg_icon(cat.icon) if cat.icon else "📁"
            self.tabs.addTab(tab, f"{icon}  {cat.name(LANG)}")

    # ── Language ───────────────────────────────────────────────────────────────

    def _set_lang(self, lang: str):
        set_lang(lang)
        for code, btn in self._lang_btns.items():
            btn.setObjectName("lang_btn_active" if code == lang else "lang_btn")
            btn.style().unpolish(btn); btn.style().polish(btn)
        self._retranslate()

    def _retranslate(self):
        cfg = ShopConfig.get()
        _title = cfg.name if cfg.name else t("app_title")
        self.setWindowTitle(_title); self._title_lbl.setText(_title)
        self._reload_logo()
        self.refresh_btn.setToolTip(t("tooltip_refresh"))
        self.admin_btn.setToolTip(t("tooltip_admin"))
        self.mode_btn.setToolTip(t("tooltip_theme"))
        self.c_tot.retranslate(); self.c_unt.retranslate()
        self.c_low.retranslate(); self.c_out.retranslate(); self.c_val.retranslate()
        self.search.setPlaceholderText(t("search_placeholder"))
        self.low_cb.setText(t("low_stock_only"))
        self.add_btn.setText(t("btn_new_product"))
        self.tabs.setTabText(0, t("tab_products"))
        self.tabs.setTabText(1, t("tab_transactions"))
        for i, tab in enumerate(self._matrix_tabs):
            if tab._cat:
                icon = load_svg_icon(tab._cat.icon) if tab._cat.icon else "📁"
                self.tabs.setTabText(2 + i, f"{icon}  {tab._cat.name(LANG)}")
            tab.retranslate()
        self._txn_caption.setText(t("txn_history_caption"))
        # Transaction refresh button uses icon only - don't set text
        self.prod_tbl.retranslate(); self.txn_tbl.retranslate()
        self._refresh_products(); self._refresh_all_txns(); self._refresh_summary()
        self.detail.retranslate(); self._check_alerts()
        self.status.showMessage(t("statusbar_ready"))

    # ── Refresh ────────────────────────────────────────────────────────────────

    def _refresh_products(self):
        s     = self.search.text().strip()
        # Search for any text length, but only use search if length >= 2
        items = _item_repo.get_all_items(
            search=s if len(s) >= 2 else "",
            filter_low_stock=self.low_cb.isChecked(),
        )
        self.prod_tbl.load(items)
        self.status.showMessage(t("status_n_products", n=len(items)), 3000)

    def _refresh_summary(self):
        s = _item_repo.get_summary(); tk = THEME.tokens
        self.c_tot.set(s.get("total_products") or 0)
        self.c_unt.set(s.get("total_units") or 0, tk.green)
        low = s.get("low_stock_count") or 0
        out = s.get("out_of_stock_count") or 0
        self.c_low.set(low, tk.orange if low > 0 else tk.green)
        self.c_out.set(out, tk.red   if out > 0 else tk.green)
        val = s.get("inventory_value") or 0.0
        cfg = ShopConfig.get()
        self.c_val.set(cfg.format_currency(val), tk.blue)

    def _refresh_all_txns(self):
        self.txn_tbl.load(_txn_repo.get_transactions(limit=500))

    def _refresh_all(self):
        self.prod_tbl.reset_column_widths()  # Reset column widths to defaults
        self._refresh_products(); self._refresh_summary(); self._refresh_all_txns()
        if self._cp:
            self._cp = _item_repo.get_by_id(self._cp.id)
            self.detail.set_product(self._cp)
        self._check_alerts()
        self.status.showMessage(t("status_refreshed"), 2000)

    # ── Events ─────────────────────────────────────────────────────────────────

    def _sel(self, item: InventoryItem | None):
        self._cp = item
        self.detail.set_product(item)

    def _barcode(self, bc: str):
        item = _item_repo.get_by_barcode(bc)
        if item:
            self.prod_tbl.select_by_id(item.id); self._sel(item)
            self.status.showMessage(
                t("status_scanned", brand=item.display_name, type=""), 5000
            )
        else:
            self.status.showMessage(t("status_unknown_bc", bc=bc), 4000)
            if QMessageBox.question(
                self, t("msg_unknown_bc_title"), t("msg_unknown_bc_body", bc=bc),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            ) == QMessageBox.StandardButton.Yes:
                self._add_product(preset_barcode=bc)

    def _toggle_mode(self):
        THEME.toggle()
        # Theme button uses icon only - don't set text
        self._bg.update()
        self._refresh_products(); self._refresh_all_txns(); self._refresh_summary()
        if self._cp: self.detail.set_product(self._cp)
        self.prod_tbl.viewport().update(); self.txn_tbl.viewport().update()

    # ── CRUD ───────────────────────────────────────────────────────────────────

    def _add_product(self, checked=False, preset_barcode=""):
        dlg = ProductDialog(self)
        if preset_barcode: dlg.barcode_edit.setText(preset_barcode)
        if dlg.exec() != QDialog.DialogCode.Accepted: return
        data = dlg.get_data()
        try:
            pid = _item_repo.add_product(
                brand=data["brand"], name=data["type_"], color=data["color"],
                stock=data.get("stock", 0), barcode=data["barcode"],
                min_stock=data["low_stock_threshold"],
                sell_price=data.get("sell_price"),
            )
            self._refresh_products(); self._refresh_summary(); self._refresh_all_txns()
            self.prod_tbl.select_by_id(pid)
            self.status.showMessage(t("status_product_added", pid=pid), 4000)
        except Exception as e:
            QMessageBox.critical(self, t("msg_error"), str(e))

    def _edit(self):
        if not self._cp or not self._cp.is_product: return
        dlg = ProductDialog(self, product=_to_edit_dict(self._cp))
        if dlg.exec() != QDialog.DialogCode.Accepted: return
        data = dlg.get_data()
        try:
            _item_repo.update_product(
                item_id=self._cp.id,
                brand=data["brand"], name=data["type_"],
                color=data["color"], barcode=data["barcode"],
                min_stock=data["low_stock_threshold"],
                sell_price=data.get("sell_price"),
            )
            self._refresh_all()
            self.status.showMessage(t("status_product_updated"), 3000)
        except Exception as e:
            QMessageBox.critical(self, t("msg_error"), str(e))

    def _delete(self):
        if not self._cp or not self._cp.is_product: return
        item = self._cp; tk = THEME.tokens
        ans = QMessageBox.question(
            self, t("msg_delete_title"),
            t("msg_delete_body", brand=item.brand, type=item.name,
              color=item.color, red=tk.red),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes: return
        try:
            _item_repo.delete(item.id)
            self._cp = None; self.detail.set_product(None)
            self._refresh_all()
            self.status.showMessage(t("status_product_deleted"), 3000)
        except Exception as e:
            QMessageBox.critical(self, t("msg_error"), str(e))

    # ── Stock Operations ────────────────────────────────────────────────────────

    def _stock_op(self, op: str):
        if not self._cp: return
        item = _item_repo.get_by_id(self._cp.id)
        if item is None:
            QMessageBox.warning(self, t("msg_not_found_title"), t("msg_not_found_body")); return
        dlg = StockOpDialog(self, product=_to_op_dict(item), operation=op)
        if dlg.exec() != QDialog.DialogCode.Accepted: return
        data = dlg.get_data()
        try:
            if op == "IN":
                res = _stock_svc.stock_in(item.id, data["quantity"], data["note"])
            elif op == "OUT":
                res = _stock_svc.stock_out(item.id, data["quantity"], data["note"])
            else:
                res = _stock_svc.stock_adjust(item.id, data["quantity"], data["note"])

            self._refresh_all(); self._check_alerts()
            self.status.showMessage(
                t("status_stock_op", op=op, before=res["before"], after=res["after"]), 4000
            )
            updated = _item_repo.get_by_id(item.id)
            if updated and updated.stock <= updated.min_stock:
                level = t("msg_level_out") if updated.stock == 0 else t("msg_level_low")
                QMessageBox.warning(
                    self, t("msg_low_title", level=level),
                    t("msg_low_body", brand=updated.display_name, type="",
                      color="", stock=updated.stock, thr=updated.min_stock),
                )
        except ValueError as e:
            QMessageBox.warning(self, t("msg_op_failed"), str(e))
        except Exception as e:
            QMessageBox.critical(self, t("msg_error"), str(e))

    # ── Alerts ──────────────────────────────────────────────────────────────────

    def _check_alerts(self):
        low = _alert_svc.get_low_stock_items(); n = len(low)
        if n == 0:
            self.alert_btn.setText(t("alert_ok")); self.alert_btn.setObjectName("alert_ok")
        elif any(p.is_out for p in low):
            s = "s" if n > 1 else ""
            self.alert_btn.setText(t("alert_critical", n=n, s=s))
            self.alert_btn.setObjectName("alert_critical")
        else:
            s = "s" if n > 1 else ""
            self.alert_btn.setText(t("alert_warn", n=n, s=s))
            self.alert_btn.setObjectName("alert_warn")
        self.alert_btn.style().unpolish(self.alert_btn)
        self.alert_btn.style().polish(self.alert_btn)

    def _show_alerts(self):
        if self._ld and self._ld.isVisible(): self._ld.raise_(); return
        self._ld = LowStockDialog(self)
        self._ld.product_selected.connect(
            lambda pid: (
                self.prod_tbl.select_by_id(pid),
                self._sel(_item_repo.get_by_id(pid)),
            )
        )
        self._ld.show()
