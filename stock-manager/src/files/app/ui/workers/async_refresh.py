"""app/ui/workers/async_refresh.py — AsyncRefreshMixin.

Standard contract for pages/tabs/panels that load data from the DB:

    class InventoryPage(AsyncRefreshMixin, QWidget):
        POOL_KEY_PREFIX = "inv_page"

        def refresh(self):
            search = self._search_box.text()
            self.async_refresh(
                fetch   = lambda: _item_repo.get_all_items(search=search),
                apply   = self._apply_items,
                key_suffix = "items",
                debounce_ms = 0,
            )

        def _apply_items(self, items):
            self._table.set_items(items)

The mixin guarantees:

* **Keyed cancellation** — a fresh submit invalidates any prior task with the
  same key, so stale results never overwrite fresh data.
* **Widget-alive guard** — the `apply` callback is skipped if the widget has
  already been deleted (tab closed during load, language/theme rebuild, etc.).
* **Safe error path** — worker exceptions go to `_show_empty_state(msg)` (a
  small overridable hook) instead of the default critical-message-box, so
  the app never freezes on an error dialog modal.
* **Loading toggle** — `_set_loading(True/False)` fires before submit and on
  completion so subclasses can show a shimmer/spinner.

The mixin does NOT introduce any threading of its own — it defers entirely
to `POOL`. Connections are on the main thread (Qt's auto-connect); the
`fetch` callable runs on a pool thread and must be SQLite-safe (repositories
already are: see `app/core/database.py` thread-local connection).
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from app.ui.workers.worker_pool import POOL

_log = logging.getLogger(__name__)


class AsyncRefreshMixin:
    """Mixin. Expects to be combined with a QObject/QWidget subclass."""

    #: Override in subclasses. Used as the POOL key prefix so each class
    #: has its own isolated key-space. Example: "inv_page", "matrix_tab".
    POOL_KEY_PREFIX: str = "async_refresh"

    # ── Public API ────────────────────────────────────────────────────────────

    def async_refresh(
        self,
        fetch: Callable[[], Any],
        apply: Callable[[Any], None],
        *,
        key_suffix: str = "",
        debounce_ms: int = 0,
        show_skeleton: bool = True,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        """Run `fetch()` on a worker, then `apply(result)` on the UI thread.

        Re-entrancy: a second call with the same `key_suffix` auto-cancels
        the prior in-flight task. Use distinct suffixes when one page issues
        multiple parallel queries.
        """
        key = self._pool_key(key_suffix)

        if show_skeleton:
            try:
                self._set_loading(True)
            except Exception:
                pass

        def _guarded_apply(value):
            if not self._is_alive():
                return
            try:
                self._set_loading(False)
            except Exception:
                pass
            try:
                apply(value)
            except Exception:
                _log.exception(
                    "async_refresh apply handler raised (key=%s)", key
                )

        def _guarded_error(msg):
            if not self._is_alive():
                return
            try:
                self._set_loading(False)
            except Exception:
                pass
            if on_error is not None:
                try:
                    on_error(msg)
                    return
                except Exception:
                    _log.exception(
                        "async_refresh on_error handler raised (key=%s)", key
                    )
            # Default: show a non-blocking empty-state rather than a modal
            try:
                self._show_empty_state(f"Couldn't load — {msg}")
            except Exception:
                pass

        if debounce_ms > 0:
            POOL.submit_debounced(
                key, fetch, _guarded_apply, _guarded_error, delay_ms=debounce_ms
            )
        else:
            POOL.submit(key, fetch, _guarded_apply, _guarded_error)

    def cancel_refresh(self, key_suffix: str = "") -> None:
        """Cancel a pending/in-flight refresh for this widget + suffix."""
        POOL.cancel(self._pool_key(key_suffix))

    def is_refresh_pending(self, key_suffix: str = "") -> bool:
        return POOL.has_pending(self._pool_key(key_suffix))

    # ── Overridable hooks ─────────────────────────────────────────────────────

    def _set_loading(self, on: bool) -> None:
        """Toggle a loading indicator. Default is a no-op; subclasses can
        wire this to a skeleton shimmer, spinner, or opacity effect on the
        main content area."""
        return

    def _show_empty_state(self, msg: str) -> None:
        """Render a non-blocking empty / error state inline. Default is
        a no-op; subclasses with a dedicated empty-state card should override
        and swap their content stack to the message card."""
        _log.info("async_refresh empty-state for %s: %s", self.POOL_KEY_PREFIX, msg)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _pool_key(self, key_suffix: str) -> str:
        if key_suffix:
            return f"{self.POOL_KEY_PREFIX}:{key_suffix}"
        return self.POOL_KEY_PREFIX

    def _is_alive(self) -> bool:
        """Best-effort check that the host widget hasn't been deleted.

        Works against both Qt C++ deletion (sip.isdeleted) and Python-side
        destruction. Safe to call from main-thread signal handlers.
        """
        try:
            import sip  # type: ignore
        except Exception:
            try:
                from PyQt6 import sip  # type: ignore
            except Exception:
                sip = None  # noqa: N806
        if sip is not None:
            try:
                if sip.isdeleted(self):  # type: ignore[attr-defined]
                    return False
            except (TypeError, RuntimeError):
                pass
        # Tombstoned widgets often raise on attribute access
        try:
            _ = self.objectName  # method presence check
        except RuntimeError:
            return False
        return True
