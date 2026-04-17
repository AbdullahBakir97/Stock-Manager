"""
app/ui/components/transaction_table.py — Transaction history table widget.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from app.core.theme import THEME
from app.core.i18n import t, note_t
from app.ui.components.responsive_table import make_table_responsive


class TransactionTable(QTableWidget):
    """Table showing stock transaction history."""
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

        # ── Responsive column hiding ────────────────────────────────────────
        # Cols: 0=DateTime  1=Item  2=Operation  3=Qty  4=Before  5=After  6=Note
        # 1=Item, 2=Op, 3=Qty, 5=After are always visible.
        make_table_responsive(self, [
            (6, 900),   # Note     — hide when viewport < 900 px
            (4, 750),   # Before   — hide when viewport < 750 px
            (0, 520),   # DateTime — hide when viewport < 520 px
        ])

    def retranslate(self):
        self.setHorizontalHeaderLabels([t(k) for k in self._COL_KEYS])

    # ── Zoom ─────────────────────────────────────────────────────────────────
    def apply_zoom(self, factor: float) -> None:
        """Content-aware zoom — columns always fit header + widest data text."""
        from app.services.zoom_service import ZOOM
        from PyQt6.QtGui import QFont, QFontMetrics

        body_pt = ZOOM.scale(11, minimum=6)
        header_pt = ZOOM.scale(10, minimum=6)
        body_font = QFont("Segoe UI", body_pt)
        header_font = QFont("Segoe UI", header_pt, QFont.Weight.Bold)
        self.setFont(body_font)
        self.horizontalHeader().setFont(header_font)

        fm_header = QFontMetrics(header_font)
        fm_body = QFontMetrics(body_font)

        hdr_pad = max(6, int(round(header_pt * 1.4)))
        hdr_vpad = max(3, int(round(header_pt * 0.5)))
        body_pad = max(4, int(round(body_pt * 1.0)))

        # Override app-wide QSS so setFont actually takes effect
        self.horizontalHeader().setStyleSheet(
            f"QHeaderView::section {{ font-size: {header_pt}pt; "
            f"font-weight: 700; padding: {hdr_vpad}px {hdr_pad}px; }}"
        )

        hdr_side = hdr_pad + 4
        body_side = body_pad + 4

        for i, w in enumerate(self._WIDTHS):
            hdr_item = self.horizontalHeaderItem(i)
            hdr_txt = hdr_item.text() if hdr_item else ""
            hdr_w = fm_header.horizontalAdvance(hdr_txt) + hdr_side * 2
            data_w = 0
            for r in range(self.rowCount()):
                it = self.item(r, i)
                if it and it.text():
                    dw = fm_body.horizontalAdvance(it.text())
                    if dw > data_w:
                        data_w = dw
            data_w += body_side * 2
            final_w = max(ZOOM.scale(w, minimum=40), hdr_w, data_w)
            self.setColumnWidth(i, final_w)

        hdr_h = max(fm_header.height() + hdr_vpad * 2 + 4, 22)
        self.horizontalHeader().setFixedHeight(hdr_h)

        row_h = max(fm_body.height() + 8, ZOOM.scale(48, minimum=20))
        self.verticalHeader().setDefaultSectionSize(row_h)
        for r in range(self.rowCount()):
            self.setRowHeight(r, row_h)
        self.viewport().update()

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
                if j == 0:
                    it.setFont(QFont("JetBrains Mono", 10))
                elif j == 2:
                    it.setForeground(QColor(OP.get(op_key, tk.t3)))
                    it.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
                elif j == 3:
                    it.setForeground(QColor(tk.green if d >= 0 else tk.red))
                    it.setFont(_mono_d)
                elif j in (4, 5):
                    it.setFont(QFont("JetBrains Mono", 10))
                self.setItem(i, j, it)
            self.setRowHeight(i, 48)
