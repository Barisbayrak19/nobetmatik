"""
Test UI Improvements (v2.0.1 Son Arayüz İyileştirmeleri Testi)
- Tablo çizgileri (1px açık gri-mavi #CBD5E1, flat relief, siyah çizgi yok)
- Öğretmen bilgi kutusu (kompakt popover, hücrenin yanında, kaydırma destekli)
- Tablo yerleşimi (kompakt genişlikler, canvas stretch)
- İşlem çubuğu (Otomatik Dağıt ve Değişiklikleri Kaydet öne çıkan butonlar, ikincil açılır menüler)
"""
import unittest
import tkinter as tk
from core.database import Database
from core.models import Assignment, Teacher, Location, Day
from logic.duty_service import DutyService
from ui.schedule_grid import ScheduleGrid, CellWidget, GridTooltip
from ui.theme import GRID_BORDER_COLOR, GRID_RELIEF, COLOR_CELL_SELECTED
import ui.theme as theme
from ui.app import MainApp

class TestUIImprovements(unittest.TestCase):
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
        import tempfile, os
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.temp_dir.name, "test_ui.db")
        self.db = Database(db_path)
        self.db.init_db()
        self.duty_service = DutyService(self.db)
        # Sample teacher, location, day
        self.teacher = Teacher(id="t1", name="Ahmet Yılmaz", branch="Matematik")
        self.db.add_teacher(self.teacher)
        self.loc = Location(id="loc1", name="Bahçe", capacity=1)
        self.db.save_location(self.loc)
        self.day = Day(name="Pazartesi", order_num=1)
        self.db.save_day(self.day)
        self.days = self.db.get_days()
        self.week_start = "2026-09-28"

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_theme_grid_relief_and_color(self):
        """1. Tablo çizgilerinin #E2E8F0 veya #CBD5E1 ve flat relief olduğunu doğrula."""
        self.assertIn(theme.GRID_BORDER_COLOR, ["#E2E8F0", "#CBD5E1"])
        self.assertEqual(theme.GRID_RELIEF, "flat")

    def test_cell_widget_borders_and_styling(self):
        """1. Hücre sınırlarının siyah olmadığını ve açık gri olduğunu doğrula."""
        assign = Assignment(
            week_start=self.week_start,
            day_id=self.day.id,
            location_id=self.loc.id,
            slot_index=0,
            teacher_id=self.teacher.id,
            fixed=False
        )
        dummy_controller = ScheduleGrid(
            parent=self.root,
            db=self.db,
            duty_service=self.duty_service,
            get_current_week=lambda: self.week_start,
            on_data_changed=lambda: None
        )
        cell = CellWidget(
            parent=self.root,
            assignment=assign,
            teacher=self.teacher,
            day=self.day,
            location=self.loc,
            slot_index=0,
            grid_controller=dummy_controller
        )

        # relief flat olmalı, highlightthickness 1 olmalı
        self.assertEqual(cell.cget("relief"), "flat")
        self.assertEqual(cell.cget("highlightthickness"), 1)
        self.assertIn(cell.cget("highlightbackground"), ["#E2E8F0", "#CBD5E1"])

        # Seçildiğinde 2px mavi olmalı
        cell.set_selected(True)
        self.assertEqual(cell.cget("highlightthickness"), 2)
        self.assertEqual(cell.cget("highlightbackground"), theme.COLOR_CELL_SELECTED_BORDER)

        # Seçim kalktığında geri dönmeli
        cell.set_selected(False)
        self.assertEqual(cell.cget("highlightthickness"), 1)
        self.assertIn(cell.cget("highlightbackground"), ["#E2E8F0", "#CBD5E1"])

        dummy_controller.destroy()
        cell.destroy()

    def test_grid_tooltip_popover_creation(self):
        """2. Bilgi kutusunun kompakt popover ve hücreye bağlı olduğunu doğrula."""
        assign = Assignment(
            week_start=self.week_start,
            day_id=self.day.id,
            location_id=self.loc.id,
            slot_index=0,
            teacher_id=self.teacher.id,
            fixed=False
        )
        controller = ScheduleGrid(
            parent=self.root,
            db=self.db,
            duty_service=self.duty_service,
            get_current_week=lambda: self.week_start,
            on_data_changed=lambda: None
        )
        cell = CellWidget(
            parent=self.root,
            assignment=assign,
            teacher=self.teacher,
            day=self.day,
            location=self.loc,
            slot_index=0,
            grid_controller=controller
        )

        self.assertIsNotNone(cell.tooltip)
        self.assertEqual(cell.tooltip.cell, cell)
        
        # Tooltip show & hide testi
        cell.tooltip.show_tip()
        if cell.tooltip.tip_window:
            self.assertTrue(cell.tooltip.tip_window.winfo_exists())
            cell.tooltip.hide_tip()
            self.assertIsNone(cell.tooltip.tip_window)

        controller.destroy()
        cell.destroy()

    def test_action_bar_structure_and_buttons(self):
        """4. İşlem çubuğunda Otomatik Dağıt, Kaydet ve ikincil açılır menülerin varlığını doğrula."""
        app = MainApp()
        app.withdraw()

        # Otomatik Dağıt ana mavi buton
        self.assertTrue(hasattr(app, "open_auto_distribution"))
        # Kaydet ana yeşil buton
        self.assertTrue(hasattr(app, "save_changes"))
        # Hafta işlemleri açılır menüsü
        self.assertTrue(hasattr(app, "btn_week_ops"))
        self.assertTrue(hasattr(app, "week_ops_menu"))
        self.assertTrue(hasattr(app, "open_week_ops_menu"))
        # Çıktılar menüsü
        self.assertTrue(hasattr(app, "btn_export"))
        self.assertTrue(hasattr(app, "export_menu"))
        # Daha fazla menüsü
        self.assertTrue(hasattr(app, "btn_more"))
        # Detay paneli kaldırıldı (tam genişlikte ızgara)
        self.assertIsNone(app.detail_panel)

        # 1. İstatistik / KPI barının kaldırıldığını doğrula
        self.assertIsNone(app.kpi_cards_frame)

        # 5. Toolbar düğmelerinin 32px yükseklikte ve standart oklarda olduğunu doğrula
        self.assertEqual(app.btn_distribute.cget("height"), 32)
        self.assertEqual(app.btn_save.cget("height"), 32)
        self.assertEqual(app.btn_shift.cget("height"), 32)
        self.assertEqual(app.btn_announcements.cget("height"), 32)
        # İkame Sistemi öne çıkan buton ve menü doğrulaması
        self.assertTrue(hasattr(app, "btn_substitution"))
        self.assertEqual(app.btn_substitution.cget("height"), 32)
        self.assertIn("İkame", app.btn_substitution.cget("text"))
        self.assertIn("substitution", app.sidebar_buttons)

        # 6. Sidebar 3px aktif vurgu çizgisini doğrula
        self.assertIn("weekly", app.sidebar_indicators)
        self.assertEqual(app.sidebar_indicators["weekly"].cget("width"), 3)

        app.destroy()

    def test_branch_format_and_cell_typography(self):
        """2, 3 ve 4. İstekler: Branş metninin kırpılmaması, sabit isim yüksekliği, açık başlıklar ve nötr rozetler."""
        from ui.schedule_grid import format_branch_display
        # Kırpma olmamalı
        self.assertEqual(format_branch_display("Din Kültürü ve Ahlak Bilgisi"), "Din Kültürü ve Ahlak Bilgisi")
        self.assertEqual(format_branch_display("Teknoloji ve Tasarım"), "Teknoloji ve Tasarım")

        assign = Assignment(
            week_start=self.week_start,
            day_id=self.day.id,
            location_id=self.loc.id,
            slot_index=0,
            teacher_id=self.teacher.id,
            fixed=True
        )
        controller = ScheduleGrid(
            parent=self.root,
            db=self.db,
            duty_service=self.duty_service,
            get_current_week=lambda: self.week_start,
            on_data_changed=lambda: None
        )
        cell = CellWidget(
            parent=self.root,
            assignment=assign,
            teacher=self.teacher,
            day=self.day,
            location=self.loc,
            slot_index=0,
            grid_controller=controller
        )

        # Sabit isim kutusu yüksekliği (38px min-h dengesi)
        self.assertTrue(hasattr(cell, "name_container"))
        self.assertEqual(cell.name_container.cget("height"), 38)

        # Branş etiketi
        self.assertTrue(hasattr(cell, "lbl_branch"))
        self.assertEqual(cell.lbl_branch.cget("text_color"), "#64748B")

        # Nötr rozet
        self.assertTrue(hasattr(cell, "badge_free"))
        self.assertEqual(cell.badge_free.cget("fg_color"), "#F1F5F9")
        self.assertNotIn("🟢", cell.lbl_free.cget("text"))

        # Sabit kilit rozeti
        self.assertTrue(hasattr(cell, "badge_lock"))

        controller.destroy()
        cell.destroy()

    def test_button_design_system_variants(self):
        """Düğme Tasarım Sistemi (Button Design System) kılavuz standartlarını test eder."""
        from ui.theme import create_modern_button, BTN_RADIUS, COLOR_BTN_PRIMARY_DARK_BG, COLOR_BTN_SECONDARY_BORDER

        # 1. Primary Dark (Koyu Lacivert)
        btn_prim = create_modern_button(self.root, text="+ Nöbet Ekle", variant="primary")
        self.assertEqual(btn_prim.cget("fg_color"), COLOR_BTN_PRIMARY_DARK_BG)
        self.assertEqual(btn_prim.cget("text_color"), "#FFFFFF")
        self.assertEqual(btn_prim.cget("corner_radius"), BTN_RADIUS)
        btn_prim.destroy()

        # 2. Secondary / Outline (Beyaz zemin, ince sınır, açık mavi hover)
        btn_sec = create_modern_button(self.root, text="Taslak Olarak Kaydet", variant="default")
        self.assertEqual(btn_sec.cget("fg_color"), "#FFFFFF")
        self.assertEqual(btn_sec.cget("border_width"), 1)
        self.assertEqual(btn_sec.cget("border_color"), COLOR_BTN_SECONDARY_BORDER)
        self.assertEqual(btn_sec.cget("corner_radius"), BTN_RADIUS)
        btn_sec.destroy()

        # 3. Success (Onayla)
        btn_suc = create_modern_button(self.root, text="✓ Onayla", variant="success")
        self.assertEqual(btn_suc.cget("fg_color"), "#059669")
        self.assertEqual(btn_suc.cget("text_color"), "#FFFFFF")
        btn_suc.destroy()

        # 4. Danger (Reddet)
        btn_dan = create_modern_button(self.root, text="✕ Reddet", variant="danger")
        self.assertEqual(btn_dan.cget("fg_color"), "#DC2626")
        self.assertEqual(btn_dan.cget("text_color"), "#FFFFFF")
        btn_dan.destroy()

        # 5. Segmented Active / Inactive
        btn_seg_act = create_modern_button(self.root, text="Günlük", variant="segmented_active")
        btn_seg_inact = create_modern_button(self.root, text="Haftalık", variant="segmented_inactive")
        self.assertEqual(btn_seg_act.cget("fg_color"), COLOR_BTN_PRIMARY_DARK_BG)
        self.assertEqual(btn_seg_inact.cget("fg_color"), "#FFFFFF")
        self.assertEqual(btn_seg_inact.cget("border_width"), 1)
        btn_seg_act.destroy()
        btn_seg_inact.destroy()

    def test_feedback_rate_limiting(self):
        """Geri bildirim kısıtlama kuralları (günlük 20 limit, cooldown, içerik doğrulama) testi."""
        import datetime
        from logic.feedback_service import FeedbackService, FeedbackData
        import tempfile
        from pathlib import Path

        # Geçici feedbacks dosyasıyla test
        temp_file = Path(self.temp_dir.name) / "test_feedbacks.json"
        orig_file = FeedbackService.LOCAL_STORAGE_FILE
        FeedbackService.LOCAL_STORAGE_FILE = temp_file

        try:
            # 1. Kısa konu veya mesaj reddedilmeli
            fb_short_subj = FeedbackData(
                category="Öneri", school_name="Okul", sender_name="Ali",
                contact="", subject="Kısa", message="Yeterince uzun bir mesaj gövdesi",
                include_logs=False
            )
            ok, msg = FeedbackService.validate_and_check_rate_limit(fb_short_subj, self.db)
            self.assertFalse(ok)
            self.assertIn("en az 5 karakter", msg)

            fb_short_msg = FeedbackData(
                category="Öneri", school_name="Okul", sender_name="Ali",
                contact="", subject="Geçerli Konu", message="Kısa",
                include_logs=False
            )
            ok, msg = FeedbackService.validate_and_check_rate_limit(fb_short_msg, self.db)
            self.assertFalse(ok)
            self.assertIn("en az 10 karakter", msg)

            # 2. Geçerli mesaj ilk seferde onaylanmalı
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            fb_valid1 = FeedbackData(
                category="Öneri", school_name="Okul", sender_name="Ali",
                contact="", subject="Geçerli Konu 1", message="Bu bir test mesajı metnidir.",
                include_logs=False, created_at=now_str
            )
            ok, _ = FeedbackService.validate_and_check_rate_limit(fb_valid1, self.db)
            self.assertTrue(ok)

            # Kaydedildiğini simüle et
            FeedbackService.save_local_feedback(fb_valid1)
            FeedbackService._record_rate_limit(fb_valid1, self.db)

            # 3. Aynı mesajın tekrarı engellenmeli
            ok, msg = FeedbackService.validate_and_check_rate_limit(fb_valid1, self.db)
            self.assertFalse(ok)
            self.assertIn("aynı mesajı", msg.lower())

            # 4. Cooldown (2 dakika / 120 sn) testi
            fb_diff = FeedbackData(
                category="Öneri", school_name="Okul", sender_name="Ali",
                contact="", subject="Farklı Konu 2", message="Bu da tamamen farklı bir açıklama metnidir.",
                include_logs=False
            )
            # Henüz 120 sn geçmediği için cooldown tetiklenmeli
            ok, msg = FeedbackService.validate_and_check_rate_limit(fb_diff, self.db)
            self.assertFalse(ok)
            self.assertIn("bekleyiniz", msg)

            # 5. Günlük 20 limit testi
            import datetime
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            self.db.set_setting("feedback_daily_date", today_str)
            self.db.set_setting("feedback_daily_count", "20")

            ok, msg = FeedbackService.validate_and_check_rate_limit(fb_diff, self.db)
            self.assertFalse(ok)
            self.assertIn("20 adet", msg)

            used, rem = FeedbackService.get_daily_stats(self.db)
            self.assertEqual(used, 20)
            self.assertEqual(rem, 0)

        finally:
            FeedbackService.LOCAL_STORAGE_FILE = orig_file


if __name__ == "__main__":
    unittest.main()
