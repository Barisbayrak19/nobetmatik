"""
Günün Özeti ve Canlı Nöbet Panosu (Daily Executive Dashboard)
- Günün Nöbetçi Kadrosu ve Nöbet Yerleri
- Boş Sınıflar ve İkame Görevlendirme Takip Merkezi
- Saat Saat Müsait Öğretmen Havuzu
- Sınıfların Günlük Ders ve Öğretmen Dağılım Matrisi
- PDF / Yazdırma Raporu ve WhatsApp Entegrasyonu
"""
import os
import datetime
from typing import Dict, List, Any, Optional, Callable
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk

from core.database import Database
from core.models import Teacher, Location, Day, Assignment, TeacherLesson, SubstitutionAssignment, SchoolInfo
from logic.duty_service import DutyService
from logic.substitution_service import SubstitutionService, PERIOD_TIMES
from core.logger import logger
import ui.theme as theme
from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    COLOR_BORDER, COLOR_BORDER_STRONG, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED,
    FONT_FAMILY, BTN_RADIUS, CARD_RADIUS
)

TURKISH_DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
TURKISH_MONTHS = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

def to_title_case(text: str) -> str:
    if not text:
        return ""
    words = text.strip().split()
    res = []
    for w in words:
        if not w:
            continue
        first = w[0].replace('i', 'İ').replace('ı', 'I').upper()
        rest = w[1:].replace('I', 'ı').replace('İ', 'i').lower()
        res.append(first + rest)
    return " ".join(res)


class DailySummaryView(ctk.CTkFrame):
    """
    Günün Özeti ve Canlı Nöbet Panosu.
    Nöbetçiler, boş sınıflar, ikame durumu ve müsait öğretmenleri canlı sunar.
    """
    def __init__(
        self,
        parent: tk.Widget,
        db: Database,
        on_open_substitution: Optional[Callable] = None,
        on_open_whatsapp: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(
            parent,
            fg_color=COLOR_BG,
            corner_radius=0,
            overwrite_preferred_drawing_method="circle_shapes",
            **kwargs
        )
        self.db = db
        self.undo_manager = None
        self.duty_service = DutyService(self.db)
        self.sub_service = SubstitutionService(self.db)
        self.on_open_substitution = on_open_substitution
        self.on_open_whatsapp = on_open_whatsapp

        # Seçili gün (varsayılan: Bugün)
        self.current_date = datetime.date.today()
        # Hafta sonu ise en yakın Cuma veya Pazartesi'ye ayarla
        if self.current_date.weekday() == 5:
            self.current_date -= datetime.timedelta(days=1)
        elif self.current_date.weekday() == 6:
            self.current_date += datetime.timedelta(days=1)

        self.current_tab = "empty_classes"  # empty_classes | free_teachers | class_matrix

        self._build_ui()
        self.load_data()

    def _build_ui(self):
        # Ana Kapsayıcı
        self.main_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0
        )
        self.main_scroll.pack(fill="both", expand=True, padx=16, pady=12)

        # 1. ÜST ÇUBUK: BAŞLIK, TARİH SEÇİCİ VE HIZLI EYLEMLER
        self._build_header_card()

        # 2. KPI ÖZET KARTLARI (4 KART)
        self._build_kpi_cards()

        # 3. İKİ KOLONLU ANA İÇERİK ALANI
        self.content_panes = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        self.content_panes.pack(fill="both", expand=True, pady=(0, 16))

        # Sol Kolon (Nöbet Yerleri ve Görevliler)
        self.left_col = ctk.CTkFrame(
            self.content_panes,
            fg_color="#FFFFFF",
            corner_radius=theme.GRID_CELL_RADIUS,
            border_width=theme.GRID_BORDER_WIDTH,
            border_color=theme.GRID_BORDER_COLOR,
            overwrite_preferred_drawing_method="circle_shapes"
        )
        self.left_col.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # Sağ Kolon (Boş Sınıf & İkame Merkezi)
        self.right_col = ctk.CTkFrame(
            self.content_panes,
            fg_color="#FFFFFF",
            corner_radius=theme.GRID_CELL_RADIUS,
            border_width=theme.GRID_BORDER_WIDTH,
            border_color=theme.GRID_BORDER_COLOR,
            overwrite_preferred_drawing_method="circle_shapes"
        )
        self.right_col.pack(side="left", fill="both", expand=True, padx=(8, 0))

        # Sol Kolon İçeriği
        self._build_left_pane()

        # Sağ Kolon İçeriği
        self._build_right_pane()

    def _build_header_card(self):
        self.header_card = ctk.CTkFrame(
            self.main_scroll,
            fg_color="#FFFFFF",
            corner_radius=theme.GRID_CELL_RADIUS,
            border_width=theme.GRID_BORDER_WIDTH,
            border_color=theme.GRID_BORDER_COLOR,
            overwrite_preferred_drawing_method="circle_shapes"
        )
        self.header_card.pack(fill="x", pady=(0, 12))

        top_row = ctk.CTkFrame(self.header_card, fg_color="transparent")
        top_row.pack(fill="x", padx=16, pady=(12, 8))

        # Sol: Sayfa Başlığı ve Açıklaması
        title_box = ctk.CTkFrame(top_row, fg_color="transparent")
        title_box.pack(side="left", fill="y")

        self.lbl_title = ctk.CTkLabel(
            title_box,
            text="☀️ Günün Özeti ve Canlı Nöbet Panosu",
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=theme.FONT_SIZE_PAGE_TITLE, weight="bold"),
            text_color="#1D1D1F"
        )
        self.lbl_title.pack(anchor="w")

        school = self.db.get_school_info()
        school_str = f"🏫 {school.name}" if school.name else "Nöbet Yönetim Sistemi"
        self.lbl_subtitle = ctk.CTkLabel(
            title_box,
            text=f"{school_str} • Günlük Nöbet Görevlileri, Boş Sınıflar ve İkame Takibi",
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=theme.FONT_SIZE_SECONDARY),
            text_color="#86868B"
        )
        self.lbl_subtitle.pack(anchor="w", pady=(2, 0))

        # Sağ: Aksiyon Butonları (Yenile, Yazdır, WhatsApp)
        btn_box = ctk.CTkFrame(top_row, fg_color="transparent")
        btn_box.pack(side="right")

        self.btn_refresh = ctk.CTkButton(
            btn_box,
            text="🔄 Yenile",
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=theme.FONT_SIZE_UI, weight="bold"),
            fg_color="#F5F5F7",
            hover_color="#E5E5EA",
            text_color="#1D1D1F",
            height=34,
            corner_radius=theme.GRID_CELL_RADIUS,
            border_width=1,
            border_color="#D1D1D6",
            command=self.load_data
        )
        self.btn_refresh.pack(side="left", padx=4)

        self.btn_print = ctk.CTkButton(
            btn_box,
            text="🖨️ Günün Raporu (PDF)",
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=theme.FONT_SIZE_UI, weight="bold"),
            fg_color="#F5F5F7",
            hover_color="#E5E5EA",
            text_color="#1D1D1F",
            height=34,
            corner_radius=theme.GRID_CELL_RADIUS,
            border_width=1,
            border_color="#D1D1D6",
            command=self.export_daily_summary_pdf
        )
        self.btn_print.pack(side="left", padx=4)

        self.btn_whatsapp = ctk.CTkButton(
            btn_box,
            text="💬 Nöbetçilere WhatsApp",
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=theme.FONT_SIZE_UI, weight="bold"),
            fg_color="#25D366",
            hover_color="#1EBE5D",
            text_color="#FFFFFF",
            height=34,
            corner_radius=theme.GRID_CELL_RADIUS,
            border_width=0,
            command=self._send_bulk_whatsapp
        )
        self.btn_whatsapp.pack(side="left", padx=4)

        # Alt: Tarih Gezinme Çubuğu (Günün Seçimi)
        nav_row = ctk.CTkFrame(self.header_card, fg_color="#F8FAFC", corner_radius=6, height=44)
        nav_row.pack(fill="x", padx=16, pady=(0, 12))
        nav_row.pack_propagate(False)

        self.btn_prev_day = ctk.CTkButton(
            nav_row,
            text="◀ Önceki Gün",
            width=100,
            height=30,
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=12, weight="bold"),
            fg_color="#FFFFFF",
            hover_color="#F1F5F9",
            text_color="#334155",
            border_width=1,
            border_color="#E2E8F0",
            corner_radius=6,
            command=self._prev_day
        )
        self.btn_prev_day.pack(side="left", padx=8, pady=7)

        # Tarih Bilgisi ve Rozet
        self.date_display_box = ctk.CTkFrame(nav_row, fg_color="transparent")
        self.date_display_box.pack(side="left", expand=True)

        self.lbl_date_text = ctk.CTkLabel(
            self.date_display_box,
            text="",
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=14, weight="bold"),
            text_color="#0F172A"
        )
        self.lbl_date_text.pack(side="left", padx=(0, 8))

        self.badge_today = ctk.CTkFrame(self.date_display_box, fg_color="#10B981", corner_radius=4, height=20)
        self.lbl_today_text = ctk.CTkLabel(
            self.badge_today,
            text="★ BUGÜN",
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=10, weight="bold"),
            text_color="#FFFFFF"
        )
        self.lbl_today_text.pack(padx=6, pady=1)

        self.btn_next_day = ctk.CTkButton(
            nav_row,
            text="Sonraki Gün ▶",
            width=100,
            height=30,
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=12, weight="bold"),
            fg_color="#FFFFFF",
            hover_color="#F1F5F9",
            text_color="#334155",
            border_width=1,
            border_color="#E2E8F0",
            corner_radius=6,
            command=self._next_day
        )
        self.btn_next_day.pack(side="right", padx=8, pady=7)

        self.btn_today_jump = ctk.CTkButton(
            nav_row,
            text="Bugün'e Git",
            width=85,
            height=30,
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=12, weight="bold"),
            fg_color="#007AFF",
            hover_color="#0062D2",
            text_color="#FFFFFF",
            corner_radius=6,
            command=self._jump_today
        )
        self.btn_today_jump.pack(side="right", padx=(0, 4), pady=7)

    def _build_kpi_cards(self):
        kpi_row = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        kpi_row.pack(fill="x", pady=(0, 12))

        # 4 Sütunlu Grid
        for i in range(4):
            kpi_row.columnconfigure(i, weight=1, uniform="kpi_col")

        # 1. Günün Nöbetçileri
        self.card_kpi_duties = self._create_kpi_box(
            kpi_row, col=0,
            icon="🛡️", title="GÜNÜN NÖBETÇİLERİ",
            val_text="0 Bölge", sub_text="Tüm noktalar aktif",
            accent_color="#10B981"
        )

        # 2. Şube ve Ders Yükü
        self.card_kpi_lessons = self._create_kpi_box(
            kpi_row, col=1,
            icon="🏫", title="GÜNLÜK DERS YÜKÜ",
            val_text="0 Şube", sub_text="Toplam 0 saat ders",
            accent_color="#007AFF"
        )

        # 3. Boş Kalan Sınıflar
        self.card_kpi_empty = self._create_kpi_box(
            kpi_row, col=2,
            icon="⚠️", title="BOŞ KALAN SINIFLAR",
            val_text="0 Boş Sınıf", sub_text="İkame bekleyen ders",
            accent_color="#FF9500"
        )

        # 4. Müsait Öğretmenler
        self.card_kpi_free = self._create_kpi_box(
            kpi_row, col=3,
            icon="🟢", title="MÜSAİT ÖĞRETMENLER",
            val_text="0 Öğretmen", sub_text="Boş saatlerinde göreve hazır",
            accent_color="#5856D6"
        )

    def _create_kpi_box(self, parent, col: int, icon: str, title: str, val_text: str, sub_text: str, accent_color: str):
        card = ctk.CTkFrame(
            parent,
            fg_color="#FFFFFF",
            corner_radius=theme.GRID_CELL_RADIUS,
            border_width=theme.GRID_BORDER_WIDTH,
            border_color=theme.GRID_BORDER_COLOR,
            overwrite_preferred_drawing_method="circle_shapes"
        )
        card.grid(row=0, column=col, sticky="nsew", padx=4, pady=2)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14, pady=10)

        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")

        lbl_icon = ctk.CTkLabel(top, text=icon, font=ctk.CTkFont(family=theme.FONT_FAMILY, size=16))
        lbl_icon.pack(side="left")

        lbl_t = ctk.CTkLabel(
            top,
            text=title,
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=11, weight="bold"),
            text_color="#86868B"
        )
        lbl_t.pack(side="left", padx=6)

        lbl_val = ctk.CTkLabel(
            inner,
            text=val_text,
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=18, weight="bold"),
            text_color=accent_color
        )
        lbl_val.pack(anchor="w", pady=(4, 0))

        lbl_sub = ctk.CTkLabel(
            inner,
            text=sub_text,
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=11),
            text_color="#86868B"
        )
        lbl_sub.pack(anchor="w", pady=(1, 0))

        return {"card": card, "val": lbl_val, "sub": lbl_sub}

    def _build_left_pane(self):
        # Sol Panel Başlığı
        header = ctk.CTkFrame(self.left_col, fg_color="#F8FAFC", corner_radius=6)
        header.pack(fill="x", padx=10, pady=10)

        lbl = ctk.CTkLabel(
            header,
            text="🛡️ Bugünün Nöbet Yerleri ve Görevlileri",
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=14, weight="bold"),
            text_color="#0F172A"
        )
        lbl.pack(side="left", padx=10, pady=8)

        self.lbl_duty_count_badge = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=11, weight="bold"),
            text_color="#10B981"
        )
        self.lbl_duty_count_badge.pack(side="right", padx=10)

        # Nöbet Kartları Listesi (Scrollable)
        self.duties_scroll = ctk.CTkScrollableFrame(
            self.left_col,
            fg_color="transparent",
            corner_radius=0
        )
        self.duties_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _build_right_pane(self):
        # Sağ Panel Başlığı ve Sekmeleri
        header = ctk.CTkFrame(self.right_col, fg_color="#F8FAFC", corner_radius=6)
        header.pack(fill="x", padx=10, pady=10)

        lbl = ctk.CTkLabel(
            header,
            text="🏫 Boş Sınıf & İkame Takip Merkezi",
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=14, weight="bold"),
            text_color="#0F172A"
        )
        lbl.pack(side="left", padx=10, pady=8)

        # 3'lü Sekme Butonları (Segmented)
        tab_bar = ctk.CTkFrame(self.right_col, fg_color="#F1F5F9", corner_radius=6, height=34)
        tab_bar.pack(fill="x", padx=10, pady=(0, 10))
        tab_bar.pack_propagate(False)

        self.tab_btn_empty = ctk.CTkButton(
            tab_bar,
            text="⚠️ Boş Kalan Sınıflar",
            height=28,
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=11, weight="bold"),
            fg_color="#FFFFFF",
            hover_color="#E2E8F0",
            text_color="#0F172A",
            corner_radius=5,
            command=lambda: self._set_right_tab("empty_classes")
        )
        self.tab_btn_empty.pack(side="left", padx=3, pady=3, fill="x", expand=True)

        self.tab_btn_free = ctk.CTkButton(
            tab_bar,
            text="🕒 Saatlik Müsait Öğretmenler",
            height=28,
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=11, weight="normal"),
            fg_color="transparent",
            hover_color="#E2E8F0",
            text_color="#64748B",
            corner_radius=5,
            command=lambda: self._set_right_tab("free_teachers")
        )
        self.tab_btn_free.pack(side="left", padx=3, pady=3, fill="x", expand=True)

        self.tab_btn_matrix = ctk.CTkButton(
            tab_bar,
            text="📊 Sınıf Ders Dağılımı",
            height=28,
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=11, weight="normal"),
            fg_color="transparent",
            hover_color="#E2E8F0",
            text_color="#64748B",
            corner_radius=5,
            command=lambda: self._set_right_tab("class_matrix")
        )
        self.tab_btn_matrix.pack(side="left", padx=3, pady=3, fill="x", expand=True)

        # Sekme İçerik Alanı
        self.right_tab_container = ctk.CTkScrollableFrame(
            self.right_col,
            fg_color="transparent",
            corner_radius=0
        )
        self.right_tab_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _set_right_tab(self, tab_key: str):
        self.current_tab = tab_key
        # Sekme buton stillerini güncelle
        tabs = [
            ("empty_classes", self.tab_btn_empty),
            ("free_teachers", self.tab_btn_free),
            ("class_matrix", self.tab_btn_matrix)
        ]
        for key, btn in tabs:
            if key == tab_key:
                btn.configure(
                    fg_color="#FFFFFF",
                    text_color="#0F172A",
                    font=ctk.CTkFont(family=theme.FONT_FAMILY, size=11, weight="bold")
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color="#64748B",
                    font=ctk.CTkFont(family=theme.FONT_FAMILY, size=11, weight="normal")
                )
        self._render_right_tab()

    def _prev_day(self):
        self.current_date -= datetime.timedelta(days=1)
        if self.current_date.weekday() == 6:  # Pazar -> Cuma
            self.current_date -= datetime.timedelta(days=2)
        elif self.current_date.weekday() == 5:
            self.current_date -= datetime.timedelta(days=1)
        self.load_data()

    def _next_day(self):
        self.current_date += datetime.timedelta(days=1)
        if self.current_date.weekday() == 5:  # Cumartesi -> Pazartesi
            self.current_date += datetime.timedelta(days=2)
        elif self.current_date.weekday() == 6:
            self.current_date += datetime.timedelta(days=1)
        self.load_data()

    def _jump_today(self):
        self.current_date = datetime.date.today()
        self.load_data()

    def load_data(self):
        """Seçili günün nöbet, ders, sınıf ve ikame verilerini yükler ve arayüzü günceller."""
        dt = self.current_date
        day_idx = dt.weekday()
        day_name = TURKISH_DAYS[day_idx]
        month_name = TURKISH_MONTHS[dt.month] if 1 <= dt.month <= 12 else ""
        date_str = dt.isoformat()
        is_today = (dt == datetime.date.today())

        # Tarih Başlığını Güncelle
        self.lbl_date_text.configure(text=f"📅 {dt.day} {month_name} {dt.year}, {day_name}")
        if is_today:
            self.badge_today.pack(side="left", padx=(0, 8))
        else:
            self.badge_today.pack_forget()

        # Hafta başlangıcı (Pazartesi)
        week_start = (dt - datetime.timedelta(days=day_idx)).isoformat()

        # 1. Nöbet Verileri
        duty_list = self.sub_service.get_day_duty_teachers(week_start, day_name)
        all_locations = self.db.get_locations()

        # 2. Ders Saatleri
        self.period_times = self.db.get_period_times() if hasattr(self.db, "get_period_times") else PERIOD_TIMES

        # 3. İkame ve Boş Sınıf Verileri
        self.substitutions = self.db.get_substitutions_for_date(date_str)

        # 4. Tüm Öğretmenler ve Ders Programları
        all_teachers = self.db.get_teachers()
        self.teachers_map = {t.id: t for t in all_teachers}

        all_lessons = self.db.get_all_teacher_lessons()
        self.day_lessons = [l for l in all_lessons if l.day_name.lower() == day_name.lower() and not l.is_free]

        # 5. Müsait Öğretmenler Havuzu (Her periyot için boş olanlar)
        self.free_teachers_by_period: Dict[int, List[Teacher]] = {}
        for p in range(1, 8):
            free_t_list = []
            for t in all_teachers:
                free_ps = self.sub_service.get_teacher_free_periods(t.id, day_name, is_duty=False)
                if p in free_ps:
                    free_t_list.append(t)
            self.free_teachers_by_period[p] = free_t_list

        # KPI Güncellemeleri
        total_loc_capacity = sum(loc.capacity for loc in all_locations)
        active_duty_count = len([d for d in duty_list if d.get("teacher")])
        self.card_kpi_duties["val"].configure(text=f"{active_duty_count} / {total_loc_capacity} Bölge")
        if active_duty_count >= total_loc_capacity:
            self.card_kpi_duties["sub"].configure(text="Tüm nöbet noktaları görevde ✓")
            self.card_kpi_duties["val"].configure(text_color="#10B981")
        else:
            eksik = total_loc_capacity - active_duty_count
            self.card_kpi_duties["sub"].configure(text=f"🚨 {eksik} nöbet noktası boşta!")
            self.card_kpi_duties["val"].configure(text_color="#FF3B30")

        distinct_classes = sorted(list(set(l.class_name for l in self.day_lessons if l.class_name)))
        self.card_kpi_lessons["val"].configure(text=f"{len(distinct_classes)} Şube")
        self.card_kpi_lessons["sub"].configure(text=f"Toplam {len(self.day_lessons)} saat ders")

        # Boş Kalan Dersler / İkame bekleyenler
        unassigned_subs = [s for s in self.substitutions if not s.duty_teacher_id]
        if unassigned_subs:
            self.card_kpi_empty["val"].configure(text=f"{len(unassigned_subs)} Boş Ders", text_color="#FF3B30")
            self.card_kpi_empty["sub"].configure(text="🚨 İkame nöbetçi atanması bekliyor")
        else:
            self.card_kpi_empty["val"].configure(text="0 Boş Sınıf", text_color="#10B981")
            self.card_kpi_empty["sub"].configure(text="Tüm sınıflarda eğitim devam ediyor ✓")

        # Gün boyunca en az 1 saat boş dersi olan öğretmen sayısı
        teachers_with_free_hour = set()
        for p_list in self.free_teachers_by_period.values():
            for t in p_list:
                teachers_with_free_hour.add(t.id)
        self.card_kpi_free["val"].configure(text=f"{len(teachers_with_free_hour)} Müsait")
        self.card_kpi_free["sub"].configure(text="Gerektiğinde ikameye hazır öğretmen")

        # Sol Paneli Render Et (Nöbetçiler)
        self._render_duties_list(all_locations, duty_list, day_name)

        # Sağ Paneli Render Et
        self._render_right_tab()

    def _render_duties_list(self, all_locations: List[Location], duty_list: List[Dict[str, Any]], day_name: str):
        for w in self.duties_scroll.winfo_children():
            w.destroy()

        self.lbl_duty_count_badge.configure(text=f"{len(duty_list)} Nöbetçi Görevde")

        # Nöbet atamalarını lokasyon ve slot bazında eşle
        duty_by_loc_slot: Dict[Tuple[str, int], Dict[str, Any]] = {}
        for d in duty_list:
            loc = d.get("location")
            assign = d.get("assignment")
            if loc and assign:
                duty_by_loc_slot[(loc.id, assign.slot_index)] = d

        for loc in all_locations:
            for slot in range(loc.capacity):
                d_info = duty_by_loc_slot.get((loc.id, slot))
                teacher: Optional[Teacher] = d_info.get("teacher") if d_info else None
                assign: Optional[Assignment] = d_info.get("assignment") if d_info else None
                free_periods: List[int] = d_info.get("free_periods", []) if d_info else []

                slot_title = loc.name
                if loc.capacity > 1:
                    slot_title += f" ({slot + 1}. Görevli)"

                # İkon seçimi
                l_lower = loc.name.lower()
                icon = "🌳" if "bahçe" in l_lower or "bahce" in l_lower else "🏢"

                # Kart
                card_bg = "#FFFFFF"
                border_c = "#E2E8F0"
                if not teacher:
                    card_bg = "#FEF2F2"
                    border_c = "#FCA5A5"
                elif assign and assign.fixed:
                    card_bg = "#FFF8ED"
                    border_c = "#FF9500"

                card = ctk.CTkFrame(
                    self.duties_scroll,
                    fg_color=card_bg,
                    corner_radius=theme.GRID_CELL_RADIUS,
                    border_width=theme.GRID_BORDER_WIDTH,
                    border_color=border_c,
                    overwrite_preferred_drawing_method="circle_shapes"
                )
                card.pack(fill="x", pady=4)

                card_inner = ctk.CTkFrame(card, fg_color="transparent")
                card_inner.pack(fill="both", expand=True, padx=12, pady=10)

                # Üst Satır: Lokasyon Başlığı ve Rozet
                top_line = ctk.CTkFrame(card_inner, fg_color="transparent")
                top_line.pack(fill="x")

                lbl_loc = ctk.CTkLabel(
                    top_line,
                    text=f"{icon} {slot_title}",
                    font=ctk.CTkFont(family=theme.FONT_FAMILY, size=13, weight="bold"),
                    text_color="#0F172A"
                )
                lbl_loc.pack(side="left")

                # Rozet
                if not teacher:
                    b_frame = ctk.CTkFrame(top_line, fg_color="#FEE2E2", corner_radius=4)
                    b_frame.pack(side="right")
                    ctk.CTkLabel(b_frame, text="🚨 NÖBETÇİ ATANMAMIŞ", font=ctk.CTkFont(family=theme.FONT_FAMILY, size=10, weight="bold"), text_color="#DC2626").pack(padx=6, pady=1)
                elif assign and assign.fixed:
                    b_frame = ctk.CTkFrame(top_line, fg_color="#FEF3C7", corner_radius=4)
                    b_frame.pack(side="right")
                    ctk.CTkLabel(b_frame, text="🔒 SABİT NÖBET", font=ctk.CTkFont(family=theme.FONT_FAMILY, size=10, weight="bold"), text_color="#B45309").pack(padx=6, pady=1)
                else:
                    b_frame = ctk.CTkFrame(top_line, fg_color="#ECFDF5", corner_radius=4)
                    b_frame.pack(side="right")
                    ctk.CTkLabel(b_frame, text="🟢 AKTİF GÖREVDE", font=ctk.CTkFont(family=theme.FONT_FAMILY, size=10, weight="bold"), text_color="#059669").pack(padx=6, pady=1)

                # Orta Satır: Öğretmen Bilgisi
                if teacher:
                    name_disp = to_title_case(teacher.name)
                    branch_disp = teacher.branch or "Genel"

                    lbl_name = ctk.CTkLabel(
                        card_inner,
                        text=f"👤 {name_disp} ({branch_disp})",
                        font=ctk.CTkFont(family=theme.FONT_FAMILY, size=13, weight="bold"),
                        text_color="#1D1D1F"
                    )
                    lbl_name.pack(anchor="w", pady=(4, 0))

                    # Ders Programı Durumu
                    if free_periods:
                        free_str = ", ".join(map(str, free_periods))
                        sched_desc = f"🕒 Boş Dersleri: {free_str}. Dersler • Diğer saatlerde sınıfta"
                    else:
                        sched_desc = "🕒 Tüm ders saatleri dolu • Nöbet aralarda yürütülüyor"

                    lbl_sched = ctk.CTkLabel(
                        card_inner,
                        text=sched_desc,
                        font=ctk.CTkFont(family=theme.FONT_FAMILY, size=11),
                        text_color="#64748B"
                    )
                    lbl_sched.pack(anchor="w", pady=(2, 0))

                    # Alt Hızlı Aksiyon Butonları
                    action_line = ctk.CTkFrame(card_inner, fg_color="transparent")
                    action_line.pack(fill="x", pady=(8, 0))

                    btn_wa = ctk.CTkButton(
                        action_line,
                        text="💬 WhatsApp Mesajı",
                        height=26,
                        font=ctk.CTkFont(family=theme.FONT_FAMILY, size=10, weight="bold"),
                        fg_color="#EBF5FF",
                        hover_color="#DBEAFE",
                        text_color="#2563EB",
                        corner_radius=4,
                        command=lambda t=teacher: self._send_single_whatsapp(t)
                    )
                    btn_wa.pack(side="left", padx=(0, 6))

                    btn_info = ctk.CTkButton(
                        action_line,
                        text="📋 Günlük Ders Programı",
                        height=26,
                        font=ctk.CTkFont(family=theme.FONT_FAMILY, size=10, weight="bold"),
                        fg_color="#F1F5F9",
                        hover_color="#E2E8F0",
                        text_color="#475569",
                        corner_radius=4,
                        command=lambda t=teacher: self._show_teacher_schedule_dialog(t, day_name)
                    )
                    btn_info.pack(side="left")
                else:
                    lbl_empty = ctk.CTkLabel(
                        card_inner,
                        text="Bu nöbet yerine henüz bir öğretmen atanmamış.",
                        font=ctk.CTkFont(family=theme.FONT_FAMILY, size=11, slant="italic"),
                        text_color="#DC2626"
                    )
                    lbl_empty.pack(anchor="w", pady=(4, 0))

    def _render_right_tab(self):
        for w in self.right_tab_container.winfo_children():
            w.destroy()

        if self.current_tab == "empty_classes":
            self._render_tab_empty_classes()
        elif self.current_tab == "free_teachers":
            self._render_tab_free_teachers()
        elif self.current_tab == "class_matrix":
            self._render_tab_class_matrix()

    def _render_tab_empty_classes(self):
        """1. Sekme: Boş Kalan ve İkame Bekleyen Sınıflar"""
        # Kayıtlı ikameleri ve boş geçen dersleri listele
        if not self.substitutions:
            # Boş ders yok: Tertemiz ferah onay kutusu
            box = ctk.CTkFrame(
                self.right_tab_container,
                fg_color="#F0FDF4",
                corner_radius=8,
                border_width=1,
                border_color="#BBF7D0"
            )
            box.pack(fill="x", pady=10)

            inner = ctk.CTkFrame(box, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=16, pady=16)

            ctk.CTkLabel(
                inner,
                text="🎉 Harika! Bugün Hiçbir Sınıf Boşta Değil",
                font=ctk.CTkFont(family=theme.FONT_FAMILY, size=14, weight="bold"),
                text_color="#15803D"
            ) .pack(anchor="w")

            ctk.CTkLabel(
                inner,
                text="Bugün gelmeyen veya öğretmensiz boş geçen herhangi bir ders bulunmuyor.\n"
                     "Tüm sınıflar programdaki asıl öğretmenleri ile eğitimine devam ediyor.",
                font=ctk.CTkFont(family=theme.FONT_FAMILY, size=12),
                text_color="#166534",
                justify="left"
            ).pack(anchor="w", pady=(4, 8))

            if self.on_open_substitution:
                ctk.CTkButton(
                    inner,
                    text="🔄 Devamsızlık / İkame Girişi Yap",
                    height=30,
                    font=ctk.CTkFont(family=theme.FONT_FAMILY, size=11, weight="bold"),
                    fg_color="#15803D",
                    hover_color="#166534",
                    text_color="#FFFFFF",
                    corner_radius=6,
                    command=lambda: self.on_open_substitution(date_str=self.current_date.strftime("%Y-%m-%d"))
                ).pack(anchor="w")
            return

        # İkameler listesi
        for sub in self.substitutions:
            time_str = self.period_times.get(sub.period, f"{sub.period}. Ders")
            is_assigned = bool(sub.duty_teacher_id)

            card_bg = "#FFFFFF" if is_assigned else "#FEF2F2"
            border_c = "#BBF7D0" if is_assigned else "#FCA5A5"

            card = ctk.CTkFrame(
                self.right_tab_container,
                fg_color=card_bg,
                corner_radius=6,
                border_width=1,
                border_color=border_c
            )
            card.pack(fill="x", pady=4)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=12, pady=10)

            top = ctk.CTkFrame(inner, fg_color="transparent")
            top.pack(fill="x")

            badge_p = ctk.CTkFrame(top, fg_color="#F1F5F9", corner_radius=4)
            badge_p.pack(side="left")
            ctk.CTkLabel(
                badge_p,
                text=f"{sub.period}. Ders ({time_str})",
                font=ctk.CTkFont(family=theme.FONT_FAMILY, size=11, weight="bold"),
                text_color="#0F172A"
            ).pack(padx=6, pady=1)

            lbl_cls = ctk.CTkLabel(
                top,
                text=f"📍 Sınıf: {sub.class_name} • {sub.subject_code or 'Ders'}",
                font=ctk.CTkFont(family=theme.FONT_FAMILY, size=12, weight="bold"),
                text_color="#1D1D1F"
            )
            lbl_cls.pack(side="left", padx=8)

            # Durum rozeti
            if is_assigned:
                b_st = ctk.CTkFrame(top, fg_color="#DCFCE7", corner_radius=4)
                b_st.pack(side="right")
                duty_t = self.teachers_map.get(sub.duty_teacher_id)
                duty_name = to_title_case(duty_t.name) if duty_t else "Nöbetçi"
                ctk.CTkLabel(
                    b_st,
                    text=f"✓ İKAME: {duty_name}",
                    font=ctk.CTkFont(family=theme.FONT_FAMILY, size=10, weight="bold"),
                    text_color="#15803D"
                ).pack(padx=6, pady=1)
            else:
                b_st = ctk.CTkFrame(top, fg_color="#FEE2E2", corner_radius=4)
                b_st.pack(side="right")
                ctk.CTkLabel(
                    b_st,
                    text="🚨 BOŞTA - İKAME BEKLİYOR",
                    font=ctk.CTkFont(family=theme.FONT_FAMILY, size=10, weight="bold"),
                    text_color="#DC2626"
                ).pack(padx=6, pady=1)

            # Asıl Öğretmen
            absent_t = self.teachers_map.get(sub.absent_teacher_id)
            abs_name = to_title_case(absent_t.name) if absent_t else "Öğretmen"
            lbl_sub_info = ctk.CTkLabel(
                inner,
                text=f"Asıl Öğretmen: {abs_name} (Gelmeyen / İzinli)",
                font=ctk.CTkFont(family=theme.FONT_FAMILY, size=11),
                text_color="#64748B"
            )
            lbl_sub_info.pack(anchor="w", pady=(4, 0))

    def _render_tab_free_teachers(self):
        """2. Sekme: Saatlik Müsait Öğretmenler Havuzu"""
        for p in range(1, 8):
            time_str = self.period_times.get(p, f"{p}. Ders")
            free_list = self.free_teachers_by_period.get(p, [])

            row = ctk.CTkFrame(
                self.right_tab_container,
                fg_color="#FFFFFF",
                corner_radius=6,
                border_width=1,
                border_color="#E2E8F0"
            )
            row.pack(fill="x", pady=4)

            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=12, pady=8)

            top = ctk.CTkFrame(inner, fg_color="transparent")
            top.pack(fill="x")

            lbl_p = ctk.CTkLabel(
                top,
                text=f"{p}. Ders ({time_str})",
                font=ctk.CTkFont(family=theme.FONT_FAMILY, size=12, weight="bold"),
                text_color="#0F172A"
            )
            lbl_p.pack(side="left")

            count_color = "#15803D" if free_list else "#94A3B8"
            lbl_cnt = ctk.CTkLabel(
                top,
                text=f"{len(free_list)} Öğretmen Müsait",
                font=ctk.CTkFont(family=theme.FONT_FAMILY, size=11, weight="bold"),
                text_color=count_color
            )
            lbl_cnt.pack(side="right")

            # Öğretmen rozetleri
            if free_list:
                chip_box = ctk.CTkFrame(inner, fg_color="transparent")
                chip_box.pack(fill="x", pady=(6, 0))

                for t in free_list:
                    chip = ctk.CTkFrame(chip_box, fg_color="#F8FAFC", border_width=1, border_color="#CBD5E1", corner_radius=4)
                    chip.pack(side="left", padx=3, pady=2)

                    b_text = f"👤 {to_title_case(t.name)} ({t.branch or 'Genel'})"
                    ctk.CTkLabel(
                        chip,
                        text=b_text,
                        font=ctk.CTkFont(family=theme.FONT_FAMILY, size=10),
                        text_color="#334155"
                    ).pack(padx=6, pady=2)
            else:
                lbl_none = ctk.CTkLabel(
                    inner,
                    text="Bu saatte tüm öğretmenlerin sınıf dersi bulunmaktadır.",
                    font=ctk.CTkFont(family=theme.FONT_FAMILY, size=10, slant="italic"),
                    text_color="#94A3B8"
                )
                lbl_none.pack(anchor="w", pady=(2, 0))

    def _render_tab_class_matrix(self):
        """3. Sekme: Sınıfların Günlük Ders Dağılım Matrisi"""
        distinct_classes = sorted(list(set(l.class_name for l in self.day_lessons if l.class_name)))
        if not distinct_classes:
            ctk.CTkLabel(
                self.right_tab_container,
                text="Görüntülenecek sınıf ders programı bulunamadı.",
                font=ctk.CTkFont(family=theme.FONT_FAMILY, size=12)
            ).pack(pady=20)
            return

        # Sınıfları periyotlara göre eşle: (class_name, period) -> TeacherLesson
        cls_period_map: Dict[Tuple[str, int], TeacherLesson] = {}
        for l in self.day_lessons:
            cls_period_map[(l.class_name, l.period)] = l

        table_box = ctk.CTkFrame(self.right_tab_container, fg_color="transparent")
        table_box.pack(fill="both", expand=True)

        # Başlık Satırı
        hdr_row = ctk.CTkFrame(table_box, fg_color="#1E293B", corner_radius=4, height=30)
        hdr_row.pack(fill="x", pady=(0, 2))
        hdr_row.pack_propagate(False)

        ctk.CTkLabel(hdr_row, text="Şube / Sınıf", font=ctk.CTkFont(family=theme.FONT_FAMILY, size=11, weight="bold"), text_color="#FFFFFF", width=80).pack(side="left", padx=4)
        for p in range(1, 8):
            ctk.CTkLabel(hdr_row, text=f"{p}. Ders", font=ctk.CTkFont(family=theme.FONT_FAMILY, size=11, weight="bold"), text_color="#E2E8F0").pack(side="left", fill="x", expand=True)

        for c_idx, c_name in enumerate(distinct_classes):
            row_bg = "#FFFFFF" if c_idx % 2 == 0 else "#F8FAFC"
            r_frame = ctk.CTkFrame(table_box, fg_color=row_bg, corner_radius=2, height=32)
            r_frame.pack(fill="x", pady=1)
            r_frame.pack_propagate(False)

            ctk.CTkLabel(r_frame, text=c_name, font=ctk.CTkFont(family=theme.FONT_FAMILY, size=11, weight="bold"), text_color="#0F172A", width=80).pack(side="left", padx=4)

            for p in range(1, 8):
                lesson = cls_period_map.get((c_name, p))
                if lesson:
                    t_obj = self.teachers_map.get(lesson.teacher_id)
                    t_short = to_title_case(t_obj.name.split()[0]) if t_obj else "Öğr."
                    cell_text = f"{lesson.subject_code or 'Ders'} ({t_short})"
                    txt_c = "#334155"
                else:
                    cell_text = "— Boş —"
                    txt_c = "#94A3B8"

                ctk.CTkLabel(r_frame, text=cell_text, font=ctk.CTkFont(family=theme.FONT_FAMILY, size=10), text_color=txt_c).pack(side="left", fill="x", expand=True)

    def _show_teacher_schedule_dialog(self, teacher: Teacher, day_name: str):
        """Öğretmenin günlük 7 saatlik ders çizelgesini popover olarak açar."""
        lessons = self.sub_service.get_teacher_schedule(teacher.id, day_name)
        lessons_by_period = {l.period: l for l in lessons if not l.is_free}

        top = tk.Toplevel(self)
        top.title(f"Ders Programı - {to_title_case(teacher.name)}")
        top.geometry("420x360")
        top.configure(bg="#FFFFFF")
        top.transient(self)
        top.grab_set()

        head = tk.Frame(top, bg="#0F172A", padx=14, pady=10)
        head.pack(fill="x")
        tk.Label(head, text=f"👤 {to_title_case(teacher.name)}", font=(theme.FONT_FAMILY, 12, "bold"), fg="#FFFFFF", bg="#0F172A").pack(anchor="w")
        tk.Label(head, text=f"Branş: {teacher.branch or 'Genel'} • {day_name} Günü Ders Çizelgesi", font=(theme.FONT_FAMILY, 9), fg="#94A3B8", bg="#0F172A").pack(anchor="w", pady=(2, 0))

        content = tk.Frame(top, bg="#FFFFFF", padx=14, pady=10)
        content.pack(fill="both", expand=True)

        for p in range(1, 8):
            time_str = self.period_times.get(p, "")
            l = lessons_by_period.get(p)
            row = tk.Frame(content, bg="#F8FAFC" if p % 2 == 0 else "#FFFFFF", padx=8, pady=4, highlightthickness=1, highlightbackground="#E2E8F0")
            row.pack(fill="x", pady=2)

            tk.Label(row, text=f"{p}. Ders ({time_str}):", font=(theme.FONT_FAMILY, 9, "bold"), fg="#334155", bg=row["bg"], width=18, anchor="w").pack(side="left")

            if l:
                c_text = f"📍 {l.class_name} ({l.subject_code or 'Ders'})"
                tk.Label(row, text=c_text, font=(theme.FONT_FAMILY, 9, "bold"), fg="#1E293B", bg=row["bg"]).pack(side="left")
            else:
                tk.Label(row, text="🟢 BOŞ DERS (Nöbet Başında / Müsait)", font=(theme.FONT_FAMILY, 9, "italic"), fg="#15803D", bg=row["bg"]).pack(side="left")

        tk.Button(top, text="Kapat", command=top.destroy, bg="#007AFF", fg="#FFFFFF", font=(theme.FONT_FAMILY, 10, "bold"), relief="flat", padx=16, pady=4).pack(pady=8)

    def _send_single_whatsapp(self, teacher: Teacher):
        if self.on_open_whatsapp:
            self.on_open_whatsapp(teacher=teacher, week_start=None)
        else:
            messagebox.showinfo("WhatsApp", f"{to_title_case(teacher.name)} için WhatsApp bildirim servisi açılıyor...")

    def _send_bulk_whatsapp(self):
        if self.on_open_whatsapp:
            self.on_open_whatsapp(teacher=None, week_start=None)
        else:
            messagebox.showinfo("WhatsApp", "Günün tüm nöbetçilerine toplu WhatsApp gönderim servisi açılıyor...")

    def export_daily_summary_pdf(self):
        """Günün Özet Raporunu şık bir PDF dosyası olarak dışa aktarır."""
        from tkinter import filedialog
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        import logic.export_service as es
        from logic.matching_service import tr_upper

        has_custom = es._register_pdf_fonts()
        font_family = "CustomArial" if (has_custom or es._FONT_REGISTERED) else "Helvetica"
        font_bold = "CustomArial-Bold" if (has_custom or es._FONT_REGISTERED) else "Helvetica-Bold"

        dt = self.current_date
        day_idx = dt.weekday()
        day_name = TURKISH_DAYS[day_idx]
        month_name = TURKISH_MONTHS[dt.month] if 1 <= dt.month <= 12 else ""
        date_display = f"{dt.day}_{month_name}_{dt.year}_{day_name}"

        default_filename = f"Gunun_Ozeti_{date_display}.pdf"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Dosyası", "*.pdf")],
            initialfile=default_filename,
            title="Günün Özet Raporunu PDF Olarak Kaydet"
        )
        if not file_path:
            return

        try:
            doc = SimpleDocTemplate(
                file_path,
                pagesize=A4,
                leftMargin=36,
                rightMargin=36,
                topMargin=36,
                bottomMargin=36
            )

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'TitleStyle',
                parent=styles['Heading1'],
                fontName=font_bold,
                fontSize=14,
                leading=18,
                alignment=1,
                textColor=colors.HexColor("#0F172A")
            )
            subtitle_style = ParagraphStyle(
                'SubtitleStyle',
                parent=styles['Normal'],
                fontName=font_family,
                fontSize=10,
                leading=14,
                alignment=1,
                textColor=colors.HexColor("#64748B")
            )
            h2_style = ParagraphStyle(
                'H2Style',
                parent=styles['Heading2'],
                fontName=font_bold,
                fontSize=11,
                leading=15,
                textColor=colors.HexColor("#1E293B")
            )
            cell_bold = ParagraphStyle('CellB', fontName=font_bold, fontSize=8, leading=10, textColor=colors.HexColor("#0F172A"))
            cell_norm = ParagraphStyle('CellN', fontName=font_family, fontSize=8, leading=10, textColor=colors.HexColor("#334155"))

            elements = []
            school = self.db.get_school_info()

            school_title = tr_upper(school.name) if school.name else "MİLLİ EĞİTİM BAKANLIĞI"
            elements.append(Paragraph(f"T.C.<br/>{school_title}", title_style))
            elements.append(Paragraph(f"GÜNLÜK NÖBET VE BOŞ SINIF TAKİP FORMU • {dt.day} {month_name} {dt.year}, {day_name}", subtitle_style))
            elements.append(Spacer(1, 14))

            # 1. Nöbetçiler Tablosu
            elements.append(Paragraph("1. GÜNÜN NÖBET YERLERİ VE GÖREVLİLERİ", h2_style))
            elements.append(Spacer(1, 4))

            duty_headers = [Paragraph("Nöbet Yeri", cell_bold), Paragraph("Görevli Öğretmen", cell_bold), Paragraph("Branş", cell_bold), Paragraph("Boş Ders Saatleri", cell_bold), Paragraph("İmza", cell_bold)]
            duty_rows = [duty_headers]

            week_start = (dt - datetime.timedelta(days=day_idx)).isoformat()
            duties = self.sub_service.get_day_duty_teachers(week_start, day_name)

            for d in duties:
                loc = d.get("location")
                t = d.get("teacher")
                fp = d.get("free_periods", [])
                fp_str = ", ".join(map(str, fp)) if fp else "Dolu"

                duty_rows.append([
                    Paragraph(loc.name if loc else "—", cell_bold),
                    Paragraph(to_title_case(t.name) if t else "—", cell_norm),
                    Paragraph(t.branch if t else "—", cell_norm),
                    Paragraph(fp_str, cell_norm),
                    Paragraph("........................", cell_norm)
                ])

            t_duty = Table(duty_rows, colWidths=[110, 140, 100, 100, 80])
            t_duty.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            elements.append(t_duty)
            elements.append(Spacer(1, 14))

            # 2. Boş Kalan Sınıflar ve İkame Tablosu
            elements.append(Paragraph("2. BOŞ KALAN SINIFLAR VE İKAME GÖREVLENDİRMELERİ", h2_style))
            elements.append(Spacer(1, 4))

            sub_headers = [Paragraph("Ders Saati", cell_bold), Paragraph("Sınıf", cell_bold), Paragraph("Ders", cell_bold), Paragraph("Asıl Öğretmen", cell_bold), Paragraph("İkame Görevlisi", cell_bold)]
            sub_rows = [sub_headers]

            if self.substitutions:
                for s in self.substitutions:
                    time_s = self.period_times.get(s.period, "")
                    abs_t = self.teachers_map.get(s.absent_teacher_id)
                    duty_t = self.teachers_map.get(s.duty_teacher_id)
                    sub_rows.append([
                        Paragraph(f"{s.period}. Ders ({time_s})", cell_norm),
                        Paragraph(s.class_name, cell_bold),
                        Paragraph(s.subject_code or "Ders", cell_norm),
                        Paragraph(to_title_case(abs_t.name) if abs_t else "—", cell_norm),
                        Paragraph(to_title_case(duty_t.name) if duty_t else "🚨 İkame Bekliyor", cell_bold)
                    ])
            else:
                sub_rows.append([Paragraph("Bugün boş geçen veya ikame bekleyen sınıf bulunmamaktadır.", cell_norm), "", "", "", ""])

            t_sub = Table(sub_rows, colWidths=[110, 70, 90, 130, 130])
            t_sub.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            if not self.substitutions:
                t_sub.setStyle(TableStyle([
                    ('SPAN', (0, 1), (-1, 1)),
                    ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
                    ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#F0FDF4")),
                ]))
            elements.append(t_sub)
            elements.append(Spacer(1, 20))

            # İmza Alanı
            sign_row = [
                [Paragraph("<b>Hazırlayan</b><br/>Nöbetçi Müdür Yardımcısı<br/>........................................", cell_norm),
                 Paragraph(f"<b>Tasdik Olunur</b><br/>{school.principal_name or 'Okul Müdürü'}<br/>Okul Müdürü", cell_norm)]
            ]
            t_sign = Table(sign_row, colWidths=[260, 260])
            t_sign.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            elements.append(t_sign)

            doc.build(elements)
            messagebox.showinfo("Başarılı", f"Günün Özet Raporu PDF olarak kaydedildi:\n{file_path}", parent=self)
        except Exception as e:
            logger.error(f"Günün özeti PDF oluşturulurken hata: {e}", exc_info=True)
            messagebox.showerror("Hata", f"PDF oluşturulurken bir hata meydana geldi:\n{e}", parent=self)
