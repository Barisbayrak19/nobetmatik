"""
Canlı Nöbet Panosu (Kiosk / TV Modu)
Öğretmenler odası, okul giriş holü veya idare ekranlarına tam ekran (F11)
yansıtılarak o anki ders saati ve görevli nöbetçileri canlı gösteren pano.
"""
import datetime
from typing import Dict, Any, List, Optional

import tkinter as tk
import customtkinter as ctk

from core.database import Database
from core.models import Location, Teacher, Assignment
from logic.substitution_service import PERIOD_TIMES
from ui.theme import FONT_FAMILY

DAY_KEYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]
DAY_INDEX_MAP = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday"
}
TURKISH_DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
TURKISH_MONTHS = [
    "", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
]


class KioskView(ctk.CTkToplevel):
    """
    Öğretmenler Odası ve Okul Girişi İçin Canlı Kiosk / TV Ekranı.
    """
    def __init__(self, parent: tk.Widget, db: Database, week_start: str):
        super().__init__(parent)
        self.db = db
        self.week_start = week_start
        self.is_dark_theme = True
        self.is_fullscreen = False

        self.title("📺 Canlı Nöbet Panosu (TV Modu)")
        self.geometry("1100x720")
        self.minsize(800, 600)
        self.transient(parent)

        # Okul ve Öğretmen Verileri
        self.school = self.db.get_school_info()
        self.locations = sorted(self.db.get_locations(), key=lambda l: l.order_num)
        self.teachers = self.db.get_teachers(active_only=True)
        self.teachers_map = {t.id: t for t in self.teachers}

        # Periyot Vakit Ayarları
        self._load_period_times()

        self._build_ui()
        self._bind_keys()
        self._tick()

    def _load_period_times(self):
        # Database bell times veya varsayılan PERIOD_TIMES
        self.period_schedules = []
        try:
            custom_times = self.db.get_setting("period_times", None)
            if custom_times:
                import json
                parsed = json.loads(custom_times) if isinstance(custom_times, str) else custom_times
                if isinstance(parsed, list) and len(parsed) > 0:
                    self.period_schedules = parsed
        except Exception:
            pass

        if not self.period_schedules:
            self.period_schedules = [
                {"period": 1, "start": "08:30", "end": "09:10"},
                {"period": 2, "start": "09:25", "end": "10:05"},
                {"period": 3, "start": "10:20", "end": "11:00"},
                {"period": 4, "start": "11:15", "end": "11:55"},
                {"period": 5, "start": "12:45", "end": "13:25"},
                {"period": 6, "start": "13:40", "end": "14:20"},
                {"period": 7, "start": "14:35", "end": "15:15"},
                {"period": 8, "start": "15:30", "end": "16:10"},
            ]

    def _bind_keys(self):
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<F11>", lambda e: self.toggle_fullscreen())

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)

    def toggle_theme(self):
        self.is_dark_theme = not self.is_dark_theme
        self._apply_theme()

    def _apply_theme(self):
        bg = "#0B0F19" if self.is_dark_theme else "#F8FAFC"
        header_bg = "#111827" if self.is_dark_theme else "#FFFFFF"
        text_col = "#F9FAFB" if self.is_dark_theme else "#0F172A"

        self.configure(fg_color=bg)
        self.header_frame.configure(fg_color=header_bg)
        self.lbl_school.configure(text_color=text_col)
        self.lbl_date.configure(text_color="#9CA3AF" if self.is_dark_theme else "#64748B")
        self.lbl_clock.configure(text_color="#38BDF8" if self.is_dark_theme else "#0284C7")
        self._refresh_content()

    def _build_ui(self):
        bg = "#0B0F19" if self.is_dark_theme else "#F8FAFC"
        self.configure(fg_color=bg)

        # 1. TV Üst Başlık Barı (Canlı Saat ve Okul Bilgisi)
        self.header_frame = ctk.CTkFrame(self, fg_color="#111827", height=85, corner_radius=0)
        self.header_frame.pack(fill="x", side="top")

        # Sol: Okul Adı ve Canlı Gün
        left_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        left_box.pack(side="left", padx=24, pady=12)

        self.lbl_school = ctk.CTkLabel(
            left_box,
            text=self.school.name.upper() or "OKUL NÖBET PANOSU",
            font=(FONT_FAMILY, 18, "bold"),
            text_color="#F9FAFB",
            anchor="w"
        )
        self.lbl_school.pack(anchor="w")

        self.lbl_date = ctk.CTkLabel(
            left_box,
            text="Tarih yükleniyor...",
            font=(FONT_FAMILY, 12),
            text_color="#9CA3AF",
            anchor="w"
        )
        self.lbl_date.pack(anchor="w")

        # Orta: Aktif Ders / Teneffüs Rozeti
        self.badge_status = ctk.CTkLabel(
            self.header_frame,
            text="DERS DURUMU",
            font=(FONT_FAMILY, 14, "bold"),
            fg_color="#1E3A8A",
            text_color="#FFFFFF",
            corner_radius=12,
            padx=20,
            pady=8
        )
        self.badge_status.pack(side="left", expand=True)

        # Sağ: Büyük Dijital Saat ve Kontroller
        right_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        right_box.pack(side="right", padx=24, pady=8)

        self.lbl_clock = ctk.CTkLabel(
            right_box,
            text="00:00:00",
            font=(FONT_FAMILY, 24, "bold"),
            text_color="#38BDF8"
        )
        self.lbl_clock.pack(side="left", padx=(0, 16))

        # Tam Ekran Butonu
        btn_fs = ctk.CTkButton(
            right_box,
            text="⛶ F11",
            font=(FONT_FAMILY, 10, "bold"),
            width=55,
            height=32,
            fg_color="#374151",
            hover_color="#4B5563",
            command=self.toggle_fullscreen
        )
        btn_fs.pack(side="left", padx=(0, 6))

        # Tema Butonu
        btn_th = ctk.CTkButton(
            right_box,
            text="☀️ / 🌙",
            font=(FONT_FAMILY, 10),
            width=50,
            height=32,
            fg_color="#374151",
            hover_color="#4B5563",
            command=self.toggle_theme
        )
        btn_th.pack(side="left", padx=(0, 6))

        # Kapat Butonu
        btn_close = ctk.CTkButton(
            right_box,
            text="✕",
            font=(FONT_FAMILY, 12, "bold"),
            width=36,
            height=32,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            command=self.destroy
        )
        btn_close.pack(side="left")

        # 2. Ana Nöbetçi Kartları Alanı
        self.scroll_content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_content.pack(fill="both", expand=True, padx=24, pady=16)

        # 3. Alt Bilgi Çubuğu (Nöbetçi İdareci & İpuçları)
        self.footer_frame = ctk.CTkFrame(self, fg_color="#111827", height=42, corner_radius=0)
        self.footer_frame.pack(fill="x", side="bottom")

        vp_name = self.db.get_setting("duty_vice_principal", "") or "Müdür Yardımcısı"
        self.lbl_vp = ctk.CTkLabel(
            self.footer_frame,
            text=f"🏛️ Günün Nöbetçi İdarecisi: {vp_name}",
            font=(FONT_FAMILY, 11, "bold"),
            text_color="#FBBF24"
        )
        self.lbl_vp.pack(side="left", padx=24, pady=8)

        lbl_esc_hint = ctk.CTkLabel(
            self.footer_frame,
            text="F11: Tam Ekran  •  ESC: Çıkış  •  Otomatik Canlı Güncellenir",
            font=(FONT_FAMILY, 10),
            text_color="#9CA3AF"
        )
        lbl_esc_hint.pack(side="right", padx=24, pady=8)

        self._refresh_content()

    def _get_current_period_status(self, now_time: datetime.time) -> str:
        now_hm = now_time.strftime("%H:%M")
        for p in self.period_schedules:
            start = p.get("start", "00:00")
            end = p.get("end", "00:00")
            p_num = p.get("period", 1)
            if start <= now_hm <= end:
                return f"🔔 {p_num}. DERS DEVAM EDİYOR ({start} - {end})"

        # Ders arası / teneffüs kontrolü
        for idx in range(len(self.period_schedules) - 1):
            p_end = self.period_schedules[idx].get("end", "00:00")
            next_start = self.period_schedules[idx + 1].get("start", "00:00")
            if p_end < now_hm < next_start:
                next_p = self.period_schedules[idx + 1].get("period", idx + 2)
                return f"☕ TENEFFÜS VAKTİ ({p_end} - {next_start}) ➔ Sonraki: {next_p}. Ders"

        # Mesai dışı
        if self.period_schedules and now_hm < self.period_schedules[0].get("start", "00:00"):
            return f"🌅 DERS BAŞLANGICI: {self.period_schedules[0].get('start')}"
        elif self.period_schedules and now_hm > self.period_schedules[-1].get("end", "00:00"):
            return "🌙 GÜNLÜK EĞİTİM TAMAMLANDI"

        return "CANLI NÖBET TAKİBİ"

    def _refresh_content(self):
        for w in self.scroll_content.winfo_children():
            w.destroy()

        today = datetime.date.today()
        weekday_idx = today.weekday()
        day_id = DAY_INDEX_MAP.get(weekday_idx, "monday")

        # Bugünün atamaları
        week_assignments = self.db.get_assignments_for_week(self.week_start)
        today_assignments = [a for a in week_assignments if a.day_id == day_id]

        # Kart Izgarası
        card_bg = "#1E293B" if self.is_dark_theme else "#FFFFFF"
        border_col = "#334155" if self.is_dark_theme else "#E2E8F0"
        title_col = "#38BDF8" if self.is_dark_theme else "#0284C7"
        teacher_col = "#F8FAFC" if self.is_dark_theme else "#0F172A"
        branch_col = "#94A3B8" if self.is_dark_theme else "#64748B"

        grid_frame = ctk.CTkFrame(self.scroll_content, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True)

        cols = 3
        for c in range(cols):
            grid_frame.columnconfigure(c, weight=1, uniform="kiosk_col")

        r = 0
        c = 0
        for loc in self.locations:
            loc_assignments = [a for a in today_assignments if a.location_id == loc.id]
            teacher_names = []
            is_any_fixed = False

            for a in loc_assignments:
                if a.teacher_id and a.teacher_id in self.teachers_map:
                    t = self.teachers_map[a.teacher_id]
                    teacher_names.append((t.name, t.branch))
                    if getattr(a, "fixed", False):
                        is_any_fixed = True

            card = ctk.CTkFrame(
                grid_frame,
                fg_color=card_bg,
                corner_radius=16,
                border_width=1,
                border_color=border_col
            )
            card.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")

            # Yer Başlığı
            loc_hdr = ctk.CTkFrame(card, fg_color="transparent")
            loc_hdr.pack(fill="x", padx=16, pady=(14, 6))

            lbl_loc = ctk.CTkLabel(
                loc_hdr,
                text=loc.name.upper(),
                font=(FONT_FAMILY, 14, "bold"),
                text_color=title_col,
                anchor="w"
            )
            lbl_loc.pack(side="left")

            if is_any_fixed:
                lbl_fix = ctk.CTkLabel(
                    loc_hdr,
                    text="Sabit",
                    font=(FONT_FAMILY, 9, "bold"),
                    fg_color="#374151" if self.is_dark_theme else "#E2E8F0",
                    text_color="#9CA3AF" if self.is_dark_theme else "#475569",
                    corner_radius=6,
                    padx=6,
                    pady=2
                )
                lbl_fix.pack(side="right")

            # Nöbetçi Öğretmenler
            body = ctk.CTkFrame(card, fg_color="transparent")
            body.pack(fill="both", expand=True, padx=16, pady=(4, 14))

            if not teacher_names:
                lbl_none = ctk.CTkLabel(
                    body,
                    text="GÖREVLİ YOK / BOŞ",
                    font=(FONT_FAMILY, 13, "bold"),
                    text_color="#EF4444",
                    anchor="w"
                )
                lbl_none.pack(anchor="w", pady=6)
            else:
                for t_name, t_branch in teacher_names:
                    t_box = ctk.CTkFrame(body, fg_color="transparent")
                    t_box.pack(fill="x", pady=4, anchor="w")

                    lbl_t = ctk.CTkLabel(
                        t_box,
                        text=f"👤 {t_name}",
                        font=(FONT_FAMILY, 15, "bold"),
                        text_color=teacher_col,
                        anchor="w"
                    )
                    lbl_t.pack(anchor="w")

                    if t_branch:
                        lbl_br = ctk.CTkLabel(
                            t_box,
                            text=f"   {t_branch}",
                            font=(FONT_FAMILY, 11),
                            text_color=branch_col,
                            anchor="w"
                        )
                        lbl_br.pack(anchor="w")

            c += 1
            if c >= cols:
                c = 0
                r += 1

    def _tick(self):
        try:
            now = datetime.datetime.now()
            today = now.date()

            # Saat
            clock_str = now.strftime("%H:%M:%S")
            self.lbl_clock.configure(text=clock_str)

            # Tarih
            day_name = TURKISH_DAYS[today.weekday()]
            month_name = TURKISH_MONTHS[today.month]
            date_str = f"📅 {today.day} {month_name} {today.year} • {day_name}"
            self.lbl_date.configure(text=date_str)

            # Ders Durumu
            status_text = self._get_current_period_status(now.time())
            self.badge_status.configure(text=status_text)
            if "TENEFFÜS" in status_text:
                self.badge_status.configure(fg_color="#D97706")  # Amber/Sarı
            elif "DERS" in status_text:
                self.badge_status.configure(fg_color="#16A34A")  # Yeşil
            else:
                self.badge_status.configure(fg_color="#1E3A8A")  # Lacivert

        except Exception:
            pass

        # Her saniye saati, her 30 saniyede bir kartları tazele
        self.after(1000, self._tick)
