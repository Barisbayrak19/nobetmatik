import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.database import Database
from core.models import Teacher, TeacherLesson
from ui.import_dialog import ImportView


class TestImportGranularSelection(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_import.db"
        self.db = Database(self.db_path)

        # Pre-populate DB with 2 teachers and their timetables
        self.t1 = Teacher(id="t1", name="Ali Demir", branch="Matematik", is_active=True)
        self.t2 = Teacher(id="t2", name="Zeynep Kaya", branch="Türkçe", is_active=True)
        self.db.save_teacher(self.t1)
        self.db.save_teacher(self.t2)

        # Pre-populate timetable for t1 and t2
        self.db.save_teacher_lessons_batch([
            TeacherLesson(teacher_id="t1", day_name="Pazartesi", period=1, class_name="5-A", subject_code="MAT", is_free=False),
            TeacherLesson(teacher_id="t2", day_name="Pazartesi", period=1, class_name="6-A", subject_code="TÜRK", is_free=False),
        ])

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("ui.import_dialog.ImportConflictDialog")
    @patch("ui.import_dialog.messagebox.showinfo")
    @patch("ui.import_dialog.messagebox.showwarning")
    def test_teachers_tab_partial_import(self, mock_warn, mock_info, mock_conflict):
        """Kullanıcının sadece seçtiği öğretmenleri aktardığını doğrula."""
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()

        view = ImportView(root, self.db)
        view.wait_window = MagicMock()

        # Simulate parsed teachers from file: Veli Can (checked) and Melis Su (unchecked)
        view.parsed_teachers = [
            {"id": "t_0", "name": "Veli Can", "branch": "Fen Bilimleri", "selected": True},
            {"id": "t_1", "name": "Melis Su", "branch": "İngilizce", "selected": False},
        ]
        view.teacher_map_by_iid = {t["id"]: t for t in view.parsed_teachers}

        # Run import
        view._start_teacher_import()

        teachers_now = self.db.get_teachers()
        names = [t.name for t in teachers_now]

        self.assertIn("Veli Can", names, "Seçili öğretmen eklenmeli")
        self.assertNotIn("Melis Su", names, "Seçilmeyen öğretmen eklenmemeli")

        root.destroy()

    @patch("ui.import_dialog.messagebox.showinfo")
    @patch("ui.import_dialog.messagebox.askyesno", return_value=False)
    def test_timetable_tab_partial_update(self, mock_ask, mock_info):
        """Sadece seçilen öğretmenin programının güncellendiğini, diğer öğretmenin korunduğunu test et."""
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()

        view = ImportView(root, self.db)

        # Simulate parsed lessons from a new timetable file for Ali Demir and Zeynep Kaya
        lesson_a_new = TeacherLesson(teacher_id="", day_name="Salı", period=2, class_name="8-B", subject_code="MAT8", is_free=False)
        lesson_a_new.temp_teacher_name = "Ali Demir"
        lesson_a_new.temp_branch = "Matematik"

        lesson_b_new = TeacherLesson(teacher_id="", day_name="Çarşamba", period=3, class_name="7-A", subject_code="TR7", is_free=False)
        lesson_b_new.temp_teacher_name = "Zeynep Kaya"
        lesson_b_new.temp_branch = "Türkçe"

        view.parsed_lessons = [lesson_a_new, lesson_b_new]
        view.parsed_tt_teachers = [
            {"id": "tt_0", "name": "Ali Demir", "branch": "Matematik", "lesson_count": 1, "selected": True},
            {"id": "tt_1", "name": "Zeynep Kaya", "branch": "Türkçe", "lesson_count": 1, "selected": False}, # Not selected!
        ]
        view.tt_teacher_map_by_iid = {t["id"]: t for t in view.parsed_tt_teachers}

        # Clear all is False -> Only selected teacher (Ali Demir) gets updated!
        view.clear_timetables_var.set(False)

        view._start_timetable_import()

        # Check lessons for Ali Demir: should have new lesson on Salı period 2
        lessons_a = self.db.get_teacher_lessons("t1")
        self.assertEqual(len(lessons_a), 1)
        self.assertEqual(lessons_a[0].day_name, "Salı")
        self.assertEqual(lessons_a[0].class_name, "8-B")

        # Check lessons for Zeynep Kaya: should still have original lesson on Pazartesi period 1 (NOT wiped, NOT changed!)
        lessons_b = self.db.get_teacher_lessons("t2")
        self.assertEqual(len(lessons_b), 1)
        self.assertEqual(lessons_b[0].day_name, "Pazartesi")
        self.assertEqual(lessons_b[0].class_name, "6-A")

        root.destroy()


if __name__ == "__main__":
    unittest.main()
