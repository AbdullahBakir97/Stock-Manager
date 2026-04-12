"""
app/ui/components/mini_txn_list.py — Compact recent transaction list.
"""
from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.core.theme import THEME, _rgba
from app.core.i18n import t
from app.repositories.transaction_repo import TransactionRepository

_txn_repo = TransactionRepository()


class MiniTxnList(QWidget):
    """Shows the last N transactions for a given item in a compact list."""

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
