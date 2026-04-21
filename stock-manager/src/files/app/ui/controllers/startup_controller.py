"""
app/ui/controllers/startup_controller.py — Post-paint startup data loading.

Runs all heavy DB work after the first paint so the window appears instantly.

Sequence:
  1. Show overlay on analytics page
  2. Fetch summary KPIs off the main thread (DataWorker)
  3. On success → fill dashboard, refresh analytics, trigger alert refresh,
     show footer "Ready", then kick off inventory list load
  4. Inventory list load → fires on_filters_changed → POOL debounced query

Usage (from MainWindow.__init__):
    self._startup = StartupController(
        inv_page=self._inv_page,
        analytics_page=self._analytics_page,
        alert_ctrl=self._alert_ctrl,
        on_filters_changed=self._on_filters_changed,
        on_status=self._show_status,
        item_repo=_item_repo,
        parent=self,
    )
    QTimer.singleShot(0, self._startup.begin)
"""
from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from app.core.i18n import t
from app.repositories.item_repo import ItemRepository
from app.ui.components.loading_overlay import LoadingOverlay
from app.ui.workers.data_worker import DataWorker


class StartupController(QObject):
    """Orchestrates the two-phase background startup data load."""

    # Emitted once the summary load finishes (success or error)
    ready = pyqtSignal()

    def __init__(
        self,
        inv_page,
        analytics_page,
        alert_ctrl,
        on_filters_changed: Callable[[dict], None],
        on_status: Callable[[str], None],
        item_repo: ItemRepository,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._inv_page           = inv_page
        self._analytics_page     = analytics_page
        self._alert_ctrl         = alert_ctrl
        self._on_filters_changed = on_filters_changed
        self._on_status          = on_status
        self._item_repo          = item_repo
        self._workers: list[DataWorker] = []

    # ── Public entry-point ────────────────────────────────────────────────────

    def begin(self) -> None:
        """Call once, after the first paint (via QTimer.singleShot(0, ...))."""
        # Overlay parent: prefer the analytics page if it exists, else fall
        # back to the inventory page (always eager). Analytics is now lazy
        # and often None on fresh startup — don't crash just because the
        # user hasn't opened it yet.
        overlay_target = self._analytics_page if self._analytics_page is not None else self._inv_page
        overlay = LoadingOverlay(overlay_target)
        overlay.show_loading(t("loading_dashboard"))
        self._load_summary(overlay)

    # ── Phase 1: Summary KPIs ─────────────────────────────────────────────────

    def _load_summary(self, overlay: LoadingOverlay) -> None:
        worker = DataWorker(self._item_repo.get_summary)
        self._workers.append(worker)

        def _on_ok(summary: dict) -> None:
            self._inv_page.dashboard.update_data(summary)
            # Analytics is a lazy page now — its own `on_activate` runs a
            # refresh the first time the user navigates to it, so we don't
            # need to fire one here. Previously this call cost 200-400 ms
            # of skeleton-paint + POOL dispatch on the startup UI thread
            # for a page the user might never open.
            overlay.hide_loading()
            self._alert_ctrl.refresh()
            self._on_status(t("statusbar_ready"))
            self.ready.emit()
            QTimer.singleShot(0, self._load_inventory)
            self._drop(worker)

        def _on_err(_: str) -> None:
            overlay.hide_loading()
            self._on_status(t("statusbar_ready"))
            # Fallback: synchronous filter so the table isn't blank
            self._on_filters_changed(self._inv_page.filter_bar.get_filters())
            self._alert_ctrl.refresh()
            self.ready.emit()
            self._drop(worker)

        worker.result.connect(_on_ok)
        worker.error.connect(_on_err)
        worker.start()

    # ── Phase 2: Inventory table ──────────────────────────────────────────────

    def _load_inventory(self) -> None:
        inv_overlay = LoadingOverlay(self._inv_page)
        inv_overlay.show_loading(t("loading_inventory"))

        # DataWorker just reads the current filter state; actual DB query goes
        # via POOL inside on_filters_changed (debounced, background-safe).
        worker = DataWorker(self._inv_page.filter_bar.get_filters)
        self._workers.append(worker)

        def _on_ok(filters: dict) -> None:
            self._on_filters_changed(filters)
            inv_overlay.hide_loading()
            self._drop(worker)

        def _on_err(_: str) -> None:
            inv_overlay.hide_loading()
            self._on_filters_changed(self._inv_page.filter_bar.get_filters())
            self._drop(worker)

        worker.result.connect(_on_ok)
        worker.error.connect(_on_err)
        worker.start()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _drop(self, worker: DataWorker) -> None:
        """Remove a finished worker from the keep-alive list (safe if missing)."""
        if worker in self._workers:
            self._workers.remove(worker)
