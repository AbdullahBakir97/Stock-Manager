"""app/ui/pages/barcode_gen_page.py — Professional barcode generator page."""
from __future__ import annotations

import os
import tempfile

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QFrame, QRadioButton,
    QComboBox, QListWidget, QCheckBox, QScrollArea,
    QFileDialog, QMessageBox, QSizePolicy, QAbstractItemView,
    QButtonGroup,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QImage

from app.core.theme import THEME
from app.core.i18n import t
from app.repositories.category_repo import CategoryRepository
from app.repositories.model_repo import ModelRepository
from app.services.barcode_gen_service import BarcodeGenService, BarcodeEntry
from app.ui.components.dashboard_widget import SummaryCard

_cat_repo = CategoryRepository()
_model_repo = ModelRepository()
_gen_svc = BarcodeGenService()


# ── Main Page ───────────────────────────────────────────────────────────────

class BarcodeGenPage(QWidget):
    """Professional barcode generator with scope selector and PDF preview."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._entries: list[BarcodeEntry] = []
        self._pdf_bytes: bytes = b""
        self._pdf_pages: list[QPixmap] = []
        self._current_page = 0
        self._build()

    def _build(self):
        tk = THEME.tokens
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)

        # ── Header ──
        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(12)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_lbl = QLabel(t("bcgen_title"))
        title_lbl.setStyleSheet(f"font-size:20px; font-weight:700; color:{tk.t1};")
        title_col.addWidget(title_lbl)
        sub_lbl = QLabel(t("bcgen_scope_all"))
        sub_lbl.setStyleSheet(f"font-size:12px; color:{tk.t3};")
        title_col.addWidget(sub_lbl)
        hdr_row.addLayout(title_col)
        hdr_row.addStretch()
        root.addLayout(hdr_row)

        # ── KPI Row — uses SummaryCard from dashboard for consistency ──
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)
        self._kpi_generated = SummaryCard("📊", tk.blue)
        self._kpi_generated.set_value(0, t("bcgen_title"))
        self._kpi_pages = SummaryCard("📄", tk.green)
        self._kpi_pages.set_value(0, t("bcgen_preview"))
        self._kpi_assigned = SummaryCard("✓", tk.purple)
        self._kpi_assigned.set_formatted_value("—", t("bcgen_assign_save"))
        kpi_row.addWidget(self._kpi_generated)
        kpi_row.addWidget(self._kpi_pages)
        kpi_row.addWidget(self._kpi_assigned)
        kpi_row.addStretch()
        root.addLayout(kpi_row)

        # ── Main splitter ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet(
            f"QSplitter::handle {{ background:{tk.border}; }}"
        )

        # ── LEFT: Controls Panel (scrollable for small screens) ──
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setObjectName("summary_card")
        left_scroll.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        left_w = QWidget()
        left = QVBoxLayout(left_w)
        left.setContentsMargins(10, 10, 10, 10)
        left.setSpacing(6)

        # Section: Scope
        scope_hdr = QLabel(t("bcgen_scope_all"))
        scope_hdr.setStyleSheet(
            f"font-size:13px; font-weight:700; color:{tk.t1};"
        )
        left.addWidget(scope_hdr)

        self._rb_all = QRadioButton(t("bcgen_scope_all"))
        self._rb_all.setChecked(True)
        self._rb_cat = QRadioButton(t("bcgen_scope_category"))
        self._rb_model = QRadioButton(t("bcgen_scope_model"))
        self._rb_pt = QRadioButton(t("bcgen_scope_part_type"))

        scope_group = QButtonGroup(self)
        for rb in (self._rb_all, self._rb_cat, self._rb_model, self._rb_pt):
            scope_group.addButton(rb)
            rb.toggled.connect(self._on_scope_change)
            left.addWidget(rb)

        # Brand filter — always visible, narrows every scope mode. "All
        # brands" disables the filter; picking a specific brand limits the
        # generated batch to that brand's models, regardless of which
        # scope radio is active.
        brand_lbl = QLabel("Brand")
        brand_lbl.setStyleSheet(f"font-size:11px; color:{tk.t3};")
        left.addWidget(brand_lbl)
        self._brand_combo = QComboBox()
        self._brand_combo.setMinimumHeight(28)
        self._brand_combo.currentIndexChanged.connect(self._on_filter_change)
        left.addWidget(self._brand_combo)

        # Category combo
        self._cat_combo = QComboBox()
        self._cat_combo.setMinimumHeight(28)
        left.addWidget(self._cat_combo)

        # Model list
        self._model_list = QListWidget()
        self._model_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self._model_list.setMaximumHeight(120)
        self._model_list.itemSelectionChanged.connect(self._on_filter_change)
        left.addWidget(self._model_list)

        # Part type list
        self._pt_list = QListWidget()
        self._pt_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self._pt_list.setMaximumHeight(120)
        self._pt_list.itemSelectionChanged.connect(self._on_filter_change)
        left.addWidget(self._pt_list)

        # Live "matching items" count — updated as the user adjusts any
        # filter. Tells the user up-front how many barcodes a Generate
        # click will produce so they can spot a too-broad scope before
        # waiting for the worker to finish.
        self._count_label = QLabel("— items match")
        self._count_label.setStyleSheet(
            f"font-size:11px; font-weight:600; color:{tk.t3}; padding:4px 0;"
        )
        left.addWidget(self._count_label)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background:{tk.border}; border:none; max-height:1px;")
        left.addWidget(sep)

        # Section: Options
        opts_hdr = QLabel(t("bcgen_format"))
        opts_hdr.setStyleSheet(
            f"font-size:13px; font-weight:700; color:{tk.t1};"
        )
        left.addWidget(opts_hdr)

        fmt_row = QHBoxLayout()
        fmt_row.setSpacing(12)
        self._rb_code39 = QRadioButton("Code 39")
        self._rb_code39.setChecked(True)
        self._rb_code128 = QRadioButton("Code 128")
        fmt_group = QButtonGroup(self)
        fmt_group.addButton(self._rb_code39)
        fmt_group.addButton(self._rb_code128)
        fmt_row.addWidget(self._rb_code39)
        fmt_row.addWidget(self._rb_code128)
        fmt_row.addStretch()
        left.addLayout(fmt_row)

        self._chk_commands = QCheckBox(t("bcgen_include_commands"))
        self._chk_commands.setChecked(True)
        left.addWidget(self._chk_commands)

        self._chk_existing = QCheckBox(t("bcgen_include_existing"))
        self._chk_existing.toggled.connect(self._on_filter_change)
        left.addWidget(self._chk_existing)

        # Regenerate (overwrite) — replaces a saved barcode with a fresh
        # one computed from the CURRENT model + part-type names. Use
        # this after renaming a part type or model so the saved codes
        # reflect the new names instead of being stuck on the legacy
        # encoding. Implies include_existing (we have to fetch rows that
        # currently have barcodes in order to overwrite them).
        self._chk_regenerate = QCheckBox("Regenerate (overwrite existing)")
        self._chk_regenerate.setToolTip(
            "When ON: every selected item gets a FRESHLY computed barcode\n"
            "based on its current brand / model / part-type / colour names,\n"
            "and Assign & Save will overwrite whatever was saved before.\n\n"
            "Useful after renaming a part type or model — e.g. if you\n"
            "changed 'ORG-Service-Pack-SM' to 'ORG Service Pack', the\n"
            "saved barcodes still spell out the old name until you\n"
            "regenerate.\n\n"
            "Implies 'Include items with existing barcodes' — they have\n"
            "to be in the batch to get overwritten."
        )
        self._chk_regenerate.toggled.connect(self._on_regenerate_toggled)
        left.addWidget(self._chk_regenerate)

        # Per-color barcodes — one extra barcode per colour variant
        # (BRAND-MODEL-PT-COLOR) so a single scan resolves directly to
        # that exact colour. The colourless parent barcode is still
        # generated alongside, so the two-step "scan model → scan colour"
        # flow keeps working for users who prefer it.
        self._chk_per_color = QCheckBox("Include per-color barcodes (direct scan)")
        self._chk_per_color.setChecked(True)
        self._chk_per_color.toggled.connect(self._on_filter_change)
        self._chk_per_color.setToolTip(
            "When ON: items with colour variants get one barcode per colour\n"
            "in addition to the colourless parent. A single scan of a\n"
            "colour barcode adds that exact variant directly — no need\n"
            "to scan a separate colour code afterwards.\n\n"
            "When OFF: only colourless parents get barcodes (legacy\n"
            "behaviour); colours are resolved via the two-step flow."
        )
        left.addWidget(self._chk_per_color)

        left.addStretch()

        # Action buttons — compact for narrow left panel
        self._btn_generate = QPushButton(t("bcgen_generate"))
        self._btn_generate.setObjectName("btn_primary_sm")
        self._btn_generate.setFixedHeight(26)
        self._btn_generate.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._btn_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_generate.clicked.connect(self._generate)
        left.addWidget(self._btn_generate)

        action_row = QHBoxLayout()
        action_row.setSpacing(3)
        action_row.setContentsMargins(0, 0, 0, 0)

        self._btn_assign = QPushButton(t("bcgen_assign_save"))
        self._btn_assign.setObjectName("alert_ok_sm")
        self._btn_assign.setFixedHeight(24)
        self._btn_assign.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._btn_assign.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_assign.clicked.connect(self._assign)
        self._btn_assign.setEnabled(False)

        self._btn_export = QPushButton(t("bcgen_export_pdf"))
        self._btn_export.setObjectName("btn_secondary_sm")
        self._btn_export.setFixedHeight(24)
        self._btn_export.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_export.clicked.connect(self._export)
        self._btn_export.setEnabled(False)

        # Export to a YunPrint Database .xlsx for the K30F (and other
        # Dlabel/YunPrint label printers). The same Code39 codes already
        # saved on items get embedded as one row per barcode; the user
        # imports the file in YunPrint's Database dialog and prints the
        # whole batch as a single job.
        self._btn_export_yp = QPushButton("Export for YunPrint")
        self._btn_export_yp.setObjectName("btn_secondary_sm")
        self._btn_export_yp.setFixedHeight(24)
        self._btn_export_yp.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._btn_export_yp.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_export_yp.setToolTip(
            "Export an Excel file you can import via YunPrint → Database\n"
            "for batch printing on the K30F label printer."
        )
        self._btn_export_yp.clicked.connect(self._export_yunprint)
        self._btn_export_yp.setEnabled(False)

        action_row.addWidget(self._btn_assign, 1)
        action_row.addWidget(self._btn_export, 1)
        action_row.addWidget(self._btn_export_yp, 1)
        left.addLayout(action_row)

        # Status
        self._status = QLabel("")
        self._status.setStyleSheet(
            f"font-size:11px; color:{tk.t3};"
        )
        self._status.setWordWrap(True)
        left.addWidget(self._status)

        left_scroll.setWidget(left_w)
        left_scroll.setMinimumWidth(180)
        splitter.addWidget(left_scroll)

        # ── RIGHT: Preview Panel ──
        right_w = QFrame()
        right_w.setObjectName("summary_card")
        right = QVBoxLayout(right_w)
        right.setContentsMargins(16, 12, 16, 12)
        right.setSpacing(8)

        # Preview toolbar — wraps naturally on small screens
        prev_bar = QHBoxLayout()
        prev_bar.setSpacing(6)
        prev_lbl = QLabel(t("bcgen_preview"))
        prev_lbl.setStyleSheet(
            f"font-size:14px; font-weight:700; color:{tk.t1};"
        )
        prev_bar.addWidget(prev_lbl)
        prev_bar.addStretch()

        self._btn_prev = QPushButton("<")
        self._btn_prev.setObjectName("btn_secondary_sm")
        self._btn_prev.setMaximumWidth(32)
        self._btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_prev.clicked.connect(lambda: self._change_page(-1))
        prev_bar.addWidget(self._btn_prev)

        self._page_lbl = QLabel("")
        self._page_lbl.setStyleSheet(
            f"font-size:11px; color:{tk.t3};"
        )
        prev_bar.addWidget(self._page_lbl)

        self._btn_next = QPushButton(">")
        self._btn_next.setObjectName("btn_secondary_sm")
        self._btn_next.setMaximumWidth(32)
        self._btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_next.clicked.connect(lambda: self._change_page(1))
        prev_bar.addWidget(self._btn_next)

        self._btn_print = QPushButton(t("bcgen_print"))
        self._btn_print.setObjectName("btn_secondary_sm")
        self._btn_print.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_print.clicked.connect(self._print)
        self._btn_print.setEnabled(False)
        prev_bar.addWidget(self._btn_print)

        right.addLayout(prev_bar)

        # Preview area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._preview_label = QLabel(t("bcgen_no_items"))
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setStyleSheet(
            f"font-size:13px; color:{tk.t3};"
        )
        scroll.setWidget(self._preview_label)
        right.addWidget(scroll, 1)

        splitter.addWidget(right_w)

        # Responsive splitter: left ~25%, right ~75%, both resize proportionally
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        root.addWidget(splitter, 1)

        self._populate_combos()
        self._on_scope_change()

    # ── Combos / Scope ──────────────────────────────────────────────────────

    def _populate_combos(self):
        # Brand combo — populated from distinct brands across all phone_models
        self._brand_combo.blockSignals(True)
        self._brand_combo.clear()
        self._brand_combo.addItem("All brands", None)
        try:
            for b in _model_repo.get_brands():
                if b:
                    self._brand_combo.addItem(b, b)
        except Exception:
            pass
        self._brand_combo.blockSignals(False)

        self._cat_combo.blockSignals(True)
        self._cat_combo.clear()
        self._cat_combo.addItem(t("disp_all_brands"), None)
        for cat in _cat_repo.get_all_active():
            self._cat_combo.addItem(cat.name_en, cat.id)
        self._cat_combo.blockSignals(False)
        self._cat_combo.currentIndexChanged.connect(self._on_cat_change)
        self._refresh_model_list()
        self._refresh_pt_list()
        self._refresh_count()

    def _on_cat_change(self):
        self._refresh_pt_list()
        self._on_filter_change()

    def _refresh_model_list(self):
        """Populate the model list, narrowed by the active brand filter so
        the user only sees relevant models when picking by-model scope."""
        self._model_list.blockSignals(True)
        self._model_list.clear()
        brand = self._brand_combo.currentData() if hasattr(self, "_brand_combo") else None
        try:
            models = _model_repo.get_all(brand=brand) if brand else _model_repo.get_all()
        except TypeError:
            # Older repo signature without brand kwarg — fall back to client-side filter
            models = [m for m in _model_repo.get_all()
                      if not brand or m.brand == brand]
        for m in models:
            from PyQt6.QtWidgets import QListWidgetItem
            it = QListWidgetItem(f"{m.brand} {m.name}")
            it.setData(Qt.ItemDataRole.UserRole, m.id)
            self._model_list.addItem(it)
        self._model_list.blockSignals(False)

    def _refresh_pt_list(self):
        self._pt_list.blockSignals(True)
        self._pt_list.clear()
        cat_id = self._cat_combo.currentData()
        cats = _cat_repo.get_all_active() if cat_id is None else [_cat_repo.get_by_id(cat_id)]
        for cat in cats:
            if not cat:
                continue
            for pt in cat.part_types:
                from PyQt6.QtWidgets import QListWidgetItem
                it = QListWidgetItem(f"{cat.name_en} · {pt.name}")
                it.setData(Qt.ItemDataRole.UserRole, pt.id)
                self._pt_list.addItem(it)
        self._pt_list.blockSignals(False)

    def _on_scope_change(self):
        is_cat = self._rb_cat.isChecked()
        is_model = self._rb_model.isChecked()
        is_pt = self._rb_pt.isChecked()
        self._cat_combo.setVisible(is_cat or is_pt)
        self._model_list.setVisible(is_model)
        self._pt_list.setVisible(is_pt)
        self._on_filter_change()

    def _on_filter_change(self):
        """Any filter widget changed — refresh the model list (brand may
        have changed) and the live count label."""
        # Brand changed → repopulate model list narrowed by brand.
        # We can't always tell which widget triggered, so just re-do both.
        if self.sender() is getattr(self, "_brand_combo", None):
            self._refresh_model_list()
        self._refresh_count()

    def _on_regenerate_toggled(self, checked: bool):
        """Regenerate implies include-existing — auto-tick the dependency
        so the user doesn't have to think about both. We also force the
        dependency check to stay set while regenerate is on, since
        unchecking it would silently drop every existing row from the
        batch (regenerate without rows to regenerate = no-op)."""
        if checked:
            self._chk_existing.blockSignals(True)
            self._chk_existing.setChecked(True)
            self._chk_existing.setEnabled(False)
            self._chk_existing.blockSignals(False)
        else:
            self._chk_existing.setEnabled(True)
        self._refresh_count()

    def _refresh_count(self):
        """Update the 'X items match' label using the same predicate the
        generator will apply. Cheap COUNT(*) — no full row materialisation."""
        try:
            params = self._get_scope_params()
            include_existing = self._chk_existing.isChecked() if hasattr(self, "_chk_existing") else False
            include_per_color = self._chk_per_color.isChecked() if hasattr(self, "_chk_per_color") else True
            n = _item_repo.count_items_for_scope(
                include_existing=include_existing,
                include_per_color=include_per_color,
                **params,
            )
        except Exception:
            n = 0
        suffix = "" if include_existing else " (without barcode)"
        self._count_label.setText(f"{n} items match{suffix}")

    def _get_scope_params(self) -> dict:
        params: dict = {}
        # Brand applies to every scope — independent of the radio choice.
        brand = self._brand_combo.currentData() if hasattr(self, "_brand_combo") else None
        if brand:
            params["brand"] = brand
        if self._rb_cat.isChecked():
            cat_id = self._cat_combo.currentData()
            if cat_id:
                params["category_id"] = cat_id
        elif self._rb_model.isChecked():
            ids = [it.data(Qt.ItemDataRole.UserRole)
                   for it in self._model_list.selectedItems()]
            if ids:
                params["model_ids"] = ids
        elif self._rb_pt.isChecked():
            ids = [it.data(Qt.ItemDataRole.UserRole)
                   for it in self._pt_list.selectedItems()]
            if ids:
                params["part_type_ids"] = ids
            cat_id = self._cat_combo.currentData()
            if cat_id:
                params["category_id"] = cat_id
        return params

    # ── Generate / Assign / Export ──────────────────────────────────────────

    def _generate(self):
        """Kick off generation in two stages.

        **Stage 1 (always)** — DB fetch + barcode-text computation. Cheap
        (~200-400ms for a full category). Runs on the worker pool but
        completes fast. Lights up Assign & Save and Export for YunPrint
        immediately because those don't need the PDF.

        **Stage 2 (on demand)** — PDF assembly + PyMuPDF preview
        rasterisation. Expensive (~20-30s for a 2000-item batch on the
        K30F label workflow). Triggered lazily the first time the user
        clicks Preview / Export PDF / Print, NOT eagerly during Generate.

        The user's primary workflow (Generate → Export for YunPrint → drop
        into YunPrint Database) used to wait ~30s for a PDF that was
        never used. Now that path is just the Stage-1 cost (~300ms).
        Stage 2 still runs through the worker pool when triggered, so
        even when needed it doesn't freeze the UI.
        """
        params = self._get_scope_params()
        include_existing = self._chk_existing.isChecked()
        include_per_color = self._chk_per_color.isChecked()
        regenerate = self._chk_regenerate.isChecked()
        # PDF render parameters captured now so Stage 2 (potentially much
        # later, after the user toggled options) uses the same settings
        # the user saw at Generate time.
        self._pending_pdf_params = {
            "fmt": "code39" if self._rb_code39.isChecked() else "code128",
            "include_cmds": self._chk_commands.isChecked(),
        }

        # Disable buttons + clear stale state while Stage 1 runs.
        self._entries = []
        self._pdf_bytes = b""
        self._pdf_pages = []
        self._btn_generate.setEnabled(False)
        self._btn_assign.setEnabled(False)
        self._btn_export.setEnabled(False)
        self._btn_export_yp.setEnabled(False)
        self._btn_print.setEnabled(False)
        self._status.setText("Generating barcodes…")
        self._preview_label.setText(
            "Generated. Click 'Export PDF' or 'Print' to render the PDF."
        )

        from app.ui.workers.worker_pool import POOL

        def _stage1_worker():
            return _gen_svc.generate_for_scope(
                scope="custom",
                include_existing=include_existing,
                include_per_color=include_per_color,
                regenerate=regenerate,
                **params,
            )

        def _on_stage1(entries):
            self._btn_generate.setEnabled(True)
            self._entries = entries

            if not entries:
                self._status.setText(t("bcgen_no_items"))
                self._preview_label.setText(t("bcgen_no_items"))
                self._kpi_generated.set_value(0, t("bcgen_title"))
                self._kpi_pages.set_value(0, t("bcgen_preview"))
                return

            self._kpi_generated.set_value(len(entries), t("bcgen_title"))
            # Light up the actions that DON'T need the PDF immediately —
            # Assign & Save just writes barcodes back to inventory_items,
            # Export for YunPrint writes the .txt CSV. Both are fast.
            self._btn_assign.setEnabled(True)
            self._btn_export_yp.setEnabled(True)
            # PDF-dependent buttons stay disabled until Stage 2 finishes.
            # They become "render-on-click" — the handlers below trigger
            # Stage 2 when first pressed.
            self._btn_export.setEnabled(True)
            self._btn_print.setEnabled(True)
            self._status.setText(
                f"{len(entries)} barcodes ready · "
                "PDF renders on demand (Export / Print)"
            )

        def _on_error(msg: str):
            self._btn_generate.setEnabled(True)
            self._status.setText("Generation failed.")
            QMessageBox.critical(self, "Error", str(msg))

        POOL.submit("barcode_gen", _stage1_worker, _on_stage1, _on_error)

    def _ensure_pdf_ready(self, on_ready) -> bool:
        """Stage 2 of barcode generation — render the PDF on demand.

        Returns True if the PDF is already rendered (caller can proceed
        synchronously with ``on_ready()`` skipped — we already invoked it
        in that case). Returns False if a render was kicked off; the
        ``on_ready`` callback fires on the UI thread once the PDF is
        ready. Callers are responsible for disabling their button while
        the render is in flight.

        Implementation note: piggy-backs on the same ``POOL.submit`` key
        as Stage 1, so a stale Stage-1 result that arrives mid-render is
        silently dropped by the epoch guard.
        """
        if self._pdf_bytes:
            on_ready()
            return True
        if not self._entries:
            return True  # nothing to render
        params = getattr(self, "_pending_pdf_params", None) or {
            "fmt": "code39", "include_cmds": True,
        }
        entries = self._entries

        self._status.setText("Rendering PDF…")
        from app.ui.workers.worker_pool import POOL

        def _stage2_worker():
            try:
                pdf_bytes = _gen_svc.create_pdf(
                    entries,
                    include_commands=params["include_cmds"],
                    barcode_format=params["fmt"],
                )
                return {"pdf": pdf_bytes}
            except Exception as e:
                return {"pdf": b"", "error": str(e)}

        def _on_stage2(payload):
            err = payload.get("error")
            if err:
                self._status.setText("PDF render failed.")
                QMessageBox.critical(self, "Error", err)
                return
            self._pdf_bytes = payload.get("pdf", b"")
            self._render_preview()
            self._kpi_pages.set_value(len(self._pdf_pages), t("bcgen_preview"))
            self._status.setText(
                f"{len(self._entries)} barcodes · {len(self._pdf_pages)} page(s)"
            )
            on_ready()

        def _on_err(msg):
            self._status.setText("PDF render failed.")
            QMessageBox.critical(self, "Error", str(msg))

        POOL.submit("barcode_gen_pdf", _stage2_worker, _on_stage2, _on_err)
        return False

    def _render_preview(self):
        """Render PDF pages to QPixmap for preview."""
        self._pdf_pages.clear()
        self._current_page = 0

        # Try importing PyMuPDF (supports both old and new module names)
        fitz = None
        try:
            import fitz as _fitz
            fitz = _fitz
        except ImportError:
            try:
                import pymupdf as _fitz  # PyMuPDF >= 1.24.x
                fitz = _fitz
            except ImportError:
                pass

        if fitz is None:
            self._pdf_pages.append(QPixmap())
            self._preview_label.setText(
                f"PDF generated ({len(self._entries)} barcodes)\n\n"
                "Install PyMuPDF for in-app preview:\n"
                "pip install PyMuPDF\n\n"
                "Use 'Export PDF' to save and view."
            )
            self._page_lbl.setText(t("bcgen_page_of", current=1, total=1))
            return

        try:
            doc = fitz.open(stream=self._pdf_bytes, filetype="pdf")
            for page in doc:
                pix = page.get_pixmap(dpi=150)
                img = QImage(pix.samples, pix.width, pix.height,
                             pix.stride, QImage.Format.Format_RGB888)
                self._pdf_pages.append(QPixmap.fromImage(img.copy()))
            doc.close()
        except Exception as e:
            print(f"[BarcodeGen] PyMuPDF render error: {e}")
            self._pdf_pages.append(QPixmap())
            self._preview_label.setText(
                f"PDF generated ({len(self._entries)} barcodes)\n\n"
                f"Preview error: {e}\n\n"
                "Use 'Export PDF' to save and view."
            )
            self._page_lbl.setText(t("bcgen_page_of", current=1, total=1))
            return

        self._show_page(0)

    def _show_page(self, idx: int):
        if not self._pdf_pages:
            return
        idx = max(0, min(idx, len(self._pdf_pages) - 1))
        self._current_page = idx
        pm = self._pdf_pages[idx]
        if not pm.isNull():
            # Scale to fit preview area width (responsive)
            avail_w = self._preview_label.width() or 600
            target_w = min(pm.width(), max(avail_w - 20, 400))
            scaled = pm.scaledToWidth(
                target_w,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._preview_label.setPixmap(scaled)
        self._page_lbl.setText(
            t("bcgen_page_of", current=idx + 1, total=len(self._pdf_pages))
        )
        self._btn_prev.setEnabled(idx > 0)
        self._btn_next.setEnabled(idx < len(self._pdf_pages) - 1)

    def _change_page(self, delta: int):
        self._show_page(self._current_page + delta)

    def _assign(self):
        if not self._entries:
            return
        count = _gen_svc.assign_barcodes(self._entries)
        self._kpi_assigned.set_value(count, t("bcgen_assign_save"))
        self._status.setText(t("bcgen_assigned_n", n=count))
        QMessageBox.information(self, t("bcgen_title"),
                                t("bcgen_assigned_n", n=count))

    def _export(self):
        # Lazy PDF render: if Stage 2 hasn't run yet, kick it off and
        # have it call _export again once the PDF is ready.
        if not self._pdf_bytes:
            if not self._entries:
                return
            self._ensure_pdf_ready(self._export)
            return
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        count = len(self._entries)
        brands = sorted(set(e.brand for e in self._entries if e.brand))
        parts = sorted(set(e.part_type for e in self._entries if e.part_type))
        brand_str = "_".join(b.replace(" ", "") for b in brands[:3])
        part_str = "_".join(p.replace(" ", "")[:10] for p in parts[:2])
        if len(parts) > 2:
            part_str += f"_+{len(parts) - 2}more"
        filename = f"Barcodes_{brand_str}_{part_str}_{count}items_{date_str}.pdf"
        filename = "".join(c if c.isalnum() or c in "-_.()" else "_" for c in filename)
        path, _ = QFileDialog.getSaveFileName(
            self, t("bcgen_export_pdf"), filename, "PDF Files (*.pdf)"
        )
        if path:
            with open(path, "wb") as f:
                f.write(self._pdf_bytes)
            self._status.setText(f"Saved: {path}")

    def _export_yunprint(self):
        """Save the current entries as a YunPrint Database .txt (tab-
        delimited, UTF-8 BOM) and open the destination folder so the user
        can drag the file into YunPrint's Database dialog."""
        if not self._entries:
            return
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        count = sum(1 for e in self._entries if not e.is_command and e.barcode_text)
        if count == 0:
            QMessageBox.information(
                self, "Export for YunPrint",
                "No item barcodes to export — only command/color barcodes are present.",
            )
            return
        filename = f"yunprint-batch-{count}items-{date_str}.txt"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export for YunPrint", filename,
            "YunPrint Database (*.txt)",
        )
        if not path:
            return
        try:
            saved_path = _gen_svc.export_for_yunprint(self._entries, path)
        except Exception as e:
            QMessageBox.critical(self, "Export for YunPrint", str(e))
            return
        self._status.setText(f"YunPrint file saved: {saved_path}")
        # Open the containing folder so the user can drag the file straight
        # into YunPrint's Database → Select File dialog.
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(saved_path)))
        QMessageBox.information(
            self, "Export for YunPrint",
            f"Saved {count} barcode rows to:\n{saved_path}\n\n"
            "In YunPrint:\n"
            "  1. Open your 50×20mm template.\n"
            "  2. Click Database → set source to .txt → Select File → "
            "choose this file.\n"
            "  3. Make sure 'first line contains the field name' is checked.\n"
            "  4. Confirm — the Sample data preview should show the rows.\n"
            "  5. Click each template field, set Content to 'Database', and "
            "pick the matching column (barcode / model / part_type).\n"
            "  6. Print — one job, all labels.",
        )

    def _print(self):
        # Same lazy-render gate as _export — first click triggers Stage 2.
        if not self._pdf_bytes:
            if not self._entries:
                return
            self._ensure_pdf_ready(self._print)
            return
        tf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tf.write(self._pdf_bytes)
        tf.close()
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(tf.name))

    # ── Retranslate / Refresh ───────────────────────────────────────────────

    def retranslate(self):
        pass  # Labels use t() at build time

    def refresh(self):
        self._populate_combos()
