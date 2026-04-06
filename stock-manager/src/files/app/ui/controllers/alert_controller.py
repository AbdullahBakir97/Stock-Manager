"""
app/ui/controllers/alert_controller.py — Stock alert badge + notification panel.

Owns:
  - Querying AlertService for low/expiring/expired counts
  - Updating the sidebar alert button and header badge
  - Opening the NotificationPanel popup
  - Opening the LowStockDialog

Usage (from MainWindow):
    self._alert_ctrl = AlertController(
        header=self._header,
        sidebar=self._sidebar,
        update_ctrl=self._upd_ctrl,   # so it can read pending_update count
        parent=self,
    )
    self._header.alerts_clicked.connect(self._alert_ctrl.toggle_panel)
    # after any stock change: self._alert_ctrl.refresh()
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget

from app.core.i18n import t
from app.services.alert_service import AlertService
from app.ui.components.notification_panel import NotificationPanel, StockAlertCounts
from app.ui.dialogs.product_dialogs import LowStockDialog
from app.repositories.item_repo import ItemRepository
from app.ui.workers.worker_pool import POOL


_alert_svc = AlertService()
_item_repo  = ItemRepository()


class AlertController(QObject):
    """Keeps the alert badge and notification panel in sync with live data."""

    # Relayed from LowStockDialog so MainWindow can select the item in the table
    product_selected = pyqtSignal(int)

    def __init__(
        self,
        header,          # HeaderBar — for notif_badge
        sidebar,         # Sidebar   — for alert_btn
        update_ctrl,     # UpdateController — reads .pending
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._header       = header
        self._sidebar      = sidebar
        self._upd_ctrl     = update_ctrl
        self._notif_panel: NotificationPanel | None = None
        self._low_stock_dlg: LowStockDialog | None  = None
        self._stock_counts = StockAlertCounts()

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def stock_counts(self) -> StockAlertCounts:
        return self._stock_counts

    def refresh(self) -> None:
        """Fetch alert counts on a background thread, then update badge on main thread."""
        POOL.submit("alerts", self._fetch_counts, self._apply_counts)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _fetch_counts(self) -> tuple:
        """Background: query all three alert categories. Returns (counts, has_out)."""
        low      = _alert_svc.get_low_stock_items()
        expired  = _alert_svc.get_expired_items()
        expiring = _alert_svc.get_expiring_items(days=30)
        has_out  = any(p.is_out for p in low)
        return StockAlertCounts(low=len(low), expiring=len(expiring), expired=len(expired)), has_out

    def _apply_counts(self, result: tuple) -> None:
        """Main thread: update sidebar button and header badge from fetched counts."""
        counts, has_out = result
        self._stock_counts = counts

        n_update  = 1 if self._upd_ctrl.pending else 0
        n_total   = counts.total + n_update
        btn       = self._sidebar.alert_btn
        badge     = self._header.notif_badge
        is_critical = counts.expired > 0 or n_update > 0 or has_out

        if n_total == 0:
            btn.setText(t("alert_ok"))
            btn.setObjectName("alert_ok")
            badge.hide()
        elif is_critical:
            s = "s" if n_total > 1 else ""
            btn.setText(t("alert_critical", n=n_total, s=s))
            btn.setObjectName("alert_critical")
            badge.setText(str(n_total)); badge.show()
        else:
            s = "s" if n_total > 1 else ""
            btn.setText(t("alert_warn", n=n_total, s=s))
            btn.setObjectName("alert_warn")
            badge.setText(str(n_total)); badge.show()

        btn.style().unpolish(btn); btn.style().polish(btn)

    def toggle_panel(self) -> None:
        """Show or hide the unified notification dropdown (toggle on repeated clicks)."""
        if self._notif_panel and self._notif_panel.isVisible():
            self._notif_panel.hide()
            return

        panel = NotificationPanel(
            pending_update=self._upd_ctrl.pending,
            stock=self._stock_counts,
            parent=None,
        )
        self._notif_panel = panel

        panel.view_alerts_requested.connect(self._open_low_stock_dialog)
        panel.install_update_requested.connect(self._upd_ctrl.show_banner)
        panel.remind_later.connect(self._upd_ctrl.remind_later)

        panel.popup_below(self._header.notif_btn)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _open_low_stock_dialog(self) -> None:
        """Open the LowStockDialog; raise if already open."""
        if self._low_stock_dlg and self._low_stock_dlg.isVisible():
            self._low_stock_dlg.raise_()
            return

        # Resolve parent widget from QObject tree
        parent_w = self.parent() if isinstance(self.parent(), QWidget) else None
        self._low_stock_dlg = LowStockDialog(parent_w)
        self._low_stock_dlg.product_selected.connect(self._on_product_selected)
        self._low_stock_dlg.show()

    def _on_product_selected(self, pid: int) -> None:
        """Relay the product-selected event so MainWindow can highlight the row."""
        self.product_selected.emit(pid)
