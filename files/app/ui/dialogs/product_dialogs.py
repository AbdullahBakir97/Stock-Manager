"""dialogs.py — All modal dialogs for Stock Manager Pro."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QDialogButtonBox, QGroupBox, QFrame,
    QMessageBox, QToolButton, QGridLayout, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import (
    QColor, QPainter, QPixmap, QIcon, QFont,
    QLinearGradient, QBrush,
)

from app.core import colors as clr
from app.repositories.product_repo import ProductRepository
from app.services.alert_service import AlertService
from app.core.theme import THEME, _rgba
from app.core.i18n import t, color_t
from app.core.config import ShopConfig

_prod_repo = ProductRepository()
_alert_svc = AlertService()


# ── helpers ───────────────────────────────────────────────────────────────────

def _row(p) -> dict:
    return dict(p) if p is not None else {}

def _field(ph="", txt=""):
    w = QLineEdit(txt); w.setPlaceholderText(ph); w.setMinimumHeight(40); return w

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
    """Set translated text on the Cancel button of a QDialogButtonBox."""
    btn = bb.button(QDialogButtonBox.StandardButton.Cancel)
    if btn: btn.setText(t("op_cancel"))


# ── QuantitySpin — custom +/− widget replacing QSpinBox ──────────────────────

class QuantitySpin(QWidget):
    """Professional +/− spin control with direct keyboard entry."""
    valueChanged = pyqtSignal(int)

    def __init__(self, mn: int = 0, mx: int = 999_999, v: int = 0, parent=None):
        super().__init__(parent)
        self._min = mn; self._max = mx; self._val = v
        # Delay timer: waits 400 ms before starting repeat
        self._delay = QTimer(self); self._delay.setSingleShot(True); self._delay.setInterval(400)
        # Repeat timer: fires every 80 ms while held
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
        self._edit.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))

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
        # If the delay hasn't fired yet the user tapped (not held) — step once
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


# ── Gradient Dialog base ──────────────────────────────────────────────────────

class GradientDialog(QDialog):
    def paintEvent(self, _ev):
        tk = THEME.tokens
        p = QPainter(self)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0.0, QColor(tk.grad_top))
        g.setColorAt(1.0, QColor(tk.grad_bot))
        p.fillRect(self.rect(), QBrush(g)); p.end()


# ── Color Picker ──────────────────────────────────────────────────────────────

class ColorPickerDialog(GradientDialog):
    def __init__(self, cur="", parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("dlg_choose_color")); self.setModal(True); self.setFixedWidth(460)
        self._sel = cur or ""; self._btns: dict[str, QToolButton] = {}
        self._build(); _style(self)

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(24, 24, 24, 20); root.setSpacing(16)
        hdr = QLabel(t("dlg_choose_color")); hdr.setObjectName("dlg_header"); root.addWidget(hdr)

        gw = QWidget()
        grid = QGridLayout(gw); grid.setSpacing(10)
        for i, (name, hex_) in enumerate(clr.PALETTE.items()):
            btn = QToolButton(); btn.setFixedSize(54, 54); btn.setToolTip(color_t(name))
            btn.setCheckable(True); btn.setChecked(name == self._sel)
            idle = "rgba(102,102,102,153)" if clr.is_light(hex_) else "transparent"
            btn.setStyleSheet(
                f"QToolButton{{background:{hex_};border-radius:27px;border:2.5px solid {idle};}}"
                f"QToolButton:hover{{border:3px solid rgba(255,255,255,153);}}"
                f"QToolButton:checked{{border:3.5px solid {THEME.tokens.blue};}}"
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
        self._nm.setText(color_t(n))   # ← translated color name

    def _confirm(self):
        self.accept()

    def get_color(self): return self._sel


# ── Color Button ──────────────────────────────────────────────────────────────

class ColorButton(QPushButton):
    def __init__(self, init="", parent=None):
        super().__init__(parent); self.setObjectName("color_pick_btn")
        self._c = init; self.setMinimumHeight(40); self.setMinimumWidth(180)
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

class ProductDialog(GradientDialog):
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
        root = QVBoxLayout(self); root.setContentsMargins(28, 28, 28, 24); root.setSpacing(20)
        hdr = QLabel(title); hdr.setObjectName("dlg_header"); root.addWidget(hdr)

        ig = QGroupBox(t("dlg_grp_identity")); fl = QFormLayout(ig)
        fl.setLabelAlignment(Qt.AlignmentFlag.AlignRight); fl.setSpacing(10); fl.setHorizontalSpacing(20)
        self.brand_edit   = _field(t("dlg_ph_brand"))
        self.type_edit    = _field(t("dlg_ph_type"))
        self.color_btn    = ColorButton()
        self.barcode_edit = _field(t("dlg_ph_barcode"))
        self.barcode_edit.setFont(QFont("Consolas", 10))
        fl.addRow(t("dlg_lbl_brand"),   self.brand_edit)
        fl.addRow(t("dlg_lbl_type"),    self.type_edit)
        fl.addRow(t("dlg_lbl_color"),   self.color_btn)
        fl.addRow(t("dlg_lbl_barcode"), self.barcode_edit)
        root.addWidget(ig)

        sg = QGroupBox(t("dlg_grp_stock")); sf = QFormLayout(sg)
        sf.setLabelAlignment(Qt.AlignmentFlag.AlignRight); sf.setSpacing(10); sf.setHorizontalSpacing(20)
        if not self.product:
            self.initial_stock = QuantitySpin(0, 999_999, 0)
            sf.addRow(t("dlg_lbl_init_stock"), self.initial_stock)
        self.threshold_spin = QuantitySpin(1, 999_999, 5)
        sf.addRow(t("dlg_lbl_alert_when"), self.threshold_spin)
        self.price_edit = _field(t("dlg_ph_sell_price"))
        self.price_edit.setValidator(QDoubleValidator(0.0, 99999.99, 2, self))
        sf.addRow(t("dlg_lbl_sell_price"), self.price_edit)
        root.addWidget(sg)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok = bb.button(QDialogButtonBox.StandardButton.Ok)
        ok.setText(t("dlg_save_product")); ok.setObjectName("btn_primary")
        _cancel_btn(bb)
        bb.accepted.connect(self._validate); bb.rejected.connect(self.reject)
        root.addWidget(bb)

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

class StockOpDialog(GradientDialog):
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

        root = QVBoxLayout(self); root.setContentsMargins(28, 28, 28, 24); root.setSpacing(18)

        # ── Header ──
        hr = QHBoxLayout()
        il = QLabel(ic); il.setFixedSize(58, 58); il.setAlignment(Qt.AlignmentFlag.AlignCenter)
        il.setStyleSheet(
            f"background:{_rgba(icol, '25')}; color:{icol}; border-radius:29px;"
            "font-size:26pt; font-weight:900;"
        )
        tl = QLabel(t(title_key)); tl.setObjectName("dlg_header")
        hr.addWidget(il); hr.addSpacing(14); hr.addWidget(tl); hr.addStretch()
        root.addLayout(hr)

        # ── Product card ──
        p    = self.product
        card = QFrame(); card.setObjectName("op_card")
        cl   = QVBoxLayout(card); cl.setContentsMargins(16, 14, 16, 14); cl.setSpacing(6)

        hc  = clr.hex_for(p.get("color", ""))
        brd = "rgba(102,102,102,153)" if clr.is_light(hc) else "transparent"

        nr = QHBoxLayout(); nr.setSpacing(9)
        dot = QLabel(); dot.setFixedSize(14, 14)
        dot.setStyleSheet(f"background:{hc}; border-radius:7px; border:1px solid {brd};")
        nl = QLabel(
            f"<b>{p.get('brand','')}</b>  ·  {p.get('type','')}  ·  {color_t(p.get('color',''))}"
        )
        nl.setObjectName("card_name")
        nr.addWidget(dot); nr.addWidget(nl); nr.addStretch()
        cl.addLayout(nr)

        mr  = QHBoxLayout()
        cur = QLabel(f"{t('op_current_stock')}  <b style='font-size:13pt'>{p.get('stock', 0)}</b>")
        cur.setObjectName("card_meta")
        thr = QLabel(t("op_alert_le", thr=p.get("low_stock_threshold", 5)))
        thr.setObjectName("card_meta_dim")
        mr.addWidget(cur); mr.addStretch(); mr.addWidget(thr)
        cl.addLayout(mr)

        barcode_val = p.get("barcode") or ""
        if barcode_val:
            bl = QLabel(barcode_val); bl.setObjectName("card_barcode"); cl.addWidget(bl)

        root.addWidget(card)

        # ── Inputs ──
        fm = QFormLayout()
        fm.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        fm.setSpacing(10); fm.setHorizontalSpacing(20)

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

        # ── Live preview ──
        self.prev = QLabel(); self.prev.setObjectName("op_preview")
        self.prev.setAlignment(Qt.AlignmentFlag.AlignCenter); self.prev.setMinimumHeight(64)
        root.addWidget(self.prev)

        # ── Buttons ──
        self.cbtn = QPushButton(t(ctxt_key)); self.cbtn.setObjectName(cobj)
        self.cbtn.setMinimumHeight(46); self.cbtn.clicked.connect(self._validate)
        can = QPushButton(t("op_cancel")); can.setObjectName("btn_ghost")
        can.setMinimumHeight(46); can.clicked.connect(self.reject)
        br = QHBoxLayout(); br.setSpacing(10)
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
            f"<span style='color:{tk.t3};font-size:9pt'>{t('op_after')}</span>"
            f"<span style='font-size:28pt;font-weight:900;color:{fg}'>{after}</span>"
            f"<span style='color:{tk.t3};font-size:9pt'>  {sign}</span>  "
            f"<span style='font-size:8pt;font-weight:700;color:{fg};"
            f"background:{_rgba(fg, '22')};padding:3px 10px;border-radius:10px'>{badge}</span>"
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

class LowStockDialog(GradientDialog):
    product_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("dlg_alerts_title"))
        self.setMinimumSize(640, 480); self.setModal(False)
        self._build(); _style(self); self.refresh()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(24, 24, 24, 20); root.setSpacing(14)
        hdr = QLabel(t("dlg_alerts_header")); hdr.setObjectName("dlg_header"); root.addWidget(hdr)

        self.table = QTableWidget(); self.table.setObjectName("alert_table")
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            t("col_brand"), t("col_type"), t("col_color"),
            t("col_barcode"), t("col_stock"), t("col_threshold"),
        ])
        hh = self.table.horizontalHeader(); hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
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
        items = _alert_svc.get_low_stock_items()
        self.table.setRowCount(len(items)); self._ids: list[int] = []
        self._is_product: list[bool] = []
        for i, item in enumerate(items):
            self._ids.append(item.id)
            self._is_product.append(item.is_product)
            fg = tk.red if item.stock == 0 else (
                tk.orange if item.stock <= max(1, item.min_stock // 2) else tk.yellow
            )
            if item.is_product:
                brand_or_name = item.brand
                type_or_part  = item.name
                color_val     = color_t(item.color)
                barcode_val   = item.barcode or "—"
            else:
                brand_or_name = item.model_brand or item.model_name
                type_or_part  = item.part_type_name
                color_val     = item.part_type_color or "—"
                barcode_val   = "—"
            vals = [brand_or_name, type_or_part, color_val,
                    barcode_val, str(item.stock), str(item.min_stock)]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                it.setForeground(QColor(fg)); self.table.setItem(i, j, it)
            self.table.setRowHeight(i, 42)

    def _dbl(self, idx):
        r = idx.row()
        if 0 <= r < len(self._ids) and self._is_product[r]:
            self.product_selected.emit(self._ids[r]); self.close()
