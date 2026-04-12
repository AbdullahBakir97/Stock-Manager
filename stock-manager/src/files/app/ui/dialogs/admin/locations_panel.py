"""
app/ui/dialogs/admin/locations_panel.py — Professional location management panel.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QPushButton, QCheckBox, QLabel, QFrame,
    QDialog, QDialogButtonBox, QMessageBox, QScrollArea,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal

from app.core.theme import THEME
from app.core.icon_utils import get_colored_icon
from app.repositories.location_repo import LocationRepository
from app.models.location import Location
from app.core.i18n import t
from app.ui.components.responsive_table import make_table_responsive

_loc_repo = LocationRepository()


# ── KPI Card ────────────────────────────────────────────────────────────────

class _KpiCard(QFrame):
    """Small KPI metric card."""

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

class _LocationDialog(QDialog):
    """Modal dialog for adding or editing a location."""

    def __init__(self, parent=None, location: Location | None = None):
        super().__init__(parent)
        self._location = location
        self.setWindowTitle(t("loc_edit_title") if location else t("loc_add_title"))
        self.setMinimumWidth(420)
        THEME.apply(self)
        self._build()
        if location:
            self._populate(location)

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)

        hdr = QLabel(t("loc_edit_title") if self._location else t("loc_add_title"))
        hdr.setObjectName("dlg_header")
        lay.addWidget(hdr)

        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(0, 0, 0, 0)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(t("loc_col_name"))
        self._desc_edit = QLineEdit()
        self._desc_edit.setPlaceholderText(t("loc_col_description"))
        self._default_cb = QCheckBox(t("loc_set_default"))

        form.addRow(t("loc_col_name") + " *", self._name_edit)
        form.addRow(t("loc_col_description"), self._desc_edit)
        form.addRow("", self._default_cb)
        lay.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(t("alert_cancel") if t("alert_cancel") != "alert_cancel" else "Cancel")
        cancel_btn.setObjectName("btn_ghost")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        ok_btn = QPushButton(t("loc_btn_edit") if self._location else t("loc_btn_add"))
        ok_btn.setObjectName("btn_primary")
        ok_btn.clicked.connect(self._validate_and_accept)
        btn_row.addWidget(ok_btn)
        lay.addLayout(btn_row)

    def _populate(self, loc: Location) -> None:
        self._name_edit.setText(loc.name)
        self._desc_edit.setText(loc.description)
        self._default_cb.setChecked(loc.is_default)

    def _validate_and_accept(self) -> None:
        if not self._name_edit.text().strip():
            QMessageBox.warning(self, t("loc_add_title"), t("loc_name_required"))
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self._name_edit.text().strip(),
            "description": self._desc_edit.text().strip(),
            "is_default": self._default_cb.isChecked(),
        }


# ── Panel ────────────────────────────────────────────────────────────────────

class LocationsPanel(QWidget):
    """Professional location management panel with KPI summary."""

    locations_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._locations: list[Location] = []
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
        self._title = QLabel(t("admin_tab_locations"))
        self._title.setObjectName("admin_panel_title")
        title_col.addWidget(self._title)
        self._subtitle = QLabel(t("loc_panel_subtitle") if t("loc_panel_subtitle") != "loc_panel_subtitle"
                                else "Manage storage locations and warehouses")
        self._subtitle.setObjectName("admin_panel_subtitle")
        title_col.addWidget(self._subtitle)
        hdr_lay.addLayout(title_col)
        hdr_lay.addStretch()
        self._add_btn = QPushButton(t('loc_btn_add'))
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
        self._kpi_default = _KpiCard()
        for card in (self._kpi_total, self._kpi_active, self._kpi_default):
            kpi_row.addWidget(card)
        outer.addLayout(kpi_row)

        # ── Table ──
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            t("loc_col_name"), t("loc_col_description"),
            t("loc_col_default"), t("loc_col_status"), "",
        ])
        hh = self._table.horizontalHeader()
        hh.setMinimumSectionSize(40)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(2, 80)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(3, 80)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(4, 120)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.doubleClicked.connect(self._edit)
        outer.addWidget(self._table, 1)
        # Cols: 0=Name  1=Description  2=Default  3=Status  4=Actions
        make_table_responsive(self._table, [
            (3, 600),   # Status      — hide when viewport < 600 px
            (2, 500),   # Default     — hide when viewport < 500 px
        ])

    # ── Data ─────────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        self._locations = _loc_repo.get_all()

        # KPIs
        total = len(self._locations)
        active = sum(1 for loc in self._locations if loc.is_active)
        default_name = next((loc.name for loc in self._locations if loc.is_default), "—")
        self._kpi_total.set_data(
            t("loc_kpi_total") if t("loc_kpi_total") != "loc_kpi_total" else "TOTAL LOCATIONS",
            str(total), "")
        self._kpi_active.set_data(
            t("loc_kpi_active") if t("loc_kpi_active") != "loc_kpi_active" else "ACTIVE",
            str(active), "")
        self._kpi_default.set_data(
            t("loc_kpi_default") if t("loc_kpi_default") != "loc_kpi_default" else "DEFAULT",
            default_name, "")

        # Render table
        self._table.setRowCount(0)
        for loc in self._locations:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, self._ro(loc.name, loc.id))
            self._table.setItem(row, 1, self._ro(loc.description, loc.id))

            # Default badge
            if loc.is_default:
                badge = QLabel(t("loc_is_default"))
                badge.setObjectName("default_badge")
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setCellWidget(row, 2, badge)
            else:
                self._table.setItem(row, 2, self._ro("", loc.id))

            # Status badge
            status_lbl = QLabel(t("sup_active") if loc.is_active else t("sup_inactive"))
            status_lbl.setObjectName("status_badge_active" if loc.is_active else "status_badge_inactive")
            status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setCellWidget(row, 3, status_lbl)

            # Action buttons in a single cell widget
            tk = THEME.tokens
            action_w = QWidget()
            action_w.setFixedSize(108, 40)
            action_lay = QHBoxLayout(action_w)
            action_lay.setContentsMargins(4, 2, 4, 2)
            action_lay.setSpacing(8)

            for icon_name, obj_name, color, tip, cb in [
                ("edit",   "admin_edit_btn", tk.blue, t("loc_btn_edit"),
                 lambda _, l=loc: self._edit_location(l)),
                ("delete", "admin_del_btn",  tk.red,  t("loc_btn_delete"),
                 lambda _, l=loc: self._delete_one(l)),
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

            self._table.setCellWidget(row, 4, action_w)
            self._table.setRowHeight(row, 48)

    # ── Actions ──────────────────────────────────────────────────────────────

    def _selected(self) -> Location | None:
        rows = {idx.row() for idx in self._table.selectedIndexes()}
        if not rows:
            return None
        r = min(rows)
        return self._locations[r] if r < len(self._locations) else None

    def _add(self) -> None:
        dlg = _LocationDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                _loc_repo.add(**data)
            except Exception as e:
                if "UNIQUE" in str(e):
                    QMessageBox.warning(
                        self, t("loc_add_title"),
                        t("loc_name_exists") if t("loc_name_exists") != "loc_name_exists"
                        else f"A location named '{data['name']}' already exists.",
                    )
                    return
                raise
            self._refresh()
            self.locations_changed.emit()

    def _edit(self) -> None:
        loc = self._selected()
        if not loc:
            return
        self._edit_location(loc)

    def _edit_location(self, loc: Location) -> None:
        dlg = _LocationDialog(self, location=loc)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                _loc_repo.update(loc.id, is_active=loc.is_active, **data)
            except Exception as e:
                if "UNIQUE" in str(e):
                    QMessageBox.warning(
                        self, t("loc_edit_title"),
                        t("loc_name_exists") if t("loc_name_exists") != "loc_name_exists"
                        else f"A location named '{data['name']}' already exists.",
                    )
                    return
                raise
            self._refresh()
            self.locations_changed.emit()

    def _delete_one(self, loc: Location) -> None:
        ok = QMessageBox.question(
            self, t("loc_btn_delete"), t("loc_delete_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ok != QMessageBox.StandardButton.Yes:
            return
        if not _loc_repo.delete(loc.id):
            QMessageBox.warning(self, t("loc_btn_delete"), t("loc_delete_blocked"))
            return
        self._refresh()
        self.locations_changed.emit()

    def _delete(self) -> None:
        loc = self._selected()
        if not loc:
            return
        self._delete_one(loc)

    def reload(self) -> None:
        self._refresh()

    @staticmethod
    def _ro(text: str, lid: int) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        it.setData(Qt.ItemDataRole.UserRole, lid)
        return it
