"""app/ui/pages/audit_page.py — Inventory audit UI with list and detail views."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QLineEdit,
)

from app.core.i18n import t
from app.core.theme import THEME
from app.models.audit import AuditLine, InventoryAudit
from app.services.audit_service import AuditService
from app.ui.components.dashboard_widget import SummaryCard
from app.ui.components.empty_state import EmptyState
from app.ui.workers.worker_pool import POOL
from app.ui.dialogs.dialog_base import DialogBase
from app.ui.components.responsive_table import make_table_responsive


# ── Audit List View ──────────────────────────────────────────────────────────


class NewAuditDialog(DialogBase):
    """Dialog to create a new audit."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize dialog."""
        super().__init__(parent)
        self.setWindowTitle(t("aud_dlg_title"))
        self.setMinimumWidth(400)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Name field
        label_name = QLabel(t("aud_dlg_name"))
        label_name.setStyleSheet(f"color: {THEME.tokens.t1}; font-weight: bold;")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Monthly Count - April 2026")
        layout.addWidget(label_name)
        layout.addWidget(self.name_input)

        # Notes field
        label_notes = QLabel(t("aud_dlg_notes"))
        label_notes.setStyleSheet(f"color: {THEME.tokens.t1}; font-weight: bold;")
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        self.notes_input.setPlaceholderText("Location, reason, etc.")
        layout.addWidget(label_notes)
        layout.addWidget(self.notes_input)

        # Buttons
        layout.addSpacing(16)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton(t("btn_cancel"))
        self.btn_cancel.setObjectName("btn_ghost")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_ok = QPushButton(t("btn_ok"))
        self.btn_ok.setObjectName("btn_primary")
        self.btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ok.clicked.connect(self._validate_and_accept)
        btn_layout.addWidget(self.btn_ok)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _validate_and_accept(self) -> None:
        """Validate name and accept."""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, t("error"), t("aud_warn_name"))
            return
        self.result = {
            "name": name,
            "notes": self.notes_input.toPlainText().strip(),
        }
        self.accept()


class AuditListView(QWidget):
    """Main audit list view with KPIs and table."""

    audit_opened = pyqtSignal(int)  # audit_id

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize list view."""
        super().__init__(parent)
        self._svc = AuditService()
        self._setup_ui()
        self._load_data()

    def _setup_ui(self) -> None:
        """Build UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(16, 16, 16, 0)

        # Saved as ``self._title_lbl`` / ``self._subtitle_lbl`` so the
        # tab-level ``apply_theme`` (added below) can re-style them on
        # theme switch — they were locals and lost their colours after
        # toggle to a different theme.
        self._title_lbl = QLabel(t("aud_title"))
        self._subtitle_lbl = QLabel(t("aud_subtitle"))

        header_left = QVBoxLayout()
        header_left.setContentsMargins(0, 0, 0, 0)
        header_left.setSpacing(4)
        header_left.addWidget(self._title_lbl)
        header_left.addWidget(self._subtitle_lbl)
        # Initial style application — also called by ``apply_theme`` on
        # every theme switch.
        self._apply_header_styles()

        header_layout.addLayout(header_left)
        header_layout.addStretch()

        self.btn_new = QPushButton(t("aud_btn_new"))
        self.btn_new.setObjectName("btn_primary")
        self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.clicked.connect(self._on_new_audit)
        header_layout.addWidget(self.btn_new)

        layout.addLayout(header_layout)

        # KPI cards
        kpi_layout = QHBoxLayout()
        kpi_layout.setContentsMargins(16, 0, 16, 0)
        kpi_layout.setSpacing(12)

        self.kpi_total = SummaryCard("📋", THEME.tokens.blue)
        self.kpi_total.set_value(0, t("aud_kpi_total"))
        self.kpi_progress = SummaryCard("⏳", THEME.tokens.orange)
        self.kpi_progress.set_value(0, t("aud_kpi_progress"))
        self.kpi_completed = SummaryCard("✓", THEME.tokens.green)
        self.kpi_completed.set_value(0, t("aud_kpi_completed"))
        self.kpi_discrepancies = SummaryCard("⚠", THEME.tokens.red)
        self.kpi_discrepancies.set_value(0, t("aud_kpi_discrepancies"))

        kpi_layout.addWidget(self.kpi_total)
        kpi_layout.addWidget(self.kpi_progress)
        kpi_layout.addWidget(self.kpi_completed)
        kpi_layout.addWidget(self.kpi_discrepancies)
        kpi_layout.addStretch()

        layout.addLayout(kpi_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            t("aud_col_name"),
            t("aud_col_status"),
            t("aud_col_started"),
            t("aud_col_completed"),
            t("aud_col_lines"),
            t("aud_col_counted"),
            t("aud_col_discrepancies"),
            t("aud_col_actions"),
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(7, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(7, 100)
        self.table.setAlternatingRowColors(True)
        # Cols: 0=Name  1=Status  2=Started  3=Completed  4=Lines  5=Counted  6=Discrepancies  7=Actions
        make_table_responsive(self.table, [
            (3, 1050),  # Completed      — hide when viewport < 1050 px
            (5,  900),  # Counted        — hide when viewport <  900 px
            (4,  780),  # Lines          — hide when viewport <  780 px
            (2,  640),  # Started        — hide when viewport <  640 px
        ])
        layout.addWidget(self.table, 1)

        # Empty state
        self.empty_state = EmptyState(
            title=t("aud_empty_title"),
            subtitle=t("aud_empty_sub"),
        )
        layout.addWidget(self.empty_state)
        self.empty_state.hide()

        self.setLayout(layout)

    def _apply_header_styles(self) -> None:
        """Apply the inline title / subtitle styles from current tokens.

        Centralised so the initial paint and the theme-toggle repaint
        share a single source of truth — adding new styled labels means
        editing one method instead of two.
        """
        tk = THEME.tokens
        self._title_lbl.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {tk.t1};"
        )
        self._subtitle_lbl.setStyleSheet(
            f"font-size: 12px; color: {tk.t2};"
        )

    def apply_theme(self) -> None:
        """Refresh inline-styled labels on theme switch. ``SummaryCard``
        children handle their own refresh via their own ``apply_theme``,
        discovered by ``MainWindow._refresh_theme``'s widget-tree walk —
        this method only needs to cover the page-level header labels."""
        try:
            self._apply_header_styles()
        except Exception:
            pass

    def _load_data(self) -> None:
        """Fetch audits + summary off the UI thread, apply on return."""
        def _fetch():
            return {
                "audits":  self._svc.get_all_audits(),
                "summary": self._svc.get_summary(),
            }
        POOL.submit("audit_load", _fetch, self._apply_audits)

    def _apply_audits(self, payload: dict) -> None:
        """Main-thread render of audit KPIs + table with pre-fetched data."""
        try:
            audits = payload.get("audits", [])
            summary = payload.get("summary", {})

            # Update KPIs
            self.kpi_total.set_value(summary["total_audits"], t("aud_kpi_total"))
            self.kpi_progress.set_value(summary["in_progress"], t("aud_kpi_progress"))
            self.kpi_completed.set_value(summary["completed"], t("aud_kpi_completed"))
            self.kpi_discrepancies.set_value(summary["total_discrepancies"], t("aud_kpi_discrepancies"))

            # Populate table
            self.table.setRowCount(len(audits))
            for row, audit in enumerate(audits):
                self._populate_row(row, audit)

            # Show/hide empty state
            if not audits:
                self.table.hide()
                self.empty_state.show()
            else:
                self.table.show()
                self.empty_state.hide()

        except Exception as e:
            print(f"Failed to render audits: {e}")

    def _populate_row(self, row: int, audit: InventoryAudit) -> None:
        """Populate table row with audit data."""
        # Name
        item_name = QTableWidgetItem(audit.name)
        self.table.setItem(row, 0, item_name)

        # Status badge
        status_text = {
            "IN_PROGRESS": t("aud_status_in_progress"),
            "COMPLETED": t("aud_status_completed"),
            "CANCELLED": t("aud_status_cancelled"),
        }.get(audit.status, audit.status)

        status_color = {
            "IN_PROGRESS": THEME.tokens.blue,
            "COMPLETED": THEME.tokens.green,
            "CANCELLED": THEME.tokens.orange,
        }.get(audit.status, THEME.tokens.t2)

        item_status = QTableWidgetItem(status_text)
        item_status.setForeground(QColor(status_color))
        self.table.setItem(row, 1, item_status)

        # Started
        started_date = datetime.fromisoformat(audit.started_at).strftime("%Y-%m-%d %H:%M")
        item_started = QTableWidgetItem(started_date)
        self.table.setItem(row, 2, item_started)

        # Completed
        if audit.completed_at:
            completed_date = datetime.fromisoformat(audit.completed_at).strftime("%Y-%m-%d %H:%M")
        else:
            completed_date = "—"
        item_completed = QTableWidgetItem(completed_date)
        self.table.setItem(row, 3, item_completed)

        # Lines
        item_lines = QTableWidgetItem(str(audit.total_lines))
        self.table.setItem(row, 4, item_lines)

        # Counted
        item_counted = QTableWidgetItem(f"{audit.counted_lines}/{audit.total_lines}")
        self.table.setItem(row, 5, item_counted)

        # Discrepancies
        item_disc = QTableWidgetItem(str(audit.discrepancies))
        self.table.setItem(row, 6, item_disc)

        # Actions button — btn_secondary_sm for good visibility on dark table rows
        action_w = QWidget()
        action_lay = QHBoxLayout(action_w)
        action_lay.setContentsMargins(6, 4, 6, 10)
        action_lay.setSpacing(0)
        btn_open = QPushButton(t("btn_open"))
        btn_open.setObjectName("btn_secondary_sm")
        btn_open.setFixedHeight(26)
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.clicked.connect(lambda checked, aid=audit.id: self.audit_opened.emit(aid))
        action_lay.addWidget(btn_open)
        self.table.setCellWidget(row, 7, action_w)
        self.table.setRowHeight(row, 48)

    def _on_new_audit(self) -> None:
        """Show new audit dialog."""
        dlg = NewAuditDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name = dlg.result["name"]
            notes = dlg.result["notes"]
            try:
                audit_id = self._svc.create_audit(name, notes)
                self._load_data()
                # Open the new audit
                self.audit_opened.emit(audit_id)
            except Exception as e:
                QMessageBox.critical(self, t("error"), str(e))


# ── Audit Detail View ────────────────────────────────────────────────────────


class AuditDetailView(QWidget):
    """Audit detail view with line items and actions."""

    back_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize detail view."""
        super().__init__(parent)
        self._svc = AuditService()
        self._audit: Optional[InventoryAudit] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(16, 16, 16, 0)

        self.btn_back = QPushButton(f"← {t('aud_detail_back')}")
        self.btn_back.setObjectName("btn_secondary")
        self.btn_back.setFixedHeight(30)
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.clicked.connect(self.back_clicked.emit)
        header_layout.addWidget(self.btn_back)

        self.lbl_title = QLabel("")
        self.lbl_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {THEME.tokens.t1};")
        header_layout.addWidget(self.lbl_title)

        self.lbl_status_badge = QLabel("")
        header_layout.addWidget(self.lbl_status_badge)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # KPI cards
        kpi_layout = QHBoxLayout()
        kpi_layout.setContentsMargins(16, 0, 16, 0)
        kpi_layout.setSpacing(12)

        self.kpi_total_items = SummaryCard("📦", THEME.tokens.blue)
        self.kpi_total_items.set_value(0, t("aud_detail_total"))
        self.kpi_counted = SummaryCard("✓", THEME.tokens.green)
        self.kpi_counted.set_value(0, t("aud_detail_counted"))
        self.kpi_remaining = SummaryCard("○", THEME.tokens.orange)
        self.kpi_remaining.set_value(0, t("aud_detail_remaining"))
        self.kpi_diff = SummaryCard("⚠", THEME.tokens.red)
        self.kpi_diff.set_value(0, t("aud_detail_diff"))

        kpi_layout.addWidget(self.kpi_total_items)
        kpi_layout.addWidget(self.kpi_counted)
        kpi_layout.addWidget(self.kpi_remaining)
        kpi_layout.addWidget(self.kpi_diff)
        kpi_layout.addStretch()

        layout.addLayout(kpi_layout)

        # Search/filter
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(16, 0, 16, 0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(t("aud_search_ph"))
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Lines table
        self.lines_table = QTableWidget()
        self.lines_table.setColumnCount(6)
        self.lines_table.setHorizontalHeaderLabels([
            t("aud_line_item"),
            t("aud_line_barcode"),
            t("aud_line_system"),
            t("aud_line_counted"),
            t("aud_line_diff"),
            t("aud_line_note"),
        ])
        self.lines_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.lines_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.lines_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.lines_table.setAlternatingRowColors(True)
        # Cols: 0=Item  1=Barcode  2=System  3=Counted  4=Diff  5=Note
        make_table_responsive(self.lines_table, [
            (1, 800),   # Barcode — hide when viewport < 800 px
            (5, 680),   # Note    — hide when viewport < 680 px
        ])
        layout.addWidget(self.lines_table, 1)

        # Toolbar
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(16, 0, 16, 16)
        toolbar_layout.setSpacing(12)

        toolbar_layout.addStretch()

        self.btn_cancel_audit = QPushButton(t("aud_btn_cancel_audit"))
        self.btn_cancel_audit.setObjectName("alert_critical")
        self.btn_cancel_audit.setMinimumHeight(40)
        self.btn_cancel_audit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel_audit.clicked.connect(self._on_cancel_audit)
        toolbar_layout.addWidget(self.btn_cancel_audit)

        self.btn_complete = QPushButton(t("aud_btn_complete"))
        self.btn_complete.setObjectName("btn_primary")
        self.btn_complete.setMinimumHeight(40)
        self.btn_complete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_complete.clicked.connect(self._on_complete)
        toolbar_layout.addWidget(self.btn_complete)

        self.btn_apply = QPushButton(t("aud_btn_apply"))
        self.btn_apply.setObjectName("alert_ok")
        self.btn_apply.setMinimumHeight(40)
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply.clicked.connect(self._on_apply)
        toolbar_layout.addWidget(self.btn_apply)

        layout.addLayout(toolbar_layout)

        self.setLayout(layout)

    def load_audit(self, audit_id: int) -> None:
        """Load and display an audit."""
        try:
            self._audit = self._svc.get_audit(audit_id)
            if not self._audit:
                return

            # Update header
            self.lbl_title.setText(self._audit.name)
            status_text = {
                "IN_PROGRESS": t("aud_status_in_progress"),
                "COMPLETED": t("aud_status_completed"),
                "CANCELLED": t("aud_status_cancelled"),
            }.get(self._audit.status, self._audit.status)

            status_color = {
                "IN_PROGRESS": THEME.tokens.blue,
                "COMPLETED": THEME.tokens.green,
                "CANCELLED": THEME.tokens.orange,
            }.get(self._audit.status, THEME.tokens.t2)

            self.lbl_status_badge.setText(status_text)
            self.lbl_status_badge.setStyleSheet(f"color: {status_color}; font-weight: bold;")

            # Update KPIs
            remaining = self._audit.total_lines - self._audit.counted_lines
            self.kpi_total_items.set_value(self._audit.total_lines, t("aud_detail_total"))
            self.kpi_counted.set_value(self._audit.counted_lines, t("aud_detail_counted"))
            self.kpi_remaining.set_value(remaining, t("aud_detail_remaining"))
            self.kpi_diff.set_value(self._audit.discrepancies, t("aud_detail_diff"))

            # Update button visibility
            self.btn_complete.setVisible(self._audit.status == "IN_PROGRESS")
            self.btn_apply.setVisible(self._audit.status == "COMPLETED")
            self.btn_cancel_audit.setVisible(self._audit.status in ("IN_PROGRESS", "COMPLETED"))

            # Load lines
            lines = self._svc.get_audit_lines(audit_id)
            self._populate_lines(lines)

        except Exception as e:
            print(f"Failed to load audit: {e}")

    def _populate_lines(self, lines: list[AuditLine]) -> None:
        """Populate lines table."""
        self.lines_table.setRowCount(min(len(lines), 200))  # Cap at 200

        for row, line in enumerate(lines[:200]):
            # Item name
            item_name = QTableWidgetItem(line.item_name)
            self.lines_table.setItem(row, 0, item_name)

            # Barcode
            item_barcode = QTableWidgetItem(line.barcode or "—")
            self.lines_table.setItem(row, 1, item_barcode)

            # System qty
            item_system = QTableWidgetItem(str(line.system_qty))
            self.lines_table.setItem(row, 2, item_system)

            # Counted qty (editable spinbox)
            spinbox = QSpinBox()
            spinbox.setMinimum(0)
            spinbox.setMaximum(9999)
            if line.counted_qty is not None:
                spinbox.setValue(line.counted_qty)
            spinbox.valueChanged.connect(
                lambda val, lid=line.id: self._on_qty_changed(lid, val)
            )
            self.lines_table.setCellWidget(row, 3, spinbox)

            # Difference
            if line.difference is not None:
                diff_text = str(line.difference)
                item_diff = QTableWidgetItem(diff_text)
                if line.difference == 0:
                    item_diff.setForeground(QColor(THEME.tokens.green))
                elif line.difference < 0:
                    item_diff.setForeground(QColor(THEME.tokens.red))
                else:
                    item_diff.setForeground(QColor(THEME.tokens.orange))
            else:
                item_diff = QTableWidgetItem("—")
            self.lines_table.setItem(row, 4, item_diff)

            # Note
            item_note = QTableWidgetItem(line.note)
            self.lines_table.setItem(row, 5, item_note)

            # Style uncounted rows
            if line.counted_qty is None:
                for col in range(6):
                    cell = self.lines_table.item(row, col)
                    if cell:
                        cell.setForeground(QColor(THEME.tokens.t3))

    def _on_qty_changed(self, line_id: int, value: int) -> None:
        """Handle quantity change with debounce — avoids full reload on every spin."""
        try:
            self._svc.record_count(line_id, value, "")
        except Exception as e:
            print(f"Failed to update quantity: {e}")
            return

        # Debounced lightweight reload (only refresh after 500ms of no changes)
        if not hasattr(self, "_debounce_timer"):
            self._debounce_timer = QTimer(self)
            self._debounce_timer.setSingleShot(True)
            self._debounce_timer.timeout.connect(self._deferred_refresh)
        self._debounce_timer.start(500)

    def _deferred_refresh(self) -> None:
        """Reload audit data after debounce delay."""
        if self._audit:
            self.load_audit(self._audit.id)

    def _on_search(self, text: str) -> None:
        """Filter lines by search text."""
        for row in range(self.lines_table.rowCount()):
            item_cell = self.lines_table.item(row, 0)
            if item_cell:
                item_cell.setHidden(text.lower() not in item_cell.text().lower())

    def _on_complete(self) -> None:
        """Complete the audit."""
        if not self._audit:
            return

        reply = QMessageBox.question(
            self, t("confirm"), t("aud_confirm_complete"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                summary = self._svc.complete_audit(self._audit.id)
                QMessageBox.information(
                    self, t("success"),
                    f"Audit completed.\nDiscrepancies: {summary['discrepancies']}"
                )
                self.load_audit(self._audit.id)
            except Exception as e:
                QMessageBox.critical(self, t("error"), str(e))

    def _on_apply(self) -> None:
        """Apply adjustments."""
        if not self._audit:
            return

        reply = QMessageBox.question(
            self, t("confirm"), t("aud_confirm_apply"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                count = self._svc.apply_adjustments(self._audit.id)
                QMessageBox.information(
                    self, t("success"),
                    f"Applied {count} stock adjustments"
                )
            except Exception as e:
                QMessageBox.critical(self, t("error"), str(e))

    def _on_cancel_audit(self) -> None:
        """Cancel the audit."""
        if not self._audit:
            return

        reply = QMessageBox.question(
            self, t("confirm"), t("aud_confirm_cancel"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._svc.cancel_audit(self._audit.id)
                QMessageBox.information(self, t("success"), "Audit cancelled")
                self.back_clicked.emit()
            except Exception as e:
                QMessageBox.critical(self, t("error"), str(e))


# ── Main Audit Page ─────────────────────────────────────────────────────────


class AuditPage(QWidget):
    """Main audit page with stacked views."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize audit page."""
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build UI with stacked widget."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.stacked = QStackedWidget()

        self.list_view = AuditListView()
        self.list_view.audit_opened.connect(self._on_audit_opened)
        self.stacked.addWidget(self.list_view)

        self.detail_view = AuditDetailView()
        self.detail_view.back_clicked.connect(self._on_back)
        self.stacked.addWidget(self.detail_view)

        self.stacked.setCurrentIndex(0)  # Start with list

        layout.addWidget(self.stacked)
        self.setLayout(layout)

    def _on_audit_opened(self, audit_id: int) -> None:
        """Switch to detail view."""
        self.detail_view.load_audit(audit_id)
        self.stacked.setCurrentIndex(1)

    def _on_back(self) -> None:
        """Return to list view and refresh."""
        self.list_view._load_data()
        self.stacked.setCurrentIndex(0)

    def refresh(self) -> None:
        """Refresh the current view."""
        if self.stacked.currentIndex() == 0:
            self.list_view._load_data()
        elif self.detail_view._audit:
            self.detail_view.load_audit(self.detail_view._audit.id)

    def retranslate(self) -> None:
        """Retranslate UI strings (called on language change)."""
        self.refresh()
