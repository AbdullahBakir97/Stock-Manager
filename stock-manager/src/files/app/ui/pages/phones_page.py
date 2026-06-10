"""app/ui/pages/phones_page.py — Phone unit inventory page."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame, QSizePolicy,
    QMessageBox, QScrollArea,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from app.core.i18n import t
from app.models.phone_unit import PhoneUnit
from app.repositories.phone_repo import PhoneRepository
from app.services.undo_manager import UNDO, Command
from app.ui.workers.worker_pool import POOL

_phone_repo = PhoneRepository()

STORAGE_COLS = ["64GB", "128GB", "256GB", "512GB", "1TB", "Other"]

# ── Color helpers ────────────────────────────────────────────────────────────

def _cell_color(count: int) -> str:
    if count == 0:
        return "#444"
    if count <= 2:
        return "#8B6914"   # amber
    return "#1A6B3C"       # green


def _cell_fg(count: int) -> str:
    return "#666" if count == 0 else "#FFF"


class PhonesPage(QWidget):

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._selected_model_id: int | None = None
        self._grid_data: list[dict] = []
        self._detail_units: list[PhoneUnit] = []
        self._filter_brand   = ""
        self._filter_storage = ""
        self._filter_cond    = ""
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        root.addWidget(self._build_kpi_row())
        root.addWidget(self._build_filter_row())
        root.addWidget(self._build_grid())

        self._detail_container = self._build_detail_panel()
        self._detail_container.setVisible(False)
        root.addWidget(self._detail_container)

    def _build_kpi_row(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("kpi_row")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 4)
        lay.setSpacing(8)

        self._kpi_total  = self._kpi_card(t("ph_kpi_total"), "0")
        self._kpi_stock  = self._kpi_card(t("ph_kpi_in_stock"), "0")
        self._kpi_sold   = self._kpi_card(t("ph_kpi_sold"), "0")
        self._kpi_batt   = self._kpi_card(t("ph_kpi_avg_battery"), "—")
        self._kpi_value  = self._kpi_card(t("ph_kpi_stock_value"), "€0")

        for w in (self._kpi_total, self._kpi_stock, self._kpi_sold,
                  self._kpi_batt, self._kpi_value):
            lay.addWidget(w)
        lay.addStretch()
        return frame

    def _kpi_card(self, label: str, value: str) -> QFrame:
        card = QFrame()
        card.setObjectName("kpi_card")
        card.setFixedHeight(64)
        card.setMinimumWidth(110)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(2)
        val_lbl = QLabel(value)
        val_lbl.setObjectName("kpi_value")
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = QFont(); f.setBold(True); f.setPointSize(16)
        val_lbl.setFont(f)
        lbl = QLabel(label)
        lbl.setObjectName("kpi_label")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(val_lbl)
        lay.addWidget(lbl)
        card._val_lbl = val_lbl
        card._lbl = lbl
        return card

    def _build_filter_row(self) -> QWidget:
        frame = QWidget()
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self._brand_combo = QComboBox()
        self._brand_combo.addItem(t("ph_filter_all_brands"), "")
        self._brand_combo.currentIndexChanged.connect(self._on_filter_changed)
        lay.addWidget(self._brand_combo)

        self._storage_combo = QComboBox()
        self._storage_combo.addItem(t("ph_filter_all_storage"), "")
        for s in STORAGE_COLS:
            self._storage_combo.addItem(s, s)
        self._storage_combo.currentIndexChanged.connect(self._on_filter_changed)
        lay.addWidget(self._storage_combo)

        self._cond_combo = QComboBox()
        self._cond_combo.addItem(t("ph_filter_all_conditions"), "")
        for val, key in [("new", "ph_cond_new"), ("used", "ph_cond_used"), ("refurbished", "ph_cond_refurbished")]:
            self._cond_combo.addItem(t(key), val)
        self._cond_combo.currentIndexChanged.connect(self._on_filter_changed)
        lay.addWidget(self._cond_combo)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText(t("ph_search_placeholder"))
        self._search_edit.setFixedWidth(200)
        self._search_edit.textChanged.connect(self._on_search_changed)
        lay.addWidget(self._search_edit)

        lay.addStretch()

        self._add_btn = QPushButton(t("ph_btn_add"))
        self._add_btn.setObjectName("btn_primary")
        self._add_btn.clicked.connect(self._add_phone)
        lay.addWidget(self._add_btn)

        self._sold_history_btn = QPushButton(t("ph_btn_sold_history"))
        self._sold_history_btn.setToolTip(t("ph_tip_sold_history"))
        self._sold_history_btn.clicked.connect(self._open_sold_history)
        lay.addWidget(self._sold_history_btn)

        self._labels_btn = QPushButton(t("ph_btn_labels"))
        self._labels_btn.setToolTip(t("ph_tip_labels"))
        self._labels_btn.clicked.connect(self._open_labels_dialog)
        lay.addWidget(self._labels_btn)

        self._refresh_btn = QPushButton(t("ph_btn_refresh"))
        self._refresh_btn.clicked.connect(self.refresh)
        lay.addWidget(self._refresh_btn)

        return frame

    def _build_grid(self) -> QWidget:
        self._grid = QTableWidget()
        self._grid.setObjectName("phone_grid")
        self._grid.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._grid.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._grid.setAlternatingRowColors(False)
        self._grid.verticalHeader().setVisible(False)
        self._grid.setFixedHeight(260)

        headers = [t("ph_col_brand_model")] + STORAGE_COLS + [t("ph_col_total")]
        self._grid.setColumnCount(len(headers))
        self._grid.setHorizontalHeaderLabels(headers)
        self._grid.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, len(headers)):
            self._grid.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeMode.Fixed
            )
            self._grid.setColumnWidth(i, 68)

        self._grid.itemSelectionChanged.connect(self._on_grid_row_selected)
        return self._grid

    def _build_detail_panel(self) -> QWidget:
        container = QFrame()
        container.setObjectName("detail_panel")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(4)

        hdr = QHBoxLayout()
        self._detail_title = QLabel(t("ph_units_title"))
        self._detail_title.setObjectName("section_header")
        f = QFont(); f.setBold(True)
        self._detail_title.setFont(f)
        hdr.addWidget(self._detail_title)
        hdr.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(lambda: (
            self._detail_container.setVisible(False),
            self._grid.clearSelection(),
        ))
        hdr.addWidget(close_btn)
        lay.addLayout(hdr)

        self._detail_table = QTableWidget()
        self._detail_table.setObjectName("detail_table")
        self._detail_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._detail_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._detail_table.verticalHeader().setVisible(False)
        self._detail_table.setAlternatingRowColors(True)
        self._detail_table.setFixedHeight(200)

        cols = [
            t("ph_col_imei"), t("ph_col_storage"), t("ph_col_condition"),
            t("ph_col_battery"), t("ph_col_buy"), t("ph_col_sell"),
            t("ph_col_status"), t("ph_col_notes"), t("ph_col_actions"),
        ]
        self._detail_table.setColumnCount(len(cols))
        self._detail_table.setHorizontalHeaderLabels(cols)
        self._detail_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._detail_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        self._detail_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self._detail_table.setColumnWidth(8, 76)

        lay.addWidget(self._detail_table)
        return container

    # ── Public ────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        POOL.submit("phones_grid", self._fetch_data, self._apply_data)

    def retranslate(self) -> None:
        # KPI cards
        self._kpi_total._lbl.setText(t("ph_kpi_total"))
        self._kpi_stock._lbl.setText(t("ph_kpi_in_stock"))
        self._kpi_sold._lbl.setText(t("ph_kpi_sold"))
        self._kpi_batt._lbl.setText(t("ph_kpi_avg_battery"))
        self._kpi_value._lbl.setText(t("ph_kpi_stock_value"))

        # Filter row
        self._brand_combo.setItemText(0, t("ph_filter_all_brands"))
        self._storage_combo.setItemText(0, t("ph_filter_all_storage"))
        self._cond_combo.setItemText(0, t("ph_filter_all_conditions"))
        for i, key in enumerate(("ph_cond_new", "ph_cond_used", "ph_cond_refurbished"), start=1):
            self._cond_combo.setItemText(i, t(key))
        self._search_edit.setPlaceholderText(t("ph_search_placeholder"))
        self._add_btn.setText(t("ph_btn_add"))
        self._sold_history_btn.setText(t("ph_btn_sold_history"))
        self._sold_history_btn.setToolTip(t("ph_tip_sold_history"))
        self._labels_btn.setText(t("ph_btn_labels"))
        self._labels_btn.setToolTip(t("ph_tip_labels"))
        self._refresh_btn.setText(t("ph_btn_refresh"))

        # Grid headers
        headers = [t("ph_col_brand_model")] + STORAGE_COLS + [t("ph_col_total")]
        self._grid.setHorizontalHeaderLabels(headers)

        # Detail panel
        self._detail_title.setText(t("ph_units_title"))
        cols = [
            t("ph_col_imei"), t("ph_col_storage"), t("ph_col_condition"),
            t("ph_col_battery"), t("ph_col_buy"), t("ph_col_sell"),
            t("ph_col_status"), t("ph_col_notes"), t("ph_col_actions"),
        ]
        self._detail_table.setHorizontalHeaderLabels(cols)

        self.refresh()

    # ── Async data ────────────────────────────────────────────────────────────

    def _fetch_data(self) -> dict:
        from app.core.database import get_connection
        try:
            with get_connection() as conn:
                brand_rows = conn.execute(
                    "SELECT DISTINCT brand FROM phone_models ORDER BY brand"
                ).fetchall()
            all_brands = [r["brand"] for r in brand_rows]
        except Exception:
            all_brands = []
        return {
            "grid":    _phone_repo.get_stock_grid(),
            "summary": _phone_repo.get_summary(),
            "brands":  all_brands,
        }

    def _apply_data(self, data: dict) -> None:
        self._grid_data = data["grid"]
        self._apply_summary(data["summary"])
        self._apply_brands(data.get("brands", []))
        self._apply_grid(self._grid_data)

    def _apply_summary(self, s: dict) -> None:
        self._kpi_total._val_lbl.setText(str(s.get("total", 0)))
        self._kpi_stock._val_lbl.setText(str(s.get("in_stock", 0)))
        self._kpi_sold._val_lbl.setText(str(s.get("sold", 0)))
        avg = s.get("avg_battery")
        self._kpi_batt._val_lbl.setText(f"{avg}%" if avg is not None else "—")
        self._kpi_value._val_lbl.setText(f"€{s.get('total_value', 0):.2f}")

    def _apply_brands(self, brands: list[str]) -> None:
        current = self._brand_combo.currentData()
        self._brand_combo.blockSignals(True)
        self._brand_combo.clear()
        self._brand_combo.addItem(t("ph_filter_all_brands"), "")
        for b in brands:
            self._brand_combo.addItem(b, b)
        # Restore selection
        idx = self._brand_combo.findData(current)
        if idx >= 0:
            self._brand_combo.setCurrentIndex(idx)
        self._brand_combo.blockSignals(False)

    def _apply_grid(self, rows: list[dict]) -> None:
        self._grid.setRowCount(0)

        # Apply active filters
        brand_f   = self._filter_brand
        storage_f = self._filter_storage

        # Build: {(model_id, storage): count}
        cnt_map: dict[tuple, int] = {}
        model_meta: dict[int, tuple] = {}  # model_id → (brand, name)
        for r in rows:
            mid     = r["model_id"]
            storage = r["storage"] or "Other"
            if storage_f and storage != storage_f:
                continue
            key = (mid, storage)
            cnt_map[key] = cnt_map.get(key, 0) + r["cnt"]
            model_meta[mid] = (r["model_brand"], r["model_name"])

        # Group by brand
        brands_order: list[str] = []
        brand_models: dict[str, list[int]] = {}
        for mid, (brand, _) in model_meta.items():
            if brand_f and brand != brand_f:
                continue
            if brand not in brand_models:
                brands_order.append(brand)
                brand_models[brand] = []
            brand_models[brand].append(mid)

        hdr_font = QFont(); hdr_font.setBold(True)

        for brand in brands_order:
            mids = brand_models[brand]

            # Brand header row
            row_idx = self._grid.rowCount()
            self._grid.insertRow(row_idx)
            hdr_item = QTableWidgetItem(f"  {brand}")
            hdr_item.setFont(hdr_font)
            hdr_item.setBackground(QColor("#2A2A3A"))
            hdr_item.setData(Qt.ItemDataRole.UserRole, None)  # no model_id
            self._grid.setItem(row_idx, 0, hdr_item)
            for c in range(1, self._grid.columnCount()):
                spacer = QTableWidgetItem("")
                spacer.setBackground(QColor("#2A2A3A"))
                spacer.setFlags(Qt.ItemFlag.NoItemFlags)
                self._grid.setItem(row_idx, c, spacer)

            for mid in mids:
                _, mname = model_meta[mid]
                row_idx = self._grid.rowCount()
                self._grid.insertRow(row_idx)

                name_item = QTableWidgetItem(f"    {mname}")
                name_item.setData(Qt.ItemDataRole.UserRole, mid)
                self._grid.setItem(row_idx, 0, name_item)

                total = 0
                for col_i, scol in enumerate(STORAGE_COLS):
                    cnt = cnt_map.get((mid, scol), 0)
                    total += cnt
                    cell = QTableWidgetItem(str(cnt) if cnt else "·")
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    cell.setBackground(QColor(_cell_color(cnt)))
                    cell.setForeground(QColor(_cell_fg(cnt)))
                    cell.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    self._grid.setItem(row_idx, col_i + 1, cell)

                tot_item = QTableWidgetItem(str(total))
                tot_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                tot_item.setFont(hdr_font)
                tot_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self._grid.setItem(row_idx, len(STORAGE_COLS) + 1, tot_item)

    # ── Detail panel ─────────────────────────────────────────────────────────

    def _on_grid_row_selected(self) -> None:
        rows = self._grid.selectedItems()
        if not rows:
            return
        row = self._grid.currentRow()
        model_id = self._grid.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if model_id is None:
            # Brand header row
            self._grid.clearSelection()
            return
        self._selected_model_id = model_id
        mname = (self._grid.item(row, 0).text() or "").strip()
        self._detail_title.setText(t("ph_units_for", model=mname))
        POOL.submit(
            "phones_detail",
            lambda mid=model_id: _phone_repo.get_by_model(mid, status=""),
            self._apply_detail,
        )

    _STATUS_KEYS = {
        "in_stock": "ph_status_in_stock",
        "sold":     "ph_status_sold",
        "reserved": "ph_status_reserved",
    }

    def _apply_detail(self, units: list[PhoneUnit]) -> None:
        self._detail_units = units
        tbl = self._detail_table
        tbl.setRowCount(0)

        for unit in units:
            r = tbl.rowCount()
            tbl.insertRow(r)

            def _item(txt: str) -> QTableWidgetItem:
                i = QTableWidgetItem(txt)
                i.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                return i

            tbl.setItem(r, 0, _item(unit.imei or "—"))
            tbl.setItem(r, 1, _item(unit.storage_label))
            tbl.setItem(r, 2, _item(unit.condition_label))
            tbl.setItem(r, 3, _item(unit.battery_label))
            tbl.setItem(r, 4, _item(f"€{unit.buy_price:.2f}" if unit.buy_price else "—"))
            tbl.setItem(r, 5, _item(f"€{unit.sell_price:.2f}" if unit.sell_price else "—"))
            status_key = self._STATUS_KEYS.get(unit.status)
            tbl.setItem(r, 6, _item(t(status_key) if status_key else unit.status.replace("_", " ").title()))
            tbl.setItem(r, 7, _item(unit.notes or ""))

            # Action buttons
            btn_w = QWidget()
            btn_lay = QHBoxLayout(btn_w)
            btn_lay.setContentsMargins(2, 1, 2, 1)
            btn_lay.setSpacing(4)

            edit_btn = QPushButton("✎")
            edit_btn.setObjectName("mgmt_edit")
            edit_btn.setFixedSize(30, 24)
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setToolTip(t("ph_tip_edit"))
            edit_btn.clicked.connect(lambda _, uid=unit.id: self._edit_phone(uid))
            btn_lay.addWidget(edit_btn)

            del_btn = QPushButton("🗑")
            del_btn.setObjectName("mgmt_del")
            del_btn.setFixedSize(30, 24)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setToolTip(t("ph_tip_delete"))
            del_btn.clicked.connect(lambda _, uid=unit.id: self._delete_phone(uid))
            btn_lay.addWidget(del_btn)

            tbl.setCellWidget(r, 8, btn_w)

        self._detail_container.setVisible(True)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _open_sold_history(self) -> None:
        from app.ui.dialogs.phone_sold_history_dialog import PhoneSoldHistoryDialog
        PhoneSoldHistoryDialog(parent=self).exec()

    def _open_labels_dialog(self) -> None:
        from app.ui.dialogs.phone_label_dialog import PhoneLabelDialog
        PhoneLabelDialog(parent=self, model_id=self._selected_model_id).exec()

    def _refresh_after(self) -> None:
        self.refresh()
        if self._selected_model_id:
            QTimer.singleShot(
                600,
                lambda: POOL.submit(
                    "phones_detail",
                    lambda mid=self._selected_model_id: _phone_repo.get_by_model(mid, status=""),
                    self._apply_detail,
                ),
            )

    def _add_phone(self) -> None:
        from app.ui.dialogs.phone_dialogs import AddEditPhoneDialog
        dlg = AddEditPhoneDialog(
            parent=self,
            preset_model_id=self._selected_model_id or 0,
        )
        if dlg.exec():
            new_id = dlg.saved_id()
            self._refresh_after()
            if new_id:
                holder = {"id": new_id}

                def _undo_add() -> None:
                    _phone_repo.delete(holder["id"])
                    self._refresh_after()

                def _redo_add() -> None:
                    p = _phone_repo.get_by_id(holder["id"])
                    # Already deleted by undo; re-create from last known snapshot
                    snap = holder.get("snapshot")
                    if snap:
                        holder["id"] = _phone_repo.add(*snap)
                    self._refresh_after()

                phone = _phone_repo.get_by_id(new_id)
                if phone:
                    holder["snapshot"] = (
                        phone.model_id, phone.imei, phone.storage, phone.condition,
                        phone.battery_pct, phone.buy_price, phone.sell_price, phone.notes,
                    )
                UNDO.push(Command(
                    label=t("ph_undo_add", name=phone.display_name if phone else "phone"),
                    undo_fn=_undo_add,
                    redo_fn=_redo_add,
                ))

    def _edit_phone(self, phone_id: int) -> None:
        from app.ui.dialogs.phone_dialogs import AddEditPhoneDialog
        phone = _phone_repo.get_by_id(phone_id)
        if not phone:
            return
        old_status = phone.status
        dlg = AddEditPhoneDialog(parent=self, phone=phone)
        if dlg.exec():
            new_phone = _phone_repo.get_by_id(phone_id)
            if new_phone:
                new_snapshot = (
                    new_phone.model_id, new_phone.imei, new_phone.storage, new_phone.condition,
                    new_phone.battery_pct, new_phone.buy_price, new_phone.sell_price, new_phone.notes,
                )
                old_fields = (
                    phone.model_id, phone.imei, phone.storage, phone.condition,
                    phone.battery_pct, phone.buy_price, phone.sell_price, phone.notes,
                )
                new_status = new_phone.status

                def _apply(fields, status) -> None:
                    _phone_repo.update(phone_id, *fields)
                    _phone_repo.update_status(phone_id, status)
                    self._refresh_after()

                UNDO.push(Command(
                    label=t("ph_undo_edit", name=new_phone.display_name),
                    undo_fn=lambda: _apply(old_fields, old_status),
                    redo_fn=lambda: _apply(new_snapshot, new_status),
                ))
            self._refresh_after()

    def _delete_phone(self, phone_id: int) -> None:
        phone = _phone_repo.get_by_id(phone_id)
        name = phone.display_name if phone else f"#{phone_id}"
        ans = QMessageBox.question(
            self, t("ph_delete_title"),
            t("ph_delete_confirm", name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        try:
            _phone_repo.delete(phone_id)
        except Exception as exc:
            QMessageBox.critical(self, t("ph_delete_error_title"), str(exc))
            return
        self._refresh_after()

        if phone:
            snapshot = (
                phone.model_id, phone.imei, phone.storage, phone.condition,
                phone.battery_pct, phone.buy_price, phone.sell_price, phone.notes,
            )
            holder = {"id": None}

            def _undo_delete() -> None:
                holder["id"] = _phone_repo.add(*snapshot)
                if phone.status != "in_stock":
                    _phone_repo.update_status(holder["id"], phone.status)
                self._refresh_after()

            def _redo_delete() -> None:
                if holder["id"] is not None:
                    _phone_repo.delete(holder["id"])
                self._refresh_after()

            UNDO.push(Command(
                label=t("ph_undo_delete", name=name),
                undo_fn=_undo_delete,
                redo_fn=_redo_delete,
            ))

    # ── Filters ───────────────────────────────────────────────────────────────

    def _on_filter_changed(self) -> None:
        self._filter_brand   = self._brand_combo.currentData() or ""
        self._filter_storage = self._storage_combo.currentData() or ""
        self._filter_cond    = self._cond_combo.currentData() or ""
        self._apply_grid(self._grid_data)

    def _on_search_changed(self, text: str) -> None:
        # Search triggers a fresh DB query
        search = text.strip()
        POOL.submit_debounced(
            "phones_search",
            lambda: _phone_repo.get_all(search=search),
            self._apply_search_results,
            delay_ms=250,
        )

    def _apply_search_results(self, units: list[PhoneUnit]) -> None:
        if not self._search_edit.text().strip():
            return  # ignore stale results after clear
        # Show results in detail panel
        self._detail_title.setText(t("ph_search_results"))
        self._apply_detail(units)
