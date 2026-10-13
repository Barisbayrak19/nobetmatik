import unittest
import tkinter as tk
import customtkinter as ctk
from pathlib import Path
import tempfile
import shutil

from core.database import Database
from ui.reports_view import ReportsView, ModernReportErrorDialog, ModernReportSuccessDialog


class TestReportsView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ctk.CTk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_reports.db"
        self.db = Database(self.db_path)
        self.db.init_db()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_reports_view_tabs_and_rendering(self):
        view = ReportsView(self.root, db=self.db)
        self.assertEqual(view.current_tab, "duty")

        # Tab geçişleri
        view.switch_tab("timetable")
        self.assertEqual(view.current_tab, "timetable")

        view.switch_tab("attendance")
        self.assertEqual(view.current_tab, "attendance")

        view.switch_tab("duty")
        self.assertEqual(view.current_tab, "duty")

    def test_month_parsing_and_system_info(self):
        view = ReportsView(self.root, db=self.db)
        view.att_month_var.set("Ekim")
        self.assertEqual(view._parse_selected_month_num(), 10)

        view.att_month_var.set("05")
        self.assertEqual(view._parse_selected_month_num(), 5)

        view.att_month_var.set("Ocak")
        self.assertEqual(view._parse_selected_month_num(), 1)

        info = view._get_att_last_exported_info()
        self.assertTrue("Son oluşturulan" in info)

    def test_modern_report_error_dialog(self):
        retried = []

        def on_retry():
            retried.append(True)

        dlg = ModernReportErrorDialog(
            self.root,
            title="PDF OLUŞTURULAMADI",
            message="Belge oluşturulurken bir sorun oluştu.",
            detail="WindowsPath object has no attribute 'split'",
            retry_callback=on_retry
        )

        self.assertFalse(dlg.is_detail_expanded)
        dlg._toggle_detail()
        self.assertTrue(dlg.is_detail_expanded)
        dlg._toggle_detail()
        self.assertFalse(dlg.is_detail_expanded)

        dlg._do_retry()
        self.assertTrue(len(retried) == 1 and retried[0] is True)

    def test_modern_report_success_dialog(self):
        dummy_file = Path(self.temp_dir) / "test_belge.pdf"
        dummy_file.write_text("dummy")

        dlg = ModernReportSuccessDialog(self.root, file_path=dummy_file)
        self.assertEqual(dlg.file_path, dummy_file)
        dlg.destroy()


if __name__ == "__main__":
    unittest.main()
