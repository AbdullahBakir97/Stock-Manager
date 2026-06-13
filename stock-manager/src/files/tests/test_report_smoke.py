"""tests/test_report_smoke.py — every PDF report must generate cleanly.

Seeds a small dataset, generates each report, and asserts:
  * no exception is raised,
  * the PDF has at least one page,
  * no page is blank/near-empty (the pagination-blank-pages regression).

This is what was verified by hand after the pagination, cost_price and arrow
fixes — now it runs automatically.
"""
from __future__ import annotations

import os
import sys
import shutil
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging; logging.disable(logging.CRITICAL)

from PyQt6.QtWidgets import QApplication
_APP = QApplication.instance() or QApplication(sys.argv)

import app.core.database as db_mod


class TestReportSmoke(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp()
        cls._orig = db_mod.DB_PATH
        db_mod.close_all_connections()
        db_mod.DB_PATH = os.path.join(cls._tmp, "report_smoke.db")
        db_mod.init_db()

        # Seed enough rows to push the inventory report onto multiple pages,
        # so the "blank page between full pages" regression would be caught.
        from app.repositories.item_repo import ItemRepository
        repo = ItemRepository()
        for i in range(60):
            repo.add_product(
                brand=("Apple" if i % 2 else "Samsung"),
                name=f"Part {i:02d}", color="Black",
                stock=(i * 7) % 12, barcode=f"SMOKE-{i:03d}",
                min_stock=(0 if i % 3 else 4),
                sell_price=round(9.5 + i, 2),
            )

    @classmethod
    def tearDownClass(cls):
        db_mod.close_all_connections()
        db_mod.DB_PATH = cls._orig
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def _assert_pdf_ok(self, path: str) -> None:
        import fitz
        self.assertTrue(path and os.path.exists(path), f"no PDF produced: {path}")
        doc = fitz.open(path)
        try:
            self.assertGreater(doc.page_count, 0, "PDF has no pages")
            blank = [i + 1 for i in range(doc.page_count)
                     if len(doc[i].get_text().strip()) < 40]
            self.assertEqual(
                blank, [],
                f"blank/near-empty page(s) {blank} in {os.path.basename(path)}",
            )
        finally:
            doc.close()

    def test_all_reports_generate(self):
        from app.services.report_service import ReportService
        svc = ReportService()
        reports = [
            svc.generate_inventory_report,
            svc.generate_low_stock_report,
            svc.generate_summary_report,
            svc.generate_valuation_report,
            svc.generate_audit_sheet,
            svc.generate_transaction_report,
            svc.generate_sales_report,
            svc.generate_scan_invoices_report,
            svc.generate_expiring_report,
            svc.generate_category_performance_report,
            svc.generate_phones_inventory_report,
            svc.generate_phones_sold_report,
        ]
        for fn in reports:
            with self.subTest(report=fn.__name__):
                self._assert_pdf_ok(fn())


if __name__ == "__main__":
    unittest.main()
