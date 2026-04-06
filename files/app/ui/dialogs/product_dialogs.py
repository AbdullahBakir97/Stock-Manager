"""dialogs.py — All modal dialogs for Stock Manager Pro.

Modern design guide compliance:
- ModernDialog base with drop shadow + custom header
- FormField widget for consistent label + input layout
- Monospace font for barcodes and stock numbers
- 4px grid spacing system
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QDialogButtonBox, QGroupBox, QFrame,
    QMessageBox, QToolButton, QGridLayout, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import (
    QColor, QPainter, QPixmap, QIcon, QFont,
    QLinearGradient, QBrush,
)

from app.core import colors as clr
from app.services.alert_service import AlertService
from app.core.theme import THEME, _rgba
from app.core.i18n import t, color_t
from app.core.config import ShopConfig

_alert_svc = AlertService()

# ── Typography constants ──────────────────────────────────────────────────────
_FONT_MONO = QFont("JetBrains Mono", 10)
_FONT_MONO.setStyleHint(QFont.StyleHint.Monospace)
_FONT_BODY = QFont("Segoe UI", 10)
_FONT_HEADING = QFont("Segoe UI", 14, QFont.Weight.DemiBold)


# ── helpers ───────────────────────────────────────────────────────────────────

def _row(p) -> dict:
    return dict(p) if p is not None else {}

def _field(ph="", txt=""):
    w = QLineEdit(txt); w.setPlaceholderText(ph); w.setMinimumHeight(38); return w

def _pm(hex_, sz=18):
    pm = QPixmap(sz, sz); pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(hex_))
    if clr.is_light(hex_):
        from PyQt6.QtGui import QPen; p.setPen(QPen(QColor(85, 85, 85, 102), 1))
    else:
        p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(1, 1, sz-2, sz-2); p.end(); return pm

def _style(dlg):
    dlg.setStyleSheet(THEME.stylesheet()); THEME.register(dlg)

def _cancel_btn(bb: QDialogButtonBox):
    btn = bb.button(QDialogButtonBox.StandardButton.Cancel)
    if btn: btn.setText(t("op_cancel"))


# ── QuantitySpin — custom +/− widget replacing QSpinBox ──────────────────────

class QuantitySpin(QWidget):
    """Professional +/− spin control with direct keyboard entry."""
    valueChanged = pyqtSignal(int)

    def __init__(self, mn: int = 0, mx: int = 999_999, v: int = 0, parent=None):
        super().__init__(parent)
        self._min = mn; self._max = mx; self._val = v
        self._delay = QTimer(self); self._delay.setSingleShot(True); self._delay.setInterval(400)
        self._repeat = QTimer(self); self._repeat.setInterval(80)
        self._delay.timeout.connect(self._repeat.start)
        self._build()

    def _build(self):
        lay = QHBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(8)

        self._minus = QPushButton("−"); self._minus.setObjectName("spin_minus")
        self._minus.setFixedSize(44, 44)

        self._edit = QLineEdit(str(self._val)); self._edit.setObjectName("spin_edit")
        self._edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._edit.setFixedHeight(44)
        self._edit.setFont(QFont("JetBrains Mono", 14, QFont.Weight.Bold))

        self._plus = QPushButton("+"); self._plus.setObjectName("spin_plus")
        self._plus.setFixedSize(44, 44)

        lay.addWidget(self._minus); lay.addWidget(self._edit, 1); lay.addWidget(self._plus)

        self._minus.pressed.connect(lambda: self._start_repeat(-1))
        self._plus.pressed.connect(lambda: self._start_repeat(1))
        self._minus.released.connect(lambda: self._on_released(-1))
        self._plus.released.connect(lambda: self._on_released(1))
        self._edit.editingFinished.connect(self._parse)

    def _start_repeat(self, d: int):
        try: self._repeat.timeout.disconnect()
        except Exception: pass
        self._repeat.timeout.connect(lambda: self._step(d))
        self._delay.start()

    def _on_released(self, d: int):
        quick = self._delay.isActive()
        self._delay.stop()
        self._repeat.stop()
        if quick:
            self._step(d)

    def _step(self, d: int):
        self.setValue(self._val + d)

    def _parse(self):
        try:
            v = int(self._edit.text())
            self.setValue(v)
        except ValueError:
            self._edit.setText(str(self._val))

    def value(self) -> int:
        return self._val

    def setValue(self, v: int):
        v = max(self._min, min(self._max, v))
        if v == self._val:
            self._edit.setText(str(v)); return
        self._val = v
        self._edit.blockSignals(True); self._edit.setText(str(v)); self._edit.blockSignals(False)
        self.valueChanged.emit(v)

    def setRange(self, mn: int, mx: int):
        self._min = mn; self._max = mx; self.setValue(self._val)


# ── Modern Dialog base ───────────────────────────────────────────────────────

class ModernDialog(QDialog):
    """Professional dialog with drop shadow and solid background."""

    def __init__(self, parent=None):
        super().__init__(parent)

    def paintEvent(self, _ev):
        tk = THEME.tokens
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(tk.grad_top))
        p.end()


# ── Legacy alias (keep backward compat with GradientDialog imports) ──────────
GradientDialog = ModernDialog


# ── FormField — consistent label + input ─────────────────────────────────────

class FormField(QWidget):
    """Consistent form field with label above input."""
    def __init__(self, label: str, widget: QWidget,
                 required: bool = False, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(6)

        label_row = QHBoxLayout()
        label_row.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size:12px; font-weight:500; color:{THEME.tokens.t2};")
        label_row.addWidget(lbl)
        if required:
            req = QLabel("*")
            req.setStyleSheet(f"color:{THEME.tokens.red}; font-weight:600;")
            label_row.addWidget(req)
        label_row.addStretch()
        layout.addLayout(label_row)
        layout.addWidget(widget)


# ── Color Picker ──────────────────────────────────────────────────────────────

class ColorPickerDialog(ModernDialog):
    def __init__(self, cur="", parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("dlg_choose_color")); self.setModal(True); self.setFixedWidth(460)
        self._sel = cur or ""; self._btns: dict[str, QToolButton] = {}
        self._build(); _style(self)

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(24, 24, 24, 20); root.setSpacing(16)

        # Header with close button
        hdr_row = QHBoxLayout()
        hdr = QLabel(t("dlg_choose_color")); hdr.setObjectName("dlg_header")
        close_btn = QPushButton("×"); close_btn.setObjectName("btn_close_x")
        close_btn.setFixedSize(32, 32); close_btn.clicked.connect(self.reject)
        hdr_row.addWidget(hdr); hdr_row.addStretch(); hdr_row.addWidget(close_btn)
        root.addLayout(hdr_row)

        gw = QWidget()
        grid = QGridLayout(gw); grid.setSpacing(10)
        for i, (name, hex_) in enumerate(clr.PALETTE.items()):
            btn = QToolButton(); btn.setFixedSize(54, 54); btn.setToolTip(color_t(name))
            btn.setCheckable(True); btn.setChecked(name == self._sel)
            idle = "rgba(102,102,102,153)" if clr.is_light(hex_) else "transparent"
            btn.setStyleSheet(
                f"QToolButton{{background:{hex_};border-radius:27px;border:2.5px solid {idle};}}"
                f"QToolButton:hover{{border:3px solid rgba(255,255,255,153);}}"
                f"QToolButton:checked{{border:3.5px solid {THEME.tokens.green};}}"
            )
            btn.clicked.connect(lambda _, n=name: self._pick(n))
            grid.addWidget(btn, i // 6, i % 6); self._btns[name] = btn
        root.addWidget(gw)

        pf = QFrame(); pf.setObjectName("preview_frame")
        pl = QHBoxLayout(pf); pl.setContentsMargins(14, 12, 14, 12); pl.setSpacing(12)
        self._dot = QLabel(); self._dot.setFixedSize(34, 34)
        self._nm = QLabel(t("dlg_color_none")); self._nm.setObjectName("preview_name_lbl")
        pl.addWidget(self._dot); pl.addWidget(self._nm); pl.addStretch()
        root.addWidget(pf); self._upd(self._sel)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok = bb.button(QDialogButtonBox.StandardButton.Ok)
        ok.setText(t("dlg_color_select")); ok.setObjectName("btn_primary")
        _cancel_btn(bb)
        bb.accepted.connect(self._confirm); bb.rejected.connect(self.reject); root.addWidget(bb)

    def _pick(self, n):
        for k, b in self._btns.items(): b.setChecked(k == n)
        self._sel = n; self._upd(n)

    def _upd(self, n):
        if not n:
            self._dot.setStyleSheet("background:transparent;")
            self._nm.setText(t("dlg_color_none")); return
        h = clr.hex_for(n); brd = "rgba(102,102,102,153)" if clr.is_light(h) else "transparent"
        self._dot.setStyleSheet(f"background:{h};border-radius:17px;border:2px solid {brd};")
        self._nm.setText(color_t(n))

    def _confirm(self):
        self.accept()

    def get_color(self): return self._sel


# ── Color Button ──────────────────────────────────────────────────────────────

class ColorButton(QPushButton):
    def __init__(self, init="", parent=None):
        super().__init__(parent); self.setObjectName("color_pick_btn")
        self._c = init; self.setMinimumHeight(38); self.setMinimumWidth(180)
        self.clicked.connect(self._open); self._refresh()

    def _refresh(self):
        if self._c:
            self.setIcon(QIcon(_pm(clr.hex_for(self._c), 18))); self.setIconSize(QSize(18, 18))
            self.setText(f"  {color_t(self._c)}")
        else:
            self.setIcon(QIcon()); self.setText(t("dlg_color_choose_btn"))

    def _open(self):
        d = ColorPickerDialog(self._c, self.window())
        if d.exec() == QDialog.DialogCode.Accepted: self._c = d.get_color(); self._refresh()

    def color_name(self): return self._c
    def set_color(self, n): self._c = n; self._refresh()


# ── Product Dialog ────────────────────────────────────────────────────────────

class ProductDialog(ModernDialog):
    def __init__(self, parent=None, product=None):
        super().__init__(parent)
        self.product = _row(product) if product is not None else None
        title = t("dlg_edit_product") if self.product else t("dlg_new_product")
        self.setWindowTitle(title)
        self.setMinimumWidth(500); self.setModal(True)
        self._build(); _style(self)
        if self.product: self._populate(self.product)

    def _build(self):
        is_edit = bool(self.product)
        title   = t("dlg_edit_product") if is_edit else t("dlg_new_product")
        root = QVBoxLayout(self); root.setContentsMargins(24, 24, 24, 20); root.setSpacing(16)

        # Header with close button
        hdr_row = QHBoxLayout()
        hdr = QLabel(title); hdr.setObjectName("dlg_header")
        close_btn = QPushButton("×"); close_btn.setObjectName("btn_close_x")
        close_btn.setFixedSize(32, 32); close_btn.clicked.connect(self.reject)
        hdr_row.addWidget(hdr); hdr_row.addStretch(); hdr_row.addWidget(close_btn)
        root.addLayout(hdr_row)

        # Identity section
        ig = QGroupBox(t("dlg_grp_identity")); fl = QFormLayout(ig)
        fl.setLabelAlignment(Qt.AlignmentFlag.AlignRight); fl.setSpacing(12); fl.setHorizontalSpacing(16)
        self.brand_edit   = _field(t("dlg_ph_brand"))
        self.type_edit    = _field(t("dlg_ph_type"))
        self.color_btn    = ColorButton()
        self.barcode_edit = _field(t("dlg_ph_barcode"))
        self.barcode_edit.setFont(_FONT_MONO)
        fl.addRow(t("dlg_lbl_brand"),   self.brand_edit)
        fl.addRow(t("dlg_lbl_type"),    self.type_edit)
        fl.addRow(t("dlg_lbl_color"),   self.color_btn)
        fl.addRow(t("dlg_lbl_barcode"), self.barcode_edit)
        root.addWidget(ig)

        # Stock section
        sg = QGroupBox(t("dlg_grp_stock")); sf = QFormLayout(sg)
        sf.setLabelAlignment(Qt.AlignmentFlag.AlignRight); sf.setSpacing(12); sf.setHorizontalSpacing(16)
        if not self.product:
            self.initial_stock = QuantitySpin(0, 999_999, 0)
            sf.addRow(t("dlg_lbl_init_stock"), self.initial_stock)
        self.threshold_spin = QuantitySpin(1, 999_999, 5)
        sf.addRow(t("dlg_lbl_alert_when"), self.threshold_spin)
        self.price_edit = _field(t("dlg_ph_sell_price"))
        self.price_edit.setValidator(QDoubleValidator(0.0, 99999.99, 2, self))
        sf.addRow(t("dlg_lbl_sell_price"), self.price_edit)
        root.addWidget(sg)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        cancel = QPushButton(t("op_cancel")); cancel.setObjectName("btn_ghost")
        cancel.setMinimumHeight(40); cancel.clicked.connect(self.reject)
        save = QPushButton(t("dlg_save_product")); save.setObjectName("btn_primary")
        save.setMinimumHeight(40); save.clicked.connect(self._validate)
        btn_row.addStretch(); btn_row.addWidget(cancel); btn_row.addWidget(save)
        root.addLayout(btn_row)

    def _populate(self, p: dict):
        self.brand_edit.setText(p.get("brand", ""))
        self.type_edit.setText(p.get("type", ""))
        self.color_btn.set_color(p.get("color", ""))
        self.barcode_edit.setText(p.get("barcode") or "")
        self.threshold_spin.setValue(p.get("low_stock_threshold", 5))
        sp = p.get("sell_price")
        self.price_edit.setText(f"{sp:.2f}" if sp else "")

    def _validate(self):
        for w, field in [(self.brand_edit, t("dlg_lbl_brand").rstrip(" *")),
                         (self.type_edit,  t("dlg_lbl_type").rstrip(" *"))]:
            if not w.text().strip():
                QMessageBox.warning(self, t("dlg_required_title"),
                                    t("dlg_field_empty", field=field))
                w.setFocus(); return
        self.accept()

    def get_data(self) -> dict:
        try:
            price_val = float(self.price_edit.text().replace(",", ".")) if self.price_edit.text().strip() else None
        except ValueError:
            price_val = None
        d = {
            "brand":               self.brand_edit.text().strip(),
            "type_":               self.type_edit.text().strip(),
            "color":               self.color_btn.color_name(),
            "barcode":             self.barcode_edit.text().strip() or None,
            "low_stock_threshold": self.threshold_spin.value(),
            "sell_price":          price_val if price_val else None,
        }
        if not self.product:
            d["stock"] = self.initial_stock.value()
        return d


# ── Stock Operation Dialog ────────────────────────────────────────────────────

class StockOpDialog(ModernDialog):
    _META_KEYS = {
        "IN":     ("↑", "op_stock_in",  "op_confirm_in",  "btn_confirm_in"),
        "OUT":    ("↓", "op_stock_out", "op_confirm_out", "btn_confirm_out"),
        "ADJUST": ("⇅", "op_adjust",    "op_confirm_adj", "btn_confirm_adj"),
    }

    def __init__(self, parent=None, product=None, operation="IN"):
        super().__init__(parent)
        self.product   = _row(product) if product is not None else {}
        self.operation = operation
        self.setWindowTitle(t(self._META_KEYS[operation][1]))
        self.setMinimumWidth(460); self.setModal(True)
        self._build(); _style(self)

    def _build(self):
        tk = THEME.tokens
        ic, title_key, ctxt_key, cobj = self._META_KEYS[self.operation]
        icol = {"IN": tk.green, "OUT": tk.red, "ADJUST": tk.blue}[self.operation]

        root = QVBoxLayout(self); root.setContentsMargins(24, 24, 24, 20); root.setSpacing(16)

        # Header with close button
        hr = QHBoxLayout()
        il = QLabel(ic); il.setFixedSize(48, 48); il.setAlignment(Qt.AlignmentFlag.AlignCenter)
        il.setStyleSheet(
            f"background:{_rgba(icol, '20')}; color:{icol}; border-radius:24px;"
            "font-size:22pt; font-weight:700;"
        )
        tl = QLabel(t(title_key)); tl.setObjectName("dlg_header")
        close_btn = QPushButton("×"); close_btn.setObjectName("btn_close_x")
        close_btn.setFixedSize(32, 32); close_btn.clicked.connect(self.reject)
        hr.addWidget(il); hr.addSpacing(12); hr.addWidget(tl); hr.addStretch(); hr.addWidget(close_btn)
        root.addLayout(hr)

        # Product card
        p    = self.product
        card = QFrame(); card.setObjectName("op_card")
        cl   = QVBoxLayout(card); cl.setContentsMargins(16, 14, 16, 14); cl.setSpacing(6)

        hc  = clr.hex_for(p.get("color", ""))
        brd = "rgba(102,102,102,153)" if clr.is_light(hc) else "transparent"

        nr = QHBoxLayout(); nr.setSpacing(8)
        dot = QLabel(); dot.setFixedSize(14, 14)
        dot.setStyleSheet(f"background:{hc}; border-radius:7px; border:1px solid {brd};")
        nl = QLabel(
            f"<b>{p.get('brand','')}</b>  ·  {p.get('type','')}  ·  {color_t(p.get('color',''))}"
        )
        nl.setObjectName("card_name")
        nr.addWidget(dot); nr.addWidget(nl); nr.addStretch()
        cl.addLayout(nr)

        mr  = QHBoxLayout()
        cur = QLabel(f"{t('op_current_stock')}  <b style='font-size:14px'>{p.get('stock', 0)}</b>")
        cur.setObjectName("card_meta")
        thr = QLabel(t("op_alert_le", thr=p.get("low_stock_threshold", 5)))
        thr.setObjectName("card_meta_dim")
        mr.addWidget(cur); mr.addStretch(); mr.addWidget(thr)
        cl.addLayout(mr)

        barcode_val = p.get("barcode") or ""
        if barcode_val:
            bl = QLabel(barcode_val); bl.setObjectName("card_barcode"); cl.addWidget(bl)

        root.addWidget(card)

        # Inputs
        fm = QFormLayout()
        fm.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        fm.setSpacing(12); fm.setHorizontalSpacing(16)

        current_stock = p.get("stock", 0)
        if self.operation == "ADJUST":
            self.qty_spin = QuantitySpin(0, 999_999, current_stock)
            fm.addRow(t("op_set_to"), self.qty_spin)
        else:
            self.qty_spin = QuantitySpin(1, 999_999, 1)
            fm.addRow(t("op_quantity"), self.qty_spin)

        self.note_edit = _field(t("op_note_ph"))
        fm.addRow(t("op_note"), self.note_edit)
        root.addLayout(fm)

        # Live preview
        self.prev = QLabel(); self.prev.setObjectName("op_preview")
        self.prev.setAlignment(Qt.AlignmentFlag.AlignCenter); self.prev.setMinimumHeight(60)
        root.addWidget(self.prev)

        # Buttons
        self.cbtn = QPushButton(t(ctxt_key)); self.cbtn.setObjectName(cobj)
        self.cbtn.setMinimumHeight(44); self.cbtn.clicked.connect(self._validate)
        can = QPushButton(t("op_cancel")); can.setObjectName("btn_ghost")
        can.setMinimumHeight(44); can.clicked.connect(self.reject)
        br = QHBoxLayout(); br.setSpacing(8)
        br.addWidget(can); br.addWidget(self.cbtn)
        root.addLayout(br)

        self.qty_spin.valueChanged.connect(self._upd)
        self._upd(self.qty_spin.value())

    def _upd(self, qty):
        tk  = THEME.tokens
        p   = self.product
        cur = p.get("stock", 0)
        thr = p.get("low_stock_threshold", 5)

        if self.operation == "IN":    after, sign = cur + qty, f"+{qty}"
        elif self.operation == "OUT": after, sign = cur - qty, f"−{qty}"
        else:                         after, sign = qty, f"{qty - cur:+d}"

        if after < 0:      fg, badge = tk.red,    t("op_invalid")
        elif after == 0:   fg, badge = tk.red,    t("op_out_of_stock")
        elif after <= thr: fg, badge = tk.orange, t("op_low_stock")
        else:              fg, badge = tk.green,  t("op_ok")

        self.prev.setText(
            f"<span style='color:{tk.t3};font-size:12px'>{t('op_after')}</span>"
            f"<span style='font-size:28pt;font-weight:700;color:{fg}'>{after}</span>"
            f"<span style='color:{tk.t3};font-size:12px'>  {sign}</span>  "
            f"<span style='font-size:11px;font-weight:600;color:{fg};"
            f"background:{_rgba(fg, '18')};padding:4px 10px;border-radius:4px'>{badge}</span>"
        )
        self.cbtn.setEnabled(after >= 0)

    def _validate(self):
        qty = self.qty_spin.value()
        cur = self.product.get("stock", 0)
        if self.operation == "OUT" and qty > cur:
            QMessageBox.warning(self, t("op_insuff_title"),
                                t("op_insuff_body", qty=qty, cur=cur))
            return
        self.accept()

    def get_data(self) -> dict:
        return {"quantity": self.qty_spin.value(), "note": self.note_edit.text().strip()}


# ── Low Stock Alert Dialog ────────────────────────────────────────────────────

class LowStockDialog(ModernDialog):
    product_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("dlg_alerts_title"))
        self.setMinimumSize(640, 480); self.setModal(False)
        self._build(); _style(self); self.refresh()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(24, 24, 24, 20); root.setSpacing(16)

        # Header with close button
        hdr_row = QHBoxLayout()
        hdr = QLabel(t("dlg_alerts_header")); hdr.setObjectName("dlg_header")
        close_btn = QPushButton("×"); close_btn.setObjectName("btn_close_x")
        close_btn.setFixedSize(32, 32); close_btn.clicked.connect(self.close)
        hdr_row.addWidget(hdr); hdr_row.addStretch(); hdr_row.addWidget(close_btn)
        root.addLayout(hdr_row)

        self.table = QTableWidget(); self.table.setObjectName("alert_table")
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            t("col_item"), t("col_barcode"),
            t("col_stock"), t("col_min"), t("col_best_bung"), t("col_status"),
            t("col_color"), t("col_threshold"),
        ])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in range(1, 8):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 60)
        self.table.setColumnWidth(3, 50)
        self.table.setColumnWidth(4, 70)
        self.table.setColumnWidth(5, 70)
        self.table.setColumnWidth(6, 60)
        self.table.setColumnWidth(7, 60)
        self.table.setEditTriggers(self.table.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True); self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False); self.table.doubleClicked.connect(self._dbl)
        root.addWidget(self.table)

        foot = QHBoxLayout()
        note = QLabel(t("dlg_alerts_hint")); note.setObjectName("dim_label")
        cb = QPushButton(t("btn_close")); cb.setObjectName("btn_ghost"); cb.clicked.connect(self.close)
        foot.addWidget(note); foot.addStretch(); foot.addWidget(cb)
        root.addLayout(foot)

    def refresh(self):
        tk   = THEME.tokens
        _mono = QFont("JetBrains Mono", 10, QFont.Weight.Bold)
        items = _alert_svc.get_low_stock_items()
        self.table.setRowCount(len(items)); self._ids: list[int] = []
        self._is_product: list[bool] = []
        for i, item in enumerate(items):
            self._ids.append(item.id)
            self._is_product.append(item.is_product)

            # Color based on severity
            if item.stock == 0:
                fg = tk.red
                status = t("status_out_lbl")
            elif item.stock <= max(1, item.min_stock // 2):
                fg = tk.orange
                status = t("status_critical_lbl")
            else:
                fg = tk.yellow
                status = t("status_low_lbl")

            if item.is_product:
                name = item.display_name
                barcode_val = item.barcode or "—"
                color_val = color_t(item.color)
            else:
                name = f"{item.model_brand or ''} {item.model_name or ''} · {item.part_type_name or ''}"
                barcode_val = item.barcode or "—"
                color_val = "—"

            diff = item.stock - item.min_stock
            diff_str = f"Δ{diff:+d}"

            # Item name
            name_it = QTableWidgetItem(name.strip())
            name_it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(i, 0, name_it)

            # Barcode
            bc_it = QTableWidgetItem(barcode_val)
            bc_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            bc_it.setFont(QFont("JetBrains Mono", 9))
            self.table.setItem(i, 1, bc_it)

            # Stock (colored)
            stk_it = QTableWidgetItem(str(item.stock))
            stk_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            stk_it.setForeground(QColor(fg))
            stk_it.setFont(_mono)
            self.table.setItem(i, 2, stk_it)

            # Min
            min_it = QTableWidgetItem(str(item.min_stock))
            min_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 3, min_it)

            # Δ Difference (colored)
            diff_it = QTableWidgetItem(diff_str)
            diff_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            diff_it.setForeground(QColor(fg))
            diff_it.setFont(_mono)
            self.table.setItem(i, 4, diff_it)

            # Status (colored label)
            stat_it = QTableWidgetItem(status)
            stat_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            stat_it.setForeground(QColor(fg))
            stat_it.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            self.table.setItem(i, 5, stat_it)

            # Color
            clr_it = QTableWidgetItem(color_val)
            clr_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 6, clr_it)

            # Threshold
            thr_it = QTableWidgetItem(str(item.min_stock))
            thr_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 7, thr_it)

            self.table.setRowHeight(i, 44)

    def _dbl(self, idx):
        r = idx.row()
        if 0 <= r < len(self._ids) and self._is_product[r]:
            self.product_selected.emit(self._ids[r]); self.close()
