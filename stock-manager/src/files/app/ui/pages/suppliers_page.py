"""app/ui/pages/suppliers_page.py — Professional suppliers management page."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QSizePolicy, QMessageBox, QDialog, QFormLayout, QLineEdit,
    QSpinBox, QDoubleSpinBox, QStackedWidget, QTextEdit,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor

from app.core.config import ShopConfig
from app.core.theme import THEME, _rgba
from app.core.i18n import t
from app.repositories.item_repo import ItemRepository
from app.services.supplier_service import SupplierService
from app.models.supplier import Supplier, SupplierItem
from app.ui.components.responsive_table import make_table_responsive

_sup_svc = SupplierService()
_item_repo = ItemRepository()


# ── KPI Card ──────────────────────────────────────────────────────────────────

class _KpiCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("summary_card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(88)
        self.setMaximumHeight(96)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(4)
        self._label = QLabel()
        self._label.setObjectName("card_label")
        self._value = QLabel("0")
        self._value.setObjectName("card_value")
        lay.addWidget(self._label)
        lay.addWidget(self._value)

    def set_data(self, label: str, value: str) -> None:
        self._label.setText(label)
        self._value.setText(value)


# ── Supplier Dialog ───────────────────────────────────────────────────────────

class _SupplierDialog(QDialog):
    """Modal dialog for adding/editing a supplier."""

    def __init__(self, parent=None, supplier: Supplier | None = None):
        super().__init__(parent)
        self._supplier = supplier
        self.setWindowTitle(
            t("sup_dlg_edit_title") if supplier else t("sup_dlg_title")
        )
        self.setMinimumWidth(480)
        THEME.apply(self)
        self._build()
        if supplier:
            self._load_data(supplier)

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)

        hdr = QLabel(
            t("sup_dlg_edit_title") if self._supplier else t("sup_dlg_title")
        )
        hdr.setObjectName("dlg_header")
        lay.addWidget(hdr)

        form = QFormLayout()
        form.setSpacing(8)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(t("sup_dlg_name"))
        form.addRow(t("sup_dlg_name"), self._name_edit)

        self._contact_edit = QLineEdit()
        self._contact_edit.setPlaceholderText(t("sup_dlg_contact"))
        form.addRow(t("sup_dlg_contact"), self._contact_edit)

        self._phone_edit = QLineEdit()
        self._phone_edit.setPlaceholderText(t("sup_dlg_phone"))
        form.addRow(t("sup_dlg_phone"), self._phone_edit)

        self._email_edit = QLineEdit()
        self._email_edit.setPlaceholderText(t("sup_dlg_email"))
        form.addRow(t("sup_dlg_email"), self._email_edit)

        self._address_edit = QLineEdit()
        self._address_edit.setPlaceholderText(t("sup_dlg_address"))
        form.addRow(t("sup_dlg_address"), self._address_edit)

        self._notes_edit = QTextEdit()
        self._notes_edit.setPlaceholderText(t("sup_dlg_notes"))
        self._notes_edit.setMaximumHeight(80)
        form.addRow(t("sup_dlg_notes"), self._notes_edit)

        self._rating_spin = QSpinBox()
        self._rating_spin.setRange(0, 5)
        self._rating_spin.setValue(0)
        form.addRow(t("sup_dlg_rating"), self._rating_spin)

        lay.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(t("alert_cancel"))
        cancel_btn.setObjectName("btn_ghost")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        ok_btn = QPushButton(t("btn_ok"))
        ok_btn.setObjectName("btn_primary")
        ok_btn.clicked.connect(self._validate)
        btn_row.addWidget(ok_btn)
        lay.addLayout(btn_row)

    def _load_data(self, supplier: Supplier) -> None:
        self._name_edit.setText(supplier.name)
        self._contact_edit.setText(supplier.contact_name)
        self._phone_edit.setText(supplier.phone)
        self._email_edit.setText(supplier.email)
        self._address_edit.setText(supplier.address)
        self._notes_edit.setText(supplier.notes)
        self._rating_spin.setValue(supplier.rating)

    def _validate(self) -> None:
        if not self._name_edit.text().strip():
            QMessageBox.warning(self, t("sup_dlg_title"), t("sup_warn_name"))
            return
        self.accept()

    def get_data(self) -> dict | None:
        return {
            "name": self._name_edit.text().strip(),
            "contact_name": self._contact_edit.text().strip(),
            "phone": self._phone_edit.text().strip(),
            "email": self._email_edit.text().strip(),
            "address": self._address_edit.text().strip(),
            "notes": self._notes_edit.toPlainText().strip(),
            "rating": self._rating_spin.value(),
        }


# ── Supplier Items Dialog ─────────────────────────────────────────────────────

class _SupplierItemsDialog(QDialog):
    """Dialog to manage items linked to a supplier."""

    def __init__(self, parent=None, supplier: Supplier | None = None):
        super().__init__(parent)
        self._supplier = supplier
        self.setWindowTitle(t("sup_items_title"))
        self.setMinimumWidth(640)
        self.setMinimumHeight(400)
        THEME.apply(self)
        self._build()
        if supplier:
            self._refresh()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        hdr = QLabel(t("sup_items_title"))
        hdr.setObjectName("dlg_header")
        lay.addWidget(hdr)

        # Add new item row
        add_row = QHBoxLayout()
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText(t("sup_dlg_item_search", default="Search items..."))
        add_row.addWidget(self._search_edit)

        self._cost_spin = QDoubleSpinBox()
        self._cost_spin.setRange(0, 999999)
        self._cost_spin.setDecimals(2)
        self._cost_spin.setPrefix("$")
        add_row.addWidget(self._cost_spin)

        self._lead_spin = QSpinBox()
        self._lead_spin.setRange(0, 365)
        self._lead_spin.setPrefix(t("sup_items_lead", default="Lead: "))
        self._lead_spin.setSuffix(" " + t("unit_days", default="days"))
        add_row.addWidget(self._lead_spin)

        add_btn = QPushButton(t("sup_items_link"))
        add_btn.setObjectName("btn_primary")
        add_btn.setMaximumWidth(100)
        add_btn.clicked.connect(self._add_item)
        add_row.addWidget(add_btn)
        lay.addLayout(add_row)

        # Items table
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            t("col_item"), t("sup_items_cost"), t("sup_items_lead"), t("col_actions")
        ])
        hh = self._table.horizontalHeader()
        hh.setMinimumSectionSize(40)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        lay.addWidget(self._table)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton(t("alert_close", default="Close"))
        close_btn.setObjectName("btn_ghost")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        lay.addLayout(btn_row)

        self._items_data: list[SupplierItem] = []

    def _add_item(self) -> None:
        if not self._supplier:
            return
        search = self._search_edit.text().strip()
        if not search or len(search) < 2:
            QMessageBox.warning(self, t("sup_items_title"), t("sup_warn_search"))
            return

        items = _item_repo.get_all_items(search=search)[:10]
        if not items:
            QMessageBox.warning(self, t("sup_items_title"), t("item_not_found"))
            return

        # Link first matching item (simplified; could be a selection dialog)
        item = items[0]
        try:
            _sup_svc.link_item(
                self._supplier.id, item.id,
                cost_price=self._cost_spin.value(),
                lead_days=self._lead_spin.value(),
            )
            self._search_edit.clear()
            self._cost_spin.setValue(0)
            self._lead_spin.setValue(0)
            self._refresh()
        except Exception as e:
            QMessageBox.warning(self, t("sup_items_title"), str(e))

    def _refresh(self) -> None:
        if not self._supplier:
            return
        self._items_data = _sup_svc.get_items(self._supplier.id)
        self._table.setRowCount(len(self._items_data))

        tk = THEME.tokens
        for i, si in enumerate(self._items_data):
            self._table.setItem(i, 0, QTableWidgetItem(si.item_name))

            cost_it = QTableWidgetItem(f"${si.cost_price:.2f}")
            cost_it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(i, 1, cost_it)

            lead_it = QTableWidgetItem(str(si.lead_days))
            lead_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 2, lead_it)

            # Delete button
            del_btn = QPushButton("✕")
            del_btn.setObjectName("mgmt_del")
            del_btn.setFixedSize(36, 28)
            del_btn.clicked.connect(
                lambda checked, sid=self._supplier.id, iid=si.item_id: self._remove_item(sid, iid)
            )
            self._table.setCellWidget(i, 3, del_btn)

            self._table.setRowHeight(i, 36)

    def _remove_item(self, supplier_id: int, item_id: int) -> None:
        reply = QMessageBox.question(
            self, t("sup_items_title"),
            t("alert_confirm_delete", default="Remove this item?")
        )
        if reply == QMessageBox.StandardButton.Yes:
            _sup_svc.unlink_item(supplier_id, item_id)
            self._refresh()


# ── Empty State ───────────────────────────────────────────────────────────────

class _EmptyState(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(8)
        icon_lbl = QLabel("🏢")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 48px;")
        lay.addWidget(icon_lbl)
        self._title = QLabel(t("sup_empty_title"))
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setStyleSheet("font-size: 16px; font-weight: 600;")
        lay.addWidget(self._title)
        self._sub = QLabel(t("sup_empty_sub"))
        self._sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub.setObjectName("detail_threshold")
        lay.addWidget(self._sub)


# ── Main Page ─────────────────────────────────────────────────────────────────

class SuppliersPage(QWidget):
    """Professional suppliers management page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._build()
        self._refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)

        # ── Header ──
        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(12)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self._title = QLabel(t("sup_title"))
        self._title.setStyleSheet("font-size: 20px; font-weight: 700;")
        title_col.addWidget(self._title)
        self._subtitle = QLabel(t("sup_subtitle"))
        self._subtitle.setObjectName("admin_panel_subtitle")
        self._subtitle.setStyleSheet("font-size: 12px;")
        title_col.addWidget(self._subtitle)
        hdr_row.addLayout(title_col)
        hdr_row.addStretch()

        self._new_btn = QPushButton(t("sup_btn_add"))
        self._new_btn.setObjectName("btn_primary")
        self._new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._new_btn.clicked.connect(self._create_supplier)
        hdr_row.addWidget(self._new_btn)
        root.addLayout(hdr_row)

        # ── KPIs ──
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)
        self._kpi_total = _KpiCard()
        self._kpi_active = _KpiCard()
        self._kpi_inactive = _KpiCard()
        self._kpi_rating = _KpiCard()
        for card in (self._kpi_total, self._kpi_active, self._kpi_inactive, self._kpi_rating):
            kpi_row.addWidget(card)
        root.addLayout(kpi_row)

        # ── Search bar ──
        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText(t("sup_search_ph"))
        self._search_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._search_edit.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self._search_edit, 1)
        search_row.addStretch()
        root.addLayout(search_row)

        # ── Table / Empty state ──
        self._stack = QStackedWidget()

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels([
            t("sup_col_name"), t("sup_col_contact"), t("sup_col_phone"),
            t("sup_col_email"), t("sup_col_items"), t("sup_col_rating"),
            t("sup_col_actions"),
        ])
        hh = self._table.horizontalHeader()
        hh.setMinimumSectionSize(40)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(6, 140)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        # Cols: 0=Name  1=Contact  2=Phone  3=Email  4=Items  5=Rating  6=Actions
        make_table_responsive(self._table, [
            (5, 950),   # Rating   — hide when viewport < 950 px
            (4, 800),   # Items    — hide when viewport < 800 px
            (3, 680),   # Email    — hide when viewport < 680 px
            (2, 560),   # Phone    — hide when viewport < 560 px
        ])

        self._empty = _EmptyState()
        self._stack.addWidget(self._table)
        self._stack.addWidget(self._empty)
        root.addWidget(self._stack, 1)

        self._suppliers_data: list[Supplier] = []

    # ── Data ──────────────────────────────────────────────────────────────────

    def _refresh(self):
        # KPIs
        summary = _sup_svc.get_summary()
        self._kpi_total.set_data(t("sup_kpi_total"), str(summary.get("total", 0) or 0))
        self._kpi_active.set_data(t("sup_kpi_active"), str(summary.get("active", 0) or 0))
        self._kpi_inactive.set_data(t("sup_kpi_inactive"), str(summary.get("inactive", 0) or 0))
        avg_rating = summary.get("avg_rating", 0) or 0
        rating_str = f"{avg_rating:.1f}/5" if avg_rating > 0 else "—"
        self._kpi_rating.set_data(t("sup_kpi_avg_rating"), rating_str)

        # Table
        search_text = self._search_edit.text().strip()
        suppliers = _sup_svc.get_all(search=search_text, active_only=False)
        self._suppliers_data = suppliers

        if not suppliers:
            self._stack.setCurrentIndex(1)
            return

        self._stack.setCurrentIndex(0)

        tk = THEME.tokens
        self._table.setRowCount(len(suppliers))
        for i, sup in enumerate(suppliers):
            self._table.setItem(i, 0, QTableWidgetItem(sup.name))
            self._table.setItem(i, 1, QTableWidgetItem(sup.contact_name or "—"))
            self._table.setItem(i, 2, QTableWidgetItem(sup.phone or "—"))
            self._table.setItem(i, 3, QTableWidgetItem(sup.email or "—"))

            items_it = QTableWidgetItem(str(sup.item_count))
            items_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 4, items_it)

            # Rating stars — use a colored label widget
            rating_w = QWidget()
            rating_lay = QHBoxLayout(rating_w)
            rating_lay.setContentsMargins(4, 0, 4, 0)
            rating_lay.setSpacing(0)
            rating_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            star_lbl = QLabel()
            filled = "★" * sup.rating
            empty = "☆" * (5 - sup.rating)
            star_lbl.setText(f'<span style="color:{tk.orange};font-size:14px;">{filled}</span>'
                             f'<span style="color:{_rgba(tk.t3, "60")};font-size:14px;">{empty}</span>')
            star_lbl.setTextFormat(Qt.TextFormat.RichText)
            star_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rating_lay.addWidget(star_lbl)
            self._table.setCellWidget(i, 5, rating_w)

            # Actions
            action_widget = QWidget()
            action_lay = QHBoxLayout(action_widget)
            action_lay.setContentsMargins(6, 6, 6, 6)
            action_lay.setSpacing(6)

            edit_btn = QPushButton(t("btn_edit", default="Edit"))
            edit_btn.setObjectName("mgmt_edit")
            edit_btn.setFixedHeight(26)
            edit_btn.setMinimumWidth(48)
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda checked, sid=sup.id: self._edit_supplier(sid))
            action_lay.addWidget(edit_btn)

            status_lbl = QLabel(
                t("sup_status_active") if sup.is_active else t("sup_status_inactive")
            )
            fg = tk.green if sup.is_active else tk.orange
            bg = _rgba(fg, "20")
            status_lbl.setStyleSheet(
                f"color:{fg}; background:{bg}; border-radius:6px;"
                "font-weight:700; font-size:9px; padding:4px 8px;"
            )
            status_lbl.setMaximumWidth(80)
            action_lay.addWidget(status_lbl)

            action_lay.addStretch()
            self._table.setCellWidget(i, 6, action_widget)
            self._table.setRowHeight(i, 48)

    def _on_search_changed(self, text: str):
        self._refresh()

    # ── Actions ───────────────────────────────────────────────────────────────

    def _create_supplier(self):
        dlg = _SupplierDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if data:
                try:
                    _sup_svc.add(**data)
                    self._refresh()
                except ValueError as e:
                    QMessageBox.warning(self, t("sup_dlg_title"), str(e))

    def _edit_supplier(self, supplier_id: int):
        supplier = _sup_svc.get_by_id(supplier_id)
        if not supplier:
            return

        dlg = _SupplierDialog(self, supplier=supplier)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if data:
                try:
                    _sup_svc.update(supplier_id, **data)
                    self._refresh()
                except ValueError as e:
                    QMessageBox.warning(self, t("sup_dlg_edit_title"), str(e))

    def retranslate(self):
        self._title.setText(t("sup_title"))
        self._subtitle.setText(t("sup_subtitle"))
        self._new_btn.setText(t("sup_btn_add"))
        self._search_edit.setPlaceholderText(t("sup_search_ph"))
        self._refresh()

    def refresh(self):
        self._refresh()
