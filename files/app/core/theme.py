"""
theme.py — Professional design system for Stock Manager Pro.

Four theme presets:
  DARK      — Original indigo-charcoal gradient
  LIGHT     — Original warm cream/periwinkle
  PRO_DARK  — Modern charcoal (#0A0A0A) with emerald accents
  PRO_LIGHT — Clean white (#FFFFFF) with emerald accents

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
    yellow: str = "#C8940A"
    purple: str = "#C17BFF"
    is_dark: bool = True


# ── Original themes ───────────────────────────────────────────────────────────

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

# ── Professional themes ───────────────────────────────────────────────────────

PRO_DARK = Tokens(
    grad_top="#0A0A0A", grad_bot="#0F0F0F",
    card="#141414",     card2="#1F1F1F",
    border="#262626",   border2="#333333",
    t1="#FFFFFF", t2="#A3A3A3", t3="#666666", t4="#404040",
    blue="#3B82F6", green="#10B981", orange="#F59E0B",
    red="#EF4444", yellow="#F59E0B", purple="#8B5CF6",
    is_dark=True,
)

PRO_LIGHT = Tokens(
    grad_top="#FFFFFF", grad_bot="#F5F5F5",
    card="#FFFFFF",     card2="#F5F5F5",
    border="#E5E5E5",   border2="#D4D4D4",
    t1="#171717", t2="#525252", t3="#A3A3A3", t4="#D4D4D4",
    blue="#2563EB", green="#059669", orange="#D97706",
    red="#DC2626", yellow="#D97706", purple="#7C3AED",
    is_dark=False,
)

# All available theme presets
THEMES = {
    "dark":      DARK,
    "light":     LIGHT,
    "pro_dark":  PRO_DARK,
    "pro_light": PRO_LIGHT,
}


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
    alt    = "#1A1A1A" if t.is_dark else "#FAFAFA"
    scr    = "#333333" if t.is_dark else "#D4D4D4"
    inp_bg = "#0D0D0D" if t.is_dark else "#FFFFFF"

    # Check if this is a Pro theme (darker backgrounds)
    is_pro = t.grad_top in ("#0A0A0A", "#FFFFFF")

    if not is_pro:
        # Original theme alternating colors
        alt    = "#2C304C" if t.is_dark else "#ECEAF6"
        scr    = "#4A4E70" if t.is_dark else "#C0BAE0"
        inp_bg = "#1A1D38" if t.is_dark else "#FFFFFF"

    # ── pre-compute every rgba value ─────────────────────────────────────────
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

    # Operation button backgrounds
    op_in_bg   = t.card
    op_out_bg  = t.card
    op_adj_bg  = t.card
    op_in_brd  = g_60
    op_out_brd = r_60
    op_adj_brd = b_60

    # Accent for primary buttons — use green for Pro, blue for original
    acc     = t.green if is_pro else t.blue
    acc_EE  = _rgba(acc, 'EE')
    acc_BB  = _rgba(acc, 'BB')
    acc_CC  = _rgba(acc, 'CC')
    acc_99  = _rgba(acc, '99')
    acc_20  = _rgba(acc, '20')
    acc_30  = _rgba(acc, '30')
    acc_40  = _rgba(acc, '40')

    # Border radius — Pro uses smaller radii for sharper look
    br_card  = "8px"  if is_pro else "20px"
    br_btn   = "6px"  if is_pro else "13px"
    br_input = "6px"  if is_pro else "13px"
    br_table = "8px"  if is_pro else "16px"
    br_tab   = "8px"  if is_pro else "20px"

    # Sidebar active — Pro uses green accent, original uses blue
    sb_active_bg  = acc_20
    sb_active_fg  = acc
    sb_active_brd = acc

    # Matrix grid lines — visible on both dark and light
    matrix_grid = "#555555" if t.is_dark else "#CCCCCC"

    return f"""
/* ── Global ──────────────────────────────────────────────── */
* {{
    font-family: 'Segoe UI', 'SF Pro Display', -apple-system, 'Helvetica Neue', sans-serif;
    outline: none;
}}
QWidget {{
    background: transparent;
    color: {t.t1};
    font-size: 13px;
}}
QMainWindow {{ background: {t.grad_top}; }}
QDialog {{
    background: {t.grad_top};
    color: {t.t1};
}}
QLabel {{
    background: transparent;
    color: {t.t1};
}}

/* ── Header bar ───────────────────────────────────────────── */
QFrame#header_bar {{
    background: {t.card};
    border-bottom: 1px solid {t.border};
    border-radius: 0;
}}
QLabel#app_title {{
    font-size: 15px; font-weight: 600; color: {t.t1}; letter-spacing: -0.5px;
}}
QPushButton#header_icon {{
    background: transparent;
    color: {t.t2};
    border: none;
    border-radius: 6px;
    font-size: 14px;
    min-width: 34px; max-width: 34px;
    min-height: 34px; max-height: 34px;
    padding: 0;
}}
QPushButton#header_icon:hover {{
    background: {t.card2};
    color: {t.t1};
}}
QPushButton#header_icon:pressed {{
    background: {t.border};
}}
QLabel#notif_badge {{
    background: {t.red};
    color: #FFFFFF;
    font-size: 9px;
    font-weight: 700;
    border-radius: 9px;
    border: 2px solid {t.card};
}}

/* ── Summary cards ────────────────────────────────────────── */
QFrame#summary_card {{
    background: {t.card};
    border: 1px solid {t.border};
    border-radius: 12px; min-height: 80px;
    padding: 16px 20px;
}}
QFrame#summary_card:hover {{
    border-color: {acc};
}}
QLabel#card_value {{
    font-size: 30px; font-weight: 700; color: {t.t1};
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}}
QLabel#card_label {{
    font-size: 11px; font-weight: 600; color: {t.t3};
    letter-spacing: 0.05em; text-transform: uppercase;
}}

/* ── Search bar ───────────────────────────────────────────── */
QLineEdit#search_bar {{
    background: {inp_bg}; color: {t.t1};
    border: 1px solid {t.border}; border-radius: {br_input};
    padding: 8px 12px; font-size: 13px;
    selection-background-color: {acc};
}}
QLineEdit#search_bar:focus {{ border-color: {acc}; }}

/* ── Icon / mode square buttons ───────────────────────────── */
QPushButton#icon_btn, QPushButton#mode_btn {{
    background-color: {t.card2};
    color: {t.t1}; border: 1px solid {t.border};
    border-radius: {br_btn};
    font-size: 14pt; font-weight: 600;
    min-width: 36px; max-width: 36px;
    min-height: 36px; max-height: 36px;
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
    background: {t.card}; border: 1px solid {t.border};
    border-radius: 8px; padding: 2px;
}}
QPushButton#lang_btn {{
    background: transparent; color: {t.t3};
    border: none; border-radius: 6px;
    font-size: 9pt; font-weight: 500;
    padding: 0px 4px;
}}
QPushButton#lang_btn:hover {{
    background: {t.border}; color: {t.t1};
}}
QPushButton#lang_btn_active {{
    background: {acc}; color: #FFFFFF;
    border: none; border-radius: 6px;
    font-size: 9pt; font-weight: 600;
    padding: 0px 4px;
}}

/* ── Primary button ───────────────────────────────────────── */
QPushButton#btn_primary {{
    background: {acc};
    color: #FFFFFF; border: none; border-radius: {br_btn};
    font-size: 13px; font-weight: 600;
    padding: 8px 16px; min-height: 36px;
}}
QPushButton#btn_primary:hover   {{ background: {acc_CC}; }}
QPushButton#btn_primary:pressed {{ background: {acc_99}; }}

/* ── Secondary button ─────────────────────────────────────── */
QPushButton#btn_secondary {{
    background: {acc_20}; color: {acc};
    border: 1px solid {acc_40}; border-radius: {br_btn};
    font-size: 12px; font-weight: 500;
    padding: 6px 14px; min-height: 30px;
}}
QPushButton#btn_secondary:hover {{ background: {acc_30}; }}

/* ── QuantitySpin +/− controls ───────────────────────────── */
QPushButton#spin_minus, QPushButton#spin_plus {{
    background: {acc}; color: #FFFFFF;
    border: none;
    border-radius: 22px;
    font-size: 22pt; font-weight: 400;
    padding: 0 0 2px 0;
}}
QPushButton#spin_minus:hover, QPushButton#spin_plus:hover {{
    background: {acc_CC};
}}
QPushButton#spin_minus:pressed, QPushButton#spin_plus:pressed {{
    background: {acc_99};
}}
QLineEdit#spin_edit {{
    background: {inp_bg}; color: {t.t1};
    border: 1px solid {t.border};
    border-radius: {br_input};
    font-size: 14pt; font-weight: 700;
}}

/* ── Ghost button ─────────────────────────────────────────── */
QPushButton#btn_ghost {{
    background: transparent; color: {t.t3};
    border: 1px solid {t.border}; border-radius: {br_btn};
    padding: 6px 14px; min-height: 30px;
}}
QPushButton#btn_ghost:hover {{ background: {t.card2}; color: {t.t1}; }}

/* ── Alert states ─────────────────────────────────────────── */
QPushButton#alert_ok {{
    background: {g_20}; color: {t.green};
    border: 1px solid {g_55}; border-radius: {br_btn};
    font-weight: 600; font-size: 12px; padding: 7px 14px; min-height: 36px;
}}
QPushButton#alert_warn {{
    background: {o_20}; color: {t.orange};
    border: 1px solid {o_55}; border-radius: {br_btn};
    font-weight: 600; font-size: 12px; padding: 7px 14px; min-height: 36px;
}}
QPushButton#alert_critical {{
    background: {r_28}; color: {t.red};
    border: 1px solid {r_55}; border-radius: {br_btn};
    font-weight: 600; font-size: 12px; padding: 7px 14px; min-height: 36px;
}}

/* ── Operation buttons (detail panel) ────────────────────── */
QPushButton[objectName="op_in"] {{
    background: {op_in_bg}; color: {t.green};
    border: 1px solid {op_in_brd};
    border-left: 3px solid {t.green};
    border-radius: {br_btn}; font-weight: 600; font-size: 13px;
    text-align: left; padding-left: 16px; min-height: 44px;
}}
QPushButton[objectName="op_in"]:hover   {{ background: {g_35}; border-left-color: {t.green}; }}
QPushButton[objectName="op_in"]:disabled {{
    background: transparent; color: {t.t4};
    border: 1px solid {t.border}; border-left-color: {t.border};
}}
QPushButton[objectName="op_out"] {{
    background: {op_out_bg}; color: {t.red};
    border: 1px solid {op_out_brd};
    border-left: 3px solid {t.red};
    border-radius: {br_btn}; font-weight: 600; font-size: 13px;
    text-align: left; padding-left: 16px; min-height: 44px;
}}
QPushButton[objectName="op_out"]:hover   {{ background: {r_35}; border-left-color: {t.red}; }}
QPushButton[objectName="op_out"]:disabled {{
    background: transparent; color: {t.t4};
    border: 1px solid {t.border}; border-left-color: {t.border};
}}
QPushButton[objectName="op_adj"] {{
    background: {op_adj_bg}; color: {t.blue};
    border: 1px solid {op_adj_brd};
    border-left: 3px solid {t.blue};
    border-radius: {br_btn}; font-weight: 600; font-size: 13px;
    text-align: left; padding-left: 16px; min-height: 44px;
}}
QPushButton[objectName="op_adj"]:hover   {{ background: {b_35}; border-left-color: {t.blue}; }}
QPushButton[objectName="op_adj"]:disabled {{
    background: transparent; color: {t.t4};
    border: 1px solid {t.border}; border-left-color: {t.border};
}}

/* ── Edit / Delete ────────────────────────────────────────── */
QPushButton#mgmt_edit {{
    background: {b_15}; color: {t.blue};
    border: 1px solid {b_40}; border-radius: {br_btn};
    font-size: 12px; font-weight: 500; min-height: 28px; padding: 4px 12px;
}}
QPushButton#mgmt_edit:hover {{ background: {b_28}; }}
QPushButton#mgmt_edit:disabled {{ background: transparent; color: {t.t4}; border-color: {t.border}; }}

QPushButton#mgmt_del {{
    background: transparent; color: {t.red};
    border: 1px solid {r_40}; border-radius: {br_btn};
    font-size: 12px; font-weight: 500; min-height: 28px; padding: 4px 12px;
}}
QPushButton#mgmt_del:hover {{ background: {t.red}; color: #FFFFFF; }}
QPushButton#mgmt_del:disabled {{ background: transparent; color: {t.t4}; border-color: {t.border}; }}

/* ── Dialog confirm buttons ───────────────────────────────── */
QPushButton#btn_confirm_in {{
    background: {g_28}; color: {t.green};
    border: 1px solid {g_45}; border-radius: {br_btn};
    font-weight: 600; min-height: 44px;
}}
QPushButton#btn_confirm_in:hover    {{ background: {g_40}; }}
QPushButton#btn_confirm_in:disabled {{ background: {t.card2}; color: {t.t4}; border-color: {t.border}; }}
QPushButton#btn_confirm_out {{
    background: {r_28}; color: {t.red};
    border: 1px solid {r_45}; border-radius: {br_btn};
    font-weight: 600; min-height: 44px;
}}
QPushButton#btn_confirm_out:hover    {{ background: {r_40}; }}
QPushButton#btn_confirm_out:disabled {{ background: {t.card2}; color: {t.t4}; border-color: {t.border}; }}
QPushButton#btn_confirm_adj {{
    background: {b_28}; color: {t.blue};
    border: 1px solid {b_45}; border-radius: {br_btn};
    font-weight: 600; min-height: 44px;
}}
QPushButton#btn_confirm_adj:hover {{ background: {b_40}; }}

/* ── Color picker button ──────────────────────────────────── */
QPushButton#color_pick_btn {{
    background: {inp_bg}; color: {t.t1};
    border: 1px solid {t.border2}; border-radius: {br_btn};
    text-align: left; padding-left: 12px;
    font-size: 13px; min-height: 38px;
}}
QPushButton#color_pick_btn:hover {{ background: {t.card2}; }}

/* ── Default fallback button ──────────────────────────────── */
QPushButton {{
    background-color: {t.card2}; color: {t.t1};
    border: 1px solid {t.border}; border-radius: {br_btn};
    padding: 8px 16px; font-size: 13px; font-weight: 500; min-height: 32px;
}}
QPushButton:hover   {{ background-color: {t.border}; border-color: {t.border2}; }}
QPushButton:pressed {{ background-color: {t.border2}; }}
QPushButton:disabled {{ background-color: {t.card2}; color: {t.t4}; border-color: {t.border}; }}

/* ── Checkbox ─────────────────────────────────────────────── */
QCheckBox {{ color: {t.t1}; spacing: 7px; font-size: 13px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 1px solid {t.border2}; border-radius: 4px; background: {t.card};
}}
QCheckBox::indicator:checked {{ background: {acc}; border-color: {acc}; }}

/* ── Tabs ─────────────────────────────────────────────────── */
QTabWidget::pane {{
    background: {t.card};
    border: 1px solid {t.border}; border-radius: {br_tab}; top: -1px;
}}
QTabWidget#main_tabs::pane {{
    background: {t.card};
    border: 1px solid {t.border}; border-radius: {br_tab}; top: -1px;
}}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    background: transparent; color: {t.t3};
    padding: 12px 20px; font-weight: 500; font-size: 13px;
    border: none; border-bottom: 2px solid transparent; margin-right: 4px;
}}
QTabBar::tab:selected {{ color: {acc}; border-bottom-color: {acc}; }}
QTabBar::tab:hover    {{ color: {t.t1}; background: {t.card2}; }}

/* ── Tables ───────────────────────────────────────────────── */
QTableWidget {{
    background: {t.card};
    alternate-background-color: {alt};
    color: {t.t1}; gridline-color: {t.border};
    border: 1px solid {t.border}; border-radius: {br_table};
    selection-background-color: {acc}; selection-color: #FFFFFF;
    outline: none;
}}
QTableWidget::item {{
    padding: 12px 16px; border: none;
    border-bottom: 1px solid {t.border};
}}
QTableWidget::item:hover {{ background: {t.card2}; }}
QTableWidget::item:selected {{ background: {acc}; color: #FFFFFF; }}

/* ── Matrix table — cell backgrounds come from item BackgroundRole ── */
QTableWidget#matrix_table {{
    gridline-color: {matrix_grid};
    color: {t.t1};
    border: none;
    border-radius: 0;
    outline: none;
    selection-background-color: {acc};
    selection-color: #FFFFFF;
}}
QTableWidget#matrix_table::item {{
    padding: 4px 8px;
}}
QTableWidget#matrix_table::item:selected {{
    color: #FFFFFF;
}}
QHeaderView {{ background: transparent; }}
QHeaderView::section {{
    background: {t.grad_top}; color: {t.t2};
    font-weight: 600; font-size: 11px; letter-spacing: 0.05em;
    text-transform: uppercase;
    border: none; border-bottom: 1px solid {t.border}; padding: 12px 16px;
}}
QHeaderView::section:hover {{ background: {t.card2}; color: {t.t1}; }}

/* ── Inputs (non-search) ──────────────────────────────────── */
QLineEdit, QSpinBox {{
    background: {inp_bg}; color: {t.t1};
    border: 1px solid {t.border}; border-radius: {br_input};
    padding: 8px 12px; font-size: 13px; min-height: 36px;
    selection-background-color: {acc};
}}
QLineEdit:focus, QSpinBox:focus {{ border-color: {acc}; }}

/* ── SpinBox arrows ──────────────────────────────────────── */
QSpinBox {{ padding-right: 28px; }}
QSpinBox::up-button {{
    subcontrol-origin: border; subcontrol-position: top right;
    width: 24px; height: 18px;
    border: none; border-left: 1px solid {t.border}; border-top-right-radius: 5px;
    background: {t.card2};
}}
QSpinBox::up-button:hover   {{ background: {t.border}; }}
QSpinBox::up-button:pressed {{ background: {t.border2}; }}
QSpinBox::up-arrow {{
    width: 8px; height: 8px;
    border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-bottom: 5px solid {t.t2};
}}
QSpinBox::down-button {{
    subcontrol-origin: border; subcontrol-position: bottom right;
    width: 24px; height: 18px;
    border: none; border-left: 1px solid {t.border}; border-bottom-right-radius: 5px;
    background: {t.card2};
}}
QSpinBox::down-button:hover   {{ background: {t.border}; }}
QSpinBox::down-button:pressed {{ background: {t.border2}; }}
QSpinBox::down-arrow {{
    width: 8px; height: 8px;
    border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-top: 5px solid {t.t2};
}}

/* ── List widget ─────────────────────────────────────────── */
QListWidget {{
    background: {t.card};
    color: {t.t1};
    border: 1px solid {t.border};
    border-radius: {br_table};
    outline: none;
    selection-background-color: {acc};
    selection-color: #FFFFFF;
}}
QListWidget::item {{
    padding: 8px 12px;
    border-bottom: 1px solid {t.border};
}}
QListWidget::item:hover {{ background: {t.card2}; }}
QListWidget::item:selected {{ background: {acc}; color: #FFFFFF; }}

/* ── ComboBox ────────────────────────────────────────────── */
QComboBox {{
    background: {inp_bg}; color: {t.t1};
    border: 1px solid {t.border}; border-radius: {br_input};
    padding: 8px 12px; font-size: 13px;
}}
QComboBox:focus {{ border-color: {acc}; }}
QComboBox::drop-down {{
    border: none; width: 30px;
}}
QComboBox::down-arrow {{
    border-left: 5px solid transparent; border-right: 5px solid transparent;
    border-top: 6px solid {t.t3}; margin-right: 10px;
}}
QComboBox QAbstractItemView {{
    background: {t.card}; border: 1px solid {t.border};
    border-radius: {br_input}; padding: 4px;
    selection-background-color: {acc}; selection-color: #FFFFFF;
}}

/* ── GroupBox ─────────────────────────────────────────────── */
QGroupBox {{
    font-weight: 600; font-size: 12px; color: {t.t3};
    border: 1px solid {t.border}; border-radius: {br_table};
    margin-top: 16px; padding-top: 24px;
    background: {t.card};
}}
QGroupBox::title {{
    subcontrol-origin: margin; left: 16px; padding: 0 6px;
    color: {t.t3}; text-transform: uppercase; letter-spacing: 0.05em;
}}

/* ── Dialog inner elements ────────────────────────────────── */
QLabel#dlg_header {{ font-size: 18px; font-weight: 600; color: {t.t1}; padding-bottom: 4px; }}
QFrame#op_card {{
    background: {t.card};
    border: 1px solid {t.border}; border-radius: {br_table};
}}
QFrame#preview_frame {{
    background: {t.card};
    border: 1px solid {t.border}; border-radius: {br_table};
}}
QLabel#card_name    {{ font-size: 14px; color: {t.t1}; font-weight: 500; }}
QLabel#card_meta    {{ font-size: 13px; color: {t.t1}; }}
QLabel#card_meta_dim {{ font-size: 12px; color: {t.t3}; }}
QLabel#card_barcode {{ font-size: 12px; color: {t.t4}; font-family: 'JetBrains Mono', Consolas, monospace; }}
QLabel#op_preview   {{ padding: 8px; }}
QLabel#dim_label    {{ font-size: 11px; color: {t.t3}; }}
QLabel#preview_name_lbl {{ font-size: 14px; font-weight: 600; color: {t.t1}; }}
QLabel#picker_title {{ font-size: 16px; font-weight: 600; color: {t.t1}; }}
QLabel#section_caption {{ font-size: 12px; color: {t.t3}; }}
QDialogButtonBox QPushButton {{ min-width: 100px; }}

/* ── Detail panel ─────────────────────────────────────────── */
QScrollArea#detail_scroll_area {{ border: none; background: transparent; }}
QScrollArea#detail_scroll_area > QWidget > QWidget {{ background: transparent; }}
QFrame#detail_card {{
    background: {t.card};
    border: 1px solid {t.border}; border-radius: {br_card};
    padding: 16px;
}}
QFrame#detail_card:hover {{
    border-color: {acc};
}}
QLabel#detail_product_name {{ font-size: 14px; font-weight: 600; color: {t.t1}; }}
QLabel#detail_color_name   {{ font-size: 13px; color: {t.t2}; }}
QLabel#detail_barcode      {{ font-size: 12px; color: {t.t3}; font-family: 'JetBrains Mono', Consolas, monospace; }}
QLabel#detail_updated      {{ font-size: 11px; color: {t.t4}; }}
QLabel#detail_section_hdr  {{
    font-size: 11px; font-weight: 600; color: {t.t3};
    letter-spacing: 0.05em; text-transform: uppercase;
}}
QLabel#big_stock           {{
    font-size: 48pt; font-weight: 700; padding: 8px 0;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}}
QLabel#detail_threshold    {{ font-size: 12px; color: {t.t3}; }}

/* ── Mini txn list ────────────────────────────────────────── */
QScrollArea#txn_scroll_area {{
    border: 1px solid {t.border}; border-radius: {br_table}; background: {t.card};
}}
QScrollArea#txn_scroll_area > QWidget > QWidget {{ background: {t.card}; }}
QFrame#txn_row     {{ background: {t.card};  border-bottom: 1px solid {t.border}; }}
QFrame#txn_row_alt {{ background: {alt};     border-bottom: 1px solid {t.border}; }}
QLabel#txn_after {{ font-size: 12px; color: {t.t3}; }}
QLabel#txn_time  {{ font-size: 11px; color: {t.t4}; font-family: 'JetBrains Mono', Consolas, monospace; }}
QLabel#txn_empty {{ font-size: 12px; color: {t.t4}; }}

/* ── Alert table ──────────────────────────────────────────── */
QTableWidget#alert_table {{
    background: {t.card}; alternate-background-color: {t.card2};
    color: {t.t1}; border: 1px solid {t.border}; border-radius: {br_table};
    selection-background-color: {acc_30};
}}

/* ── Sidebar ──────────────────────────────────────────────── */
QFrame#sidebar {{
    background: {t.card};
    border-right: 1px solid {t.border};
    border-radius: 0;
}}
QScrollArea#sidebar_scroll {{
    background: {t.card};
    border: none;
}}
QScrollArea#sidebar_scroll > QWidget > QWidget {{
    background: {t.card};
}}
QFrame#sidebar_divider {{
    background: {t.border};
    border: none;
    margin: 4px 16px;
    max-height: 1px;
}}
QLabel#sidebar_section_hdr {{
    font-size: 10px;
    font-weight: 600;
    color: {t.t3};
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 8px 8px 4px 8px;
}}
QPushButton#sidebar_section_toggle {{
    background: transparent;
    color: {t.t3};
    border: none;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    text-align: left;
    padding: 6px 8px;
    margin: 0px 8px;
    min-height: 28px;
}}
QPushButton#sidebar_section_toggle:hover {{
    background: {t.card2};
    color: {t.t2};
}}
QPushButton#sidebar_btn {{
    background: transparent;
    color: {t.t2};
    border: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    text-align: left;
    padding: 0px 12px;
    margin: 1px 8px;
    min-height: 42px;
}}
QPushButton#sidebar_btn:hover {{
    background: {t.card2};
    color: {t.t1};
}}
QPushButton#sidebar_btn_active {{
    background: {acc};
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    text-align: left;
    padding: 0px 12px;
    margin: 1px 8px;
    min-height: 42px;
}}
QPushButton#sidebar_btn_active:hover {{
    background: {acc_CC};
    color: #FFFFFF;
}}
QFrame#sidebar_user_info {{
    background: {t.card2};
    border-radius: 8px;
    margin: 4px 8px;
}}
QLabel#sidebar_shop_name {{
    font-size: 12px; font-weight: 600; color: {t.t1};
}}
QLabel#sidebar_shop_meta {{
    font-size: 11px; color: {t.t3};
}}

/* ── Theme toggle switch ─────────────────────────────────── */
QFrame#theme_toggle {{
    background: {t.card2};
    border: 1px solid {t.border};
    border-radius: 14px;
    min-height: 28px;
    max-height: 28px;
}}

/* ── Quick scan feed ─────────────────────────────────────── */
QFrame#scan_feed_item {{
    background: {t.card};
    border: 1px solid {t.border};
    border-radius: {br_table};
    padding: 8px 12px;
}}
QFrame#scan_feed_success {{
    background: {g_20};
    border: 1px solid {g_40};
    border-radius: {br_table};
    padding: 8px 12px;
}}
QFrame#scan_feed_error {{
    background: {r_15};
    border: 1px solid {r_40};
    border-radius: {br_table};
    padding: 8px 12px;
}}
QFrame#scan_feed_warn {{
    background: {o_20};
    border: 1px solid {t.border};
    border-radius: {br_table};
    padding: 8px 12px;
}}

/* ── Quick Scan mode bars ────────────────────────────────── */
QFrame#scan_mode_idle {{
    background: {t.card2};
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 12px 16px;
}}
QFrame#scan_mode_takeout {{
    background: {r_15};
    border: 1px solid {r_40};
    border-radius: 8px;
    padding: 12px 16px;
}}
QFrame#scan_mode_insert {{
    background: {g_20};
    border: 1px solid {g_40};
    border-radius: 8px;
    padding: 12px 16px;
}}

/* ── Stock ops card ──────────────────────────────────────── */
QFrame#stockops_card {{
    background: {t.card};
    border: 1px solid {t.border};
    border-radius: {br_card};
}}
QFrame#stockops_selected {{
    background: {acc_20};
    border: 1px solid {acc_40};
    border-radius: {br_table};
    padding: 12px;
}}

/* ── Progress bar ─────────────────────────────────────────── */
QProgressBar {{
    background: {t.card2}; border: none; border-radius: 4px; height: 8px;
    text-align: center; color: transparent;
}}
QProgressBar::chunk {{ background: {acc}; border-radius: 4px; }}

/* ── Menu ─────────────────────────────────────────────────── */
QMenuBar {{
    background: {t.grad_top}; color: {t.t1};
    border-bottom: 1px solid {t.border}; padding: 4px 8px;
}}
QMenuBar::item {{ background: transparent; padding: 6px 12px; border-radius: 4px; }}
QMenuBar::item:selected {{ background: {t.card2}; }}
QMenu {{
    background: {t.card}; border: 1px solid {t.border};
    border-radius: 8px; padding: 4px;
}}
QMenu::item {{ padding: 8px 24px 8px 12px; border-radius: 4px; }}
QMenu::item:selected {{ background: {acc}; color: #FFFFFF; }}
QMenu::separator {{ height: 1px; background: {t.border}; margin: 4px 8px; }}

/* ── Splitter ─────────────────────────────────────────────── */
QSplitter::handle {{ background: {t.border}; width: 1px; height: 1px; }}

/* ── Footer bar ───────────────────────────────────────────── */
QFrame#footer_bar {{
    background: {t.card};
    border-top: 1px solid {t.border};
    border-radius: 0;
}}
QLabel#footer_status {{
    font-size: 11px; color: {t.t3}; font-weight: 500;
}}
QLabel#footer_version {{
    font-size: 11px; color: {t.t4}; font-weight: 400;
}}
QLabel#footer_sync {{
    font-size: 11px; color: {t.green}; font-weight: 500;
}}
QProgressBar#footer_progress {{
    background: {t.card2}; border: none; border-radius: 2px; max-height: 4px;
}}
QProgressBar#footer_progress::chunk {{
    background: {acc}; border-radius: 2px;
}}
/* Legacy status bar fallback */
QStatusBar {{ background: transparent; color: {t.t4}; font-size: 11px; border: none; }}
QStatusBar::item {{ border: none; }}

/* ── Tooltips ─────────────────────────────────────────────── */
QToolTip {{
    background: {t.card2}; color: {t.t1};
    border: 1px solid {t.border}; border-radius: 6px;
    padding: 8px 12px; font-size: 12px;
}}

/* ── Scrollbars ───────────────────────────────────────────── */
QScrollBar:vertical   {{ width: 8px; background: transparent; margin: 0; }}
QScrollBar::handle:vertical   {{ background: {scr}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {t.t3}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QScrollBar:horizontal {{ height: 8px; background: transparent; }}
QScrollBar::handle:horizontal {{ background: {scr}; border-radius: 4px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: {t.t3}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
"""


class ThemeManager:
    def __init__(self):
        self._dark = True
        self._key = "pro_dark"  # Default to Pro Dark
        self._t = PRO_DARK
        self._targets: list = []

    @property
    def is_dark(self) -> bool: return self._dark

    @property
    def tokens(self) -> Tokens: return self._t

    @property
    def theme_key(self) -> str: return self._key

    def set_theme(self, key: str) -> None:
        """Switch to a named theme preset."""
        if key in THEMES:
            self._key = key
            self._t = THEMES[key]
            self._dark = self._t.is_dark
            ss = self.stylesheet()
            for w in list(self._targets):
                try:   w.setStyleSheet(ss); w.update()
                except RuntimeError: self._targets.remove(w)

    def toggle(self) -> None:
        """Toggle between dark and light variant of current style."""
        if self._key == "pro_dark":
            self.set_theme("pro_light")
        elif self._key == "pro_light":
            self.set_theme("pro_dark")
        elif self._key == "dark":
            self.set_theme("light")
        elif self._key == "light":
            self.set_theme("dark")
        else:
            self._dark = not self._dark
            self._t = DARK if self._dark else LIGHT
            ss = self.stylesheet()
            for w in list(self._targets):
                try:   w.setStyleSheet(ss); w.update()
                except RuntimeError: self._targets.remove(w)

    def cycle(self) -> None:
        """Cycle through all 4 themes: pro_dark → pro_light → dark → light → ..."""
        order = ["pro_dark", "pro_light", "dark", "light"]
        idx = order.index(self._key) if self._key in order else 0
        next_key = order[(idx + 1) % len(order)]
        self.set_theme(next_key)

    def stylesheet(self) -> str: return _ss(self._t)

    def apply(self, widget):
        widget.setStyleSheet(self.stylesheet())
        self.register(widget)

    def register(self, widget):
        if widget not in self._targets:
            self._targets.append(widget)


THEME = ThemeManager()
