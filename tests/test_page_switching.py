import unittest
import customtkinter as ctk
from pathlib import Path
import tempfile
import shutil

from core.database import Database
from ui.app import MainApp


class TestPageSwitching(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_switch.db"
        self.db = Database(self.db_path)
        self.db.init_db()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_switch_between_teachers_and_reports(self):
        app = MainApp()
        app.withdraw()
        app.update()

        # Öğretmenler sayfasına geçiş
        app.switch_page("teachers")
        app.update()
        self.assertEqual(app.current_page_key, "teachers")
        self.assertIsNotNone(app.current_page_frame)

        # Raporlar sayfasına geçiş
        app.switch_page("reports")
        app.update()
        self.assertEqual(app.current_page_key, "reports")
        self.assertIsNotNone(app.current_page_frame)

        # Haftalık nöbet sayfasına dönüş
        app.switch_page("weekly")
        app.update()
        self.assertEqual(app.current_page_key, "weekly")

        # Tekrar öğretmenlere ve raporlara geçiş
        app.switch_page("teachers")
        app.update()
        self.assertEqual(app.current_page_key, "teachers")

        app.switch_page("reports")
        app.update()
        self.assertEqual(app.current_page_key, "reports")

        app.destroy()


if __name__ == "__main__":
    unittest.main()
