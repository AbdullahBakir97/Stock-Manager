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
from app.ui.pages.barcode_gen_page import BarcodeGenPage

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
        alt = THEME.tokens.card2

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
        alt = THEME.tokens.card2

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
        self.setMaximumHeight(88)
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
                painter.fillRect(option.rect, QColor(THEME.tokens.card2))
            painter.setPen(QColor(THEME.tokens.t4))
            painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, "—")
            painter.restore()
            return

        hex_color = PALETTE.get(color_name, color_name)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tk = THEME.tokens
        alt = THEME.tokens.card2

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
        alt = THEME.tokens.card2
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
                painter.setPen(QColor(THEME.tokens.t4))
                painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, "—")
        painter.restore()

# ── Product Table ──────────────────────────────────────────────────────────────

class ProductTable(QTableWidget):
    row_selected = pyqtSignal(object)
    _COL_KEYS = ["col_num", "col_item", "col_color", "col_barcode", "col_price",
                 "col_stock", "col_min", "col_best_bung", "col_status"]
    _WIDTHS    = [40, 200, 50, 100, 70, 60, 50, 80, 80]

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
        self.verticalHeader().setVisible(False); self.setShowGrid(False)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setVerticalScrollMode(self.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(self.ScrollMode.ScrollPerPixel)
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
            _mono = QFont("JetBrains Mono", 11, QFont.Weight.Bold)
            _mono.setStyleHint(QFont.StyleHint.Monospace)
            for j, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if j == 3:  # Barcode — monospace
                    it.setFont(QFont("JetBrains Mono", 10))
                elif j == 5:  # Stock — monospace bold colored
                    it.setForeground(sc)
                    it.setFont(_mono)
                elif j == 7:  # Difference — monospace bold colored
                    it.setForeground(sc)
                    it.setFont(_mono)
                self.setItem(i, j, it)
            self.setRowHeight(i, 48)
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
    _WIDTHS   = [140, 220, 90, 70, 70, 70, 160]

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
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setVerticalScrollMode(self.ScrollMode.ScrollPerPixel)

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
            _mono_d = QFont("JetBrains Mono", 11, QFont.Weight.Bold)
            _mono_d.setStyleHint(QFont.StyleHint.Monospace)
            for j, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if j == 0:  # Timestamp — monospace
                    it.setFont(QFont("JetBrains Mono", 10))
                elif j == 2:  # Operation — bold colored
                    it.setForeground(QColor(OP.get(op_key, tk.t3)))
                    it.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
                elif j == 3:  # Delta — monospace bold
                    it.setForeground(QColor(tk.green if d >= 0 else tk.red))
                    it.setFont(_mono_d)
                elif j in (4, 5):  # Before/After — monospace
                    it.setFont(QFont("JetBrains Mono", 10))
                self.setItem(i, j, it)
            self.setRowHeight(i, 48)


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
    """Barcode-driven Quick Scan with TAKEOUT/INSERT modes and pending list."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        from app.services.scan_session_service import ScanSessionService
        self._session = ScanSessionService()
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Top bar: title + settings
        top = QHBoxLayout()
        self._title = QLabel(t("qscan_title")); self._title.setObjectName("dlg_header")
        top.addWidget(self._title); top.addStretch()
        root.addLayout(top)

        # Mode indicator bar
        self._mode_bar = QFrame(); self._mode_bar.setObjectName("scan_mode_idle")
        mb_lay = QHBoxLayout(self._mode_bar); mb_lay.setContentsMargins(16, 10, 16, 10)
        self._mode_icon = QLabel(""); self._mode_icon.setFixedWidth(24)
        self._mode_label = QLabel(t("qscan_mode_idle"))
        self._mode_label.setStyleSheet("font-weight:600; font-size:13px;")
        self._cancel_session_btn = QPushButton(t("qscan_cancel_btn"))
        self._cancel_session_btn.setObjectName("btn_ghost")
        self._cancel_session_btn.setFixedHeight(30)
        self._cancel_session_btn.clicked.connect(self._cancel_session)
        self._cancel_session_btn.hide()
        mb_lay.addWidget(self._mode_icon); mb_lay.addWidget(self._mode_label)
        mb_lay.addStretch(); mb_lay.addWidget(self._cancel_session_btn)
        root.addWidget(self._mode_bar)

        # Scan input
        self._scan_input = BarcodeLineEdit()
        self._scan_input.setObjectName("search_bar")
        self._scan_input.setPlaceholderText(t("qscan_scan_field"))
        self._scan_input.setMinimumHeight(52)
        self._scan_input.setFont(QFont("Segoe UI", 14))
        self._scan_input.barcode_scanned.connect(self._on_scan)
        root.addWidget(self._scan_input)

        # Pending table header
        self._pending_hdr = QLabel(t("qscan_pending_hdr", n=0))
        self._pending_hdr.setObjectName("detail_section_hdr")
        root.addWidget(self._pending_hdr)

        # Pending table
        self._pending_tbl = QTableWidget()
        self._pending_tbl.setColumnCount(6)
        self._pending_tbl.setHorizontalHeaderLabels(["#", t("col_item"), t("col_barcode"), "Qty", "After", ""])
        hh = self._pending_tbl.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._pending_tbl.setColumnWidth(0, 30)
        self._pending_tbl.setColumnWidth(2, 100)
        self._pending_tbl.setColumnWidth(3, 45)
        self._pending_tbl.setColumnWidth(4, 55)
        self._pending_tbl.setColumnWidth(5, 30)
        self._pending_tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._pending_tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._pending_tbl.verticalHeader().setVisible(False)
        self._pending_tbl.setAlternatingRowColors(True)
        self._pending_tbl.setShowGrid(False)
        root.addWidget(self._pending_tbl, 1)

        # Action bar: summary + cancel + confirm
        action = QHBoxLayout(); action.setSpacing(8)
        self._summary_lbl = QLabel("")
        self._summary_lbl.setObjectName("section_caption")
        action.addWidget(self._summary_lbl); action.addStretch()
        self._btn_cancel = QPushButton(t("qscan_cancel_btn"))
        self._btn_cancel.setObjectName("btn_ghost"); self._btn_cancel.setFixedHeight(36)
        self._btn_cancel.clicked.connect(self._cancel_session)
        self._btn_confirm = QPushButton(t("qscan_confirm_btn"))
        self._btn_confirm.setObjectName("btn_primary"); self._btn_confirm.setFixedHeight(36)
        self._btn_confirm.clicked.connect(self._confirm_session)
        action.addWidget(self._btn_cancel); action.addWidget(self._btn_confirm)
        root.addLayout(action)

        # Recent sessions feed (scrollable)
        self._recent_section = CollapsibleSection(t("qscan_recent"))
        recent_scroll = QScrollArea()
        recent_scroll.setWidgetResizable(True)
        recent_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        recent_scroll.setFrameShape(QFrame.Shape.NoFrame)
        recent_inner = QWidget()
        self._recent_lay = QVBoxLayout(recent_inner)
        self._recent_lay.setContentsMargins(0, 0, 0, 0)
        self._recent_lay.setSpacing(4)
        self._recent_lay.addStretch()
        recent_scroll.setWidget(recent_inner)
        self._recent_section.add_widget(recent_scroll)
        root.addWidget(self._recent_section, 1)
        self._feed_items: list[QFrame] = []

        self._update_ui()

    def process_command_barcode(self, bc: str):
        """Called from header/global scanner when a command barcode is detected."""
        self._on_scan(bc)

    def _update_ui(self):
        """Update mode bar, pending table, and button states."""
        mode = self._session.mode
        tk = THEME.tokens

        if mode == "TAKEOUT":
            self._mode_bar.setObjectName("scan_mode_takeout")
            self._mode_icon.setText("↓")
            self._mode_icon.setStyleSheet(f"color:{tk.red}; font-size:18px; font-weight:700;")
            self._mode_label.setText(t("qscan_mode_takeout"))
            self._mode_label.setStyleSheet(f"color:{tk.red}; font-weight:600; font-size:13px;")
            self._cancel_session_btn.show()
        elif mode == "INSERT":
            self._mode_bar.setObjectName("scan_mode_insert")
            self._mode_icon.setText("↑")
            self._mode_icon.setStyleSheet(f"color:{tk.green}; font-size:18px; font-weight:700;")
            self._mode_label.setText(t("qscan_mode_insert"))
            self._mode_label.setStyleSheet(f"color:{tk.green}; font-weight:600; font-size:13px;")
            self._cancel_session_btn.show()
        else:
            self._mode_bar.setObjectName("scan_mode_idle")
            self._mode_icon.setText("")
            self._mode_label.setText(t("qscan_mode_idle"))
            self._mode_label.setStyleSheet(f"color:{tk.t3}; font-weight:600; font-size:13px;")
            self._cancel_session_btn.hide()

        self._mode_bar.style().unpolish(self._mode_bar)
        self._mode_bar.style().polish(self._mode_bar)
        self._refresh_pending()

    def _cancel_session(self):
        """Cancel current scan session."""
        self._session.cancel()
        self._update_ui()

    def _confirm_session(self):
        """Confirm and commit current scan session."""
        from app.models.scan_session import ScanEventType
        event = self._session.commit()
        if event.event_type == ScanEventType.BATCH_COMMITTED:
            self._add_feed_item(event.message, "success")
        self._update_ui()

    def _refresh_pending(self):
        """Rebuild the pending table from session state."""
        items = self._session.pending_items
        tk = THEME.tokens
        self._pending_hdr.setText(t("qscan_pending_hdr", n=len(items)))
        self._pending_tbl.setRowCount(len(items))

        for i, p in enumerate(items):
            row_color = tk.red if self._session.mode == "TAKEOUT" else tk.green

            # #
            num_it = QTableWidgetItem(str(i + 1))
            num_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._pending_tbl.setItem(i, 0, num_it)

            # Item name
            name_it = QTableWidgetItem(p.item.display_name)
            name_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._pending_tbl.setItem(i, 1, name_it)

            # Barcode
            bc_it = QTableWidgetItem(p.item.barcode or "—")
            bc_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._pending_tbl.setItem(i, 2, bc_it)

            # Qty
            qty_it = QTableWidgetItem(str(p.quantity))
            qty_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            qty_it.setFont(QFont("JetBrains Mono", 11, QFont.Weight.Bold))
            qty_it.setForeground(QColor(row_color))
            self._pending_tbl.setItem(i, 3, qty_it)

            # After
            after_it = QTableWidgetItem(str(p.predicted_after))
            after_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            after_it.setFont(QFont("JetBrains Mono", 11))
            after_it.setForeground(QColor(tk.red) if p.predicted_after <= 0 else QColor(tk.t2))
            self._pending_tbl.setItem(i, 4, after_it)

            # Remove button — QToolButton to avoid QPushButton QSS conflicts
            from PyQt6.QtWidgets import QToolButton
            rm_btn = QToolButton()
            rm_btn.setText("×")
            rm_btn.setFixedSize(24, 24)
            rm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            rm_btn.setStyleSheet(
                f"QToolButton {{ color:{tk.red}; background:transparent; border:none;"
                f"  font-weight:700; font-size:13px; }}"
                f"QToolButton:hover {{ background:{_rgba(tk.red, '20')}; border-radius:4px; }}"
            )
            rm_btn.clicked.connect(lambda _=False, idx=i: self._remove_pending(idx))
            self._pending_tbl.setCellWidget(i, 5, rm_btn)

            self._pending_tbl.setRowHeight(i, 40)

        total_qty = self._session.pending_count
        total_items = self._session.pending_item_count
        self._summary_lbl.setText(
            t("qscan_total_summary", ops=total_qty, items=total_items) if total_items else ""
        )
        has_pending = total_items > 0
        self._btn_cancel.setEnabled(has_pending or self._session.mode is not None)
        self._btn_confirm.setEnabled(has_pending)

    def _remove_pending(self, index: int):
        """Remove an item from the pending list by index."""
        self._session.remove_pending(index)
        self._refresh_pending()
        self._scan_input.setFocus()

    def _add_feed_item(self, text: str, style: str):
        frame = QFrame()
        obj_map = {"success": "scan_feed_success", "error": "scan_feed_error", "warn": "scan_feed_warn"}
        frame.setObjectName(obj_map.get(style, "scan_feed_item"))
        lay = QHBoxLayout(frame); lay.setContentsMargins(12, 8, 12, 8)
        lbl = QLabel(text); lbl.setWordWrap(True)
        tk = THEME.tokens
        color_map = {"success": tk.green, "error": tk.red, "warn": tk.orange}
        lbl.setStyleSheet(f"color:{color_map.get(style, tk.t1)}; font-size:12px;")
        lay.addWidget(lbl)
        # Insert at top of scrollable feed
        self._recent_lay.insertWidget(0, frame)
        self._feed_items.insert(0, frame)
        while len(self._feed_items) > 50:
            old = self._feed_items.pop()
            self._recent_lay.removeWidget(old)
            old.deleteLater()

    def retranslate(self):
        self._title.setText(t("qscan_title"))
        self._scan_input.setPlaceholderText(t("qscan_scan_field"))
        self._btn_cancel.setText(t("qscan_cancel_btn"))
        self._btn_confirm.setText(t("qscan_confirm_btn"))
        self._cancel_session_btn.setText(t("qscan_cancel_btn"))
        self._update_ui()

    def _on_scan(self, bc: str):
        """Handle barcode scan in Quick Scan tab."""
        from app.models.scan_session import ScanEventType
        event = self._session.process_barcode(bc)

        if event.event_type == ScanEventType.MODE_CHANGED:
            self._update_ui()
        elif event.event_type in (ScanEventType.ITEM_ADDED, ScanEventType.ITEM_INCREMENTED):
            self._refresh_pending()
        elif event.event_type == ScanEventType.BATCH_COMMITTED:
            self._add_feed_item(event.message, "success")
            self._update_ui()
        elif event.event_type == ScanEventType.BATCH_EMPTY:
            self._add_feed_item(event.message, "warn")
        elif event.event_type == ScanEventType.NOT_FOUND:
            self._add_feed_item(event.message, "error")
        elif event.event_type == ScanEventType.NO_MODE:
            self._add_feed_item(event.message, "warn")
        elif event.event_type == ScanEventType.INSUFFICIENT_STOCK:
            self._add_feed_item(event.message, "warn")
        elif event.event_type == ScanEventType.SESSION_ACTIVE:
            self._add_feed_item(event.message, "warn")

        # Keep focus on scan input
        self._scan_input.clear()
        self._scan_input.setFocus()

    def focus_input(self):
        self._scan_input.setFocus()
        self._scan_input.clear()


# ── Stock Operations Tab ──────────────────────────────────────────────────────

class StockOpsTab(QWidget):
    """Professional stock operations panel with search, select, and operate."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._selected_item: InventoryItem | None = None
        self._build()

    def _build(self):
        from app.ui.dialogs.product_dialogs import QuantitySpin

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(0)

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
        self._list.setColumnWidth(1, 100)
        self._list.setColumnWidth(2, 60)
        self._list.setColumnWidth(3, 70)
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

        # Right — scrollable operations panel
        right_inner = QWidget()
        right = QVBoxLayout(right_inner)
        right.setSpacing(12)
        right.setContentsMargins(12, 0, 0, 0)

        # Selected item card — full product info
        self._sel_card = QFrame()
        self._sel_card.setObjectName("detail_card")
        scl = QVBoxLayout(self._sel_card)
        scl.setContentsMargins(16, 14, 16, 14)
        scl.setSpacing(6)
        self._sel_name = QLabel(t("stockops_select_prompt"))
        self._sel_name.setObjectName("detail_product_name")
        self._sel_name.setWordWrap(True)
        scl.addWidget(self._sel_name)
        # Color dot + color name
        cr = QHBoxLayout(); cr.setSpacing(8)
        self._sel_dot = QLabel(); self._sel_dot.setFixedSize(16, 16)
        self._sel_color_name = QLabel(""); self._sel_color_name.setObjectName("detail_color_name")
        cr.addWidget(self._sel_dot); cr.addWidget(self._sel_color_name); cr.addStretch()
        scl.addLayout(cr)
        # Barcode + price
        self._sel_barcode = QLabel("")
        self._sel_barcode.setObjectName("detail_barcode")
        scl.addWidget(self._sel_barcode)
        self._sel_price = QLabel("")
        self._sel_price.setObjectName("detail_barcode")
        scl.addWidget(self._sel_price)
        # Stock display
        self._sel_stock = QLabel("")
        self._sel_stock.setObjectName("big_stock")
        self._sel_stock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scl.addWidget(self._sel_stock)
        # Status badge + threshold + difference
        self._sel_badge = QLabel("")
        self._sel_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scl.addWidget(self._sel_badge)
        self._sel_info = QLabel("")
        self._sel_info.setObjectName("detail_threshold")
        self._sel_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scl.addWidget(self._sel_info)
        right.addWidget(self._sel_card)

        # Operation card
        ops_card = QFrame()
        ops_card.setObjectName("stockops_card")
        ocl = QVBoxLayout(ops_card)
        ocl.setContentsMargins(16, 16, 16, 16)
        ocl.setSpacing(10)

        ops_hdr = QLabel(t("detail_operations"))
        ops_hdr.setObjectName("detail_section_hdr")
        ocl.addWidget(ops_hdr)
        self._ops_hdr = ops_hdr

        # Quantity — use QuantitySpin (proper +/− buttons)
        qty_row = QHBoxLayout(); qty_row.setSpacing(8)
        qty_lbl = QLabel(t("stockops_qty_label"))
        self._qty_lbl = qty_lbl
        self._qty_spin = QuantitySpin(1, 99999, 1)
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

        # Operation buttons
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

        # Recent transactions
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

        # Wrap right panel in scroll area
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setWidget(right_inner)

        # Splitter: left list + right detail (hideable by dragging)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.addWidget(left_w)
        splitter.addWidget(right_scroll)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([600, 350])
        root.addWidget(splitter, 1)

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
            stk_it.setFont(QFont("JetBrains Mono", 10, QFont.Weight.Bold))
            self._list.setItem(i, 2, stk_it)

            sl = _sl(item.stock, item.min_stock)
            sl_labels = {"OK": t("status_ok_lbl"), "LOW": t("status_low_lbl"),
                         "CRITICAL": t("status_critical_lbl"), "OUT": t("status_out_lbl")}
            stat_it = QTableWidgetItem(sl_labels.get(sl, sl))
            stat_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            stat_it.setForeground(sc)
            stat_it.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
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
        tk = THEME.tokens
        sc = _sc(item.stock, item.min_stock)
        sl = _sl(item.stock, item.min_stock)

        # Name
        self._sel_name.setText(f"<b>{item.display_name}</b>")

        # Color dot
        if item.is_product and item.color:
            hc = clr.hex_for(item.color)
            brd = "rgba(102,102,102,153)" if clr.is_light(hc) else "transparent"
            self._sel_dot.setStyleSheet(f"background:{hc}; border-radius:8px; border:1px solid {brd};")
            self._sel_color_name.setText(color_t(item.color))
        elif item.part_type_color:
            hc = item.part_type_color
            self._sel_dot.setStyleSheet(f"background:{hc}; border-radius:8px;")
            self._sel_color_name.setText(item.part_type_name or "")
        else:
            self._sel_dot.setStyleSheet("")
            self._sel_color_name.setText("")

        # Barcode + Price
        self._sel_barcode.setText(
            t("detail_barcode", val=item.barcode or t("dlg_color_none"))
        )
        cfg = ShopConfig.get()
        price_display = cfg.format_currency(item.sell_price) if item.sell_price else "—"
        self._sel_price.setText(t("detail_sell_price", val=price_display))

        # Stock number (big, colored)
        self._sel_stock.setText(str(item.stock))
        self._sel_stock.setStyleSheet(f"color:{sc.name()};")

        # Status badge
        badge_map = {
            "OK":       (tk.green,  _rgba(tk.green,  "28")),
            "LOW":      (tk.yellow, _rgba(tk.yellow, "30")),
            "CRITICAL": (tk.orange, _rgba(tk.orange, "28")),
            "OUT":      (tk.red,    _rgba(tk.red,    "28")),
        }
        badge_labels = {
            "OK": t("badge_ok"), "LOW": t("badge_low"),
            "CRITICAL": t("badge_critical"), "OUT": t("badge_out"),
        }
        fg, bg = badge_map.get(sl, (tk.t3, tk.border))
        self._sel_badge.setText(badge_labels.get(sl, sl))
        self._sel_badge.setStyleSheet(
            f"color:{fg}; background:{bg}; border:1px solid {_rgba(fg, '40')};"
            "border-radius:10px; font-weight:800; font-size:9pt; padding:5px 14px;"
        )

        # Threshold + difference
        diff = item.stock - item.min_stock
        diff_str = f"Δ{diff:+d}" if item.min_stock > 0 else ""
        self._sel_info.setText(
            f"{t('detail_alert_at', n=item.min_stock)}   {diff_str}"
        )

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

class ThemeToggle(QWidget):
    """Animated sliding toggle with sun/moon icons. Click = toggle, right-click = cycle."""
    theme_toggled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(52, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(t("tooltip_theme"))
        self._knob_x = self._target_x()
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(12)
        self._anim_timer.timeout.connect(self._animate_step)

    def _target_x(self) -> float:
        return float(self.width() - self.height() + 2) if THEME.is_dark else 2.0

    def _animate_step(self):
        target = self._target_x()
        diff = target - self._knob_x
        if abs(diff) < 0.5:
            self._knob_x = target
            self._anim_timer.stop()
        else:
            self._knob_x += diff * 0.25
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        knob_d = h - 4

        # Track — indigo for dark, light gray for light
        track_col = QColor("#334155") if THEME.is_dark else QColor("#CBD5E1")
        p.setBrush(track_col)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, w, h, h // 2, h // 2)

        # Stars dots in dark side (left when light mode, right when dark)
        if THEME.is_dark:
            p.setBrush(QColor(255, 255, 255, 40))
            p.drawEllipse(8, 7, 3, 3)
            p.drawEllipse(14, 14, 2, 2)
            p.drawEllipse(11, 19, 2, 2)
        else:
            # Sun rays hint on right side
            p.setBrush(QColor(251, 191, 36, 50))
            p.drawEllipse(34, 8, 3, 3)
            p.drawEllipse(38, 15, 2, 2)
            p.drawEllipse(32, 18, 2, 2)

        # Knob
        kx = int(self._knob_x)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(kx, 2, knob_d, knob_d)

        # Icon on knob
        icon_font = QFont("Segoe UI", 11)
        p.setFont(icon_font)
        if THEME.is_dark:
            p.setPen(QColor("#1E293B"))
            p.drawText(kx, 2, knob_d, knob_d, Qt.AlignmentFlag.AlignCenter, "🌙")
        else:
            p.setPen(QColor("#92400E"))
            p.drawText(kx, 2, knob_d, knob_d, Qt.AlignmentFlag.AlignCenter, "☀")

        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            THEME.cycle()
        else:
            THEME.toggle()
        self._anim_timer.start()
        self.theme_toggled.emit()

    def _update_text(self):
        self._knob_x = self._target_x()
        self.update()


class CollapsibleSection(QWidget):
    """A section with a clickable header that shows/hides its content."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._expanded = True
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Header button
        self._header = QPushButton(f"  ▾  {title}")
        self._header.setObjectName("sidebar_section_toggle")
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.clicked.connect(self._toggle)
        lay.addWidget(self._header)

        # Content container
        self._content = QWidget()
        self._content_lay = QVBoxLayout(self._content)
        self._content_lay.setContentsMargins(0, 2, 0, 0)
        self._content_lay.setSpacing(2)
        lay.addWidget(self._content)

        self._title = title

    def add_widget(self, w: QWidget):
        self._content_lay.addWidget(w)

    def _toggle(self):
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        arrow = "▾" if self._expanded else "▸"
        self._header.setText(f"  {arrow}  {self._title}")

    def set_title(self, title: str):
        self._title = title
        arrow = "▾" if self._expanded else "▸"
        self._header.setText(f"  {arrow}  {title}")


# ── Main Window ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    # Sidebar page indices
    _PAGE_INVENTORY    = 0
    _PAGE_TRANSACTIONS = 1
    _PAGE_STOCK_OPS    = 2
    _PAGE_QUICK_SCAN   = 3
    _PAGE_BARCODE_GEN  = 4
    _PAGE_MATRIX_START = 5  # dynamic matrix tabs start here

    def __init__(self):
        super().__init__()
        init_db()
        cfg = ShopConfig.get()

        # Apply saved theme
        saved_theme = cfg.theme
        if saved_theme in ("pro_dark", "pro_light", "dark", "light"):
            THEME.set_theme(saved_theme)

        _title = cfg.name if cfg.name else t("app_title")
        self.setWindowTitle(_title); self.resize(1280, 800)
        self.setMinimumSize(800, 500)
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
        outer = QVBoxLayout(self._bg)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ══════════════════════════════════════════════════════════════════════
        # HEADER BAR (56px) — Logo, Title, Search, Notifications, Settings
        # ══════════════════════════════════════════════════════════════════════
        header = QFrame()
        header.setObjectName("header_bar")
        header.setFixedHeight(56)
        header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        hdr_lay = QHBoxLayout(header)
        hdr_lay.setContentsMargins(16, 0, 16, 0)
        hdr_lay.setSpacing(0)

        # Left group: hamburger + logo + title
        left_hdr = QHBoxLayout(); left_hdr.setSpacing(8)
        cfg = ShopConfig.get()
        _title = cfg.name if cfg.name else t("app_title")

        # Sidebar toggle (hamburger)
        self._sidebar_toggle = QPushButton("☰")
        self._sidebar_toggle.setObjectName("header_icon")
        self._sidebar_toggle.setFixedSize(34, 34)
        self._sidebar_toggle.setToolTip("Toggle sidebar")
        self._sidebar_toggle.clicked.connect(self._toggle_sidebar)
        left_hdr.addWidget(self._sidebar_toggle)

        self._logo_lbl = self._build_logo_label()
        if self._logo_lbl:
            left_hdr.addWidget(self._logo_lbl)
        self._title_lbl = QLabel(_title)
        self._title_lbl.setObjectName("app_title")
        left_hdr.addWidget(self._title_lbl)
        hdr_lay.addLayout(left_hdr)

        hdr_lay.addStretch()

        # Center: search
        self.search = BarcodeLineEdit(); self.search.setObjectName("search_bar")
        self.search.setFixedWidth(260)
        self.search.setFixedHeight(34)
        hdr_lay.addWidget(self.search)

        hdr_lay.addSpacing(12)

        # Right actions
        right_hdr = QHBoxLayout(); right_hdr.setSpacing(8)

        # Language switcher (compact, in header)
        lang_fr = QFrame(); lang_fr.setObjectName("lang_bar")
        lang_lay = QHBoxLayout(lang_fr)
        lang_lay.setContentsMargins(2, 2, 2, 2); lang_lay.setSpacing(1)
        self._lang_btns: dict[str, QPushButton] = {}
        for code in ("EN", "DE", "AR"):
            b = QPushButton(code)
            b.setObjectName("lang_btn_active" if code == LANG else "lang_btn")
            b.setFixedSize(34, 26)
            b.clicked.connect(lambda _, c=code: self._set_lang(c))
            lang_lay.addWidget(b); self._lang_btns[code] = b
        right_hdr.addWidget(lang_fr)

        right_hdr.addSpacing(4)

        # Notification bell with badge
        self.notif_btn = QPushButton("🔔")
        self.notif_btn.setObjectName("header_icon")
        self.notif_btn.setFixedSize(34, 34)
        self.notif_btn.setToolTip(t("dlg_alerts_title"))
        self.notif_btn.clicked.connect(self._show_alerts)
        self._notif_badge = QLabel("0", self.notif_btn)
        self._notif_badge.setObjectName("notif_badge")
        self._notif_badge.setFixedSize(18, 18)
        self._notif_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._notif_badge.move(18, -2)
        self._notif_badge.hide()
        right_hdr.addWidget(self.notif_btn)

        # Refresh
        self.refresh_btn = QPushButton()
        self.refresh_btn.setObjectName("header_icon")
        self.refresh_btn.setFixedSize(34, 34)
        self.refresh_btn.setIcon(get_button_icon("refresh"))
        self.refresh_btn.setIconSize(QSize(16, 16))
        self.refresh_btn.setToolTip(t("tooltip_refresh"))
        self.refresh_btn.clicked.connect(self._refresh_all)
        right_hdr.addWidget(self.refresh_btn)

        # Theme toggle (animated sliding switch)
        self._theme_toggle = ThemeToggle()
        self._theme_toggle.theme_toggled.connect(self._toggle_mode)
        right_hdr.addWidget(self._theme_toggle)

        # Admin/Settings
        self.admin_btn = QPushButton()
        self.admin_btn.setObjectName("header_icon")
        self.admin_btn.setFixedSize(34, 34)
        self.admin_btn.setIcon(get_button_icon("settings"))
        self.admin_btn.setIconSize(QSize(16, 16))
        self.admin_btn.setToolTip(t("tooltip_admin"))
        self.admin_btn.clicked.connect(self._open_admin)
        right_hdr.addWidget(self.admin_btn)

        hdr_lay.addLayout(right_hdr)
        outer.addWidget(header, 0)

        # ══════════════════════════════════════════════════════════════════════
        # BODY — Sidebar (240px) + Content
        # ══════════════════════════════════════════════════════════════════════
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # ── SIDEBAR ──────────────────────────────────────────────────────────
        self._sidebar = QFrame()
        sidebar_frame = self._sidebar
        sidebar_frame.setObjectName("sidebar")
        sidebar_frame.setFixedWidth(240)
        sidebar_frame.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        sidebar_outer = QVBoxLayout(sidebar_frame)
        sidebar_outer.setContentsMargins(0, 0, 0, 0)
        sidebar_outer.setSpacing(0)

        # Scrollable area for nav + categories
        sb_scroll = QScrollArea()
        sb_scroll.setWidgetResizable(True)
        sb_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sb_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sb_scroll.setObjectName("sidebar_scroll")

        sb_inner = QWidget()
        sb_lay = QVBoxLayout(sb_inner)
        sb_lay.setContentsMargins(0, 0, 0, 0)
        sb_lay.setSpacing(0)

        # ── Main navigation ──
        nav_section = QWidget()
        nav_lay = QVBoxLayout(nav_section)
        nav_lay.setContentsMargins(8, 12, 8, 4)
        nav_lay.setSpacing(2)

        self._nav_btns: list[QPushButton] = []
        self._nav_keys: list[str] = []
        nav_items = [
            ("nav_inventory",    "📦"),
            ("nav_transactions", "📋"),
            ("nav_stock_ops",    "⚙"),
            ("nav_quick_scan",   "⚡"),
            ("nav_barcode_gen",  "🏷"),
        ]
        for key, icon in nav_items:
            btn = QPushButton(f"  {icon}   {t(key)}")
            btn.setObjectName("sidebar_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self._nav_to(k))
            nav_lay.addWidget(btn)
            self._nav_btns.append(btn)
            self._nav_keys.append(key)
        sb_lay.addWidget(nav_section)

        # ── Collapsible categories ──
        self._cat_sep = QFrame()
        self._cat_sep.setObjectName("sidebar_divider")
        self._cat_sep.setFixedHeight(1)
        sb_lay.addWidget(self._cat_sep)

        self._cat_section = CollapsibleSection("CATEGORIES")
        self._cat_nav_btns: list[QPushButton] = []
        for cat in _cat_repo.get_all_active():
            icon = load_svg_icon(cat.icon) if cat.icon else "📁"
            btn = QPushButton(f"  {icon}   {cat.name(LANG)}")
            btn.setObjectName("sidebar_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=cat.key: self._nav_to(f"cat_{k}"))
            self._cat_section.add_widget(btn)
            self._cat_nav_btns.append(btn)
            self._nav_btns.append(btn)
            self._nav_keys.append(f"cat_{cat.key}")
        sb_lay.addWidget(self._cat_section)

        sb_lay.addStretch()
        sb_scroll.setWidget(sb_inner)
        sidebar_outer.addWidget(sb_scroll, 1)

        # ── Fixed bottom: shop info ──
        btm_div = QFrame()
        btm_div.setObjectName("sidebar_divider")
        btm_div.setFixedHeight(1)
        sidebar_outer.addWidget(btm_div)

        if cfg.name:
            shop_frame = QFrame()
            shop_frame.setObjectName("sidebar_user_info")
            sf_lay = QVBoxLayout(shop_frame)
            sf_lay.setContentsMargins(12, 10, 12, 10)
            sf_lay.setSpacing(2)
            self._shop_name_lbl = QLabel(cfg.name)
            self._shop_name_lbl.setObjectName("sidebar_shop_name")
            sf_lay.addWidget(self._shop_name_lbl)
            if cfg.contact_info:
                self._shop_meta_lbl = QLabel(cfg.contact_info)
                self._shop_meta_lbl.setObjectName("sidebar_shop_meta")
                sf_lay.addWidget(self._shop_meta_lbl)
            else:
                self._shop_meta_lbl = None
            sidebar_outer.addWidget(shop_frame)
        else:
            self._shop_name_lbl = None
            self._shop_meta_lbl = None

        # Hidden alert button (used by _check_alerts, not visible in sidebar)
        self.alert_btn = QPushButton()
        self.alert_btn.setObjectName("alert_ok")
        self.alert_btn.hide()

        body.addWidget(sidebar_frame)

        # ── CONTENT AREA ─────────────────────────────────────────────────────
        content = QVBoxLayout()
        content.setContentsMargins(16, 16, 16, 12)
        content.setSpacing(12)

        self._stack = QStackedWidget()
        self._stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)

        # Page 0: Inventory
        inv_page = QWidget()
        inv_page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        inv_lay = QVBoxLayout(inv_page)
        inv_lay.setContentsMargins(0, 0, 0, 0)
        inv_lay.setSpacing(12)

        cr = QHBoxLayout(); cr.setSpacing(12)
        self.c_tot = SummaryCard("card_total_products")
        self.c_unt = SummaryCard("card_total_units")
        self.c_low = SummaryCard("card_low_stock")
        self.c_out = SummaryCard("card_out_of_stock")
        self.c_val = SummaryCard("card_inventory_value")
        for c in (self.c_tot, self.c_unt, self.c_low, self.c_out, self.c_val):
            cr.addWidget(c)
        inv_lay.addLayout(cr)

        tb = QHBoxLayout(); tb.setSpacing(8)
        self.low_cb = QCheckBox(t("low_stock_only"))
        self.low_cb.stateChanged.connect(self._refresh_products)
        self.add_btn = QPushButton(t("btn_new_product"))
        self.add_btn.setObjectName("btn_primary")
        self.add_btn.setMaximumHeight(36)
        self.add_btn.clicked.connect(self._add_product)
        tb.addWidget(self.low_cb); tb.addStretch(); tb.addWidget(self.add_btn)
        inv_lay.addLayout(tb)

        sp = QSplitter(Qt.Orientation.Horizontal); sp.setHandleWidth(1)
        sp.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.prod_tbl = ProductTable()
        sp.addWidget(self.prod_tbl)
        rs = QScrollArea(); rs.setWidgetResizable(True)
        rs.setMinimumWidth(0); rs.setMaximumWidth(320)
        rs.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        rs.setObjectName("detail_scroll_area")
        self.detail = ProductDetail(); rs.setWidget(self.detail)
        sp.addWidget(rs)
        sp.setStretchFactor(0, 3); sp.setStretchFactor(1, 1)
        sp.setSizes([700, 300])
        inv_lay.addWidget(sp, 1)
        self._stack.addWidget(inv_page)

        # Page 1: Transactions
        txn_pg = QWidget()
        txn_pg.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        tl = QVBoxLayout(txn_pg); tl.setContentsMargins(0, 0, 0, 0); tl.setSpacing(8)
        tbar = QHBoxLayout(); tbar.setContentsMargins(0, 0, 0, 0)
        self._txn_caption = QLabel(t("txn_history_caption"))
        self._txn_caption.setObjectName("section_caption")
        self._txn_ref_btn = QPushButton()
        self._txn_ref_btn.setObjectName("btn_secondary")
        self._txn_ref_btn.setIcon(get_button_icon("refresh"))
        self._txn_ref_btn.setIconSize(QSize(16, 16))
        self._txn_ref_btn.clicked.connect(self._refresh_all_txns)
        tbar.addWidget(self._txn_caption); tbar.addStretch()
        tbar.addWidget(self._txn_ref_btn)
        tl.addLayout(tbar)
        self.txn_tbl = TransactionTable(); tl.addWidget(self.txn_tbl)
        self._stack.addWidget(txn_pg)

        # Page 2: Stock Operations
        self._stock_ops_tab = StockOpsTab()
        self._stack.addWidget(self._stock_ops_tab)

        # Page 3: Quick Scan
        self._quick_scan_tab = QuickScanTab()
        self._stack.addWidget(self._quick_scan_tab)

        # Page 4: Barcode Generator
        self._barcode_gen_page = BarcodeGenPage()
        self._stack.addWidget(self._barcode_gen_page)

        # Pages 5+: Dynamic matrix tabs
        self._matrix_tabs: list[MatrixTab] = []
        for cat in _cat_repo.get_all_active():
            tab = MatrixTab(cat.key)
            self._matrix_tabs.append(tab)
            self._stack.addWidget(tab)

        content.addWidget(self._stack, 1)
        content_w = QWidget()
        content_w.setLayout(content)
        content_w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        body.addWidget(content_w, 1)

        body_w = QWidget()
        body_w.setLayout(body)
        body_w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        outer.addWidget(body_w, 1)

        # ══════════════════════════════════════════════════════════════════════
        # FOOTER BAR (32px) — Status, Version, Sync indicator
        # ══════════════════════════════════════════════════════════════════════
        footer = QFrame()
        footer.setObjectName("footer_bar")
        footer.setFixedHeight(32)
        footer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        ftr_lay = QHBoxLayout(footer)
        ftr_lay.setContentsMargins(16, 0, 16, 0)
        ftr_lay.setSpacing(0)

        self._footer_status = QLabel(t("statusbar_ready"))
        self._footer_status.setObjectName("footer_status")
        ftr_lay.addWidget(self._footer_status)
        ftr_lay.addStretch()

        self._footer_version = QLabel("v2.0.0")
        self._footer_version.setObjectName("footer_version")
        ftr_lay.addWidget(self._footer_version)
        ftr_lay.addStretch()

        right_ftr = QHBoxLayout(); right_ftr.setSpacing(8)
        self._footer_sync = QLabel("●  Connected")
        self._footer_sync.setObjectName("footer_sync")
        right_ftr.addWidget(self._footer_sync)
        ftr_lay.addLayout(right_ftr)

        outer.addWidget(footer, 0)

        # Set initial active nav
        self._current_nav = "nav_inventory"
        self._update_nav_styles()

    # ── Navigation ────────────────────────────────────────────────────────────

    def _toggle_sidebar(self):
        vis = self._sidebar.isVisible()
        self._sidebar.setVisible(not vis)
        self._sidebar_toggle.setText("☰" if vis else "×")

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
        elif key == "nav_barcode_gen":
            self._stack.setCurrentIndex(self._PAGE_BARCODE_GEN)
            self._barcode_gen_page.refresh()
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
        QShortcut(QKeySequence("Ctrl+B"), self).activated.connect(self._toggle_sidebar)

        # Global barcode capture — catches scanner input even when no field is focused
        self._global_bc_buf: list[str] = []
        self._global_bc_timer = QTimer(self)
        self._global_bc_timer.setSingleShot(True)
        self._global_bc_timer.setInterval(100)
        self._global_bc_timer.timeout.connect(self._flush_global_bc)

    def keyPressEvent(self, event):
        """Capture keystrokes globally for barcode scanner detection."""
        # Only intercept if no QLineEdit/QSpinBox currently has focus
        focus = self.focusWidget()
        if isinstance(focus, (QLineEdit, QSpinBox)):
            super().keyPressEvent(event)
            return

        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # Flush buffer as barcode
            self._global_bc_timer.stop()
            bc = "".join(self._global_bc_buf).strip()
            self._global_bc_buf.clear()
            if bc:
                self._barcode(bc)
        elif event.text() and event.text().isprintable():
            self._global_bc_buf.append(event.text())
            self._global_bc_timer.start()
        else:
            super().keyPressEvent(event)

    def _flush_global_bc(self):
        """Auto-flush global buffer if 3+ chars accumulated (scanner fires fast)."""
        if len(self._global_bc_buf) >= 3:
            bc = "".join(self._global_bc_buf).strip()
            if bc:
                self._barcode(bc)
        self._global_bc_buf.clear()

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
        saved_nav = self._current_nav
        open_admin(self)
        ShopConfig.invalidate()
        cfg = ShopConfig.get()
        if cfg.theme in ("pro_dark", "pro_light", "dark", "light"):
            THEME.set_theme(cfg.theme)
            self._theme_toggle._update_text()
            self._bg.update()
        ensure_matrix_entries()
        self._rebuild_matrix_tabs()
        self._retranslate()
        # Restore the page the user was on before opening admin
        self._nav_to(saved_nav)

    def _rebuild_matrix_tabs(self) -> None:
        # Remove old matrix tabs from stack
        for tab in self._matrix_tabs:
            self._stack.removeWidget(tab)
            tab.deleteLater()
        self._matrix_tabs.clear()

        # Remove old category nav buttons
        for btn in self._cat_nav_btns:
            btn.deleteLater()
        for btn in self._cat_nav_btns:
            if btn in self._nav_btns:
                idx = self._nav_btns.index(btn)
                self._nav_btns.pop(idx)
                self._nav_keys.pop(idx)
        self._cat_nav_btns.clear()

        # Rebuild into collapsible section
        for cat in _cat_repo.get_all_active():
            icon = load_svg_icon(cat.icon) if cat.icon else "📁"
            btn = QPushButton(f"  {icon}   {cat.name(LANG)}")
            btn.setObjectName("sidebar_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=cat.key: self._nav_to(f"cat_{k}"))
            self._cat_section.add_widget(btn)
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
            ("nav_barcode_gen",  "🏷"),
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

        # Shop info in sidebar
        cfg2 = ShopConfig.get()
        if self._shop_name_lbl and cfg2.name:
            self._shop_name_lbl.setText(cfg2.name)
        if self._shop_meta_lbl and cfg2.contact_info:
            self._shop_meta_lbl.setText(cfg2.contact_info)

        self._refresh_products(); self._refresh_all_txns(); self._refresh_summary()
        self.detail.retranslate(); self._check_alerts()
        self._show_status(t("statusbar_ready"))

    # ── Status ─────────────────────────────────────────────────────────────────

    def _show_status(self, msg: str, timeout: int = 0):
        """Update footer status text."""
        self._footer_status.setText(msg)
        if timeout > 0:
            QTimer.singleShot(timeout, lambda: self._footer_status.setText(t("statusbar_ready")))

    # ── Refresh ────────────────────────────────────────────────────────────────

    def _refresh_products(self):
        s     = self.search.text().strip()
        items = _item_repo.get_all_items(
            search=s if len(s) >= 2 else "",
            filter_low_stock=self.low_cb.isChecked(),
        )
        self.prod_tbl.load(items)
        self._show_status(t("status_n_products", n=len(items)), 3000)

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
        self._show_status(t("status_refreshed"), 2000)

    # ── Events ─────────────────────────────────────────────────────────────────

    def _sel(self, item: InventoryItem | None):
        self._cp = item
        self.detail.set_product(item)

    def _barcode(self, bc: str):
        from app.core.scan_config import ScanConfig
        scan_cfg = ScanConfig.get()

        # 1) Command barcodes → always Quick Scan
        if scan_cfg.is_command(bc):
            self.search.clear()
            self._nav_to("nav_quick_scan")
            self._quick_scan_tab.process_command_barcode(bc)
            self._quick_scan_tab.focus_input()
            return

        # 2) Quick Scan has active session → route item barcodes there
        if self._quick_scan_tab._session.mode:
            self.search.clear()
            self._nav_to("nav_quick_scan")
            self._quick_scan_tab.process_command_barcode(bc)
            self._quick_scan_tab.focus_input()
            return

        # 3) Normal: navigate to inventory + select product
        item = _item_repo.get_by_barcode(bc)
        if item:
            self.search.clear()
            self._nav_to("nav_inventory")
            self.prod_tbl.select_by_id(item.id)
            self._sel(item)
            self._show_status(
                t("status_scanned", brand=item.display_name, type=""), 5000
            )
        else:
            self._show_status(t("status_unknown_bc", bc=bc), 4000)
            if QMessageBox.question(
                self, t("msg_unknown_bc_title"), t("msg_unknown_bc_body", bc=bc),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            ) == QMessageBox.StandardButton.Yes:
                self._add_product(preset_barcode=bc)

    def _toggle_mode(self):
        # Theme was already toggled by ThemeToggle widget — just refresh UI
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
            self._show_status(t("status_product_added", pid=pid), 4000)
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
            self._show_status(t("status_product_updated"), 3000)
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
            self._show_status(t("status_product_deleted"), 3000)
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
            self._show_status(
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
            self._notif_badge.hide()
        elif any(p.is_out for p in low):
            s = "s" if n > 1 else ""
            self.alert_btn.setText(t("alert_critical", n=n, s=s))
            self.alert_btn.setObjectName("alert_critical")
            self._notif_badge.setText(str(n))
            self._notif_badge.show()
        else:
            s = "s" if n > 1 else ""
            self.alert_btn.setText(t("alert_warn", n=n, s=s))
            self.alert_btn.setObjectName("alert_warn")
            self._notif_badge.setText(str(n))
            self._notif_badge.show()
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
