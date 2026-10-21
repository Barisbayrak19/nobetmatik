"""
Ana Uygulama Penceresi (Main Window)
İlk kurulum sihirbazı geçişi, hafta yönetimi, araç çubuğu, kısayollar ve dışa aktarım menüleri.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import datetime
from pathlib import Path
from typing import Optional
import customtkinter as ctk

from core.database import Database
from core.undo_manager import UndoManager
from core.config import APP_NAME, APP_VERSION, EXPORTS_DIR, ICON_PATH, DEFAULT_GITHUB_REPO
from logic.duty_service import DutyService
from logic.backup_service import BackupService
from logic.export_service import ExportService
from core.logger import logger

from ui.theme import (
    setup_styles, setup_customtkinter, COLOR_BG, COLOR_HEADER_BG, COLOR_HEADER_TEXT,
    COLOR_PRIMARY, COLOR_SUCCESS, COLOR_BORDER, COLOR_BORDER_STRONG, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED,
    COLOR_SIDEBAR_BG, COLOR_SIDEBAR_ACTIVE, COLOR_SIDEBAR_HOVER, COLOR_SIDEBAR_TEXT, COLOR_SIDEBAR_MUTED,
    COLOR_BADGE_FREE, COLOR_BADGE_FREE_TXT, COLOR_BADGE_FIXED, COLOR_BADGE_FIXED_TXT,
    COLOR_BADGE_EMPTY, COLOR_BADGE_EMPTY_TXT, COLOR_CELL_SELECTED, COLOR_CELL_SELECTED_BORDER,
    COLOR_TRAFFIC_RED, COLOR_TRAFFIC_YELLOW, COLOR_TRAFFIC_GREEN, COLOR_CARD, CARD_RADIUS, BTN_RADIUS,
    FONT_FAMILY
)
from ui.schedule_grid import TURKISH_MONTHS
from logic.substitution_service import PERIOD_TIMES
from ui.wizard_view import WizardView
from ui.schedule_grid import ScheduleGrid
from ui.teacher_management import TeacherManagementView, TeacherManagementDialog
from ui.location_management import LocationManagementView, LocationManagementDialog
from ui.distribution_dialog import DistributionView, DistributionDialog
from ui.import_dialog import ImportView, ImportDialog
from ui.backup_dialog import BackupView, BackupDialog
from ui.settings_dialog import SettingsView, SettingsDialog
from ui.reports_view import ReportsView
from ui.shift_dialog import ShiftDialog
from ui.substitution_dialog import SubstitutionDialog
from ui.attendance_dialog import AttendanceDialog
from ui.timetable_export_dialog import TimetableExportDialog

class SimpleTooltip:
    """Kompakt ve şık düğme ipucu (Tooltip) yöneticisi."""
    def __init__(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        self.tip = None
        self._after_id = None
        self.widget.bind("<Enter>", self._on_enter, add="+")
        self.widget.bind("<Leave>", self._on_leave, add="+")
        self.widget.bind("<ButtonPress>", self._hide, add="+")

    def _on_enter(self, event=None):
        self._cancel()
        self._after_id = self.widget.after(300, self._show)

    def _on_leave(self, event=None):
        self._cancel()
        self._hide()

    def _cancel(self):
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self):
        if self.tip:
            return
        try:
            x = self.widget.winfo_rootx() + 4
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
            self.tip = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            tw.attributes("-topmost", True)
            lbl = tk.Label(
                tw,
                text=self.text,
                font=(FONT_FAMILY, 9),
                bg="#1C1C1E",
                fg="#FFFFFF",
                padx=8,
                pady=4,
                relief="flat",
                bd=0
            )
            lbl.pack()
        except Exception:
            pass

    def _hide(self, event=None):
        if self.tip:
            try:
                self.tip.destroy()
            except Exception:
                pass
            self.tip = None

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        setup_customtkinter()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1280x800")
        self.minsize(1180, 720)

        if ICON_PATH.exists():
            try:
                self.iconbitmap(str(ICON_PATH))
            except Exception:
                pass

        # Temel Servisler
        self.db = Database()
        self.undo_manager = UndoManager()
        self.duty_service = DutyService(self.db, self.undo_manager)
        self.backup_service = BackupService()
        self.export_service = ExportService(self.db)

        # Hafta Yönetimi (Pazartesi bazlı - Güncel Takvim Haftası)
        today = datetime.date.today()
        self.current_week_start = today - datetime.timedelta(days=today.weekday())
        self.has_unsaved_changes = False

        setup_styles(self, self.db)

        # Klavye Kısayolları
        self.bind("<Control-z>", lambda e: self.do_undo())
        self.bind("<Control-y>", lambda e: self.do_redo())
        self.bind("<Control-s>", lambda e: self.save_changes())

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # İlk Kurulum Kontrolü
        school = self.db.get_school_info()
        if not school.installed:
            self.show_wizard()
        else:
            self.show_main_view()

    def show_wizard(self):
        for w in self.winfo_children():
            w.destroy()
        wizard = WizardView(self, self.db, on_complete=self.show_main_view)
        wizard.pack(fill="both", expand=True)

    def show_main_view(self):
        for w in self.winfo_children():
            w.destroy()

        # Ana Düzen: Sol Modern Sidebar + Sağ Ana İçerik Alanı
        self._build_sidebar()

        self.main_container = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        self.main_container.pack(side="left", fill="both", expand=True)

        self._build_top_header()

        # Dinamik Güncelleme & Bildirim Bandı Alanı (Modern Banner)
        self.update_banner_container = ctk.CTkFrame(self.main_container, fg_color="transparent")

        # SPA Ana İçerik Alanı
        self.content_container = ctk.CTkFrame(self.main_container, fg_color="transparent", corner_radius=0)
        self.content_container.pack(fill="both", expand=True)

        # 1. Haftalık Nöbet Sayfası (Kalıcı - State ASLA kaybolmaz)
        self.page_weekly = ctk.CTkFrame(self.content_container, fg_color="transparent", corner_radius=0)
        self._build_footer(self.page_weekly)
        self._build_kpi_cards(self.page_weekly)
        self._build_action_bar(self.page_weekly)
        self._build_workspace(self.page_weekly)

        # Sayfa Görünümleri Sözlüğü (Lazy Cache)
        self.page_views = {"weekly": self.page_weekly}
        self.current_page_key = "weekly"
        self.current_page_frame = self.page_weekly
        self.page_weekly.pack(fill="both", expand=True)

        self.undo_manager.register_callback(self.update_undo_redo_ui)
        self.update_header_info()
        self.after(600, self._check_announcements_background)
        self.after(1200, self._check_updates_background)

    def get_current_week_str(self) -> str:
        return self.current_week_start.isoformat()

    # --- 1. SOL MODERN NAVİGASYON (SIDEBAR - macOS SONOMA / SEQUOIA STYLE) ---
    def _build_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(
            self,
            width=220,
            fg_color=COLOR_SIDEBAR_BG,
            corner_radius=0
        )
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)

        # macOS Pencere Trafik Işıkları (Traffic Lights - Red, Yellow, Green)
        traffic_box = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        traffic_box.pack(anchor="w", padx=18, pady=(16, 6))
        for col in (COLOR_TRAFFIC_RED, COLOR_TRAFFIC_YELLOW, COLOR_TRAFFIC_GREEN):
            dot = ctk.CTkFrame(traffic_box, width=12, height=12, corner_radius=6, fg_color=col)
            dot.pack(side="left", padx=(0, 6))
            dot.pack_propagate(False)

        # Üst Okul & Yönetici Bilgi Kartı
        school = self.db.get_school_info()
        brand_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        brand_frame.pack(fill="x", padx=16, pady=(10, 12))

        lbl_logo = ctk.CTkLabel(
            brand_frame,
            text="🛡️ NöbetMatik",
            font=ctk.CTkFont(family=FONT_FAMILY, size=17, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_logo.pack(anchor="w", pady=(0, 8))

        self.lbl_sidebar_school = ctk.CTkLabel(
            brand_frame,
            text=school.name if school.name else "Okul Yönetim Sistemi",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color="#FFFFFF",
            wraplength=188,
            justify="left"
        )
        self.lbl_sidebar_school.pack(anchor="w", pady=(0, 6))

        self.lbl_sidebar_year = ctk.CTkLabel(
            brand_frame,
            text=f"🎓 {school.academic_year or '2026-2027'} Eğitim Yılı",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLOR_PRIMARY,
            fg_color="#27272A",
            corner_radius=6,
            padx=8,
            pady=3
        )
        self.lbl_sidebar_year.pack(anchor="w", pady=(0, 6))

        self.lbl_sidebar_principal = ctk.CTkLabel(
            brand_frame,
            text=f"Müdür: {school.principal_name}" if school.principal_name else "Müdürlük",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_SIDEBAR_MUTED,
            wraplength=188,
            justify="left"
        )
        self.lbl_sidebar_principal.pack(anchor="w", pady=(0, 2))

        # İnce ayırıcı çizgi
        div1 = ctk.CTkFrame(self.sidebar_frame, fg_color="#27272A", height=1)
        div1.pack(fill="x", padx=12, pady=(8, 8))

        # 1. ANA MENÜ Başlığı
        lbl_main_title = ctk.CTkLabel(
            self.sidebar_frame,
            text="ANA MENÜ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color="#71717A"
        )
        lbl_main_title.pack(anchor="w", padx=16, pady=(0, 4))

        self.sidebar_buttons = {}
        self.sidebar_indicators = {}

        main_nav_items = [
            ("weekly", "📅  Haftalık Nöbet"),
            ("substitution", "🔄  İkame Sistemi"),
            ("teachers", "👥  Öğretmenler"),
            ("locations", "📍  Nöbet Yerleri"),
            ("distribute", "⚡  Otomatik Dağıtım"),
            ("import", "📥  İçe Aktarma"),
            ("reports", "📊  Raporlar"),
        ]

        def _create_sidebar_pill(key: str, text: str, is_active: bool = False):
            row = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent", height=36)
            row.pack(fill="x", padx=(0, 8), pady=2)
            row.pack_propagate(False)

            ind = ctk.CTkFrame(
                row,
                width=3,
                corner_radius=1,
                fg_color=COLOR_PRIMARY if is_active else "transparent"
            )
            ind.pack(side="left", fill="y", padx=(0, 6), pady=4)

            btn = ctk.CTkButton(
                row,
                text=text,
                height=34,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold" if is_active else "normal"),
                anchor="w",
                fg_color=COLOR_PRIMARY if is_active else "transparent",
                hover_color=COLOR_PRIMARY if is_active else COLOR_SIDEBAR_HOVER,
                text_color="#FFFFFF" if is_active else "#D4D4D8",
                corner_radius=8,
                border_width=0,
                command=lambda k=key: self.switch_page(k)
            )
            btn.pack(side="left", fill="both", expand=True)
            self.sidebar_buttons[key] = btn
            self.sidebar_indicators[key] = ind

        for key, text in main_nav_items:
            _create_sidebar_pill(key, text, is_active=(key == "weekly"))

        # İnce ayırıcı çizgi
        div2 = ctk.CTkFrame(self.sidebar_frame, fg_color="#27272A", height=1)
        div2.pack(fill="x", padx=12, pady=(10, 8))

        # 2. SİSTEM Menü Başlığı
        lbl_sys_title = ctk.CTkLabel(
            self.sidebar_frame,
            text="SİSTEM",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color="#71717A"
        )
        lbl_sys_title.pack(anchor="w", padx=16, pady=(0, 4))

        system_nav_items = [
            ("backup", "💾  Veri Yedekleme"),
            ("settings", "⚙️  Ayarlar"),
            ("announcements", "🔔  Duyurular"),
            ("feedback", "💬  Geri Bildirim"),
        ]

        for key, text in system_nav_items:
            _create_sidebar_pill(key, text, is_active=False)

        # Alt Alan: Dinamik & Şık Sürüm / Güncelleme Kartı
        self.sidebar_version_card = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.sidebar_version_card.pack(side="bottom", fill="x", padx=10, pady=12)

        div3 = ctk.CTkFrame(self.sidebar_version_card, fg_color="#27272A", height=1)
        div3.pack(fill="x", pady=(0, 8))

        self.sidebar_ver_box = ctk.CTkFrame(self.sidebar_version_card, fg_color="transparent")
        self.sidebar_ver_box.pack(fill="x", padx=4)

        self.lbl_sidebar_version = ctk.CTkLabel(
            self.sidebar_ver_box,
            text=f"🟢 v{APP_VERSION}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLOR_SIDEBAR_MUTED
        )
        self.lbl_sidebar_version.pack(side="left")

        self.btn_sidebar_check = ctk.CTkButton(
            self.sidebar_ver_box,
            text="🔄",
            width=26,
            height=24,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color="transparent",
            hover_color=COLOR_SIDEBAR_HOVER,
            text_color="#A1A1AA",
            corner_radius=6,
            command=self.check_updates_manual
        )
        self.btn_sidebar_check.pack(side="right")
        SimpleTooltip(self.btn_sidebar_check, "Güncellemeleri Denetle")

    def _update_sidebar_active(self, active_key: str):
        for key, btn in self.sidebar_buttons.items():
            is_active = (key == active_key)
            btn.configure(
                fg_color=COLOR_PRIMARY if is_active else "transparent",
                hover_color=COLOR_PRIMARY if is_active else COLOR_SIDEBAR_HOVER,
                text_color="#FFFFFF" if is_active else "#D4D4D8",
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold" if is_active else "normal")
            )
            if hasattr(self, "sidebar_indicators") and key in self.sidebar_indicators:
                self.sidebar_indicators[key].configure(
                    fg_color=COLOR_PRIMARY if is_active else "transparent"
                )

    def switch_page(self, key: str):
        if key == "announcements":
            self.open_announcements_dialog()
            return
        if key == "feedback":
            self.open_feedback_dialog()
            return
        if key == "substitution":
            self.open_substitution_dialog()
            return

        if hasattr(self, "current_page_key") and key == self.current_page_key and key != "weekly":
            return

        if key in ("teachers", "locations", "settings") and self.db.is_password_protected():
            title_map = {
                "teachers": "Öğretmen Yönetimi",
                "locations": "Nöbet Yerleri Yönetimi",
                "settings": "Sistem Ayarları"
            }
            self.require_admin_password(
                lambda: self._do_switch_page(key),
                title_map.get(key, "Yönetici Doğrulaması")
            )
            return

        self._do_switch_page(key)

    def _do_switch_page(self, key: str):
        try:
            target_frame = self._get_or_create_page(key)
        except Exception as e:
            logger.error(f"Sayfa açılırken hata ({key}): {e}", exc_info=True)
            messagebox.showerror(
                "Sayfa Yükleme Hatası",
                f"'{key}' sayfası açılırken bir hata oluştu:\n{e}",
                parent=self
            )
            return

        if hasattr(self, "current_page_frame") and self.current_page_frame:
            self.current_page_frame.pack_forget()

        target_frame.pack(fill="both", expand=True)
        self.current_page_frame = target_frame
        self.current_page_key = key

        self._update_sidebar_active(key)
        self._update_header_for_page(key)

    def _get_or_create_page(self, key: str):
        if key in self.page_views:
            view = self.page_views[key]
            if key == "weekly":
                self.schedule_grid.refresh()
                self.update_header_info()
            elif key == "teachers":
                view.load_teachers()
            elif key == "locations":
                view.load_locations()
            elif key == "distribute":
                view.calculate_preview()
            elif key == "backup":
                view.load_backups()
            return view

        if key == "teachers":
            view = TeacherManagementView(
                self.content_container,
                db=self.db,
                on_data_changed=self.on_teachers_data_changed
            )
        elif key == "locations":
            view = LocationManagementView(
                self.content_container,
                db=self.db,
                on_data_changed=self.on_locations_data_changed
            )
        elif key == "distribute":
            view = DistributionView(
                self.content_container,
                db=self.db,
                get_week_start=self.get_current_week_str,
                on_applied=self.on_distribution_applied,
                on_cancel=lambda: self.switch_page("weekly")
            )
        elif key == "import":
            view = ImportView(
                self.content_container,
                db=self.db,
                on_imported=self.on_import_data_changed,
                on_finish=lambda: self.switch_page("weekly")
            )
        elif key == "reports":
            view = ReportsView(
                self.content_container,
                db=self.db,
                get_current_week=self.get_current_week_str,
                open_print_preview_callback=self.open_print_preview,
                open_attendance_callback=self.open_attendance_dialog
            )
        elif key == "backup":
            view = BackupView(
                self.content_container,
                backup_service=self.backup_service,
                on_restore_complete=self.on_backup_restored,
                on_finish=lambda: self.switch_page("weekly")
            )
        elif key == "settings":
            view = SettingsView(
                self.content_container,
                db=self.db,
                on_saved=self._on_settings_saved,
                on_finish=lambda: self.switch_page("weekly")
            )
        else:
            view = self.page_weekly

        self.page_views[key] = view
        return view

    def _update_header_for_page(self, key: str):
        headers = {
            "weekly": ("", "", True),
            "teachers": ("ÖĞRETMEN YÖNETİMİ", "Öğretmen Listesi, Branşlar ve Müsaitlik Durumları", False),
            "locations": ("NÖBET YERLERİ YÖNETİMİ", "Nöbet Bölgeleri, Kapasiteler ve Sıralama", False),
            "distribute": ("OTOMATİK NÖBET DAĞITIMI", "Akıllı Dağıtım Algoritması ve Adalet Analizi", True),
            "import": ("İÇE AKTARMA MERKEZİ", "e-Okul, Excel, CSV ve Ders Programı Aktarımı", False),
            "reports": ("RAPORLAR", "Resmi belgeler, çizelgeler ve okul çıktılarını tek yerden yönetin.", False),
            "backup": ("VERİ YEDEKLEME VE GERİ YÜKLEME", "Sistem Veritabanı Yedekleri ve Geri Yükleme", False),
            "settings": ("SİSTEM VE OKUL AYARLARI", "Okul Bilgileri, Zaman Çizelgesi ve Güvenlik Parametreleri", False),
        }
        title, subtitle, show_week_nav = headers.get(key, ("", "", True))
        if hasattr(self, "lbl_title"):
            self.lbl_title.configure(text=title)
        if hasattr(self, "lbl_header_school"):
            self.lbl_header_school.configure(text=subtitle)

        if hasattr(self, "left_header_box"):
            if title or subtitle:
                self.left_header_box.pack(side="left", padx=(16, 8), pady=8)
            else:
                self.left_header_box.pack_forget()

        if hasattr(self, "nav_card"):
            if show_week_nav:
                if key == "weekly":
                    self.nav_card.pack(side="left", padx=(16, 8), pady=10)
                else:
                    self.nav_card.pack(side="right", padx=(0, 8), pady=10)
            else:
                self.nav_card.pack_forget()

        if hasattr(self, "action_bar_frame"):
            if key == "weekly":
                self.action_bar_frame.pack(side="right", padx=(0, 8), pady=10)
            else:
                self.action_bar_frame.pack_forget()

    def on_teachers_data_changed(self):
        self.schedule_grid.refresh()
        self.update_header_info()

    def on_locations_data_changed(self):
        self.schedule_grid.build_grid()
        self.schedule_grid.refresh()
        self.update_header_info()

    def on_distribution_applied(self):
        self.schedule_grid.refresh()
        self.on_duty_data_changed()
        self.switch_page("weekly")

    def on_import_data_changed(self):
        self.schedule_grid.build_grid()
        self.schedule_grid.refresh()
        self.update_header_info()

    def on_backup_restored(self):
        self.schedule_grid.build_grid()
        self.schedule_grid.refresh()
        self.update_header_info()

    # --- 2. BİRLEŞTİRİLMİŞ TEK ÜST BAR (APPLE HIG / macOS TOOLBAR STYLE) ---
    def _build_top_header(self):
        self.top_header_frame = ctk.CTkFrame(
            self.main_container,
            fg_color="#FFFFFF",
            corner_radius=0,
            height=58,
            border_width=1,
            border_color="#E5E5EA"
        )
        self.top_header_frame.pack(fill="x", side="top")

        self.left_header_box = ctk.CTkFrame(self.top_header_frame, fg_color="transparent")

        self.lbl_title = ctk.CTkLabel(
            self.left_header_box,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color="#1D1D1F"
        )
        self.lbl_title.pack(anchor="w")

        self.lbl_header_school = ctk.CTkLabel(
            self.left_header_box,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color="#86868B"
        )
        self.lbl_header_school.pack(anchor="w")

        # Üst Sağ Hızlı İkon Kapsülü (Duyurular & Geri Bildirim - Apple Minimal İkon Dock)
        self.header_actions_box = ctk.CTkFrame(
            self.top_header_frame,
            fg_color="#F5F5F7",
            corner_radius=10,
            border_width=1,
            border_color="#E5E5EA"
        )
        self.header_actions_box.pack(side="right", padx=(0, 16), pady=10)

        self.btn_feedback = ctk.CTkButton(
            self.header_actions_box,
            text="💬",
            width=32,
            height=32,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            fg_color="transparent",
            hover_color="#E5E5EA",
            text_color="#1D1D1F",
            border_width=0,
            corner_radius=8,
            command=self.open_feedback_dialog
        )
        self.btn_feedback.pack(side="right", padx=(1, 3), pady=3)
        SimpleTooltip(self.btn_feedback, "Geri Bildirim Gönder")

        self.btn_announcements = ctk.CTkButton(
            self.header_actions_box,
            text="🔔",
            width=32,
            height=32,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            fg_color="transparent",
            hover_color="#E5E5EA",
            text_color="#1D1D1F",
            border_width=0,
            corner_radius=8,
            command=self.open_announcements_dialog
        )
        self.btn_announcements.pack(side="right", padx=(3, 1), pady=3)
        SimpleTooltip(self.btn_announcements, "Sistem Duyuruları")

        # Üst Sol Hafta Gezinme Kapsülü (Apple Segmented Control Stili)
        self.nav_card = ctk.CTkFrame(
            self.top_header_frame,
            fg_color="#F5F5F7",
            corner_radius=10,
            border_width=1,
            border_color="#E5E5EA"
        )
        self.nav_card.pack(side="left", padx=(16, 8), pady=10)

        self.btn_undo = None
        self.btn_redo = None

        btn_prev = ctk.CTkButton(
            self.nav_card,
            text="‹",
            width=30,
            height=32,
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            fg_color="transparent",
            hover_color="#E5E5EA",
            text_color="#1D1D1F",
            border_width=0,
            corner_radius=8,
            command=self.prev_week
        )
        btn_prev.pack(side="left", padx=(3, 1), pady=3)
        SimpleTooltip(btn_prev, "Önceki Hafta")

        self.lbl_week_range = ctk.CTkLabel(
            self.nav_card,
            text="",
            height=32,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color="#1D1D1F",
            fg_color="#FFFFFF",
            corner_radius=8,
            padx=12,
            pady=0
        )
        self.lbl_week_range.pack(side="left", padx=2, pady=3)

        btn_next = ctk.CTkButton(
            self.nav_card,
            text="›",
            width=30,
            height=32,
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            fg_color="transparent",
            hover_color="#E5E5EA",
            text_color="#1D1D1F",
            border_width=0,
            corner_radius=8,
            command=self.next_week
        )
        btn_next.pack(side="left", padx=(1, 2), pady=3)
        SimpleTooltip(btn_next, "Sonraki Hafta")

        btn_today = ctk.CTkButton(
            self.nav_card,
            text="Bugün",
            width=56,
            height=32,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color="#EBF5FF",
            hover_color="#D6EBFF",
            text_color="#007AFF",
            border_width=0,
            corner_radius=8,
            command=self.current_week
        )
        btn_today.pack(side="left", padx=(2, 3), pady=3)
        SimpleTooltip(btn_today, "Bu Haftaya Dön")

    # --- 3. İSTATİSTİK (KPI) KARTLARI (Kullanıcı Talebiyle Kaldırıldı - Dikey Alan Kazanımı) ---
    def _build_kpi_cards(self, parent=None):
        self.kpi_cards_frame = None
        self.kpi_widgets = {}
        self.kpi_card_frames = {}

    # --- 4. ÜST BAŞLIKLA BİRLEŞTİRİLMİŞ ULTRA-MİNİMALİST İKON & PASTEL KAPSÜL DOCK ---
    def _build_action_bar(self, parent=None):
        # Operasyonel Aksiyon Kapsülü (Apple HIG Soft Pill Dock)
        self.action_bar_frame = ctk.CTkFrame(
            self.top_header_frame,
            fg_color="#F5F5F7",
            corner_radius=10,
            border_width=1,
            border_color="#E5E5EA"
        )
        self.action_bar_frame.pack(side="right", padx=(0, 8), pady=10)

        # 1. ⚡ Dağıt (Apple Soft Blue Pill)
        self.btn_distribute = ctk.CTkButton(
            self.action_bar_frame,
            text="⚡ Dağıt",
            width=82,
            height=32,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color="#EBF5FF",
            hover_color="#D6EBFF",
            text_color="#007AFF",
            border_width=0,
            corner_radius=8,
            command=self.open_auto_distribution
        )
        self.btn_distribute.pack(side="left", padx=2, pady=3)
        SimpleTooltip(self.btn_distribute, "Otomatik Nöbet Dağıtım Sihirbazı")

        # 2. 🔄 İkame Sistemi (Apple Indigo/Purple Soft Pill)
        self.btn_substitution = ctk.CTkButton(
            self.action_bar_frame,
            text="🔄 İkame Sistemi",
            width=124,
            height=32,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color="#F5F3FF",
            hover_color="#EDE9FE",
            text_color="#5856D6",
            border_width=0,
            corner_radius=8,
            command=self.open_substitution_dialog
        )
        self.btn_substitution.pack(side="left", padx=2, pady=3)
        SimpleTooltip(self.btn_substitution, "Boş Ders Doldurma ve Nöbetçi İkame Asistanı")

        # 3. ↔ Nöbet Kaydır (Ultra-Minimalist İkon + Tooltip)
        self.btn_shift = ctk.CTkButton(
            self.action_bar_frame,
            text="↔",
            width=32,
            height=32,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color="transparent",
            hover_color="#E5E5EA",
            text_color="#1D1D1F",
            border_width=0,
            corner_radius=8,
            command=self.open_shift_dialog
        )
        self.btn_shift.pack(side="left", padx=1, pady=3)
        SimpleTooltip(self.btn_shift, "Nöbet Rotasyonu ve Hafta Kaydırma")

        # 5. 🖨️ Baskı Önizleme (Ultra-Minimalist İkon + Tooltip)
        self.btn_quick_print = ctk.CTkButton(
            self.action_bar_frame,
            text="🖨️",
            width=32,
            height=32,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            fg_color="transparent",
            hover_color="#E5E5EA",
            text_color="#1D1D1F",
            border_width=0,
            corner_radius=8,
            command=self.open_print_preview
        )
        self.btn_quick_print.pack(side="left", padx=1, pady=3)
        SimpleTooltip(self.btn_quick_print, "Baskı Önizleme ve Yazdır")

        # 6. ••• Tüm İşlemler Popover (İkon + Ok Düğmesi)
        self.btn_actions = ctk.CTkButton(
            self.action_bar_frame,
            text="••• ▾",
            width=52,
            height=32,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color="#FFFFFF",
            hover_color="#E5E5EA",
            text_color="#1D1D1F",
            border_width=1,
            border_color="#E5E5EA",
            corner_radius=8,
            command=self.open_unified_actions_menu
        )
        self.btn_actions.pack(side="left", padx=2, pady=3)
        SimpleTooltip(self.btn_actions, "Hafta Aktarma, Çıktılar ve Tüm İşlemler")
        self.btn_week_ops = self.btn_actions
        self.btn_export = self.btn_actions
        self.btn_more = self.btn_actions

        div_b = ctk.CTkFrame(self.action_bar_frame, fg_color="#E5E5EA", width=1, height=18)
        div_b.pack(side="left", padx=3, pady=7)

        # 7. ✓ Kaydet (Apple Soft Green Pill Buton)
        self.btn_save = ctk.CTkButton(
            self.action_bar_frame,
            text="✓ Kaydet",
            width=92,
            height=32,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color="#E8F8EE",
            hover_color="#D1F2DE",
            text_color="#34C759",
            border_width=0,
            corner_radius=8,
            command=self.save_changes
        )
        self.btn_save.pack(side="left", padx=(2, 3), pady=3)
        SimpleTooltip(self.btn_save, "Değişiklikleri Kaydet (Ctrl+S)")

        # Geriye dönük uyumluluk için tk.Menu referansları
        self.week_ops_menu = tk.Menu(self, tearoff=0)
        self.week_ops_menu.add_command(
            label="📅 Sonraki Haftaya Aktar (Birebir Aynı Nöbetler)",
            command=self.quick_copy_next_same
        )
        self.week_ops_menu.add_command(
            label="🔄 Sonraki Haftaya Aktar (1 Gün Kaydırarak)",
            command=lambda: self._copy_next_with_mode("shift_day")
        )
        self.week_ops_menu.add_command(
            label="📍 Sonraki Haftaya Aktar (Nöbet Yerlerini Kaydırarak)",
            command=lambda: self._copy_next_with_mode("shift_loc")
        )
        self.week_ops_menu.add_separator()
        self.week_ops_menu.add_command(
            label="↔ Hızlı Nöbet Kaydır...",
            command=self.quick_shift
        )
        self.week_ops_menu.add_command(
            label="⚙️ Tüm Rotasyon ve Kaydırma Ayarları...",
            command=self.open_shift_dialog
        )

        self.export_menu = tk.Menu(self, tearoff=0)
        self.export_menu.add_command(label="🖨️ Baskı Önizleme ve Yazdırma Penceresi...", command=self.open_print_preview)
        self.export_menu.add_separator()
        self.export_menu.add_command(label="📖 Resmi Günlük Nöbet Defteri / Rapor Sayfası...", command=self.open_duty_log_dialog)
        self.export_menu.add_separator()
        self.export_menu.add_command(label="📄 PDF Belgesi Olarak Kaydet (.pdf)", command=self.export_pdf)
        self.export_menu.add_command(label="📊 Excel Tablosu Olarak Kaydet (.xlsx)", command=self.export_excel)
        self.export_menu.add_command(label="📝 Word Belgesi Olarak Kaydet (.docx)", command=self.export_word)
        self.export_menu.add_command(label="🌐 Yazdırılabilir HTML Sayfası (.html)", command=self.export_html)
        self.export_menu.add_command(label="📑 CSV Listesi Olarak Kaydet (.csv)", command=self.export_csv)
        self.export_menu.add_separator()
        self.export_menu.add_command(label="📚 Ders Programı Rapor Merkezi...", command=lambda: self.switch_page("reports"))
        self.export_menu.add_command(label="📅 Personel Devam Takip Çizelgeleri...", command=self.open_attendance_dialog)
        self.export_menu.add_command(label="💰 Ay Sonu İkame & Ek Ders İcmali...", command=self.open_ek_ders_dialog)

        self.tt_menu = tk.Menu(self, tearoff=0)
        self.tt_menu.add_command(label="📚 Ders Programı Çıktı ve Rapor Merkezi...", command=self.open_timetable_exports)
        self.tt_menu.add_separator()
        self.tt_menu.add_command(label="👤 Öğretmen El Programları (Tüm Öğretmenler PDF)", command=lambda: self.quick_export_timetable("teacher_pdf"))
        self.tt_menu.add_command(label="👤 Öğretmen El Programları (Excel Tablosu)", command=lambda: self.quick_export_timetable("teacher_excel"))
        self.tt_menu.add_separator()
        self.tt_menu.add_command(label="🏫 Sınıf / Şube Ders Programları (Tüm Şubeler PDF)", command=lambda: self.quick_export_timetable("class_pdf"))
        self.tt_menu.add_command(label="🏫 Sınıf / Şube Ders Programları (Excel Tablosu)", command=lambda: self.quick_export_timetable("class_excel"))
        self.tt_menu.add_separator()
        self.tt_menu.add_command(label="📊 Genel Haftalık Çarşaf Program (.xlsx)", command=lambda: self.quick_export_timetable("master_excel"))
        self.tt_menu.add_command(label="🟢 Öğretmen Boş Ders Saatleri Çizelgesi (.xlsx)", command=lambda: self.quick_export_timetable("free_excel"))

        self.more_menu = tk.Menu(self, tearoff=0)
        self.more_menu.add_command(label="📅 Personel Devam Takip Modülü", command=self.open_attendance_dialog)
        self.more_menu.add_command(label="💰 Ay Sonu İkame & Ek Ders İcmali", command=self.open_ek_ders_dialog)
        self.more_menu.add_command(label="📚 Ders Programı Rapor Merkezi", command=lambda: self.switch_page("reports"))
        self.more_menu.add_separator()
        self.more_menu.add_command(label="🔄 Nöbet Rotasyon ve Kaydırma Ayarları...", command=self.open_shift_dialog)
        self.more_menu.add_command(label="💾 Sistem Veritabanı Yedekleme...", command=lambda: self.switch_page("backup"))

        self.reports_menu = tk.Menu(self, tearoff=0)
        self.reports_menu.add_command(label="🖨️ Nöbet Çizelgesi Önizleme & Yazdır", command=self.open_print_preview)
        self.reports_menu.add_command(label="📄 Nöbet Çizelgesi PDF Kaydet", command=self.export_pdf)
        self.reports_menu.add_command(label="📊 Nöbet Çizelgesi Excel Kaydet", command=self.export_excel)
        self.reports_menu.add_separator()
        self.reports_menu.add_command(label="📚 Ders Programı Çıktı ve Rapor Merkezi...", command=lambda: self.switch_page("reports"))
        self.reports_menu.add_command(label="📅 Personel Devam Takip Çizelgeleri...", command=self.open_attendance_dialog)
        self.reports_menu.add_command(label="💰 Ay Sonu İkame & Ek Ders İcmali...", command=self.open_ek_ders_dialog)

    def _close_actions_popover(self):
        """Aksiyonlar popover menüsünü güvenli bir şekilde kapatır."""
        if hasattr(self, "_actions_popover") and self._actions_popover is not None:
            try:
                if self._actions_popover.winfo_exists():
                    self._actions_popover.destroy()
            except Exception:
                pass
            self._actions_popover = None

    def _handle_actions_popover_outside_click(self, event):
        """Popover dışına tıklandığında menüyü kapatır, içine veya tetikleme butonuna tıklandığında izin verir."""
        if not hasattr(self, "_actions_popover") or self._actions_popover is None:
            return
        try:
            if not self._actions_popover.winfo_exists():
                self._actions_popover = None
                return

            x, y = event.x_root, event.y_root

            # Popover sınırları içindeyse kapatma (tıklamanın çalışmasına izin ver)
            px = self._actions_popover.winfo_rootx()
            py = self._actions_popover.winfo_rooty()
            pw = self._actions_popover.winfo_width()
            ph = self._actions_popover.winfo_height()
            if px <= x <= px + pw and py <= y <= py + ph:
                return

            # Tetikleme butonuna tıklandıysa kapatma (kendi toggle mantığı yönetsin)
            if hasattr(self, "btn_actions") and self.btn_actions.winfo_exists():
                bx = self.btn_actions.winfo_rootx()
                by = self.btn_actions.winfo_rooty()
                bw = self.btn_actions.winfo_width()
                bh = self.btn_actions.winfo_height()
                if bx <= x <= bx + bw and by <= y <= by + bh:
                    return
        except Exception:
            pass

        self._close_actions_popover()

    def open_unified_actions_menu(self):
        """Klasik Windows menüsü yerine yuvarlatılmış, kategorili Modern CustomTkinter Popover Menüsü açar."""
        if hasattr(self, "_actions_popover") and self._actions_popover is not None:
            try:
                if self._actions_popover.winfo_exists():
                    self._close_actions_popover()
                    return
            except Exception:
                self._actions_popover = None

        pop = tk.Toplevel(self)
        pop.wm_overrideredirect(True)
        pop.attributes("-topmost", True)
        pop.configure(bg="#E5E5EA")
        self._actions_popover = pop

        # Dışarı tıklandığında menüyü kapatmak için global listener (tek seferlik bağlanır)
        if not getattr(self, "_actions_popover_listener_bound", False):
            self._actions_popover_listener_bound = True
            self.bind_all("<Button-1>", self._handle_actions_popover_outside_click, add="+")
            self.bind_all("<Escape>", lambda e: self._close_actions_popover(), add="+")

        # Butonun hemen altına veya ekrana sığacak şekilde konumlandır
        self.update_idletasks()
        x = self.btn_actions.winfo_rootx()
        y = self.btn_actions.winfo_rooty() + self.btn_actions.winfo_height() + 4
        pop_w = 320
        pop_h = 515

        screen_h = self.winfo_screenheight()
        if y + pop_h > screen_h - 40:
            y = max(10, self.btn_actions.winfo_rooty() - pop_h - 4)

        pop.wm_geometry(f"{pop_w}x{pop_h}+{x}+{y}")

        card = ctk.CTkFrame(
            pop,
            fg_color="#FFFFFF",
            corner_radius=12,
            border_width=1,
            border_color="#E5E5EA"
        )
        card.pack(fill="both", expand=True)

        def _run_and_close(cmd):
            self._close_actions_popover()
            if cmd:
                def _safe_run():
                    try:
                        cmd()
                    except Exception as e:
                        logger.error(f"Menü komutu çalıştırılırken hata: {e}", exc_info=True)
                        messagebox.showerror("Hata", f"İşlem çalıştırılırken hata oluştu:\n{e}", parent=self)
                self.after(20, _safe_run)

        def _add_section_header(title_txt):
            lbl = ctk.CTkLabel(
                card,
                text=title_txt,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color="#86868B"
            )
            lbl.pack(anchor="w", padx=12, pady=(8, 2))

        def _add_menu_btn(label_txt, cmd, accent=False):
            btn = ctk.CTkButton(
                card,
                text=label_txt,
                height=30,
                anchor="w",
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold" if accent else "normal"),
                fg_color="#EBF5FF" if accent else "transparent",
                hover_color="#D6EBFF" if accent else "#F5F5F7",
                text_color="#007AFF" if accent else "#1D1D1F",
                border_width=0,
                corner_radius=8,
                command=lambda: _run_and_close(cmd)
            )
            btn.pack(fill="x", padx=6, pady=1)

        def _add_sep():
            sep = ctk.CTkFrame(card, fg_color="#E5E5EA", height=1)
            sep.pack(fill="x", padx=10, pady=4)

        _add_section_header("ÖNCELİKLİ OPERASYONLAR")
        _add_menu_btn("🔄  Boş Ders İkame Sistemi Asistanı", self.open_substitution_dialog, accent=True)

        _add_sep()
        _add_section_header("SONRAKİ HAFTAYA AKTARIM")
        _add_menu_btn("📋  Aynısını Sonraki Haftaya Aktar", self.quick_copy_next_same, accent=True)
        _add_menu_btn("🔄  1 Gün Kaydırarak Aktar (Pzt ➔ Sal)", lambda: self._copy_next_with_mode("shift_day"))
        _add_menu_btn("📍  Nöbet Yerlerini Kaydırarak Aktar", lambda: self._copy_next_with_mode("shift_loc"))
        _add_menu_btn("⚡  Son Ayarla Hızlı Kaydır", self.quick_shift)

        _add_sep()
        _add_section_header("BELGE & ÇIKTI MERKEZİ")
        _add_menu_btn("📄  Nöbet Çizelgesi PDF İndir (.pdf)", self.export_pdf)
        _add_menu_btn("📊  Nöbet Çizelgesi Excel İndir (.xlsx)", self.export_excel)
        _add_menu_btn("📝  Nöbet Çizelgesi Word İndir (.docx)", self.export_word)
        _add_menu_btn("📚  Ders Programı Çıktıları (El Programı)", self.open_timetable_exports)
        _add_menu_btn("📅  Personel Devam Takip Çizelgesi", self.open_attendance_dialog)
        _add_menu_btn("💰  Ay Sonu İkame & Ek Ders İcmali", self.open_ek_ders_dialog)

        _add_sep()
        _add_menu_btn("🔤  Görünüm & Yazı Tipi Ayarları...", lambda: self.open_settings("font"))

    # --- 5. ÇALIŞMA ALANI (GRID + SAĞ DETAY PANELİ) ---
    def _build_workspace(self, parent=None):
        target = parent if parent is not None else self.main_container
        self.workspace_frame = ctk.CTkFrame(target, fg_color="transparent")
        self.workspace_frame.pack(fill="both", expand=True, padx=16, pady=(10, 8))

        # Tablo Izgara Alanı
        self.grid_container = ttk.Frame(self.workspace_frame)
        self.grid_container.pack(side="left", fill="both", expand=True)

        self.schedule_grid = ScheduleGrid(
            parent=self.grid_container,
            db=self.db,
            duty_service=self.duty_service,
            get_current_week=self.get_current_week_str,
            on_data_changed=self.on_duty_data_changed,
            on_cell_selected=self.on_cell_selected
        )
        self.schedule_grid.pack(fill="both", expand=True)

        # Sağ panel tamamen kaldırıldı; çizelge tüm ekran genişliğini kullanır.
        self.detail_panel = None
        self.is_detail_open = False

    def on_cell_selected(self, cell):
        pass

    def close_detail_panel(self):
        pass

    def show_detail_panel(self, cell):
        pass

    # --- 6. ALT BİLGİ / DURUM ÇUBUĞU / LEGEND (macOS STATUS BAR STYLE) ---
    def _build_footer(self, parent=None):
        target = parent if parent is not None else self.main_container
        self.footer_frame = ctk.CTkFrame(target, fg_color="#FFFFFF", height=32, corner_radius=0, border_width=1, border_color="#E5E5EA")
        self.footer_frame.pack(fill="x", side="bottom")

        # Sol Gösterge (Legend)
        legend_box = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        legend_box.pack(side="left", padx=12, pady=3)

        badges = [
            ("⚪ Normal Görev", "#1D1D1F"),
            ("🔒 Sabit Görev", "#FF9500"),
            ("🔴 Eksik Nöbet", "#FF3B30"),
            ("🔵 Seçili Hücre", "#007AFF"),
        ]
        for txt, color in badges:
            lbl = ctk.CTkLabel(
                legend_box,
                text=txt,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                text_color=color
            )
            lbl.pack(side="left", padx=(0, 10))

        # Orta: Durum Mesajı
        self.lbl_status = ctk.CTkLabel(
            self.footer_frame,
            text="Hazır. Öğretmenleri sürükleyerek veya tıklayarak detayını inceleyebilirsiniz.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color="#6E6E73"
        )
        self.lbl_status.pack(side="left", padx=8)

        # Sağ: Son Kayıt Zamanı
        self.lbl_last_save = ctk.CTkLabel(
            self.footer_frame,
            text=f"Son kayıt: Bugün {datetime.datetime.now().strftime('%H:%M')}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color="#86868B"
        )
        self.lbl_last_save.pack(side="right", padx=12)

    def open_week_ops_menu(self):
        try:
            x = self.btn_week_ops.winfo_rootx()
            y = self.btn_week_ops.winfo_rooty() + self.btn_week_ops.winfo_height()
            self.week_ops_menu.tk_popup(x, y)
        finally:
            self.week_ops_menu.grab_release()

    def open_export_menu(self):
        try:
            x = self.btn_export.winfo_rootx()
            y = self.btn_export.winfo_rooty() + self.btn_export.winfo_height()
            self.export_menu.tk_popup(x, y)
        finally:
            self.export_menu.grab_release()

    def open_tt_export_menu(self):
        try:
            x = self.winfo_pointerx()
            y = self.winfo_pointery()
            self.tt_menu.tk_popup(x, y)
        finally:
            self.tt_menu.grab_release()

    def open_more_menu(self):
        try:
            x = self.btn_more.winfo_rootx()
            y = self.btn_more.winfo_rooty() + self.btn_more.winfo_height()
            self.more_menu.tk_popup(x, y)
        finally:
            self.more_menu.grab_release()

    def open_reports_menu(self):
        self.switch_page("reports")

    def update_header_info(self):
        school = self.db.get_school_info()
        short_name = (school.name[:34] + "…") if school.name and len(school.name) > 35 else (school.name or "Okul Nöbet Sistemi")
        if hasattr(self, "current_page_key") and self.current_page_key != "weekly":
            self.lbl_header_school.configure(text=f"{short_name} • {school.academic_year}")
        else:
            self.lbl_header_school.configure(text="")
        if hasattr(self, "lbl_sidebar_school"):
            self.lbl_sidebar_school.configure(text=school.name if school.name else "Okul Yönetim Sistemi")
        if hasattr(self, "lbl_sidebar_year"):
            self.lbl_sidebar_year.configure(text=f"🎓 {school.academic_year or '2026-2027'} Eğitim Yılı")
        if hasattr(self, "lbl_sidebar_principal"):
            self.lbl_sidebar_principal.configure(text=f"Müdür: {school.principal_name}" if school.principal_name else "Müdürlük")

        end_date = self.current_week_start + datetime.timedelta(days=4)
        m_start = TURKISH_MONTHS[self.current_week_start.month] if 1 <= self.current_week_start.month <= 12 else ""
        m_end = TURKISH_MONTHS[end_date.month] if 1 <= end_date.month <= 12 else ""
        if self.current_week_start.month == end_date.month:
            week_str = f"{self.current_week_start.day} – {end_date.day} {m_end} {end_date.year}"
        else:
            week_str = f"{self.current_week_start.day} {m_start} – {end_date.day} {m_end} {end_date.year}"
        self.lbl_week_range.configure(text=week_str)

        # KPI İstatistiklerini Hesapla ve Güncelle
        teachers = self.db.get_teachers(active_only=True)
        active_count = len(teachers)

        matrix = self.duty_service.get_grid_matrix(self.get_current_week_str())
        locations = matrix["locations"]
        days = matrix["days"]
        total_slots = sum(loc.capacity for loc in locations) * len(days)
        assign_map = matrix["assignments"]
        filled_count = sum(1 for a in assign_map.values() if a.teacher_id)
        missing_count = max(0, total_slots - filled_count)
        fixed_count = sum(1 for a in assign_map.values() if a.fixed and a.teacher_id)
        rate_pct = int(filled_count / total_slots * 100) if total_slots > 0 else 0

        if hasattr(self, "kpi_widgets"):
            if "teachers" in self.kpi_widgets:
                self.kpi_widgets["teachers"][0].configure(text=str(active_count))
            if "filled" in self.kpi_widgets:
                self.kpi_widgets["filled"][0].configure(text=f"{filled_count} / {total_slots}")
            if "missing" in self.kpi_widgets:
                self.kpi_widgets["missing"][0].configure(text=str(missing_count))
                if hasattr(self, "kpi_card_frames") and "missing" in self.kpi_card_frames:
                    if missing_count > 0:
                        self.kpi_card_frames["missing"].configure(fg_color="#FEF2F2", border_color="#FCA5A5")
                        self.kpi_widgets["missing"][0].configure(text_color="#DC2626")
                    else:
                        self.kpi_card_frames["missing"].configure(fg_color="#FFFFFF", border_color="#E2E8F0")
                        self.kpi_widgets["missing"][0].configure(text_color="#059669")
            if "fixed" in self.kpi_widgets:
                self.kpi_widgets["fixed"][0].configure(text=str(fixed_count))
            if "rate" in self.kpi_widgets:
                self.kpi_widgets["rate"][0].configure(text=f"%{rate_pct}")
                rate_color = "#059669" if rate_pct == 100 else ("#D97706" if rate_pct > 0 else "#64748B")
                self.kpi_widgets["rate"][0].configure(text_color=rate_color)

    def prev_week(self):
        self.current_week_start -= datetime.timedelta(days=7)
        self.update_header_info()
        self.schedule_grid.refresh()

    def advance_to_next_week(self):
        """Haftayı 1 hafta ileri alır ve arayüzü günceller."""
        self.current_week_start += datetime.timedelta(days=7)
        self.update_header_info()
        self.schedule_grid.refresh()

    def next_week(self):
        old_week_str = self.get_current_week_str()
        target_week_start = self.current_week_start + datetime.timedelta(days=7)
        target_week_str = target_week_start.isoformat()

        has_src = self.db.has_assigned_duties_for_week(old_week_str)
        has_tgt = self.db.has_assigned_duties_for_week(target_week_str)

        self.current_week_start = target_week_start

        # Kaynak haftada nöbet varsa ve hedef hafta henüz boşsa tercihe göre otomatik aktar
        if has_src and not has_tgt:
            carry_mode = self.db.get_setting("week_carry_mode", "same")
            if carry_mode == "same":
                self.duty_service.copy_week_to_next(old_week_str, target_week_str, shift_mode="same")
                self.on_duty_data_changed()
                self.lbl_status.configure(text=f"✔ Önceki haftanın nöbet çizelgesi aynen bu haftaya aktarıldı. (Geri almak için: Ctrl+Z)")
            elif carry_mode == "shift_day":
                self.duty_service.copy_week_to_next(old_week_str, target_week_str, shift_mode="shift_day", shift_steps=1)
                self.on_duty_data_changed()
                self.lbl_status.configure(text=f"✔ Önceki haftanın nöbet çizelgesi 1 gün kaydırılarak aktarıldı. (Geri almak için: Ctrl+Z)")
            elif carry_mode == "shift_loc":
                self.duty_service.copy_week_to_next(old_week_str, target_week_str, shift_mode="shift_loc", shift_steps=1)
                self.on_duty_data_changed()
                self.lbl_status.configure(text=f"✔ Önceki haftanın nöbet çizelgesi yerler kaydırılarak aktarıldı. (Geri almak için: Ctrl+Z)")

        self.update_header_info()
        self.schedule_grid.refresh()

    def current_week(self):
        today = datetime.date.today()
        # Pazartesiye çek
        self.current_week_start = today - datetime.timedelta(days=today.weekday())
        self.update_header_info()
        self.schedule_grid.refresh()

    def quick_copy_next_same(self):
        """Mevcut haftanın nöbetlerini birebir bir sonraki haftaya aktarır ve o haftaya geçer."""
        cur_week_str = self.get_current_week_str()
        if not self.db.has_assigned_duties_for_week(cur_week_str):
            messagebox.showwarning("Uyarı", "Aktarılacak nöbet bulunamadı. Lütfen önce bu haftaya nöbet dağıtımı yapınız.")
            return

        next_dt = self.current_week_start + datetime.timedelta(days=7)
        next_week_str = next_dt.isoformat()

        success = self.duty_service.copy_week_to_next(cur_week_str, next_week_str, shift_mode="same")
        if success:
            self.current_week_start = next_dt
            self.update_header_info()
            self.schedule_grid.refresh()
            self.on_duty_data_changed()
            self.lbl_status.configure(text=f"✔ Nöbetler birebir sonraki haftaya ({next_week_str}) aktarıldı. (Geri almak için: Ctrl+Z)")

    def open_copy_menu(self):
        """Sonraki haftaya aktarma seçenekleri açılır menüsü."""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(
            label="📋 Aynısını Sonraki Haftaya Aktar (Birebir Kopyala)",
            command=self.quick_copy_next_same
        )
        menu.add_command(
            label="🔄 1 Gün Kaydırarak Sonraki Haftaya Aktar (Pzt ➔ Sal ...)",
            command=lambda: self._copy_next_with_mode("shift_day")
        )
        menu.add_command(
            label="📍 Nöbet Yerlerini Kaydırarak Sonraki Haftaya Aktar",
            command=lambda: self._copy_next_with_mode("shift_loc")
        )
        menu.add_separator()
        menu.add_command(
            label="⚙️ Tüm Rotasyon ve Kaydırma Ayarları...",
            command=self.open_shift_dialog
        )
        try:
            x = self.winfo_pointerx()
            y = self.winfo_pointery()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _copy_next_with_mode(self, mode: str):
        cur_week_str = self.get_current_week_str()
        if not self.db.has_assigned_duties_for_week(cur_week_str):
            messagebox.showwarning("Uyarı", "Aktarılacak nöbet bulunamadı. Lütfen önce bu haftaya nöbet dağıtımı yapınız.")
            return

        next_dt = self.current_week_start + datetime.timedelta(days=7)
        next_week_str = next_dt.isoformat()

        success = self.duty_service.copy_week_to_next(cur_week_str, next_week_str, shift_mode=mode, shift_steps=1)
        if success:
            self.current_week_start = next_dt
            self.update_header_info()
            self.schedule_grid.refresh()
            self.on_duty_data_changed()
            desc = "1 gün kaydırılarak" if mode == "shift_day" else "yerler kaydırılarak"
            self.lbl_status.configure(text=f"✔ Nöbetler {desc} sonraki haftaya ({next_week_str}) aktarıldı. (Geri almak için: Ctrl+Z)")

    def on_duty_data_changed(self):
        self.has_unsaved_changes = True
        self.update_header_info()
        self.lbl_status.configure(text="Çizelgede değişiklik yapıldı. [💾 Değişiklikleri Kaydet] ile kalıcı yapabilirsiniz.")

    def update_undo_redo_ui(self):
        can_u = self.undo_manager.can_undo()
        can_r = self.undo_manager.can_redo()
        if hasattr(self, "btn_undo") and self.btn_undo:
            self.btn_undo.configure(state="normal" if can_u else "disabled")
        if hasattr(self, "btn_redo") and self.btn_redo:
            self.btn_redo.configure(state="normal" if can_r else "disabled")

    def do_undo(self):
        if self.undo_manager.undo():
            self.schedule_grid.refresh()
            self.on_duty_data_changed()
            self.lbl_status.configure(text="Son işlem geri alındı.")

    def do_redo(self):
        if self.undo_manager.redo():
            self.schedule_grid.refresh()
            self.on_duty_data_changed()
            self.lbl_status.configure(text="Geri alınan işlem tekrar uygulandı.")

    def save_changes(self):
        self.has_unsaved_changes = False
        now_str = datetime.datetime.now().strftime('%H:%M')
        if hasattr(self, "lbl_last_save"):
            self.lbl_last_save.configure(text=f"Son kayıt: Bugün {now_str}")
        self.lbl_status.configure(text="Tüm değişiklikler başarıyla veritabanına kaydedildi.")
        messagebox.showinfo("Kayıt", "Nöbet çizelgesi değişiklikleri kaydedildi.")

    # --- Diyaloglar ---
    def require_admin_password(self, callback, action_title: str = "Yönetici Doğrulaması"):
        """Eğer yönetici şifresi aktifse şifre modalını açar, doğrulanırsa callback çalıştırır."""
        if not self.db.is_password_protected():
            callback()
            return
        from ui.password_dialog import AdminPasswordDialog
        AdminPasswordDialog(self, self.db, on_success=callback, title_text=action_title)

    def open_auto_distribution(self):
        self.switch_page("distribute")

    def quick_shift(self):
        from ui.shift_dialog import execute_shift
        mode = self.db.get_setting("last_shift_mode", "copy_next_shift_day")
        preserve = self.db.get_setting("last_shift_preserve", "1") == "1"
        week_str = self.get_current_week_str()

        is_next = mode in ("copy_next_week", "copy_next_shift_day", "copy_next_shift_loc", "copy_next_same")

        try:
            desc = execute_shift(self.duty_service, week_str, mode, preserve)
            if is_next:
                self.current_week_start += datetime.timedelta(days=7)
            self.update_header_info()
            self.schedule_grid.refresh()
            self.on_duty_data_changed()
            self.lbl_status.configure(
                text=f"✔ Nöbetler son ayara göre uygulandı ({desc}). Geri almak için: Ctrl+Z | Ayarlar: ▾ butonu"
            )
        except Exception as e:
            logger.error(f"Hızlı kaydırma hatası: {e}")
            messagebox.showerror("Hata", f"Kaydırma işlemi başarısız:\n{e}")

    def open_shift_dialog(self):
        ShiftDialog(
            parent=self,
            db=self.db,
            duty_service=self.duty_service,
            current_week_str=self.get_current_week_str(),
            on_applied=lambda: [self.schedule_grid.refresh(), self.on_duty_data_changed()],
            advance_week_callback=self.advance_to_next_week
        )

    def open_teachers(self):
        self.switch_page("teachers")

    def open_locations(self):
        self.switch_page("locations")

    def open_import(self):
        self.switch_page("import")

    def open_backup(self):
        self.switch_page("backup")

    def open_settings(self, initial_tab=None):
        view = self.switch_page("settings")
        if initial_tab and hasattr(view, "select_tab"):
            view.select_tab(initial_tab)

    def _on_settings_saved(self):
        try:
            from ui.theme import load_theme_settings, setup_styles
            load_theme_settings(self.db)
            setup_styles(self, self.db)
            self._update_all_ui_fonts()
            self.update_header_info()
            self.schedule_grid.build_grid()
            self.schedule_grid.refresh()
        except Exception as e:
            logger.error(f"Arayüz güncellenirken hata: {e}", exc_info=True)

    def _update_all_ui_fonts(self):
        import ui.theme as theme
        fam = theme.FONT_FAMILY
        ui_sz = theme.FONT_SIZE_UI

        # Menü fontları
        menu_font = (fam, ui_sz)
        if hasattr(self, "export_menu"):
            try:
                self.export_menu.configure(font=menu_font)
            except Exception:
                pass
        if hasattr(self, "tt_menu"):
            try:
                self.tt_menu.configure(font=menu_font)
            except Exception:
                pass

        # Üst Başlıklar
        if hasattr(self, "lbl_header_title"):
            try:
                self.lbl_header_title.configure(font=ctk.CTkFont(family=fam, size=theme.FONT_SIZE_PAGE_TITLE, weight="bold"))
            except Exception:
                pass
        if hasattr(self, "lbl_header_school"):
            try:
                self.lbl_header_school.configure(font=ctk.CTkFont(family=fam, size=theme.FONT_SIZE_SECONDARY))
            except Exception:
                pass

        # Hafta Gezinme Kartı
        if hasattr(self, "lbl_week_range"):
            try:
                self.lbl_week_range.configure(font=ctk.CTkFont(family=fam, size=ui_sz, weight="bold"))
            except Exception:
                pass

        # KPI Kartları (Rakamlar ve alt başlıklar)
        if hasattr(self, "kpi_widgets"):
            for val_lbl, sub_lbl in self.kpi_widgets.values():
                try:
                    val_lbl.configure(font=ctk.CTkFont(family=fam, size=theme.FONT_SIZE_KPI_VALUE, weight="bold"))
                    sub_lbl.configure(font=ctk.CTkFont(family=fam, size=theme.FONT_SIZE_SECONDARY, weight="bold"))
                except Exception:
                    pass

        # Tüm butonları ve aksiyon elemanlarını dinamik güncelle
        def _recursive_update_buttons(w):
            try:
                if isinstance(w, ctk.CTkButton):
                    w.configure(font=ctk.CTkFont(family=fam, size=ui_sz, weight="bold"))
            except Exception:
                pass
            for child in w.winfo_children():
                _recursive_update_buttons(child)

        if hasattr(self, "sidebar_frame"):
            _recursive_update_buttons(self.sidebar_frame)
        if hasattr(self, "top_header_frame"):
            _recursive_update_buttons(self.top_header_frame)
        if hasattr(self, "action_bar_frame"):
            _recursive_update_buttons(self.action_bar_frame)
        if hasattr(self, "footer_frame"):
            _recursive_update_buttons(self.footer_frame)
        if hasattr(self, "detail_panel"):
            _recursive_update_buttons(self.detail_panel)

    def open_print_preview(self):
        """Haftalık nöbet çizelgesini Evrensel Baskı ve Önizleme Merkezi'nde açar."""
        from ui.preview_dialog import PrintPreviewDialog
        import tempfile
        week = self.get_current_week_str()
        default_name = f"Nobet_Cizelgesi_{week}"

        tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp_pdf.close()
        tmp_html = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8")
        tmp_html.close()
        try:
            self.export_service.export_pdf(week, Path(tmp_pdf.name))
            self.export_service.export_html(week, Path(tmp_html.name))
            PrintPreviewDialog(
                parent=self,
                title=f"Haftalık Nöbet Çizelgesi Önizleme ({week})",
                pdf_path=tmp_pdf.name,
                html_path=tmp_html.name,
                default_filename=default_name
            )
        except Exception as e:
            logger.error(f"Önizleme açılırken hata: {e}", exc_info=True)
            messagebox.showerror("Hata", f"Baskı önizleme oluşturulamadı:\n{e}", parent=self)

    def open_substitution_dialog(self):
        if hasattr(self, '_substitution_dialog') and self._substitution_dialog:
            try:
                if self._substitution_dialog.winfo_exists():
                    self._substitution_dialog.deiconify()
                    self._substitution_dialog.lift()
                    self._substitution_dialog.focus_force()
                    return
            except Exception:
                self._substitution_dialog = None

        self._substitution_dialog = SubstitutionDialog(
            parent=self,
            db=self.db,
            current_week_start=self.get_current_week_str()
        )

    def open_attendance_dialog(self):
        AttendanceDialog(
            parent=self,
            db=self.db
        )

    def open_duty_log_dialog(self, initial_date=None):
        try:
            from ui.duty_log_dialog import DutyLogDialog
            DutyLogDialog(self, self.db, initial_date=initial_date)
        except Exception as e:
            logger.error(f"DutyLogDialog hatası: {e}", exc_info=True)

    def open_ek_ders_dialog(self):
        from ui.ek_ders_dialog import EkDersMonthlySummaryDialog
        def _go_to_teacher(t_id):
            self.switch_page("teachers")
            if "teachers" in self.page_views:
                self.page_views["teachers"].select_teacher_by_id(t_id)

        EkDersMonthlySummaryDialog(
            parent=self,
            db=self.db,
            on_select_teacher=_go_to_teacher
        )

    def open_timetable_exports(self, default_tab: int = 0):
        try:
            TimetableExportDialog(self, self.db, default_tab=default_tab)
        except Exception as e:
            logger.error(f"TimetableExportDialog hatası: {e}", exc_info=True)
            v = self.switch_page("reports")
            if hasattr(v, "switch_tab"):
                v.switch_tab("timetable")

    def quick_export_timetable(self, export_type: str):
        if not self.db.has_timetable_data():
            messagebox.showwarning(
                "Ders Programı Bulunamadı",
                "Veritabanında yüklü ders programı bulunamadı.\n"
                "Lütfen önce 'İçe Aktarma Merkezi'nden e-Okul PDF veya Excel ders programını yükleyin.",
                parent=self
            )
            return

        school = self.db.get_school_info()
        year_str = school.academic_year.replace("-", "_")

        if export_type == "teacher_pdf":
            path = filedialog.asksaveasfilename(
                title="Tüm Öğretmenler El Programı PDF Kaydet",
                initialdir=str(EXPORTS_DIR),
                initialfile=f"Tum_Ogretmenler_Ders_Programi_{year_str}.pdf",
                defaultextension=".pdf",
                filetypes=[("PDF Belgesi", "*.pdf")],
                parent=self
            )
            if path:
                self.export_service.export_teacher_timetable_pdf(Path(path))
                messagebox.showinfo("Başarılı", f"Öğretmen ders programları PDF olarak kaydedildi:\n{path}", parent=self)

        elif export_type == "teacher_excel":
            path = filedialog.asksaveasfilename(
                title="Öğretmenler Ders Programı Excel Kaydet",
                initialdir=str(EXPORTS_DIR),
                initialfile=f"Ogretmenler_Ders_Programi_{year_str}.xlsx",
                defaultextension=".xlsx",
                filetypes=[("Excel Dosyası", "*.xlsx")],
                parent=self
            )
            if path:
                self.export_service.export_teacher_timetable_excel(Path(path))
                messagebox.showinfo("Başarılı", f"Öğretmen ders programları Excel olarak kaydedildi:\n{path}", parent=self)

        elif export_type == "class_pdf":
            path = filedialog.asksaveasfilename(
                title="Tüm Sınıflar Ders Programı PDF Kaydet",
                initialdir=str(EXPORTS_DIR),
                initialfile=f"Tum_Siniflar_Ders_Programi_{year_str}.pdf",
                defaultextension=".pdf",
                filetypes=[("PDF Belgesi", "*.pdf")],
                parent=self
            )
            if path:
                self.export_service.export_class_timetable_pdf(Path(path))
                messagebox.showinfo("Başarılı", f"Sınıf ders programları PDF olarak kaydedildi:\n{path}", parent=self)

        elif export_type == "class_excel":
            path = filedialog.asksaveasfilename(
                title="Sınıflar Ders Programı Excel Kaydet",
                initialdir=str(EXPORTS_DIR),
                initialfile=f"Siniflar_Haftalik_Ders_Programi_{year_str}.xlsx",
                defaultextension=".xlsx",
                filetypes=[("Excel Dosyası", "*.xlsx")],
                parent=self
            )
            if path:
                self.export_service.export_class_timetable_excel(Path(path))
                messagebox.showinfo("Başarılı", f"Sınıf ders programları Excel olarak kaydedildi:\n{path}", parent=self)

        elif export_type == "master_excel":
            path = filedialog.asksaveasfilename(
                title="Genel Çarşaf Program Excel Kaydet",
                initialdir=str(EXPORTS_DIR),
                initialfile=f"Genel_Carsaf_Ders_Programi_{year_str}.xlsx",
                defaultextension=".xlsx",
                filetypes=[("Excel Dosyası", "*.xlsx")],
                parent=self
            )
            if path:
                self.export_service.export_master_timetable_excel(Path(path))
                messagebox.showinfo("Başarılı", f"Genel çarşaf ders programı Excel olarak kaydedildi:\n{path}", parent=self)

        elif export_type == "free_excel":
            path = filedialog.asksaveasfilename(
                title="Boş Dersler Çizelgesi Excel Kaydet",
                initialdir=str(EXPORTS_DIR),
                initialfile=f"Ogretmen_Bos_Dersler_Cizelgesi.xlsx",
                defaultextension=".xlsx",
                filetypes=[("Excel Dosyası", "*.xlsx")],
                parent=self
            )
            if path:
                self.export_service.export_free_periods_excel(Path(path))
                messagebox.showinfo("Başarılı", f"Öğretmen boş ders çizelgesi Excel olarak kaydedildi:\n{path}", parent=self)

    # --- Dışa Aktarımlar ---
    def export_excel(self):
        week = self.get_current_week_str()
        default_name = f"Nobet_Cizelgesi_{week}.xlsx"
        path = filedialog.asksaveasfilename(
            title="Excel Olarak Kaydet",
            initialfile=default_name,
            defaultextension=".xlsx",
            filetypes=[("Excel Dosyası", "*.xlsx")]
        )
        if path:
            dest = self.export_service.export_excel(week, Path(path))
            messagebox.showinfo("Başarılı", f"Excel çıktısı kaydedildi:\n{dest}")

    def export_word(self):
        week = self.get_current_week_str()
        default_name = f"Nobet_Cizelgesi_{week}.docx"
        path = filedialog.asksaveasfilename(
            title="Word Belgesi Olarak Kaydet",
            initialfile=default_name,
            defaultextension=".docx",
            filetypes=[("Word Dosyası", "*.docx")]
        )
        if path:
            dest = self.export_service.export_word(week, Path(path))
            messagebox.showinfo("Başarılı", f"Word belgesi kaydedildi:\n{dest}")

    def export_pdf(self):
        week = self.get_current_week_str()
        default_name = f"Nobet_Cizelgesi_{week}.pdf"
        path = filedialog.asksaveasfilename(
            title="PDF Belgesi Olarak Kaydet",
            initialfile=default_name,
            defaultextension=".pdf",
            filetypes=[("PDF Dosyası", "*.pdf")]
        )
        if path:
            dest = self.export_service.export_pdf(week, Path(path))
            messagebox.showinfo("Başarılı", f"PDF belgesi oluşturuldu:\n{dest}")

    def export_html(self):
        week = self.get_current_week_str()
        default_name = f"Nobet_Cizelgesi_{week}.html"
        path = filedialog.asksaveasfilename(
            title="HTML Olarak Kaydet",
            initialfile=default_name,
            defaultextension=".html",
            filetypes=[("HTML Dosyası", "*.html")]
        )
        if path:
            dest = self.export_service.export_html(week, Path(path))
            messagebox.showinfo("Başarılı", f"HTML sayfası kaydedildi:\n{dest}")

    def export_csv(self):
        week = self.get_current_week_str()
        default_name = f"Nobet_Cizelgesi_{week}.csv"
        path = filedialog.asksaveasfilename(
            title="CSV Olarak Kaydet",
            initialfile=default_name,
            defaultextension=".csv",
            filetypes=[("CSV Dosyası", "*.csv")]
        )
        if path:
            dest = self.export_service.export_csv(week, Path(path))
            messagebox.showinfo("Başarılı", f"CSV dosyası kaydedildi:\n{dest}")

    # --- Geliştirici Duyuruları ve Geri Bildirim ---
    def open_announcements_dialog(self):
        from ui.announcement_dialog import AnnouncementDialog
        dlg = AnnouncementDialog(self, self.db)
        self.wait_window(dlg)
        self._update_announcements_badge()

    def open_feedback_dialog(self):
        from ui.feedback_dialog import FeedbackDialog
        dlg = FeedbackDialog(self, self.db)
        self.wait_window(dlg)

    def _check_announcements_background(self):
        import threading
        def worker():
            try:
                from logic.announcement_service import AnnouncementService
                announcements = AnnouncementService.fetch_announcements()
                unread_count = AnnouncementService.get_unread_count(self.db, announcements)
                self.after(0, lambda: self._apply_announcements_badge(unread_count, announcements))
            except Exception as e:
                logger.debug(f"Duyuru arka plan kontrol hatası: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _apply_announcements_badge(self, unread_count: int, announcements: list):
        if hasattr(self, "btn_announcements") and self.btn_announcements.winfo_exists():
            if unread_count > 0:
                self.btn_announcements.configure(
                    text=f"🔔 {unread_count}",
                    width=48,
                    fg_color="#FEF3C7",
                    hover_color="#FDE68A",
                    text_color="#B45309",
                    border_width=0
                )
            else:
                self.btn_announcements.configure(
                    text="🔔",
                    width=34,
                    fg_color="transparent",
                    hover_color="#E2E8F0",
                    text_color="#334155",
                    border_width=0
                )

    def _update_announcements_badge(self):
        try:
            from logic.announcement_service import AnnouncementService
            announcements = AnnouncementService.fetch_announcements()
            unread_count = AnnouncementService.get_unread_count(self.db, announcements)
            self._apply_announcements_badge(unread_count, announcements)
        except Exception:
            pass

    # --- Otomatik Güncelleme ve Şık Bildirim Merkezi ---
    def _check_updates_background(self):
        """Açılışta arka planda yeni sürüm olup olmadığını otomatik sorgular."""
        if self.db.get_setting("auto_check_updates", "1") != "1":
            return

        def worker():
            try:
                from logic.update_service import UpdateService
                repo = self.db.get_setting("github_repo", DEFAULT_GITHUB_REPO)
                svc = UpdateService(repo)
                info = svc.check_for_updates()
                if info.get("success") and info.get("has_update"):
                    self.after(0, lambda: self._on_startup_update_found(info, svc))
            except Exception as e:
                logger.debug(f"Arka plan güncelleme sorgulama hatası: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _show_update_banner(self, info: dict, svc=None):
        """Ana pencerenin en üstünde modern, dikkat çekici ve şık bir güncelleme bildirim bandı gösterir."""
        if not hasattr(self, "update_banner_container") or not self.update_banner_container.winfo_exists():
            return

        for w in self.update_banner_container.winfo_children():
            w.destroy()

        latest_v = info.get("latest_version", "")
        title_text = info.get("title") or "Yeni Sürüm ve Özellikler Paketi"

        # Şık Koyu Lacivert / Mavi Vurgulu Bildirim Kartı
        banner_card = ctk.CTkFrame(
            self.update_banner_container,
            fg_color="#1C1C1E",
            corner_radius=10,
            border_width=1,
            border_color="#007AFF"
        )
        banner_card.pack(fill="x", ipady=4)

        # Sol Alan (Rozet ve Metinler)
        f_left = ctk.CTkFrame(banner_card, fg_color="transparent")
        f_left.pack(side="left", fill="both", expand=True, padx=14, pady=8)

        f_badge_row = ctk.CTkFrame(f_left, fg_color="transparent")
        f_badge_row.pack(fill="x", anchor="w")

        badge = ctk.CTkFrame(f_badge_row, fg_color="#2C2C2E", corner_radius=6, border_width=1, border_color="#007AFF")
        badge.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            badge,
            text=f"🚀 YENİ SÜRÜM: {latest_v}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color="#007AFF"
        ).pack(padx=8, pady=2)

        ctk.CTkLabel(
            f_badge_row,
            text=f"{title_text}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color="#FFFFFF"
        ).pack(side="left", anchor="w")

        ctk.CTkLabel(
            f_left,
            text=f"Mevcut sürümünüz: v{APP_VERSION} • Yeni MEB mevzuat uyumu, performans geliştirmeleri ve raporlama araçları hazır.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color="#94A3B8"
        ).pack(anchor="w", pady=(3, 0))

        # Sağ Alan (Eylem Butonları)
        f_actions = ctk.CTkFrame(banner_card, fg_color="transparent")
        f_actions.pack(side="right", padx=(8, 14), pady=8)

        btn_update = ctk.CTkButton(
            f_actions,
            text="⬇️ Şimdi Güncelle",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color="#007AFF",
            hover_color="#0062D2",
            text_color="#FFFFFF",
            height=32,
            corner_radius=8,
            command=lambda: self._open_update_center(info, svc)
        )
        btn_update.pack(side="left", padx=(0, 6))

        btn_notes = ctk.CTkButton(
            f_actions,
            text="📋 Yenilikler",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color="#2C2C2E",
            hover_color="#3A3A3C",
            text_color="#F4F4F5",
            height=32,
            corner_radius=8,
            command=lambda: self._open_update_center(info, svc)
        )
        btn_notes.pack(side="left", padx=(0, 6))

        btn_dismiss = ctk.CTkButton(
            f_actions,
            text="✕",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color="transparent",
            hover_color="#2C2C2E",
            text_color="#86868B",
            width=28,
            height=32,
            corner_radius=6,
            command=lambda: self.update_banner_container.pack_forget()
        )
        btn_dismiss.pack(side="left")
        SimpleTooltip(btn_dismiss, "Bu bildirimi gizle")

        # Görünür yap (Header ile Content arasına yerleştir)
        self.update_banner_container.pack(fill="x", side="top", padx=16, pady=(10, 4), before=self.content_container)

    def _update_sidebar_for_new_version(self, info: dict, svc=None):
        """Sol menünün altındaki sürüm alanını parlak güncelleme butonuna çevirir."""
        if hasattr(self, "sidebar_version_card") and self.sidebar_version_card.winfo_exists():
            if hasattr(self, "sidebar_ver_box") and self.sidebar_ver_box.winfo_exists():
                self.sidebar_ver_box.pack_forget()

            if not hasattr(self, "btn_sidebar_update") or not self.btn_sidebar_update.winfo_exists():
                self.btn_sidebar_update = ctk.CTkButton(
                    self.sidebar_version_card,
                    text=f"🚀 {info.get('latest_version')} Yayında!",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                    fg_color="#059669",
                    hover_color="#047857",
                    text_color="#FFFFFF",
                    height=30,
                    corner_radius=8,
                    command=lambda: self._open_update_center(info, svc)
                )
                self.btn_sidebar_update.pack(fill="x", pady=(4, 0))
                SimpleTooltip(self.btn_sidebar_update, "Yeni sürümü yüklemek için tıklayın")

    def _open_update_center(self, info: dict, svc=None):
        """Güncelleme diyalogunu açar."""
        if not svc:
            from logic.update_service import UpdateService
            repo = self.db.get_setting("github_repo", DEFAULT_GITHUB_REPO)
            svc = UpdateService(repo)
        from ui.update_dialog import UpdateDialog
        UpdateDialog(self, info, svc)

    def _on_startup_update_found(self, info: dict, svc):
        """Yeni bir sürüm yayınlandığında tüm şık bildirim bileşenlerini aktif eder."""
        # 1. Ana pencere üst banner'ı
        self._show_update_banner(info, svc)

        # 2. Üst başlık rozeti
        if hasattr(self, "header_actions_box") and self.header_actions_box.winfo_exists():
            if not hasattr(self, "btn_update_badge") or not self.btn_update_badge.winfo_exists():
                self.btn_update_badge = ctk.CTkButton(
                    self.header_actions_box,
                    text=f"🚀 {info.get('latest_version')}",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                    fg_color="#059669",
                    hover_color="#047857",
                    text_color="#FFFFFF",
                    height=28,
                    corner_radius=7,
                    command=lambda: self._open_update_center(info, svc)
                )
                self.btn_update_badge.pack(side="right", padx=(2, 2), pady=2)
                SimpleTooltip(self.btn_update_badge, "Yeni sürümü yüklemek için tıklayın")

        # 3. Sol menü alt sürüm alanı
        self._update_sidebar_for_new_version(info, svc)

    def check_updates_manual(self, simulate_preview: bool = False):
        """Kullanıcının manuel güncelleme denetimini yönetir."""
        if hasattr(self, "btn_sidebar_check") and self.btn_sidebar_check.winfo_exists():
            self.btn_sidebar_check.configure(state="disabled", text="⏳")

        if simulate_preview:
            # Önizleme ve test simülasyonu
            sim_info = {
                "success": True,
                "has_update": True,
                "latest_version": "v2.2.0",
                "current_version": APP_VERSION,
                "title": "NöbetMatik v2.2.0 - Yeni Özellikler & Güncelleme Paketi",
                "body": "## 🚀 NöbetMatik v2.2.0 Yenilikleri\n\n- 💰 Ek Ders Hakediş Hesaplamaları ve MEB 44. Madde Uyumu\n- 📋 Personel Devam Takip Tablosu ve Yeşil Hakediş Vurgulaması\n- 🎨 Modernleştirilmiş Okul Yönetim Merkezi Raporlar Ekranı\n- 🔔 Yeni Şık Otomatik Güncelleme Bildirimleri\n- ⚡ Performans ve Hata Düzeltmeleri",
                "html_url": "https://github.com/Barisbayrak19/nobetmatik/releases",
                "published_at": "2026-10-19",
                "download_url": "https://github.com/Barisbayrak19/nobetmatik/releases/download/v2.1.0/NobetMatik_v2.1.0_Kurulum.exe",
                "asset_name": "NobetMatik_v2.1.0_Kurulum.exe"
            }
            if hasattr(self, "btn_sidebar_check") and self.btn_sidebar_check.winfo_exists():
                self.btn_sidebar_check.configure(state="normal", text="🔄")
            from logic.update_service import UpdateService
            svc = UpdateService()
            self._on_startup_update_found(sim_info, svc)
            return

        def worker():
            try:
                from logic.update_service import UpdateService
                repo = self.db.get_setting("github_repo", DEFAULT_GITHUB_REPO)
                svc = UpdateService(repo)
                info = svc.check_for_updates()
                self.after(0, lambda: self._on_manual_update_result(info, svc))
            except Exception as e:
                self.after(0, lambda: self._on_manual_update_result({"success": False, "error": str(e)}, None))

        threading.Thread(target=worker, daemon=True).start()

    def _on_manual_update_result(self, info: dict, svc):
        if hasattr(self, "btn_sidebar_check") and self.btn_sidebar_check.winfo_exists():
            self.btn_sidebar_check.configure(state="normal", text="🔄")

        if not info.get("success"):
            if hasattr(self, "lbl_sidebar_version") and self.lbl_sidebar_version.winfo_exists():
                orig_text = self.lbl_sidebar_version.cget("text")
                self.lbl_sidebar_version.configure(text="⚠️ Bağlantı Yok", text_color="#EF4444")
                self.after(3500, lambda: self.lbl_sidebar_version.configure(text=orig_text, text_color="#94A3B8"))
            return

        if info.get("has_update"):
            self._on_startup_update_found(info, svc)
            self._open_update_center(info, svc)
        else:
            if hasattr(self, "lbl_sidebar_version") and self.lbl_sidebar_version.winfo_exists():
                orig_text = self.lbl_sidebar_version.cget("text")
                self.lbl_sidebar_version.configure(text="✔ Sürümünüz Güncel", text_color="#10B981")
                self.after(3500, lambda: self.lbl_sidebar_version.configure(text=orig_text, text_color="#94A3B8"))

    def on_close(self):
        try:
            from logic.network_service import stop_global_host_service
            stop_global_host_service()
        except Exception:
            pass

        if self.has_unsaved_changes:
            ans = messagebox.askyesnocancel("Çıkış Onayı", "Kaydedilmemiş değişiklikleriniz var. Çıkmadan önce kaydetmek ister misiniz?")
            if ans is True:
                self.save_changes()
                self.destroy()
            elif ans is False:
                self.destroy()
        else:
            self.destroy()
