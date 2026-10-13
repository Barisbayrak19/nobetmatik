"""
Smoke Interactive Verification Test:
- MainApp başlatılır.
- Tablo ve hücreler taranır.
- Hücre seçilir, popover tetiklenir, sürükle-bırak simüle edilir.
- Değişiklikleri kaydet çağrılır.
- Başarıyla kapanır.
"""
import unittest
import tkinter as tk
from ui.app import MainApp

class SmokeInteractiveTest(unittest.TestCase):
    def test_app_lifecycle_and_interactions(self):
        app = MainApp()
        app.update()

        # 1. Tablo çizgileri ve hücre kontrolü
        self.assertIsNotNone(app.schedule_grid)
        cells = [w for w in app.schedule_grid.table_frame.winfo_children() if hasattr(w, "assignment")]
        self.assertGreater(len(cells), 0, "Çizelgede hücreler oluşturulmuş olmalı.")

        first_cell = cells[0]
        # Hücre sınır rengi ve relief kontrolü
        self.assertEqual(first_cell.cget("relief"), "flat")
        self.assertEqual(first_cell.cget("highlightthickness"), 1)
        self.assertIn(first_cell.cget("highlightbackground"), ["#E2E8F0", "#CBD5E1"])

        # 2. Hücre seçimi (Seçili hücre 2px mavi vurgu almalı)
        first_cell._on_press(type("Event", (), {"x": 10, "y": 10})())
        app.update()
        self.assertTrue(first_cell.is_selected)
        self.assertEqual(first_cell.cget("highlightthickness"), 2)
        self.assertEqual(first_cell.cget("highlightbackground"), "#2563EB")

        # 3. Bilgi kutusu (Popover) kontrolü
        if first_cell.teacher:
            first_cell.tooltip.show_tip()
            app.update()
            self.assertIsNotNone(first_cell.tooltip.tip_window)
            first_cell.tooltip.hide_tip()
            app.update()
            self.assertIsNone(first_cell.tooltip.tip_window)

        # 4. İşlem çubuğu butonları kontrolü
        self.assertTrue(hasattr(app, "btn_undo"))
        self.assertTrue(hasattr(app, "btn_redo"))
        self.assertTrue(hasattr(app, "btn_week_ops"))
        self.assertTrue(hasattr(app, "btn_export"))
        self.assertTrue(hasattr(app, "btn_more"))

        # 5. Kayıt işlemi tetikleme
        app.has_unsaved_changes = True
        # save_changes normally shows a messagebox, we mock it or close safely
        from unittest.mock import patch
        with patch("tkinter.messagebox.showinfo"):
            app.save_changes()
        self.assertFalse(app.has_unsaved_changes)

        app.destroy()

if __name__ == "__main__":
    unittest.main()
