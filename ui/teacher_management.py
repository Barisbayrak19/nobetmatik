"""
Öğretmen Yönetimi ve 360° Takip Paneli (Model 3: Master-Detail Architecture)
Öğretmen listesi, nöbet adalet istatistikleri, devam-devamsızlık geçmişi,
haftalık ders programı ve ay sonu ikame / ek ders hak ediş takibi.
"""
import os
import datetime
import webbrowser
from typing import Callable, Optional, List, Dict, Any

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from core.models import Teacher, Assignment, AttendanceRecord, TeacherLesson
from core.database import Database
from core.config import WEEKDAYS, EXPORTS_DIR
from core.logger import logger
from logic.substitution_service import get_teacher_substitutions_summary, is_same_branch
from ui.ek_ders_dialog import EkDersMonthlySummaryDialog, TURKISH_MONTHS
from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_PRIMARY_HOVER,
    COLOR_SUCCESS, COLOR_DANGER, COLOR_BORDER, COLOR_BORDER_STRONG,
    COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, FONT_FAMILY,
    create_modern_button
)


class TeacherEditModal(tk.Toplevel):
    """
    Öğretmen Ekleme ve Düzenleme Modalı (Temiz, Kaydırılabilir Form)
    """
    def __init__(
        self,
        parent: tk.Widget,
        db: Database,
        teacher: Optional[Teacher] = None,
        on_saved: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent)
        self.db = db
        self.teacher = teacher
        self.on_saved = on_saved

        self.title("Öğretmen Bilgilerini Düzenle" if teacher else "Yeni Öğretmen Ekle")
        self.geometry("560x680")
        self.minsize(520, 600)
        self.configure(bg=COLOR_BG)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self.name_var = tk.StringVar(value=teacher.name if teacher else "")
        self.branch_var = tk.StringVar(value=teacher.branch if teacher else "")
        self.phone_var = tk.StringVar(value=getattr(teacher, "phone", "") if teacher else "")
        self.shift_var = tk.StringVar(value=getattr(teacher, "shift_group", "Tümü") if teacher else "Tümü")
        self.active_var = tk.BooleanVar(value=teacher.is_active if teacher else True)
        self.notes_var = tk.StringVar(value=teacher.notes if teacher else "")
        self.seniority_var = tk.IntVar(value=getattr(teacher, "seniority_years", 0) if teacher else 0)
        self.is_primary_var = tk.BooleanVar(value=getattr(teacher, "is_primary_school", True) if teacher else True)

        self.is_exempt_var = tk.BooleanVar(value=getattr(teacher, "is_exempt", False) if teacher else False)
        self.exemption_reason_var = tk.StringVar(value=getattr(teacher, "exemption_reason", "") if teacher else "")
        self.exemption_requested_var = tk.BooleanVar(value=getattr(teacher, "exemption_requested", False) if teacher else False)

        unavail = teacher.unavailable_days if teacher else []
        self.day_vars = {day: tk.BooleanVar(value=day in unavail) for day in WEEKDAYS}

        pref = getattr(teacher, "preferred_days", []) if teacher else []
        self.pref_day_vars = {day: tk.BooleanVar(value=day in pref) for day in WEEKDAYS}

        self._build_ui()

    def _build_ui(self):
        # Üst Başlık
        hdr = tk.Frame(self, bg="#1E3A8A", padx=16, pady=12)
        hdr.pack(fill="x", side="top")
        tk.Label(
            hdr,
            text=f"✏️ {self.teacher.name} Bilgilerini Düzenle" if self.teacher else "➕ Yeni Öğretmen Ekle",
            font=(FONT_FAMILY, 11, "bold"),
            bg="#1E3A8A",
            fg="#FFFFFF"
        ).pack(anchor="w")

        # Kaydırılabilir İçerik Alanı
        canvas = tk.Canvas(self, bg=COLOR_BG, highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scroll_content = tk.Frame(canvas, bg=COLOR_BG, padx=16, pady=12)

        scroll_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_win = canvas.create_window((0, 0), window=scroll_content, anchor="nw")

        def _on_canvas_configure(e):
            canvas.itemconfig(canvas_win, width=e.width)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.configure(yscrollcommand=sb.set)

        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # 1. Temel Bilgiler Kartı
        grp_basic = tk.LabelFrame(scroll_content, text=" 👤 Temel Bilgiler ", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, padx=12, pady=10)
        grp_basic.pack(fill="x", pady=(0, 10))

        tk.Label(grp_basic, text="Ad Soyad:*", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).pack(anchor="w")
        self.entry_name = ttk.Entry(grp_basic, textvariable=self.name_var, font=(FONT_FAMILY, 9))
        self.entry_name.pack(fill="x", pady=(2, 6))

        tk.Label(grp_basic, text="Branş:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).pack(anchor="w")
        ttk.Entry(grp_basic, textvariable=self.branch_var, font=(FONT_FAMILY, 9)).pack(fill="x", pady=(2, 6))

        f_row = tk.Frame(grp_basic, bg=COLOR_CARD)
        f_row.pack(fill="x", pady=(2, 6))

        f_phone = tk.Frame(f_row, bg=COLOR_CARD)
        f_phone.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Label(f_phone, text="Telefon (WhatsApp):", font=(FONT_FAMILY, 8, "bold"), bg=COLOR_CARD).pack(anchor="w")
        ttk.Entry(f_phone, textvariable=self.phone_var, font=(FONT_FAMILY, 9)).pack(fill="x", pady=(2, 0))

        f_shift = tk.Frame(f_row, bg=COLOR_CARD)
        f_shift.pack(side="left", fill="x", expand=True)
        tk.Label(f_shift, text="Devre:", font=(FONT_FAMILY, 8, "bold"), bg=COLOR_CARD).pack(anchor="w")
        cb_shift = ttk.Combobox(f_shift, textvariable=self.shift_var, values=["Tümü", "Sabahçı", "Öğlenci"], state="readonly")
        cb_shift.pack(fill="x", pady=(2, 0))

        f_sen = tk.Frame(grp_basic, bg=COLOR_CARD)
        f_sen.pack(fill="x", pady=(4, 6))
        tk.Label(f_sen, text="Hizmet Yılı:", font=(FONT_FAMILY, 8, "bold"), bg=COLOR_CARD).pack(side="left", padx=(0, 6))
        ttk.Spinbox(f_sen, from_=0, to=50, textvariable=self.seniority_var, width=5).pack(side="left")
        ttk.Checkbutton(f_sen, text="Kadrosu Bu Okulda", variable=self.is_primary_var).pack(side="right")

        ttk.Checkbutton(grp_basic, text="Aktif Öğretmen (Nöbet ve ikame dağıtımında listelenir)", variable=self.active_var).pack(anchor="w", pady=(4, 0))

        # 2. Mevzuat & Muafiyet Kartı
        grp_exempt = tk.LabelFrame(scroll_content, text=" ⚖️ Mevzuat & Muafiyet Durumu ", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, padx=12, pady=10, fg="#B45309")
        grp_exempt.pack(fill="x", pady=(0, 10))

        ttk.Checkbutton(grp_exempt, text="⛔ Nöbetten Kesin Muaf (Nöbet havuzuna dahil edilmez)", variable=self.is_exempt_var).pack(anchor="w", pady=(0, 4))

        tk.Label(grp_exempt, text="Muafiyet / Mazeret Gerekçesi:", font=(FONT_FAMILY, 8), bg=COLOR_CARD).pack(anchor="w")
        cb_exempt_reasons = [
            "İdareci (Müdür / Müdür Yardımcısı)",
            "YEĞİTEK Okul Sorumlusu (BTR)",
            "Hamilelik / Süt İzni (Mevzuat)",
            "Engelli Öğretmen / Sağlık Raporu",
            "Engelli Çocuğu / Bakmakla Yükümlü Birey",
            "20/25 Yıl Kıdem Muafiyeti",
            "Başka Kurumda Görevli / Görevlendirme",
            "Yönetici İzni / Diğer Yasal Mazeret"
        ]
        cb_reason = ttk.Combobox(grp_exempt, textvariable=self.exemption_reason_var, values=cb_exempt_reasons, font=(FONT_FAMILY, 8))
        cb_reason.bind("<<ComboboxSelected>>", lambda e: self.is_exempt_var.set(True) if self.exemption_reason_var.get() else None)
        cb_reason.pack(fill="x", pady=(2, 4))

        ttk.Checkbutton(grp_exempt, text="20/25 Yıl Kıdem Muafiyet Talebi Var (İstekli)", variable=self.exemption_requested_var).pack(anchor="w")

        # 3. Gün Tercihleri ve Engeller
        f_days = tk.Frame(scroll_content, bg=COLOR_BG)
        f_days.pack(fill="x", pady=(0, 10))

        grp_pref = tk.LabelFrame(f_days, text=" ⭐ Tercih Ettiği Günler ", font=(FONT_FAMILY, 8, "bold"), bg=COLOR_CARD, padx=8, pady=6, fg="#15803D")
        grp_pref.pack(side="left", fill="both", expand=True, padx=(0, 4))
        for day in WEEKDAYS:
            ttk.Checkbutton(grp_pref, text=day, variable=self.pref_day_vars[day]).pack(anchor="w", pady=1)

        grp_unavail = tk.LabelFrame(f_days, text=" 🚫 Müsait Olmadığı Günler ", font=(FONT_FAMILY, 8, "bold"), bg=COLOR_CARD, padx=8, pady=6, fg="#DC2626")
        grp_unavail.pack(side="left", fill="both", expand=True, padx=(4, 0))
        for day in WEEKDAYS:
            ttk.Checkbutton(grp_unavail, text=day, variable=self.day_vars[day]).pack(anchor="w", pady=1)

        # 4. Notlar
        tk.Label(scroll_content, text="Notlar / İdari Açıklama:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_BG).pack(anchor="w")
        ttk.Entry(scroll_content, textvariable=self.notes_var, font=(FONT_FAMILY, 9)).pack(fill="x", pady=(2, 12))

        # Alt Butonlar
        f_btns = tk.Frame(self, bg=COLOR_BG, padx=16, pady=10)
        f_btns.pack(fill="x", side="bottom")

        create_modern_button(f_btns, text="💾 Kaydet", variant="success", command=self._save).pack(side="right", padx=(6, 0))
        create_modern_button(f_btns, text="İptal", variant="default", command=self.destroy).pack(side="right")

    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Uyarı", "Lütfen öğretmen adını giriniz.", parent=self)
            return

        t = self.teacher or Teacher()
        t.name = name
        t.branch = self.branch_var.get().strip()
        t.phone = self.phone_var.get().strip()
        t.shift_group = self.shift_var.get().strip()
        t.is_active = self.active_var.get()
        t.notes = self.notes_var.get().strip()
        t.is_exempt = self.is_exempt_var.get()
        t.exemption_reason = self.exemption_reason_var.get().strip()
        t.seniority_years = self.seniority_var.get()
        t.exemption_requested = self.exemption_requested_var.get()
        t.is_primary_school = self.is_primary_var.get()
        t.unavailable_days = [day for day, var in self.day_vars.items() if var.get()]
        t.preferred_days = [day for day, var in self.pref_day_vars.items() if var.get()]

        self.db.save_teacher(t)
        self.destroy()
        if self.on_saved:
            self.on_saved()


class TeacherManagementView(ttk.Frame):
    """
    Model 3 Master-Detail: Öğretmen Yönetimi ve 360° Takip Paneli
    """
    def __init__(self, parent: tk.Widget, db: Database, on_data_changed: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.db = db
        self.on_data_changed = on_data_changed

        self.search_var = tk.StringVar()
        self.filter_var = tk.StringVar(value="Tümü")

        self.selected_teacher: Optional[Teacher] = None
        self.teachers_cache: List[Teacher] = []

        now = datetime.datetime.now()
        cur_month_idx = now.month - 1
        self.selected_month_var = tk.StringVar(value=TURKISH_MONTHS[cur_month_idx][1])
        self.selected_year_var = tk.StringVar(value=str(now.year))

        self._build_ui()
        self.load_teachers()

    def _build_ui(self):
        # PanedWindow: Sol Liste (Master) + Sağ Detay (Detail)
        self.paned = ttk.PanedWindow(self, orient="horizontal")
        self.paned.pack(fill="both", expand=True)

        # =====================================================================
        # SOL MASTER PANELİ (Öğretmen Listesi ve Arama)
        # =====================================================================
        self.left_frame = ttk.Frame(self.paned, padding=(10, 10, 6, 10))
        self.paned.add(self.left_frame, weight=2)

        # Arama ve Filtre
        search_bar = ttk.Frame(self.left_frame)
        search_bar.pack(fill="x", pady=(0, 6))

        ttk.Label(search_bar, text="🔍", font=(FONT_FAMILY, 10, "bold")).pack(side="left", padx=(0, 4))
        ent_search = ttk.Entry(search_bar, textvariable=self.search_var, font=(FONT_FAMILY, 9))
        ent_search.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.search_var.trace_add("write", lambda *args: self.apply_filter())

        cb_filter = ttk.Combobox(
            search_bar,
            textvariable=self.filter_var,
            values=["Tümü", "Aktifler", "Pasifler", "Muaf Olanlar", "Ek Ders Alanlar"],
            state="readonly",
            width=13
        )
        cb_filter.pack(side="right")
        cb_filter.bind("<<ComboboxSelected>>", lambda e: self.apply_filter())

        # Ağaç Tablosu (Treeview)
        table_container = ttk.Frame(self.left_frame)
        table_container.pack(fill="both", expand=True)

        cols = ("name", "branch", "status")
        self.tree = ttk.Treeview(table_container, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("name", text="Adı Soyadı")
        self.tree.heading("branch", text="Branşı")
        self.tree.heading("status", text="Durum")

        self.tree.column("name", width=140)
        self.tree.column("branch", width=95)
        self.tree.column("status", width=70, anchor="center")

        sb_tree = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb_tree.set)

        self.tree.pack(side="left", fill="both", expand=True)
        sb_tree.pack(side="right", fill="y")

        self.tree.tag_configure("even", background="#FFFFFF")
        self.tree.tag_configure("odd", background="#F8FAFC")
        self.tree.tag_configure("exempt", foreground="#B45309")
        self.tree.tag_configure("inactive", foreground="#94A3B8")

        self.tree.bind("<<TreeviewSelect>>", self._on_teacher_selected)
        self.tree.bind("<Double-Button-1>", lambda e: self.edit_teacher())

        # Sol Alt Bar
        left_bottom = ttk.Frame(self.left_frame, padding=(0, 8, 0, 0))
        left_bottom.pack(fill="x", side="bottom")

        btn_add = create_modern_button(left_bottom, text="➕ Yeni", variant="primary", command=self.add_teacher)
        btn_add.pack(side="left", padx=(0, 4))

        btn_toggle = create_modern_button(left_bottom, text="🔄 Aktif/Pasif", variant="default", command=self.toggle_active)
        btn_toggle.pack(side="left", padx=(0, 4))

        btn_del = create_modern_button(left_bottom, text="🗑️", variant="danger", command=self.delete_teacher)
        btn_del.pack(side="left")

        self.lbl_count = ttk.Label(left_bottom, text="0 öğretmen", font=(FONT_FAMILY, 8, "italic"))
        self.lbl_count.pack(side="right")

        # =====================================================================
        # SAĞ DETAY PANELİ (360° Öğretmen Detay Kartı)
        # =====================================================================
        self.right_frame = ttk.Frame(self.paned, padding=(6, 10, 10, 10))
        self.paned.add(self.right_frame, weight=5)

        # 1. Hero Başlık Kartı
        self.hero_card = tk.Frame(self.right_frame, bg="#FFFFFF", relief="solid", bd=1, padx=16, pady=12)
        self.hero_card.pack(fill="x", pady=(0, 8))

        f_hero_left = tk.Frame(self.hero_card, bg="#FFFFFF")
        f_hero_left.pack(side="left", fill="both", expand=True)

        self.lbl_hero_name = tk.Label(
            f_hero_left,
            text="Lütfen Bir Öğretmen Seçiniz",
            font=(FONT_FAMILY, 13, "bold"),
            bg="#FFFFFF",
            fg=COLOR_TEXT_MAIN
        )
        self.lbl_hero_name.pack(anchor="w")

        self.lbl_hero_meta = tk.Label(
            f_hero_left,
            text="Detayları görüntülemek için sol taraftaki listeden seçim yapabilirsiniz.",
            font=(FONT_FAMILY, 9),
            bg="#FFFFFF",
            fg=COLOR_TEXT_MUTED
        )
        self.lbl_hero_meta.pack(anchor="w", pady=(2, 0))

        f_hero_right = tk.Frame(self.hero_card, bg="#FFFFFF")
        f_hero_right.pack(side="right")

        self.btn_edit = create_modern_button(
            f_hero_right,
            text="✏️ Bilgileri Düzenle",
            variant="default",
            command=self.edit_teacher
        )
        self.btn_edit.pack(side="right", padx=(6, 0))

        self.btn_whatsapp = create_modern_button(
            f_hero_right,
            text="💬 WhatsApp",
            variant="success",
            command=self._send_whatsapp
        )
        self.btn_whatsapp.pack(side="right")

        # 2. Sekmeli Detay Notebook
        self.notebook = ttk.Notebook(self.right_frame)
        self.notebook.pack(fill="both", expand=True)

        # SEKME 1: Nöbet İstatistiği & Tercihler
        self.tab_duties = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_duties, text="  🛡️ Nöbet İstatistiği  ")
        self._build_tab_duties()

        # SEKME 2: Devam-Devamsızlık
        self.tab_attendance = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_attendance, text="  📋 Devam-Devamsızlık  ")
        self._build_tab_attendance()

        # SEKME 3: Ders Programı
        self.tab_timetable = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_timetable, text="  📅 Ders Programı  ")
        self._build_tab_timetable()

        # SEKME 4: İkame & Ek Ders Takibi
        self.tab_ek_ders = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_ek_ders, text="  💰 İkame & Ek Ders Takibi  ")
        self._build_tab_ek_ders()

    # -------------------------------------------------------------------------
    # SEKME YAPILANDIRMALARI
    # -------------------------------------------------------------------------

    def _build_tab_duties(self):
        # KPI Barı
        kpi_bar = tk.Frame(self.tab_duties, bg=COLOR_BG)
        kpi_bar.pack(fill="x", pady=(0, 8))

        self.card_duty_count = tk.Label(kpi_bar, text="Toplam Nöbet: 0", font=(FONT_FAMILY, 10, "bold"), bg="#DBEAFE", fg="#1E40AF", padx=10, pady=6, relief="solid", bd=1)
        self.card_duty_count.pack(side="left", padx=(0, 8))

        self.card_duty_status = tk.Label(kpi_bar, text="Adalet Dengesi: -", font=(FONT_FAMILY, 9, "bold"), bg="#F1F5F9", fg="#334155", padx=10, pady=6, relief="solid", bd=1)
        self.card_duty_status.pack(side="left", padx=(0, 8))

        # Tercihler ve Engeller Kartı
        self.lbl_duty_prefs = tk.Label(
            self.tab_duties,
            text="⭐ Tercih Edilen Günler: -\n🚫 Müsait Olmadığı Günler: -",
            font=(FONT_FAMILY, 9),
            justify="left",
            bg=COLOR_CARD,
            padx=12,
            pady=8,
            relief="solid",
            bd=1
        )
        self.lbl_duty_prefs.pack(fill="x", pady=(0, 8))

        # Nöbet Geçmişi Listesi
        ttk.Label(self.tab_duties, text="📌 Bu Dönem Görevlendirildiği Nöbetler:", font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", pady=(4, 2))
        list_f = ttk.Frame(self.tab_duties)
        list_f.pack(fill="both", expand=True)

        self.tree_duties = ttk.Treeview(list_f, columns=("week", "day", "location", "slot"), show="headings", selectmode="browse")
        self.tree_duties.heading("week", text="Hafta Başlangıcı")
        self.tree_duties.heading("day", text="Gün")
        self.tree_duties.heading("location", text="Nöbet Bölgesi / Kat")
        self.tree_duties.heading("slot", text="Görev Sırası")

        self.tree_duties.column("week", width=110, anchor="center")
        self.tree_duties.column("day", width=100, anchor="center")
        self.tree_duties.column("location", width=180)
        self.tree_duties.column("slot", width=90, anchor="center")

        sb = ttk.Scrollbar(list_f, orient="vertical", command=self.tree_duties.yview)
        self.tree_duties.configure(yscrollcommand=sb.set)
        self.tree_duties.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _build_tab_attendance(self):
        kpi_bar = tk.Frame(self.tab_attendance, bg=COLOR_BG)
        kpi_bar.pack(fill="x", pady=(0, 8))

        self.card_att_count = tk.Label(kpi_bar, text="Toplam Devamsızlık: 0 Gün", font=(FONT_FAMILY, 10, "bold"), bg="#FEE2E2", fg="#B91C1C", padx=10, pady=6, relief="solid", bd=1)
        self.card_att_count.pack(side="left", padx=(0, 8))

        # Devamsızlık Listesi
        ttk.Label(self.tab_attendance, text="📋 Kayıtlı Devamsızlık / Rapor / Sevk Geçmişi:", font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", pady=(4, 2))
        list_f = ttk.Frame(self.tab_attendance)
        list_f.pack(fill="both", expand=True)

        self.tree_att = ttk.Treeview(list_f, columns=("date", "status", "periods", "notes"), show="headings", selectmode="browse")
        self.tree_att.heading("date", text="Tarih")
        self.tree_att.heading("status", text="Mazeret Durumu")
        self.tree_att.heading("periods", text="Süre / Ders")
        self.tree_att.heading("notes", text="Açıklama / Fiş")

        self.tree_att.column("date", width=100, anchor="center")
        self.tree_att.column("status", width=130, anchor="center")
        self.tree_att.column("periods", width=110, anchor="center")
        self.tree_att.column("notes", width=220)

        sb = ttk.Scrollbar(list_f, orient="vertical", command=self.tree_att.yview)
        self.tree_att.configure(yscrollcommand=sb.set)
        self.tree_att.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _build_tab_timetable(self):
        ttk.Label(self.tab_timetable, text="📅 Haftalık Ders Programı (Saatlik Dağılım):", font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", pady=(0, 4))
        list_f = ttk.Frame(self.tab_timetable)
        list_f.pack(fill="both", expand=True)

        cols = ["period"] + WEEKDAYS
        self.tree_tt = ttk.Treeview(list_f, columns=cols, show="headings", selectmode="browse")
        self.tree_tt.heading("period", text="Ders Saati")
        self.tree_tt.column("period", width=80, anchor="center")

        for d in WEEKDAYS:
            self.tree_tt.heading(d, text=d)
            self.tree_tt.column(d, width=100, anchor="center")

        sb = ttk.Scrollbar(list_f, orient="vertical", command=self.tree_tt.yview)
        self.tree_tt.configure(yscrollcommand=sb.set)
        self.tree_tt.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.tree_tt.tag_configure("even", background="#FFFFFF")
        self.tree_tt.tag_configure("odd", background="#F8FAFC")

    def _build_tab_ek_ders(self):
        # Üst Ay Seçici ve Genel İcmal Butonu
        top_ctrl = tk.Frame(self.tab_ek_ders, bg=COLOR_BG)
        top_ctrl.pack(fill="x", pady=(0, 8))

        tk.Label(top_ctrl, text="Ay:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_BG).pack(side="left", padx=(0, 4))
        cb_m = ttk.Combobox(top_ctrl, textvariable=self.selected_month_var, values=[m[1] for m in TURKISH_MONTHS], width=9, state="readonly")
        cb_m.pack(side="left", padx=(0, 8))
        cb_m.bind("<<ComboboxSelected>>", lambda e: self._load_ek_ders_details())

        tk.Label(top_ctrl, text="Yıl:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_BG).pack(side="left", padx=(0, 4))
        cb_y = ttk.Combobox(top_ctrl, textvariable=self.selected_year_var, values=["2024", "2025", "2026", "2027"], width=6, state="readonly")
        cb_y.pack(side="left", padx=(0, 12))
        cb_y.bind("<<ComboboxSelected>>", lambda e: self._load_ek_ders_details())

        btn_all = create_modern_button(
            top_ctrl,
            text="📊 Ay Sonu Tüm Okul İcmali (PDF / Excel)",
            variant="primary",
            command=self.open_all_school_summary
        )
        btn_all.pack(side="right")

        # KPI Sayaçları
        kpi_bar = tk.Frame(self.tab_ek_ders, bg=COLOR_BG)
        kpi_bar.pack(fill="x", pady=(0, 8))

        self.card_ek_total = tk.Label(kpi_bar, text="Toplam İkame: 0 Saat", font=(FONT_FAMILY, 9, "bold"), bg="#DBEAFE", fg="#1E40AF", padx=10, pady=5, relief="solid", bd=1)
        self.card_ek_total.pack(side="left", padx=(0, 6))

        self.card_ek_eligible = tk.Label(kpi_bar, text="⭐ Ek Ders Hak Ediş: 0 Saat", font=(FONT_FAMILY, 9, "bold"), bg="#DCFCE7", fg="#15803D", padx=10, pady=5, relief="solid", bd=1)
        self.card_ek_eligible.pack(side="left", padx=(0, 6))

        self.card_ek_super = tk.Label(kpi_bar, text="Nöbet Nezareti: 0 Saat", font=(FONT_FAMILY, 9, "bold"), bg="#F1F5F9", fg="#475569", padx=10, pady=5, relief="solid", bd=1)
        self.card_ek_super.pack(side="left")

        # Ders Dökümü Tablosu
        list_f = ttk.Frame(self.tab_ek_ders)
        list_f.pack(fill="both", expand=True)

        cols = ("date", "period", "class", "absent", "status", "reason")
        self.tree_ek_ders = ttk.Treeview(list_f, columns=cols, show="headings", selectmode="browse")

        self.tree_ek_ders.heading("date", text="Tarih")
        self.tree_ek_ders.heading("period", text="Ders")
        self.tree_ek_ders.heading("class", text="Sınıf")
        self.tree_ek_ders.heading("absent", text="Gelmeyen Öğretmen")
        self.tree_ek_ders.heading("status", text="Ek Ders Durumu")
        self.tree_ek_ders.heading("reason", text="Gerekçe / Açıklama")

        self.tree_ek_ders.column("date", width=90, anchor="center")
        self.tree_ek_ders.column("period", width=55, anchor="center")
        self.tree_ek_ders.column("class", width=75, anchor="center")
        self.tree_ek_ders.column("absent", width=140)
        self.tree_ek_ders.column("status", width=130, anchor="center")
        self.tree_ek_ders.column("reason", width=180)

        sb = ttk.Scrollbar(list_f, orient="vertical", command=self.tree_ek_ders.yview)
        self.tree_ek_ders.configure(yscrollcommand=sb.set)
        self.tree_ek_ders.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.tree_ek_ders.tag_configure("ek_yes", background="#DCFCE7", font=(FONT_FAMILY, 9, "bold"))
        self.tree_ek_ders.tag_configure("ek_no", background="#F8FAFC")

    # -------------------------------------------------------------------------
    # VERİ YÜKLEME VE GÜNCELLEME
    # -------------------------------------------------------------------------

    def load_teachers(self):
        self.teachers_cache = self.db.get_teachers(active_only=False)
        self.apply_filter()

    def apply_filter(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        query = self.search_var.get().strip().lower()
        filter_type = self.filter_var.get()

        count = 0
        target_item = None

        for idx, t in enumerate(self.teachers_cache):
            if filter_type == "Aktifler" and not t.is_active:
                continue
            if filter_type == "Pasifler" and t.is_active:
                continue
            if filter_type == "Muaf Olanlar" and not getattr(t, "is_exempt", False):
                continue

            if query and (query not in t.name.lower() and query not in t.branch.lower()):
                continue

            # Durum rozeti
            if not t.is_active:
                status_str = "Pasif 🔴"
                tag = "inactive"
            elif getattr(t, "is_exempt", False):
                status_str = "Muaf ⛔"
                tag = "exempt"
            else:
                status_str = "Aktif 🟢"
                tag = "even" if count % 2 == 0 else "odd"

            item_id = self.tree.insert(
                "",
                "end",
                values=(t.name, t.branch or "-", status_str),
                tags=(t.id, tag)
            )

            if self.selected_teacher and self.selected_teacher.id == t.id:
                target_item = item_id

            count += 1

        self.lbl_count.configure(text=f"{count} öğretmen")

        children = self.tree.get_children()
        if target_item:
            self.tree.selection_set(target_item)
            self._on_teacher_selected()
        elif children:
            self.tree.selection_set(children[0])
            self._on_teacher_selected()
        else:
            self._clear_detail_panel()

    def select_teacher_by_id(self, teacher_id: str):
        """Dışarıdan belirli bir öğretmeni seçip profilini açar."""
        self.selected_teacher = self.db.get_teacher_by_id(teacher_id)
        self.apply_filter()

    def _on_teacher_selected(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return

        t_id = self.tree.item(sel[0], "tags")[0]
        teacher = self.db.get_teacher_by_id(t_id)
        if not teacher:
            return

        self.selected_teacher = teacher
        self._update_hero_card(teacher)
        self._load_duty_details()
        self._load_attendance_details()
        self._load_timetable_details()
        self._load_ek_ders_details()

    def _clear_detail_panel(self):
        self.selected_teacher = None
        self.lbl_hero_name.configure(text="Öğretmen Bulunamadı")
        self.lbl_hero_meta.configure(text="Lütfen arama veya filtre kriterlerinizi değiştiriniz.")

    def _update_hero_card(self, teacher: Teacher):
        status_text = "🟢 Aktif Görevde" if teacher.is_active else "🔴 Pasif"
        if getattr(teacher, "is_exempt", False):
            reason = getattr(teacher, "exemption_reason", "")
            status_text += f" | ⛔ Nöbetten Muaf ({reason})" if reason else " | ⛔ Nöbetten Muaf"

        seniority = f" | Kıdem: {getattr(teacher, 'seniority_years', 0)} Yıl" if getattr(teacher, "seniority_years", 0) > 0 else ""
        devre = f" | Devre: {getattr(teacher, 'shift_group', 'Tümü')}"
        kadro = " | Kadrosu Bu Okulda" if getattr(teacher, "is_primary_school", True) else " | Görevlendirme"

        self.lbl_hero_name.configure(text=f"{teacher.name} — {teacher.branch or 'Branş Belirtilmemiş'}")
        self.lbl_hero_meta.configure(text=f"{status_text}{devre}{seniority}{kadro} | Tel: {getattr(teacher, 'phone', '') or 'Belirtilmedi'}")

    def _load_duty_details(self):
        if not self.selected_teacher:
            return

        for item in self.tree_duties.get_children():
            self.tree_duties.delete(item)

        assignments = self.db.get_assignments_for_teacher(self.selected_teacher.id)
        self.card_duty_count.configure(text=f"Toplam Nöbet: {len(assignments)}")

        # Tercihler
        t = self.selected_teacher
        prefs = ", ".join(getattr(t, "preferred_days", [])) or "Yok"
        unav = ", ".join(getattr(t, "unavailable_days", [])) or "Yok"
        self.lbl_duty_prefs.configure(
            text=f"⭐ Tercih Ettiği Günler: {prefs}\n🚫 Müsait Olmadığı Günler: {unav}\n📝 Not: {t.notes or 'Yok'}"
        )

        locations = {loc.id: loc.name for loc in self.db.get_locations(active_only=False)}
        days = {day.id: day.name for day in self.db.get_days(active_only=False)}

        for a in assignments:
            day_name = days.get(a.day_id, a.day_id)
            loc_name = locations.get(a.location_id, a.location_id)
            self.tree_duties.insert(
                "",
                "end",
                values=(a.week_start, day_name, loc_name, f"{a.slot_index + 1}. Görevli")
            )

    def _load_attendance_details(self):
        if not self.selected_teacher:
            return

        for item in self.tree_att.get_children():
            self.tree_att.delete(item)

        records = self.db.get_attendance_records(teacher_id=self.selected_teacher.id)
        self.card_att_count.configure(text=f"Toplam Devamsızlık: {len(records)} Kayıt")

        for r in records:
            note_str = r.notes or ""
            if getattr(r, "slip_path", ""):
                note_str += " [Fiş/Rapor Dosyası Mevcut]"

            self.tree_att.insert(
                "",
                "end",
                values=(r.date_str, r.status, r.periods_missed or "Tüm Gün", note_str)
            )

    def _load_timetable_details(self):
        if not self.selected_teacher:
            return

        for item in self.tree_tt.get_children():
            self.tree_tt.delete(item)

        lessons = self.db.get_teacher_lessons(self.selected_teacher.id)
        grid: Dict[int, Dict[str, str]] = {p: {d: "Boş / Müsait" for d in WEEKDAYS} for p in range(1, 8)}

        for l in lessons:
            if not l.is_free and (l.class_name or l.subject_code):
                text = f"{l.class_name} ({l.subject_code})" if l.subject_code else l.class_name
                if l.period in grid and l.day_name in grid[l.period]:
                    grid[l.period][l.day_name] = text

        for p in range(1, 8):
            row_vals = [f"{p}. Ders"] + [grid[p][d] for d in WEEKDAYS]
            tag = "even" if p % 2 == 0 else "odd"
            self.tree_tt.insert("", "end", values=row_vals, tags=(tag,))

    def _load_ek_ders_details(self):
        if not self.selected_teacher:
            return

        for item in self.tree_ek_ders.get_children():
            self.tree_ek_ders.delete(item)

        # Ay dizesi oluştur
        month_name = self.selected_month_var.get()
        month_num = "10"
        for num, name in TURKISH_MONTHS:
            if name == month_name:
                month_num = num
                break
        month_str = f"{self.selected_year_var.get()}-{month_num}"

        res = get_teacher_substitutions_summary(self.db, self.selected_teacher.id, month_str=month_str)

        self.card_ek_total.configure(text=f"Toplam İkame: {res['total_substitutions']} Saat")
        self.card_ek_eligible.configure(text=f"⭐ Ek Ders Hak Ediş: {res['ek_ders_hours']} Saat")
        self.card_ek_super.configure(text=f"Nöbet Nezareti: {res['supervision_hours']} Saat")

        for d in res["details"]:
            status_text = "⭐ Ek Ders Hak Etti" if d["is_ek_ders"] else "Nöbet Nezareti"
            tag = "ek_yes" if d["is_ek_ders"] else "ek_no"

            self.tree_ek_ders.insert(
                "",
                "end",
                values=(
                    d["date_str"],
                    f"{d['period']}. Ders",
                    d["class_name"] or "-",
                    f"{d['absent_teacher_name']} ({d['absent_teacher_branch']})",
                    status_text,
                    d["reason"]
                ),
                tags=(tag,)
            )

    # -------------------------------------------------------------------------
    # AKSİYONLAR
    # -------------------------------------------------------------------------

    def add_teacher(self):
        TeacherEditModal(self, self.db, teacher=None, on_saved=self._on_saved)

    def edit_teacher(self):
        if not self.selected_teacher:
            messagebox.showinfo("Bilgi", "Lütfen düzenlemek için bir öğretmen seçiniz.", parent=self)
            return
        TeacherEditModal(self, self.db, teacher=self.selected_teacher, on_saved=self._on_saved)

    def _on_saved(self):
        self.load_teachers()
        if self.on_data_changed:
            self.on_data_changed()

    def toggle_active(self):
        if not self.selected_teacher:
            return
        self.selected_teacher.is_active = not self.selected_teacher.is_active
        self.db.save_teacher(self.selected_teacher)
        self.load_teachers()
        if self.on_data_changed:
            self.on_data_changed()

    def delete_teacher(self):
        if not self.selected_teacher:
            return
        t = self.selected_teacher
        if messagebox.askyesno(
            "Öğretmen Silme Onayı",
            f"'{t.name}' adlı öğretmeni sistemden silmek istediğinize emin misiniz?\n(Varsa geçmiş atamaları boşa düşecektir)",
            parent=self
        ):
            self.db.delete_teacher(t.id)
            self.selected_teacher = None
            self.load_teachers()
            if self.on_data_changed:
                self.on_data_changed()

    def _send_whatsapp(self):
        if not self.selected_teacher or not getattr(self.selected_teacher, "phone", ""):
            messagebox.showinfo("Bilgi", "Seçili öğretmenin kayıtlı bir telefon numarası bulunmuyor.", parent=self)
            return

        phone = self.selected_teacher.phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if phone.startswith("0"):
            phone = "90" + phone[1:]
        elif not phone.startswith("90"):
            phone = "90" + phone

        url = f"https://web.whatsapp.com/send?phone={phone}"
        try:
            webbrowser.open(url)
        except Exception as e:
            logger.error(f"WhatsApp açılamadı: {e}")

    def open_all_school_summary(self):
        """Ay Sonu Ek Ders İcmal Penceresini açar."""
        month_name = self.selected_month_var.get()
        month_num = "10"
        for num, name in TURKISH_MONTHS:
            if name == month_name:
                month_num = num
                break
        month_str = f"{self.selected_year_var.get()}-{month_num}"

        EkDersMonthlySummaryDialog(
            self,
            self.db,
            initial_month_str=month_str,
            on_select_teacher=self.select_teacher_by_id
        )


class TeacherManagementDialog(tk.Toplevel):
    """Geriye dönük uyumluluk için Toplevel sarmalayıcı."""
    def __init__(self, parent: tk.Widget, db: Database, on_data_changed: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.title("Öğretmen Yönetimi ve 360° Takip Paneli")
        self.geometry("1180x760")
        self.minsize(980, 640)
        self.transient(parent)
        self.view = TeacherManagementView(self, db, on_data_changed)
        self.view.pack(fill="both", expand=True)

    def __getattr__(self, name):
        if "view" in self.__dict__ and hasattr(self.view, name):
            return getattr(self.view, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
