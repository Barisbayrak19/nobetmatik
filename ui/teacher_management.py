"""
Öğretmen Yönetimi Paneli (Tek Ana Pencere Uyumlu View & Dialog)
Öğretmen ekleme, düzenleme, silme, pasifleştirme, arama ve filtreleme.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional, List
from core.models import Teacher
from core.database import Database
from core.config import WEEKDAYS
from core.logger import logger
from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_SUCCESS,
    COLOR_DANGER, COLOR_BORDER, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, FONT_FAMILY,
    create_modern_button
)

class TeacherManagementView(ttk.Frame):
    """Ana pencere içine gömülü Öğretmen Yönetimi Ekranı."""
    def __init__(self, parent: tk.Widget, db: Database, on_data_changed: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.db = db
        self.on_data_changed = on_data_changed

        self.search_var = tk.StringVar()
        self.filter_active_var = tk.StringVar(value="Tümü")

        self.current_editing_teacher: Optional[Teacher] = None

        self._build_ui()
        self.load_teachers()

    def _build_ui(self):
        # 1. Üst Araç Çubuğu (Arama ve Filtre)
        toolbar = ttk.Frame(self, padding=(16, 12, 16, 10))
        toolbar.pack(fill="x", side="top")

        ttk.Label(toolbar, text="🔍 Ara:", font=(FONT_FAMILY, 9, "bold")).pack(side="left", padx=(0, 6))
        entry_search = ttk.Entry(toolbar, textvariable=self.search_var, width=24, font=(FONT_FAMILY, 9))
        entry_search.pack(side="left", padx=(0, 15))
        self.search_var.trace_add("write", lambda *args: self.load_teachers())

        ttk.Label(toolbar, text="Durum:", font=(FONT_FAMILY, 9, "bold")).pack(side="left", padx=(0, 6))
        cb_filter = ttk.Combobox(toolbar, textvariable=self.filter_active_var, values=["Tümü", "Aktifler", "Pasifler"], state="readonly", width=12)
        cb_filter.pack(side="left", padx=(0, 15))
        cb_filter.bind("<<ComboboxSelected>>", lambda e: self.load_teachers())

        btn_add = create_modern_button(toolbar, text="➕ Yeni Öğretmen", variant="primary", command=self.add_teacher)
        btn_add.pack(side="right", padx=(5, 0))

        # 2. Orta İçerik Alanı: Sol Tablo + Sağ Düzenleme Paneli
        self.content_area = ttk.Frame(self, padding=(16, 0, 16, 10))
        self.content_area.pack(fill="both", expand=True)

        # Tablo Çerçevesi
        self.table_frame = ttk.Frame(self.content_area)
        self.table_frame.pack(side="left", fill="both", expand=True)

        columns = ("id", "name", "branch", "devre", "phone", "status", "unavail", "notes")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Adı Soyadı")
        self.tree.heading("branch", text="Branş")
        self.tree.heading("devre", text="Devre")
        self.tree.heading("phone", text="Telefon")
        self.tree.heading("status", text="Durum")
        self.tree.heading("unavail", text="Müsait Olmadığı Günler")
        self.tree.heading("notes", text="Not")

        self.tree.column("id", width=65, stretch=False)
        self.tree.column("name", width=175)
        self.tree.column("branch", width=125)
        self.tree.column("devre", width=85, anchor="center")
        self.tree.column("phone", width=105, anchor="center")
        self.tree.column("status", width=75, anchor="center")
        self.tree.column("unavail", width=160)
        self.tree.column("notes", width=120)

        scrollbar = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.tag_configure("even", background="#FFFFFF")
        self.tree.tag_configure("odd", background="#F8FAFC")

        self.tree.bind("<Double-Button-1>", lambda e: self.edit_teacher())

        # Sağ Düzenleme Kartı (Varsayılan olarak gizli)
        self._build_edit_panel()

        # 3. Alt Buton Barı
        bottom_bar = ttk.Frame(self, padding=(16, 8, 16, 12))
        bottom_bar.pack(fill="x", side="bottom")

        btn_edit = create_modern_button(bottom_bar, text="✏️ Düzenle", variant="default", command=self.edit_teacher)
        btn_edit.pack(side="left", padx=(0, 8))

        btn_toggle = create_modern_button(bottom_bar, text="🔄 Aktif/Pasif Yap", variant="default", command=self.toggle_active)
        btn_toggle.pack(side="left", padx=(0, 8))

        btn_delete = create_modern_button(bottom_bar, text="🗑️ Sil", variant="danger", command=self.delete_teacher)
        btn_delete.pack(side="left")

        self.lbl_count = ttk.Label(bottom_bar, text="Toplam: 0 öğretmen", font=(FONT_FAMILY, 9, "italic"))
        self.lbl_count.pack(side="right")

    def _build_edit_panel(self):
        """Sağ tarafta açılan gömülü öğretmen ekleme/düzenleme formu."""
        self.edit_panel = ttk.LabelFrame(self.content_area, text=" Öğretmen Bilgileri ", padding=14)

        self.name_var = tk.StringVar()
        self.branch_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.shift_var = tk.StringVar(value="Tümü")
        self.active_var = tk.BooleanVar(value=True)
        self.notes_var = tk.StringVar()
        self.day_vars = {day: tk.BooleanVar(value=False) for day in WEEKDAYS}
        self.pref_day_vars = {day: tk.BooleanVar(value=False) for day in WEEKDAYS}
        self.is_exempt_var = tk.BooleanVar(value=False)
        self.exemption_reason_var = tk.StringVar(value="")
        self.seniority_var = tk.IntVar(value=0)
        self.exemption_requested_var = tk.BooleanVar(value=False)
        self.is_primary_var = tk.BooleanVar(value=True)

        # Kaydırılabilir İçerik
        canvas = tk.Canvas(self.edit_panel, highlightthickness=0, width=340)
        sb = ttk.Scrollbar(self.edit_panel, orient="vertical", command=canvas.yview)
        scroll_content = ttk.Frame(canvas)
        scroll_content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_content, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)

        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # Form Alanları
        ttk.Label(scroll_content, text="Ad Soyad:*", font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", pady=(0, 2))
        self.entry_name = ttk.Entry(scroll_content, textvariable=self.name_var, font=(FONT_FAMILY, 9), width=32)
        self.entry_name.pack(fill="x", pady=(0, 6))

        ttk.Label(scroll_content, text="Branş:", font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", pady=(0, 2))
        ttk.Entry(scroll_content, textvariable=self.branch_var, font=(FONT_FAMILY, 9)).pack(fill="x", pady=(0, 6))

        f_row = ttk.Frame(scroll_content)
        f_row.pack(fill="x", pady=(0, 6))

        f_phone = ttk.Frame(f_row)
        f_phone.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Label(f_phone, text="Telefon (WhatsApp):", font=(FONT_FAMILY, 8, "bold")).pack(anchor="w", pady=(0, 2))
        ttk.Entry(f_phone, textvariable=self.phone_var, font=(FONT_FAMILY, 9)).pack(fill="x")

        f_shift = ttk.Frame(f_row)
        f_shift.pack(side="left", fill="x", expand=True)
        ttk.Label(f_shift, text="Devre:", font=(FONT_FAMILY, 8, "bold")).pack(anchor="w", pady=(0, 2))
        cb_shift = ttk.Combobox(f_shift, textvariable=self.shift_var, values=["Tümü", "Sabahçı", "Öğlenci"], state="readonly", width=8)
        cb_shift.pack(fill="x")

        # Kıdem ve Kadro Durumu
        f_sen = ttk.Frame(scroll_content)
        f_sen.pack(fill="x", pady=(0, 6))
        ttk.Label(f_sen, text="Hizmet Yılı:", font=(FONT_FAMILY, 8, "bold")).pack(side="left", padx=(0, 6))
        ttk.Spinbox(f_sen, from_=0, to=50, textvariable=self.seniority_var, width=5).pack(side="left")
        ttk.Checkbutton(f_sen, text="Kadro Bu Okulda", variable=self.is_primary_var).pack(side="right")

        ttk.Checkbutton(scroll_content, text="Aktif Öğretmen (Sistemde kayıtlı)", variable=self.active_var).pack(anchor="w", pady=(0, 4))

        # Mevzuat ve Muafiyet Grubu
        grp_exempt = tk.LabelFrame(
            scroll_content,
            text=" ⚖️ Mevzuat & Muafiyet Durumu ",
            font=(FONT_FAMILY, 8, "bold"),
            padx=8,
            pady=6,
            relief="solid",
            bd=1,
            fg="#B45309"
        )
        grp_exempt.pack(fill="x", pady=(0, 6))

        ttk.Checkbutton(grp_exempt, text="⛔ Nöbetten Kesin Muaf (Aday Havuzuna Alınmaz)", variable=self.is_exempt_var).pack(anchor="w", pady=(0, 4))
        
        ttk.Label(grp_exempt, text="Muafiyet Gerekçesi (Gizli/Yönetici):", font=(FONT_FAMILY, 8)).pack(anchor="w")
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
        cb_reason.bind(
            "<<ComboboxSelected>>",
            lambda e: self.is_exempt_var.set(True) if self.exemption_reason_var.get() else None
        )
        cb_reason.pack(fill="x", pady=(0, 4))

        ttk.Checkbutton(grp_exempt, text="20/25 Yıl Kıdem Muafiyet Talebi Var (İstekli)", variable=self.exemption_requested_var).pack(anchor="w")

        # Tercih Edilen Günler
        grp_pref = tk.LabelFrame(
            scroll_content,
            text=" ⭐ Tercih Ettiği Günler (+Puan) ",
            font=(FONT_FAMILY, 8, "bold"),
            padx=8,
            pady=4,
            relief="solid",
            bd=1,
            fg="#15803D"
        )
        grp_pref.pack(fill="x", pady=(0, 6))
        for day in WEEKDAYS:
            ttk.Checkbutton(grp_pref, text=f"{day}", variable=self.pref_day_vars[day]).pack(anchor="w", pady=0)

        # Müsait Olmadığı Günler
        group_unavail = tk.LabelFrame(
            scroll_content,
            text=" 🚫 Müsait Olmadığı Günler (Kesin Engel) ",
            font=(FONT_FAMILY, 8, "bold"),
            padx=8,
            pady=4,
            relief="solid",
            bd=1,
            fg="#DC2626"
        )
        group_unavail.pack(fill="x", pady=(0, 6))
        for day in WEEKDAYS:
            ttk.Checkbutton(group_unavail, text=f"{day}", variable=self.day_vars[day]).pack(anchor="w", pady=0)

        ttk.Label(scroll_content, text="Notlar / Açıklama:", font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", pady=(0, 2))
        ttk.Entry(scroll_content, textvariable=self.notes_var, font=(FONT_FAMILY, 9)).pack(fill="x", pady=(0, 8))

        # Butonlar
        f_btns = ttk.Frame(scroll_content)
        f_btns.pack(fill="x", pady=(0, 8))
        create_modern_button(f_btns, text="💾 Kaydet", variant="success", command=self._save_inline).pack(side="left", fill="x", expand=True, padx=(0, 4))
        create_modern_button(f_btns, text="İptal", variant="default", command=self.hide_edit_panel).pack(side="left", fill="x", expand=True)

    def show_edit_panel(self, teacher: Optional[Teacher] = None):
        self.current_editing_teacher = teacher
        if teacher:
            self.edit_panel.configure(text=f" ✏️ {teacher.name} Düzenle ")
            self.name_var.set(teacher.name)
            self.branch_var.set(teacher.branch)
            self.phone_var.set(getattr(teacher, "phone", ""))
            self.shift_var.set(getattr(teacher, "shift_group", "Tümü"))
            self.active_var.set(teacher.is_active)
            self.notes_var.set(teacher.notes)
            self.is_exempt_var.set(getattr(teacher, "is_exempt", False))
            self.exemption_reason_var.set(getattr(teacher, "exemption_reason", ""))
            self.seniority_var.set(getattr(teacher, "seniority_years", 0))
            self.exemption_requested_var.set(getattr(teacher, "exemption_requested", False))
            self.is_primary_var.set(getattr(teacher, "is_primary_school", True))
            for day in WEEKDAYS:
                self.day_vars[day].set(day in teacher.unavailable_days)
                self.pref_day_vars[day].set(day in getattr(teacher, "preferred_days", []))
        else:
            self.edit_panel.configure(text=" ➕ Yeni Öğretmen Ekle ")
            self.name_var.set("")
            self.branch_var.set("")
            self.phone_var.set("")
            self.shift_var.set("Tümü")
            self.active_var.set(True)
            self.notes_var.set("")
            self.is_exempt_var.set(False)
            self.exemption_reason_var.set("")
            self.seniority_var.set(0)
            self.exemption_requested_var.set(False)
            self.is_primary_var.set(True)
            for day in WEEKDAYS:
                self.day_vars[day].set(False)
                self.pref_day_vars[day].set(False)

        self.edit_panel.pack(side="right", fill="y", padx=(12, 0))
        self.entry_name.focus()

    def hide_edit_panel(self):
        self.edit_panel.pack_forget()
        self.current_editing_teacher = None

    def _save_inline(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Uyarı", "Lütfen öğretmen adını giriniz.", parent=self)
            return

        t = self.current_editing_teacher or Teacher()
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
        self.hide_edit_panel()
        self.load_teachers()
        if self.on_data_changed:
            self.on_data_changed()

    def load_teachers(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        teachers = self.db.get_teachers()
        query = self.search_var.get().strip().lower()
        filter_status = self.filter_active_var.get()

        count = 0
        for t in teachers:
            if filter_status == "Aktifler" and not t.is_active:
                continue
            if filter_status == "Pasifler" and t.is_active:
                continue

            if query and (query not in t.name.lower() and query not in t.branch.lower()):
                continue

            status_text = "Aktif" if t.is_active else "Pasif"
            unavail_text = ", ".join(t.unavailable_days) if t.unavailable_days else "-"
            tag_stripe = "even" if count % 2 == 0 else "odd"

            self.tree.insert("", "end", values=(
                t.id[:8] + "...",
                t.name,
                t.branch,
                getattr(t, "shift_group", "Tümü"),
                getattr(t, "phone", "") or "-",
                status_text,
                unavail_text,
                t.notes
            ), tags=(t.id, tag_stripe))
            count += 1

        self.lbl_count.configure(text=f"Listelenen: {count} öğretmen")

    def add_teacher(self):
        self.show_edit_panel(teacher=None)

    def edit_teacher(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Bilgi", "Lütfen düzenlemek için bir öğretmen seçiniz.", parent=self)
            return
        t_id = self.tree.item(sel[0], "tags")[0]
        teacher = self.db.get_teacher_by_id(t_id)
        if teacher:
            self.show_edit_panel(teacher=teacher)

    def toggle_active(self):
        sel = self.tree.selection()
        if not sel:
            return
        t_id = self.tree.item(sel[0], "tags")[0]
        teacher = self.db.get_teacher_by_id(t_id)
        if teacher:
            teacher.is_active = not teacher.is_active
            self.db.save_teacher(teacher)
            self.load_teachers()
            if self.on_data_changed:
                self.on_data_changed()

    def delete_teacher(self):
        sel = self.tree.selection()
        if not sel:
            return
        t_id = self.tree.item(sel[0], "tags")[0]
        teacher = self.db.get_teacher_by_id(t_id)
        if not teacher:
            return

        if messagebox.askyesno("Onay", f"'{teacher.name}' adlı öğretmeni silmek istediğinizden emin misiniz?\n(Varsa geçmiş atamaları boşa düşecektir)", parent=self):
            self.db.delete_teacher(teacher.id)
            if self.current_editing_teacher and self.current_editing_teacher.id == teacher.id:
                self.hide_edit_panel()
            self.load_teachers()
            if self.on_data_changed:
                self.on_data_changed()


class TeacherManagementDialog(tk.Toplevel):
    """Geriye dönük uyumluluk için Toplevel sarmalayıcı."""
    def __init__(self, parent: tk.Widget, db: Database, on_data_changed: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.title("Öğretmen Yönetimi")
        self.geometry("950x620")
        self.transient(parent)
        self.view = TeacherManagementView(self, db, on_data_changed)
        self.view.pack(fill="both", expand=True)

    def __getattr__(self, name):
        if "view" in self.__dict__ and hasattr(self.view, name):
            return getattr(self.view, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

