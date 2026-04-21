"""
app/ui/controllers/nav_controller.py — Page navigation orchestration.

Owns:
  - QStackedWidget page switching
  - Sidebar active-nav highlight
  - Sidebar visibility toggle
  - Dynamic matrix-tab lifecycle (rebuild when categories change)

Usage (from MainWindow._build_ui):
    self._nav_ctrl = NavController(
        stack=self._stack,
        sidebar=self._sidebar,
        toggle_btn=self._header.sidebar_toggle,
        cat_repo=_cat_repo,
        matrix_tab_factory=MatrixTab,
        parent=self,
    )
    self._nav_ctrl.register("nav_inventory", _PAGE_INVENTORY)
    self._nav_ctrl.register("nav_transactions", _PAGE_TRANSACTIONS,
                            on_activate=lambda: self._txn_page.refresh())
    ...
    self._sidebar.nav_clicked.connect(self._nav_ctrl.go)
    self._header.sidebar_toggled.connect(self._nav_ctrl.toggle_sidebar)
"""
from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QStackedWidget, QWidget, QVBoxLayout, QLabel

from app.repositories.category_repo import CategoryRepository
from app.ui.components.sidebar import Sidebar
from app.ui.tabs.matrix_tab import MatrixTab


class _MatrixPlaceholder(QWidget):
    """Lightweight stand-in for a real MatrixTab.

    The real tab (FrozenMatrixContainer + tables + banner + cards) is
    expensive to construct — creating all 6 at startup was the biggest
    single source of UI-thread stalls. We defer construction until the
    user navigates to that category for the first time.
    """

    def __init__(self, cat_key: str, parent=None):
        super().__init__(parent)
        self._cat_key = cat_key
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("")
        lbl.setObjectName("matrix_placeholder")
        lay.addWidget(lbl)


class NavController(QObject):
    """Owns all navigation state and page-switching logic."""

    # Emitted after the active page changes (key = nav key string)
    navigated = pyqtSignal(str)

    def __init__(
        self,
        stack: QStackedWidget,
        sidebar: Sidebar,
        toggle_btn,                       # QPushButton — sidebar ☰ / × button
        cat_repo: CategoryRepository,
        matrix_tab_factory: Callable[[str], MatrixTab],
        matrix_page_start: int,
        help_fn: Callable[[], None],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._stack          = stack
        self._sidebar        = sidebar
        self._toggle_btn     = toggle_btn
        self._cat_repo       = cat_repo
        self._tab_factory    = matrix_tab_factory
        self._matrix_start   = matrix_page_start
        self._help_fn        = help_fn

        self.current: str = ""
        # Each entry: (page_index, on_activate, factory, realized_flag)
        # - factory == None  → eager page, already in the stack.
        # - factory != None  → lazy page. Placeholder is at page_index
        #   until first nav; then factory() builds the real widget, we
        #   swap it into the stack at the same index, and `realized_flag`
        #   is toggled to True so subsequent navs skip the build path.
        self._pages: dict[str, tuple[int, Callable | None, Callable | None, bool]] = {}
        # Cached realised lazy pages so callers can retrieve them (e.g.
        # for cross-page drill-down wiring after they are built).
        self._lazy_instances: dict[str, object] = {}
        # `matrix_tabs` contains either MatrixTab instances (realised)
        # or `_MatrixPlaceholder` widgets (not yet realised). `_go_matrix`
        # transparently upgrades a placeholder to a real tab on first nav.
        self.matrix_tabs: list[QWidget] = []
        # Category keys paralleling matrix_tabs so we can find the slot
        # to upgrade without depending on widget attributes.
        self._matrix_cat_keys: list[str] = []

    # ── Registration ─────────────────────────────────────────────────────────

    def register(
        self,
        key: str,
        page_index: int,
        on_activate: Callable | None = None,
    ) -> None:
        """Register an eagerly-constructed page at `page_index`.

        The widget must already be inserted in the QStackedWidget at
        that index by the caller. `on_activate` fires after every
        setCurrentIndex to this key — typically a cheap refresh().
        """
        self._pages[key] = (page_index, on_activate, None, True)

    def register_lazy(
        self,
        key: str,
        page_index: int,
        factory: Callable[[], object],
        on_activate: Callable | None = None,
        on_build: Callable | None = None,
    ) -> None:
        """Register a lazily-constructed page.

        The caller must still have a placeholder widget at `page_index`
        in the stack (see `register_placeholder` helper). The first time
        the user navigates to `key`, `factory()` is called on the UI
        thread to build the real widget; it is swapped into the stack
        at `page_index`, the placeholder is deleted, `on_build(widget)`
        fires once for post-build wiring (e.g. drill-down targets), and
        then `on_activate` runs as normal. Subsequent navs are eager.
        """
        self._pages[key] = (page_index, on_activate, (factory, on_build), False)

    def register_placeholder(self, page_index: int) -> QWidget:
        """Insert a lightweight placeholder widget at `page_index` in the
        stack and return it. Use this before `register_lazy` so the
        QStackedWidget has something occupying the slot.
        """
        ph = QWidget()
        ph.setObjectName("page_placeholder")
        self._stack.insertWidget(page_index, ph)
        return ph

    def get_lazy_instance(self, key: str):
        """Return the realised widget for a lazy page, or None if the
        user has not yet navigated to it. Safe to call at any time."""
        return self._lazy_instances.get(key)

    def realize(self, key: str):
        """Force-build a lazy page if it hasn't been already.

        Useful when a caller (e.g. cross-page wiring) needs the real
        widget without actually switching to it. Returns the realised
        widget, or None if the key is not registered lazily.
        """
        entry = self._pages.get(key)
        if entry is None:
            return None
        page_index, on_activate, lazy, realized = entry
        if realized or lazy is None:
            return self._lazy_instances.get(key)
        return self._realize_lazy(key, entry)

    def _realize_lazy(self, key: str, entry):
        """Build the real widget, swap into stack, mark realised."""
        page_index, on_activate, lazy, _realized = entry
        factory, on_build = lazy
        widget = factory()
        # Insert real widget at the same index; that pushes the
        # placeholder to page_index+1. Then remove the placeholder.
        self._stack.insertWidget(page_index, widget)
        placeholder = self._stack.widget(page_index + 1)
        if placeholder is not None:
            self._stack.removeWidget(placeholder)
            placeholder.deleteLater()
        # Update registry + cache
        self._pages[key] = (page_index, on_activate, None, True)
        self._lazy_instances[key] = widget
        if on_build is not None:
            try:
                on_build(widget)
            except Exception:
                pass
        return widget

    # ── Navigation ────────────────────────────────────────────────────────────

    def go(self, key: str) -> None:
        """Switch to the page identified by *key*. Realises lazy pages
        on first nav."""
        self.current = key
        self._sidebar.update_styles(key)

        if key == "nav_help":
            self._help_fn()
            return  # don't change the visible page

        if key.startswith("cat_"):
            self._go_matrix(key[4:])
            return

        entry = self._pages.get(key)
        if entry is None:
            return
        page_index, on_activate, lazy, realized = entry
        if lazy is not None and not realized:
            self._realize_lazy(key, entry)
        self._stack.setCurrentIndex(page_index)
        if on_activate is not None:
            try:
                on_activate()
            except Exception:
                pass

        self.navigated.emit(key)

    def _go_matrix(self, cat_key: str) -> None:
        for i, tab in enumerate(self.matrix_tabs):
            slot_key = self._matrix_cat_keys[i] if i < len(self._matrix_cat_keys) else getattr(tab, "_cat_key", None)
            if slot_key != cat_key:
                continue
            # Upgrade placeholder → real MatrixTab on first access
            if isinstance(tab, _MatrixPlaceholder):
                real_tab = self._tab_factory(cat_key)
                # Replace in the stack at the same index so page_index math stays stable
                idx = self._matrix_start + i
                self._stack.insertWidget(idx, real_tab)
                # Remove placeholder (index now shifted by +1) then set current
                self._stack.removeWidget(tab)
                tab.deleteLater()
                self.matrix_tabs[i] = real_tab
                tab = real_tab
            self._stack.setCurrentIndex(self._matrix_start + i)
            # Defer refresh until after the page is shown so the switch
            # itself doesn't stall on the DB round-trip + widget rebuild.
            QTimer.singleShot(0, tab.refresh)
            self.navigated.emit(f"cat_{cat_key}")
            return

    # ── Sidebar toggle ────────────────────────────────────────────────────────

    def toggle_sidebar(self) -> None:
        """Show/hide the sidebar and update the toggle button glyph."""
        visible = self._sidebar.isVisible()
        self._sidebar.setVisible(not visible)
        self._toggle_btn.setText("☰" if visible else "×")

    # ── Matrix tab lifecycle ──────────────────────────────────────────────────

    def rebuild_matrix_tabs(self) -> None:
        """Synchronise matrix tabs with the current category list.

        Fast path — if the active-category set is unchanged (the common
        case on settings close, since most admin changes don't touch
        categories), we KEEP every existing tab (realised + placeholder)
        intact and just mark realised tabs dirty so they refresh lazily.
        This avoids the blank-page flash the user saw when a realised
        tab was nuked into a placeholder and had to be rebuilt.

        Slow path — only when categories are added/removed/reordered do
        we tear everything down and reinstate placeholders.
        """
        new_cats = list(self._cat_repo.get_all_active())
        new_keys = [cat.key for cat in new_cats]

        if new_keys == self._matrix_cat_keys and self.matrix_tabs:
            # Fast path: category set unchanged — keep existing tabs.
            # Mark realised tabs dirty so they pick up any data changes
            # (e.g. after ensure_matrix_entries added new model × pt rows).
            #
            # IMPORTANT: refresh() is deferred to the next event-loop tick.
            # This function is often called from within another worker's
            # result-signal callback (e.g. settings-close → ensure_matrix_entries
            # on_result → rebuild_matrix_tabs). Calling tab.refresh() inline
            # happens *before* the worker's internal _cleanup slot runs, so
            # any guard that checks `has_pending(...)` would wrongly skip.
            # Deferring via QTimer ensures we're back at a clean event-loop
            # idle state before we submit the refresh.
            for tab in self.matrix_tabs:
                if isinstance(tab, _MatrixPlaceholder):
                    continue
                try:
                    tab._dirty = True
                    if tab.isVisible():
                        QTimer.singleShot(0, tab.refresh)
                except Exception:
                    pass
            # Keep the sidebar in sync (retranslate labels, etc.)
            self._sidebar.rebuild_categories()
            return

        # Slow path: category list actually changed — rebuild placeholders
        for tab in self.matrix_tabs:
            self._stack.removeWidget(tab)
            tab.deleteLater()
        self.matrix_tabs.clear()
        self._matrix_cat_keys.clear()
        self._sidebar.rebuild_categories()

        for cat in new_cats:
            placeholder = _MatrixPlaceholder(cat.key)
            self.matrix_tabs.append(placeholder)
            self._matrix_cat_keys.append(cat.key)
            self._stack.addWidget(placeholder)

    def retranslate_matrix_tabs(self) -> None:
        for tab in self.matrix_tabs:
            if isinstance(tab, _MatrixPlaceholder):
                continue
            try:
                tab.retranslate()
            except Exception:
                pass

    def apply_theme_to_matrix_tabs(self) -> None:
        """Re-apply inline theme styles on all REALISED matrix tabs.
        Placeholders have no theme state — they don't need touching."""
        for tab in self.matrix_tabs:
            if isinstance(tab, _MatrixPlaceholder):
                continue
            try:
                tab.apply_theme()
            except Exception:
                pass
