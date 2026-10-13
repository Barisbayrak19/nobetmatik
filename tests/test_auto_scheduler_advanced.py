"""
Gelişmiş Otomatik Nöbet Dağıtım Algoritması Birim Testleri
- Kesin Kurallar vs Dengeleme Kuralları
- Muafiyet ve Özel Durum Kontrolü (Hamilelik, Engellilik, vb.)
- 20/25 Yıl Kıdem Kuralı ve Personel Yeterlilik Analizi
- Sabit Nöbetlerin Korunması
- Aynı Gün Çakışma ve Kapasite Engeli
- Öğretmen Gün Tercihleri ve Ders Programı Yükü
- 2 Aşamalı Optimizasyon ve Açıklanabilirlik / Gerekçe Üretimi
- Manuel Sürükle-Bırak Çakışma Doğrulaması
"""
import unittest
import tempfile
import shutil
from pathlib import Path

from core.database import Database
from core.models import Teacher, Location, Day, Assignment, SchoolInfo, TeacherLesson
from logic.auto_scheduler import AutoScheduler
from logic.duty_service import DutyService

class TestAutoSchedulerAdvanced(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_advanced_sched.db"
        self.db = Database(self.db_path)
        self.scheduler = AutoScheduler(self.db)
        self.duty_service = DutyService(self.db)

        # Temel Günler (Pzt - Cuma)
        days_names = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
        self.days = []
        for i, name in enumerate(days_names):
            d = Day(name=name, order_num=i + 1, is_active=True)
            self.db.save_day(d)
            self.days.append(d)

        # 3 Nöbet Yeri (Her biri 1 kapasiteli -> Toplam 5 gün x 3 = 15 slot)
        self.loc1 = Location(name="Zemin Kat", order_num=1, capacity=1, is_active=True)
        self.loc2 = Location(name="1. Kat", order_num=2, capacity=1, is_active=True)
        self.loc3 = Location(name="Bahçe", order_num=3, capacity=1, is_active=True)
        self.db.save_location(self.loc1)
        self.db.save_location(self.loc2)
        self.db.save_location(self.loc3)

        self.week_start = "2026-10-12"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_exemption_hard_constraint(self):
        """Muaf öğretmenler (hamilelik, engellilik vb.) kesinlikle aday havuzuna alınmamalıdır."""
        # 16 öğretmen oluştur: 1 tanesi kesin muaf
        for i in range(15):
            t = Teacher(name=f"Öğretmen {i+1}", branch="Matematik", is_active=True)
            self.db.save_teacher(t)

        exempt_teacher = Teacher(
            name="Ayşe Yılmaz",
            branch="Türkçe",
            is_active=True,
            is_exempt=True,
            exemption_reason="Hamilelik / Süt İzni (Mevzuat)"
        )
        self.db.save_teacher(exempt_teacher)

        assignments, report = self.scheduler.generate_schedule(self.week_start)

        # Ayşe Yılmaz'a hiçbir nöbet verilmemeli
        assigned_teachers = [a.teacher_id for a in assignments if a.teacher_id]
        self.assertNotIn(exempt_teacher.id, assigned_teachers)

        # Muaf öğretmen raporda gerekçesiyle yer almalı
        self.assertIn("Ayşe Yılmaz", report.excluded_teachers)
        self.assertIn("Hamilelik", report.excluded_teachers["Ayşe Yılmaz"])

    def test_idareci_and_yegitek_exemption(self):
        """İdareci ve YEĞİTEK Okul Sorumluları nöbet havuzundan muaf tutulmalıdır."""
        for i in range(15):
            t = Teacher(name=f"Öğretmen {i+1}", branch="Matematik", is_active=True)
            self.db.save_teacher(t)

        mudur_yard = Teacher(
            name="Kemal MüdürYard",
            branch="Tarih",
            is_active=True,
            is_exempt=True,
            exemption_reason="İdareci (Müdür / Müdür Yardımcısı)"
        )
        btr_ogretmen = Teacher(
            name="Serkan YEĞİTEK",
            branch="Bilişim",
            is_active=True,
            is_exempt=True,
            exemption_reason="YEĞİTEK Okul Sorumlusu (BTR)"
        )
        self.db.save_teacher(mudur_yard)
        self.db.save_teacher(btr_ogretmen)

        assignments, report = self.scheduler.generate_schedule(self.week_start)
        assigned_ids = [a.teacher_id for a in assignments if a.teacher_id]

        self.assertNotIn(mudur_yard.id, assigned_ids)
        self.assertNotIn(btr_ogretmen.id, assigned_ids)
        self.assertIn("Kemal MüdürYard", report.excluded_teachers)
        self.assertIn("İdareci", report.excluded_teachers["Kemal MüdürYard"])
        self.assertIn("Serkan YEĞİTEK", report.excluded_teachers)
        self.assertIn("YEĞİTEK", report.excluded_teachers["Serkan YEĞİTEK"])


    def test_fixed_duties_preserved(self):
        """Sabit nöbetler asla değiştirilmemeli, günü ve yeri korunmalıdır."""
        teachers = []
        for i in range(16):
            t = Teacher(name=f"Öğretmen {i+1}", branch="Branş", is_active=True)
            self.db.save_teacher(t)
            teachers.append(t)

        # Salı günü Bahçe nöbetini Öğretmen 1 için sabitle
        t_fixed = teachers[0]
        tue_day = next(d for d in self.days if d.name == "Salı")
        fixed_assign = Assignment(
            week_start=self.week_start,
            day_id=tue_day.id,
            location_id=self.loc3.id,
            slot_index=0,
            teacher_id=t_fixed.id,
            fixed=True
        )
        self.db.save_assignment(fixed_assign)

        assignments, report = self.scheduler.generate_schedule(self.week_start, preserve_fixed=True)

        found_fixed = next(
            a for a in assignments
            if a.day_id == tue_day.id and a.location_id == self.loc3.id and a.slot_index == 0
        )
        self.assertEqual(found_fixed.teacher_id, t_fixed.id)
        self.assertTrue(found_fixed.fixed)
        self.assertEqual(report.stats.get("fixed_preserved"), 1)

    def test_no_same_day_conflict(self):
        """Hiçbir öğretmene aynı hafta içinde aynı gün 2 nöbet verilemez (Kesin Çakışma Kuralı)."""
        for i in range(15):
            t = Teacher(name=f"Öğretmen {i+1}", branch="Branş", is_active=True)
            self.db.save_teacher(t)

        assignments, report = self.scheduler.generate_schedule(self.week_start)

        # Her gün için atanan öğretmenlerin teklik kontrolü
        for day in self.days:
            teachers_on_day = [
                a.teacher_id for a in assignments
                if a.day_id == day.id and a.teacher_id is not None
            ]
            self.assertEqual(len(teachers_on_day), len(set(teachers_on_day)), f"{day.name} gününde mükerrer öğretmen ataması tespit edildi!")

    def test_capacity_not_exceeded(self):
        """Nöbet yerinin kapasitesi aşılmamalıdır."""
        for i in range(15):
            t = Teacher(name=f"Öğretmen {i+1}", branch="Branş", is_active=True)
            self.db.save_teacher(t)

        assignments, report = self.scheduler.generate_schedule(self.week_start)

        # Her yer ve gün için slot sayısı kapasiteyi aşmamalı
        for day in self.days:
            for loc in [self.loc1, self.loc2, self.loc3]:
                slots = [a for a in assignments if a.day_id == day.id and a.location_id == loc.id]
                self.assertEqual(len(slots), loc.capacity)

    def test_seniority_20_years_rule(self):
        """
        20/25 yıl kıdemli öğretmen muafiyet talep etmişse:
        Personel yeterliyse muaf tutulmalı; personel yetersizse yönetici uyarısı ile havuza alınmalıdır.
        """
        # Durum A: 20 öğretmen var, 15 slot gerekiyor (Personel yeterli)
        for i in range(19):
            t = Teacher(name=f"Genç Öğretmen {i+1}", branch="Branş", is_active=True, seniority_years=5)
            self.db.save_teacher(t)

        senior_t = Teacher(
            name="Mehmet Kıdemli",
            branch="Tarih",
            is_active=True,
            seniority_years=25,
            exemption_requested=True
        )
        self.db.save_teacher(senior_t)

        assignments, report = self.scheduler.generate_schedule(self.week_start)
        assigned_ids = [a.teacher_id for a in assignments if a.teacher_id]
        # Yeterli personel olduğu için kıdemli öğretmen muaf tutulmalı
        self.assertNotIn(senior_t.id, assigned_ids)
        self.assertIn("Mehmet Kıdemli", report.excluded_teachers)

    def test_seniority_insufficient_staff_warning(self):
        """Personel yetersizse 20/25 yıl kıdemli öğretmenler uyarılı olarak havuza dahil edilmelidir."""
        # Toplam 15 slot var ama sadece 14 öğretmen var (1'i kıdemli talepkar)
        for i in range(13):
            t = Teacher(name=f"Genç Öğretmen {i+1}", branch="Branş", is_active=True, seniority_years=5)
            self.db.save_teacher(t)

        senior_t = Teacher(
            name="Mehmet Kıdemli",
            branch="Tarih",
            is_active=True,
            seniority_years=25,
            exemption_requested=True
        )
        self.db.save_teacher(senior_t)

        assignments, report = self.scheduler.generate_schedule(self.week_start)
        # Personel yetersiz uyarısı verilmiş olmalı
        warning_found = any("yetersiz olduğundan" in w and "Mehmet Kıdemli" in w for w in report.warnings)
        self.assertTrue(warning_found)

    def test_teacher_day_preferences(self):
        """Öğretmenin tercih ettiği güne atanma olasılığı artmalıdır."""
        # 1 öğretmen Çarşamba gününü tercih ediyor
        t_pref = Teacher(
            name="Ali Tercihli",
            branch="Fen",
            is_active=True,
            preferred_days=["Çarşamba"]
        )
        self.db.save_teacher(t_pref)

        for i in range(14):
            t = Teacher(name=f"Diğer {i+1}", branch="Branş", is_active=True)
            self.db.save_teacher(t)

        assignments, report = self.scheduler.generate_schedule(self.week_start)
        wed_day = next(d for d in self.days if d.name == "Çarşamba")

        ali_assignments = [a for a in assignments if a.teacher_id == t_pref.id]
        if ali_assignments:
            # Tercih karşılandı mı?
            self.assertEqual(ali_assignments[0].day_id, wed_day.id)
            self.assertIn("tercih ettiği gün", ali_assignments[0].notes)

    def test_unfilled_slots_explanation(self):
        """Uygun öğretmen sayısı yetersiz olduğunda eksik slotlar ve gerekçeleri raporda yer almalıdır."""
        # Sadece 2 öğretmen oluştur (15 slot var)
        t1 = Teacher(name="Öğretmen A", is_active=True)
        t2 = Teacher(name="Öğretmen B", is_active=True)
        self.db.save_teacher(t1)
        self.db.save_teacher(t2)

        assignments, report = self.scheduler.generate_schedule(self.week_start)

        self.assertGreater(len(report.unfilled_slots), 0)
        self.assertGreater(len(report.warnings), 0)
        # Sistem zorla çakışmalı atama yapmamalıdır (her gün max 2 nöbet atanabilir)
        for day in self.days:
            assigned_today = [a.teacher_id for a in assignments if a.day_id == day.id and a.teacher_id]
            self.assertEqual(len(assigned_today), len(set(assigned_today)))

    def test_manual_drag_and_drop_conflict_prevention(self):
        """Manuel sürükle-bırak veya atamada aynı gün çakışması engellenmeli ve hata mesajı dönmelidir."""
        t1 = Teacher(name="Öğretmen A", is_active=True)
        t2 = Teacher(name="Öğretmen B", is_active=True)
        self.db.save_teacher(t1)
        self.db.save_teacher(t2)

        pzt = self.days[0]
        sali = self.days[1]

        # t1 Pazartesi Zemin Kat'ta nöbetçi
        a1 = Assignment(week_start=self.week_start, day_id=pzt.id, location_id=self.loc1.id, slot_index=0, teacher_id=t1.id)
        # t1 Salı Zemin Kat'ta da nöbetçi
        a2 = Assignment(week_start=self.week_start, day_id=sali.id, location_id=self.loc1.id, slot_index=0, teacher_id=t1.id)
        # Pazartesi 1. Kat boş
        a3 = Assignment(week_start=self.week_start, day_id=pzt.id, location_id=self.loc2.id, slot_index=0, teacher_id=None)

        self.db.save_assignment(a1)
        self.db.save_assignment(a2)
        self.db.save_assignment(a3)

        # t1'in Salı günkü nöbetini (a2) Pazartesi 1. Kat'a (a3) taşımaya çalış -> t1 zaten Pazartesi Zemin Kat'ta!
        success = self.duty_service.move_or_swap(
            week_start=self.week_start,
            source_day_id=sali.id,
            source_loc_id=self.loc1.id,
            source_slot=0,
            target_day_id=pzt.id,
            target_loc_id=self.loc2.id,
            target_slot=0
        )

        self.assertFalse(success)
        self.assertIsNotNone(self.duty_service.last_error)
        self.assertIn("başka bir nöbette görevli", self.duty_service.last_error)

    def test_zero_lesson_day_strict_exclusion(self):
        """Seçenek B (Katı Kural): O gün hiç dersi olmayan öğretmene KESİNLİKLE nöbet verilmemelidir."""
        # Öğretmen oluştur
        t_monday_free = Teacher(name="Fatma Öğretmen", branch="Matematik", is_active=True)
        self.db.save_teacher(t_monday_free)

        # Fatma Öğretmen'e Salı ve Çarşamba ders ekle, ama Pazartesi 0 ders olsun
        lessons = [
            TeacherLesson(teacher_id=t_monday_free.id, day_name="Salı", period=1, class_name="8A", subject_code="MAT", is_free=False),
            TeacherLesson(teacher_id=t_monday_free.id, day_name="Salı", period=2, class_name="8A", subject_code="MAT", is_free=False),
            TeacherLesson(teacher_id=t_monday_free.id, day_name="Çarşamba", period=1, class_name="7B", subject_code="MAT", is_free=False),
        ]
        self.db.save_teacher_lessons_batch(lessons)

        # 1. Otomatik Dağıtım Testi:
        assignments, report = self.scheduler.generate_schedule(self.week_start)
        pzt = self.days[0]

        # Fatma Öğretmen Pazartesi günü ASLA nöbetçi olmamalıdır
        pzt_fatma_duties = [
            a for a in assignments
            if a.day_id == pzt.id and a.teacher_id == t_monday_free.id
        ]
        self.assertEqual(len(pzt_fatma_duties), 0, "Dersi olmayan öğretmene Pazartesi nöbeti verildi!")

        # Pazartesi günü için unfilled slots raporunda gerekçe belirtilmeli
        pzt_unfilled = [u for u in report.unfilled_slots if u["day"] == "Pazartesi"]
        self.assertGreater(len(pzt_unfilled), 0)
        self.assertTrue(any("dersi olan öğretmen bulunamadı" in u["reason"] or "müsait veya çakışmasız" in u["reason"] for u in pzt_unfilled))

        # 2. Manuel Atama Testi (assign_teacher): Pazartesi boş bir slota Fatma'yı atamaya çalış
        pzt_assign = Assignment(week_start=self.week_start, day_id=pzt.id, location_id=self.loc1.id, slot_index=0, teacher_id=None)
        self.db.save_assignment(pzt_assign)
        assign_ok = self.duty_service.assign_teacher(pzt_assign, t_monday_free.id)
        self.assertFalse(assign_ok, "Manuel atama dersi olmayan güne izin vermemeli!")
        self.assertIn("hiç dersi bulunmadığı için", self.duty_service.last_error or "")

        # 3. Manuel Taşıma Testi (move_or_swap): Fatma'nın Salı günkü nöbetini Pazartesi'ye taşımaya çalış
        sali = self.days[1]
        sali_assign = Assignment(week_start=self.week_start, day_id=sali.id, location_id=self.loc1.id, slot_index=0, teacher_id=t_monday_free.id)
        self.db.save_assignment(sali_assign)

        move_ok = self.duty_service.move_or_swap(
            week_start=self.week_start,
            source_day_id=sali.id,
            source_loc_id=self.loc1.id,
            source_slot=0,
            target_day_id=pzt.id,
            target_loc_id=self.loc1.id,
            target_slot=0
        )
        self.assertFalse(move_ok, "Manuel taşıma dersi olmayan güne izin vermemeli!")
        self.assertIn("hiç dersi bulunmadığı için", self.duty_service.last_error or "")

if __name__ == "__main__":
    unittest.main()
