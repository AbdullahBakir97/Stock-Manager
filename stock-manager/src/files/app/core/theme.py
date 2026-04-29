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
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal


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
        from PyQt6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

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

    # Border radius — tighter for pro themes, slightly rounded for originals
    br_card  = "6px"  if is_pro else "10px"
    br_btn   = "4px"  if is_pro else "8px"
    br_input = "4px"  if is_pro else "8px"
    br_table = "6px"  if is_pro else "8px"
    br_tab   = "6px"  if is_pro else "8px"

    # Search bar — pill-shaped; true glass (transparent + rim) for pro, subtle tint for original
    br_search = "17px"  # pill = half of 34px height
    if is_pro:
        # Transparent glass: no fill, just a crisp white/black rim
        search_bg          = "transparent"
        search_bg_hover    = "rgba(255,255,255,8)"  if t.is_dark else "rgba(0,0,0,6)"
        search_border      = "rgba(255,255,255,45)" if t.is_dark else "rgba(0,0,0,35)"
        search_border_focus = acc
    else:
        search_bg          = _rgba(t.card2, 'AA')
        search_bg_hover    = _rgba(t.card2, 'CC')
        search_border      = t.border
        search_border_focus = acc

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
    border-bottom: 1px solid {t.border2};
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

/* ── Dashboard actions toolbar ────────────────────────────── */
QFrame#dashboard_actions {{
    background: {t.card};
    border: 1px solid {t.border};
    border-radius: {br_card};
    padding: 6px 8px;
    min-height: 36px;
    max-height: 44px;
}}
QPushButton#dash_btn_primary {{
    background: {acc};
    color: #FFFFFF;
    border: none;
    border-radius: {br_btn};
    font-size: 12px;
    font-weight: 600;
    padding: 6px 14px;
    min-height: 30px;
}}
QPushButton#dash_btn_primary:hover {{ background: {acc_CC}; }}
QPushButton#dash_btn_primary:pressed {{ background: {acc_99}; }}

QPushButton#dash_btn {{
    background: transparent;
    color: {t.t2};
    border: 1px solid {t.border};
    border-radius: {br_btn};
    font-size: 12px;
    font-weight: 500;
    padding: 5px 12px;
    min-height: 28px;
}}
QPushButton#dash_btn:hover {{
    background: {t.card2};
    border-color: {t.border2};
    color: {t.t1};
}}
QPushButton#dash_btn:pressed {{
    background: {t.border};
}}

/* ── Summary cards ────────────────────────────────────────── */
QFrame#summary_card {{
    background: {t.card};
    border: 1px solid {t.border};
    border-left: 3px solid {acc};
    border-radius: {br_card}; min-height: 80px;
    padding: 14px 18px;
}}
QFrame#summary_card:hover {{
    border-color: {t.border2};
    border-left-color: {acc};
}}
QLabel#card_value {{
    font-size: 30px; font-weight: 700; color: {t.t1};
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}}
QLabel#card_label {{
    font-size: 11px; font-weight: 600; color: {t.t3};
    letter-spacing: 0.05em; text-transform: uppercase;
}}

/* ── Search bar — pill-shaped transparent glass ─────────────── */
QLineEdit#search_bar {{
    background: {search_bg};
    color: {t.t1};
    border: 1px solid {search_border};
    border-radius: {br_search};
    padding: 8px 18px;
    font-size: 13px;
    selection-background-color: {acc};
}}
QLineEdit#search_bar:hover {{
    background: {search_bg_hover};
    border-color: {search_border};
}}
QLineEdit#search_bar:focus {{
    background: {search_bg_hover};
    border: 1px solid {search_border_focus};
}}

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

/* ── Language switcher dropdown ───────────────────────────── */
QFrame#lang_trigger {{
    background: {t.card}; border: 1px solid {t.border};
    border-radius: 8px;
}}
QFrame#lang_dropdown {{
    background: {t.card}; border: 1px solid {t.border};
    border-radius: 10px;
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

/* ── Close button (×) ────────────────────────────────────── */
QPushButton#btn_close_x {{
    background: transparent; color: {t.t3};
    border: none; border-radius: 6px;
    font-size: 18px; font-weight: 400;
    min-width: 32px; max-width: 32px;
    min-height: 32px; max-height: 32px;
    padding: 0;
}}
QPushButton#btn_close_x:hover {{
    background: {t.card2}; color: {t.t1};
}}

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

/* ── Compact button variants (sidebar panels, toolbars) ──── */
QPushButton#btn_primary_sm {{
    background: {acc};
    color: #FFFFFF; border: none; border-radius: {br_btn};
    font-size: 11px; font-weight: 600;
    padding: 2px 8px; min-height: 22px; max-height: 30px;
}}
QPushButton#btn_primary_sm:hover   {{ background: {acc_CC}; }}
QPushButton#btn_primary_sm:pressed {{ background: {acc_99}; }}
QPushButton#btn_primary_sm:disabled {{ background: {t.card2}; color: {t.t4}; }}

QPushButton#btn_secondary_sm {{
    background: {acc_20}; color: {acc};
    border: 1px solid {acc_40}; border-radius: {br_btn};
    font-size: 10px; font-weight: 500;
    padding: 2px 8px; min-height: 20px; max-height: 28px;
}}
QPushButton#btn_secondary_sm:hover {{ background: {acc_30}; }}
QPushButton#btn_secondary_sm:disabled {{ background: {t.card2}; color: {t.t4}; border-color: {t.border}; }}

QPushButton#alert_ok_sm {{
    background: {g_20}; color: {t.green};
    border: 1px solid {g_55}; border-radius: {br_btn};
    font-weight: 600; font-size: 10px;
    padding: 2px 8px; min-height: 20px; max-height: 28px;
}}
QPushButton#alert_ok_sm:hover {{ background: {g_35}; }}
QPushButton#alert_ok_sm:disabled {{ background: {t.card2}; color: {t.t4}; border-color: {t.border}; }}

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
    font-size: 12px; font-weight: 500; min-height: 24px; padding: 3px 12px;
}}
QPushButton#mgmt_edit:hover {{ background: {b_28}; }}
QPushButton#mgmt_edit:disabled {{ background: transparent; color: {t.t4}; border-color: {t.border}; }}

QPushButton#mgmt_del {{
    background: transparent; color: {t.red};
    border: 1px solid {r_40}; border-radius: {br_btn};
    font-size: 12px; font-weight: 500; min-height: 24px; padding: 3px 12px;
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
    border: 1px solid {t.border};
    border-radius: {br_tab};
    background: transparent;
    top: -1px;
}}
QTabWidget#main_tabs::pane {{
    border: 1px solid {t.border};
    border-radius: {br_tab};
    background: transparent;
    top: -1px;
}}
QTabBar {{
    background: transparent;
}}
QTabBar::tab {{
    background: transparent;
    color: {t.t2};
    padding: 8px 16px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 12px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    color: {acc};
    border-bottom: 2px solid {acc};
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{
    color: {t.t1};
    background: {_rgba(acc, '10')};
}}

/* ── Tables ───────────────────────────────────────────────── */
QTableWidget {{
    background: {t.card};
    alternate-background-color: {alt};
    color: {t.t1}; gridline-color: {t.border};
    border: 1px solid {t.border}; border-radius: {br_table};
    selection-background-color: {acc_30}; selection-color: {t.t1};
    outline: none;
}}
QTableWidget::item {{
    padding: 4px 12px; border: none;
    border-bottom: 1px solid {t.border};
}}
QTableWidget::item:hover {{ background: {_rgba(acc, '10')}; }}
QTableWidget::item:selected {{ background: {acc_30}; color: {t.t1}; }}

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
    background: {t.card2}; color: {t.t3};
    font-weight: 600; font-size: 11px; letter-spacing: 0.05em;
    text-transform: uppercase;
    border: none; border-bottom: 2px solid {t.border}; padding: 10px 16px;
}}
QHeaderView::section:hover {{ color: {t.t1}; }}

/* ── Inputs (non-search) ──────────────────────────────────── */
QLineEdit, QSpinBox {{
    background: {inp_bg}; color: {t.t1};
    border: 1px solid {t.border}; border-radius: {br_input};
    padding: 8px 12px; font-size: 13px; min-height: 36px;
    selection-background-color: {acc};
}}
QLineEdit:focus, QSpinBox:focus {{ border-color: {acc}; }}

/* ── SpinBox — no custom arrows, use Qt native ───────────── */

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
    background: transparent;
    color: {t.t2};
    border: none;
    border-bottom: 1px solid {t.border};
    border-radius: 0;
    padding: 3px 8px;
    font-size: 12px;
    font-weight: 500;
}}
QComboBox:hover {{
    color: {t.t1};
    border-bottom: 1px solid {acc};
}}
QComboBox:focus {{
    color: {t.t1};
    border-bottom: 2px solid {acc};
    padding-bottom: 2px;
}}
QComboBox::drop-down {{
    border: none;
    width: 18px;
}}
QComboBox::down-arrow {{
    image: none;
}}
QComboBox QAbstractItemView {{
    background: {t.card};
    color: {t.t1};
    border: 1px solid {t.border};
    border-radius: 6px;
    outline: none;
    padding: 4px;
    font-size: 12px;
    selection-background-color: {_rgba(acc, '30')};
    selection-color: {t.t1};
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
/* ── Inventory page section headers ──────────────────────── */
QLabel#inv_section_lbl {{
    font-size: 10px; font-weight: 700; color: {t.t4};
    letter-spacing: 0.8px;
}}
QFrame#inv_divider {{
    background: {t.border};
    max-height: 1px;
    border: none;
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
    background: {_rgba(acc, '12')};
    color: {t.t1};
}}
QPushButton#sidebar_btn_active {{
    background: {acc_20};
    color: {acc};
    border: none;
    border-left: 3px solid {acc};
    border-radius: 0px 6px 6px 0px;
    font-size: 13px;
    font-weight: 600;
    text-align: left;
    padding: 0px 12px 0px 9px;
    margin: 1px 8px;
    min-height: 42px;
}}
QPushButton#sidebar_btn_active:hover {{
    background: {acc_30};
    color: {acc};
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

/* ── Quick Scan totals card ───────────────────────────────── */
QFrame#qscan_totals_card {{
    background: {t.card2};
    border: 1px solid {t.border};
    border-left: 3px solid {acc};
    border-radius: 6px;
    padding: 0;
}}
QFrame#qscan_totals_card QLabel {{
    color: {t.t1};
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

/* ── Filter chips ────────────────────────────────────────── */
QPushButton#filter_chip {{
    background: {t.card2};
    color: {t.t2};
    border: 1px solid {t.border};
    border-radius: 16px;
    font-size: 12px;
    font-weight: 500;
    padding: 4px 14px;
    min-height: 30px;
}}
QPushButton#filter_chip:hover {{
    background: {_rgba(acc, '15')};
    color: {t.t1};
    border-color: {_rgba(acc, '40')};
}}
QPushButton#filter_chip:checked {{
    background: {acc_20};
    color: {acc};
    border-color: {acc};
    font-weight: 600;
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
/* ── Footer zoom group ──────────────────────────────────── */
QWidget#footer_zoom_group {{
    background: {t.card2};
    border: 1px solid {t.border};
    border-radius: 4px;
}}
QToolButton#footer_zoom_btn {{
    background: transparent; color: {t.t2};
    border: none; border-radius: 3px;
    font-size: 13px; font-weight: 600; padding: 0;
}}
QToolButton#footer_zoom_btn:hover {{
    background: {t.border}; color: {t.t1};
}}
QToolButton#footer_zoom_btn:pressed {{
    background: {t.border2}; color: {acc};
}}
QToolButton#footer_zoom_preset {{
    background: transparent; color: {t.t2};
    border: none; border-radius: 3px;
    font-size: 10px; font-weight: 600; padding: 0 6px;
    font-family: 'JetBrains Mono', monospace;
}}
QToolButton#footer_zoom_preset:hover {{
    background: {t.border}; color: {t.t1};
}}
QToolButton#footer_zoom_preset::menu-indicator {{
    image: none;
    subcontrol-position: right center;
    width: 0;
}}
QFrame#footer_zoom_divider {{
    color: {t.border2};
    background: {t.border2};
    max-width: 1px;
}}
QMenu#footer_zoom_menu {{
    background: {t.card};
    border: 1px solid {t.border};
    border-radius: 4px;
    padding: 4px 0;
}}
QMenu#footer_zoom_menu::item {{
    color: {t.t1}; padding: 6px 18px;
    font-size: 11px; font-family: 'JetBrains Mono', monospace;
}}
QMenu#footer_zoom_menu::item:selected {{
    background: {acc}; color: white;
}}
QMenu#footer_zoom_menu::separator {{
    height: 1px; background: {t.border}; margin: 4px 8px;
}}
QSlider#footer_zoom_slider {{
    background: transparent;
    min-height: 18px; max-height: 18px;
}}
QSlider#footer_zoom_slider::groove:horizontal {{
    background: {t.border};
    height: 3px; border-radius: 1px;
    margin: 0;
}}
QSlider#footer_zoom_slider::sub-page:horizontal {{
    background: {acc};
    height: 3px; border-radius: 1px;
}}
QSlider#footer_zoom_slider::handle:horizontal {{
    background: {t.t1};
    border: 2px solid {acc};
    width: 8px; height: 8px;
    margin: -4px 0;
    border-radius: 6px;
}}
QSlider#footer_zoom_slider::handle:horizontal:hover {{
    background: {acc};
    border-color: {t.t1};
    width: 8px; height: 8px;
}}
QSlider#footer_zoom_slider::tick-mark:horizontal {{
    background: {t.t4};
    width: 1px; height: 3px;
}}
QLabel#footer_filter_indicator {{
    font-size: 11px; color: {acc}; font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
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
    background: {t.card};
    color: {t.t1};
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ── Scrollbars ───────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {_rgba(t.t3, '60')};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {_rgba(t.t3, '99')};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {_rgba(t.t3, '60')};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {_rgba(t.t3, '99')};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}

/* ── Summary strip (transactions page) ───────────────────── */
QFrame#summary_strip {{
    background: {t.card};
    border: 1px solid {t.border};
    border-radius: {br_card};
}}
QLabel#summary_stat {{
    font-size: 12px; font-weight: 600; color: {t.t2};
}}
QLabel#summary_stat_green {{
    font-size: 12px; font-weight: 700; color: {t.green};
}}
QLabel#summary_stat_red {{
    font-size: 12px; font-weight: 700; color: {t.red};
}}
QLabel#summary_stat_dim {{
    font-size: 11px; font-weight: 400; color: {t.t3};
}}

/* ── Empty states ────────────────────────────────────────── */
QLabel#empty_title {{
    font-size: 16px; font-weight: 700; color: {t.t2};
    background: transparent;
}}
QLabel#empty_sub {{
    font-size: 12px; color: {t.t3};
    background: transparent;
}}

/* ── Report cards ────────────────────────────────────────── */
QFrame#report_card {{
    background: {t.card};
    border: 1px solid {t.border};
    border-radius: {br_card};
}}
QFrame#report_card:hover {{
    background: {t.card2};
    border: 1px solid {acc};
}}

/* ── Section caption ─────────────────────────────────────── */
QLabel#section_caption {{
    font-size: 15px; font-weight: 700; color: {t.t1};
    background: transparent;
    padding: 0;
}}

/* ── Context menus (enhanced) ────────────────────────────── */
QMenu {{
    background: {t.card}; border: 1px solid {t.border};
    border-radius: 8px; padding: 6px;
}}
QMenu::item {{
    padding: 8px 28px 8px 14px; border-radius: 6px;
    font-size: 12px;
}}
QMenu::item:selected {{ background: {acc_30}; color: {t.t1}; }}
QMenu::item:disabled {{ color: {t.t4}; }}
QMenu::separator {{ height: 1px; background: {t.border}; margin: 4px 10px; }}
QMenu::icon {{ padding-left: 8px; }}

/* ── Enhanced footer status icons ────────────────────────── */
QLabel#footer_status_ok {{
    font-size: 11px; color: {t.green}; font-weight: 600;
}}
QLabel#footer_status_warn {{
    font-size: 11px; color: {t.orange}; font-weight: 600;
}}
QLabel#footer_status_err {{
    font-size: 11px; color: {t.red}; font-weight: 600;
}}
QLabel#footer_filter_indicator {{
    font-size: 10px; color: {acc}; font-weight: 500;
    background: {acc_20}; border-radius: 8px; padding: 2px 8px;
}}
QLabel#footer_timestamp {{
    font-size: 10px; color: {t.t4}; font-weight: 400;
}}

/* ── Detail panel enhancements ───────────────────────────── */
QLabel#detail_category {{
    font-size: 10px; color: {acc}; font-weight: 600;
    background: {acc_20}; border-radius: 4px; padding: 2px 8px;
}}
QLabel#detail_notes {{
    font-size: 11px; color: {t.t3}; font-style: italic;
    background: transparent;
}}
QFrame#detail_barcode_frame {{
    background: #FFFFFF; border: 1px solid {t.border};
    border-radius: 4px; padding: 4px;
}}
QFrame#detail_sparkline {{
    background: {t.card2}; border: 1px solid {t.border};
    border-radius: 6px;
}}

/* ── Keyboard shortcut hints ─────────────────────────────── */
QLabel#shortcut_hint {{
    font-size: 9px; color: {t.t4}; font-weight: 500;
    background: {_rgba(t.t4, '15')}; border-radius: 3px;
    padding: 1px 5px; font-family: 'JetBrains Mono', monospace;
}}

/* ── Analytics page ─────────────────────────────────────── */
QLabel#analytics_page_title {{
    font-size: 18px; font-weight: 700; color: {t.t1};
    padding-bottom: 4px;
}}
QFrame#analytics_kpi {{
    background: {t.card}; border: 1px solid {t.border};
    border-radius: {br_card}; border-left: 3px solid {acc};
}}
QLabel#analytics_kpi_label {{
    font-size: 10px; font-weight: 600; color: {t.t3};
    letter-spacing: 0.05em;
}}
QLabel#analytics_kpi_value {{
    font-size: 22px; font-weight: 700; color: {t.t1};
}}
QLabel#analytics_kpi_sub {{
    font-size: 10px; color: {t.t4};
}}
QFrame#analytics_chart_card {{
    background: {t.card}; border: 1px solid {t.border};
    border-radius: {br_card}; padding: 4px;
}}
QLabel#analytics_chart_title {{
    font-size: 12px; font-weight: 600; color: {t.t2};
    padding-bottom: 4px;
}}
QScrollArea#analytics_scroll {{
    border: none; background: transparent;
}}

/* ── New Analytics (2.3.9) ─────────────────────────────── */
QFrame#kpi_tile {{
    background: {t.card}; border: 1px solid {t.border};
    border-radius: {br_card};
}}
QFrame#kpi_tile:hover {{
    border-color: {acc};
    background: {t.card2};
}}
QLabel#analytics_section_hdr {{
    font-size: 11px; font-weight: 800; color: {t.t3};
    letter-spacing: 0.10em;
    padding: 2px 0;
}}
QFrame#analytics_section_card {{
    background: {t.card}; border: 1px solid {t.border};
    border-radius: {br_card};
}}
QWidget#analytics_empty_state {{
    background: {t.card2};
    border: 1px dashed {t.border2};
    border-radius: {br_card};
}}
QTableWidget#analytics_pivot {{
    background: {t.card};
    border: 1px solid {t.border};
    border-radius: {br_card};
    gridline-color: {t.border};
}}
QTableWidget#analytics_pivot::item {{
    padding: 4px 6px;
}}
QToolButton#analytics_preset_btn {{
    background: {t.card2}; color: {t.t2};
    border: 1px solid {t.border};
    border-radius: 4px;
    font-size: 11px; font-weight: 600;
    padding: 4px 10px;
}}
QToolButton#analytics_preset_btn:hover {{
    background: {t.border}; color: {t.t1};
}}
QToolButton#analytics_preset_btn:checked {{
    background: {acc}; color: white; border-color: {acc};
}}

/* ── Sales / POS ───────────────────────────────────────── */
QLabel#sales_page_title {{
    font-size: 18px; font-weight: 700; color: {t.t1};
    padding-bottom: 4px;
}}
QFrame#sales_kpi {{
    background: {t.card}; border: 1px solid {t.border};
    border-radius: {br_card}; border-left: 3px solid {acc};
}}
QLabel#sales_kpi_label {{
    font-size: 10px; font-weight: 600; color: {t.t3};
    letter-spacing: 0.05em;
}}
QLabel#sales_kpi_value {{
    font-size: 22px; font-weight: 700; color: {t.t1};
}}
QLabel#sales_kpi_sub {{
    font-size: 10px; color: {t.t4};
}}
QPushButton#sales_new_btn {{
    background: {acc}; color: #FFFFFF;
    border: none; border-radius: {br_btn};
    font-size: 13px; font-weight: 600;
    padding: 8px 20px; min-height: 36px;
}}
QPushButton#sales_new_btn:hover {{ background: {acc_CC}; }}
QPushButton#sales_new_btn:pressed {{ background: {acc_99}; }}

/* POS Dialog */
QDialog#pos_dialog {{
    background: {t.grad_top};
}}
QFrame#pos_panel {{
    background: {t.card}; border: 1px solid {t.border};
    border-radius: {br_card};
}}
QLabel#pos_panel_title {{
    font-size: 14px; font-weight: 600; color: {t.t1};
}}
QLabel#pos_hint {{
    font-size: 11px; color: {t.t4};
}}
QFrame#pos_total_bar {{
    background: {t.card2}; border: 1px solid {t.border};
    border-radius: {br_card}; padding: 12px 16px;
}}
QLabel#pos_total_label {{
    font-size: 13px; font-weight: 600; color: {t.t3};
}}
QLabel#pos_total_value {{
    font-size: 28px; font-weight: 700; color: {acc};
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}}
QPushButton#pos_complete_btn {{
    background: {t.green}; color: #FFFFFF;
    border: none; border-radius: {br_btn};
    font-size: 14px; font-weight: 600;
    padding: 10px 24px; min-height: 44px;
}}
QPushButton#pos_complete_btn:hover {{ background: {_rgba(t.green, 'CC')}; }}
QPushButton#pos_complete_btn:pressed {{ background: {_rgba(t.green, '99')}; }}
QPushButton#pos_cancel_btn {{
    background: transparent; color: {t.t3};
    border: 1px solid {t.border}; border-radius: {br_btn};
    font-size: 13px; font-weight: 500;
    padding: 8px 20px; min-height: 44px;
}}
QPushButton#pos_cancel_btn:hover {{ background: {t.card2}; color: {t.t1}; }}
QPushButton#pos_add_btn {{
    background: {acc_20}; color: {acc};
    border: 1px solid {acc_40}; border-radius: 4px;
    font-size: 16px; font-weight: 700;
    min-width: 32px; max-width: 32px; min-height: 28px; max-height: 28px;
    padding: 0;
}}
QPushButton#pos_add_btn:hover {{ background: {acc_30}; }}
QPushButton#pos_remove_btn {{
    background: transparent; color: {t.red};
    border: 1px solid {r_40}; border-radius: {br_btn};
    font-size: 12px; font-weight: 500; padding: 4px 12px; min-height: 28px;
}}
QPushButton#pos_remove_btn:hover {{ background: {t.red}; color: #FFFFFF; }}

/* ── Admin panels (Suppliers / Locations) ──────────────── */
QFrame#admin_panel_header {{
    background: transparent; padding-bottom: 8px;
}}
QLabel#admin_panel_title {{
    font-size: 15px; font-weight: 700; color: {t.t1};
}}
QLabel#admin_panel_subtitle {{
    font-size: 12px; color: {t.t3};
}}
QFrame#admin_kpi {{
    background: {t.card}; border: 1px solid {t.border};
    border-radius: {br_card}; border-left: 3px solid {acc};
}}
QLabel#admin_kpi_label {{
    font-size: 10px; font-weight: 600; color: {t.t3};
    letter-spacing: 0.05em;
}}
QLabel#admin_kpi_value {{
    font-size: 20px; font-weight: 700; color: {t.t1};
}}
QLabel#admin_kpi_sub {{
    font-size: 10px; color: {t.t4};
}}
QPushButton#admin_action_btn {{
    background: {acc}; color: #FFFFFF;
    border: none; border-radius: {br_btn};
    font-size: 12px; font-weight: 600;
    padding: 6px 14px; min-height: 30px;
}}
QPushButton#admin_action_btn:hover {{ background: {acc_CC}; }}
QPushButton#admin_action_btn:pressed {{ background: {acc_99}; }}
QPushButton#admin_edit_btn {{
    background: {b_15}; color: {t.blue};
    border: 1px solid {b_40}; border-radius: 6px;
    padding: 0px; margin: 0px;
}}
QPushButton#admin_edit_btn:hover {{ background: {b_28}; border-color: {t.blue}; }}
QPushButton#admin_toggle_btn {{
    background: {_rgba(t.orange, '15')}; color: {t.orange};
    border: 1px solid {o_55}; border-radius: 6px;
    padding: 0px; margin: 0px;
}}
QPushButton#admin_toggle_btn:hover {{ background: {o_20}; border-color: {t.orange}; }}
QPushButton#admin_del_btn {{
    background: transparent; color: {t.red};
    border: 1px solid {r_40}; border-radius: 6px;
    padding: 0px; margin: 0px;
}}
QPushButton#admin_del_btn:hover {{ background: {r_15}; border-color: {t.red}; }}
QFrame#admin_search_bar {{
    background: {inp_bg}; border: 1px solid {t.border};
    border-radius: {br_input};
}}
QLabel#status_badge_active {{
    font-size: 11px; font-weight: 600; color: {t.green};
    background: {g_20}; border-radius: 4px; padding: 2px 8px;
}}
QLabel#status_badge_inactive {{
    font-size: 11px; font-weight: 600; color: {t.red};
    background: {r_15}; border-radius: 4px; padding: 2px 8px;
}}
QLabel#default_badge {{
    font-size: 11px; font-weight: 600; color: {acc};
    background: {acc_20}; border-radius: 4px; padding: 2px 8px;
}}

/* ── Admin dialog — sidebar navigation ──────────────── */
QDialog#admin_dialog {{
    background: {t.grad_top};
}}
QFrame#admin_sidebar {{
    background: {t.card};
    border-right: 1px solid {t.border};
    border-radius: 0;
    min-width: 220px;
    max-width: 220px;
}}
QLabel#admin_sidebar_title {{
    font-size: 14px; font-weight: 700; color: {t.t1};
    padding: 16px 16px 4px 16px;
}}
QLabel#admin_sidebar_subtitle {{
    font-size: 11px; color: {t.t3};
    padding: 0px 16px 8px 16px;
}}
QLabel#admin_nav_group {{
    font-size: 10px; font-weight: 600; color: {t.t3};
    letter-spacing: 0.08em;
    padding: 12px 16px 4px 16px;
}}
QPushButton#admin_nav_item {{
    background: transparent; color: {t.t2};
    border: none; border-radius: 6px;
    font-size: 12px; font-weight: 500;
    text-align: left; padding: 8px 16px;
    margin: 1px 8px;
    min-height: 34px; max-height: 34px;
}}
QPushButton#admin_nav_item:hover {{
    background: {_rgba(acc, '12')}; color: {t.t1};
}}
QPushButton#admin_nav_active {{
    background: {acc_20}; color: {acc};
    border: none;
    border-left: 3px solid {acc};
    border-radius: 0px 6px 6px 0px;
    font-size: 12px; font-weight: 600;
    text-align: left; padding: 8px 16px 8px 13px;
    margin: 1px 8px;
    min-height: 34px; max-height: 34px;
}}
QPushButton#admin_nav_active:hover {{
    background: {acc_30}; color: {acc};
}}
QFrame#admin_nav_separator {{
    background: {t.border}; border: none;
    margin: 6px 16px; max-height: 1px;
}}

/* Admin content area */
QLabel#admin_content_title {{
    font-size: 17px; font-weight: 700; color: {t.t1};
}}
QLabel#admin_content_desc {{
    font-size: 12px; color: {t.t3};
}}
QFrame#admin_form_card {{
    background: {t.card}; border: 1px solid {t.border};
    border-radius: {br_card}; padding: 16px;
}}
QLabel#admin_form_card_title {{
    font-size: 13px; font-weight: 600; color: {t.t1};
    padding-bottom: 2px;
}}
QLabel#admin_form_card_desc {{
    font-size: 11px; color: {t.t3};
    padding-bottom: 8px;
}}
QFrame#admin_info_card {{
    background: {t.card}; border: 1px solid {t.border};
    border-radius: {br_card}; border-left: 3px solid {t.blue};
}}
QLabel#admin_info_label {{
    font-size: 11px; font-weight: 500; color: {t.t3};
}}
QLabel#admin_info_value {{
    font-size: 12px; font-weight: 600; color: {t.t1};
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}}
"""


class ThemeManager(QObject):
    """Singleton coordinating Qt stylesheet application across the app.

    Emits ``changed`` after a theme toggle so components that captured
    ``tk.tX`` colors at construction time (inline ``setStyleSheet`` calls
    in widget ``__init__``) can re-read from ``THEME.tokens`` and refresh
    themselves. Widgets connect via:

        from app.core.theme import THEME
        THEME.changed.connect(self.apply_theme)

    Without this, a theme toggle re-paints the QSS-driven properties (the
    huge selector-based stylesheet at module level) but every f-string
    inline style remains stuck on the colors of the theme that was active
    when the widget was built.
    """

    # Emitted after a theme switch — connected widgets re-read THEME.tokens
    # and rebuild any inline styles they cached at construction time.
    changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._dark = True
        self._key = "pro_dark"  # Default to Pro Dark
        self._t = PRO_DARK
        self._targets: list = []
        self._css_cache: dict[str, str] = {}  # key -> pre-generated QSS

    @property
    def is_dark(self) -> bool: return self._dark

    @property
    def tokens(self) -> Tokens: return self._t

    @property
    def theme_key(self) -> str: return self._key

    def set_theme(self, key: str) -> None:
        """Switch to a named theme preset.

        The internal state (tokens, is_dark) updates immediately so any code
        that reads ``THEME.tokens`` right after this call sees the new theme.

        Stylesheet application is deferred to the next event-loop tick via
        ``QTimer.singleShot(0)``. This ensures that if set_theme() is
        called from inside an event handler (e.g. mousePressEvent on the
        toggle button) the handler returns first — keeping the UI
        responsive and letting the animation start before Qt re-styles
        the whole widget tree.

        On the deferred tick we:
          1. Apply the cached QSS to **every** registered target (the
             root window plus any extra top-level dialogs that called
             ``apply()`` / ``register()``). The legacy code only applied
             to ``_targets[0]`` which left dialogs / popups stuck on the
             previous theme.
          2. Emit ``changed`` so widgets that hold cached ``tk.tX`` color
             tokens can re-read from ``self.tokens`` and rebuild any
             inline styles they set during construction.
        """
        if key not in THEMES or key == self._key:
            return
        self._key = key
        self._t = THEMES[key]
        self._dark = self._t.is_dark
        ss = self.stylesheet()   # reads from cache — no work done here
        QTimer.singleShot(0, lambda: self._apply_to_all(ss))

    def _apply_to_all(self, ss: str) -> None:
        """Apply QSS to every registered target then emit ``changed``."""
        # Iterate over a snapshot — connected slots may add/remove targets.
        for w in list(self._targets):
            try:
                w.setStyleSheet(ss)
                w.update()
            except RuntimeError:
                # Widget was deleted — drop it from the registry.
                if w in self._targets:
                    self._targets.remove(w)
        # Notify connected widgets so they can refresh inline styles + repaint.
        try:
            self.changed.emit()
        except Exception:
            pass

    def _apply_ss(self, root: QWidget, ss: str) -> None:
        """Legacy single-target apply — kept for backwards compatibility
        with any external caller. New callers should use ``_apply_to_all``
        which handles the registered list.
        """
        try:
            root.setStyleSheet(ss)
            root.update()
        except RuntimeError:
            self._targets.clear()

    def toggle(self) -> None:
        """Toggle between dark and light variant of current style."""
        pairs = {"pro_dark": "pro_light", "pro_light": "pro_dark",
                 "dark": "light", "light": "dark"}
        self.set_theme(pairs.get(self._key, "pro_dark"))

    def cycle(self) -> None:
        """Cycle through all 4 themes: pro_dark → pro_light → dark → light → ..."""
        order = ["pro_dark", "pro_light", "dark", "light"]
        idx = order.index(self._key) if self._key in order else 0
        self.set_theme(order[(idx + 1) % len(order)])

    def stylesheet(self) -> str:
        """Return cached QSS for current theme — generated once per theme key."""
        if self._key not in self._css_cache:
            self._css_cache[self._key] = _ss(self._t)
        return self._css_cache[self._key]

    def apply(self, widget):
        """Apply stylesheet and register as root target."""
        widget.setStyleSheet(self.stylesheet())
        # Always keep root (first registered) at index 0
        if widget not in self._targets:
            self._targets.insert(0, widget)

    def register(self, widget):
        """Register a widget to receive theme updates (non-root)."""
        if widget not in self._targets:
            self._targets.append(widget)

    def warm_cache(self) -> None:
        """Pre-generate QSS for all themes in the background so first toggle is instant."""
        for key, tokens in THEMES.items():
            if key not in self._css_cache:
                self._css_cache[key] = _ss(tokens)


THEME = ThemeManager()
