"""
main_window.py — Stock Manager Pro v2
Professional sidebar layout, gradient dark/light, i18n (EN/DE/AR).
Sidebar navigation, summary cards in inventory only, quick scan mode.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QLineEdit,
    QPushButton, QFrame, QStatusBar, QScrollArea, QCheckBox,
    QTabWidget, QMessageBox, QDialog, QSizePolicy,
    QStyle, QStyleOptionViewItem, QStyledItemDelegate,
    QStackedWidget, QComboBox, QSpinBox,
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
        if len(self._buf) >= 3:
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
        lay = QVBoxLayout(self); lay.setContentsMargins(14, 12, 14, 12); lay.setSpacing(2)
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
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            if option.state & QStyle.StateFlag.State_Selected:
                painter.fillRect(option.rect, qc(THEME.tokens.blue, 0x40))
            elif index.row() % 2 == 0:
                painter.fillRect(option.rect, QColor(THEME.tokens.card))
            else:
                painter.fillRect(option.rect, QColor("#2C304C" if THEME.is_dark else "#E4E2F4"))
            painter.setPen(QColor(128, 128, 128))
            painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, "—")
            painter.restore()
            return

        hex_color = PALETTE.get(color_name, color_name)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tk = THEME.tokens
        alt = "#2C304C" if THEME.is_dark else "#E4E2F4"

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, qc(tk.blue, 0x40))
        elif index.row() % 2 == 0:
            painter.fillRect(option.rect, QColor(tk.card))
        else:
            painter.fillRect(option.rect, QColor(alt))

        rect = option.rect
        R = 9
        cx = rect.center().x()
        cy = rect.center().y()
        painter.setBrush(QColor(tk.border2))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx-R-1, cy-R-1, 2*R+2, 2*R+2)
        painter.setBrush(QColor(hex_color))
        painter.drawEllipse(cx-R, cy-R, 2*R, 2*R)
        painter.restore()

class DifferenceDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()
        tk = THEME.tokens
        alt = "#2C304C" if THEME.is_dark else "#E4E2F4"
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, qc(tk.blue, 0x40))
        elif index.row() % 2 == 0:
            painter.fillRect(option.rect, QColor(tk.card))
        else:
            painter.fillRect(option.rect, QColor(alt))

        item = self.parent().item(index.row(), index.column())
        if item:
            text = item.text()
            if text and text != "—":
                painter.setPen(item.foreground().color())
                font = QFont("Segoe UI", 10, QFont.Weight.Bold)
                painter.setFont(font)
                painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, text)
            else:
                painter.setPen(QColor(128, 128, 128))
                painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, "—")
        painter.restore()

# ── Product Table ──────────────────────────────────────────────────────────────

class ProductTable(QTableWidget):
    row_selected = pyqtSignal(object)
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
        self.setAlternatingRowColors(False); self.setSortingEnabled(True)
        self.setShowGrid(True)
        self.verticalHeader().setVisible(False); self.setShowGrid(False)
        self.setItemDelegateForColumn(0, AlternatingRowDelegate(self))
        self.setItemDelegateForColumn(1, AlternatingRowDelegate(self))
        self.setItemDelegateForColumn(2, ColorDotDelegate(self))
        self.setItemDelegateForColumn(3, AlternatingRowDelegate(self))
        self.setItemDelegateForColumn(4, AlternatingRowDelegate(self))
        self.setItemDelegateForColumn(5, AlternatingRowDelegate(self))
        self.setItemDelegateForColumn(6, AlternatingRowDelegate(self))
        self.setItemDelegateForColumn(7, DifferenceDelegate(self))
        self.setItemDelegateForColumn(8, StatusBadgeDelegate(self))
        self._data: list[InventoryItem] = []
        self.itemSelectionChanged.connect(self._emit)
        self._default_widths = self._WIDTHS.copy()

    def retranslate(self):
        self.setHorizontalHeaderLabels([t(k) for k in self._COL_KEYS])

    def reset_column_widths(self):
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
                if j == 5:
                    it.setForeground(sc)
                    it.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
                elif j == 7:
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


# ── Quick Scan Tab ────────────────────────────────────────────────────────────

class QuickScanTab(QWidget):
    """Fast barcode scanning for instant stock takeout."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scan_count = 0
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # Title
        title = QLabel(t("qscan_title"))
        title.setObjectName("dlg_header")
        root.addWidget(title)

        hint = QLabel(t("qscan_hint"))
        hint.setObjectName("section_caption")
        root.addWidget(hint)

        # Scan input — large and prominent
        self._scan_input = BarcodeLineEdit()
        self._scan_input.setObjectName("search_bar")
        self._scan_input.setPlaceholderText(t("qscan_scan_field"))
        self._scan_input.setMinimumHeight(56)
        self._scan_input.setFont(QFont("Segoe UI", 14))
        self._scan_input.barcode_scanned.connect(self._on_scan)
        root.addWidget(self._scan_input)

        # Counter
        self._counter = QLabel(t("qscan_count", n=0))
        self._counter.setObjectName("card_label")
        root.addWidget(self._counter)

        # Feed header
        feed_hdr = QLabel(t("qscan_last_scans"))
        feed_hdr.setObjectName("detail_section_hdr")
        root.addWidget(feed_hdr)
        self._feed_hdr = feed_hdr

        # Scan feed
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setObjectName("txn_scroll_area")
        self._feed_widget = QWidget()
        self._feed_lay = QVBoxLayout(self._feed_widget)
        self._feed_lay.setContentsMargins(0, 0, 0, 0)
        self._feed_lay.setSpacing(6)
        self._feed_lay.addStretch()
        scroll.setWidget(self._feed_widget)
        root.addWidget(scroll, 1)

        self._feed_items: list[QFrame] = []

    def _on_scan(self, bc: str):
        item = _item_repo.get_by_barcode(bc)
        if not item:
            self._add_feed_item(t("qscan_not_found", bc=bc), "error")
            return
        if item.stock <= 0:
            self._add_feed_item(t("qscan_out_of_stock", name=item.display_name), "warn")
            return
        try:
            res = _stock_svc.stock_out(item.id, 1, "Quick Scan")
            self._scan_count += 1
            self._counter.setText(t("qscan_count", n=self._scan_count))
            self._add_feed_item(
                t("qscan_taken_out", name=item.display_name,
                  before=res["before"], after=res["after"]),
                "success"
            )
        except ValueError:
            self._add_feed_item(t("qscan_out_of_stock", name=item.display_name), "warn")

    def _add_feed_item(self, text: str, style: str):
        frame = QFrame()
        obj_map = {"success": "scan_feed_success", "error": "scan_feed_error", "warn": "scan_feed_warn"}
        frame.setObjectName(obj_map.get(style, "scan_feed_item"))
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(12, 8, 12, 8)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        tk = THEME.tokens
        color_map = {"success": tk.green, "error": tk.red, "warn": tk.orange}
        lbl.setStyleSheet(f"color:{color_map.get(style, tk.t1)}; font-size:10pt;")
        lay.addWidget(lbl)

        # Insert at top (before stretch)
        self._feed_lay.insertWidget(0, frame)
        self._feed_items.insert(0, frame)

        # Keep max 50 items
        while len(self._feed_items) > 50:
            old = self._feed_items.pop()
            self._feed_lay.removeWidget(old)
            old.deleteLater()

    def retranslate(self):
        self._counter.setText(t("qscan_count", n=self._scan_count))
        self._feed_hdr.setText(t("qscan_last_scans"))
        self._scan_input.setPlaceholderText(t("qscan_scan_field"))

    def focus_input(self):
        self._scan_input.setFocus()
        self._scan_input.clear()


# ── Stock Operations Tab ──────────────────────────────────────────────────────

class StockOpsTab(QWidget):
    """Professional stock operations panel with search, select, and operate."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_item: InventoryItem | None = None
        self._build()

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # Left — item list
        left = QVBoxLayout()
        left.setSpacing(8)

        title = QLabel(t("stockops_title"))
        title.setObjectName("dlg_header")
        left.addWidget(title)
        self._title_lbl = title

        self._search = BarcodeLineEdit()
        self._search.setObjectName("search_bar")
        self._search.setPlaceholderText(t("stockops_search"))
        self._search.setMinimumHeight(36)
        self._search.setMaximumHeight(36)
        self._search.textChanged.connect(self._filter)
        self._search.barcode_scanned.connect(self._on_barcode)
        left.addWidget(self._search)

        self._list = QTableWidget()
        self._list.setColumnCount(4)
        self._list.setHorizontalHeaderLabels([t("col_item"), t("col_barcode"), t("col_stock"), t("col_status")])
        hh = self._list.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self._list.setColumnWidth(1, 120)
        self._list.setColumnWidth(2, 70)
        self._list.setColumnWidth(3, 80)
        self._list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._list.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._list.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._list.verticalHeader().setVisible(False)
        self._list.setAlternatingRowColors(True)
        self._list.itemSelectionChanged.connect(self._on_select)
        left.addWidget(self._list, 1)
        self._items_data: list[InventoryItem] = []

        left_w = QWidget()
        left_w.setLayout(left)
        root.addWidget(left_w, 3)

        # Right — operations panel
        right = QVBoxLayout()
        right.setSpacing(12)
        right.setContentsMargins(0, 0, 0, 0)

        # Selected item card
        self._sel_card = QFrame()
        self._sel_card.setObjectName("stockops_selected")
        scl = QVBoxLayout(self._sel_card)
        scl.setContentsMargins(16, 14, 16, 14)
        scl.setSpacing(6)
        self._sel_name = QLabel(t("stockops_select_prompt"))
        self._sel_name.setObjectName("detail_product_name")
        self._sel_name.setWordWrap(True)
        self._sel_stock = QLabel("")
        self._sel_stock.setObjectName("big_stock")
        self._sel_stock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scl.addWidget(self._sel_name)
        scl.addWidget(self._sel_stock)
        right.addWidget(self._sel_card)

        # Operation buttons
        ops_card = QFrame()
        ops_card.setObjectName("stockops_card")
        ocl = QVBoxLayout(ops_card)
        ocl.setContentsMargins(16, 16, 16, 16)
        ocl.setSpacing(10)

        ops_hdr = QLabel(t("detail_operations"))
        ops_hdr.setObjectName("detail_section_hdr")
        ocl.addWidget(ops_hdr)
        self._ops_hdr = ops_hdr

        # Quantity
        qty_row = QHBoxLayout()
        qty_row.setSpacing(8)
        qty_lbl = QLabel(t("stockops_qty_label"))
        qty_lbl.setMinimumWidth(80)
        self._qty_lbl = qty_lbl
        self._qty_spin = QSpinBox()
        self._qty_spin.setMinimum(1)
        self._qty_spin.setMaximum(99999)
        self._qty_spin.setValue(1)
        self._qty_spin.setMinimumHeight(40)
        qty_row.addWidget(qty_lbl)
        qty_row.addWidget(self._qty_spin, 1)
        ocl.addLayout(qty_row)

        # Note
        note_lbl = QLabel(t("stockops_note_label"))
        self._note_lbl = note_lbl
        ocl.addWidget(note_lbl)
        self._note_edit = QLineEdit()
        self._note_edit.setPlaceholderText(t("op_note_ph"))
        ocl.addWidget(self._note_edit)

        # Buttons
        self._btn_in = QPushButton(t("btn_stock_in"))
        self._btn_in.setObjectName("op_in")
        self._btn_in.clicked.connect(lambda: self._do_op("IN"))

        self._btn_out = QPushButton(t("btn_stock_out"))
        self._btn_out.setObjectName("op_out")
        self._btn_out.clicked.connect(lambda: self._do_op("OUT"))

        self._btn_adj = QPushButton(t("btn_adjust"))
        self._btn_adj.setObjectName("op_adj")
        self._btn_adj.clicked.connect(lambda: self._do_op("ADJUST"))

        for b in (self._btn_in, self._btn_out, self._btn_adj):
            b.setEnabled(False)
            ocl.addWidget(b)

        right.addWidget(ops_card)

        # Recent ops for selected item
        self._txn_hdr = QLabel(t("detail_recent_txns"))
        self._txn_hdr.setObjectName("detail_section_hdr")
        right.addWidget(self._txn_hdr)

        txn_scroll = QScrollArea()
        txn_scroll.setWidgetResizable(True)
        txn_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        txn_scroll.setObjectName("txn_scroll_area")
        self._mini_txn = MiniTxnList()
        txn_scroll.setWidget(self._mini_txn)
        right.addWidget(txn_scroll, 1)

        right_w = QWidget()
        right_w.setLayout(right)
        root.addWidget(right_w, 2)

        self._load_items()

    def _load_items(self, search: str = ""):
        items = _item_repo.get_all_items(search=search if len(search) >= 2 else "")
        self._items_data = items
        self._list.setRowCount(len(items))
        tk = THEME.tokens
        for i, item in enumerate(items):
            name_it = QTableWidgetItem(item.display_name)
            name_it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self._list.setItem(i, 0, name_it)

            bc_it = QTableWidgetItem(item.barcode or "—")
            bc_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list.setItem(i, 1, bc_it)

            stk_it = QTableWidgetItem(str(item.stock))
            stk_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            sc = _sc(item.stock, item.min_stock)
            stk_it.setForeground(sc)
            stk_it.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self._list.setItem(i, 2, stk_it)

            sl = _sl(item.stock, item.min_stock)
            stat_it = QTableWidgetItem(sl)
            stat_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list.setItem(i, 3, stat_it)

            self._list.setRowHeight(i, 38)

    def _filter(self, text: str):
        self._load_items(text.strip())

    def _on_barcode(self, bc: str):
        item = _item_repo.get_by_barcode(bc)
        if item:
            self._select_item(item)
        else:
            self._search.setText(bc)

    def _on_select(self):
        row = self._list.currentRow()
        if 0 <= row < len(self._items_data):
            self._select_item(self._items_data[row])

    def _select_item(self, item: InventoryItem):
        self._selected_item = item
        self._sel_name.setText(f"<b>{item.display_name}</b>")
        tk = THEME.tokens
        sc = _sc(item.stock, item.min_stock)
        self._sel_stock.setText(str(item.stock))
        self._sel_stock.setStyleSheet(f"color:{sc.name()};")
        for b in (self._btn_in, self._btn_out, self._btn_adj):
            b.setEnabled(True)
        self._mini_txn.load(item.id)

    def _do_op(self, op: str):
        if not self._selected_item:
            return
        item = _item_repo.get_by_id(self._selected_item.id)
        if not item:
            QMessageBox.warning(self, t("msg_not_found_title"), t("msg_not_found_body"))
            return
        qty = self._qty_spin.value()
        note = self._note_edit.text().strip() or ""
        try:
            if op == "IN":
                res = _stock_svc.stock_in(item.id, qty, note)
            elif op == "OUT":
                res = _stock_svc.stock_out(item.id, qty, note)
            else:
                res = _stock_svc.stock_adjust(item.id, qty, note)

            # Refresh
            updated = _item_repo.get_by_id(item.id)
            if updated:
                self._select_item(updated)
            self._load_items(self._search.text().strip())
            self._note_edit.clear()
            self._qty_spin.setValue(1)
        except ValueError as e:
            QMessageBox.warning(self, t("msg_op_failed"), str(e))
        except Exception as e:
            QMessageBox.critical(self, t("msg_error"), str(e))

    def retranslate(self):
        self._title_lbl.setText(t("stockops_title"))
        self._search.setPlaceholderText(t("stockops_search"))
        self._list.setHorizontalHeaderLabels([t("col_item"), t("col_barcode"), t("col_stock"), t("col_status")])
        self._sel_name.setText(t("stockops_select_prompt") if not self._selected_item else f"<b>{self._selected_item.display_name}</b>")
        self._ops_hdr.setText(t("detail_operations"))
        self._qty_lbl.setText(t("stockops_qty_label"))
        self._note_lbl.setText(t("stockops_note_label"))
        self._note_edit.setPlaceholderText(t("op_note_ph"))
        self._btn_in.setText(t("btn_stock_in"))
        self._btn_out.setText(t("btn_stock_out"))
        self._btn_adj.setText(t("btn_adjust"))
        self._txn_hdr.setText(t("detail_recent_txns"))

    def refresh(self):
        self._load_items(self._search.text().strip())
        if self._selected_item:
            updated = _item_repo.get_by_id(self._selected_item.id)
            if updated:
                self._select_item(updated)


# ── Theme Toggle Widget ──────────────────────────────────────────────────────

class ThemeToggle(QFrame):
    """Professional dark/light toggle switch."""
    toggled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("theme_toggle")
        self.setFixedSize(56, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        tk = THEME.tokens

        # Track background
        track_color = QColor(tk.blue) if THEME.is_dark else QColor(tk.border2)
        p.setBrush(track_color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, self.width(), self.height(), 14, 14)

        # Knob
        knob_x = 30 if THEME.is_dark else 4
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(knob_x, 4, 20, 20)

        # Icon on knob
        p.setPen(QColor(tk.card if THEME.is_dark else tk.t2))
        f = QFont("Segoe UI", 8)
        p.setFont(f)
        icon = "🌙" if THEME.is_dark else "☀"
        p.drawText(knob_x, 4, 20, 20, Qt.AlignmentFlag.AlignCenter, icon)

        p.end()

    def mousePressEvent(self, event):
        self.toggled.emit()


# ── Main Window ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    # Sidebar page indices
    _PAGE_INVENTORY    = 0
    _PAGE_TRANSACTIONS = 1
    _PAGE_STOCK_OPS    = 2
    _PAGE_QUICK_SCAN   = 3
    _PAGE_MATRIX_START = 4  # dynamic matrix tabs start here

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

        QTimer.singleShot(100, self._check_first_run)

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QHBoxLayout(self._bg)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        sidebar.setMinimumHeight(600)
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(6, 12, 6, 12)
        sb_lay.setSpacing(4)

        # Logo + title
        cfg = ShopConfig.get()
        _title = cfg.name if cfg.name else t("app_title")
        self._logo_lbl = self._build_logo_label()
        if self._logo_lbl:
            logo_row = QHBoxLayout()
            logo_row.setContentsMargins(8, 4, 8, 8)
            logo_row.addWidget(self._logo_lbl)
            logo_row.addStretch()
            sb_lay.addLayout(logo_row)

        self._title_lbl = QLabel(_title)
        self._title_lbl.setStyleSheet("font-size:13pt; font-weight:800; padding:4px 10px 12px 10px;")
        self._title_lbl.setWordWrap(True)
        sb_lay.addWidget(self._title_lbl)

        # Nav separator
        sep1 = QFrame(); sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("color:rgba(128,128,128,40); margin:0 8px;")
        sb_lay.addWidget(sep1)

        # Navigation buttons
        self._nav_btns: list[QPushButton] = []
        self._nav_keys: list[str] = []
        nav_items = [
            ("nav_inventory",    "📦"),
            ("nav_transactions", "📋"),
            ("nav_stock_ops",    "⚙"),
            ("nav_quick_scan",   "⚡"),
        ]
        for key, icon in nav_items:
            btn = QPushButton(f"  {icon}   {t(key)}")
            btn.setObjectName("sidebar_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self._nav_to(k))
            sb_lay.addWidget(btn)
            self._nav_btns.append(btn)
            self._nav_keys.append(key)

        # Matrix category separator
        self._cat_sep = QFrame(); self._cat_sep.setFrameShape(QFrame.Shape.HLine)
        self._cat_sep.setStyleSheet("color:rgba(128,128,128,40); margin:4px 8px;")
        sb_lay.addWidget(self._cat_sep)

        # Dynamic category nav buttons
        self._cat_nav_btns: list[QPushButton] = []
        for cat in _cat_repo.get_all_active():
            icon = load_svg_icon(cat.icon) if cat.icon else "📁"
            btn = QPushButton(f"  {icon}   {cat.name(LANG)}")
            btn.setObjectName("sidebar_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=cat.key: self._nav_to(f"cat_{k}"))
            sb_lay.addWidget(btn)
            self._cat_nav_btns.append(btn)
            self._nav_btns.append(btn)
            self._nav_keys.append(f"cat_{cat.key}")

        sb_lay.addStretch()

        # Bottom: Alert
        self.alert_btn = QPushButton(t("alert_ok")); self.alert_btn.setObjectName("alert_ok")
        self.alert_btn.clicked.connect(self._show_alerts)
        sb_lay.addWidget(self.alert_btn)

        # Language switcher
        lang_fr = QFrame(); lang_fr.setObjectName("lang_bar")
        lang_lay = QHBoxLayout(lang_fr); lang_lay.setContentsMargins(3, 3, 3, 3); lang_lay.setSpacing(1)
        self._lang_btns: dict[str, QPushButton] = {}
        for code in ("EN", "DE", "AR"):
            b = QPushButton(code); b.setObjectName("lang_btn_active" if code == LANG else "lang_btn")
            b.setFixedSize(40, 30); b.clicked.connect(lambda _, c=code: self._set_lang(c))
            lang_lay.addWidget(b); self._lang_btns[code] = b
        sb_lay.addWidget(lang_fr)

        # Theme toggle + Admin
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)
        bottom_row.setContentsMargins(4, 8, 4, 0)

        self._theme_toggle = ThemeToggle()
        self._theme_toggle.toggled.connect(self._toggle_mode)
        self._theme_toggle.setToolTip(t("tooltip_theme"))
        bottom_row.addWidget(self._theme_toggle)

        bottom_row.addStretch()

        self.admin_btn = QPushButton()
        self.admin_btn.setObjectName("icon_btn")
        self.admin_btn.setFixedSize(36, 36)
        self.admin_btn.setIcon(get_button_icon("settings"))
        self.admin_btn.setIconSize(QSize(18, 18))
        self.admin_btn.setToolTip(t("tooltip_admin"))
        self.admin_btn.clicked.connect(self._open_admin)
        bottom_row.addWidget(self.admin_btn)

        sb_lay.addLayout(bottom_row)

        root.addWidget(sidebar)

        # ── Content area ─────────────────────────────────────────────────────
        content = QVBoxLayout()
        content.setContentsMargins(12, 12, 12, 12)
        content.setSpacing(8)

        # Top bar (minimal — refresh only)
        top = QHBoxLayout(); top.setSpacing(8)
        self.refresh_btn = QPushButton()
        self.refresh_btn.setObjectName("icon_btn")
        self.refresh_btn.setFixedSize(36, 36)
        self.refresh_btn.setIcon(get_button_icon("refresh"))
        self.refresh_btn.setIconSize(QSize(18, 18))
        self.refresh_btn.setToolTip(t("tooltip_refresh"))
        self.refresh_btn.clicked.connect(self._refresh_all)
        top.addStretch()
        top.addWidget(self.refresh_btn)
        content.addLayout(top)

        # Stacked content pages
        self._stack = QStackedWidget()

        # Page 0: Inventory (with summary cards + detail panel)
        inv_page = QWidget()
        inv_lay = QVBoxLayout(inv_page)
        inv_lay.setContentsMargins(0, 0, 0, 0)
        inv_lay.setSpacing(8)

        # Summary cards (only in inventory)
        cr = QHBoxLayout(); cr.setSpacing(8)
        self.c_tot = SummaryCard("card_total_products")
        self.c_unt = SummaryCard("card_total_units")
        self.c_low = SummaryCard("card_low_stock")
        self.c_out = SummaryCard("card_out_of_stock")
        self.c_val = SummaryCard("card_inventory_value")
        for c in (self.c_tot, self.c_unt, self.c_low, self.c_out, self.c_val): cr.addWidget(c)
        inv_lay.addLayout(cr)

        # Toolbar — smaller search
        tb = QHBoxLayout(); tb.setSpacing(8)
        self.search = BarcodeLineEdit(); self.search.setObjectName("search_bar")
        self.search.setMaximumWidth(350)
        self.search.setMinimumHeight(36)
        self.search.setMaximumHeight(36)
        self.low_cb = QCheckBox(t("low_stock_only"))
        self.low_cb.stateChanged.connect(self._refresh_products)
        self.add_btn = QPushButton(t("btn_new_product")); self.add_btn.setObjectName("btn_primary")
        self.add_btn.setMaximumHeight(36)
        self.add_btn.clicked.connect(self._add_product)
        tb.addWidget(self.search); tb.addWidget(self.low_cb); tb.addStretch(); tb.addWidget(self.add_btn)
        inv_lay.addLayout(tb)

        # Splitter: table + detail
        sp = QSplitter(Qt.Orientation.Horizontal); sp.setHandleWidth(1)
        self.prod_tbl = ProductTable()
        sp.addWidget(self.prod_tbl)

        rs = QScrollArea(); rs.setWidgetResizable(True)
        rs.setMinimumWidth(280); rs.setMaximumWidth(340)
        rs.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        rs.setObjectName("detail_scroll_area")
        self.detail = ProductDetail(); rs.setWidget(self.detail)
        sp.addWidget(rs)
        sp.setStretchFactor(0, 5); sp.setStretchFactor(1, 1)
        inv_lay.addWidget(sp, 1)

        self._stack.addWidget(inv_page)  # index 0

        # Page 1: Transactions
        txn_pg = QWidget()
        tl = QVBoxLayout(txn_pg); tl.setContentsMargins(0, 0, 0, 0); tl.setSpacing(8)
        tbar = QHBoxLayout(); tbar.setContentsMargins(0, 0, 0, 0)
        self._txn_caption = QLabel(t("txn_history_caption")); self._txn_caption.setObjectName("section_caption")
        self._txn_ref_btn = QPushButton(); self._txn_ref_btn.setObjectName("btn_secondary")
        self._txn_ref_btn.setIcon(get_button_icon("refresh"))
        self._txn_ref_btn.setIconSize(QSize(16, 16))
        self._txn_ref_btn.clicked.connect(self._refresh_all_txns)
        tbar.addWidget(self._txn_caption); tbar.addStretch(); tbar.addWidget(self._txn_ref_btn)
        tl.addLayout(tbar)
        self.txn_tbl = TransactionTable(); tl.addWidget(self.txn_tbl)
        self._stack.addWidget(txn_pg)  # index 1

        # Page 2: Stock Operations
        self._stock_ops_tab = StockOpsTab()
        self._stack.addWidget(self._stock_ops_tab)  # index 2

        # Page 3: Quick Scan
        self._quick_scan_tab = QuickScanTab()
        self._stack.addWidget(self._quick_scan_tab)  # index 3

        # Pages 4+: Dynamic matrix tabs
        self._matrix_tabs: list[MatrixTab] = []
        for cat in _cat_repo.get_all_active():
            tab = MatrixTab(cat.key)
            self._matrix_tabs.append(tab)
            self._stack.addWidget(tab)

        content.addWidget(self._stack, 1)

        content_w = QWidget()
        content_w.setLayout(content)
        root.addWidget(content_w, 1)

        self.status = QStatusBar(); self.setStatusBar(self.status)
        self.status.showMessage(t("statusbar_ready"))

        # Set initial active nav
        self._current_nav = "nav_inventory"
        self._update_nav_styles()

    # ── Navigation ────────────────────────────────────────────────────────────

    def _nav_to(self, key: str):
        self._current_nav = key
        self._update_nav_styles()

        if key == "nav_inventory":
            self._stack.setCurrentIndex(self._PAGE_INVENTORY)
        elif key == "nav_transactions":
            self._stack.setCurrentIndex(self._PAGE_TRANSACTIONS)
            self._refresh_all_txns()
        elif key == "nav_stock_ops":
            self._stack.setCurrentIndex(self._PAGE_STOCK_OPS)
            self._stock_ops_tab.refresh()
        elif key == "nav_quick_scan":
            self._stack.setCurrentIndex(self._PAGE_QUICK_SCAN)
            self._quick_scan_tab.focus_input()
        elif key.startswith("cat_"):
            cat_key = key[4:]
            for i, tab in enumerate(self._matrix_tabs):
                if tab._cat_key == cat_key:
                    self._stack.setCurrentIndex(self._PAGE_MATRIX_START + i)
                    tab.refresh()
                    break

    def _update_nav_styles(self):
        for btn, key in zip(self._nav_btns, self._nav_keys):
            if key == self._current_nav:
                btn.setObjectName("sidebar_btn_active")
            else:
                btn.setObjectName("sidebar_btn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

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
        # Find the sidebar layout and update logo
        pass  # Logo reloads on full retranslate

    # ── Admin / First-run ──────────────────────────────────────────────────────

    def _check_first_run(self) -> None:
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
        # Remove old matrix tabs from stack
        for tab in self._matrix_tabs:
            self._stack.removeWidget(tab)
            tab.deleteLater()
        self._matrix_tabs.clear()

        # Remove old category nav buttons
        for btn in self._cat_nav_btns:
            btn.deleteLater()
        # Remove those buttons from nav_btns/nav_keys too
        for btn in self._cat_nav_btns:
            if btn in self._nav_btns:
                idx = self._nav_btns.index(btn)
                self._nav_btns.pop(idx)
                self._nav_keys.pop(idx)
        self._cat_nav_btns.clear()

        # Find sidebar layout (parent of _cat_sep)
        sb_lay = self._cat_sep.parent().layout()
        # Find insert position (after _cat_sep)
        insert_idx = sb_lay.indexOf(self._cat_sep) + 1

        # Rebuild
        for cat in _cat_repo.get_all_active():
            icon = load_svg_icon(cat.icon) if cat.icon else "📁"
            btn = QPushButton(f"  {icon}   {cat.name(LANG)}")
            btn.setObjectName("sidebar_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=cat.key: self._nav_to(f"cat_{k}"))
            sb_lay.insertWidget(insert_idx, btn)
            insert_idx += 1
            self._cat_nav_btns.append(btn)
            self._nav_btns.append(btn)
            self._nav_keys.append(f"cat_{cat.key}")

            tab = MatrixTab(cat.key)
            self._matrix_tabs.append(tab)
            self._stack.addWidget(tab)

        self._update_nav_styles()

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
        self.refresh_btn.setToolTip(t("tooltip_refresh"))
        self.admin_btn.setToolTip(t("tooltip_admin"))
        self._theme_toggle.setToolTip(t("tooltip_theme"))

        # Summary cards
        self.c_tot.retranslate(); self.c_unt.retranslate()
        self.c_low.retranslate(); self.c_out.retranslate(); self.c_val.retranslate()

        # Inventory toolbar
        self.search.setPlaceholderText(t("search_placeholder"))
        self.low_cb.setText(t("low_stock_only"))
        self.add_btn.setText(t("btn_new_product"))

        # Sidebar nav buttons
        nav_items = [
            ("nav_inventory",    "📦"),
            ("nav_transactions", "📋"),
            ("nav_stock_ops",    "⚙"),
            ("nav_quick_scan",   "⚡"),
        ]
        for i, (key, icon) in enumerate(nav_items):
            if i < len(self._nav_btns):
                self._nav_btns[i].setText(f"  {icon}   {t(key)}")

        # Category nav buttons
        cats = _cat_repo.get_all_active()
        for i, btn in enumerate(self._cat_nav_btns):
            if i < len(cats):
                cat = cats[i]
                icon = load_svg_icon(cat.icon) if cat.icon else "📁"
                btn.setText(f"  {icon}   {cat.name(LANG)}")

        # Transaction page
        self._txn_caption.setText(t("txn_history_caption"))

        # Sub-tabs
        self.prod_tbl.retranslate(); self.txn_tbl.retranslate()
        self._stock_ops_tab.retranslate()
        self._quick_scan_tab.retranslate()
        for tab in self._matrix_tabs:
            tab.retranslate()

        self._refresh_products(); self._refresh_all_txns(); self._refresh_summary()
        self.detail.retranslate(); self._check_alerts()
        self.status.showMessage(t("statusbar_ready"))

    # ── Refresh ────────────────────────────────────────────────────────────────

    def _refresh_products(self):
        s     = self.search.text().strip()
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
        self.prod_tbl.reset_column_widths()
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
        self._theme_toggle.update()
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
