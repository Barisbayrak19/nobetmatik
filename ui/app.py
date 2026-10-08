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
from logic.update_service import UpdateService
from core.logger import logger

from ui.theme import (
    setup_styles, setup_customtkinter, COLOR_BG, COLOR_HEADER_BG, COLOR_HEADER_TEXT,
    COLOR_PRIMARY, COLOR_SUCCESS, COLOR_BORDER, COLOR_BORDER_STRONG, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED,
    COLOR_SIDEBAR_BG, COLOR_SIDEBAR_ACTIVE, COLOR_SIDEBAR_HOVER, COLOR_SIDEBAR_TEXT, COLOR_SIDEBAR_MUTED,
    COLOR_BADGE_FREE, COLOR_BADGE_FREE_TXT, COLOR_BADGE_FIXED, COLOR_BADGE_FIXED_TXT,
    COLOR_BADGE_EMPTY, COLOR_BADGE_EMPTY_TXT, COLOR_CELL_SELECTED, COLOR_CELL_SELECTED_BORDER,
    FONT_FAMILY
)
from ui.schedule_grid import TURKISH_MONTHS
from logic.substitution_service import PERIOD_TIMES
from ui.wizard_view import WizardView
from ui.schedule_grid import ScheduleGrid
from ui.teacher_management import TeacherManagementDialog
from ui.location_management import LocationManagementDialog
from ui.distribution_dialog import DistributionDialog
from ui.import_dialog import ImportDialog
from ui.backup_dialog import BackupDialog
from ui.settings_dialog import SettingsDialog
from ui.shift_dialog import ShiftDialog
from ui.substitution_dialog import SubstitutionDialog
from ui.attendance_dialog import AttendanceDialog
from ui.timetable_export_dialog import TimetableExportDialog
from ui.update_dialog import UpdateDialog

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        setup_customtkinter()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1280x800")
        self.minsize(1024, 680)

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

        # Hafta Yönetimi (Pazartesi bazlı)
        # Referans nöbet haftası: 28 Eylül 2026
        self.current_week_start = datetime.date(2026, 9, 28)
        self.has_unsaved_changes = False

        setup_styles(self)

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
        self._build_kpi_cards()
        self._build_action_bar()
        self._build_workspace()
        self._build_footer()

        self.undo_manager.register_callback(self.update_undo_redo_ui)
        self.update_header_info()

        # Açılışta otomatik güncelleme denetimi (arka planda sessiz)
        if self.db.get_setting("auto_check_updates", "1") == "1":
            self.after(3500, lambda: self.check_for_updates(silent=True))

    def get_current_week_str(self) -> str:
        return self.current_week_start.isoformat()

    # --- 1. SOL MODERN NAVİGASYON (SIDEBAR) ---
    def _build_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(
            self,
            width=220,
            fg_color="#0F172A",
            corner_radius=0
        )
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)

        # Üst Okul & Yönetici Bilgi Kartı
        school = self.db.get_school_info()
        brand_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        brand_frame.pack(fill="x", padx=16, pady=(16, 10))

        lbl_logo = ctk.CTkLabel(
            brand_frame,
            text="🛡️ NöbetMatik",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color="#38BDF8"
        )
        lbl_logo.pack(anchor="w")

        self.lbl_sidebar_school = ctk.CTkLabel(
            brand_frame,
            text=school.name if school.name else "Okul Yönetim Sistemi",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color="#F8FAFC",
            wraplength=185,
            justify="left"
        )
        self.lbl_sidebar_school.pack(anchor="w", pady=(4, 0))

        self.lbl_sidebar_year = ctk.CTkLabel(
            brand_frame,
            text=f"{school.academic_year} Eğitim Yılı",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color="#94A3B8"
        )
        self.lbl_sidebar_year.pack(anchor="w", pady=(1, 0))

        self.lbl_sidebar_principal = ctk.CTkLabel(
            brand_frame,
            text=f"Müdür: {school.principal_name}" if school.principal_name else "Müdürlük",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color="#94A3B8",
            wraplength=185,
            justify="left"
        )
        self.lbl_sidebar_principal.pack(anchor="w", pady=(1, 0))

        # İnce ayırıcı çizgi
        div1 = ctk.CTkFrame(self.sidebar_frame, fg_color="#1E293B", height=1)
        div1.pack(fill="x", padx=12, pady=(10, 12))

        # Menü Başlığı
        lbl_menu_title = ctk.CTkLabel(
            self.sidebar_frame,
            text="ANA MENÜ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color="#64748B"
        )
        lbl_menu_title.pack(anchor="w", padx=16, pady=(0, 4))

        # Menü Butonları
        self.sidebar_buttons = {}
        nav_items = [
            ("weekly", "📅 Haftalık Nöbet", None, True),
            ("teachers", "👥 Öğretmenler", self.open_teachers, False),
            ("locations", "📍 Nöbet Yerleri", self.open_locations, False),
            ("distribute", "⚡ Otomatik Dağıtım", self.open_auto_distribution, False),
            ("import", "📥 İçe Aktarma", self.open_import, False),
            ("reports", "📊 Raporlar", self.open_reports_menu, False),
            ("settings", "⚙️ Ayarlar", self.open_settings, False),
        ]

        for key, text, cmd, is_active in nav_items:
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=text,
                height=32,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold" if is_active else "normal"),
                anchor="w",
                fg_color="#2563EB" if is_active else "transparent",
                hover_color="#1D4ED8" if is_active else "#1E293B",
                text_color="#FFFFFF" if is_active else "#E2E8F0",
                corner_radius=6,
                command=cmd
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.sidebar_buttons[key] = btn

        # Alt Alan (Yedekleme, Güncelle ve Sürüm)
        bottom_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", padx=10, pady=12)

        div2 = ctk.CTkFrame(bottom_frame, fg_color="#1E293B", height=1)
        div2.pack(fill="x", pady=(0, 8))

        btn_backup = ctk.CTkButton(
            bottom_frame,
            text="💾 Veri Yedekleme",
            height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            anchor="w",
            fg_color="transparent",
            hover_color="#1E293B",
            text_color="#94A3B8",
            corner_radius=5,
            command=self.open_backup
        )
        btn_backup.pack(fill="x", pady=1)

        btn_update = ctk.CTkButton(
            bottom_frame,
            text="🔄 Güncellemeler",
            height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            anchor="w",
            fg_color="transparent",
            hover_color="#1E293B",
            text_color="#94A3B8",
            corner_radius=5,
            command=lambda: self.check_for_updates(silent=False)
        )
        btn_update.pack(fill="x", pady=1)

        lbl_ver = ctk.CTkLabel(
            bottom_frame,
            text=f"v{APP_VERSION} (Kararlı)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color="#475569"
        )
        lbl_ver.pack(anchor="w", padx=6, pady=(6, 0))

    # --- 2. ÜST BİLGİ & HAFTA NAVİGASYONU ---
    def _build_top_header(self):
        self.top_header_frame = ctk.CTkFrame(self.main_container, fg_color="#FFFFFF", corner_radius=0, height=58, border_width=1, border_color="#E2E8F0")
        self.top_header_frame.pack(fill="x", side="top")

        left_box = ctk.CTkFrame(self.top_header_frame, fg_color="transparent")
        left_box.pack(side="left", padx=16, pady=8)

        lbl_title = ctk.CTkLabel(
            left_box,
            text="HAFTALIK NÖBET YÖNETİMİ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color="#0F172A"
        )
        lbl_title.pack(anchor="w")

        self.lbl_header_school = ctk.CTkLabel(
            left_box,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color="#64748B"
        )
        self.lbl_header_school.pack(anchor="w")

        # Üst Sağ Hafta Gezinme Kartı
        nav_card = ctk.CTkFrame(self.top_header_frame, fg_color="#F8FAFC", corner_radius=6, border_width=1, border_color="#E2E8F0")
        nav_card.pack(side="right", padx=16, pady=8)

        btn_prev = ctk.CTkButton(
            nav_card,
            text="← Önceki Hafta",
            width=92,
            height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            fg_color="#FFFFFF",
            hover_color="#F1F5F9",
            text_color="#0F172A",
            border_width=1,
            border_color="#CBD5E1",
            corner_radius=5,
            command=self.prev_week
        )
        btn_prev.pack(side="left", padx=(3, 2), pady=3)

        self.lbl_week_range = ctk.CTkLabel(
            nav_card,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color="#0F172A",
            fg_color="#EFF6FF",
            corner_radius=5,
            padx=12,
            pady=3
        )
        self.lbl_week_range.pack(side="left", padx=3, pady=3)

        btn_next = ctk.CTkButton(
            nav_card,
            text="Sonraki Hafta →",
            width=92,
            height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            fg_color="#FFFFFF",
            hover_color="#F1F5F9",
            text_color="#0F172A",
            border_width=1,
            border_color="#CBD5E1",
            corner_radius=5,
            command=self.next_week
        )
        btn_next.pack(side="left", padx=2, pady=3)

        btn_today = ctk.CTkButton(
            nav_card,
            text="Bugün",
            width=50,
            height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            fg_color="#0F172A",
            hover_color="#1E293B",
            text_color="#FFFFFF",
            corner_radius=5,
            command=self.current_week
        )
        btn_today.pack(side="left", padx=(3, 3), pady=3)

    # --- 3. İSTATİSTİK (KPI) KARTLARI ---
    def _build_kpi_cards(self):
        self.kpi_cards_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.kpi_cards_frame.pack(fill="x", padx=16, pady=(10, 6))

        for i in range(5):
            self.kpi_cards_frame.columnconfigure(i, weight=1, uniform="kpi")

        self.kpi_widgets = {}

        card_defs = [
            ("teachers", "Aktif Öğretmen", "#0F172A", "0"),
            ("filled", "Dolu Nöbet", "#2563EB", "0 / 0"),
            ("missing", "Eksik Nöbet", "#DC2626", "0"),
            ("fixed", "Sabit Görev", "#D97706", "0"),
            ("rate", "Dağılım Oranı", "#059669", "%0"),
        ]

        for idx, (key, title, val_color, def_val) in enumerate(card_defs):
            card = ctk.CTkFrame(
                self.kpi_cards_frame,
                fg_color="#FFFFFF",
                corner_radius=8,
                border_width=1,
                border_color="#E2E8F0"
            )
            card.grid(row=0, column=idx, padx=4, pady=0, sticky="nsew")

            lbl_val = ctk.CTkLabel(
                card,
                text=def_val,
                font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
                text_color=val_color
            )
            lbl_val.pack(anchor="w", padx=12, pady=(8, 1))

            lbl_sub = ctk.CTkLabel(
                card,
                text=title,
                font=ctk.CTkFont(family=FONT_FAMILY, size=9),
                text_color="#64748B"
            )
            lbl_sub.pack(anchor="w", padx=12, pady=(0, 8))

            self.kpi_widgets[key] = (lbl_val, lbl_sub)

    # --- 4. AKSİYON BUTONLARI ÇUBUĞU ---
    def _build_action_bar(self):
        self.action_bar_frame = ctk.CTkFrame(self.main_container, fg_color="#FFFFFF", corner_radius=8, border_width=1, border_color="#E2E8F0")
        self.action_bar_frame.pack(fill="x", padx=16, pady=(2, 8))

        left_box = ctk.CTkFrame(self.action_bar_frame, fg_color="transparent")
        left_box.pack(side="left", padx=8, pady=6)

        # Geri / İleri Al
        self.btn_undo = ctk.CTkButton(
            left_box,
            text="↶ Geri",
            width=50,
            height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            fg_color="#F8FAFC",
            hover_color="#F1F5F9",
            text_color="#0F172A",
            border_width=1,
            border_color="#CBD5E1",
            corner_radius=5,
            state="disabled",
            command=self.do_undo
        )
        self.btn_undo.pack(side="left", padx=(0, 2))

        self.btn_redo = ctk.CTkButton(
            left_box,
            text="↷ İleri",
            width=50,
            height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            fg_color="#F8FAFC",
            hover_color="#F1F5F9",
            text_color="#0F172A",
            border_width=1,
            border_color="#CBD5E1",
            corner_radius=5,
            state="disabled",
            command=self.do_redo
        )
        self.btn_redo.pack(side="left", padx=(0, 6))

        # ⚡ Otomatik Dağıt (Öne Çıkan Modern Mavi Buton)
        btn_distribute = ctk.CTkButton(
            left_box,
            text="⚡ Otomatik Dağıt",
            width=125,
            height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            text_color="#FFFFFF",
            corner_radius=6,
            command=self.open_auto_distribution
        )
        btn_distribute.pack(side="left", padx=(0, 5))

        # ↔ Nöbet Kaydır Grubu
        f_shift = ctk.CTkFrame(left_box, fg_color="transparent")
        f_shift.pack(side="left", padx=(0, 5))

        btn_shift = ctk.CTkButton(
            f_shift,
            text="↔ Nöbet Kaydır",
            width=105,
            height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            fg_color="#FFFFFF",
            hover_color="#F1F5F9",
            text_color="#0F172A",
            border_width=1,
            border_color="#CBD5E1",
            corner_radius=5,
            command=self.quick_shift
        )
        btn_shift.pack(side="left")

        btn_shift_opt = ctk.CTkButton(
            f_shift,
            text="▾",
            width=20,
            height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            fg_color="#FFFFFF",
            hover_color="#F1F5F9",
            text_color="#0F172A",
            border_width=1,
            border_color="#CBD5E1",
            corner_radius=5,
            command=self.open_shift_dialog
        )
        btn_shift_opt.pack(side="left", padx=(2, 0))

        # ＋ Boş Ders Doldurma
        btn_sub = ctk.CTkButton(
            left_box,
            text="＋ Boş Ders Doldurma",
            width=135,
            height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            fg_color="#FFFFFF",
            hover_color="#F1F5F9",
            text_color="#0F172A",
            border_width=1,
            border_color="#CBD5E1",
            corner_radius=5,
            command=self.open_substitution_dialog
        )
        btn_sub.pack(side="left", padx=(0, 5))

        # 📅 Sonraki Haftaya Aktar Grubu
        f_carry = ctk.CTkFrame(left_box, fg_color="transparent")
        f_carry.pack(side="left", padx=(0, 5))

        btn_carry = ctk.CTkButton(
            f_carry,
            text="📅 Sonraki Haftaya Aktar",
            width=145,
            height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            fg_color="#FFFFFF",
            hover_color="#F1F5F9",
            text_color="#0F172A",
            border_width=1,
            border_color="#CBD5E1",
            corner_radius=5,
            command=self.quick_copy_next_same
        )
        btn_carry.pack(side="left")

        btn_carry_opt = ctk.CTkButton(
            f_carry,
            text="▾",
            width=20,
            height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            fg_color="#FFFFFF",
            hover_color="#F1F5F9",
            text_color="#0F172A",
            border_width=1,
            border_color="#CBD5E1",
            corner_radius=5,
            command=self.open_copy_menu
        )
        btn_carry_opt.pack(side="left", padx=(2, 0))

        # 🖨️ Çıktılar Butonu
        self.btn_export = ctk.CTkButton(
            left_box,
            text="🖨️ Çıktılar ▾",
            width=90,
            height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            fg_color="#FFFFFF",
            hover_color="#F1F5F9",
            text_color="#0F172A",
            border_width=1,
            border_color="#CBD5E1",
            corner_radius=5,
            command=self.open_export_menu
        )
        self.btn_export.pack(side="left", padx=(0, 5))

        # ⋯ Daha Fazla Butonu
        self.btn_more = ctk.CTkButton(
            left_box,
            text="⋯ Daha Fazla ▾",
            width=100,
            height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            fg_color="#FFFFFF",
            hover_color="#F1F5F9",
            text_color="#0F172A",
            border_width=1,
            border_color="#CBD5E1",
            corner_radius=5,
            command=self.open_more_menu
        )
        self.btn_more.pack(side="left", padx=(0, 5))

        # Sağ Taraf: Değişiklikleri Kaydet
        btn_save = ctk.CTkButton(
            self.action_bar_frame,
            text="💾 Değişiklikleri Kaydet",
            width=150,
            height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            fg_color="#059669",
            hover_color="#047857",
            text_color="#FFFFFF",
            corner_radius=6,
            command=self.save_changes
        )
        btn_save.pack(side="right", padx=8, pady=6)

        # Çıktılar ve Menüler Yapılandırması
        self.export_menu = tk.Menu(self, tearoff=0)
        self.export_menu.add_command(label="🖨️ Baskı Önizleme ve Yazdırma Penceresi...", command=self.open_print_preview)
        self.export_menu.add_separator()
        self.export_menu.add_command(label="📄 PDF Belgesi Olarak Kaydet (.pdf)", command=self.export_pdf)
        self.export_menu.add_command(label="📊 Excel Tablosu Olarak Kaydet (.xlsx)", command=self.export_excel)
        self.export_menu.add_command(label="📝 Word Belgesi Olarak Kaydet (.docx)", command=self.export_word)
        self.export_menu.add_command(label="🌐 Yazdırılabilir HTML Sayfası (.html)", command=self.export_html)
        self.export_menu.add_command(label="📑 CSV Listesi Olarak Kaydet (.csv)", command=self.export_csv)

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
        self.more_menu.add_command(label="📚 Ders Programı Rapor Merkezi", command=self.open_timetable_exports)
        self.more_menu.add_separator()
        self.more_menu.add_command(label="🔄 Nöbet Rotasyon ve Kaydırma Ayarları...", command=self.open_shift_dialog)
        self.more_menu.add_command(label="💾 Sistem Veritabanı Yedekleme...", command=self.open_backup)
        self.more_menu.add_separator()
        self.more_menu.add_command(label="🔄 Güncellemeleri Denetle...", command=lambda: self.check_for_updates(silent=False))

        self.reports_menu = tk.Menu(self, tearoff=0)
        self.reports_menu.add_command(label="🖨️ Nöbet Çizelgesi Önizleme & Yazdır", command=self.open_print_preview)
        self.reports_menu.add_command(label="📄 Nöbet Çizelgesi PDF Kaydet", command=self.export_pdf)
        self.reports_menu.add_command(label="📊 Nöbet Çizelgesi Excel Kaydet", command=self.export_excel)
        self.reports_menu.add_separator()
        self.reports_menu.add_command(label="📚 Ders Programı Çıktı ve Rapor Merkezi...", command=self.open_timetable_exports)
        self.reports_menu.add_command(label="📅 Personel Devam Takip Çizelgeleri...", command=self.open_attendance_dialog)

    # --- 5. ÇALIŞMA ALANI (GRID + SAĞ DETAY PANELİ) ---
    def _build_workspace(self):
        self.workspace_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.workspace_frame.pack(fill="both", expand=True, padx=16, pady=(0, 6))

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

        # Sağ Detay Paneli (Varsayılan olarak kapalıdır, hücre seçilince sağdan açılır)
        self.detail_panel = ctk.CTkFrame(
            self.workspace_frame,
            width=320,
            fg_color="#FFFFFF",
            corner_radius=8,
            border_width=1,
            border_color="#CBD5E1"
        )
        self.detail_panel.pack_propagate(False)
        self.is_detail_open = False

    def on_cell_selected(self, cell):
        """Çizelgede bir hücre seçildiğinde sağ detay panelini açar ve doldurur."""
        self.show_detail_panel(cell)

    def close_detail_panel(self):
        """Sağ detay panelini kapatır ve çizelgeyi tam genişliğe genişletir."""
        if self.is_detail_open:
            self.detail_panel.pack_forget()
            self.is_detail_open = False
        if hasattr(self, "schedule_grid"):
            self.schedule_grid.deselect_cell()

    def show_detail_panel(self, cell):
        """Seçilen nöbet hücresinin detaylarını modern kartlarla gösterir."""
        if not self.is_detail_open:
            self.detail_panel.pack(side="right", fill="y", padx=(8, 0))
            self.is_detail_open = True

        for w in self.detail_panel.winfo_children():
            w.destroy()

        # Başlık ve Kapat Butonu (✕)
        hdr = ctk.CTkFrame(self.detail_panel, fg_color="transparent")
        hdr.pack(fill="x", padx=12, pady=(12, 6))

        lbl_hdr = ctk.CTkLabel(
            hdr,
            text="Nöbet Detayı",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color="#0F172A"
        )
        lbl_hdr.pack(side="left")

        btn_close = ctk.CTkButton(
            hdr,
            text="✕",
            width=26,
            height=26,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color="transparent",
            hover_color="#F1F5F9",
            text_color="#64748B",
            corner_radius=4,
            command=self.close_detail_panel
        )
        btn_close.pack(side="right")

        # Kaydırılabilir Detay Alanı
        scroll = ctk.CTkScrollableFrame(self.detail_panel, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        # 1. Öğretmen Bilgi Kartı
        teacher_card = ctk.CTkFrame(scroll, fg_color="#F8FAFC", corner_radius=6, border_width=1, border_color="#E2E8F0")
        teacher_card.pack(fill="x", padx=4, pady=(4, 6))

        if cell.teacher:
            name_str = cell.teacher.name
            branch_str = f"◉ {cell.teacher.branch}" if cell.teacher.branch else "◉ Branş Belirtilmemiş"
        else:
            name_str = "[BOŞ GÖREV SLOTU]"
            branch_str = "Atanmış öğretmen bulunmuyor"

        lbl_tname = ctk.CTkLabel(
            teacher_card,
            text=name_str,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color="#0F172A",
            wraplength=270,
            justify="left"
        )
        lbl_tname.pack(anchor="w", padx=10, pady=(8, 2))

        lbl_tbranch = ctk.CTkLabel(
            teacher_card,
            text=branch_str,
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color="#64748B"
        )
        lbl_tbranch.pack(anchor="w", padx=10, pady=(0, 8))

        # 2. Görev Yeri & Tarih Bilgisi
        info_card = ctk.CTkFrame(scroll, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#E2E8F0")
        info_card.pack(fill="x", padx=4, pady=4)

        try:
            week_dt = datetime.date.fromisoformat(self.get_current_week_str())
            day_names_list = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
            day_idx = day_names_list.index(cell.day.name) if cell.day.name in day_names_list else 0
            cell_dt = week_dt + datetime.timedelta(days=day_idx)
            m_name = TURKISH_MONTHS[cell_dt.month] if 1 <= cell_dt.month <= 12 else ""
            date_str = f"{cell.day.name}, {cell_dt.day} {m_name} {cell_dt.year}"
        except Exception:
            date_str = cell.day.name

        lbl_date = ctk.CTkLabel(
            info_card,
            text=f"📅 {date_str}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color="#0F172A"
        )
        lbl_date.pack(anchor="w", padx=10, pady=(8, 2))

        lbl_loc = ctk.CTkLabel(
            info_card,
            text=f"📍 {cell.location.name} (Slot {cell.slot_index + 1})",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color="#334155"
        )
        lbl_loc.pack(anchor="w", padx=10, pady=(0, 4))

        if cell.assignment.fixed:
            status_text = "🔒 Sabit Nöbet (Kilitli)"
            status_color = "#B45309"
        elif cell.teacher:
            status_text = "🟢 Normal Nöbet Ataması"
            status_color = "#15803D"
        else:
            status_text = "🔴 Boş / Eksik Nöbet"
            status_color = "#DC2626"

        lbl_status_tag = ctk.CTkLabel(
            info_card,
            text=status_text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color=status_color
        )
        lbl_status_tag.pack(anchor="w", padx=10, pady=(0, 8))

        # 3. Boş Dersler Bölümü
        lbl_sec1 = ctk.CTkLabel(
            scroll,
            text="BOŞ DERSLER",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color="#64748B"
        )
        lbl_sec1.pack(anchor="w", padx=6, pady=(8, 2))

        free_card = ctk.CTkFrame(scroll, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#E2E8F0")
        free_card.pack(fill="x", padx=4, pady=2)

        if cell.teacher:
            free_periods = self.schedule_grid.get_teacher_free_periods(cell.teacher.id, cell.day.name)
            if free_periods:
                for p in free_periods:
                    t_str = PERIOD_TIMES.get(p, "")
                    time_info = f" ({t_str})" if t_str else ""
                    p_lbl = ctk.CTkLabel(
                        free_card,
                        text=f"🟢 {p}. Ders{time_info}",
                        font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
                        text_color="#15803D"
                    )
                    p_lbl.pack(anchor="w", padx=10, pady=2)
            else:
                lbl_nofree = ctk.CTkLabel(
                    free_card,
                    text="Bu gün nöbet saatlerinde boş dersi yok.",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=9),
                    text_color="#64748B"
                )
                lbl_nofree.pack(anchor="w", padx=10, pady=6)
        else:
            lbl_nofree = ctk.CTkLabel(
                free_card,
                text="Slot boş.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=9),
                text_color="#64748B"
            )
            lbl_nofree.pack(anchor="w", padx=10, pady=6)

        # 4. Hızlı İşlem Butonları
        lbl_sec2 = ctk.CTkLabel(
            scroll,
            text="HIZLI İŞLEMLER",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color="#64748B"
        )
        lbl_sec2.pack(anchor="w", padx=6, pady=(10, 2))

        actions_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        actions_frame.pack(fill="x", padx=4, pady=2)

        btn_pick = ctk.CTkButton(
            actions_frame,
            text="👤 Öğretmeni Değiştir / Ata",
            height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            fg_color="#F8FAFC",
            hover_color="#F1F5F9",
            text_color="#0F172A",
            border_width=1,
            border_color="#CBD5E1",
            corner_radius=5,
            command=lambda: [self.schedule_grid.open_teacher_picker(cell), self.show_detail_panel(cell)]
        )
        btn_pick.pack(fill="x", pady=2)

        if cell.teacher:
            btn_move = ctk.CTkButton(
                actions_frame,
                text="↔ Nöbeti Kaydır...",
                height=28,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                fg_color="#F8FAFC",
                hover_color="#F1F5F9",
                text_color="#0F172A",
                border_width=1,
                border_color="#CBD5E1",
                corner_radius=5,
                command=lambda: [self.schedule_grid.open_move_dialog(cell), self.show_detail_panel(cell)]
            )
            btn_move.pack(fill="x", pady=2)

            btn_swap = ctk.CTkButton(
                actions_frame,
                text="🔄 Başkasıyla Takas Et...",
                height=28,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                fg_color="#F8FAFC",
                hover_color="#F1F5F9",
                text_color="#0F172A",
                border_width=1,
                border_color="#CBD5E1",
                corner_radius=5,
                command=lambda: [self.schedule_grid.open_swap_dialog(cell), self.show_detail_panel(cell)]
            )
            btn_swap.pack(fill="x", pady=2)

            lock_text = "🔓 Nöbet Kilidini Aç" if cell.assignment.fixed else "🔒 Sabit Nöbet Yap"
            btn_lock = ctk.CTkButton(
                actions_frame,
                text=lock_text,
                height=28,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                fg_color="#FEF3C7" if cell.assignment.fixed else "#F8FAFC",
                hover_color="#FDE68A",
                text_color="#B45309" if cell.assignment.fixed else "#0F172A",
                border_width=1,
                border_color="#F59E0B" if cell.assignment.fixed else "#CBD5E1",
                corner_radius=5,
                command=lambda: [self.schedule_grid.toggle_cell_fixed(cell), self.show_detail_panel(cell)]
            )
            btn_lock.pack(fill="x", pady=2)

            btn_clear = ctk.CTkButton(
                actions_frame,
                text="❌ Nöbeti Sil",
                height=28,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                fg_color="#FEE2E2",
                hover_color="#FECACA",
                text_color="#DC2626",
                border_width=1,
                border_color="#FCA5A5",
                corner_radius=5,
                command=lambda: [self.schedule_grid.clear_cell(cell), self.show_detail_panel(cell)]
            )
            btn_clear.pack(fill="x", pady=2)

        # 5. Öğretmen Bilgisi Özeti
        if cell.teacher:
            lbl_sec3 = ctk.CTkLabel(
                scroll,
                text="ÖĞRETMEN BİLGİSİ",
                font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
                text_color="#64748B"
            )
            lbl_sec3.pack(anchor="w", padx=6, pady=(10, 2))

            stat_card = ctk.CTkFrame(scroll, fg_color="#FFFFFF", corner_radius=6, border_width=1, border_color="#E2E8F0")
            stat_card.pack(fill="x", padx=4, pady=(2, 8))

            all_week_assigns = self.db.get_assignments_for_week(self.get_current_week_str())
            t_duty_count = sum(1 for a in all_week_assigns if a.teacher_id == cell.teacher.id)
            t_lessons = self.db.get_teacher_lessons(cell.teacher.id)
            total_lessons = sum(1 for l in t_lessons if not l.is_free)

            stats_rows = [
                ("Branş:", cell.teacher.branch or "Genel"),
                ("Toplam Nöbet:", f"{t_duty_count} gün"),
                ("Haftalık Ders:", f"{total_lessons} saat"),
            ]
            for label_t, val_t in stats_rows:
                r_fr = ctk.CTkFrame(stat_card, fg_color="transparent")
                r_fr.pack(fill="x", padx=10, pady=2)
                ctk.CTkLabel(r_fr, text=label_t, font=ctk.CTkFont(family=FONT_FAMILY, size=9), text_color="#64748B").pack(side="left")
                ctk.CTkLabel(r_fr, text=val_t, font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"), text_color="#0F172A").pack(side="right")

    # --- 6. ALT BİLGİ / DURUM ÇUBUĞU / LEGEND ---
    def _build_footer(self):
        self.footer_frame = ctk.CTkFrame(self.main_container, fg_color="#FFFFFF", height=30, corner_radius=0, border_width=1, border_color="#E2E8F0")
        self.footer_frame.pack(fill="x", side="bottom")

        # Sol Gösterge (Legend)
        legend_box = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        legend_box.pack(side="left", padx=12, pady=3)

        badges = [
            ("🟢 Uygun / Boş Ders", "#15803D"),
            ("🟠 Sabit Görev", "#B45309"),
            ("🔴 Eksik Nöbet", "#DC2626"),
            ("🔵 Seçili Hücre", "#2563EB"),
        ]
        for txt, color in badges:
            lbl = ctk.CTkLabel(
                legend_box,
                text=txt,
                font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
                text_color=color
            )
            lbl.pack(side="left", padx=(0, 10))

        # Orta: Durum Mesajı
        self.lbl_status = ctk.CTkLabel(
            self.footer_frame,
            text="Hazır. Öğretmenleri sürükleyerek veya tıklayarak detayını inceleyebilirsiniz.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color="#64748B"
        )
        self.lbl_status.pack(side="left", padx=8)

        # Sağ: Son Kayıt Zamanı
        self.lbl_last_save = ctk.CTkLabel(
            self.footer_frame,
            text=f"Son kayıt: Bugün {datetime.datetime.now().strftime('%H:%M')}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color="#94A3B8"
        )
        self.lbl_last_save.pack(side="right", padx=12)

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
        try:
            btn = self.sidebar_buttons.get("reports")
            if btn:
                x = btn.winfo_rootx() + btn.winfo_width()
                y = btn.winfo_rooty()
            else:
                x = self.winfo_pointerx()
                y = self.winfo_pointery()
            self.reports_menu.tk_popup(x, y)
        finally:
            self.reports_menu.grab_release()

    def update_header_info(self):
        school = self.db.get_school_info()
        self.lbl_header_school.configure(text=f"{school.name} • {school.academic_year} Eğitim Öğretim Yılı")
        if hasattr(self, "lbl_sidebar_school"):
            self.lbl_sidebar_school.configure(text=school.name if school.name else "Okul Yönetim Sistemi")
        if hasattr(self, "lbl_sidebar_year"):
            self.lbl_sidebar_year.configure(text=f"{school.academic_year} Eğitim Yılı")
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
            if "fixed" in self.kpi_widgets:
                self.kpi_widgets["fixed"][0].configure(text=str(fixed_count))
            if "rate" in self.kpi_widgets:
                self.kpi_widgets["rate"][0].configure(text=f"%{rate_pct}")

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
        self.btn_undo.configure(state="normal" if can_u else "disabled")
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
        self.require_admin_password(
            lambda: DistributionDialog(
                parent=self,
                db=self.db,
                week_start=self.get_current_week_str(),
                on_applied=lambda: [self.schedule_grid.refresh(), self.on_duty_data_changed()]
            ),
            "Otomatik Nöbet Dağıtımı"
        )

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
        self.require_admin_password(
            lambda: TeacherManagementDialog(
                parent=self,
                db=self.db,
                on_data_changed=lambda: [self.schedule_grid.refresh(), self.update_header_info()]
            ),
            "Öğretmen Yönetimi"
        )

    def open_locations(self):
        self.require_admin_password(
            lambda: LocationManagementDialog(
                parent=self,
                db=self.db,
                on_data_changed=lambda: [self.schedule_grid.refresh(), self.update_header_info()]
            ),
            "Nöbet Yerleri Yönetimi"
        )

    def open_import(self):
        ImportDialog(
            parent=self,
            db=self.db,
            on_imported=lambda: [self.schedule_grid.refresh(), self.update_header_info()]
        )

    def open_backup(self):
        BackupDialog(
            parent=self,
            backup_service=self.backup_service,
            on_restore_complete=lambda: [self.schedule_grid.refresh(), self.update_header_info()]
        )

    def open_settings(self):
        self.require_admin_password(
            lambda: SettingsDialog(
                parent=self,
                db=self.db,
                on_saved=self._on_settings_saved
            ),
            "Sistem Ayarları"
        )

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

        # Tüm CustomTkinter butonları ve etiketlerini dinamik güncelle
        def _recursive_update(w):
            try:
                if isinstance(w, ctk.CTkButton):
                    w.configure(font=ctk.CTkFont(family=fam, size=ui_sz, weight="bold"))
                elif isinstance(w, ctk.CTkLabel):
                    old_f = w.cget("font")
                    weight = "bold" if hasattr(old_f, "cget") and old_f.cget("weight") == "bold" else "normal"
                    w.configure(font=ctk.CTkFont(family=fam, size=ui_sz, weight=weight))
            except Exception:
                pass
            for child in w.winfo_children():
                _recursive_update(child)

        if hasattr(self, "sidebar_frame"):
            _recursive_update(self.sidebar_frame)
        if hasattr(self, "top_header_frame"):
            _recursive_update(self.top_header_frame)
        if hasattr(self, "kpi_cards_frame"):
            _recursive_update(self.kpi_cards_frame)
        if hasattr(self, "action_bar_frame"):
            _recursive_update(self.action_bar_frame)
        if hasattr(self, "footer_frame"):
            _recursive_update(self.footer_frame)
        if hasattr(self, "detail_panel"):
            _recursive_update(self.detail_panel)

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

    def open_timetable_exports(self, default_tab: int = 0):
        TimetableExportDialog(self, self.db, default_tab=default_tab)

    def check_for_updates(self, silent: bool = False):
        """GitHub Releases üzerinden yeni sürüm denetimi yapar."""
        repo = self.db.get_setting("github_repo", DEFAULT_GITHUB_REPO)
        svc = UpdateService(repo)

        def worker():
            info = svc.check_for_updates()
            self.after(0, lambda: self._on_update_result(info, svc, silent))

        threading.Thread(target=worker, daemon=True).start()

    def _on_update_result(self, info: dict, svc: UpdateService, silent: bool):
        if not info.get("success"):
            if not silent:
                messagebox.showwarning("Güncelleme Denetimi", f"Güncelleme denetlenemedi:\n{info.get('error')}", parent=self)
            return

        if info.get("has_update"):
            UpdateDialog(self, info, svc)
        elif not silent:
            messagebox.showinfo(
                "Yazılım Güncel",
                f"Tebrikler! En güncel NöbetMatik sürümünü (v{APP_VERSION}) kullanıyorsunuz.",
                parent=self
            )

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
