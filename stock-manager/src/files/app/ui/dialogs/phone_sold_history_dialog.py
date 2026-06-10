"""app/ui/dialogs/phone_sold_history_dialog.py — Sold Phones history viewer."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QCheckBox,
)
from PyQt6.QtCore import Qt, QDate

from app.repositories.phone_repo import PhoneRepository
from app.ui.workers.worker_pool import POOL

_phone_repo = PhoneRepository()


class PhoneSoldHistoryDialog(QDialog):
    """Read-only history of every phone unit ever marked as 'sold'."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sold Phones History")
        self.resize(820, 520)
        self._build()
        self._reload()

    def _build(self) -> None:
        root = QVBoxLayout(self)

        filt = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search IMEI, brand, model…")
        self._search.textChanged.connect(self._on_filter_changed)
        filt.addWidget(self._search)

        self._use_dates = QCheckBox("Filter by date")
        self._use_dates.toggled.connect(self._on_filter_changed)
        filt.addWidget(self._use_dates)

        self._date_from = QDateEdit(calendarPopup=True)
        self._date_from.setDate(QDate.currentDate().addMonths(-1))
        self._date_from.dateChanged.connect(self._on_filter_changed)
        filt.addWidget(QLabel("From"))
        filt.addWidget(self._date_from)

        self._date_to = QDateEdit(calendarPopup=True)
        self._date_to.setDate(QDate.currentDate())
        self._date_to.dateChanged.connect(self._on_filter_changed)
        filt.addWidget(QLabel("To"))
        filt.addWidget(self._date_to)

        filt.addStretch()
        refresh_btn = QPushButton("↺ Refresh")
        refresh_btn.clicked.connect(self._reload)
        filt.addWidget(refresh_btn)
        root.addLayout(filt)

        self._summary_lbl = QLabel("")
        root.addWidget(self._summary_lbl)

        self._table = QTableWidget()
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        cols = ["Sold On", "Brand", "Model", "Storage", "IMEI", "Sale Price", "Note"]
        self._table.setColumnCount(len(cols))
        self._table.setHorizontalHeaderLabels(cols)
        self._table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self._table)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    def _on_filter_changed(self) -> None:
        self._date_from.setEnabled(self._use_dates.isChecked())
        self._date_to.setEnabled(self._use_dates.isChecked())
        self._reload()

    def _reload(self) -> None:
        search = self._search.text().strip()
        date_from = ""
        date_to = ""
        if self._use_dates.isChecked():
            date_from = self._date_from.date().toString("yyyy-MM-dd")
            date_to = self._date_to.date().toString("yyyy-MM-dd")
        POOL.submit(
            "phones_sold_history",
            lambda: _phone_repo.get_sold_history(
                search=search, date_from=date_from, date_to=date_to, limit=1000,
            ),
            self._apply,
        )

    def _apply(self, txs: list) -> None:
        self._table.setRowCount(0)
        total_value = 0.0
        for tx in txs:
            r = self._table.rowCount()
            self._table.insertRow(r)

            def _item(text: str) -> QTableWidgetItem:
                i = QTableWidgetItem(text)
                i.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                return i

            self._table.setItem(r, 0, _item(tx.timestamp.replace("T", " ")))
            self._table.setItem(r, 1, _item(tx.model_brand))
            self._table.setItem(r, 2, _item(tx.model_name))
            self._table.setItem(r, 3, _item(tx.storage or "—"))
            self._table.setItem(r, 4, _item(tx.imei or "—"))
            price = tx.sell_price
            if price:
                total_value += price
            self._table.setItem(r, 5, _item(f"€{price:.2f}" if price else "—"))
            self._table.setItem(r, 6, _item(tx.note or ""))

        self._summary_lbl.setText(
            f"{len(txs)} phone(s) sold — total €{total_value:.2f}"
        )
