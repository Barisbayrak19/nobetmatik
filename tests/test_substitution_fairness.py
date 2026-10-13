import unittest
import tempfile
import shutil
from pathlib import Path
from core.database import Database
from core.models import Teacher, Day, Location, Assignment, TeacherLesson, SubstitutionAssignment
from logic.substitution_service import SubstitutionService

class TestSubstitutionFairness(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "test.db"
        self.db = Database(self.db_path)
        self.sub_service = SubstitutionService(self.db)
        self.week_start = "2026-09-28"
        self.date_str = "2026-09-28" # Pazartesi

        # Setup days
        self.days = [
            Day(name="Pazartesi", order_num=1),
            Day(name="Salı", order_num=2),
            Day(name="Çarşamba", order_num=3),
            Day(name="Perşembe", order_num=4),
            Day(name="Cuma", order_num=5),
        ]
        for d in self.days:
            self.db.save_day(d)

        # Setup locations
        self.loc1 = Location(name="1. Kat", order_num=1)
        self.loc2 = Location(name="Bahçe", order_num=2)
        self.db.save_location(self.loc1)
        self.db.save_location(self.loc2)

        # Setup teachers: 1 absent, 2 duty teachers
        self.t_absent = Teacher(name="Ali Gelmeyen", branch="Matematik", is_active=True)
        self.t_duty1 = Teacher(name="Ayşe Nöbetçi", branch="Fizik", is_active=True)
        self.t_duty2 = Teacher(name="Mehmet Nöbetçi", branch="Kimya", is_active=True)
        self.db.save_teacher(self.t_absent)
        self.db.save_teacher(self.t_duty1)
        self.db.save_teacher(self.t_duty2)

        # Assign duties for Pazartesi
        d_paz = self.days[0]
        self.db.save_assignment(Assignment(week_start=self.week_start, day_id=d_paz.id, location_id=self.loc1.id, teacher_id=self.t_duty1.id, slot_index=0))
        self.db.save_assignment(Assignment(week_start=self.week_start, day_id=d_paz.id, location_id=self.loc2.id, teacher_id=self.t_duty2.id, slot_index=0))

        # Setup timetable: t_absent has lesson at period 2 and 3
        # t_duty1 and t_duty2 are free at period 2 and 3
        self.db.save_teacher_lesson(TeacherLesson(teacher_id=self.t_absent.id, day_name="Pazartesi", period=2, class_name="9-A", subject_code="MAT", is_free=False))
        self.db.save_teacher_lesson(TeacherLesson(teacher_id=self.t_absent.id, day_name="Pazartesi", period=3, class_name="9-B", subject_code="MAT", is_free=False))

        for p in range(1, 8):
            self.db.save_teacher_lesson(TeacherLesson(teacher_id=self.t_duty1.id, day_name="Pazartesi", period=p, class_name="", subject_code="", is_free=True))
            self.db.save_teacher_lesson(TeacherLesson(teacher_id=self.t_duty2.id, day_name="Pazartesi", period=p, class_name="", subject_code="", is_free=True))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_single_teacher_auto_assign_with_tandem(self):
        # Auto assign with tandem enabled
        subs = self.sub_service.auto_assign_substitutions(
            date_str=self.date_str,
            day_name="Pazartesi",
            absent_teacher_id=self.t_absent.id,
            week_start=self.week_start,
            teachers_per_lesson=1,
            assign_tandem_for_unassigned=True
        )
        self.assertGreaterEqual(len(subs), 2)
        assigned_teachers = {s.duty_teacher_id for s in subs if s.duty_teacher_id}
        # Both duty teachers should be engaged
        self.assertIn(self.t_duty1.id, assigned_teachers)
        self.assertIn(self.t_duty2.id, assigned_teachers)

    def test_multi_teacher_auto_assign_with_tandem(self):
        results = self.sub_service.auto_assign_multi_substitutions(
            date_str=self.date_str,
            day_name="Pazartesi",
            absent_teacher_ids=[self.t_absent.id],
            week_start=self.week_start,
            teachers_per_lesson=1,
            assign_tandem_for_unassigned=True
        )
        subs = results[self.t_absent.id]
        assigned_teachers = {s.duty_teacher_id for s in subs if s.duty_teacher_id}
        self.assertIn(self.t_duty1.id, assigned_teachers)
        self.assertIn(self.t_duty2.id, assigned_teachers)

    def test_fairness_report_calculation(self):
        subs = self.sub_service.auto_assign_substitutions(
            date_str=self.date_str,
            day_name="Pazartesi",
            absent_teacher_id=self.t_absent.id,
            week_start=self.week_start,
            teachers_per_lesson=1,
            assign_tandem_for_unassigned=True
        )
        report = self.sub_service.get_fairness_report(
            date_str=self.date_str,
            day_name="Pazartesi",
            assignments=subs,
            week_start=self.week_start,
            absent_teacher_ids=[self.t_absent.id]
        )
        self.assertIsNotNone(report)
        self.assertGreaterEqual(report.fairness_score, 75.0)
        self.assertLessEqual(report.gini_index, 0.5)
        self.assertEqual(len(report.idle_teachers_today), 0) # No idle teachers left because tandem engaged both

    def test_fairness_report_with_idle_proposals(self):
        # Assign only 1 lesson to duty1 without tandem
        single_sub = SubstitutionAssignment(
            date_str=self.date_str,
            period=2,
            absent_teacher_id=self.t_absent.id,
            class_name="9-A",
            subject_code="MAT",
            duty_teacher_id=self.t_duty1.id
        )
        report = self.sub_service.get_fairness_report(
            date_str=self.date_str,
            day_name="Pazartesi",
            assignments=[single_sub],
            week_start=self.week_start,
            absent_teacher_ids=[self.t_absent.id]
        )
        # Mehmet Nöbetçi should be detected as idle today
        idle_ids = [i["teacher_id"] for i in report.idle_teachers_today]
        self.assertIn(self.t_duty2.id, idle_ids)
        # Should generate proposal for t_duty2 to be co-substitute
        self.assertGreaterEqual(len(report.proposals), 1)
        self.assertEqual(report.proposals[0]["co_teacher_id"], self.t_duty2.id)

    def test_fairness_dialog_ui(self):
        import customtkinter as ctk
        from ui.substitution_dialog import SubstitutionFairnessDialog
        root = ctk.CTk()
        root.withdraw()
        try:
            report = self.sub_service.get_fairness_report(
                date_str=self.date_str,
                day_name="Pazartesi",
                assignments=[],
                week_start=self.week_start,
                absent_teacher_ids=[]
            )
            dlg = SubstitutionFairnessDialog(root, report=report)
            dlg.update_idletasks()
            dlg.destroy()
        finally:
            root.destroy()

if __name__ == "__main__":
    unittest.main()

