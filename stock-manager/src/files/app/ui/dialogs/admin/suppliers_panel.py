"""
app/ui/dialogs/admin/suppliers_panel.py — Professional supplier management panel.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QPushButton, QLabel, QTextEdit, QFrame,
    QDialog, QDialogButtonBox, QMessageBox, QScrollArea,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal

from app.core.theme import THEME
from app.core.icon_utils import get_colored_icon
from app.repositories.supplier_repo import SupplierRepository
from app.models.supplier import Supplier
from app.core.i18n import t
from app.ui.components.responsive_table import make_table_responsive

_sup_repo = SupplierRepository()


# ── KPI Card ────────────────────────────────────────────────────────────────

class _KpiCard(QFrame):
    """Small KPI metric card for the supplier summary row."""

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


# ── Add/Edit dialog ─────────────────────────────────────────────────────────

class _SupplierDialog(QDialog):
    """Modal dialog for adding or editing a supplier."""

    def __init__(self, parent=None, supplier: Supplier | None = None):
        super().__init__(parent)
        self._supplier = supplier
        self.setWindowTitle(t("sup_edit_title") if supplier else t("sup_add_title"))
        self.setMinimumWidth(460)
        THEME.apply(self)
        self._build()
        if supplier:
            self._populate(supplier)

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)

        # Header
        hdr = QLabel(t("sup_edit_title") if self._supplier else t("sup_add_title"))
        hdr.setObjectName("dlg_header")
        lay.addWidget(hdr)

        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(0, 0, 0, 0)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(t("sup_col_name"))
        self._contact_edit = QLineEdit()
        self._contact_edit.setPlaceholderText(t("sup_col_contact"))
        self._phone_edit = QLineEdit()
        self._phone_edit.setPlaceholderText(t("sup_col_phone"))
        self._email_edit = QLineEdit()
        self._email_edit.setPlaceholderText(t("sup_col_email"))
        self._address_edit = QLineEdit()
        self._address_edit.setPlaceholderText(t("sup_col_address"))
        self._notes_edit = QTextEdit()
        self._notes_edit.setMaximumHeight(80)
        self._notes_edit.setPlaceholderText(t("sup_col_notes"))

        form.addRow(t("sup_col_name") + " *", self._name_edit)
        form.addRow(t("sup_col_contact"), self._contact_edit)
        form.addRow(t("sup_col_phone"), self._phone_edit)
        form.addRow(t("sup_col_email"), self._email_edit)
        form.addRow(t("sup_col_address"), self._address_edit)
        form.addRow(t("sup_col_notes"), self._notes_edit)
        lay.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(t("alert_cancel") if t("alert_cancel") != "alert_cancel" else "Cancel")
        cancel_btn.setObjectName("btn_ghost")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        ok_btn = QPushButton(t("sup_btn_edit") if self._supplier else t("sup_btn_add"))
        ok_btn.setObjectName("btn_primary")
        ok_btn.clicked.connect(self._validate_and_accept)
        btn_row.addWidget(ok_btn)
        lay.addLayout(btn_row)

    def _populate(self, s: Supplier) -> None:
        self._name_edit.setText(s.name)
        self._contact_edit.setText(s.contact_name)
        self._phone_edit.setText(s.phone)
        self._email_edit.setText(s.email)
        self._address_edit.setText(s.address)
        self._notes_edit.setPlainText(s.notes)

    def _validate_and_accept(self) -> None:
        if not self._name_edit.text().strip():
            QMessageBox.warning(self, t("sup_add_title"), t("sup_name_required"))
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self._name_edit.text().strip(),
            "contact_name": self._contact_edit.text().strip(),
            "phone": self._phone_edit.text().strip(),
            "email": self._email_edit.text().strip(),
            "address": self._address_edit.text().strip(),
            "notes": self._notes_edit.toPlainText().strip(),
        }


# ── Panel ────────────────────────────────────────────────────────────────────

class SuppliersPanel(QWidget):
    """Professional supplier management panel with KPI summary."""

    suppliers_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._suppliers: list[Supplier] = []
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
        self._title = QLabel(t("admin_tab_suppliers"))
        self._title.setObjectName("admin_panel_title")
        title_col.addWidget(self._title)
        self._subtitle = QLabel(t("sup_panel_subtitle") if t("sup_panel_subtitle") != "sup_panel_subtitle"
                                else "Manage your supplier contacts and relationships")
        self._subtitle.setObjectName("admin_panel_subtitle")
        title_col.addWidget(self._subtitle)
        hdr_lay.addLayout(title_col)
        hdr_lay.addStretch()
        self._add_btn = QPushButton(t('sup_btn_add'))
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
        self._kpi_inactive = _KpiCard()
        for card in (self._kpi_total, self._kpi_active, self._kpi_inactive):
            kpi_row.addWidget(card)
        outer.addLayout(kpi_row)

        # ── Search bar ──
        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        self._search = QLineEdit()
        self._search.setPlaceholderText(f"  🔍  {t('sup_search_placeholder') if t('sup_search_placeholder') != 'sup_search_placeholder' else 'Search suppliers…'}")
        self._search.setObjectName("search_bar")
        self._search.setMaximumWidth(320)
        self._search.textChanged.connect(self._refresh)
        search_row.addWidget(self._search)
        search_row.addStretch()
        outer.addLayout(search_row)

        # ── Table ──
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels([
            t("sup_col_name"), t("sup_col_contact"), t("sup_col_phone"),
            t("sup_col_email"), t("sup_col_status"), "",
        ])
        hh = self._table.horizontalHeader()
        hh.setMinimumSectionSize(40)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in (1, 2, 3):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Interactive)
            self._table.setColumnWidth(c, 110)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(4, 80)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(5, 160)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self._table.setAlternatingRowColors(True)
        self._table.doubleClicked.connect(self._edit)
        outer.addWidget(self._table, 1)
        # Cols: 0=Name  1=Contact  2=Phone  3=Email  4=Status  5=Actions
        make_table_responsive(self._table, [
            (3, 850),   # Email   — hide when viewport < 850 px
            (2, 700),   # Phone   — hide when viewport < 700 px
            (1, 580),   # Contact — hide when viewport < 580 px
        ])

    # ── Data ─────────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        all_suppliers = _sup_repo.get_all()
        search = self._search.text().strip().lower()
        self._suppliers = all_suppliers
        if search:
            self._suppliers = [
                s for s in self._suppliers
                if search in s.name.lower() or search in s.contact_name.lower()
                or search in s.phone.lower() or search in s.email.lower()
            ]

        # Update KPIs
        total = len(all_suppliers)
        active = sum(1 for s in all_suppliers if s.is_active)
        inactive = total - active
        self._kpi_total.set_data(
            t("sup_kpi_total") if t("sup_kpi_total") != "sup_kpi_total" else "TOTAL SUPPLIERS",
            str(total), "")
        self._kpi_active.set_data(
            t("sup_kpi_active") if t("sup_kpi_active") != "sup_kpi_active" else "ACTIVE",
            str(active), "")
        self._kpi_inactive.set_data(
            t("sup_kpi_inactive") if t("sup_kpi_inactive") != "sup_kpi_inactive" else "INACTIVE",
            str(inactive), "")

        # Render table
        self._table.setRowCount(0)
        for sup in self._suppliers:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, self._ro(sup.name, sup.id))
            self._table.setItem(row, 1, self._ro(sup.contact_name, sup.id))
            self._table.setItem(row, 2, self._ro(sup.phone, sup.id))
            self._table.setItem(row, 3, self._ro(sup.email, sup.id))

            # Status badge
            status_lbl = QLabel(t("sup_active") if sup.is_active else t("sup_inactive"))
            status_lbl.setObjectName("status_badge_active" if sup.is_active else "status_badge_inactive")
            status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setCellWidget(row, 4, status_lbl)

            # Action buttons in a single cell widget
            tk = THEME.tokens
            action_w = QWidget()
            action_w.setFixedSize(152, 40)
            action_lay = QHBoxLayout(action_w)
            action_lay.setContentsMargins(4, 2, 4, 2)
            action_lay.setSpacing(8)

            for icon_name, obj_name, color, tip, cb in [
                ("edit",   "admin_edit_btn",   tk.blue,   t("sup_btn_edit"),
                 lambda _, s=sup: self._edit_supplier(s)),
                ("power",  "admin_toggle_btn", tk.orange, t("sup_btn_toggle"),
                 lambda _, s=sup: self._toggle_one(s)),
                ("delete", "admin_del_btn",    tk.red,    t("sup_btn_delete"),
                 lambda _, s=sup: self._delete_one(s)),
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

            self._table.setCellWidget(row, 5, action_w)
            self._table.setRowHeight(row, 48)

    # ── Actions ──────────────────────────────────────────────────────────────

    def _selected(self) -> list[Supplier]:
        rows = {idx.row() for idx in self._table.selectedIndexes()}
        return [self._suppliers[r] for r in sorted(rows) if r < len(self._suppliers)]

    def _add(self) -> None:
        dlg = _SupplierDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                _sup_repo.add(**data)
            except Exception as e:
                if "UNIQUE" in str(e):
                    QMessageBox.warning(
                        self, t("sup_add_title"),
                        t("sup_name_exists") if t("sup_name_exists") != "sup_name_exists"
                        else f"A supplier named '{data['name']}' already exists.",
                    )
                    return
                raise
            self._refresh()
            self.suppliers_changed.emit()

    def _edit(self) -> None:
        selected = self._selected()
        if len(selected) != 1:
            return
        self._edit_supplier(selected[0])

    def _edit_supplier(self, sup: Supplier) -> None:
        dlg = _SupplierDialog(self, supplier=sup)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                _sup_repo.update(sup.id, is_active=sup.is_active, **data)
            except Exception as e:
                if "UNIQUE" in str(e):
                    QMessageBox.warning(
                        self, t("sup_edit_title"),
                        t("sup_name_exists") if t("sup_name_exists") != "sup_name_exists"
                        else f"A supplier named '{data['name']}' already exists.",
                    )
                    return
                raise
            self._refresh()
            self.suppliers_changed.emit()

    def _toggle_one(self, sup: Supplier) -> None:
        _sup_repo.set_active(sup.id, not sup.is_active)
        self._refresh()
        self.suppliers_changed.emit()

    def _toggle_active(self) -> None:
        for sup in self._selected():
            _sup_repo.set_active(sup.id, not sup.is_active)
        self._refresh()
        self.suppliers_changed.emit()

    def _delete_one(self, sup: Supplier) -> None:
        ok = QMessageBox.question(
            self, t("sup_btn_delete"),
            t("sup_delete_confirm", n=1),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ok != QMessageBox.StandardButton.Yes:
            return
        if not _sup_repo.delete(sup.id):
            QMessageBox.warning(
                self, t("sup_btn_delete"),
                t("sup_delete_blocked") + f"\n{sup.name}",
            )
        self._refresh()
        self.suppliers_changed.emit()

    def _delete(self) -> None:
        selected = self._selected()
        if not selected:
            return
        ok = QMessageBox.question(
            self, t("sup_btn_delete"),
            t("sup_delete_confirm", n=len(selected)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ok != QMessageBox.StandardButton.Yes:
            return
        blocked = [s for s in selected if not _sup_repo.delete(s.id)]
        if blocked:
            names = ", ".join(s.name for s in blocked)
            QMessageBox.warning(
                self, t("sup_btn_delete"),
                t("sup_delete_blocked") + f"\n{names}",
            )
        self._refresh()
        self.suppliers_changed.emit()

    def reload(self) -> None:
        self._refresh()

    @staticmethod
    def _ro(text: str, sid: int) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        it.setData(Qt.ItemDataRole.UserRole, sid)
        return it
