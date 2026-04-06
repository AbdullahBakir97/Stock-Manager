"""
app/ui/dialogs/admin/customers_panel.py — Professional customer management panel.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QLineEdit, QPushButton, QLabel, QTextEdit, QFrame,
    QDialog, QMessageBox, QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal

from app.core.theme import THEME
from app.core.icon_utils import get_colored_icon
from app.services.customer_service import CustomerService
from app.services.sale_service import SaleService
from app.models.customer import Customer
from app.core.i18n import t
from app.core.config import ShopConfig
from app.ui.components.responsive_table import make_table_responsive

_svc = CustomerService()
_sale_svc = SaleService()


# ── KPI Card ────────────────────────────────────────────────────────────────

class _KpiCard(QFrame):
    """Small KPI metric card for the customer summary row."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("admin_kpi")
        self.setFixedHeight(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)
        self._label = QLabel()
        self._label.setObjectName("admin_kpi_label")
        self._value = QLabel()
        self._value.setObjectName("admin_kpi_value")
        self._sub = QLabel()
        self._sub.setObjectName("admin_kpi_sub")
        lay.addWidget(self._label)
        lay.addWidget(self._value)
        lay.addWidget(self._sub)

    def set_data(self, label: str, value: str, sub: str = "") -> None:
        self._label.setText(label)
        self._value.setText(value)
        self._sub.setText(sub)


# ── Add / Edit Dialog ───────────────────────────────────────────────────────

class _CustomerDialog(QDialog):
    """Modal dialog for adding or editing a customer."""

    def __init__(self, parent=None, customer: Customer | None = None):
        super().__init__(parent)
        self._customer = customer
        self.setWindowTitle(t("cust_dlg_edit") if customer else t("cust_dlg_add"))
        self.setMinimumWidth(460)
        THEME.apply(self)
        self._build()
        if customer:
            self._populate(customer)

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)

        # Header
        hdr = QLabel(t("cust_dlg_edit") if self._customer else t("cust_dlg_add"))
        hdr.setObjectName("dlg_header")
        lay.addWidget(hdr)

        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(0, 0, 0, 0)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(t("cust_lbl_name"))
        self._phone_edit = QLineEdit()
        self._phone_edit.setPlaceholderText(t("cust_lbl_phone"))
        self._email_edit = QLineEdit()
        self._email_edit.setPlaceholderText(t("cust_lbl_email"))
        self._address_edit = QLineEdit()
        self._address_edit.setPlaceholderText(t("cust_lbl_address"))
        self._notes_edit = QTextEdit()
        self._notes_edit.setMaximumHeight(80)
        self._notes_edit.setPlaceholderText(t("cust_lbl_notes"))

        form.addRow(t("cust_lbl_name") + " *", self._name_edit)
        form.addRow(t("cust_lbl_phone"), self._phone_edit)
        form.addRow(t("cust_lbl_email"), self._email_edit)
        form.addRow(t("cust_lbl_address"), self._address_edit)
        form.addRow(t("cust_lbl_notes"), self._notes_edit)
        lay.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(t("alert_cancel") if t("alert_cancel") != "alert_cancel" else "Cancel")
        cancel_btn.setObjectName("btn_ghost")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        ok_btn = QPushButton(t("cust_dlg_edit") if self._customer else t("cust_dlg_add"))
        ok_btn.setObjectName("btn_primary")
        ok_btn.clicked.connect(self._validate_and_accept)
        btn_row.addWidget(ok_btn)
        lay.addLayout(btn_row)

    def _populate(self, c: Customer) -> None:
        self._name_edit.setText(c.name)
        self._phone_edit.setText(c.phone)
        self._email_edit.setText(c.email)
        self._address_edit.setText(c.address)
        self._notes_edit.setPlainText(c.notes)

    def _validate_and_accept(self) -> None:
        if not self._name_edit.text().strip():
            QMessageBox.warning(self, t("cust_dlg_add"), t("cust_name_required"))
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self._name_edit.text().strip(),
            "phone": self._phone_edit.text().strip(),
            "email": self._email_edit.text().strip(),
            "address": self._address_edit.text().strip(),
            "notes": self._notes_edit.toPlainText().strip(),
        }


# ── Panel ────────────────────────────────────────────────────────────────────

class CustomersPanel(QWidget):
    """Professional customer management panel with KPI summary."""

    customers_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._customers: list[Customer] = []
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setObjectName("analytics_scroll")
        inner = QWidget()
        scroll.setWidget(inner)

        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.addWidget(scroll)

        outer = QVBoxLayout(inner)
        outer.setContentsMargins(20, 16, 20, 16)
        outer.setSpacing(14)

        # ── Header ──
        hdr_frame = QFrame()
        hdr_frame.setObjectName("admin_panel_header")
        hdr_lay = QHBoxLayout(hdr_frame)
        hdr_lay.setContentsMargins(0, 0, 0, 0)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self._title = QLabel(t("cust_page_title"))
        self._title.setObjectName("admin_panel_title")
        title_col.addWidget(self._title)
        self._subtitle = QLabel(t("cust_page_desc"))
        self._subtitle.setObjectName("admin_panel_subtitle")
        title_col.addWidget(self._subtitle)
        hdr_lay.addLayout(title_col)
        hdr_lay.addStretch()
        self._add_btn = QPushButton(t('cust_btn_add'))
        self._add_btn.setObjectName("admin_action_btn")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self._add)
        hdr_lay.addWidget(self._add_btn)
        outer.addWidget(hdr_frame)

        # ── KPI row ──
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)
        self._kpi_total = _KpiCard()
        self._kpi_active = _KpiCard()
        self._kpi_purchases = _KpiCard()
        for card in (self._kpi_total, self._kpi_active, self._kpi_purchases):
            kpi_row.addWidget(card)
        outer.addLayout(kpi_row)

        # ── Search bar ──
        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        self._search = QLineEdit()
        self._search.setPlaceholderText("  🔍  Search customers…")
        self._search.setObjectName("search_bar")
        self._search.setMaximumWidth(320)
        self._search.textChanged.connect(self._refresh)
        search_row.addWidget(self._search)
        search_row.addStretch()
        outer.addLayout(search_row)

        # ── Table ──
        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels([
            t("cust_col_name"), t("cust_col_phone"), t("cust_col_email"),
            t("cust_col_purchases"), t("cust_col_total_spent"),
            t("cust_col_last_purchase"), "",
        ])
        hh = self._table.horizontalHeader()
        hh.setMinimumSectionSize(40)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in (1, 2):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Interactive)
            self._table.setColumnWidth(c, 120)
        for c in (3, 4):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Interactive)
            self._table.setColumnWidth(c, 85)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(5, 110)
        hh.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(6, 160)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self._table.setAlternatingRowColors(True)
        self._table.doubleClicked.connect(self._edit)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        outer.addWidget(self._table, 1)
        # Cols: 0=Name  1=Phone  2=Email  3=Purchases  4=Total Spent  5=Last Purchase  6=Actions
        make_table_responsive(self._table, [
            (5, 950),   # Last Purchase — hide when viewport < 950 px
            (3, 800),   # Purchases     — hide when viewport < 800 px
            (1, 650),   # Phone         — hide when viewport < 650 px
        ])

        # ── Customer Detail Card ──
        self._detail_card = QFrame()
        self._detail_card.setObjectName("admin_form_card")
        detail_lay = QVBoxLayout(self._detail_card)
        detail_lay.setContentsMargins(16, 12, 16, 12)
        detail_lay.setSpacing(8)

        detail_hdr = QHBoxLayout()
        self._detail_title = QLabel("Select a customer to view details")
        self._detail_title.setObjectName("admin_form_card_title")
        detail_hdr.addWidget(self._detail_title)
        detail_hdr.addStretch()
        detail_lay.addLayout(detail_hdr)

        # Info row
        info_row = QHBoxLayout()
        info_row.setSpacing(20)
        self._detail_phone = QLabel()
        self._detail_phone.setObjectName("admin_info_label")
        self._detail_email = QLabel()
        self._detail_email.setObjectName("admin_info_label")
        self._detail_address = QLabel()
        self._detail_address.setObjectName("admin_info_label")
        self._detail_notes = QLabel()
        self._detail_notes.setObjectName("admin_info_label")
        for w in (self._detail_phone, self._detail_email,
                  self._detail_address, self._detail_notes):
            info_row.addWidget(w)
        info_row.addStretch()
        detail_lay.addLayout(info_row)

        # Purchase history table
        self._history_table = QTableWidget(0, 4)
        self._history_table.setHorizontalHeaderLabels([
            "Date", "Items", "Total", "Note",
        ])
        self._history_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Interactive)
        self._history_table.setColumnWidth(0, 160)
        self._history_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Interactive)
        self._history_table.setColumnWidth(1, 60)
        self._history_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Interactive)
        self._history_table.setColumnWidth(2, 100)
        self._history_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch)
        self._history_table.verticalHeader().setVisible(False)
        self._history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._history_table.setAlternatingRowColors(True)
        self._history_table.setMaximumHeight(180)
        detail_lay.addWidget(self._history_table)

        self._detail_card.setVisible(False)
        outer.addWidget(self._detail_card)

    # ── Data ─────────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        all_customers = _svc.get_all()
        search = self._search.text().strip().lower()
        self._customers = all_customers
        if search:
            self._customers = [
                c for c in self._customers
                if search in c.name.lower() or search in c.phone.lower()
                or search in c.email.lower()
            ]

        # Update KPIs
        summary = _svc.get_summary()
        self._kpi_total.set_data(t("cust_kpi_total"), str(summary["total"]), "")
        self._kpi_active.set_data(t("cust_kpi_active"), str(summary["active"]), "")
        self._kpi_purchases.set_data(
            t("cust_kpi_with_purchases"), str(summary["with_purchases"]), "")

        # Render table
        self._table.setRowCount(0)
        for cust in self._customers:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, self._ro(cust.name, cust.id))
            self._table.setItem(row, 1, self._ro(cust.phone, cust.id))
            self._table.setItem(row, 2, self._ro(cust.email, cust.id))
            self._table.setItem(row, 3, self._ro(str(cust.total_purchases), cust.id))

            # Format currency
            spent_text = f"{cust.total_spent:,.2f}"
            self._table.setItem(row, 4, self._ro(spent_text, cust.id))
            self._table.setItem(row, 5, self._ro(cust.last_purchase, cust.id))

            # Action buttons in a single cell widget
            tk = THEME.tokens
            action_w = QWidget()
            action_w.setFixedSize(152, 40)
            action_lay = QHBoxLayout(action_w)
            action_lay.setContentsMargins(4, 2, 4, 2)
            action_lay.setSpacing(8)

            for icon_name, obj_name, color, tip, cb in [
                ("edit",   "admin_edit_btn",   tk.blue,   t("cust_dlg_edit"),
                 lambda _, c=cust: self._edit_customer(c)),
                ("power",  "admin_toggle_btn", tk.orange, "Toggle active",
                 lambda _, c=cust: self._toggle_one(c)),
                ("delete", "admin_del_btn",    tk.red,    "Delete",
                 lambda _, c=cust: self._delete_one(c)),
            ]:
                btn = QPushButton()
                btn.setObjectName(obj_name)
                btn.setIcon(get_colored_icon(icon_name, color))
                btn.setIconSize(QSize(15, 15))
                btn.setToolTip(tip)
                btn.setFixedSize(36, 36)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(cb)
                action_lay.addWidget(btn)

            self._table.setCellWidget(row, 6, action_w)
            self._table.setRowHeight(row, 48)

    # ── Detail view ───────────────────────────────────────────────────────────

    def _on_selection_changed(self) -> None:
        """Show detail card when a single customer is selected."""
        selected = self._selected()
        if len(selected) != 1:
            self._detail_card.setVisible(False)
            return

        cust = selected[0]
        self._detail_card.setVisible(True)
        self._detail_title.setText(f"📋  {cust.name}")
        self._detail_phone.setText(f"Phone: {cust.phone or '—'}")
        self._detail_email.setText(f"Email: {cust.email or '—'}")
        self._detail_address.setText(f"Address: {cust.address or '—'}")
        self._detail_notes.setText(f"Notes: {cust.notes or '—'}")

        # Load purchase history
        cfg = ShopConfig.get()
        sales = _sale_svc.get_by_customer(cust.id, limit=20)
        self._history_table.setRowCount(0)
        for sale in sales:
            row = self._history_table.rowCount()
            self._history_table.insertRow(row)
            self._history_table.setItem(row, 0, QTableWidgetItem(sale.timestamp))
            self._history_table.setItem(
                row, 1, QTableWidgetItem(str(sale.item_count)))
            net = sale.net_total
            self._history_table.setItem(
                row, 2, QTableWidgetItem(f"{net:,.2f} {cfg.currency}"))
            self._history_table.setItem(row, 3, QTableWidgetItem(sale.note))
            self._history_table.setRowHeight(row, 36)

    # ── Actions ──────────────────────────────────────────────────────────────

    def _selected(self) -> list[Customer]:
        rows = {idx.row() for idx in self._table.selectedIndexes()}
        return [self._customers[r] for r in sorted(rows) if r < len(self._customers)]

    def _add(self) -> None:
        dlg = _CustomerDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                _svc.add_customer(**data)
            except ValueError as e:
                QMessageBox.warning(self, t("cust_dlg_add"), str(e))
                return
            self._refresh()
            self.customers_changed.emit()

    def _edit(self) -> None:
        selected = self._selected()
        if len(selected) != 1:
            return
        self._edit_customer(selected[0])

    def _edit_customer(self, cust: Customer) -> None:
        dlg = _CustomerDialog(self, customer=cust)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                _svc.update_customer(cust.id, **data)
            except ValueError as e:
                QMessageBox.warning(self, t("cust_dlg_edit"), str(e))
                return
            self._refresh()
            self.customers_changed.emit()

    def _toggle_one(self, cust: Customer) -> None:
        _svc.toggle_active(cust.id)
        self._refresh()
        self.customers_changed.emit()

    def _delete_one(self, cust: Customer) -> None:
        ok = QMessageBox.question(
            self, t("cust_dlg_edit"),
            t("cust_delete_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ok != QMessageBox.StandardButton.Yes:
            return
        if not _svc.delete_customer(cust.id):
            QMessageBox.warning(self, t("cust_dlg_edit"), t("cust_delete_blocked"))
        self._refresh()
        self.customers_changed.emit()

    def reload(self) -> None:
        self._refresh()

    @staticmethod
    def _ro(text: str, cid: int) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        it.setData(Qt.ItemDataRole.UserRole, cid)
        return it
