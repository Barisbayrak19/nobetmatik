"""
Test suite for Category 1 & Category 2 new features:
- Spotlight Search (Ctrl + K)
- KBS Monthly Duty Attendance & Ek Ders Excel Export
- WhatsApp Duty Notice Dialog
- Kiosk TV Mode View
- Undo / Redo Toolbar & Highlights
- Analytics & Fairness Distribution
"""
import unittest
import tempfile
import datetime
from pathlib import Path

from core.database import Database
from core.models import Teacher, Location, Assignment, SchoolInfo, Day
from core.undo_manager import UndoManager
from logic.duty_service import DutyService
from logic.export_service import ExportService


class TestNewSmartFeatures(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.db = Database(str(self.db_path))

        # Günleri Kaydet
        days_data = [
            ("monday", "Pazartesi", 1),
            ("tuesday", "Salı", 2),
            ("wednesday", "Çarşamba", 3),
            ("thursday", "Perşembe", 4),
            ("friday", "Cuma", 5),
        ]
        for d_id, d_name, d_order in days_data:
            self.db.save_day(Day(id=d_id, name=d_name, order_num=d_order, is_active=True))

        # Okul Bilgisi
        self.db.save_school_info(SchoolInfo(
            name="Atatürk Ortaokulu",
            city="İstanbul",
            district="Kadıköy",
            principal_name="Mehmet Özkan",
            installed=True
        ))

        # Öğretmenler
        self.t1 = Teacher(name="Ahmet Yılmaz", branch="Matematik", phone="05551112233")
        self.t2 = Teacher(name="Ayşe Kaya", branch="Türkçe", phone="05554445566")
        self.t3 = Teacher(name="Fatma Demir", branch="Fen Bilimleri", phone="")
        self.db.save_teacher(self.t1)
        self.db.save_teacher(self.t2)
        self.db.save_teacher(self.t3)

        # Nöbet Yerleri
        self.l1 = Location(name="Zemin Kat", capacity=1, order_num=1)
        self.l2 = Location(name="Bahçe", capacity=1, order_num=2)
        self.db.save_location(self.l1)
        self.db.save_location(self.l2)

        self.week_start = "2026-10-19"  # Pazartesi
        # Atamalar
        self.a1 = Assignment(
            week_start=self.week_start,
            day_id="monday",
            location_id=self.l1.id,
            slot_index=0,
            teacher_id=self.t1.id
        )
        self.a2 = Assignment(
            week_start=self.week_start,
            day_id="tuesday",
            location_id=self.l2.id,
            slot_index=0,
            teacher_id=self.t2.id
        )
        self.db.save_assignment(self.a1)
        self.db.save_assignment(self.a2)

        self.undo_mgr = UndoManager()
        self.duty_service = DutyService(self.db, self.undo_mgr)
        self.export_service = ExportService(self.db)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_kbs_duty_attendance_excel_export(self):
        out_file = Path(self.temp_dir.name) / "kbs_puantaj_test.xlsx"
        res = self.export_service.export_monthly_kbs_duty_sheet(2026, 10, out_file)
        self.assertTrue(res.exists())
        self.assertGreater(res.stat().st_size, 1000)

        # openpyxl ile oku ve doğrula
        import openpyxl
        wb = openpyxl.load_workbook(str(res))
        ws = wb.active
        self.assertIn("Nöbet Puantaj", ws.title)
        self.assertIn("ATATÜRK ORTAOKULU", ws["A1"].value)
        self.assertIn("KBS", ws["A2"].value)

        # Öğretmen isimlerini kontrol et
        teacher_names = [ws.cell(row=r, column=2).value for r in range(7, 10)]
        self.assertIn("Ahmet Yılmaz", teacher_names)
        self.assertIn("Ayşe Kaya", teacher_names)

        # 19 Ekim 2026 Pazartesi -> Ahmet Yılmaz Nöbetçi
        col_19_oct = 3 + 19
        row_ahmet = None
        for r in range(7, 10):
            if ws.cell(row=r, column=2).value == "Ahmet Yılmaz":
                row_ahmet = r
                break
        self.assertIsNotNone(row_ahmet)
        cell_val = ws.cell(row=row_ahmet, column=col_19_oct).value
        self.assertEqual(cell_val, "N")

    def test_whatsapp_duty_message_generation(self):
        from ui.whatsapp_dialog import WhatsAppDutyNoticeDialog
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        try:
            dlg = WhatsAppDutyNoticeDialog(root, self.db, self.week_start, initial_teacher_id=self.t1.id)
            self.assertEqual(dlg.sel_teacher_var.get(), "Ahmet Yılmaz")
            single_text = dlg.txt_single.get("1.0", "end-1c")
            self.assertIn("Ahmet Yılmaz", single_text)
            self.assertIn("Pazartesi", single_text)
            self.assertIn("Zemin Kat", single_text)

            group_text = dlg.txt_group.get("1.0", "end-1c")
            self.assertIn("HAFTALIK ÖĞRETMEN NÖBET ÇİZELGESİ", group_text)
            self.assertIn("Ahmet Yılmaz", group_text)
            self.assertIn("Ayşe Kaya", group_text)
            dlg.destroy()
        finally:
            root.destroy()

    def test_undo_manager_integration(self):
        # Başlangıçta can_undo False
        self.assertFalse(self.undo_mgr.can_undo())

        # Bir atama yap
        success = self.duty_service.assign_teacher(self.a1, self.t2.id)
        self.assertTrue(success)
        self.assertTrue(self.undo_mgr.can_undo())
        self.assertEqual(self.undo_mgr.get_undo_description(), "Öğretmen Atama")

        # Geri al
        undo_success = self.undo_mgr.undo()
        self.assertTrue(undo_success)
        self.assertTrue(self.undo_mgr.can_redo())

        # Yeniden uygula
        redo_success = self.undo_mgr.redo()
        self.assertTrue(redo_success)

    def test_spotlight_dialog_search(self):
        from ui.spotlight_dialog import SpotlightDialog
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        try:
            dlg = SpotlightDialog(
                parent=root,
                db=self.db,
                duty_service=self.duty_service,
                current_week_start=self.week_start
            )
            # Arama filtresi: Ahmet
            dlg.search_var.set("Ahmet")
            dlg._search()
            titles = [r.get("title") for r in dlg.filtered_results]
            self.assertIn("Ahmet Yılmaz", titles)

            # Arama filtresi: Bahçe
            dlg.search_var.set("Bahçe")
            dlg._search()
            loc_titles = [r.get("title") for r in dlg.filtered_results]
            self.assertTrue(any("Bahçe" in t for t in loc_titles))

            dlg.destroy()
        finally:
            root.destroy()

    def test_kiosk_view_period_calculation(self):
        from ui.kiosk_view import KioskView
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        try:
            kiosk = KioskView(root, self.db, self.week_start)
            # Saat 08:45 -> 1. Ders içinde
            t_during = datetime.time(8, 45)
            status_during = kiosk._get_current_period_status(t_during)
            self.assertIn("1. DERS", status_during)

            # Saat 09:15 -> Teneffüste (09:10 - 09:25 arası)
            t_break = datetime.time(9, 15)
            status_break = kiosk._get_current_period_status(t_break)
            self.assertIn("TENEFFÜS", status_break)
            self.assertIn("2. Ders", status_break)

            kiosk.destroy()
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
