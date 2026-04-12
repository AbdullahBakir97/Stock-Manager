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

        # Category combo
        self._cat_combo = QComboBox()
        self._cat_combo.setMinimumHeight(28)
        left.addWidget(self._cat_combo)

        # Model list
        self._model_list = QListWidget()
        self._model_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self._model_list.setMaximumHeight(120)
        left.addWidget(self._model_list)

        # Part type list
        self._pt_list = QListWidget()
        self._pt_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self._pt_list.setMaximumHeight(120)
        left.addWidget(self._pt_list)

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
        left.addWidget(self._chk_existing)

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

        action_row.addWidget(self._btn_assign, 1)
        action_row.addWidget(self._btn_export, 1)
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
        self._cat_combo.clear()
        self._cat_combo.addItem(t("disp_all_brands"), None)
        for cat in _cat_repo.get_all_active():
            self._cat_combo.addItem(cat.name_en, cat.id)
        self._cat_combo.currentIndexChanged.connect(self._on_cat_change)
        self._refresh_model_list()
        self._refresh_pt_list()

    def _on_cat_change(self):
        self._refresh_pt_list()

    def _refresh_model_list(self):
        self._model_list.clear()
        for m in _model_repo.get_all():
            from PyQt6.QtWidgets import QListWidgetItem
            it = QListWidgetItem(f"{m.brand} {m.name}")
            it.setData(Qt.ItemDataRole.UserRole, m.id)
            self._model_list.addItem(it)

    def _refresh_pt_list(self):
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

    def _on_scope_change(self):
        is_cat = self._rb_cat.isChecked()
        is_model = self._rb_model.isChecked()
        is_pt = self._rb_pt.isChecked()
        self._cat_combo.setVisible(is_cat or is_pt)
        self._model_list.setVisible(is_model)
        self._pt_list.setVisible(is_pt)

    def _get_scope_params(self) -> dict:
        params: dict = {}
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
        params = self._get_scope_params()
        include_existing = self._chk_existing.isChecked()
        self._entries = _gen_svc.generate_for_scope(
            scope="custom",
            include_existing=include_existing,
            **params,
        )

        if not self._entries:
            self._status.setText(t("bcgen_no_items"))
            self._preview_label.setText(t("bcgen_no_items"))
            self._btn_assign.setEnabled(False)
            self._btn_export.setEnabled(False)
            self._btn_print.setEnabled(False)
            self._kpi_generated.set_value(0, t("bcgen_title"))
            self._kpi_pages.set_value(0, t("bcgen_preview"))
            return

        self._kpi_generated.set_value(len(self._entries), t("bcgen_title"))
        self._status.setText(f"{len(self._entries)} barcodes generated...")

        fmt = "code39" if self._rb_code39.isChecked() else "code128"
        include_cmds = self._chk_commands.isChecked()

        try:
            self._pdf_bytes = _gen_svc.create_pdf(
                self._entries,
                include_commands=include_cmds,
                barcode_format=fmt,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self._render_preview()
        self._btn_assign.setEnabled(True)
        self._btn_export.setEnabled(True)
        self._btn_print.setEnabled(True)
        self._kpi_pages.set_value(len(self._pdf_pages), t("bcgen_preview"))
        self._status.setText(
            f"{len(self._entries)} barcodes · {len(self._pdf_pages)} page(s)"
        )

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
        if not self._pdf_bytes:
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

    def _print(self):
        if not self._pdf_bytes:
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
