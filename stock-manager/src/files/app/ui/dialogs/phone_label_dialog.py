"""app/ui/dialogs/phone_label_dialog.py — Export phone unit barcode labels."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QCheckBox, QFileDialog, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QFrame,
)
from PyQt6.QtCore import Qt

from app.models.phone_unit import PhoneUnit
from app.repositories.phone_repo import PhoneRepository

_phone_repo = PhoneRepository()


class PhoneLabelDialog(QDialog):
    """Select phone units and export barcode labels for YunPrint."""

    def __init__(
        self,
        parent: QWidget | None = None,
        model_id: int | None = None,
    ) -> None:
        super().__init__(parent)
        self._model_id = model_id
        self.setWindowTitle("Export Phone Labels — YunPrint")
        self.setMinimumSize(620, 480)
        self.setModal(True)
        self._phones: list[PhoneUnit] = []
        self._build()
        self._load()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        # Filter row
        filter_row = QHBoxLayout()

        filter_row.addWidget(QLabel("Status:"))
        self._status_combo = QComboBox()
        self._status_combo.addItem("In Stock only", "in_stock")
        self._status_combo.addItem("All statuses", "")
        self._status_combo.currentIndexChanged.connect(self._load)
        filter_row.addWidget(self._status_combo)

        filter_row.addWidget(QLabel("Model:"))
        self._model_combo = QComboBox()
        self._model_combo.addItem("All Models", 0)
        filter_row.addWidget(self._model_combo)
        self._model_combo.currentIndexChanged.connect(self._load)

        filter_row.addStretch()
        root.addLayout(filter_row)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["", "Barcode", "Model", "Storage", "Condition"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._table.setColumnWidth(0, 32)
        self._table.setColumnWidth(3, 80)
        self._table.setColumnWidth(4, 100)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        root.addWidget(self._table)

        # Selection helpers
        sel_row = QHBoxLayout()
        sel_all = QPushButton("Select All")
        sel_all.clicked.connect(self._select_all)
        sel_none = QPushButton("Select None")
        sel_none.clicked.connect(self._select_none)
        self._count_lbl = QLabel("0 selected")
        sel_row.addWidget(sel_all)
        sel_row.addWidget(sel_none)
        sel_row.addStretch()
        sel_row.addWidget(self._count_lbl)
        root.addLayout(sel_row)

        # Separator
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        # Info label
        info = QLabel(
            "YunPrint columns: barcode · model · storage · condition · "
            "battery · sell_price · imei · label"
        )
        info.setStyleSheet("color: #888; font-size: 9pt;")
        info.setWordWrap(True)
        root.addWidget(info)

        # Buttons
        btn_row = QHBoxLayout()
        self._export_btn = QPushButton("🏷  Export for YunPrint (.txt)")
        self._export_btn.setObjectName("btn_primary")
        self._export_btn.clicked.connect(self._export)
        cancel_btn = QPushButton("Close")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._export_btn)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        root.addLayout(btn_row)

    # ── Data ──────────────────────────────────────────────────────────────────

    def _load(self) -> None:
        from app.services.barcode_gen_service import phone_barcode_text
        status = self._status_combo.currentData() or ""
        mid    = self._model_combo.currentData() or 0

        # Populate model combo on first load
        if self._model_combo.count() == 1:
            try:
                from app.core.database import get_connection
                with get_connection() as conn:
                    rows = conn.execute(
                        "SELECT id, brand, name FROM phone_models ORDER BY brand, name"
                    ).fetchall()
                for r in rows:
                    self._model_combo.addItem(
                        f"{r['brand']} {r['name']}", r["id"]
                    )
                if self._model_id:
                    for i in range(self._model_combo.count()):
                        if self._model_combo.itemData(i) == self._model_id:
                            self._model_combo.setCurrentIndex(i)
                            mid = self._model_id
                            break
            except Exception:
                pass

        self._phones = _phone_repo.get_by_model(mid, status=status) if mid else \
                       _phone_repo.get_all(status=status)

        self._table.setRowCount(0)
        for p in self._phones:
            r = self._table.rowCount()
            self._table.insertRow(r)

            chk = QTableWidgetItem()
            chk.setCheckState(Qt.CheckState.Checked)
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            self._table.setItem(r, 0, chk)

            bc_item = QTableWidgetItem(phone_barcode_text(p))
            bc_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._table.setItem(r, 1, bc_item)

            m_item = QTableWidgetItem(f"{p.model_brand} {p.model_name}".strip())
            m_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._table.setItem(r, 2, m_item)

            s_item = QTableWidgetItem(p.storage_label)
            s_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._table.setItem(r, 3, s_item)

            c_item = QTableWidgetItem(p.condition_label)
            c_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._table.setItem(r, 4, c_item)

        self._update_count()
        self._table.itemChanged.connect(self._update_count)

    def _select_all(self)  -> None:
        for r in range(self._table.rowCount()):
            self._table.item(r, 0).setCheckState(Qt.CheckState.Checked)

    def _select_none(self) -> None:
        for r in range(self._table.rowCount()):
            self._table.item(r, 0).setCheckState(Qt.CheckState.Unchecked)

    def _update_count(self) -> None:
        n = sum(
            1 for r in range(self._table.rowCount())
            if self._table.item(r, 0) and
               self._table.item(r, 0).checkState() == Qt.CheckState.Checked
        )
        self._count_lbl.setText(f"{n} selected")

    def _selected_phones(self) -> list[PhoneUnit]:
        result = []
        for r in range(self._table.rowCount()):
            if (self._table.item(r, 0) and
                    self._table.item(r, 0).checkState() == Qt.CheckState.Checked
                    and r < len(self._phones)):
                result.append(self._phones[r])
        return result

    # ── Export ────────────────────────────────────────────────────────────────

    def _export(self) -> None:
        phones = self._selected_phones()
        if not phones:
            QMessageBox.information(self, "Nothing selected",
                                    "Select at least one phone unit to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save YunPrint file",
            "phone_labels.txt",
            "YunPrint CSV (*.txt);;All Files (*)",
        )
        if not path:
            return

        try:
            from app.services.barcode_gen_service import BarcodeGenService
            svc  = BarcodeGenService()
            out  = svc.export_phones_for_yunprint(phones, path, validate=True)
            QMessageBox.information(
                self, "Export complete",
                f"Exported {len(phones)} label(s) to:\n{out}\n\n"
                "Open YunPrint → Database → select this file → Print.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Export error", str(exc))
