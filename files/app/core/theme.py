"""
theme.py — Gradient design system for Stock Manager Pro.

DARK  : #1E2035 deep indigo-charcoal → #2A2D48 soft slate-purple
LIGHT : #F5F3EF warm cream            → #E9ECF7 cool periwinkle-silver

FIX: All 8-digit hex replaced with rgba() — Qt QSS does NOT support #RRGGBBAA.
     QColor helper qc() uses integer RGBA constructor (not string) to avoid the
     wrong #AARRGGBB interpretation.
"""
from __future__ import annotations
from dataclasses import dataclass
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QLinearGradient, QColor, QBrush
from PyQt6.QtCore import Qt


# ── Color utilities ────────────────────────────────────────────────────────────

def _rgba(hex6: str, alpha_hex: str) -> str:
    """Return 'rgba(r,g,b,a)' string usable in Qt QSS — the ONLY valid alpha format."""
    h = hex6.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    a = int(alpha_hex, 16)
    return f"rgba({r},{g},{b},{a})"


def qc(hex6: str, alpha: int) -> QColor:
    """QColor from #RRGGBB + integer alpha (0-255). Avoids the AARRGGBB string trap."""
    h = hex6.lstrip('#')
    return QColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


# ── Token dataclass ────────────────────────────────────────────────────────────

@dataclass
class Tokens:
    grad_top: str; grad_bot: str
    card: str;  card2: str
    border: str; border2: str
    t1: str; t2: str; t3: str; t4: str
    blue:   str = "#4A9EFF"
    green:  str = "#32D583"
    orange: str = "#FF9F3A"
    red:    str = "#FF5A52"
    yellow: str = "#C8940A"   # darker yellow — readable on both modes
    purple: str = "#C17BFF"
    is_dark: bool = True


DARK = Tokens(
    grad_top="#1E2035", grad_bot="#2A2D48",
    card="#252840",     card2="#2F324E",
    border="#3A3D5C",   border2="#4E5278",
    t1="#F0F2FF", t2="#B8BCDC", t3="#8A8FB8", t4="#4A4E70",
    blue="#4A9EFF", green="#32D583", orange="#FF9F3A",
    red="#FF5A52", yellow="#FFD23F", purple="#C17BFF",
    is_dark=True,
)

LIGHT = Tokens(
    grad_top="#F0EEF8", grad_bot="#E4E8F8",
    card="#FFFFFF",     card2="#F2F0FC",
    border="#DDD8F0",   border2="#B8B2DC",
    t1="#18182E", t2="#32325A", t3="#6060A0", t4="#A0A0C8",
    blue="#2979FF", green="#00A85A", orange="#D06000",
    red="#D32F2F", yellow="#9A7000", purple="#7B2FBE",
    is_dark=False,
)


# ── Gradient background widget ────────────────────────────────────────────────

class GradientBackground(QWidget):
    """Central widget painting a vertical gradient — children stay transparent."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

    def paintEvent(self, _ev):
        t = THEME.tokens
        p = QPainter(self)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0.0, QColor(t.grad_top))
        g.setColorAt(1.0, QColor(t.grad_bot))
        p.fillRect(self.rect(), QBrush(g))
        p.end()


# ── Stylesheet generator ───────────────────────────────────────────────────────

def _ss(t: Tokens) -> str:
    alt    = "#2C304C" if t.is_dark else "#ECEAF6"
    scr    = "#4A4E70" if t.is_dark else "#C0BAE0"
    inp_bg = "#1A1D38" if t.is_dark else "#FFFFFF"

    # ── pre-compute every rgba value so the f-string stays clean ──────────────
    # Blue
    b_EE = _rgba(t.blue, 'EE'); b_BB = _rgba(t.blue, 'BB')
    b_CC = _rgba(t.blue, 'CC'); b_99 = _rgba(t.blue, '99')
    b_60 = _rgba(t.blue, '60'); b_55 = _rgba(t.blue, '55')
    b_45 = _rgba(t.blue, '45'); b_40 = _rgba(t.blue, '40')
    b_35 = _rgba(t.blue, '35'); b_30 = _rgba(t.blue, '30')
    b_28 = _rgba(t.blue, '28'); b_20 = _rgba(t.blue, '20')
    b_15 = _rgba(t.blue, '15')

    # Green
    g_60 = _rgba(t.green, '60'); g_55 = _rgba(t.green, '55')
    g_45 = _rgba(t.green, '45'); g_40 = _rgba(t.green, '40')
    g_35 = _rgba(t.green, '35'); g_30 = _rgba(t.green, '30')
    g_28 = _rgba(t.green, '28'); g_20 = _rgba(t.green, '20')

    # Red
    r_60 = _rgba(t.red, '60'); r_55 = _rgba(t.red, '55')
    r_45 = _rgba(t.red, '45'); r_40 = _rgba(t.red, '40')
    r_35 = _rgba(t.red, '35'); r_30 = _rgba(t.red, '30')
    r_28 = _rgba(t.red, '28'); r_15 = _rgba(t.red, '15')

    # Orange
    o_20 = _rgba(t.orange, '20'); o_55 = _rgba(t.orange, '55')

    # Card gradient stops
    c_88  = _rgba(t.card,  '88')
    c2_88 = _rgba(t.card2, '88')

    # Operation button borders (solid, full-opacity card bg so Windows can't fallback)
    op_in_bg   = t.card
    op_out_bg  = t.card
    op_adj_bg  = t.card
    op_in_brd  = g_60
    op_out_brd = r_60
    op_adj_brd = b_60

    return f"""
/* ── Global ──────────────────────────────────────────────── */
* {{
    font-family: 'Segoe UI', 'SF Pro Text', 'Helvetica Neue', sans-serif;
    outline: none;
}}
QWidget {{
    background: transparent;
    color: {t.t1};
}}
QMainWindow {{ background: {t.grad_top}; }}
QDialog {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {t.grad_top}, stop:1 {t.grad_bot});
}}

/* ── App title ────────────────────────────────────────────── */
QLabel#app_title {{
    font-size: 21pt; font-weight: 900; color: {t.t1}; letter-spacing: -0.3px;
}}

/* ── Summary cards ────────────────────────────────────────── */
QFrame#summary_card {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {t.card}, stop:1 {t.card2});
    border: 1.5px solid {t.border};
    border-radius: 20px; min-height: 90px;
}}
QLabel#card_value {{
    font-size: 30pt; font-weight: 900; color: {t.t1};
}}
QLabel#card_label {{
    font-size: 8pt; font-weight: 600; color: {t.t3}; letter-spacing: 0.9px;
}}

/* ── Search bar ───────────────────────────────────────────── */
QLineEdit#search_bar {{
    background: {inp_bg}; color: {t.t1};
    border: 1.5px solid {t.border}; border-radius: 13px;
    padding: 8px 14px; font-size: 10pt; min-height: 42px;
    selection-background-color: {t.blue};
}}
QLineEdit#search_bar:focus {{ border-color: {t.blue}; }}

/* ── Icon / mode square buttons ───────────────────────────── */
QPushButton#icon_btn, QPushButton#mode_btn {{
    background-color: {t.card2};
    color: {t.t1}; border: 1.5px solid {t.border};
    border-radius: 13px;
    font-size: 17pt; font-weight: 900;
    min-width: 44px; max-width: 44px;
    min-height: 44px; max-height: 44px;
    padding: 0;
}}
QPushButton#icon_btn:hover, QPushButton#mode_btn:hover {{
    background-color: {t.border}; border-color: {t.border2};
}}
QPushButton#icon_btn:pressed, QPushButton#mode_btn:pressed {{
    background-color: {t.border2};
}}

/* ── Language switcher (segmented control) ────────────────── */
QFrame#lang_bar {{
    background: {t.card}; border: 1.5px solid {t.border};
    border-radius: 12px; padding: 2px;
}}
QPushButton#lang_btn {{
    background: transparent; color: {t.t3};
    border: none; border-radius: 8px;
    font-size: 9pt; font-weight: 600;
    padding: 0px 4px;
}}
QPushButton#lang_btn:hover {{
    background: {t.border}; color: {t.t1};
}}
QPushButton#lang_btn_active {{
    background: {t.blue}; color: #FFFFFF;
    border: none; border-radius: 8px;
    font-size: 9pt; font-weight: 800;
    padding: 0px 4px;
}}

/* ── Primary button ───────────────────────────────────────── */
QPushButton#btn_primary {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {b_EE}, stop:1 {b_BB});
    color: #FFFFFF; border: none; border-radius: 13px;
    font-size: 10pt; font-weight: 700;
    padding: 9px 22px; min-height: 44px;
}}
QPushButton#btn_primary:hover   {{ background: {b_CC}; }}
QPushButton#btn_primary:pressed {{ background: {b_99}; }}

/* ── Secondary button ─────────────────────────────────────── */
QPushButton#btn_secondary {{
    background: {b_20}; color: {t.blue};
    border: 1px solid {b_40}; border-radius: 10px;
    font-size: 9pt; font-weight: 600;
    padding: 6px 14px; min-height: 34px;
}}
QPushButton#btn_secondary:hover {{ background: {b_35}; }}

/* ── QuantitySpin +/− controls ───────────────────────────── */
QPushButton#spin_minus, QPushButton#spin_plus {{
    background: {t.blue}; color: #FFFFFF;
    border: none;
    border-radius: 22px;
    font-size: 22pt; font-weight: 400;
    padding: 0 0 2px 0;
}}
QPushButton#spin_minus:hover, QPushButton#spin_plus:hover {{
    background: #3A96FF;
}}
QPushButton#spin_minus:pressed, QPushButton#spin_plus:pressed {{
    background: #006ED9;
}}
QLineEdit#spin_edit {{
    background: {inp_bg}; color: {t.t1};
    border: 1.5px solid {t.border};
    border-radius: 10px;
    font-size: 14pt; font-weight: 700;
}}

/* ── Ghost button ─────────────────────────────────────────── */
QPushButton#btn_ghost {{
    background: transparent; color: {t.t3};
    border: 1px solid {t.border}; border-radius: 10px;
    padding: 6px 14px; min-height: 34px;
}}
QPushButton#btn_ghost:hover {{ background: {t.card2}; }}

/* ── Alert states ─────────────────────────────────────────── */
QPushButton#alert_ok {{
    background: {g_20}; color: {t.green};
    border: 1.5px solid {g_55}; border-radius: 13px;
    font-weight: 700; font-size: 9pt; padding: 7px 16px; min-height: 40px;
}}
QPushButton#alert_warn {{
    background: {o_20}; color: {t.orange};
    border: 1.5px solid {o_55}; border-radius: 13px;
    font-weight: 700; font-size: 9pt; padding: 7px 16px; min-height: 40px;
}}
QPushButton#alert_critical {{
    background: {r_28}; color: {t.red};
    border: 1.5px solid {r_55}; border-radius: 13px;
    font-weight: 700; font-size: 9pt; padding: 7px 16px; min-height: 40px;
}}

/* ── Operation buttons (detail panel) ────────────────────── */
QPushButton[objectName="op_in"] {{
    background: {op_in_bg}; color: {t.green};
    border: 1.5px solid {op_in_brd};
    border-left: 4px solid {t.green};
    border-radius: 13px; font-weight: 700; font-size: 10pt;
    text-align: left; padding-left: 18px; min-height: 48px;
}}
QPushButton[objectName="op_in"]:hover   {{ background: {g_35}; border-left-color: {t.green}; }}
QPushButton[objectName="op_in"]:disabled {{
    background: transparent; color: {t.t4};
    border: 1.5px solid {t.border}; border-left-color: {t.border};
}}
QPushButton[objectName="op_out"] {{
    background: {op_out_bg}; color: {t.red};
    border: 1.5px solid {op_out_brd};
    border-left: 4px solid {t.red};
    border-radius: 13px; font-weight: 700; font-size: 10pt;
    text-align: left; padding-left: 18px; min-height: 48px;
}}
QPushButton[objectName="op_out"]:hover   {{ background: {r_35}; border-left-color: {t.red}; }}
QPushButton[objectName="op_out"]:disabled {{
    background: transparent; color: {t.t4};
    border: 1.5px solid {t.border}; border-left-color: {t.border};
}}
QPushButton[objectName="op_adj"] {{
    background: {op_adj_bg}; color: {t.blue};
    border: 1.5px solid {op_adj_brd};
    border-left: 4px solid {t.blue};
    border-radius: 13px; font-weight: 700; font-size: 10pt;
    text-align: left; padding-left: 18px; min-height: 48px;
}}
QPushButton[objectName="op_adj"]:hover   {{ background: {b_35}; border-left-color: {t.blue}; }}
QPushButton[objectName="op_adj"]:disabled {{
    background: transparent; color: {t.t4};
    border: 1.5px solid {t.border}; border-left-color: {t.border};
}}

/* ── Edit / Delete ────────────────────────────────────────── */
QPushButton#mgmt_edit {{
    background: {b_15}; color: {t.blue};
    border: 1.5px solid {b_40}; border-radius: 11px;
    font-size: 9pt; font-weight: 600; min-height: 28px; padding: 4px 12px;
}}
QPushButton#mgmt_edit:hover {{ background: {b_28}; }}
QPushButton#mgmt_edit:disabled {{ background: transparent; color: {t.t4}; border-color: {t.border}; }}

QPushButton#mgmt_del {{
    background: {r_15}; color: {t.red};
    border: 1.5px solid {r_40}; border-radius: 11px;
    font-size: 9pt; font-weight: 600; min-height: 28px; padding: 4px 12px;
}}
QPushButton#mgmt_del:hover {{ background: {r_30}; border-color: {r_60}; }}
QPushButton#mgmt_del:disabled {{ background: transparent; color: {t.t4}; border-color: {t.border}; }}

/* ── Dialog confirm buttons ───────────────────────────────── */
QPushButton#btn_confirm_in {{
    background: {g_28}; color: {t.green};
    border: 1px solid {g_45}; border-radius: 12px;
    font-weight: 700; min-height: 46px;
}}
QPushButton#btn_confirm_in:hover    {{ background: {g_40}; }}
QPushButton#btn_confirm_in:disabled {{ background: {t.card2}; color: {t.t4}; border-color: {t.border}; }}
QPushButton#btn_confirm_out {{
    background: {r_28}; color: {t.red};
    border: 1px solid {r_45}; border-radius: 12px;
    font-weight: 700; min-height: 46px;
}}
QPushButton#btn_confirm_out:hover    {{ background: {r_40}; }}
QPushButton#btn_confirm_out:disabled {{ background: {t.card2}; color: {t.t4}; border-color: {t.border}; }}
QPushButton#btn_confirm_adj {{
    background: {b_28}; color: {t.blue};
    border: 1px solid {b_45}; border-radius: 12px;
    font-weight: 700; min-height: 46px;
}}
QPushButton#btn_confirm_adj:hover {{ background: {b_40}; }}

/* ── Color picker button ──────────────────────────────────── */
QPushButton#color_pick_btn {{
    background: {inp_bg}; color: {t.t1};
    border: 1.5px solid {t.border2}; border-radius: 10px;
    text-align: left; padding-left: 12px;
    font-size: 10pt; min-height: 40px;
}}
QPushButton#color_pick_btn:hover {{ background: {t.card2}; }}

/* ── Default fallback button ──────────────────────────────── */
QPushButton {{
    background-color: {t.card}; color: {t.t1};
    border: 1px solid {t.border}; border-radius: 10px;
    padding: 7px 14px; font-size: 10pt; min-height: 36px;
}}
QPushButton:hover   {{ background-color: {t.card2}; }}
QPushButton:pressed {{ background-color: {t.border}; }}
QPushButton:disabled {{ background-color: {t.card2}; color: {t.t4}; border-color: {t.border}; }}

/* ── Checkbox ─────────────────────────────────────────────── */
QCheckBox {{ color: {t.t1}; spacing: 7px; font-size: 9pt; }}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 1.5px solid {t.border2}; border-radius: 5px; background: {t.card};
}}
QCheckBox::indicator:checked {{ background: {t.blue}; border-color: {t.blue}; }}

/* ── Tabs ─────────────────────────────────────────────────── */
QTabWidget#main_tabs::pane {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {t.card}, stop:1 {t.card2});
    border: 1.5px solid {t.border}; border-radius: 20px; top: -1px;
}}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    background: transparent; color: {t.t3};
    padding: 11px 24px; font-weight: 600; font-size: 10pt;
    border: none; border-bottom: 2.5px solid transparent; margin-right: 2px;
}}
QTabBar::tab:selected {{ color: {t.blue}; border-bottom-color: {t.blue}; }}
QTabBar::tab:hover    {{ color: {t.t1}; }}

/* ── Tables ───────────────────────────────────────────────── */
QTableWidget {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {t.card}, stop:1 {t.card2});
    alternate-background-color: {alt};
    color: {t.t1}; gridline-color: transparent;
    border: none; border-radius: 16px;
    selection-background-color: {b_30}; outline: none;
}}
QTableWidget::item {{ padding: 4px 8px; border: none; }}
QTableWidget::item:selected {{ background: {b_30}; color: {t.t1}; }}
QHeaderView {{ background: transparent; }}
QHeaderView::section {{
    background: transparent; color: {t.t3};
    font-weight: 700; font-size: 8pt; letter-spacing: 0.7px;
    border: none; border-bottom: 1px solid {t.border}; padding: 10px 8px;
}}

/* ── Inputs (non-search) ──────────────────────────────────── */
QLineEdit, QSpinBox {{
    background: {inp_bg}; color: {t.t1};
    border: 1.5px solid {t.border2}; border-radius: 10px;
    padding: 7px 12px; font-size: 10pt; min-height: 38px;
    selection-background-color: {t.blue};
}}
QLineEdit:focus, QSpinBox:focus {{ border-color: {t.blue}; }}

/* ── SpinBox — clean minimal arrows ──────────────────────── */
QSpinBox {{ padding-right: 28px; }}
QSpinBox::up-button {{
    subcontrol-origin: border; subcontrol-position: top right;
    width: 24px; height: 19px;
    border: none; border-left: 1px solid {t.border2}; border-top-right-radius: 9px;
    background: {t.card2};
}}
QSpinBox::up-button:hover   {{ background: {t.border2}; }}
QSpinBox::up-button:pressed {{ background: {t.border}; }}
QSpinBox::up-arrow {{
    width: 8px; height: 8px;
    border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-bottom: 5px solid {t.t2};
}}
QSpinBox::down-button {{
    subcontrol-origin: border; subcontrol-position: bottom right;
    width: 24px; height: 19px;
    border: none; border-left: 1px solid {t.border2}; border-bottom-right-radius: 9px;
    background: {t.card2};
}}
QSpinBox::down-button:hover   {{ background: {t.border2}; }}
QSpinBox::down-button:pressed {{ background: {t.border}; }}
QSpinBox::down-arrow {{
    width: 8px; height: 8px;
    border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-top: 5px solid {t.t2};
}}

/* ── GroupBox ─────────────────────────────────────────────── */
QGroupBox {{
    font-weight: 700; font-size: 9pt; color: {t.t3};
    border: 1px solid {t.border}; border-radius: 14px;
    margin-top: 14px; padding-top: 12px;
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {c_88}, stop:1 {c2_88});
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 14px; padding: 0 6px; color: {t.t3}; }}

/* ── Dialog inner elements ────────────────────────────────── */
QLabel#dlg_header {{ font-size: 18pt; font-weight: 800; color: {t.t1}; padding-bottom: 4px; }}
QFrame#op_card {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {t.card}, stop:1 {t.card2});
    border: 1px solid {t.border}; border-radius: 16px;
}}
QFrame#preview_frame {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {t.card}, stop:1 {t.card2});
    border: 1px solid {t.border}; border-radius: 14px;
}}
QLabel#card_name    {{ font-size: 11pt; color: {t.t1}; font-weight: 600; }}
QLabel#card_meta    {{ font-size: 10pt; color: {t.t1}; }}
QLabel#card_meta_dim {{ font-size: 9pt; color: {t.t3}; }}
QLabel#card_barcode {{ font-size: 9pt; color: {t.t4}; font-family: Consolas; }}
QLabel#op_preview   {{ padding: 8px; }}
QLabel#dim_label    {{ font-size: 8pt; color: {t.t3}; }}
QLabel#preview_name_lbl {{ font-size: 12pt; font-weight: 600; color: {t.t1}; }}
QLabel#picker_title {{ font-size: 14pt; font-weight: 700; color: {t.t1}; }}
QLabel#section_caption {{ font-size: 9pt; color: {t.t3}; }}
QDialogButtonBox QPushButton {{ min-width: 100px; }}

/* ── Detail panel ─────────────────────────────────────────── */
QScrollArea#detail_scroll_area {{ border: none; background: transparent; }}
QScrollArea#detail_scroll_area > QWidget > QWidget {{ background: transparent; }}
QFrame#detail_card {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {t.card}, stop:1 {t.card2});
    border: 1.5px solid {t.border}; border-radius: 20px;
}}
QLabel#detail_product_name {{ font-size: 13pt; font-weight: 800; color: {t.t1}; }}
QLabel#detail_color_name   {{ font-size: 10pt; color: {t.t2}; }}
QLabel#detail_barcode      {{ font-size: 9pt; color: {t.t3}; font-family: Consolas; }}
QLabel#detail_updated      {{ font-size: 8pt; color: {t.t4}; }}
QLabel#detail_section_hdr  {{ font-size: 8pt; font-weight: 700; color: {t.t3}; letter-spacing: 0.8px; }}
QLabel#big_stock           {{ font-size: 58pt; font-weight: 900; padding: 4px 0; }}
QLabel#detail_threshold    {{ font-size: 9pt; color: {t.t3}; }}

/* ── Mini txn list ────────────────────────────────────────── */
QScrollArea#txn_scroll_area {{
    border: 1.5px solid {t.border}; border-radius: 14px; background: {t.card};
}}
QScrollArea#txn_scroll_area > QWidget > QWidget {{ background: {t.card}; }}
QFrame#txn_row     {{ background: {t.card};  border-bottom: 1px solid {t.border}; }}
QFrame#txn_row_alt {{ background: {alt};     border-bottom: 1px solid {t.border}; }}
QLabel#txn_after {{ font-size: 9pt; color: {t.t3}; }}
QLabel#txn_time  {{ font-size: 8pt; color: {t.t4}; font-family: Consolas; }}
QLabel#txn_empty {{ font-size: 9pt; color: {t.t4}; }}

/* ── Alert table ──────────────────────────────────────────── */
QTableWidget#alert_table {{
    background: {t.card}; alternate-background-color: {t.card2};
    color: {t.t1}; border: 1px solid {t.border}; border-radius: 12px;
    selection-background-color: {b_30};
}}

/* ── Splitter ─────────────────────────────────────────────── */
QSplitter::handle {{ background: {t.border}; width: 1px; height: 1px; }}

/* ── Status bar ───────────────────────────────────────────── */
QStatusBar {{ background: transparent; color: {t.t4}; font-size: 8pt; border: none; }}
QStatusBar::item {{ border: none; }}

/* ── Scrollbars ───────────────────────────────────────────── */
QScrollBar:vertical   {{ width: 6px; background: transparent; margin: 0; }}
QScrollBar::handle:vertical   {{ background: {scr}; border-radius: 3px; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ height: 6px; background: transparent; }}
QScrollBar::handle:horizontal {{ background: {scr}; border-radius: 3px; min-width: 24px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
"""


class ThemeManager:
    def __init__(self):
        self._dark = True
        self._t = DARK
        self._targets: list = []

    @property
    def is_dark(self): return self._dark
    @property
    def tokens(self) -> Tokens: return self._t

    def toggle(self):
        self._dark = not self._dark
        self._t = DARK if self._dark else LIGHT
        ss = self.stylesheet()
        for w in list(self._targets):
            try:   w.setStyleSheet(ss); w.update()
            except RuntimeError: self._targets.remove(w)

    def stylesheet(self) -> str: return _ss(self._t)

    def apply(self, widget):
        widget.setStyleSheet(self.stylesheet())
        self.register(widget)

    def register(self, widget):
        if widget not in self._targets:
            self._targets.append(widget)


THEME = ThemeManager()
