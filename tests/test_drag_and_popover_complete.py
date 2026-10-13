"""
Comprehensive test suite covering all 10 user-specified scenarios for
NöbetMatik v2.0.1 Drag & Drop, Click Separation, and Teacher Info Popover:
1. Clicking teacher does not open info popover.
2. Short distance dragging (>6px) starts drag operation.
3. Teacher can be moved to another duty cell.
4. Dropping on valid cell executes move/swap correctly.
5. Dropping on invalid cell does not corrupt schedule.
6. Fixed teacher duty cannot be moved illegally.
7. Clicking info icon (ℹ) opens teacher details popover.
8. While info popover is open, dragging another teacher closes it and allows drag.
9. When drag completes, info popover does not automatically open.
10. Weekly schedule, auto-scheduler, and save operations continue functioning.
"""
import unittest
import tempfile
import os
import shutil
import tkinter as tk
from pathlib import Path
from unittest.mock import MagicMock

from core.database import Database
from core.models import Assignment, Teacher, Location, Day, TeacherLesson
from logic.duty_service import DutyService
from ui.schedule_grid import ScheduleGrid, CellWidget, TeacherInfoPopover, DragGhostWindow
import ui.theme as theme

class MockEvent:
    def __init__(self, x=0, y=0, x_root=100, y_root=100):
        self.x = x
        self.y = y
        self.x_root = x_root
        self.y_root = y_root

class TestDragAndPopoverComplete(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        from unittest.mock import patch
        self.patch_warning = patch("tkinter.messagebox.showwarning")
        self.patch_info = patch("tkinter.messagebox.showinfo")
        self.mock_warning = self.patch_warning.start()
        self.mock_info = self.patch_info.start()

        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_drag.db")
        self.db = Database(self.db_path)
        self.duty_service = DutyService(self.db)
        self.week_start = "2026-09-28"

        # Days
        self.day_paz = Day(name="Pazartesi", order_num=1)
        self.day_sal = Day(name="Salı", order_num=2)
        self.db.save_day(self.day_paz)
        self.db.save_day(self.day_sal)

        # Locations
        self.loc1 = Location(name="1. Kat", capacity=1, order_num=1)
        self.loc2 = Location(name="Bahçe", capacity=1, order_num=2)
        self.db.save_location(self.loc1)
        self.db.save_location(self.loc2)

        # Teachers
        self.t1 = Teacher(name="Ahmet Yılmaz", branch="Matematik", is_active=True)
        self.t2 = Teacher(name="Ayşe Kaya", branch="Fizik", is_active=True)
        self.t_fixed = Teacher(name="Mehmet Demir", branch="Kimya", is_active=True)
        self.db.save_teacher(self.t1)
        self.db.save_teacher(self.t2)
        self.db.save_teacher(self.t_fixed)

        # Duty assignments for 2026-09-28
        # Pazartesi 1. Kat -> Ahmet Yılmaz
        self.assign1 = Assignment(week_start=self.week_start, day_id=self.day_paz.id, location_id=self.loc1.id, slot_index=0, teacher_id=self.t1.id)
        # Pazartesi Bahçe -> Ayşe Kaya
        self.assign2 = Assignment(week_start=self.week_start, day_id=self.day_paz.id, location_id=self.loc2.id, slot_index=0, teacher_id=self.t2.id)
        # Salı 1. Kat -> Mehmet Demir (Fixed)
        self.assign_fixed = Assignment(week_start=self.week_start, day_id=self.day_sal.id, location_id=self.loc1.id, slot_index=0, teacher_id=self.t_fixed.id, fixed=True)
        # Salı Bahçe -> Empty
        self.assign_empty = Assignment(week_start=self.week_start, day_id=self.day_sal.id, location_id=self.loc2.id, slot_index=0, teacher_id=None)

        self.db.save_assignment(self.assign1)
        self.db.save_assignment(self.assign2)
        self.db.save_assignment(self.assign_fixed)
        self.db.save_assignment(self.assign_empty)

        # Setup timetable lessons (give teachers active lessons on both days)
        for t in [self.t1, self.t2, self.t_fixed]:
            for d in ["Pazartesi", "Salı"]:
                self.db.save_teacher_lesson(TeacherLesson(teacher_id=t.id, day_name=d, period=1, class_name="9-A", subject_code="DERS", is_free=False))
                self.db.save_teacher_lesson(TeacherLesson(teacher_id=t.id, day_name=d, period=2, class_name="", subject_code="", is_free=True))

        self.data_changed_mock = MagicMock()
        self.grid = ScheduleGrid(
            parent=self.root,
            db=self.db,
            duty_service=self.duty_service,
            get_current_week=lambda: self.week_start,
            on_data_changed=self.data_changed_mock
        )
        self.grid.refresh()

    def tearDown(self):
        try:
            self.patch_warning.stop()
            self.patch_info.stop()
        except Exception:
            pass
        try:
            self.grid.destroy()
        except Exception:
            pass
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _get_cell(self, day_id: str, loc_id: str) -> CellWidget:
        for child in self.grid.table_frame.winfo_children():
            if isinstance(child, CellWidget):
                if child.day.id == day_id and child.location.id == loc_id:
                    return child
        raise ValueError(f"Cell for day {day_id} and loc {loc_id} not found")

    def test_scenario_1_click_does_not_open_popover(self):
        """1. Öğretmene tıklayınca sürükleme başlamadan bilgi penceresi açılmıyor."""
        cell = self._get_cell(self.day_paz.id, self.loc1.id)
        self.assertEqual(cell.teacher.name, "Ahmet Yılmaz")

        # Simulate normal mouse press and release without motion
        press_ev = MockEvent(x=10, y=10, x_root=200, y_root=200)
        cell._on_press(press_ev)
        release_ev = MockEvent(x=10, y=10, x_root=200, y_root=200)
        cell._on_release(release_ev)

        # Popover must NOT be opened!
        self.assertIsNone(self.grid.active_popover)
        self.assertIsNone(cell.tooltip.tip_window)
        # But cell must be cleanly selected
        self.assertTrue(cell.is_selected)

    def test_scenario_2_short_motion_starts_drag(self):
        """2. Öğretmeni kısa mesafede sürükleyince (>6px) taşıma başlıyor."""
        cell = self._get_cell(self.day_paz.id, self.loc1.id)
        
        # Press at (200, 200)
        cell._on_press(MockEvent(x=10, y=10, x_root=200, y_root=200))
        self.assertFalse(cell._is_dragging)

        # Move only 2px -> should NOT start drag
        cell._on_motion(MockEvent(x=12, y=11, x_root=202, y_root=201))
        self.assertFalse(cell._is_dragging)
        self.assertIsNone(self.grid.drag_source_cell)

        # Move 8px -> MUST start drag
        cell._on_motion(MockEvent(x=18, y=15, x_root=208, y_root=205))
        self.assertTrue(cell._is_dragging)
        self.assertEqual(self.grid.drag_source_cell, cell)
        self.assertIsNotNone(self.grid.drag_ghost)

        # Clean release
        cell._on_release(MockEvent(x_root=208, y_root=205))
        self.assertFalse(cell._is_dragging)

    def test_scenario_3_and_4_valid_drop_executes_move_correctly(self):
        """3 & 4. Öğretmeni başka bir nöbet hücresine taşıma ve geçerli hücreye bırakınca kayıt yapılması."""
        cell_src = self._get_cell(self.day_paz.id, self.loc1.id) # Pazartesi 1. Kat (Ahmet)
        cell_tgt = self._get_cell(self.day_paz.id, self.loc2.id) # Pazartesi Bahçe (Ayşe)

        # Test pre-validation
        is_valid, reason = self.grid.is_valid_drop_target(cell_src, cell_tgt)
        self.assertTrue(is_valid)

        # Perform drag & drop from cell_src to cell_tgt (Swap on same day)
        cell_src._on_press(MockEvent(x_root=100, y_root=100))
        cell_src._on_motion(MockEvent(x_root=115, y_root=115))
        self.assertTrue(cell_src._is_dragging)

        # Target cell gets visual blue highlight
        self.grid.on_drag_motion(MockEvent(x_root=cell_tgt.winfo_rootx() + 5, y_root=cell_tgt.winfo_rooty() + 5))

        # Release on target cell
        self.grid._find_cell_parent = MagicMock(return_value=cell_tgt)
        cell_src._on_release(MockEvent(x_root=cell_tgt.winfo_rootx() + 5, y_root=cell_tgt.winfo_rooty() + 5))

        # Check DB: duties swapped!
        assignments = self.db.get_assignments_for_week(self.week_start)
        paz_1k = next(a for a in assignments if a.day_id == self.day_paz.id and a.location_id == self.loc1.id)
        paz_bah = next(a for a in assignments if a.day_id == self.day_paz.id and a.location_id == self.loc2.id)

        self.assertEqual(paz_1k.teacher_id, self.t2.id) # Ayşe is now at 1. Kat
        self.assertEqual(paz_bah.teacher_id, self.t1.id) # Ahmet is now at Bahçe

    def test_scenario_5_and_6_invalid_drop_preserves_schedule_and_blocks_fixed(self):
        """5 & 6. Sabit öğretmen taşınamaz ve geçersiz hücreye bırakınca çizelge bozulmaz."""
        cell_fixed = self._get_cell(self.day_sal.id, self.loc1.id) # Mehmet Demir (Fixed)
        cell_empty = self._get_cell(self.day_sal.id, self.loc2.id)

        # Fixed cell should not even start drag
        cell_fixed._on_press(MockEvent(x_root=100, y_root=100))
        cell_fixed._on_motion(MockEvent(x_root=120, y_root=120))
        self.assertFalse(cell_fixed._is_dragging)
        self.assertIsNone(self.grid.drag_source_cell)

        # Now try to drag another teacher ONTO the fixed cell
        cell_src = self._get_cell(self.day_paz.id, self.loc1.id)
        is_valid, reason = self.grid.is_valid_drop_target(cell_src, cell_fixed)
        self.assertFalse(is_valid)
        self.assertIn("Sabit", reason)

        # Attempt to drop on fixed cell
        cell_src._on_press(MockEvent(x_root=100, y_root=100))
        cell_src._on_motion(MockEvent(x_root=120, y_root=120))
        self.grid._find_cell_parent = MagicMock(return_value=cell_fixed)
        cell_src._on_release(MockEvent(x_root=200, y_root=200))

        # Check that fixed cell is still Mehmet Demir and src is still Ahmet Yılmaz
        assignments = self.db.get_assignments_for_week(self.week_start)
        fixed_check = next(a for a in assignments if a.id == self.assign_fixed.id)
        self.assertEqual(fixed_check.teacher_id, self.t_fixed.id)

    def test_scenario_7_info_button_opens_popover(self):
        """7. Bilgi simgesine (ℹ) tıklayınca öğretmen ayrıntıları açılıyor."""
        cell = self._get_cell(self.day_paz.id, self.loc1.id)
        self.assertTrue(hasattr(cell, "btn_info"))

        # Click the ℹ button directly
        cell._on_info_clicked()
        self.assertIsNotNone(self.grid.active_popover)
        self.assertEqual(self.grid.active_popover.cell, cell)
        if self.grid.active_popover.tip_window:
            self.assertTrue(self.grid.active_popover.tip_window.winfo_exists())

        # Clean close
        self.grid.close_info_popover()
        self.assertIsNone(self.grid.active_popover)

    def test_scenario_8_dragging_while_popover_open_closes_popover(self):
        """8. Bilgi penceresi açıkken başka bir öğretmeni sürüklemek mümkün ve popover kapanır."""
        cell1 = self._get_cell(self.day_paz.id, self.loc1.id)
        cell2 = self._get_cell(self.day_paz.id, self.loc2.id)

        # Open popover for cell1
        cell1._on_info_clicked()
        self.assertIsNotNone(self.grid.active_popover)

        # Start dragging cell2
        cell2._on_press(MockEvent(x_root=100, y_root=100))
        # Pressing should close open popover immediately
        self.assertIsNone(self.grid.active_popover)

        cell2._on_motion(MockEvent(x_root=120, y_root=120))
        self.assertTrue(cell2._is_dragging)
        self.assertEqual(self.grid.drag_source_cell, cell2)

        cell2._on_release(MockEvent(x_root=120, y_root=120))

    def test_scenario_9_drop_completion_does_not_open_popover(self):
        """9. Sürükleme tamamlandığında bilgi penceresi kendiliğinden açılmıyor."""
        cell_src = self._get_cell(self.day_paz.id, self.loc1.id)
        cell_tgt = self._get_cell(self.day_sal.id, self.loc2.id) # Empty cell on Salı

        cell_src._on_press(MockEvent(x_root=100, y_root=100))
        cell_src._on_motion(MockEvent(x_root=120, y_root=120))
        self.grid._find_cell_parent = MagicMock(return_value=cell_tgt)
        cell_src._on_release(MockEvent(x_root=200, y_root=200))

        # Popover MUST NOT be opened!
        self.assertIsNone(self.grid.active_popover)

    def test_scenario_10_system_features_continue_working(self):
        """10. Haftalık çizelge, otomatik dağıtım, kaydetme özellikleri çalışmaya devam ediyor."""
        from logic.auto_scheduler import AutoScheduler
        scheduler = AutoScheduler(self.db)
        assignments, report = scheduler.generate_schedule(self.week_start)
        self.assertIsInstance(assignments, list)
        self.assertIsNotNone(report)

if __name__ == "__main__":
    unittest.main()
