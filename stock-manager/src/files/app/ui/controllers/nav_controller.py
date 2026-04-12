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

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QStackedWidget

from app.repositories.category_repo import CategoryRepository
from app.ui.components.sidebar import Sidebar
from app.ui.tabs.matrix_tab import MatrixTab


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
        self._pages: dict[str, tuple[int, Callable | None]] = {}
        self.matrix_tabs: list[MatrixTab] = []

    # ── Registration ─────────────────────────────────────────────────────────

    def register(
        self,
        key: str,
        page_index: int,
        on_activate: Callable | None = None,
    ) -> None:
        """Register a static page with an optional refresh callback."""
        self._pages[key] = (page_index, on_activate)

    # ── Navigation ────────────────────────────────────────────────────────────

    def go(self, key: str) -> None:
        """Switch to the page identified by *key*."""
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
        page_index, on_activate = entry
        self._stack.setCurrentIndex(page_index)
        if on_activate is not None:
            on_activate()

        self.navigated.emit(key)

    def _go_matrix(self, cat_key: str) -> None:
        for i, tab in enumerate(self.matrix_tabs):
            if tab._cat_key == cat_key:
                self._stack.setCurrentIndex(self._matrix_start + i)
                tab.refresh()
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
        """Remove all dynamic category tabs, recreate from DB, re-add to stack."""
        for tab in self.matrix_tabs:
            self._stack.removeWidget(tab)
            tab.deleteLater()
        self.matrix_tabs.clear()
        self._sidebar.rebuild_categories()

        for cat in self._cat_repo.get_all_active():
            tab = self._tab_factory(cat.key)
            self.matrix_tabs.append(tab)
            self._stack.addWidget(tab)

    def retranslate_matrix_tabs(self) -> None:
        for tab in self.matrix_tabs:
            tab.retranslate()

    def apply_theme_to_matrix_tabs(self) -> None:
        """Re-apply inline theme styles on all dynamic matrix tabs."""
        for tab in self.matrix_tabs:
            tab.apply_theme()
