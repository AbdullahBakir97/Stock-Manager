"""app/ui/dialogs/phone_dialogs.py — Add / Edit phone unit dialogs."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QPushButton, QDialogButtonBox, QMessageBox,
    QTextEdit,
)
from PyQt6.QtCore import Qt

from app.core.i18n import t
from app.models.phone_unit import PhoneUnit
from app.repositories.phone_repo import PhoneRepository

_phone_repo = PhoneRepository()

STORAGE_OPTIONS = ["", "64GB", "128GB", "256GB", "512GB", "1TB", "Other"]


def _condition_options() -> list[tuple[str, str]]:
    return [
        ("new",         t("ph_cond_new")),
        ("used",        t("ph_cond_used")),
        ("refurbished", t("ph_cond_refurbished")),
    ]


def _status_options() -> list[tuple[str, str]]:
    return [
        ("in_stock",  t("ph_status_in_stock")),
        ("sold",      t("ph_status_sold")),
        ("reserved",  t("ph_status_reserved")),
    ]


class AddEditPhoneDialog(QDialog):
    """Dialog for adding or editing a single phone unit."""

    def __init__(
        self,
        parent: QWidget | None = None,
        phone: Optional[PhoneUnit] = None,
        preset_model_id: int = 0,
    ) -> None:
        super().__init__(parent)
        self._phone = phone
        self._preset_model_id = preset_model_id
        self._saved_id: Optional[int] = None

        self.setWindowTitle(t("phd_title_edit") if phone else t("phd_title_add"))
        self.setMinimumWidth(460)
        self.setModal(True)

        self._build()
        self._populate()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)

        # Model
        self._model_combo = QComboBox()
        self._model_combo.setMinimumWidth(260)
        form.addRow(t("phd_lbl_model"), self._model_combo)

        # IMEI
        self._imei_edit = QLineEdit()
        self._imei_edit.setPlaceholderText(t("phd_imei_placeholder"))
        self._imei_edit.setMaxLength(20)
        form.addRow(t("phd_lbl_imei"), self._imei_edit)

        # Storage
        self._storage_combo = QComboBox()
        for s in STORAGE_OPTIONS:
            self._storage_combo.addItem(s or "—", s)
        form.addRow(t("phd_lbl_storage"), self._storage_combo)

        # Condition
        self._condition_combo = QComboBox()
        for val, label in _condition_options():
            self._condition_combo.addItem(label, val)
        form.addRow(t("phd_lbl_condition"), self._condition_combo)

        # Battery
        batt_row = QHBoxLayout()
        self._batt_spin = QSpinBox()
        self._batt_spin.setRange(0, 100)
        self._batt_spin.setSuffix("%")
        self._batt_spin.setFixedWidth(80)
        self._batt_unknown = QCheckBox(t("phd_unknown"))
        self._batt_unknown.toggled.connect(lambda v: self._batt_spin.setDisabled(v))
        batt_row.addWidget(self._batt_spin)
        batt_row.addWidget(self._batt_unknown)
        batt_row.addStretch()
        form.addRow(t("phd_lbl_battery"), batt_row)

        # Prices
        self._buy_spin = QDoubleSpinBox()
        self._buy_spin.setRange(0, 999_999)
        self._buy_spin.setDecimals(2)
        self._buy_spin.setPrefix("€")
        self._buy_spin.setFixedWidth(120)
        form.addRow(t("phd_lbl_buy"), self._buy_spin)

        self._sell_spin = QDoubleSpinBox()
        self._sell_spin.setRange(0, 999_999)
        self._sell_spin.setDecimals(2)
        self._sell_spin.setPrefix("€")
        self._sell_spin.setFixedWidth(120)
        form.addRow(t("phd_lbl_sell"), self._sell_spin)

        # Status (only shown for editing)
        self._status_combo = QComboBox()
        for val, label in _status_options():
            self._status_combo.addItem(label, val)
        if self._phone is not None:
            form.addRow(t("phd_lbl_status"), self._status_combo)

        # Notes
        self._notes_edit = QTextEdit()
        self._notes_edit.setFixedHeight(60)
        self._notes_edit.setPlaceholderText(t("phd_notes_placeholder"))
        form.addRow(t("phd_lbl_notes"), self._notes_edit)

        root.addLayout(form)

        # Buttons
        self._btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        self._btn_box.accepted.connect(self._save)
        self._btn_box.rejected.connect(self.reject)
        root.addWidget(self._btn_box)

    def _populate(self) -> None:
        # Load phone models for combo
        try:
            models = _phone_repo.get_all_models_with_phones()
        except Exception:
            models = []

        # We also need ALL models (even without phones), fetched directly
        from app.core.database import get_connection
        try:
            with get_connection() as conn:
                rows = conn.execute(
                    "SELECT id, name, brand FROM phone_models ORDER BY brand, name"
                ).fetchall()
            all_models = [dict(r) for r in rows]
        except Exception:
            all_models = models

        self._model_ids: list[int] = []
        current_brand = None
        for m in all_models:
            brand = m.get("model_brand") or m.get("brand", "")
            name  = m.get("model_name")  or m.get("name", "")
            mid   = m["id"]
            if brand != current_brand:
                self._model_combo.addItem(f"── {brand} ──", -1)
                current_brand = brand
            self._model_combo.addItem(f"  {name}", mid)
            self._model_ids.append(mid)

        if self._phone:
            p = self._phone
            # Set model
            for i in range(self._model_combo.count()):
                if self._model_combo.itemData(i) == p.model_id:
                    self._model_combo.setCurrentIndex(i)
                    break
            self._imei_edit.setText(p.imei or "")
            # Storage
            idx = self._storage_combo.findData(p.storage)
            if idx >= 0:
                self._storage_combo.setCurrentIndex(idx)
            # Condition
            for i, (val, _) in enumerate(_condition_options()):
                if val == p.condition:
                    self._condition_combo.setCurrentIndex(i)
                    break
            # Battery
            if p.battery_pct is None:
                self._batt_unknown.setChecked(True)
            else:
                self._batt_spin.setValue(p.battery_pct)
            self._buy_spin.setValue(p.buy_price or 0.0)
            self._sell_spin.setValue(p.sell_price or 0.0)
            # Status
            for i, (val, _) in enumerate(_status_options()):
                if val == p.status:
                    self._status_combo.setCurrentIndex(i)
                    break
            self._notes_edit.setPlainText(p.notes or "")
        else:
            # Preset model
            if self._preset_model_id:
                for i in range(self._model_combo.count()):
                    if self._model_combo.itemData(i) == self._preset_model_id:
                        self._model_combo.setCurrentIndex(i)
                        break
            # Default battery unknown for new phones
            self._batt_unknown.setChecked(False)
            self._batt_spin.setValue(100)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _save(self) -> None:
        model_id = self._model_combo.currentData()
        if not model_id or model_id < 0:
            QMessageBox.warning(self, t("phd_validation_title"), t("phd_validation_model"))
            return

        imei      = self._imei_edit.text().strip()
        storage   = self._storage_combo.currentData() or ""
        condition = self._condition_combo.currentData()
        battery   = None if self._batt_unknown.isChecked() else self._batt_spin.value()
        buy_price = self._buy_spin.value() or None
        sell_price= self._sell_spin.value() or None
        status    = self._status_combo.currentData() if self._phone else "in_stock"
        notes     = self._notes_edit.toPlainText().strip()

        # IMEI uniqueness check
        if imei:
            exclude = self._phone.id if self._phone else 0
            if _phone_repo.imei_exists(imei, exclude_id=exclude):
                ans = QMessageBox.question(
                    self, t("phd_dup_imei_title"),
                    t("phd_dup_imei_body", imei=imei),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if ans != QMessageBox.StandardButton.Yes:
                    return

        try:
            if self._phone:
                _phone_repo.update(
                    self._phone.id, model_id, imei, storage, condition,
                    battery, buy_price, sell_price, notes,
                )
                _phone_repo.update_status(self._phone.id, status)
                self._saved_id = self._phone.id
            else:
                self._saved_id = _phone_repo.add(
                    model_id, imei, storage, condition,
                    battery, buy_price, sell_price, notes,
                )
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, t("phd_save_error_title"), str(exc))

    def saved_id(self) -> Optional[int]:
        return self._saved_id
