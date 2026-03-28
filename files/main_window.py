"""
main_window.py — Stock Manager Pro
Gradient dark (indigo-charcoal) / warm light (cream→periwinkle).
All CRUD, stock ops, scanner, alerts, dark/light toggle, i18n (EN/DE/AR).
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
    QColor, QKeySequence, QShortcut, QPainter, QPainterPath,
    QFont, QPixmap, QIcon, QLinearGradient, QBrush,
)

import database as db
import colors as clr
from dialogs import ProductDialog, StockOpDialog, LowStockDialog
from theme import THEME, GradientBackground, qc, _rgba
from i18n import t, set_lang, LANG, color_t, note_t


# ── sqlite3.Row helper ────────────────────────────────────────────────────────

def _row(p) -> dict:
    if p is None: return {}
    if isinstance(p, dict): return p
    return dict(p)


# ── Stock level helpers ────────────────────────────────────────────────────────

def _sc(s: int, thr: int) -> QColor:
    tk = THEME.tokens
    if s == 0:              return QColor(tk.red)
    if s <= max(1, thr//2): return QColor(tk.orange)
    if s <= thr:            return QColor(tk.yellow)
    return QColor(tk.green)

def _sl(s: int, thr: int) -> str:
    # Returns internal English key — used for palette lookup, NOT display
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
        name    = color_t(en_name)   # translate for display, keep EN in model
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

        key  = idx.data(Qt.ItemDataRole.DisplayRole) or ""   # "OK"/"LOW"/etc. — always EN key
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


# ── Barcode / Search input ────────────────────────────────────────────────────

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
        if len(self._buf) >= 4:
            bc = "".join(self._buf).strip()
            if bc: self.barcode_scanned.emit(bc)
        self._buf.clear()

    def _commit(self):
        self._t.stop(); txt = self.text().strip()
        if txt: self.barcode_scanned.emit(txt); self.clear()
        self._buf.clear()


# ── Summary Card ──────────────────────────────────────────────────────────────

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


# ── Product Table ──────────────────────────────────────────────────────────────

class ProductTable(QTableWidget):
    row_selected = pyqtSignal(object)
    _COL_KEYS = ["col_num", "col_brand", "col_type", "col_color",
                 "col_barcode", "col_stock", "col_alert", "col_status"]
    _WIDTHS    = [42, 140, 140, 140, 130, 72, 72, 96]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(len(self._COL_KEYS))
        self.setHorizontalHeaderLabels([t(k) for k in self._COL_KEYS])
        hh = self.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for i, w in enumerate(self._WIDTHS): self.setColumnWidth(i, w)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.setSelectionBehavior(self.SelectionBehavior.SelectRows)
        self.setSelectionMode(self.SelectionMode.SingleSelection)
        self.setEditTriggers(self.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True); self.setSortingEnabled(True)
        self.verticalHeader().setVisible(False); self.setShowGrid(False)
        self.setItemDelegateForColumn(3, ColorSwatchDelegate(self))
        self.setItemDelegateForColumn(7, StatusBadgeDelegate(self))
        self._data: list[dict] = []
        self.itemSelectionChanged.connect(self._emit)

    def retranslate(self):
        self.setHorizontalHeaderLabels([t(k) for k in self._COL_KEYS])

    def load(self, rows):
        self._data = [_row(r) for r in rows]
        self.setSortingEnabled(False); self.setRowCount(len(self._data))
        for i, p in enumerate(self._data):
            sc = _sc(p["stock"], p["low_stock_threshold"])
            sl = _sl(p["stock"], p["low_stock_threshold"])
            hc = clr.hex_for(p["color"])
            vals = [str(p["id"]), p["brand"], p["type"], p["color"],
                    p.get("barcode") or "—", str(p["stock"]),
                    str(p["low_stock_threshold"]), sl]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if j == 3: it.setData(Qt.ItemDataRole.UserRole, hc)
                if j == 5:
                    it.setForeground(sc)
                    it.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
                self.setItem(i, j, it)
            self.setRowHeight(i, 44)
        self.setSortingEnabled(True)

    def _emit(self):
        r = self.currentRow()
        if r < 0: self.row_selected.emit(None); return
        it = self.item(r, 0)
        if it:
            pid = int(it.text())
            for p in self._data:
                if p["id"] == pid: self.row_selected.emit(p); return
        self.row_selected.emit(None)

    def select_by_id(self, pid: int):
        for r in range(self.rowCount()):
            it = self.item(r, 0)
            if it and int(it.text()) == pid:
                self.selectRow(r); self.scrollToItem(it); return


# ── Transaction Table ─────────────────────────────────────────────────────────

class TransactionTable(QTableWidget):
    _COL_KEYS = ["col_datetime", "col_brand", "col_type", "col_color",
                 "col_operation", "col_delta", "col_before", "col_after_col", "col_note"]
    _WIDTHS   = [130, 120, 120, 120, 90, 64, 64, 64, 150]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(len(self._COL_KEYS))
        self.setHorizontalHeaderLabels([t(k) for k in self._COL_KEYS])
        hh = self.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for i, w in enumerate(self._WIDTHS): self.setColumnWidth(i, w)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.setSelectionBehavior(self.SelectionBehavior.SelectRows)
        self.setEditTriggers(self.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True); self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setItemDelegateForColumn(3, ColorSwatchDelegate(self))

    def retranslate(self):
        self.setHorizontalHeaderLabels([t(k) for k in self._COL_KEYS])

    _OP_LBL = {"IN": "op_in_short", "OUT": "op_out_short",
               "ADJUST": "op_adj_short", "CREATE": "op_create_short"}

    def load(self, rows):
        tk = THEME.tokens
        OP = {"IN": tk.green, "OUT": tk.red, "ADJUST": tk.blue, "CREATE": tk.purple}
        self.setRowCount(len(rows))
        for i, row in enumerate(rows):
            tx = _row(row)
            d  = tx["stock_after"] - tx["stock_before"]
            ds = f"+{d}" if d >= 0 else str(d)
            op_key     = tx["operation"]
            op_display = t(self._OP_LBL.get(op_key, op_key))
            vals = [
                tx["timestamp"][:16], tx["brand"], tx["type"], tx["color"],
                op_display, ds,
                str(tx["stock_before"]), str(tx["stock_after"]),
                note_t(tx.get("note") or "") or "—",
            ]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if j == 3:
                    it.setData(Qt.ItemDataRole.UserRole, clr.hex_for(tx["color"]))
                elif j == 4:
                    it.setForeground(QColor(OP.get(op_key, tk.t3)))
                    it.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                elif j == 5:
                    it.setForeground(QColor(tk.green if d >= 0 else tk.red))
                    it.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                self.setItem(i, j, it)
            self.setRowHeight(i, 44)


# ── Mini transaction list ─────────────────────────────────────────────────────

class MiniTxnList(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0); self._lay.setSpacing(0)
        self._rows: list[QWidget] = []

    def load(self, pid: int):
        for w in self._rows: self._lay.removeWidget(w); w.deleteLater()
        self._rows.clear()

        txns = db.get_transactions(product_id=pid, limit=10)
        if not txns:
            lb = QLabel(t("no_transactions")); lb.setObjectName("txn_empty")
            lb.setAlignment(Qt.AlignmentFlag.AlignCenter); lb.setMinimumHeight(48)
            self._lay.addWidget(lb); self._rows.append(lb); return

        tk = THEME.tokens
        OP     = {"IN": tk.green, "OUT": tk.red, "ADJUST": tk.blue, "CREATE": tk.purple}
        OP_LBL = {"IN": "op_in_short", "OUT": "op_out_short",
                  "ADJUST": "op_adj_short", "CREATE": "op_create_short"}

        for idx, row in enumerate(txns):
            tx   = _row(row)
            rf   = QFrame()
            rf.setObjectName("txn_row_alt" if idx % 2 else "txn_row")
            rl   = QHBoxLayout(rf); rl.setContentsMargins(12, 8, 12, 8); rl.setSpacing(10)

            opfg    = OP.get(tx["operation"], tk.t3)
            op_text = t(OP_LBL.get(tx["operation"], "op_in_short"))
            d    = tx["stock_after"] - tx["stock_before"]
            ds   = f"+{d}" if d >= 0 else str(d)

            ol = QLabel(op_text); ol.setFixedWidth(60)
            ol.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ol.setStyleSheet(
                f"color:{opfg}; background:{_rgba(opfg, '20')}; border-radius:7px;"
                "font-weight:700; font-size:8pt; padding:3px 4px;"
            )
            dl = QLabel(ds); dl.setFixedWidth(40); dl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dl.setStyleSheet(f"color:{tk.green if d >= 0 else tk.red}; font-weight:800; font-size:10pt;")
            al = QLabel(f"→ {tx['stock_after']}"); al.setObjectName("txn_after")
            tl = QLabel(tx["timestamp"][5:16]);    tl.setObjectName("txn_time")

            rl.addWidget(ol); rl.addWidget(dl); rl.addWidget(al); rl.addStretch(); rl.addWidget(tl)
            self._lay.addWidget(rf); self._rows.append(rf)


# ── Product Detail Panel ──────────────────────────────────────────────────────

class ProductDetail(QWidget):
    request_in   = pyqtSignal()
    request_out  = pyqtSignal()
    request_adj  = pyqtSignal()
    request_edit = pyqtSignal()
    request_del  = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._p: dict = {}
        self._build(); self._empty()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(12, 12, 12, 12); root.setSpacing(10)

        # ── Info card ──
        self.ic = QFrame(); self.ic.setObjectName("detail_card")
        il = QVBoxLayout(self.ic); il.setContentsMargins(16, 14, 16, 14); il.setSpacing(6)
        cr = QHBoxLayout(); cr.setSpacing(8)
        self.dot = QLabel(); self.dot.setFixedSize(18, 18)
        self.cnm = QLabel(); self.cnm.setObjectName("detail_color_name")
        cr.addWidget(self.dot); cr.addWidget(self.cnm); cr.addStretch()
        self.nm = QLabel(); self.nm.setObjectName("detail_product_name"); self.nm.setWordWrap(True)
        self.bc = QLabel(); self.bc.setObjectName("detail_barcode")
        self.up = QLabel(); self.up.setObjectName("detail_updated")
        il.addWidget(self.nm); il.addLayout(cr); il.addWidget(self.bc); il.addWidget(self.up)
        root.addWidget(self.ic)

        # ── Stock card ──
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

        # ── Operations card ──
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

        # ── Edit / Delete ──
        mr = QHBoxLayout(); mr.setSpacing(8)
        self.bed = QPushButton(t("btn_edit"));   self.bed.setObjectName("mgmt_edit")
        self.bdl = QPushButton(t("btn_delete")); self.bdl.setObjectName("mgmt_del")
        mr.addWidget(self.bed); mr.addWidget(self.bdl)
        self.bed.clicked.connect(self.request_edit)
        self.bdl.clicked.connect(self.request_del)
        root.addLayout(mr)

        # ── Recent transactions ──
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
        self.bed.setText(t("btn_edit"))
        self.bdl.setText(t("btn_delete"))
        if self._p:
            self.set_product(self._p)
        else:
            self._empty()

    def set_product(self, p):
        self._p = _row(p)
        if not self._p: self._empty(); return
        self._set_op_btn_text()

        hc  = clr.hex_for(self._p.get("color", ""))
        brd = "rgba(102,102,102,153)" if clr.is_light(hc) else "transparent"
        self.nm.setText(f"<b>{self._p.get('brand', '')}</b>  ·  {self._p.get('type', '')}")
        self.dot.setStyleSheet(f"background:{hc}; border-radius:9px; border:1.5px solid {brd};")
        self.cnm.setText(self._p.get("color", ""))
        self.bc.setText(t("detail_barcode", val=self._p.get("barcode") or t("dlg_color_none")))
        self.up.setText(t("detail_updated", val=str(self._p.get("updated_at", ""))[:16]))

        tk  = THEME.tokens
        stk = self._p.get("stock", 0)
        thr = self._p.get("low_stock_threshold", 5)
        sc  = _sc(stk, thr); sl = _sl(stk, thr)
        self.sv.setText(str(stk))
        self.sv.setStyleSheet(f"color:{sc.name()};")

        badge_map = {
            "OK":       (tk.green,  _rgba(tk.green,  "28")),
            "LOW":      (tk.yellow, _rgba(tk.yellow, "30")),
            "CRITICAL": (tk.orange, _rgba(tk.orange, "28")),
            "OUT":      (tk.red,    _rgba(tk.red,    "28")),
        }
        fg, bg = badge_map.get(sl, (tk.t3, tk.border))
        badge_labels = {
            "OK":       t("badge_ok"),
            "LOW":      t("badge_low"),
            "CRITICAL": t("badge_critical"),
            "OUT":      t("badge_out"),
        }
        self.sb.setText(badge_labels.get(sl, sl))
        self.sb.setStyleSheet(
            f"color:{fg}; background:{bg}; border:1px solid {_rgba(fg, '40')};"
            "border-radius:10px; font-weight:800; font-size:9pt; padding:5px 14px;"
        )
        self.st.setText(t("detail_alert_at", n=thr))
        self.mt.load(self._p["id"])
        for b in (self.bin, self.bot, self.bad, self.bed, self.bdl): b.setEnabled(True)

    def _empty(self):
        self.nm.setText(f"<i style='color:#7A7FA8'>{t('detail_select_prompt')}</i>")
        self.dot.setStyleSheet(""); self.cnm.setText("")
        self.bc.setText(""); self.up.setText("")
        self.sv.setText("—"); self.sv.setStyleSheet("")
        self.sb.setText(""); self.sb.setStyleSheet("")
        self.st.setText("")
        for b in (self.bin, self.bot, self.bad, self.bed, self.bdl): b.setEnabled(False)


# ── Main Window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        db.init_db()
        self.setWindowTitle(t("app_title")); self.resize(1440, 900)
        self._cp: dict = {}
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

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self._bg)
        root.setContentsMargins(18, 16, 18, 16); root.setSpacing(12)

        # Top bar
        top = QHBoxLayout(); top.setSpacing(10)
        self._title_lbl = QLabel(t("app_title")); self._title_lbl.setObjectName("app_title")
        top.addWidget(self._title_lbl); top.addStretch()

        self.alert_btn = QPushButton(t("alert_ok"))
        self.alert_btn.setObjectName("alert_ok")
        self.alert_btn.clicked.connect(self._show_alerts)

        self.refresh_btn = QPushButton("\u21BA")
        self.refresh_btn.setObjectName("icon_btn")
        self.refresh_btn.setFixedSize(44, 44)
        self.refresh_btn.setFont(QFont("Segoe UI Symbol", 16, QFont.Weight.Bold))
        self.refresh_btn.setToolTip(t("tooltip_refresh"))
        self.refresh_btn.clicked.connect(self._refresh_all)

        self.mode_btn = QPushButton("\u2600")
        self.mode_btn.setObjectName("mode_btn")
        self.mode_btn.setFixedSize(44, 44)
        self.mode_btn.setFont(QFont("Segoe UI Symbol", 16))
        self.mode_btn.setToolTip(t("tooltip_theme"))
        self.mode_btn.clicked.connect(self._toggle_mode)

        # Language buttons
        lang_fr = QFrame(); lang_fr.setObjectName("lang_bar")
        lang_lay = QHBoxLayout(lang_fr); lang_lay.setContentsMargins(3, 3, 3, 3); lang_lay.setSpacing(1)
        self._lang_btns: dict[str, QPushButton] = {}
        for code in ("EN", "DE", "AR"):
            b = QPushButton(code); b.setObjectName("lang_btn_active" if code == LANG else "lang_btn")
            b.setFixedSize(40, 30); b.clicked.connect(lambda _, c=code: self._set_lang(c))
            lang_lay.addWidget(b); self._lang_btns[code] = b

        top.addWidget(lang_fr)
        top.addWidget(self.alert_btn)
        top.addWidget(self.refresh_btn)
        top.addWidget(self.mode_btn)
        root.addLayout(top)

        # Summary cards
        cr = QHBoxLayout(); cr.setSpacing(12)
        self.c_tot = SummaryCard("card_total_products")
        self.c_unt = SummaryCard("card_total_units")
        self.c_low = SummaryCard("card_low_stock")
        self.c_out = SummaryCard("card_out_of_stock")
        for c in (self.c_tot, self.c_unt, self.c_low, self.c_out): cr.addWidget(c)
        root.addLayout(cr)

        # Toolbar
        tb = QHBoxLayout(); tb.setSpacing(10)
        self.search = BarcodeLineEdit(); self.search.setObjectName("search_bar")
        self.search.setMinimumHeight(44)
        self.low_cb = QCheckBox(t("low_stock_only"))
        self.low_cb.stateChanged.connect(self._refresh_products)
        self.add_btn = QPushButton(t("btn_new_product"))
        self.add_btn.setObjectName("btn_primary")
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
        self._txn_caption = QLabel(t("txn_history_caption"))
        self._txn_caption.setObjectName("section_caption")
        self._txn_ref_btn = QPushButton(t("btn_refresh")); self._txn_ref_btn.setObjectName("btn_secondary")
        self._txn_ref_btn.clicked.connect(self._refresh_all_txns)
        tbar.addWidget(self._txn_caption); tbar.addStretch(); tbar.addWidget(self._txn_ref_btn)
        tl.addLayout(tbar)
        self.txn_tbl = TransactionTable()
        tl.addWidget(self.txn_tbl)
        self.tabs.addTab(txn_pg, t("tab_transactions"))
        sp.addWidget(self.tabs)

        # Right — detail
        rs = QScrollArea(); rs.setWidgetResizable(True)
        rs.setMinimumWidth(295); rs.setMaximumWidth(375)
        rs.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        rs.setObjectName("detail_scroll_area")
        self.detail = ProductDetail()
        rs.setWidget(self.detail)
        sp.addWidget(rs)
        sp.setStretchFactor(0, 4); sp.setStretchFactor(1, 1)
        root.addWidget(sp, 1)

        # Status bar
        self.status = QStatusBar(); self.setStatusBar(self.status)
        self.status.showMessage(t("statusbar_ready"))

    # ── Signals ────────────────────────────────────────────────────────────────

    def _connect(self):
        self.prod_tbl.row_selected.connect(self._sel)
        self.search.barcode_scanned.connect(self._barcode)
        self.search.textChanged.connect(
            lambda txt: self._refresh_products() if len(txt) != 1 else None
        )
        self.detail.request_in.connect(lambda: self._stock_op("IN"))
        self.detail.request_out.connect(lambda: self._stock_op("OUT"))
        self.detail.request_adj.connect(lambda: self._stock_op("ADJUST"))
        self.detail.request_edit.connect(self._edit)
        self.detail.request_del.connect(self._delete)

        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self._add_product)
        QShortcut(QKeySequence("F5"),     self).activated.connect(self._refresh_all)
        QShortcut(QKeySequence("Ctrl+I"), self).activated.connect(lambda: self._stock_op("IN"))
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(lambda: self._stock_op("OUT"))

    # ── Language ────────────────────────────────────────────────────────────────

    def _set_lang(self, lang: str):
        set_lang(lang)
        for code, btn in self._lang_btns.items():
            btn.setObjectName("lang_btn_active" if code == lang else "lang_btn")
            btn.style().unpolish(btn); btn.style().polish(btn)
        self._retranslate()

    def _retranslate(self):
        self.setWindowTitle(t("app_title"))
        self._title_lbl.setText(t("app_title"))
        self.refresh_btn.setToolTip(t("tooltip_refresh"))
        self.mode_btn.setToolTip(t("tooltip_theme"))
        self.c_tot.retranslate(); self.c_unt.retranslate()
        self.c_low.retranslate(); self.c_out.retranslate()
        self.search.setPlaceholderText(t("search_placeholder"))
        self.low_cb.setText(t("low_stock_only"))
        self.add_btn.setText(t("btn_new_product"))
        self.tabs.setTabText(0, t("tab_products"))
        self.tabs.setTabText(1, t("tab_transactions"))
        self._txn_caption.setText(t("txn_history_caption"))
        self._txn_ref_btn.setText(t("btn_refresh"))
        self.prod_tbl.retranslate()
        self.txn_tbl.retranslate()
        # Reload table data so operation labels and color names repaint in new language
        self._refresh_products()
        self._refresh_all_txns()
        self._refresh_summary()
        self.detail.retranslate()
        self._check_alerts()
        self.status.showMessage(t("statusbar_ready"))

    # ── Refresh ────────────────────────────────────────────────────────────────

    def _refresh_products(self):
        s    = self.search.text().strip()
        rows = db.get_all_products(
            search=s if len(s) >= 2 else "",
            filter_low_stock=self.low_cb.isChecked()
        )
        self.prod_tbl.load(rows)
        self.status.showMessage(t("status_n_products", n=len(rows)), 3000)

    def _refresh_summary(self):
        s = db.get_summary(); tk = THEME.tokens
        self.c_tot.set(s.get("total_products") or 0)
        self.c_unt.set(s.get("total_units") or 0, tk.green)
        low = s.get("low_stock_count") or 0
        out = s.get("out_of_stock_count") or 0
        self.c_low.set(low, tk.orange if low > 0 else tk.green)
        self.c_out.set(out, tk.red   if out > 0 else tk.green)

    def _refresh_all_txns(self):
        self.txn_tbl.load(db.get_transactions(limit=500))

    def _refresh_all(self):
        self._refresh_products(); self._refresh_summary(); self._refresh_all_txns()
        if self._cp:
            row = db.get_product_by_id(self._cp["id"])
            self._cp = _row(row); self.detail.set_product(self._cp)
        self._check_alerts()
        self.status.showMessage(t("status_refreshed"), 2000)

    # ── Events ─────────────────────────────────────────────────────────────────

    def _sel(self, p):
        self._cp = _row(p) if p else {}
        self.detail.set_product(self._cp if self._cp else None)

    def _barcode(self, bc: str):
        p = db.get_product_by_barcode(bc)
        if p:
            pd = _row(p)
            self.prod_tbl.select_by_id(pd["id"])
            self._sel(pd)
            self.status.showMessage(t("status_scanned", brand=pd["brand"], type=pd["type"]), 5000)
        else:
            self.status.showMessage(t("status_unknown_bc", bc=bc), 4000)
            if QMessageBox.question(
                self, t("msg_unknown_bc_title"),
                t("msg_unknown_bc_body", bc=bc),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) == QMessageBox.StandardButton.Yes:
                self._add_product(preset_barcode=bc)

    def _toggle_mode(self):
        THEME.toggle()
        self.mode_btn.setText("\u2600" if THEME.is_dark else "\U0001F319")
        self._bg.update()
        self._refresh_products(); self._refresh_all_txns(); self._refresh_summary()
        if self._cp:
            self.detail.set_product(self._cp)
        self.prod_tbl.viewport().update()
        self.txn_tbl.viewport().update()

    # ── CRUD ───────────────────────────────────────────────────────────────────

    def _add_product(self, checked=False, preset_barcode=""):
        dlg = ProductDialog(self)
        if preset_barcode: dlg.barcode_edit.setText(preset_barcode)
        if dlg.exec() != QDialog.DialogCode.Accepted: return
        data = dlg.get_data()
        try:
            pid = db.add_product(**data)
            self._refresh_products(); self._refresh_summary(); self._refresh_all_txns()
            self.prod_tbl.select_by_id(pid)
            self.status.showMessage(t("status_product_added", pid=pid), 4000)
        except Exception as e:
            QMessageBox.critical(self, t("msg_error"), str(e))

    def _edit(self):
        if not self._cp: return
        row = db.get_product_by_id(self._cp["id"])
        dlg = ProductDialog(self, product=row)
        if dlg.exec() != QDialog.DialogCode.Accepted: return
        data = dlg.get_data()
        try:
            db.update_product(
                product_id=self._cp["id"],
                brand=data["brand"], type_=data["type_"],
                color=data["color"], barcode=data["barcode"],
                low_stock_threshold=data["low_stock_threshold"],
            )
            self._refresh_all()
            self.status.showMessage(t("status_product_updated"), 3000)
        except Exception as e:
            QMessageBox.critical(self, t("msg_error"), str(e))

    def _delete(self):
        if not self._cp: return
        p = self._cp; tk = THEME.tokens
        ans = QMessageBox.question(
            self, t("msg_delete_title"),
            t("msg_delete_body", brand=p.get("brand"), type=p.get("type"),
              color=p.get("color"), red=tk.red),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes: return
        try:
            db.delete_product(p["id"])
            self._cp = {}; self.detail.set_product(None)
            self._refresh_all()
            self.status.showMessage(t("status_product_deleted"), 3000)
        except Exception as e:
            QMessageBox.critical(self, t("msg_error"), str(e))

    # ── Stock Operations ────────────────────────────────────────────────────────

    def _stock_op(self, op: str):
        if not self._cp: return
        row = db.get_product_by_id(self._cp["id"])
        if row is None:
            QMessageBox.warning(self, t("msg_not_found_title"), t("msg_not_found_body")); return
        p   = _row(row)
        dlg = StockOpDialog(self, product=p, operation=op)
        if dlg.exec() != QDialog.DialogCode.Accepted: return
        data = dlg.get_data()
        try:
            if op == "IN":
                res = db.stock_in(p["id"], data["quantity"], data["note"])
            elif op == "OUT":
                res = db.stock_out(p["id"], data["quantity"], data["note"])
            else:
                res = db.adjust_stock(p["id"], data["quantity"], data["note"])

            self._refresh_all()
            self._check_alerts()
            self.status.showMessage(
                t("status_stock_op", op=op, before=res["before"], after=res["after"]), 4000
            )
            updated = _row(db.get_product_by_id(p["id"]))
            if updated and updated["stock"] <= updated["low_stock_threshold"]:
                level = t("msg_level_out") if updated["stock"] == 0 else t("msg_level_low")
                QMessageBox.warning(
                    self, t("msg_low_title", level=level),
                    t("msg_low_body", brand=updated["brand"], type=updated["type"],
                      color=updated["color"], stock=updated["stock"],
                      thr=updated["low_stock_threshold"]),
                )
        except ValueError as e:
            QMessageBox.warning(self, t("msg_op_failed"), str(e))
        except Exception as e:
            QMessageBox.critical(self, t("msg_error"), str(e))

    # ── Alerts ──────────────────────────────────────────────────────────────────

    def _check_alerts(self):
        low = db.get_low_stock_products(); n = len(low)
        if n == 0:
            self.alert_btn.setText(t("alert_ok"))
            self.alert_btn.setObjectName("alert_ok")
        elif any(_row(p)["stock"] == 0 for p in low):
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
                self._sel(_row(db.get_product_by_id(pid))),
            )
        )
        self._ld.show()
