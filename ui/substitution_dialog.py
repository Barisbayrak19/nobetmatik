"""
Boş Ders Doldurma ve Nöbetçi İkame Dialogu (Substitution Dialog - Modern CustomTkinter)
Birden fazla gelmeyen öğretmenin ders saatlerini aynı anda yönetir,
o gün nöbetçi olan öğretmenlerin boş dersleri ve okulun boş öğretmenleri ile
sıfır çakışma ve tam adaletle eşleştirir.
Tek bir derse birden fazla nöbetçi atanabilir.
Bireysel görevlendirme fişi ve toplu günlük çizelge (PDF/HTML) üretir.
"""
import os
import datetime
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict

from core.models import Teacher, Day, Location, TeacherLesson, SubstitutionAssignment, AttendanceRecord
from core.database import Database
from logic.substitution_service import SubstitutionService, PERIOD_TIMES, is_same_branch
from core.logger import logger
from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_SECONDARY, COLOR_SUCCESS,
    COLOR_BORDER, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, FONT_FAMILY
)
from ui.whatsapp_dialog import WhatsAppNotifyDialog

class SubstitutionDialog(ctk.CTkToplevel):
    _instance: Optional['SubstitutionDialog'] = None

    def __new__(cls, parent: Any, db: Database, current_week_start: str):
        if cls._instance is not None:
            try:
                if cls._instance.winfo_exists():
                    cls._instance.deiconify()
                    cls._instance.lift()
                    cls._instance.focus_force()
                    return cls._instance
            except Exception:
                cls._instance = None
        instance = super().__new__(cls)
        cls._instance = instance
        return instance

    def __init__(self, parent: Any, db: Database, current_week_start: str):
        if getattr(self, '_initialized', False):
            self.deiconify()
            self.lift()
            self.focus_force()
            return
        self._initialized = True

        super().__init__(parent)
        self.title("Boş Ders Doldurma ve Nöbetçi Öğretmen İkame Asistanı (Çoklu Öğretmen Destekli)")
        self.geometry("1180x800")
        self.minsize(880, 600)
        self.configure(fg_color=COLOR_BG)

        # Ön plana çıkarma ve odaklanma
        self.after(100, self.lift)
        self.after(150, self.focus_force)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.db = db
        self.sub_service = SubstitutionService(db)
        self.current_week_start = self.sub_service._ensure_week_start(current_week_start)

        self.teachers = self.db.get_teachers(active_only=True)
        self.all_teachers = self.db.get_teachers(active_only=False)
        self.teacher_map = {t.id: t for t in self.all_teachers}
        self.days = self.db.get_days()

        # Varsayılan gün ve tarih
        today = datetime.date.today()
        if today.weekday() > 4:
            days_ahead = 7 - today.weekday()
            today = today + datetime.timedelta(days=days_ahead)

        day_names_tr = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        cur_day_name = day_names_tr[today.weekday()] if today.weekday() < 5 else "Pazartesi"

        self.date_var = tk.StringVar(value=today.strftime("%Y-%m-%d"))
        self.day_var = tk.StringVar(value=cur_day_name)
        self.add_teacher_var = tk.StringVar()
        self.absence_status_var = tk.StringVar(value="Raporlu")
        self.teachers_per_lesson_var = tk.IntVar(value=1)

        # Çoklu Gelmeyen Öğretmen Yönetimi
        self.absent_teachers: List[Teacher] = []
        self.active_teacher_id: Optional[str] = None
        self.teacher_absence_status: Dict[str, str] = {}
        # teacher_id -> list of SubstitutionAssignment (in-memory)
        self.assignments_cache: Dict[str, List[SubstitutionAssignment]] = {}

        # Aktif tablodaki satır verileri (aktif öğretmen için)
        self.period_rows: List[Dict[str, Any]] = []

        self._build_ui()
        self._load_initial_absent_teachers()

    def _build_ui(self):
        # Combobox için özel genişletilmiş açılır menü (dropdown) stili
        try:
            combo_style = ttk.Style()
            combo_style.configure("SubCandidate.TCombobox", postoffset=(0, 0, 160, 0))
        except Exception:
            pass

        # 1. Üst Başlık ve Bilgilendirme
        top_frame = ctk.CTkFrame(self, fg_color=COLOR_PRIMARY, corner_radius=0)
        top_frame.pack(fill="x", side="top", ipady=8)

        f_inner_top = ctk.CTkFrame(top_frame, fg_color="transparent")
        f_inner_top.pack(fill="x", padx=20, pady=4)

        lbl_title = ctk.CTkLabel(
            f_inner_top,
            text="📋 BOŞ DERS DOLDURMA & ÇOKLU NÖBETÇİ GÖREVLENDİRME ASİSTANI",
            font=(FONT_FAMILY, 14, "bold"),
            text_color="#FFFFFF"
        )
        lbl_title.pack(anchor="w")

        lbl_desc = ctk.CTkLabel(
            f_inner_top,
            text="Birden fazla gelmeyen öğretmenin derslerini çakışmasız ve adil dağıtır. Nöbetçiler doluysa okulun boş öğretmenlerini ve kat nöbetçilerini devreye sokar.",
            font=(FONT_FAMILY, 11),
            text_color="#CBD5E1"
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        # 2. Üst Kontrol Çubuğu (2 Satırlı Düzenli ve Taşmayan Kontroller)
        control_card = ctk.CTkFrame(
            self,
            fg_color=COLOR_CARD,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER
        )
        control_card.pack(fill="x", padx=16, pady=(10, 6))

        # Satır 1: Tarih, Gün, Gelmeyen Öğretmen Seçimi ve Listeye Ekle Butonu
        f_row1 = ctk.CTkFrame(control_card, fg_color="transparent")
        f_row1.pack(fill="x", padx=14, pady=(8, 4))

        # Tarih
        ctk.CTkLabel(f_row1, text="Tarih:", font=(FONT_FAMILY, 11, "bold"), text_color=COLOR_TEXT_MAIN).pack(side="left", padx=(0, 6))
        ent_date = ctk.CTkEntry(f_row1, textvariable=self.date_var, width=105, font=(FONT_FAMILY, 11), height=30)
        ent_date.pack(side="left", padx=(0, 14))
        ent_date.bind("<FocusOut>", lambda e: self._on_date_changed())
        ent_date.bind("<Return>", lambda e: self._on_date_changed())

        # Gün
        ctk.CTkLabel(f_row1, text="Gün:", font=(FONT_FAMILY, 11, "bold"), text_color=COLOR_TEXT_MAIN).pack(side="left", padx=(0, 6))
        day_cb = ttk.Combobox(
            f_row1,
            textvariable=self.day_var,
            values=[d.name for d in self.days],
            state="readonly",
            width=11,
            font=(FONT_FAMILY, 10)
        )
        day_cb.pack(side="left", padx=(0, 14), ipady=2)
        day_cb.bind("<<ComboboxSelected>>", lambda e: self._on_day_changed())

        # Ayırıcı
        ttk.Separator(f_row1, orient="vertical").pack(side="left", fill="y", padx=8, pady=2)

        # Gelmeyen Öğretmen Seç
        ctk.CTkLabel(f_row1, text="Gelmeyen Öğretmen:", font=(FONT_FAMILY, 11, "bold"), text_color=COLOR_TEXT_MAIN).pack(side="left", padx=(0, 6))
        teacher_names = sorted([t.name for t in self.teachers])
        cb_values = ["— Öğretmen Seçin —"] + teacher_names
        self.cb_add_teacher = ttk.Combobox(
            f_row1,
            textvariable=self.add_teacher_var,
            values=cb_values,
            state="readonly",
            width=22,
            font=(FONT_FAMILY, 10)
        )
        self.cb_add_teacher.pack(side="left", padx=(0, 8), ipady=2)
        self.cb_add_teacher.current(0)

        # Neden
        ctk.CTkLabel(f_row1, text="Neden:", font=(FONT_FAMILY, 11, "bold"), text_color=COLOR_TEXT_MAIN).pack(side="left", padx=(0, 6))
        status_cb = ttk.Combobox(
            f_row1,
            textvariable=self.absence_status_var,
            values=["Raporlu", "İzinli", "Sevkli", "Görevli", "Mazeretli"],
            state="readonly",
            width=10,
            font=(FONT_FAMILY, 10)
        )
        status_cb.pack(side="left", padx=(0, 10), ipady=2)

        btn_add = ctk.CTkButton(
            f_row1,
            text="➕ Listeye Ekle",
            font=(FONT_FAMILY, 11, "bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_SECONDARY,
            height=30,
            corner_radius=6,
            command=self._on_add_absent_teacher
        )
        btn_add.pack(side="left")

        # Satır 2: Dağıtım Tercihleri ve Bilgilendirme
        f_row2 = ctk.CTkFrame(control_card, fg_color="transparent")
        f_row2.pack(fill="x", padx=14, pady=(2, 8))

        # Nöbetçi/Ders
        ctk.CTkLabel(f_row2, text="Ders Başına Nöbetçi:", font=(FONT_FAMILY, 10, "bold"), text_color=COLOR_TEXT_MAIN).pack(side="left", padx=(0, 6))
        count_cb = ttk.Combobox(
            f_row2,
            textvariable=self.teachers_per_lesson_var,
            values=[1, 2],
            state="readonly",
            width=4,
            font=(FONT_FAMILY, 10)
        )
        count_cb.pack(side="left", padx=(0, 14), ipady=1)

        # Ayırıcı
        ttk.Separator(f_row2, orient="vertical").pack(side="left", fill="y", padx=8, pady=2)

        # Branşdaşa Ek Ders Öner Checkbox
        self.allow_branch_peers_var = tk.BooleanVar(value=True)
        chk_branch = ctk.CTkCheckBox(
            f_row2,
            text="Nöbetçi yetmezse branşdaşına ek ders öner (Gönüllü Ek Ders)",
            variable=self.allow_branch_peers_var,
            font=(FONT_FAMILY, 10, "bold"),
            text_color=COLOR_TEXT_MAIN,
            checkbox_width=18,
            checkbox_height=18,
            corner_radius=4
        )
        chk_branch.pack(side="left", padx=(4, 14))

        # Açıklama Rozeti
        lbl_info_badge = ctk.CTkLabel(
            f_row2,
            text="💡 Okulda kabul kriteri: Öğretmenin o günkü ilk ve son ders saatleri aralığıdır.",
            font=(FONT_FAMILY, 9),
            text_color=COLOR_TEXT_MUTED
        )
        lbl_info_badge.pack(side="right")

        # 3. Gelmeyen Öğretmenler Çubuğu (Dinamik Rozetler / Tablar)
        self.f_absent_pills = ctk.CTkFrame(self, fg_color="transparent")
        self.f_absent_pills.pack(fill="x", padx=16, pady=(4, 4))

        # 4. O Günün Nöbetçi Öğretmenleri Bilgi Paneli
        self.duty_banner = ctk.CTkFrame(
            self,
            fg_color="#EFF6FF",
            border_width=1,
            border_color="#BFDBFE",
            corner_radius=8
        )
        self.duty_banner.pack(fill="x", padx=16, pady=(2, 6))

        self.lbl_duty_info = ctk.CTkLabel(
            self.duty_banner,
            text="Günün Nöbetçileri yükleniyor...",
            font=(FONT_FAMILY, 10),
            text_color="#1E40AF",
            justify="left",
            wraplength=1120
        )
        self.lbl_duty_info.pack(fill="x", anchor="w", padx=14, pady=8)

        # 5. Dersler ve İkame Tablosu (CustomTkinter Scrollable Frame)
        self.table_container = ctk.CTkFrame(
            self,
            fg_color=COLOR_CARD,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER
        )
        self.table_container.pack(fill="both", expand=True, padx=16, pady=4)

        # Container Header
        self.lbl_table_header = ctk.CTkLabel(
            self.table_container,
            text=" 📚 Seçili Gelmeyen Öğretmenin Dersleri ve İkameleri ",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLOR_TEXT_MAIN
        )
        self.lbl_table_header.pack(anchor="w", padx=14, pady=(10, 4))

        self.scroll_content = ctk.CTkScrollableFrame(self.table_container, fg_color="transparent")
        self.scroll_content.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # 6. Alt Butonlar Barı
        bottom_bar = ctk.CTkFrame(self, fg_color="transparent", height=45)
        bottom_bar.pack(fill="x", side="bottom", padx=16, pady=(6, 12))

        btn_save = ctk.CTkButton(
            bottom_bar,
            text="💾 TÜM GÖREVLENDİRMELERİ KAYDET",
            font=(FONT_FAMILY, 11, "bold"),
            fg_color="#059669",
            hover_color="#047857",
            height=34,
            corner_radius=6,
            command=self.save_assignments
        )
        btn_save.pack(side="left", padx=(0, 10))

        btn_daily_preview = ctk.CTkButton(
            bottom_bar,
            text="🖨️ Toplu Önizle & Yazdır",
            font=(FONT_FAMILY, 10, "bold"),
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            height=34,
            corner_radius=6,
            command=self.preview_daily
        )
        btn_daily_preview.pack(side="left", padx=(0, 8))

        btn_single_preview = ctk.CTkButton(
            bottom_bar,
            text="📄 Kişisel Fiş Önizle & Yazdır",
            font=(FONT_FAMILY, 10, "bold"),
            fg_color="#334155",
            hover_color="#1E293B",
            height=34,
            corner_radius=6,
            command=self.preview_single
        )
        btn_single_preview.pack(side="left", padx=(0, 8))

        btn_whatsapp = ctk.CTkButton(
            bottom_bar,
            text="📱 WhatsApp ile Bildir",
            font=(FONT_FAMILY, 10, "bold"),
            fg_color="#16A34A",
            hover_color="#15803D",
            height=34,
            corner_radius=6,
            command=self.open_whatsapp_dialog
        )
        btn_whatsapp.pack(side="left", padx=(0, 8))

        btn_close = ctk.CTkButton(
            bottom_bar,
            text="Kapat",
            font=(FONT_FAMILY, 10, "bold"),
            fg_color="#94A3B8",
            hover_color="#64748B",
            height=34,
            width=80,
            corner_radius=6,
            command=self.destroy
        )
        btn_close.pack(side="right")

    def destroy(self):
        SubstitutionDialog._instance = None
        super().destroy()

    # --- Gelmeyen Öğretmenler Yönetimi ---
    def _load_initial_absent_teachers(self):
        date_str = self.date_var.get().strip()
        self.current_week_start = self.sub_service._ensure_week_start(date_str)
        existing = self.db.get_substitutions_for_date(date_str)
        attendance = self.db.get_attendance_records(date_str=date_str)

        self.absent_teachers = []
        self.assignments_cache.clear()
        self.teacher_absence_status.clear()
        self.active_teacher_id = None

        initial_ids = set()
        for s in existing:
            if s.absent_teacher_id:
                initial_ids.add(s.absent_teacher_id)
        for a in attendance:
            if a.teacher_id:
                initial_ids.add(a.teacher_id)
                self.teacher_absence_status[a.teacher_id] = a.status

        # Mevcut kayıtlı atamaları önbelleğe al
        for s in existing:
            if s.absent_teacher_id not in self.assignments_cache:
                self.assignments_cache[s.absent_teacher_id] = []
            self.assignments_cache[s.absent_teacher_id].append(s)

        for tid in initial_ids:
            t = self.teacher_map.get(tid)
            if t and t not in self.absent_teachers:
                self.absent_teachers.append(t)
                if tid not in self.teacher_absence_status:
                    self.teacher_absence_status[tid] = "Raporlu"

        if self.absent_teachers:
            self.active_teacher_id = self.absent_teachers[0].id
        else:
            self.active_teacher_id = None

        self._refresh_pills_and_view()

    def _on_add_absent_teacher(self):
        name = self.add_teacher_var.get().strip()
        if not name or name == "— Öğretmen Seçin —":
            messagebox.showwarning("Uyarı", "Lütfen bir öğretmen seçin.", parent=self)
            return

        t = next((teach for teach in self.teachers if teach.name == name), None)
        if not t:
            messagebox.showwarning("Uyarı", "Seçilen öğretmen bulunamadı.", parent=self)
            return

        if any(at.id == t.id for at in self.absent_teachers):
            messagebox.showinfo("Bilgi", f"'{t.name}' zaten gelmeyenler listesinde yer alıyor.", parent=self)
            self.active_teacher_id = t.id
            self._refresh_pills_and_view()
            return

        self._save_current_rows_to_cache()
        self.absent_teachers.append(t)
        self.teacher_absence_status[t.id] = self.absence_status_var.get().strip() or "Raporlu"
        self.active_teacher_id = t.id
        self._refresh_pills_and_view()

    def _remove_absent_teacher(self, teacher_id: str):
        self._save_current_rows_to_cache()
        t = self.teacher_map.get(teacher_id)
        if not t:
            return

        if messagebox.askyesno("Onay", f"'{t.name}' gelmeyenler listesinden çıkarılsın mı?", parent=self):
            self.absent_teachers = [at for at in self.absent_teachers if at.id != teacher_id]
            self.assignments_cache.pop(teacher_id, None)
            self.teacher_absence_status.pop(teacher_id, None)
            if self.active_teacher_id == teacher_id:
                self.active_teacher_id = self.absent_teachers[0].id if self.absent_teachers else None
            self._refresh_pills_and_view()

    def _refresh_pills_and_view(self):
        # Rozet çubuğunu temizle ve yeniden oluştur
        for w in self.f_absent_pills.winfo_children():
            w.destroy()

        count = len(self.absent_teachers)
        lbl_lbl = ctk.CTkLabel(
            self.f_absent_pills,
            text=f"📌 Gelmeyen Öğretmenler ({count}):",
            font=(FONT_FAMILY, 11, "bold"),
            text_color="#0F172A"
        )
        lbl_lbl.pack(side="left", padx=(0, 8), pady=2)

        if not self.absent_teachers:
            lbl_none = ctk.CTkLabel(
                self.f_absent_pills,
                text="Henüz gelmeyen öğretmen eklenmedi. Yukarıdan seçip '➕ Listeye Ekle'ye tıklayın.",
                font=(FONT_FAMILY, 10, "italic"),
                text_color=COLOR_TEXT_MUTED
            )
            lbl_none.pack(side="left", padx=(0, 8), pady=2)

        for t in self.absent_teachers:
            is_active = (t.id == self.active_teacher_id)
            status = self.teacher_absence_status.get(t.id, "Raporlu")

            pill_bg = "#2563EB" if is_active else "#E2E8F0"
            pill_hover = "#1D4ED8" if is_active else "#CBD5E1"
            text_col = "#FFFFFF" if is_active else "#0F172A"

            pill_frame = ctk.CTkFrame(self.f_absent_pills, fg_color=pill_bg, corner_radius=12)
            pill_frame.pack(side="left", padx=4, pady=2)

            btn_pill = ctk.CTkButton(
                pill_frame,
                text=f"👤 {t.name} ({status})",
                font=(FONT_FAMILY, 10, "bold" if is_active else "normal"),
                fg_color="transparent",
                hover_color=pill_hover,
                text_color=text_col,
                height=26,
                command=lambda tid=t.id: self._switch_active_teacher(tid)
            )
            btn_pill.pack(side="left", padx=(4, 0))

            btn_del = ctk.CTkButton(
                pill_frame,
                text="✕",
                font=(FONT_FAMILY, 10, "bold"),
                fg_color="transparent",
                hover_color="#FCA5A5",
                text_color="#FCA5A5" if is_active else "#DC2626",
                width=22,
                height=26,
                command=lambda tid=t.id: self._remove_absent_teacher(tid)
            )
            btn_del.pack(side="left", padx=(0, 4))

        # Sağ tarafa Otomatik Dağıtım Butonları
        f_actions = ctk.CTkFrame(self.f_absent_pills, fg_color="transparent")
        f_actions.pack(side="right")

        btn_auto_all = ctk.CTkButton(
            f_actions,
            text="⚡ TÜM GELMEYENLER İÇİN ADİL DAĞIT",
            font=(FONT_FAMILY, 11, "bold"),
            fg_color="#D97706",
            hover_color="#B45309",
            corner_radius=6,
            height=30,
            command=self.auto_match_all_teachers
        )
        btn_auto_all.pack(side="right", padx=(8, 0))

        btn_auto_single = ctk.CTkButton(
            f_actions,
            text="⚡ Bu Öğretmen İçin Dağıt",
            font=(FONT_FAMILY, 10, "bold"),
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            corner_radius=6,
            height=30,
            command=self.auto_match_single_teacher
        )
        btn_auto_single.pack(side="right")

        self._render_active_teacher_lessons()

    def _switch_active_teacher(self, teacher_id: str):
        if self.active_teacher_id != teacher_id:
            self._save_current_rows_to_cache()
            self.active_teacher_id = teacher_id
            self._refresh_pills_and_view()

    def _save_current_rows_to_cache(self):
        if not self.active_teacher_id:
            return
        if not self.period_rows:
            return
        assignments = self._collect_current_rows()
        has_any_assigned = any(s.duty_teacher_id for s in assignments)
        existing_in_cache = self.assignments_cache.get(self.active_teacher_id, [])
        cache_has_assigned = any(s.duty_teacher_id for s in existing_in_cache)
        # Eğer ekranda henüz seçim yapılmamışsa ama bellekte geçerli atama varsa, belleği ezme!
        if not has_any_assigned and cache_has_assigned:
            return
        self.assignments_cache[self.active_teacher_id] = assignments

    def _get_all_in_memory_assignments(self, save_current: bool = False) -> List[SubstitutionAssignment]:
        """Tüm gelmeyen öğretmenlerin bellekteki atamalarını tek listede toplar."""
        if save_current:
            self._save_current_rows_to_cache()
        all_subs = []
        for t_id, subs in self.assignments_cache.items():
            all_subs.extend(subs)
        return all_subs

    # --- Banner ve Tarih Güncellemeleri ---
    def _on_date_changed(self):
        date_str = self.date_var.get().strip()
        try:
            dt = datetime.date.fromisoformat(date_str)
            day_names_tr = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
            if dt.weekday() < 5:
                self.day_var.set(day_names_tr[dt.weekday()])
        except Exception:
            pass
        self._load_initial_absent_teachers()

    def _on_day_changed(self):
        self.assignments_cache.clear()
        self._render_active_teacher_lessons()

    def _update_duty_banner(self):
        day_name = self.day_var.get()
        duty_info = self.sub_service.get_day_duty_teachers(self.current_week_start, day_name)
        if not duty_info:
            self.lbl_duty_info.configure(text=f"⚠️ {day_name} günü için ({self.current_week_start} haftası) atanmış nöbetçi öğretmen bulunamadı.")
            return

        all_subs = self._get_all_in_memory_assignments(save_current=False)
        assigned_counts: Dict[str, int] = defaultdict(int)
        assigned_periods_map: Dict[str, List[int]] = defaultdict(list)
        for s in all_subs:
            if s.duty_teacher_id:
                assigned_counts[s.duty_teacher_id] += 1
                assigned_periods_map[s.duty_teacher_id].append(s.period)

        absent_ids = {t.id for t in self.absent_teachers}

        lines = [f"• {day_name.upper()} GÜNÜ NÖBETÇİ ÖĞRETMENLERİ VE GÖREVLENDİRME DURUMU:"]
        for d in duty_info:
            t = d["teacher"]
            loc = d["location"].name if d["location"] else "-"
            if t.id in absent_ids:
                lines.append(f"   ⚠️ {t.name} ({loc}) ➔ NÖBETÇİ ANCAK KENDİSİ DE BUGÜN GELMEDİ (İzinli/Raporlu - İkame havuzundan muaf)")
            else:
                free_str = ", ".join(map(str, d["free_periods"])) if d["free_periods"] else "Dolu"
                given = assigned_counts[t.id]
                given_str = f" | ⚡ Verilen İkame: {given} saat ({', '.join(map(str, sorted(assigned_periods_map[t.id])))}. Ders)" if given > 0 else " | Henüz İkame Verilmedi"
                lines.append(f"   • {t.name} ({loc}) ➔ Boş Saatleri: {free_str}{given_str}")

        self.lbl_duty_info.configure(text="\n".join(lines))

    # --- Ders Tablosu Render ---
    def _render_active_teacher_lessons(self):
        for w in self.scroll_content.winfo_children():
            w.destroy()
        self.period_rows.clear()

        teacher = self.teacher_map.get(self.active_teacher_id) if self.active_teacher_id else None
        if not teacher:
            self.lbl_table_header.configure(text=" ◆ Dersler ve İkame Görevlendirme Tablosu ")
            f_empty = ctk.CTkFrame(self.scroll_content, fg_color="transparent")
            f_empty.pack(expand=True, fill="both", pady=40)

            ctk.CTkLabel(
                f_empty,
                text="ℹ️ Henüz gelmeyen bir öğretmen seçilmedi.",
                font=(FONT_FAMILY, 13, "bold"),
                text_color=COLOR_TEXT_MAIN
            ).pack(pady=(0, 6))

            ctk.CTkLabel(
                f_empty,
                text="Yukarıdaki 'Gelmeyen Öğretmen' kutusundan gelmeyen öğretmeni seçip '➕ Listeye Ekle' butonuna basınız.\nBirden fazla gelmeyen öğretmen ekleyerek tüm dersleri tek tıkla adil ve çakışmasız dağıtabilirsiniz.",
                font=(FONT_FAMILY, 11),
                text_color=COLOR_TEXT_MUTED,
                justify="center"
            ).pack()

            self._update_duty_banner()
            return

        status = self.teacher_absence_status.get(teacher.id, "Raporlu")
        self.lbl_table_header.configure(text=f" ◆ {teacher.name} ({teacher.branch} - {status}) Dersleri ve Görevlendirilen Nöbetçiler ")

        day_name = self.day_var.get()
        lessons = self.sub_service.get_teacher_schedule(teacher.id, day_name)

        if not lessons:
            lbl = ctk.CTkLabel(
                self.scroll_content,
                text=f"'{teacher.name}' isimli öğretmenin {day_name} günü ders programı bulunamadı.",
                font=(FONT_FAMILY, 11),
                text_color=COLOR_TEXT_MUTED
            )
            lbl.pack(pady=30)
            return

        # Bellekteki veya veritabanındaki kayıtlı atamalar
        date_str = self.date_var.get().strip()
        cached_subs = self.assignments_cache.get(teacher.id)
        if cached_subs is None:
            db_subs = [s for s in self.db.get_substitutions_for_date(date_str) if s.absent_teacher_id == teacher.id]
            cached_subs = db_subs
            self.assignments_cache[teacher.id] = cached_subs

        existing_map: Dict[int, List[SubstitutionAssignment]] = defaultdict(list)
        for s in cached_subs:
            existing_map[s.period].append(s)

        # Başlık Satırı
        h_frame = ctk.CTkFrame(self.scroll_content, fg_color="#1E293B", corner_radius=6)
        h_frame.pack(fill="x", pady=(0, 6), padx=4, ipady=6)

        ctk.CTkLabel(h_frame, text="Ders Saati", font=(FONT_FAMILY, 10, "bold"), text_color="#FFF", width=80, anchor="w").pack(side="left", padx=(10, 0))
        ctk.CTkLabel(h_frame, text="Saat Aralığı", font=(FONT_FAMILY, 10, "bold"), text_color="#FFF", width=110, anchor="w").pack(side="left")
        ctk.CTkLabel(h_frame, text="Sınıf", font=(FONT_FAMILY, 10, "bold"), text_color="#FFF", width=70, anchor="w").pack(side="left")
        ctk.CTkLabel(h_frame, text="Ders", font=(FONT_FAMILY, 10, "bold"), text_color="#FFF", width=80, anchor="w").pack(side="left")
        ctk.CTkLabel(h_frame, text="Durum / Uyarı", font=(FONT_FAMILY, 10, "bold"), text_color="#FFF", width=170, anchor="w").pack(side="right", padx=(0, 10))
        ctk.CTkLabel(h_frame, text="Görevlendirilen Öğretmen(ler)", font=(FONT_FAMILY, 10, "bold"), text_color="#FFF", anchor="w").pack(side="left", padx=(0, 8))

        # Diğer gelmeyen öğretmenlerin atamaları (saat çakışması tespiti için)
        other_subs = []
        for tid, s_list in self.assignments_cache.items():
            if tid != teacher.id:
                other_subs.extend(s_list)

        has_busy_lesson = False
        for l in sorted(lessons, key=lambda x: x.period):
            if l.is_free:
                continue
            has_busy_lesson = True

            candidates = self.sub_service.find_candidates_for_period(
                week_start=self.current_week_start,
                day_name=day_name,
                period=l.period,
                absent_teacher_id=teacher.id,
                absent_teacher_branch=teacher.branch,
                date_str=date_str,
                exclude_teacher_ids=[at.id for at in self.absent_teachers],
                active_substitutions=other_subs
            )

            cb_values = ["— Öğretmen Seçin —"]
            teacher_option_map = {}
            for c in candidates:
                if c.get("is_duty"):
                    role_text = "[Nöbetçi]"
                    if c["is_free"]:
                        status_text = "✔ [BOŞ]"
                    else:
                        ld = c.get('lesson_desc', 'Dolu')
                        if ld.startswith("⚠️") or ld.startswith("⛔") or ld.startswith("🔴") or ld.startswith("⚪"):
                            status_text = ld
                        else:
                            status_text = f"⚠️ [{ld}]"
                    ek_ders_tag = " ⭐ [Ek Ders (Branş)]" if c.get("is_branch_match") and c["is_free"] else ""
                    opt_text = f"{c['teacher'].name} {role_text} {status_text}{ek_ders_tag}"
                else:
                    role_text = "⭐ [Branşdaş]"
                    if c["is_free"]:
                        status_text = "✔ [BOŞ - Ek Ders]"
                    else:
                        ld = c.get('lesson_desc', 'Dolu')
                        if ld.startswith("⚠️") or ld.startswith("⛔") or ld.startswith("🔴") or ld.startswith("⚪"):
                            status_text = ld
                        else:
                            status_text = f"⚠️ [{ld}]"
                    opt_text = f"{c['teacher'].name} {role_text} {status_text}"
                cb_values.append(opt_text)
                teacher_option_map[opt_text] = c["teacher"]

            row_f = ctk.CTkFrame(self.scroll_content, fg_color="#F8FAFC", corner_radius=6, border_width=1, border_color="#E2E8F0")
            row_f.pack(fill="x", pady=3, padx=4, ipady=4)

            ctk.CTkLabel(row_f, text=f"{l.period}. Ders", font=(FONT_FAMILY, 10, "bold"), text_color=COLOR_TEXT_MAIN, width=80, anchor="w").pack(side="left", padx=(10, 0))
            time_str = PERIOD_TIMES.get(l.period, "")
            ctk.CTkLabel(row_f, text=time_str, font=(FONT_FAMILY, 10), text_color=COLOR_TEXT_MAIN, width=110, anchor="w").pack(side="left")
            ctk.CTkLabel(row_f, text=l.class_name, font=(FONT_FAMILY, 10, "bold"), text_color="#2563EB", width=70, anchor="w").pack(side="left")
            ctk.CTkLabel(row_f, text=l.subject_code, font=(FONT_FAMILY, 10), text_color=COLOR_TEXT_MAIN, width=80, anchor="w").pack(side="left")

            duty_container = ctk.CTkFrame(row_f, fg_color="transparent")
            duty_container.pack(side="left", fill="x", padx=(0, 8))

            slots_frame = ctk.CTkFrame(duty_container, fg_color="transparent")
            slots_frame.pack(side="left")

            lbl_status = ctk.CTkLabel(row_f, text="Atama bekleniyor", font=(FONT_FAMILY, 9, "italic"), text_color=COLOR_TEXT_MUTED, width=170, anchor="w")
            lbl_status.pack(side="right", padx=(0, 10))

            row_data = {
                "period": l.period,
                "lesson": l,
                "slots_frame": slots_frame,
                "slots": [],
                "opt_map": teacher_option_map,
                "cb_values": cb_values,
                "candidates": candidates,
                "status_lbl": lbl_status
            }

            btn_add = ctk.CTkButton(
                duty_container,
                text="➕ Ekle",
                font=(FONT_FAMILY, 9, "bold"),
                fg_color="#E2E8F0",
                hover_color="#CBD5E1",
                text_color="#0F172A",
                width=50,
                height=26,
                corner_radius=4,
                command=lambda rd=row_data: self._add_teacher_slot(rd)
            )
            btn_add.pack(side="left", padx=4)

            self.period_rows.append(row_data)

            # Önceden kayıtlı olan görevlendirmeleri yükle
            existing_for_period = existing_map.get(l.period, [])
            valid_existing = [s for s in existing_for_period if s.duty_teacher_id]
            if valid_existing:
                for s in valid_existing:
                    self._add_teacher_slot(row_data, teacher_id=s.duty_teacher_id)
            else:
                self._add_teacher_slot(row_data)

        if not has_busy_lesson:
            lbl_empty = ctk.CTkLabel(
                self.scroll_content,
                text=f"✔ '{teacher.name}' isimli öğretmenin {day_name} günü dersi bulunmamaktadır (Tüm gün boş).",
                font=(FONT_FAMILY, 11, "bold"),
                text_color="#16A34A"
            )
            lbl_empty.pack(pady=30)

        # Tablo çizildikten sonra nöbetçi özetini güncelle
        self._update_duty_banner()

    def _add_teacher_slot(self, row_data: Dict[str, Any], teacher_id: Optional[str] = None):
        slot_f = ctk.CTkFrame(row_data["slots_frame"], fg_color="transparent")
        slot_f.pack(side="left", padx=(0, 4))

        var_choice = tk.StringVar(value=row_data["cb_values"][0])

        if teacher_id:
            found = False
            for opt_text, t_obj in row_data["opt_map"].items():
                if t_obj.id == teacher_id:
                    var_choice.set(opt_text)
                    found = True
                    break
            if not found:
                t_obj = self.teacher_map.get(teacher_id)
                if t_obj:
                    opt_text = f"{t_obj.name} [Kat Nöbetçisi Gözetmen]"
                    row_data["cb_values"].append(opt_text)
                    row_data["opt_map"][opt_text] = t_obj
                    var_choice.set(opt_text)

        cb = ttk.Combobox(
            slot_f,
            textvariable=var_choice,
            values=row_data["cb_values"],
            state="readonly",
            style="SubCandidate.TCombobox",
            width=44,
            font=(FONT_FAMILY, 9)
        )
        cb.pack(side="left", padx=(0, 2), ipady=2)
        cb.set(var_choice.get())

        slot_item = {"var": var_choice, "cb": cb, "frame": slot_f}
        row_data["slots"].append(slot_item)

        btn_del = ctk.CTkButton(
            slot_f,
            text="✕",
            font=(FONT_FAMILY, 9, "bold"),
            fg_color="#FEE2E2",
            hover_color="#FCA5A5",
            text_color="#DC2626",
            width=24,
            height=24,
            corner_radius=4,
            command=lambda rd=row_data, si=slot_item: self._remove_teacher_slot(rd, si)
        )
        btn_del.pack(side="left")

        cb.bind("<<ComboboxSelected>>", lambda e, rd=row_data: self._update_row_status(rd))
        self._update_row_status(row_data)

    def _remove_teacher_slot(self, row_data: Dict[str, Any], slot_item: Dict[str, Any]):
        if len(row_data["slots"]) > 1:
            slot_item["frame"].destroy()
            row_data["slots"].remove(slot_item)
        else:
            slot_item["var"].set(row_data["cb_values"][0])
            slot_item["cb"].set(row_data["cb_values"][0])
        self._update_row_status(row_data)

    def _update_row_status(self, row_data: Dict[str, Any]):
        assigned_teachers = []
        has_conflict = False
        for s in row_data["slots"]:
            val = s["var"].get()
            t_obj = row_data["opt_map"].get(val)
            if t_obj:
                assigned_teachers.append(t_obj)
                if "⚠️" in val or "⛔" in val or "❌" in val or "🔴" in val:
                    has_conflict = True

        lbl = row_data["status_lbl"]
        if not assigned_teachers:
            lbl.configure(text="Atama bekleniyor", text_color=COLOR_TEXT_MUTED)
        elif has_conflict:
            lbl.configure(text="⚠️ Kat Nöbetçisi (Gözetmen)", text_color="#D97706")
        elif len(assigned_teachers) == 1:
            lbl.configure(text="✔ 1 Öğretmen Boşta", text_color="#16A34A")
        else:
            lbl.configure(text=f"✔ {len(assigned_teachers)} Öğretmen (Ortak)", text_color="#2563EB")

    # --- Otomatik Dağıtım Mekanizmaları ---
    def auto_match_all_teachers(self):
        """
        Tüm gelmeyen öğretmenlerin derslerini TEK BİR KÜRESEL OPTİMİZASYONLA dağıtır.
        Nöbetçiler doluysa okulun boş öğretmenlerini ve kat nöbetçisini devreye sokar.
        Hiçbir öğretmen aynı saatte iki derse çakışmaz, iş yükü eşit paylaştırılır.
        """
        if not self.absent_teachers:
            messagebox.showwarning("Uyarı", "Lütfen en az bir gelmeyen öğretmen ekleyin.")
            return

        date_str = self.date_var.get().strip()
        day_name = self.day_var.get()
        count_per_lesson = self.teachers_per_lesson_var.get()
        absent_ids = [t.id for t in self.absent_teachers]

        self.current_week_start = self.sub_service._ensure_week_start(date_str)

        allow_branch_peers = self.allow_branch_peers_var.get()

        results_by_teacher = self.sub_service.auto_assign_multi_substitutions(
            date_str=date_str,
            day_name=day_name,
            absent_teacher_ids=absent_ids,
            week_start=self.current_week_start,
            teachers_per_lesson=count_per_lesson,
            allow_branch_peers_ek_ders=allow_branch_peers
        )

        for tid, subs in results_by_teacher.items():
            self.assignments_cache[tid] = subs

        # Aktif tablodaki satırları yeniden doldur
        self._render_active_teacher_lessons()

        total_lessons = sum(len(subs) for subs in results_by_teacher.values())
        assigned_duties = sum(1 for subs in results_by_teacher.values() for s in subs if s.duty_teacher_id)

        messagebox.showinfo(
            "Toplu Adil Dağıtım Tamamlandı",
            f"Toplam {len(self.absent_teachers)} gelmeyen öğretmenin {total_lessons} ders saatine "
            f"toplam {assigned_duties} görevlendirme sıfır çakışma ile adil olarak paylaştırıldı.\n\n"
            f"(Önce boş nöbetçiler, gerekirse aynı branştaki boş öğretmenler veya kat nöbetçileri devreye alındı)."
        )

    def auto_match_single_teacher(self):
        """
        Yalnızca seçili gelmeyen öğretmenin derslerini dağıtır.
        Diğer gelmeyen öğretmenlerin atamalarını hesaba katarak çakışmaları engeller.
        """
        teacher = self.teacher_map.get(self.active_teacher_id)
        if not teacher:
            messagebox.showwarning("Uyarı", "Lütfen bir öğretmen seçin.")
            return

        date_str = self.date_var.get().strip()
        day_name = self.day_var.get()
        count_per_lesson = self.teachers_per_lesson_var.get()
        allow_branch_peers = self.allow_branch_peers_var.get()

        self.current_week_start = self.sub_service._ensure_week_start(date_str)

        # Diğer gelmeyenlerin atamalarını topla
        other_subs = []
        for tid, s_list in self.assignments_cache.items():
            if tid != teacher.id:
                other_subs.extend(s_list)

        auto_subs = self.sub_service.auto_assign_substitutions(
            date_str=date_str,
            day_name=day_name,
            absent_teacher_id=teacher.id,
            week_start=self.current_week_start,
            teachers_per_lesson=count_per_lesson,
            exclude_teacher_ids=[at.id for at in self.absent_teachers],
            active_substitutions=other_subs,
            allow_branch_peers_ek_ders=allow_branch_peers
        )

        self.assignments_cache[teacher.id] = auto_subs
        self._render_active_teacher_lessons()

        assigned_count = sum(1 for s in auto_subs if s.duty_teacher_id)
        messagebox.showinfo(
            "Eşleştirme Tamamlandı",
            f"'{teacher.name}' isimli öğretmenin {len(auto_subs)} ders saatine "
            f"{assigned_count} görevlendirme çakışmasız yapıldı."
        )

    def _collect_current_rows(self) -> List[SubstitutionAssignment]:
        teacher = self.teacher_map.get(self.active_teacher_id)
        if not teacher:
            return []

        date_str = self.date_var.get().strip()
        assignments = []

        for row in self.period_rows:
            assigned_teachers = []
            for s in row["slots"]:
                sel = s["var"].get()
                chosen_t = row["opt_map"].get(sel)
                if chosen_t and chosen_t not in assigned_teachers:
                    assigned_teachers.append(chosen_t)

            if assigned_teachers:
                for t in assigned_teachers:
                    is_ek = is_same_branch(t.branch, teacher.branch)
                    note = f"İkame Görevlendirme: {t.name}"
                    if is_ek:
                        note += " (⭐ Ek Ders Hak Eder - Branş Öğretmeni)"
                    sub = SubstitutionAssignment(
                        date_str=date_str,
                        period=row["period"],
                        absent_teacher_id=teacher.id,
                        class_name=row["lesson"].class_name,
                        subject_code=row["lesson"].subject_code,
                        duty_teacher_id=t.id,
                        is_ek_ders=is_ek,
                        notes=note
                    )
                    assignments.append(sub)
            else:
                sub = SubstitutionAssignment(
                    date_str=date_str,
                    period=row["period"],
                    absent_teacher_id=teacher.id,
                    class_name=row["lesson"].class_name,
                    subject_code=row["lesson"].subject_code,
                    duty_teacher_id=None,
                    is_ek_ders=False,
                    notes="Atanmadı"
                )
                assignments.append(sub)

        return assignments

    # --- Kaydetme ve Çıktı İşlemleri ---
    def save_assignments(self):
        self._save_current_rows_to_cache()
        date_str = self.date_var.get().strip()
        all_subs = self._get_all_in_memory_assignments()

        if not all_subs:
            messagebox.showwarning("Uyarı", "Kaydedilecek görevlendirme bulunamadı.")
            return

        # Bu tarihte kayıtlı olan tüm gelmeyen öğretmenlerimizin eski ikamelerini temizle
        saved_absent_ids = set(self.assignments_cache.keys())
        existing = self.db.get_substitutions_for_date(date_str)
        for s in existing:
            if s.absent_teacher_id in saved_absent_ids:
                self.db.delete_substitution(s.id)

        # Yeni görevlendirmeleri kaydet
        for s in all_subs:
            self.db.save_substitution(s)

        # Her bir gelmeyen öğretmen için devam takip kaydını ve fişini güncelle
        slips_dir = Path("exports/slips")
        slips_dir.mkdir(parents=True, exist_ok=True)

        for teacher in self.absent_teachers:
            t_subs = self.assignments_cache.get(teacher.id, [])
            status = self.teacher_absence_status.get(teacher.id, "Raporlu")

            busy_periods = sorted(list({s.period for s in t_subs}))
            periods_str = ", ".join(map(str, busy_periods)) + f" ({len(busy_periods)} Saat)" if busy_periods else "Tüm Gün"
            lessons_str = ", ".join([f"{s.class_name} ({s.subject_code})" for s in t_subs])

            safe_name = teacher.name.replace(" ", "_")
            slip_file = slips_dir / f"Gorevlendirme_{date_str}_{safe_name}.html"
            slip_pdf = slips_dir / f"Gorevlendirme_{date_str}_{safe_name}.pdf"
            saved_slip_path = ""

            try:
                self.sub_service.export_substitution_html(
                    output_path=str(slip_file),
                    date_str=date_str,
                    day_name=self.day_var.get(),
                    absent_teacher=teacher,
                    assignments=t_subs
                )
                saved_slip_path = str(slip_file.resolve())
                try:
                    self.sub_service.export_substitution_pdf(
                        output_path=str(slip_pdf),
                        date_str=date_str,
                        day_name=self.day_var.get(),
                        absent_teacher=teacher,
                        assignments=t_subs
                    )
                    saved_slip_path = str(slip_pdf.resolve())
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"Fiş arşivleme hatası: {e}")

            self.db.delete_attendance_for_teacher_date(teacher.id, date_str)
            att_rec = AttendanceRecord(
                date_str=date_str,
                teacher_id=teacher.id,
                teacher_name=teacher.name,
                branch=teacher.branch,
                status=status,
                periods_missed=periods_str,
                lessons_missed=lessons_str,
                slip_path=saved_slip_path,
                notes=f"Çoklu boş ders ikamesi işlendi ({len(t_subs)} ders)."
            )
            self.db.save_attendance_record(att_rec)

        self._update_duty_banner()

        messagebox.showinfo(
            "Başarılı",
            f"Toplam {len(self.absent_teachers)} gelmeyen öğretmenin {len(all_subs)} ders saati "
            f"görevlendirmesi başarıyla veritabanına ve devam-takip çizelgesine kaydedildi!\n\n"
            f"Fişler 'exports/slips' klasörüne arşivlendi."
        )

    def export_daily_pdf(self):
        all_subs = self._get_all_in_memory_assignments()
        if not all_subs:
            messagebox.showwarning("Uyarı", "Çıktı alınacak görevlendirme bulunamadı.")
            return

        date_str = self.date_var.get().strip()
        day_name = self.day_var.get()
        default_name = f"Gunluk_Toplu_Bos_Ders_{date_str}.pdf"
        out_path = filedialog.asksaveasfilename(
            title="Günlük Toplu Görevlendirme Çizelgesini PDF Olarak Kaydet",
            initialfile=default_name,
            defaultextension=".pdf",
            filetypes=[("PDF Dosyası", "*.pdf")]
        )
        if not out_path:
            return

        try:
            self.sub_service.export_daily_substitutions_pdf(
                output_path=out_path,
                date_str=date_str,
                day_name=day_name,
                assignments=all_subs
            )
            messagebox.showinfo("Başarılı", f"Günlük toplu PDF belgesi oluşturuldu:\n{out_path}")
            if os.name == "nt":
                os.startfile(out_path)
        except Exception as e:
            logger.error(f"Toplu PDF hatası: {e}", exc_info=True)
            messagebox.showerror("Hata", f"PDF belgesi oluşturulamadı:\n{e}")

    def export_daily_html(self):
        all_subs = self._get_all_in_memory_assignments()
        if not all_subs:
            messagebox.showwarning("Uyarı", "Çıktı alınacak görevlendirme bulunamadı.")
            return

        date_str = self.date_var.get().strip()
        day_name = self.day_var.get()
        default_name = f"Gunluk_Toplu_Bos_Ders_{date_str}.html"
        out_path = filedialog.asksaveasfilename(
            title="Günlük Toplu Görevlendirme Çizelgesini HTML Olarak Kaydet",
            initialfile=default_name,
            defaultextension=".html",
            filetypes=[("HTML Dosyası", "*.html")]
        )
        if not out_path:
            return

        try:
            self.sub_service.export_daily_substitutions_html(
                output_path=out_path,
                date_str=date_str,
                day_name=day_name,
                assignments=all_subs
            )
            messagebox.showinfo("Başarılı", f"HTML belgesi oluşturuldu:\n{out_path}")
            webbrowser.open(f"file://{os.path.abspath(out_path)}")
        except Exception as e:
            logger.error(f"Toplu HTML hatası: {e}", exc_info=True)
            messagebox.showerror("Hata", f"HTML belgesi oluşturulamadı:\n{e}")

    def export_pdf(self):
        teacher = self.teacher_map.get(self.active_teacher_id)
        if not teacher:
            messagebox.showwarning("Uyarı", "Lütfen bir öğretmen seçin.")
            return

        self._save_current_rows_to_cache()
        assignments = self.assignments_cache.get(teacher.id, [])
        if not assignments:
            messagebox.showwarning("Uyarı", "Çıktı alınacak ders bulunamadı.")
            return

        date_str = self.date_var.get().strip()
        day_name = self.day_var.get()
        default_name = f"Bos_Ders_Gorevlendirme_{date_str}_{teacher.name.replace(' ', '_')}.pdf"
        out_path = filedialog.asksaveasfilename(
            title="Kişisel Görevlendirme Fişini PDF Olarak Kaydet",
            initialfile=default_name,
            defaultextension=".pdf",
            filetypes=[("PDF Dosyası", "*.pdf")]
        )
        if not out_path:
            return

        try:
            self.sub_service.export_substitution_pdf(
                output_path=out_path,
                date_str=date_str,
                day_name=day_name,
                absent_teacher=teacher,
                assignments=assignments
            )
            messagebox.showinfo("Başarılı", f"PDF belgesi oluşturuldu:\n{out_path}")
            if os.name == "nt":
                os.startfile(out_path)
        except Exception as e:
            logger.error(f"Kişisel PDF hatası: {e}", exc_info=True)
            messagebox.showerror("Hata", f"PDF belgesi oluşturulamadı:\n{e}")

    def export_html(self):
        teacher = self.teacher_map.get(self.active_teacher_id)
        if not teacher:
            messagebox.showwarning("Uyarı", "Lütfen bir öğretmen seçin.")
            return

        self._save_current_rows_to_cache()
        assignments = self.assignments_cache.get(teacher.id, [])
        if not assignments:
            messagebox.showwarning("Uyarı", "Çıktı alınacak ders bulunamadı.")
            return

        date_str = self.date_var.get().strip()
        day_name = self.day_var.get()
        default_name = f"Bos_Ders_Gorevlendirme_{date_str}_{teacher.name.replace(' ', '_')}.html"
        out_path = filedialog.asksaveasfilename(
            title="Kişisel Görevlendirme Fişini HTML Olarak Kaydet",
            initialfile=default_name,
            defaultextension=".html",
            filetypes=[("HTML Dosyası", "*.html")]
        )
        if not out_path:
            return

        try:
            self.sub_service.export_substitution_html(
                output_path=out_path,
                date_str=date_str,
                day_name=day_name,
                absent_teacher=teacher,
                assignments=assignments
            )
            messagebox.showinfo("Başarılı", f"HTML belgesi oluşturuldu:\n{out_path}")
            webbrowser.open(f"file://{os.path.abspath(out_path)}")
        except Exception as e:
            logger.error(f"Kişisel HTML hatası: {e}", exc_info=True)
            messagebox.showerror("Hata", f"HTML belgesi oluşturulamadı:\n{e}")

    def preview_daily(self):
        """Günlük toplu görevlendirmeyi Evrensel Önizleme ve Yazdırma penceresinde açar."""
        from ui.preview_dialog import PrintPreviewDialog
        import tempfile

        all_subs = self._get_all_in_memory_assignments()
        if not all_subs:
            messagebox.showwarning("Uyarı", "Önizleme ve çıktı için görevlendirilmiş ders bulunamadı.", parent=self)
            return

        date_str = self.date_var.get().strip()
        day_name = self.day_var.get()
        default_name = f"Gunluk_Toplu_Bos_Ders_{date_str}"

        tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp_pdf.close()
        tmp_html = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8")
        tmp_html.close()

        try:
            self.sub_service.export_daily_substitutions_pdf(
                output_path=tmp_pdf.name,
                date_str=date_str,
                day_name=day_name,
                assignments=all_subs
            )
            self.sub_service.export_daily_substitutions_html(
                output_path=tmp_html.name,
                date_str=date_str,
                day_name=day_name,
                assignments=all_subs
            )
            PrintPreviewDialog(
                parent=self,
                title=f"Günlük Toplu İkame Çizelgesi Önizleme ({date_str})",
                pdf_path=tmp_pdf.name,
                html_path=tmp_html.name,
                default_filename=default_name
            )
        except Exception as e:
            logger.error(f"Toplu önizleme hatası: {e}", exc_info=True)
            messagebox.showerror("Hata", f"Baskı önizleme oluşturulamadı:\n{e}", parent=self)

    def preview_single(self):
        """Seçili öğretmenin kişisel görevlendirme fişini Evrensel Önizleme ve Yazdırma penceresinde açar."""
        from ui.preview_dialog import PrintPreviewDialog
        import tempfile

        teacher = self.teacher_map.get(self.active_teacher_id)
        if not teacher:
            messagebox.showwarning("Uyarı", "Lütfen bir öğretmen seçin.", parent=self)
            return

        self._save_current_rows_to_cache()
        assignments = self.assignments_cache.get(teacher.id, [])
        if not assignments:
            messagebox.showwarning("Uyarı", f"{teacher.name} için görevlendirme kaydı bulunamadı.", parent=self)
            return

        date_str = self.date_var.get().strip()
        day_name = self.day_var.get()
        default_name = f"Bos_Ders_Gorevlendirme_{date_str}_{teacher.name.replace(' ', '_')}"

        tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp_pdf.close()
        tmp_html = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8")
        tmp_html.close()

        try:
            self.sub_service.export_substitution_pdf(
                output_path=tmp_pdf.name,
                date_str=date_str,
                day_name=day_name,
                absent_teacher=teacher,
                assignments=assignments
            )
            self.sub_service.export_substitution_html(
                output_path=tmp_html.name,
                date_str=date_str,
                day_name=day_name,
                absent_teacher=teacher,
                assignments=assignments
            )
            PrintPreviewDialog(
                parent=self,
                title=f"Kişisel Görevlendirme Fişi Önizleme - {teacher.name}",
                pdf_path=tmp_pdf.name,
                html_path=tmp_html.name,
                default_filename=default_name
            )
        except Exception as e:
            logger.error(f"Kişisel fiş önizleme hatası: {e}", exc_info=True)
            messagebox.showerror("Hata", f"Baskı önizleme oluşturulamadı:\n{e}", parent=self)

    def open_whatsapp_dialog(self):
        """Atanan ikame ve boş ders görevlerini WhatsApp Bildirim Merkezinde açar."""
        all_subs = self._get_all_in_memory_assignments()
        if not all_subs:
            messagebox.showwarning("Uyarı", "WhatsApp bildirimi göndermek için görevlendirilmiş ders bulunamadı.", parent=self)
            return

        date_str = self.date_var.get().strip()
        day_name = self.day_var.get()
        school_info = self.db.get_school_info()
        school_name = school_info.name if school_info else "Okul"

        tasks = []
        for s in all_subs:
            if s.duty_teacher_id:
                duty_t = self.teacher_map.get(s.duty_teacher_id)
                abs_t = self.teacher_map.get(s.absent_teacher_id)
                tasks.append({
                    "period": s.period,
                    "class": s.class_name,
                    "subject": s.subject_code,
                    "duty_teacher": duty_t.name if duty_t else "Öğretmen",
                    "absent_teacher": abs_t.name if abs_t else "",
                    "is_ek_ders": s.is_ek_ders,
                    "phone": getattr(duty_t, "phone", "") if duty_t else ""
                })

        WhatsAppNotifyDialog(self, school_name, date_str, day_name, tasks)


