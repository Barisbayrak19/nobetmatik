import unittest
import tempfile
import datetime
from pathlib import Path
import tkinter as tk

from core.database import Database
from core.models import Teacher, Location, Assignment, Day, SchoolInfo, SubstitutionAssignment
from logic.export_service import ExportService
from ui.duty_log_dialog import DutyLogDialog


class TestDutyLog(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_nobet.db"
        self.db = Database(self.db_path)
        self.export_service = ExportService(self.db)

        # Temel okul bilgisi
        school = SchoolInfo(
            name="Test Atatürk Ortaokulu",
            city="İzmir",
            district="Konak",
            academic_year="2026-2027",
            principal_name="Mehmet Yılmaz",
            daily_periods=7
        )
        self.db.save_school_info(school)
        self.db.set_setting("vice_principal_name", "Ahmet Kaya")
        self.db.set_setting("first_lesson_start", "08:30")
        self.db.set_setting("duty_start_offset", "30")
        self.db.set_setting("duty_end_offset", "30")

        # Temel Günler (Pazartesi - Cuma)
        days_names = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
        self.days = []
        for i, name in enumerate(days_names):
            d = Day(id=f"day_{i+1}", name=name, order_num=i + 1, is_active=True)
            self.db.save_day(d)
            self.days.append(d)

        # Nöbet yerleri
        self.loc1 = Location(id="loc_1", name="Bahçe", order_num=1)
        self.loc2 = Location(id="loc_2", name="1. Kat", order_num=2)
        self.db.save_location(self.loc1)
        self.db.save_location(self.loc2)

        # Öğretmenler
        self.t1 = Teacher(id="t_1", name="Ali Veli", branch="Matematik")
        self.t2 = Teacher(id="t_2", name="Ayşe Yılmaz", branch="Türkçe")
        self.t3 = Teacher(id="t_3", name="Fatma Demir", branch="Fen Bilimleri")
        self.db.save_teacher(self.t1)
        self.db.save_teacher(self.t2)
        self.db.save_teacher(self.t3)

        # Nöbet ataması (Pazartesi için)
        week_start = "2026-10-19"  # Pazartesi
        a1 = Assignment(id="a_1", week_start=week_start, day_id="day_1", location_id="loc_1", teacher_id="t_1")
        a2 = Assignment(id="a_2", week_start=week_start, day_id="day_1", location_id="loc_2", teacher_id="t_2")
        self.db.save_assignment(a1)
        self.db.save_assignment(a2)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_export_single_day_duty_log_pdf_no_absent(self):
        """Gelmeyen öğretmen olmayan günde tek sayfalık nöbet defteri PDF üretimi."""
        out_pdf = Path(self.temp_dir.name) / "gunluk_nobet_defteri.pdf"
        res = self.export_service.export_daily_duty_log_pdf(
            date_str="2026-10-19",
            output_path=out_pdf,
            custom_notes="Herhangi bir vukuat yoktur.",
            include_full_week=False
        )
        self.assertTrue(res.exists())
        self.assertGreater(res.stat().st_size, 1000)

    def test_export_duty_log_with_substitutions(self):
        """İkame ve devamsızlık bulunan günde nöbet defteri PDF üretimi."""
        # 1 adet ikame ekle
        sub = SubstitutionAssignment(
            id="sub_1",
            date_str="2026-10-19",
            period=2,
            absent_teacher_id="t_3",
            class_name="7-A",
            subject_code="FEN",
            duty_teacher_id="t_1",
            is_ek_ders=True
        )
        self.db.save_substitution(sub)

        out_pdf = Path(self.temp_dir.name) / "nobet_defteri_ikame.pdf"
        res = self.export_service.export_daily_duty_log_pdf(
            date_str="2026-10-19",
            output_path=out_pdf,
            custom_notes="2. ders fen dersi ikame edilmiştir.",
            include_full_week=False
        )
        self.assertTrue(res.exists())
        self.assertGreater(res.stat().st_size, 1000)

    def test_export_weekly_duty_log_booklet(self):
        """Haftalık 5 günlük toplu nöbet defteri kitapçığı üretimi."""
        out_pdf = Path(self.temp_dir.name) / "haftalik_kitapcik.pdf"
        res = self.export_service.export_daily_duty_log_pdf(
            date_str="2026-10-19",
            output_path=out_pdf,
            include_full_week=True
        )
        self.assertTrue(res.exists())
        self.assertGreater(res.stat().st_size, 2000)

    def test_duty_log_dialog_creation(self):
        """DutyLogDialog penceresinin hatasız başlatılması ve bileşenleri."""
        root = tk.Tk()
        root.withdraw()
        try:
            dlg = DutyLogDialog(root, self.db, initial_date="2026-10-19")
            self.assertEqual(dlg.selected_date, datetime.date(2026, 10, 19))
            self.assertTrue(hasattr(dlg, "txt_notes"))
            dlg.destroy()
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
