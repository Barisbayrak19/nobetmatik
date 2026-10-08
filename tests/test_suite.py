"""
Otomatik Test Paketi (Automated Test Suite)
Tüm sistem gereksinimlerini, veri modellerini, servisleri ve dışa aktarımları test eder.
"""
import unittest
import os
import shutil
import tempfile
from pathlib import Path
import datetime

from core.models import SchoolInfo, Day, Location, Teacher, Assignment, TeacherLesson, SubstitutionAssignment, AttendanceRecord
from core.database import Database
from core.undo_manager import UndoManager
from logic.duty_service import DutyService
from logic.auto_scheduler import AutoScheduler
from logic.backup_service import BackupService
from logic.matching_service import MatchingService
from logic.export_service import ExportService
from logic.substitution_service import SubstitutionService
from data.reference_data import (
    REFERENCE_SCHOOL, REFERENCE_DAYS, REFERENCE_LOCATIONS,
    REFERENCE_TEACHERS, REFERENCE_DUTY_TABLE
)

import pymupdf
import openpyxl
from docx import Document

class TestNobetSystem(unittest.TestCase):
    def setUp(self):
        # Her test için izole geçici dizin ve veritabanı
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "test_nobet.db"
        self.backup_dir = self.temp_dir / "backups"
        self.export_dir = self.temp_dir / "exports"

        self.db = Database(self.db_path)
        self.undo_mgr = UndoManager()
        self.duty_service = DutyService(self.db, self.undo_mgr)
        self.backup_service = BackupService(self.db_path, self.backup_dir)
        self.export_service = ExportService(self.db)
        self.sub_service = SubstitutionService(self.db)

        # Referans verilerini ilk kuruluma benzer şekilde yükle
        self._init_reference_data()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _init_reference_data(self):
        # 1. Okul
        school = SchoolInfo(
            name=REFERENCE_SCHOOL["name"],
            city=REFERENCE_SCHOOL["city"],
            district=REFERENCE_SCHOOL["district"],
            academic_year=REFERENCE_SCHOOL["academic_year"],
            principal_name=REFERENCE_SCHOOL["principal_name"],
            duty_rules=REFERENCE_SCHOOL["duty_rules"],
            installed=True
        )
        self.db.save_school_info(school)

        # 2. Günler
        self.days_map = {}
        for d in REFERENCE_DAYS:
            day_obj = Day(name=d["name"], order_num=d["order_num"])
            self.db.save_day(day_obj)
            self.days_map[day_obj.name] = day_obj

        # 3. Nöbet Yerleri
        self.locs_map = {}
        for l in REFERENCE_LOCATIONS:
            loc_obj = Location(name=l["name"], order_num=l["order_num"], capacity=l["capacity"])
            self.db.save_location(loc_obj)
            self.locs_map[loc_obj.name] = loc_obj

        # 4. Öğretmenler
        self.teachers_map = {}
        for t in REFERENCE_TEACHERS:
            t_obj = Teacher(
                name=t["name"],
                branch=t["branch"],
                is_active=t.get("is_active", True),
                notes=t["notes"]
            )
            self.db.save_teacher(t_obj)
            self.teachers_map[t_obj.name] = t_obj

        # 5. Atamalar (2026-09-28)
        self.week_start = "2026-09-28"
        for day_name, loc_dict in REFERENCE_DUTY_TABLE.items():
            day_obj = self.days_map.get(day_name)
            for loc_name, teacher_names in loc_dict.items():
                loc_obj = self.locs_map.get(loc_name)
                for slot_idx, t_name in enumerate(teacher_names):
                    t_obj = self.teachers_map.get(t_name)
                    assign = Assignment(
                        week_start=self.week_start,
                        day_id=day_obj.id,
                        location_id=loc_obj.id,
                        slot_index=slot_idx,
                        teacher_id=t_obj.id if t_obj else None,
                        fixed=False
                    )
                    self.db.save_assignment(assign)

        # 6. Ders programlarını yükle
        self.sub_service.import_timetables_from_json()

    # 1. test_first_install_import
    def test_first_install_import(self):
        school = self.db.get_school_info()
        self.assertTrue(school.installed)
        self.assertEqual(school.name, "Şehit Kadir Altuntaş Cumhuriyet Ortaokulu")
        self.assertEqual(school.district, "Torbalı")
        self.assertEqual(school.principal_name, "Salahattin GÜNEK")

        days = self.db.get_days()
        self.assertEqual(len(days), 5)

        locs = self.db.get_locations()
        self.assertEqual(len(locs), 6)
        bahce1 = next((l for l in locs if l.name == "BAHÇE 1"), None)
        bahce2 = next((l for l in locs if l.name == "BAHÇE 2"), None)
        self.assertIsNotNone(bahce1)
        self.assertIsNotNone(bahce2)
        self.assertEqual(bahce1.capacity, 1)
        self.assertEqual(bahce2.capacity, 1)

        teachers = self.db.get_teachers()
        self.assertEqual(len(teachers), len(REFERENCE_TEACHERS))
        active_teachers = self.db.get_teachers(active_only=True)
        self.assertEqual(len(active_teachers), 30)

        assignments = self.db.get_assignments_for_week(self.week_start)
        self.assertEqual(len(assignments), 30)

    # 2. test_teacher_create
    def test_teacher_create(self):
        new_teacher = Teacher(
            name="KEMAL ATATÜRK",
            branch="Tarih",
            unavailable_days=["Cuma"],
            notes="Test Öğretmeni"
        )
        self.db.save_teacher(new_teacher)

        retrieved = self.db.get_teacher_by_id(new_teacher.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "KEMAL ATATÜRK")
        self.assertEqual(retrieved.branch, "Tarih")
        self.assertEqual(retrieved.unavailable_days, ["Cuma"])

    # 3. test_teacher_edit
    def test_teacher_edit(self):
        teachers = self.db.get_teachers()
        t = teachers[0]
        t.name = "DÜZENLENMİŞ İSİM"
        t.branch = "Fizik"
        t.is_active = False
        self.db.save_teacher(t)

        updated = self.db.get_teacher_by_id(t.id)
        self.assertEqual(updated.name, "DÜZENLENMİŞ İSİM")
        self.assertEqual(updated.branch, "Fizik")
        self.assertFalse(updated.is_active)

    # 4. test_teacher_delete
    def test_teacher_delete(self):
        t = Teacher(name="SİLİNECEK ÖĞRETMEN", branch="Resim")
        self.db.save_teacher(t)
        self.assertIsNotNone(self.db.get_teacher_by_id(t.id))

        self.db.delete_teacher(t.id)
        self.assertIsNone(self.db.get_teacher_by_id(t.id))

    # 5. test_location_create
    def test_location_create(self):
        loc = Location(name="SPOR SALONU", order_num=6, capacity=1)
        self.db.save_location(loc)

        retrieved = self.db.get_location_by_id(loc.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "SPOR SALONU")
        self.assertEqual(retrieved.capacity, 1)

    # 6. test_assignment_create
    def test_assignment_create(self):
        day = self.days_map["Pazartesi"]
        loc = self.locs_map["1. KAT"]
        assign = Assignment(
            week_start="2026-10-05",
            day_id=day.id,
            location_id=loc.id,
            slot_index=0,
            teacher_id=None
        )
        self.db.save_assignment(assign)

        retrieved = self.db.get_assignment_by_id(assign.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.week_start, "2026-10-05")

    # 7. test_assignment_move (Boş hücreye taşıma)
    def test_assignment_move(self):
        day_pzt = self.days_map["Pazartesi"]
        loc_1 = self.locs_map["1. KAT"]
        day_sal = self.days_map["Salı"]

        # Boş bir hedef slot oluştur (veya mevcut atamayı al)
        assign_sal = Assignment(
            week_start=self.week_start,
            day_id=day_sal.id,
            location_id=loc_1.id,
            slot_index=0,
            teacher_id=None
        )
        self.db.save_assignment(assign_sal)

        # Kaynak: Pazartesi 1. KAT (Mehmet Beydilli atanmış)
        matrix = self.duty_service.get_grid_matrix(self.week_start)
        src_assign = matrix["assignments"][(day_pzt.id, loc_1.id, 0)]
        original_teacher_id = src_assign.teacher_id
        self.assertIsNotNone(original_teacher_id)

        # Boş hücreye taşı
        success = self.duty_service.move_or_swap(
            week_start=self.week_start,
            source_day_id=day_pzt.id,
            source_loc_id=loc_1.id,
            source_slot=0,
            target_day_id=day_sal.id,
            target_loc_id=loc_1.id,
            target_slot=0
        )
        self.assertTrue(success)

        # Kontrol: Kaynak artık boş olmalı, hedef original_teacher_id olmalı
        matrix_after = self.duty_service.get_grid_matrix(self.week_start)
        src_after = matrix_after["assignments"][(day_pzt.id, loc_1.id, 0)]
        tgt_after = matrix_after["assignments"][(day_sal.id, loc_1.id, 0)]

        self.assertIsNone(src_after.teacher_id)
        self.assertEqual(tgt_after.teacher_id, original_teacher_id)

    # 8. test_assignment_swap (Dolu hücreye taşıma = TAKAS)
    def test_assignment_swap(self):
        day_pzt = self.days_map["Pazartesi"]
        day_sal = self.days_map["Salı"]
        loc_1 = self.locs_map["1. KAT"]

        matrix = self.duty_service.get_grid_matrix(self.week_start)
        pzt_assign = matrix["assignments"][(day_pzt.id, loc_1.id, 0)]
        sal_assign = matrix["assignments"][(day_sal.id, loc_1.id, 0)]

        teacher_pzt = pzt_assign.teacher_id
        teacher_sal = sal_assign.teacher_id
        self.assertIsNotNone(teacher_pzt)
        self.assertIsNotNone(teacher_sal)
        self.assertNotEqual(teacher_pzt, teacher_sal)

        # Dolu hücreye taşı -> TAKAS (SWAP)
        success = self.duty_service.move_or_swap(
            week_start=self.week_start,
            source_day_id=day_pzt.id,
            source_loc_id=loc_1.id,
            source_slot=0,
            target_day_id=day_sal.id,
            target_loc_id=loc_1.id,
            target_slot=0
        )
        self.assertTrue(success)

        # Kontrol: Öğretmenler yer değiştirmiş olmalı!
        matrix_after = self.duty_service.get_grid_matrix(self.week_start)
        pzt_after = matrix_after["assignments"][(day_pzt.id, loc_1.id, 0)]
        sal_after = matrix_after["assignments"][(day_sal.id, loc_1.id, 0)]

        self.assertEqual(pzt_after.teacher_id, teacher_sal)
        self.assertEqual(sal_after.teacher_id, teacher_pzt)

    # 9. test_assignment_same_cell (Aynı hücreye bırakma = NO-OP)
    def test_assignment_same_cell(self):
        day_pzt = self.days_map["Pazartesi"]
        loc_1 = self.locs_map["1. KAT"]

        matrix = self.duty_service.get_grid_matrix(self.week_start)
        assign = matrix["assignments"][(day_pzt.id, loc_1.id, 0)]
        original_teacher = assign.teacher_id

        # Kendi hücresine bırak
        success = self.duty_service.move_or_swap(
            week_start=self.week_start,
            source_day_id=day_pzt.id,
            source_loc_id=loc_1.id,
            source_slot=0,
            target_day_id=day_pzt.id,
            target_loc_id=loc_1.id,
            target_slot=0
        )
        self.assertTrue(success)

        matrix_after = self.duty_service.get_grid_matrix(self.week_start)
        assign_after = matrix_after["assignments"][(day_pzt.id, loc_1.id, 0)]
        self.assertEqual(assign_after.teacher_id, original_teacher)

    # 10. test_fixed_assignment (Sabit nöbet koruması)
    def test_fixed_assignment(self):
        day_pzt = self.days_map["Pazartesi"]
        day_car = self.days_map["Çarşamba"]
        loc_1 = self.locs_map["1. KAT"]

        matrix = self.duty_service.get_grid_matrix(self.week_start)
        assign = matrix["assignments"][(day_pzt.id, loc_1.id, 0)]

        # Sabitle
        self.duty_service.toggle_fixed(assign.id)
        fixed_assign = self.db.get_assignment_by_id(assign.id)
        self.assertTrue(fixed_assign.fixed)

        # Sabit hücreyi taşımaya çalış -> Başarısız olmalı
        fail_move = self.duty_service.move_or_swap(
            week_start=self.week_start,
            source_day_id=day_pzt.id,
            source_loc_id=loc_1.id,
            source_slot=0,
            target_day_id=day_car.id,
            target_loc_id=loc_1.id,
            target_slot=0
        )
        self.assertFalse(fail_move)

        # Kilidi kaldır
        self.duty_service.toggle_fixed(assign.id)
        unfixed_assign = self.db.get_assignment_by_id(assign.id)
        self.assertFalse(unfixed_assign.fixed)

    # 11. test_save_load
    def test_save_load(self):
        self.db.set_setting("app_theme", "dark")
        val = self.db.get_setting("app_theme")
        self.assertEqual(val, "dark")

        # Yeni bağlantı ile tekrar oku
        new_db = Database(self.db_path)
        self.assertEqual(new_db.get_setting("app_theme"), "dark")

    # 12. test_backup_restore
    def test_backup_restore(self):
        backup_file = self.backup_service.create_backup()
        self.assertTrue(backup_file.exists())

        # Mevcut veritabanında bir değişiklik yapalım (Tüm öğretmenleri silelim)
        for t in self.db.get_teachers():
            self.db.delete_teacher(t.id)
        self.assertEqual(len(self.db.get_teachers()), 0)

        # Yedekten geri yükle
        self.backup_service.restore_backup(backup_file)

        # Kontrol: Öğretmenler geri gelmiş olmalı
        teachers_restored = self.db.get_teachers()
        self.assertGreater(len(teachers_restored), 0)
        self.assertEqual(len(teachers_restored), len(REFERENCE_TEACHERS))

    # 13. test_import_matching
    def test_import_matching(self):
        existing_names = [t["name"] for t in REFERENCE_TEACHERS]

        # 1. Kısaltma eşleşmesi: "M.BEYDİLLİ" -> "MEHMET BEYDİLLİ"
        matches1 = MatchingService.find_best_matches("M.BEYDİLLİ", existing_names)
        self.assertGreater(len(matches1), 0)
        self.assertEqual(matches1[0][0], "MEHMET BEYDİLLİ")
        self.assertGreaterEqual(matches1[0][1], 0.85)

        # 2. İsim benzerliği: "İlknur Akbaş" -> "İLKNUR AKBAŞ UZUN"
        matches2 = MatchingService.find_best_matches("İlknur Akbaş", existing_names)
        self.assertGreater(len(matches2), 0)
        self.assertEqual(matches2[0][0], "İLKNUR AKBAŞ UZUN")

    # 14. test_pdf_export
    def test_pdf_export(self):
        pdf_path = self.export_dir / "test_duty.pdf"
        res_path = self.export_service.export_pdf(self.week_start, pdf_path)
        self.assertTrue(res_path.exists())
        self.assertGreater(res_path.stat().st_size, 1000)

        # PyMuPDF ile içeriği doğrula
        doc = pymupdf.open(str(res_path))
        self.assertGreater(len(doc), 0)
        page_text = doc[0].get_text()
        self.assertIn("HAFTALIK", page_text.upper())
        self.assertIn("28.09.2026", page_text)
        today_str = datetime.date.today().strftime("%d.%m.%Y")
        self.assertIn(today_str, page_text)
        doc.close()

    # 15. test_excel_export
    def test_excel_export(self):
        xlsx_path = self.export_dir / "test_duty.xlsx"
        res_path = self.export_service.export_excel(self.week_start, xlsx_path)
        self.assertTrue(res_path.exists())

        wb = openpyxl.load_workbook(res_path)
        self.assertIn("Haftalık Nöbet Çizelgesi", wb.sheetnames)
        ws = wb["Haftalık Nöbet Çizelgesi"]
        self.assertIn("KAYMAKAMLIĞI", str(ws["A2"].value))
        self.assertIn("28.09.2026", str(ws["A5"].value))
        today_str = datetime.date.today().strftime("%d.%m.%Y")
        # İmzadan hemen önceki satırda bugünün tarihi var mı?
        found_today = any(today_str in str(cell.value) for row in ws.iter_rows() for cell in row if cell.value)
        self.assertTrue(found_today)

    # 16. test_word_export
    def test_word_export(self):
        docx_path = self.export_dir / "test_duty.docx"
        res_path = self.export_service.export_word(self.week_start, docx_path)
        self.assertTrue(res_path.exists())

        doc = Document(str(res_path))
        self.assertGreater(len(doc.tables), 0)
        full_text = "\n".join([p.text for p in doc.paragraphs])
        self.assertIn("HAFTALIK NÖBET ÇİZELGESİ", full_text)
        self.assertIn("28.09.2026", full_text)
        today_str = datetime.date.today().strftime("%d.%m.%Y")
        self.assertIn(today_str, full_text)

    # 17. test_csv_export
    def test_csv_export(self):
        csv_path = self.export_dir / "test_duty.csv"
        res_path = self.export_service.export_csv(self.week_start, csv_path)
        self.assertTrue(res_path.exists())
        with open(res_path, "r", encoding="utf-8-sig") as f:
            content = f.read()
            self.assertIn("HAFTALIK NÖBET ÇİZELGESİ", content)
            self.assertIn("28.09.2026", content)
            today_str = datetime.date.today().strftime("%d.%m.%Y")
            self.assertIn(today_str, content)

    # 18. test_html_export
    def test_html_export(self):
        html_path = self.export_dir / "test_duty.html"
        res_path = self.export_service.export_html(self.week_start, html_path)
        self.assertTrue(res_path.exists())
        with open(res_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("<table", content)
            self.assertIn("Şehit Kadir Altuntaş Cumhuriyet Ortaokulu", content)
            self.assertIn("28.09.2026", content)
            today_str = datetime.date.today().strftime("%d.%m.%Y")
            self.assertIn(today_str, content)

    # 19. test_undo_redo
    def test_undo_redo(self):
        day_pzt = self.days_map["Pazartesi"]
        day_sal = self.days_map["Salı"]
        loc_1 = self.locs_map["1. KAT"]

        # Takas işlemi yap
        self.duty_service.move_or_swap(
            week_start=self.week_start,
            source_day_id=day_pzt.id,
            source_loc_id=loc_1.id,
            source_slot=0,
            target_day_id=day_sal.id,
            target_loc_id=loc_1.id,
            target_slot=0
        )
        self.assertTrue(self.undo_mgr.can_undo())

        # Geri al (Undo)
        undo_res = self.undo_mgr.undo()
        self.assertTrue(undo_res)
        self.assertTrue(self.undo_mgr.can_redo())

        # İleri al (Redo)
        redo_res = self.undo_mgr.redo()
        self.assertTrue(redo_res)

    # 20. test_auto_scheduler
    def test_auto_scheduler(self):
        scheduler = AutoScheduler(self.db)
        # Yeni bir hafta için dağıtım üret
        new_week = "2026-10-05"
        plan, report = scheduler.generate_schedule(new_week, avoid_consecutive_days=True)
        self.assertEqual(len(plan), 30)
        self.assertGreater(report.fairness_score, 0)
        # Planı uygula
        scheduler.apply_schedule(plan)
        saved = self.db.get_assignments_for_week(new_week)
        self.assertEqual(len(saved), 30)

    # 21. test_shift_schedule_by_day
    def test_shift_schedule_by_day(self):
        day_pzt = self.days_map["Pazartesi"]
        day_sal = self.days_map["Salı"]
        loc_1 = self.locs_map["1. KAT"]

        matrix_before = self.duty_service.get_grid_matrix(self.week_start)
        pzt_teacher_before = matrix_before["assignments"][(day_pzt.id, loc_1.id, 0)].teacher_id

        # Günleri 1 gün ileri kaydır (Pzt -> Sal)
        success = self.duty_service.shift_schedule(self.week_start, shift_type="day", steps=1, preserve_fixed=True)
        self.assertTrue(success)

        # Salı günündeki 1. Kat nöbetçisi artık önceki Pazartesi'nin nöbetçisi olmalı
        matrix_after = self.duty_service.get_grid_matrix(self.week_start)
        sal_teacher_after = matrix_after["assignments"][(day_sal.id, loc_1.id, 0)].teacher_id
        self.assertEqual(sal_teacher_after, pzt_teacher_before)

        # Undo testi
        self.undo_mgr.undo()
        matrix_undone = self.duty_service.get_grid_matrix(self.week_start)
        self.assertEqual(matrix_undone["assignments"][(day_pzt.id, loc_1.id, 0)].teacher_id, pzt_teacher_before)

    # 22. test_shift_schedule_by_location
    def test_shift_schedule_by_location(self):
        day_pzt = self.days_map["Pazartesi"]
        loc_1 = self.locs_map["1. KAT"]
        loc_2 = self.locs_map["2. KAT"]

        matrix_before = self.duty_service.get_grid_matrix(self.week_start)
        loc1_teacher_before = matrix_before["assignments"][(day_pzt.id, loc_1.id, 0)].teacher_id

        # Yerleri 1 sıra kaydır (1. Kat -> 2. Kat)
        success = self.duty_service.shift_schedule(self.week_start, shift_type="location", steps=1, preserve_fixed=True)
        self.assertTrue(success)

        matrix_after = self.duty_service.get_grid_matrix(self.week_start)
        loc2_teacher_after = matrix_after["assignments"][(day_pzt.id, loc_2.id, 0)].teacher_id
        self.assertEqual(loc2_teacher_after, loc1_teacher_before)

    # 23. test_copy_week_to_next
    def test_copy_week_to_next(self):
        next_week = "2026-10-05"
        success = self.duty_service.copy_week_to_next(self.week_start, next_week, shift_days=1)
        self.assertTrue(success)

        assignments_next = self.db.get_assignments_for_week(next_week)
        self.assertEqual(len(assignments_next), 30)

    # 24. test_timetable_import_and_queries
    def test_timetable_import_and_queries(self):
        t = self.teachers_map["MEHMET BEYDİLLİ"]
        lessons = self.sub_service.get_teacher_schedule(t.id, "Pazartesi")
        self.assertEqual(len(lessons), 7)
        for i, l in enumerate(lessons, 1):
            self.assertEqual(l.period, i)

        # Tüm 5 günün dersleri mevcut olmalı
        all_lessons = self.db.get_teacher_lessons(t.id)
        self.assertEqual(len(all_lessons), 35)

    # 25. test_teacher_free_periods
    def test_teacher_free_periods(self):
        t = self.teachers_map["MEHMET BEYDİLLİ"]
        free_p = self.sub_service.get_teacher_free_periods(t.id, "Pazartesi")
        self.assertIsInstance(free_p, list)
        for p in free_p:
            self.assertIn(p, range(1, 8))

    # 26. test_substitution_candidate_search
    def test_substitution_candidate_search(self):
        # Pazartesi günü nöbetçileri arasında aday arama
        absent_t = self.teachers_map["MEHMET BEYDİLLİ"]
        candidates = self.sub_service.find_candidates_for_period(
            self.week_start, "Pazartesi", period=1, absent_teacher_id=absent_t.id
        )
        self.assertGreater(len(candidates), 0)
        # Gelmeyen öğretmenin kendisi adaylar arasında olmamalı
        candidate_ids = [c["teacher"].id for c in candidates]
        self.assertNotIn(absent_t.id, candidate_ids)

    # 27. test_substitution_auto_matching_fairness
    def test_substitution_auto_matching_fairness(self):
        # Pazartesi günü dersi olan bir öğretmeni seç
        absent_t = self.teachers_map["İLKNUR AKBAŞ UZUN"]
        date_str = "2026-09-28"
        subs = self.sub_service.auto_assign_substitutions(
            date_str=date_str,
            day_name="Pazartesi",
            absent_teacher_id=absent_t.id,
            week_start=self.week_start
        )
        self.assertGreater(len(subs), 0)
        # Atanan nöbetçilerin o saatte boş olduğunu doğrula
        for s in subs:
            if s.duty_teacher_id:
                duty_lessons = self.sub_service.get_teacher_schedule(s.duty_teacher_id, "Pazartesi")
                duty_at_period = next((l for l in duty_lessons if l.period == s.period), None)
                self.assertIsNotNone(duty_at_period)
                self.assertTrue(duty_at_period.is_free)

    # 28. test_substitution_save_and_export
    def test_substitution_save_and_export(self):
        absent_t = self.teachers_map["LATİF CANDAN"]
        date_str = "2026-09-30"
        subs = self.sub_service.auto_assign_substitutions(
            date_str=date_str,
            day_name="Çarşamba",
            absent_teacher_id=absent_t.id,
            week_start=self.week_start
        )
        self.assertGreater(len(subs), 0)

        # Veritabanına kaydet
        for s in subs:
            self.db.save_substitution(s)

        loaded_subs = self.db.get_substitutions_for_date(date_str)
        self.assertEqual(len(loaded_subs), len(subs))

        # PDF Çıktısı Testi
        pdf_path = self.export_dir / "substitution_test.pdf"
        out_pdf = self.sub_service.export_substitution_pdf(
            output_path=str(pdf_path),
            date_str=date_str,
            day_name="Çarşamba",
            absent_teacher=absent_t,
            assignments=subs
        )
        self.assertTrue(os.path.exists(out_pdf))
        self.assertGreater(os.path.getsize(out_pdf), 1000)

        # HTML Çıktısı Testi
        html_path = self.export_dir / "substitution_test.html"
        out_html = self.sub_service.export_substitution_html(
            output_path=str(html_path),
            date_str=date_str,
            day_name="Çarşamba",
            absent_teacher=absent_t,
            assignments=subs
        )
        self.assertTrue(os.path.exists(out_html))
        self.assertGreater(os.path.getsize(out_html), 500)

    # 29. test_fair_distribution_no_overload
    def test_fair_distribution_no_overload(self):
        # Pazartesi günü dersi olan bir öğretmeni seç
        absent_t = self.teachers_map["İLKNUR AKBAŞ UZUN"]
        date_str = "2026-09-28"
        subs = self.sub_service.auto_assign_substitutions(
            date_str=date_str,
            day_name="Pazartesi",
            absent_teacher_id=absent_t.id,
            week_start=self.week_start,
            teachers_per_lesson=1
        )
        self.assertGreater(len(subs), 0)

        # Görevlendirilen nöbetçilerin sayısını hesapla
        assigned_counts: Dict[str, int] = {}
        for s in subs:
            if s.duty_teacher_id:
                assigned_counts[s.duty_teacher_id] = assigned_counts.get(s.duty_teacher_id, 0) + 1

        # Eğer birden fazla boş nöbetçi varsa, hiçbir nöbetçiye tüm dersler yığılmamalıdır
        if len(assigned_counts) > 1:
            max_assigned = max(assigned_counts.values())
            min_assigned = min(assigned_counts.values())
            # Fark en fazla 1 olmalı (ideal adalet)
            self.assertLessEqual(max_assigned - min_assigned, 1)

    # 30. test_multi_duty_teachers_per_lesson
    def test_multi_duty_teachers_per_lesson(self):
        absent_t = self.teachers_map["MEHMET BEYDİLLİ"]
        date_str = "2026-09-28"
        # Her derse 2 nöbetçi ata
        subs = self.sub_service.auto_assign_substitutions(
            date_str=date_str,
            day_name="Pazartesi",
            absent_teacher_id=absent_t.id,
            week_start=self.week_start,
            teachers_per_lesson=2
        )
        self.assertGreater(len(subs), 0)

        # Veritabanına kaydet
        for s in subs:
            self.db.save_substitution(s)

        loaded = self.db.get_substitutions_for_date(date_str)
        self.assertEqual(len(loaded), len(subs))

        # PDF ve HTML oluşturulmasını test et
        pdf_path = self.export_dir / "multi_sub_test.pdf"
        out_pdf = self.sub_service.export_substitution_pdf(
            output_path=str(pdf_path),
            date_str=date_str,
            day_name="Pazartesi",
            absent_teacher=absent_t,
            assignments=subs
        )
        self.assertTrue(os.path.exists(out_pdf))
        self.assertGreater(os.path.getsize(out_pdf), 1000)

        html_path = self.export_dir / "multi_sub_test.html"
        out_html = self.sub_service.export_substitution_html(
            output_path=str(html_path),
            date_str=date_str,
            day_name="Pazartesi",
            absent_teacher=absent_t,
            assignments=subs
        )
        self.assertTrue(os.path.exists(out_html))
        self.assertGreater(os.path.getsize(out_html), 500)

    # 31. test_same_branch_priority_and_ek_ders
    def test_same_branch_priority_and_ek_ders(self):
        # absent teacher
        absent_t = Teacher(id="t_absent_math", name="Ali Matematikçi", branch="Matematik", is_active=True)
        # duty teacher 1: Türkçe
        duty_t1 = Teacher(id="t_duty_turk", name="Veli Türkçeci", branch="Türkçe", is_active=True)
        # duty teacher 2: Matematik (Aynı branş!)
        duty_t2 = Teacher(id="t_duty_math", name="Ayşe Matematikçi", branch="İlköğretim Matematik", is_active=True)

        self.db.save_teacher(absent_t)
        self.db.save_teacher(duty_t1)
        self.db.save_teacher(duty_t2)

        # Absent teacher has a lesson at period 3
        self.db.save_teacher_lessons([
            TeacherLesson(teacher_id=absent_t.id, day_name="Pazartesi", period=3, class_name="7-A", subject_code="MAT", is_free=False)
        ])

        # Both duty teachers are on duty on an isolated week
        test_week = "2026-10-12"
        day_pzt = next(d for d in self.db.get_days() if d.name == "Pazartesi")
        loc1 = self.db.get_locations()[0]
        loc2 = self.db.get_locations()[1]
        self.db.save_assignment(Assignment(week_start=test_week, day_id=day_pzt.id, location_id=loc1.id, teacher_id=duty_t1.id))
        self.db.save_assignment(Assignment(week_start=test_week, day_id=day_pzt.id, location_id=loc2.id, teacher_id=duty_t2.id))

        # Both are free at period 3 (no lessons)
        subs = self.sub_service.auto_assign_substitutions(
            date_str="2026-10-12",
            day_name="Pazartesi",
            absent_teacher_id=absent_t.id,
            week_start=test_week,
            teachers_per_lesson=1
        )

        self.assertGreaterEqual(len(subs), 1)
        # Matematik branşındaki öğretmen öncelikli atanmalı ve is_ek_ders=True olmalıdır
        primary_sub = next((s for s in subs if s.duty_teacher_id == duty_t2.id), None)
        self.assertIsNotNone(primary_sub)
        self.assertTrue(primary_sub.is_ek_ders)
        self.assertIn("Ek Ders", primary_sub.notes)

    # 32. test_workload_sharing_idle_duty_teachers
    def test_workload_sharing_idle_duty_teachers(self):
        absent_t = Teacher(id="t_absent_idle", name="Gelmeyen Öğretmen", branch="Fen Bilimleri", is_active=True)
        duty_t1 = Teacher(id="t_duty_fen1", name="Nöbetçi Fen 1", branch="Fen Bilimleri", is_active=True)
        duty_t2 = Teacher(id="t_duty_sosyal", name="Nöbetçi Sosyal", branch="Sosyal Bilgiler", is_active=True)

        self.db.save_teacher(absent_t)
        self.db.save_teacher(duty_t1)
        self.db.save_teacher(duty_t2)

        self.db.save_teacher_lessons([
            TeacherLesson(teacher_id=absent_t.id, day_name="Salı", period=2, class_name="6-B", subject_code="FEN", is_free=False)
        ])

        test_week = "2026-10-19"
        day_sal = next(d for d in self.db.get_days() if d.name == "Salı")
        loc1 = self.db.get_locations()[0]
        loc2 = self.db.get_locations()[1]
        self.db.save_assignment(Assignment(week_start=test_week, day_id=day_sal.id, location_id=loc1.id, teacher_id=duty_t1.id))
        self.db.save_assignment(Assignment(week_start=test_week, day_id=day_sal.id, location_id=loc2.id, teacher_id=duty_t2.id))

        # 1. teachers_per_lesson=2 olduğunda iki nöbetçi de aynı derse atanabilmelidir
        subs = self.sub_service.auto_assign_substitutions(
            date_str="2026-10-20",
            day_name="Salı",
            absent_teacher_id=absent_t.id,
            week_start=test_week,
            teachers_per_lesson=2
        )

        assigned_ids = [s.duty_teacher_id for s in subs]
        self.assertIn(duty_t1.id, assigned_ids)
        self.assertIn(duty_t2.id, assigned_ids)
        self.assertEqual(len(subs), 2)

        # 2. Birden fazla ders olduğunda nöbetçilere adil dağıtım (iş yükü paylaşımı)
        absent_multi = Teacher(id="t_absent_multi", name="Gelmeyen 2", branch="Beden Eğitimi", is_active=True)
        duty_a = Teacher(id="t_duty_a", name="Nöbetçi A", branch="Türkçe", is_active=True)
        duty_b = Teacher(id="t_duty_b", name="Nöbetçi B", branch="Sosyal Bilgiler", is_active=True)
        self.db.save_teacher(absent_multi)
        self.db.save_teacher(duty_a)
        self.db.save_teacher(duty_b)
        self.db.save_teacher_lessons([
            TeacherLesson(teacher_id=absent_multi.id, day_name="Salı", period=1, class_name="5-A", subject_code="BED", is_free=False),
            TeacherLesson(teacher_id=absent_multi.id, day_name="Salı", period=3, class_name="6-A", subject_code="BED", is_free=False),
        ])
        test_week_2 = "2026-10-26"
        self.db.save_assignment(Assignment(week_start=test_week_2, day_id=day_sal.id, location_id=loc1.id, teacher_id=duty_a.id))
        self.db.save_assignment(Assignment(week_start=test_week_2, day_id=day_sal.id, location_id=loc2.id, teacher_id=duty_b.id))
        subs_fair = self.sub_service.auto_assign_substitutions(
            date_str="2026-10-27",
            day_name="Salı",
            absent_teacher_id=absent_multi.id,
            week_start=test_week_2,
            teachers_per_lesson=1
        )
        fair_duty_ids = {s.duty_teacher_id for s in subs_fair}
        self.assertIn(duty_a.id, fair_duty_ids)
        self.assertIn(duty_b.id, fair_duty_ids)
        self.assertEqual(len(subs_fair), 2)

    # 33. test_attendance_records_crud_and_auto_logging
    def test_attendance_records_crud_and_auto_logging(self):
        rec1 = AttendanceRecord(
            date_str="2026-09-28",
            teacher_id="t1",
            teacher_name="Ahmet Yılmaz",
            branch="Matematik",
            status="Raporlu",
            periods_missed="1, 2, 3 (3 Saat)",
            notes="Boş ders dolduruldu"
        )
        rec2 = AttendanceRecord(
            date_str="2026-09-29",
            teacher_id="t2",
            teacher_name="Fatma Demir",
            branch="Türkçe",
            status="İzinli",
            periods_missed="Tüm Gün",
            notes="Sevkli/İzinli"
        )
        rec3 = AttendanceRecord(
            date_str="2026-10-05",
            teacher_id="t1",
            teacher_name="Ahmet Yılmaz",
            branch="Matematik",
            status="Görevli",
            periods_missed="Tüm Gün",
            notes="İlçe MEM Görevlendirme"
        )

        self.db.save_attendance_record(rec1)
        self.db.save_attendance_record(rec2)
        self.db.save_attendance_record(rec3)

        # 1. Query by month
        sep_recs = self.db.get_attendance_records(month_str="2026-09")
        self.assertEqual(len(sep_recs), 2)
        oct_recs = self.db.get_attendance_records(month_str="2026-10")
        self.assertEqual(len(oct_recs), 1)

        # 2. Query by teacher
        t1_recs = self.db.get_attendance_records(teacher_id="t1")
        self.assertEqual(len(t1_recs), 2)

        # 3. Query by exact date
        d_recs = self.db.get_attendance_records(date_str="2026-09-28")
        self.assertEqual(len(d_recs), 1)
        self.assertEqual(d_recs[0].teacher_name, "Ahmet Yılmaz")

        # 4. Export to Excel and PDF
        excel_path = self.export_dir / "attendance_test.xlsx"
        pdf_path = self.export_dir / "attendance_test.pdf"

        out_excel = self.export_service.export_attendance_excel(sep_recs, excel_path)
        self.assertTrue(os.path.exists(out_excel))
        self.assertGreater(os.path.getsize(out_excel), 1000)

        out_pdf = self.export_service.export_attendance_pdf(sep_recs, pdf_path)
        self.assertTrue(os.path.exists(out_pdf))
        self.assertGreater(os.path.getsize(out_pdf), 1000)

    # 34. test_attendance_slip_and_lessons_persistence
    def test_attendance_slip_and_lessons_persistence(self):
        rec = AttendanceRecord(
            date_str="2026-09-30",
            teacher_id="t_test_slip",
            teacher_name="Zeynep Kaya",
            branch="Fen Bilimleri",
            status="Raporlu",
            periods_missed="1, 2, 3",
            lessons_missed="5-A (FEN), 6-B (FEN)",
            slip_path="exports/slips/Gorevlendirme_2026-09-30_Zeynep_Kaya.pdf",
            notes="Grip teşhisi"
        )
        self.db.save_attendance_record(rec)

        loaded = self.db.get_attendance_records(teacher_id="t_test_slip")
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].lessons_missed, "5-A (FEN), 6-B (FEN)")
        self.assertEqual(loaded[0].slip_path, "exports/slips/Gorevlendirme_2026-09-30_Zeynep_Kaya.pdf")

        # Test exports with lessons_missed
        excel_path = self.export_dir / "attendance_slip_test.xlsx"
        pdf_path = self.export_dir / "attendance_slip_test.pdf"
        self.export_service.export_attendance_excel(loaded, excel_path)
        self.export_service.export_attendance_pdf(loaded, pdf_path)
        self.assertTrue(os.path.exists(excel_path))
        self.assertTrue(os.path.exists(pdf_path))

    # 35. test_quick_shift_and_settings
    def test_quick_shift_and_settings(self):
        from ui.shift_dialog import execute_shift

        # Save app settings
        self.db.set_setting("last_shift_mode", "day_forward")
        self.db.set_setting("last_shift_preserve", "1")
        self.assertEqual(self.db.get_setting("last_shift_mode"), "day_forward")
        self.assertEqual(self.db.get_setting("last_shift_preserve"), "1")

        # Execute shift via execute_shift helper
        msg = execute_shift(self.duty_service, self.week_start, "day_forward", preserve_fixed=True)
        self.assertIn("kaydırıldı", msg.lower())

    # 36. test_shift_with_fixed_assignment_no_duplicates
    def test_shift_with_fixed_assignment_no_duplicates(self):
        # Perşembe BAHÇE 1'i sabit yap
        day_per = self.days_map["Perşembe"]
        loc_b1 = self.locs_map["BAHÇE 1"]
        assignments = self.db.get_assignments_for_week(self.week_start)
        assign = next(a for a in assignments if a.day_id == day_per.id and a.location_id == loc_b1.id and a.slot_index == 0)
        self.assertIsNotNone(assign)
        fixed_teacher_id = assign.teacher_id
        assign.fixed = True
        self.db.save_assignment(assign)

        # 1. Yer bazlı ileri ve geri kaydır
        for _ in range(3):
            self.duty_service.shift_schedule(self.week_start, shift_type="location", steps=1, preserve_fixed=True)
            assignments = self.db.get_assignments_for_week(self.week_start)
            teacher_ids = [a.teacher_id for a in assignments if a.teacher_id]
            self.assertEqual(len(teacher_ids), 30)
            self.assertEqual(len(set(teacher_ids)), 30, "Yer kaydırmada öğretmen tekrarı oluştu!")
            # Sabit atama yerinde kalmalı
            fixed_check = next(a for a in assignments if a.day_id == day_per.id and a.location_id == loc_b1.id and a.slot_index == 0)
            self.assertEqual(fixed_check.teacher_id, fixed_teacher_id)

        # 2. Gün bazlı ileri ve geri kaydır
        for _ in range(3):
            self.duty_service.shift_schedule(self.week_start, shift_type="day", steps=1, preserve_fixed=True)
            assignments = self.db.get_assignments_for_week(self.week_start)
            teacher_ids = [a.teacher_id for a in assignments if a.teacher_id]
            self.assertEqual(len(teacher_ids), 30)
            self.assertEqual(len(set(teacher_ids)), 30, "Gün kaydırmada öğretmen tekrarı oluştu!")
            # Sabit atama yerinde kalmalı
            fixed_check = next(a for a in assignments if a.day_id == day_per.id and a.location_id == loc_b1.id and a.slot_index == 0)
            self.assertEqual(fixed_check.teacher_id, fixed_teacher_id)

    # 37. test_eokul_pdf_parsing_and_import
    def test_eokul_pdf_parsing_and_import(self):
        pdf_path = Path("data/eokul_sample_timetable.pdf")
        self.assertTrue(pdf_path.exists())

        # 1. Parse et ve doğrula
        parsed = self.sub_service.parse_eokul_timetable_pdf(str(pdf_path))
        self.assertEqual(len(parsed["teachers"]), 35)
        self.assertGreaterEqual(len(parsed["classes"]), 20)
        self.assertEqual(parsed["total_lessons"], 700)

        # 2. İçe aktar
        res = self.sub_service.import_timetables_from_pdf(str(pdf_path), auto_create_missing_teachers=True, clear_existing=True)
        self.assertEqual(res["teachers_count"], 35)
        self.assertEqual(res["lessons_count"], 1225) # 35 öğretmen x 35 periyot

        # 3. Veritabanından rastgele bir öğretmenin derslerini kontrol et
        t_adnan = next((t for t in self.db.get_teachers() if "ADNAN" in t.name), None)
        self.assertIsNotNone(t_adnan)
        adnan_lessons = self.db.get_teacher_lessons(t_adnan.id)
        self.assertEqual(len(adnan_lessons), 35)

    # 38. test_reset_timetables_and_all_data
    def test_reset_timetables_and_all_data(self):
        # 1. Ders programını sıfırla
        self.db.reset_timetables()
        all_t = self.db.get_teachers()
        first_t = all_t[0]
        lessons = self.db.get_teacher_lessons(first_t.id)
        self.assertEqual(len(lessons), 0)

        # 2. Tüm verileri sıfırla
        self.db.reset_all_data(keep_school_info=True, keep_locations=True)
        self.assertEqual(len(self.db.get_teachers()), 0)
        self.assertEqual(len(self.db.get_assignments_for_week(self.week_start)), 0)
        # Okul ve lokasyon korunmalı
        school = self.db.get_school_info()
        self.assertTrue(school.installed)
        self.assertGreater(len(self.db.get_locations()), 0)

    # 39. test_past_duty_pdf_parsing_and_import
    def test_past_duty_pdf_parsing_and_import(self):
        pdf_path = Path("data/past_duty_sample.pdf")
        self.assertTrue(pdf_path.exists(), "Test PDF dosyası data/past_duty_sample.pdf bulunamadı")

        target_week = "2026-10-12"
        assignments = self.duty_service.parse_duty_table_pdf(str(pdf_path), target_week)

        # 30 nöbet görevi eksiksiz çıkarılmalı
        self.assertEqual(len(assignments), 30)
        # Tüm görevlerde öğretmenler başarıyla eşleşmiş olmalı
        self.assertTrue(all(a.teacher_id is not None for a in assignments))

        # 30 farklı nöbetçi öğretmen atanmış olmalı
        unique_teachers = set(a.teacher_id for a in assignments)
        self.assertEqual(len(unique_teachers), 30)

        # Veritabanına aktarımı test et
        self.db.clear_assignments(target_week)
        for a in assignments:
            self.db.save_assignment(a)

        db_assignments = self.db.get_assignments_for_week(target_week)
        self.assertEqual(len(db_assignments), 30)

        # Sistem çıktısı formatındaki PDF'i de test et (Nobet_Cizelgesi_2026-09-28.pdf)
        sys_pdf = Path("Nobet_Cizelgesi_2026-09-28.pdf")
        if sys_pdf.exists():
            sys_assignments = self.duty_service.parse_duty_table_pdf(str(sys_pdf), "2026-10-19")
            self.assertEqual(len(sys_assignments), 30)
            self.assertTrue(all(a.teacher_id is not None for a in sys_assignments))

    # 40. test_timetable_exports
    def test_timetable_exports(self):
        # Database metodları
        self.assertTrue(self.db.has_timetable_data())
        classes = self.db.get_distinct_classes()
        self.assertGreaterEqual(len(classes), 1)
        first_cls_lessons = self.db.get_class_lessons(classes[0])
        self.assertGreater(len(first_cls_lessons), 0)

        # 1. Öğretmen Ders Programı PDF ve Excel
        t = self.db.get_teachers()[0]
        t_pdf = self.export_service.export_teacher_timetable_pdf(self.export_dir / "t_single.pdf", teacher_id=t.id)
        self.assertTrue(t_pdf.exists())
        self.assertGreater(t_pdf.stat().st_size, 1000)

        t_excel = self.export_service.export_teacher_timetable_excel(self.export_dir / "t_single.xlsx", teacher_id=t.id)
        self.assertTrue(t_excel.exists())

        # 2. Sınıf Ders Programı PDF ve Excel
        c_pdf = self.export_service.export_class_timetable_pdf(self.export_dir / "c_single.pdf", class_name=classes[0])
        self.assertTrue(c_pdf.exists())
        self.assertGreater(c_pdf.stat().st_size, 1000)

        c_excel = self.export_service.export_class_timetable_excel(self.export_dir / "c_single.xlsx", class_name=classes[0])
        self.assertTrue(c_excel.exists())

        # 3. Genel Çarşaf Program Excel
        m_excel = self.export_service.export_master_timetable_excel(self.export_dir / "master.xlsx")
        self.assertTrue(m_excel.exists())
        self.assertGreater(m_excel.stat().st_size, 1000)

        # 4. Boş Dersler Çizelgesi Excel
        f_excel = self.export_service.export_free_periods_excel(self.export_dir / "free.xlsx")
        self.assertTrue(f_excel.exists())

    # 41. test_week_carry_and_multi_mode_shift
    def test_week_carry_and_multi_mode_shift(self):
        from ui.shift_dialog import execute_shift

        # 1. Kaynak haftada nöbetler var
        self.assertTrue(self.db.has_assigned_duties_for_week(self.week_start))
        
        # Hedef hafta başlangıçta boş
        target_week = "2026-10-12"
        self.assertFalse(self.db.has_assigned_duties_for_week(target_week))

        # 2. Aynısını aktar (same)
        success = self.duty_service.copy_week_to_next(self.week_start, target_week, shift_mode="same")
        self.assertTrue(success)
        self.assertTrue(self.db.has_assigned_duties_for_week(target_week))

        # Kontrol: Pazartesi 1. Kat öğretmeni kaynak ile hedefte birebir aynı olmalı
        day_pzt = self.days_map["Pazartesi"]
        loc_1 = self.locs_map["1. KAT"]
        src_matrix = self.duty_service.get_grid_matrix(self.week_start)
        tgt_matrix = self.duty_service.get_grid_matrix(target_week)
        self.assertEqual(
            src_matrix["assignments"][(day_pzt.id, loc_1.id, 0)].teacher_id,
            tgt_matrix["assignments"][(day_pzt.id, loc_1.id, 0)].teacher_id
        )

        # 3. 1 gün kaydırarak aktar (shift_day)
        target_week_2 = "2026-10-19"
        success2 = self.duty_service.copy_week_to_next(self.week_start, target_week_2, shift_mode="shift_day", shift_steps=1)
        self.assertTrue(success2)
        tgt2_matrix = self.duty_service.get_grid_matrix(target_week_2)
        day_sal = self.days_map["Salı"]
        # Pazartesi'deki öğretmen Salı gününe geçmiş olmalı
        self.assertEqual(
            src_matrix["assignments"][(day_pzt.id, loc_1.id, 0)].teacher_id,
            tgt2_matrix["assignments"][(day_sal.id, loc_1.id, 0)].teacher_id
        )

        # 4. Yerleri kaydırarak aktar (shift_loc)
        target_week_3 = "2026-10-26"
        success3 = self.duty_service.copy_week_to_next(self.week_start, target_week_3, shift_mode="shift_loc", shift_steps=1)
        self.assertTrue(success3)
        tgt3_matrix = self.duty_service.get_grid_matrix(target_week_3)
        loc_2 = self.locs_map["2. KAT"]
        # 1. Kat'taki öğretmen 2. Kat'a geçmiş olmalı
        self.assertEqual(
            src_matrix["assignments"][(day_pzt.id, loc_1.id, 0)].teacher_id,
            tgt3_matrix["assignments"][(day_pzt.id, loc_2.id, 0)].teacher_id
        )

        # 5. execute_shift ile yeni modların testi
        msg_same = execute_shift(self.duty_service, self.week_start, "copy_next_same")
        self.assertIn("aktarıldı", msg_same.lower())

        msg_day = execute_shift(self.duty_service, self.week_start, "copy_next_shift_day")
        self.assertIn("aktarıldı", msg_day.lower())

        msg_loc = execute_shift(self.duty_service, self.week_start, "copy_next_shift_loc")
        self.assertIn("aktarıldı", msg_loc.lower())

    # 42. test_multi_absent_teachers_no_collision
    def test_multi_absent_teachers_no_collision(self):
        # 1. İki gelmeyen öğretmen ve dersleri tanımla
        absent1 = Teacher(id="t_multi_abs1", name="Gelmeyen Mat", branch="Matematik", is_active=True)
        absent2 = Teacher(id="t_multi_abs2", name="Gelmeyen Turk", branch="Türkçe", is_active=True)
        # Nöbetçi öğretmenler
        duty1 = Teacher(id="t_multi_duty1", name="Nöbetçi Matçı", branch="Matematik", is_active=True)
        duty2 = Teacher(id="t_multi_duty2", name="Nöbetçi Fen", branch="Fen Bilimleri", is_active=True)
        duty3_sick = Teacher(id="t_multi_duty3_sick", name="Nöbetçi Hasta", branch="Sosyal Bilgiler", is_active=True)

        for t in [absent1, absent2, duty1, duty2, duty3_sick]:
            self.db.save_teacher(t)

        # İki gelmeyen öğretmenin de 2. saatte dersi var
        self.db.save_teacher_lessons([
            TeacherLesson(teacher_id=absent1.id, day_name="Çarşamba", period=2, class_name="8-A", subject_code="MAT", is_free=False),
            TeacherLesson(teacher_id=absent2.id, day_name="Çarşamba", period=2, class_name="7-B", subject_code="TRK", is_free=False),
        ])

        test_week = "2026-11-02"
        day_car = next(d for d in self.db.get_days() if d.name == "Çarşamba")
        loc1 = self.db.get_locations()[0]
        loc2 = self.db.get_locations()[1]
        loc3 = self.db.get_locations()[2]

        self.db.save_assignment(Assignment(week_start=test_week, day_id=day_car.id, location_id=loc1.id, teacher_id=duty1.id))
        self.db.save_assignment(Assignment(week_start=test_week, day_id=day_car.id, location_id=loc2.id, teacher_id=duty2.id))
        self.db.save_assignment(Assignment(week_start=test_week, day_id=day_car.id, location_id=loc3.id, teacher_id=duty3_sick.id))

        # duty3_sick nöbetçi listesinde olmasına rağmen kendisi de gelmedi (izinli/raporlu)
        absent_ids = [absent1.id, absent2.id, duty3_sick.id]

        multi_results = self.sub_service.auto_assign_multi_substitutions(
            date_str="2026-11-04",
            day_name="Çarşamba",
            absent_teacher_ids=absent_ids,
            week_start=test_week,
            teachers_per_lesson=1
        )

        # 1. Gelmeyen nöbetçi (duty3_sick) asla bir derse atanmamalı
        all_assigned_duty_ids = [
            sub.duty_teacher_id
            for subs in multi_results.values()
            for sub in subs
            if sub.duty_teacher_id
        ]
        self.assertNotIn(duty3_sick.id, all_assigned_duty_ids, "Gelmeyen nöbetçi öğretmen ikameye atandı!")

        # 2. 2. ders saati için görevlendirilen nöbetçiler çakışmamalı (farklı olmalı)
        sub1 = multi_results[absent1.id][0]
        sub2 = multi_results[absent2.id][0]
        self.assertIsNotNone(sub1.duty_teacher_id)
        self.assertIsNotNone(sub2.duty_teacher_id)
        self.assertNotEqual(sub1.duty_teacher_id, sub2.duty_teacher_id, "Aynı saatteki iki farklı derse aynı nöbetçi atandı!")

        # 3. Branş eşleşmesi: Matematik dersine Matematik branşındaki duty1 atanmış ve ek ders işaretlenmiş olmalı
        self.assertEqual(sub1.duty_teacher_id, duty1.id)
        self.assertTrue(sub1.is_ek_ders)
        self.assertEqual(sub2.duty_teacher_id, duty2.id)

    # 43. test_daily_substitutions_exports
    def test_daily_substitutions_exports(self):
        # İki gelmeyen öğretmenin atamaları
        absent1 = Teacher(id="t_exp_abs1", name="Ali Çelik", branch="Matematik", is_active=True)
        absent2 = Teacher(id="t_exp_abs2", name="Ayşe Yılmaz", branch="Türkçe", is_active=True)
        duty1 = Teacher(id="t_exp_dut1", name="Mehmet Demir", branch="Fen Bilimleri", is_active=True)
        for t in [absent1, absent2, duty1]:
            self.db.save_teacher(t)

        assignments = [
            SubstitutionAssignment(
                date_str="2026-11-04",
                period=1,
                absent_teacher_id=absent1.id,
                class_name="5-A",
                subject_code="MAT",
                duty_teacher_id=duty1.id,
                notes="Otomatik Eşleştirildi",
                is_ek_ders=False
            ),
            SubstitutionAssignment(
                date_str="2026-11-04",
                period=2,
                absent_teacher_id=absent2.id,
                class_name="6-B",
                subject_code="TRK",
                duty_teacher_id=duty1.id,
                notes="Otomatik Eşleştirildi",
                is_ek_ders=False
            )
        ]

        # 1. Günlük Toplu PDF Çıktısı
        pdf_path = self.export_dir / "gunluk_toplu_ikame.pdf"
        out_pdf = self.sub_service.export_daily_substitutions_pdf(
            output_path=str(pdf_path),
            date_str="2026-11-04",
            day_name="Çarşamba",
            assignments=assignments
        )
        self.assertTrue(os.path.exists(out_pdf))
        self.assertGreater(os.path.getsize(out_pdf), 1000)

        # PDF içeriğini kontrol et
        doc = pymupdf.open(out_pdf)
        self.assertGreaterEqual(len(doc), 1)
        full_text = "".join(page.get_text() for page in doc)
        self.assertIn("GÜNLÜK BOŞ DERS", full_text)
        self.assertIn("Ali Çelik", full_text)
        self.assertIn("Ayşe Yılmaz", full_text)
        doc.close()

        # 2. Günlük Toplu HTML Çıktısı
        html_path = self.export_dir / "gunluk_toplu_ikame.html"
        out_html = self.sub_service.export_daily_substitutions_html(
            output_path=str(html_path),
            date_str="2026-11-04",
            day_name="Çarşamba",
            assignments=assignments
        )
        self.assertTrue(os.path.exists(out_html))
        self.assertGreater(os.path.getsize(out_html), 500)

        with open(out_html, "r", encoding="utf-8") as f:
            html_text = f.read()
        self.assertIn("Ali Çelik", html_text)
        self.assertIn("Ayşe Yılmaz", html_text)
        self.assertIn("Mehmet Demir", html_text)


if __name__ == "__main__":
    unittest.main()

