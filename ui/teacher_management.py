"""
Öğretmen Yönetimi Paneli
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
    COLOR_DANGER, COLOR_BORDER, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, FONT_FAMILY
)

class TeacherEditDialog(tk.Toplevel):
    def __init__(self, parent: tk.Widget, teacher: Optional[Teacher] = None, on_save: Optional[Callable[[Teacher], None]] = None):
        super().__init__(parent)
        self.teacher = teacher or Teacher()
        self.is_new = teacher is None
        self.on_save = on_save

        self.title("Öğretmen Düzenle" if not self.is_new else "Yeni Öğretmen Ekle")
        self.geometry("450x520")
        self.transient(parent)
        self.grab_set()

        self.name_var = tk.StringVar(value=self.teacher.name)
        self.branch_var = tk.StringVar(value=self.teacher.branch)
        self.phone_var = tk.StringVar(value=getattr(self.teacher, "phone", ""))
        self.shift_var = tk.StringVar(value=getattr(self.teacher, "shift_group", "Tümü"))
        self.active_var = tk.BooleanVar(value=self.teacher.is_active)
        self.notes_var = tk.StringVar(value=self.teacher.notes)

        # Müsait olunmayan günler
        self.day_vars = {day: tk.BooleanVar(value=(day in self.teacher.unavailable_days)) for day in WEEKDAYS}

        self._build_ui()

    def _build_ui(self):
        container = ttk.Frame(self, padding=20)
        container.pack(fill="both", expand=True)

        # Ad Soyad
        ttk.Label(container, text="Ad Soyad:*", font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", pady=(0, 2))
        entry_name = ttk.Entry(container, textvariable=self.name_var, font=(FONT_FAMILY, 10))
        entry_name.pack(fill="x", pady=(0, 10))
        entry_name.focus()

        # Branş
        ttk.Label(container, text="Branş:", font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", pady=(0, 2))
        entry_branch = ttk.Entry(container, textvariable=self.branch_var, font=(FONT_FAMILY, 10))
        entry_branch.pack(fill="x", pady=(0, 10))

        # Telefon & Devre (İkili Eğitim)
        f_row = ttk.Frame(container)
        f_row.pack(fill="x", pady=(0, 10))

        f_phone = ttk.Frame(f_row)
        f_phone.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Label(f_phone, text="Telefon (WhatsApp):", font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", pady=(0, 2))
        ttk.Entry(f_phone, textvariable=self.phone_var, font=(FONT_FAMILY, 10)).pack(fill="x")

        f_shift = ttk.Frame(f_row)
        f_shift.pack(side="left", fill="x", expand=True)
        ttk.Label(f_shift, text="Devre (İkili Eğitim):", font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", pady=(0, 2))
        cb_shift = ttk.Combobox(f_shift, textvariable=self.shift_var, values=["Tümü", "Sabahçı", "Öğlenci"], state="readonly")
        cb_shift.pack(fill="x")

        # Aktif / Pasif
        chk_active = ttk.Checkbutton(container, text="Aktif Öğretmen (Nöbet listesine dahil)", variable=self.active_var)
        chk_active.pack(anchor="w", pady=(0, 12))

        # Müsait Olmadığı Günler
        group_unavail = tk.LabelFrame(
            container,
            text=" 🚫 Müsait Olmadığı Günler ",
            font=(FONT_FAMILY, 9, "bold"),
            padx=10,
            pady=8,
            relief="solid",
            bd=1
        )
        group_unavail.pack(fill="x", pady=(0, 12))

        for day in WEEKDAYS:
            cb = ttk.Checkbutton(group_unavail, text=f"{day} günü nöbet tutamaz", variable=self.day_vars[day])
            cb.pack(anchor="w", pady=2)

        # Notlar
        ttk.Label(container, text="Notlar / Açıklama:", font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", pady=(0, 2))
        entry_notes = ttk.Entry(container, textvariable=self.notes_var, font=(FONT_FAMILY, 10))
        entry_notes.pack(fill="x", pady=(0, 15))

        # Butonlar
        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill="x", side="bottom")

        btn_cancel = ttk.Button(btn_frame, text="İptal", command=self.destroy)
        btn_cancel.pack(side="right", padx=(5, 0))

        btn_save = ttk.Button(btn_frame, text="Kaydet", style="Primary.TButton", command=self._save)
        btn_save.pack(side="right")

    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Uyarı", "Lütfen öğretmen adını giriniz.")
            return

        self.teacher.name = name
        self.teacher.branch = self.branch_var.get().strip()
        self.teacher.phone = self.phone_var.get().strip()
        self.teacher.shift_group = self.shift_var.get().strip()
        self.teacher.is_active = self.active_var.get()
        self.teacher.notes = self.notes_var.get().strip()
        self.teacher.unavailable_days = [day for day, var in self.day_vars.items() if var.get()]

        if self.on_save:
            self.on_save(self.teacher)

        self.destroy()


class TeacherManagementDialog(tk.Toplevel):
    def __init__(self, parent: tk.Widget, db: Database, on_data_changed: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.db = db
        self.on_data_changed = on_data_changed

        self.title("Öğretmen Yönetimi")
        self.geometry("900x600")
        self.transient(parent)

        self.search_var = tk.StringVar()
        self.filter_active_var = tk.StringVar(value="Tümü")

        self._build_ui()
        self.load_teachers()

    def _build_ui(self):
        # Üst Araç Çubuğu (Arama ve Filtre)
        toolbar = ttk.Frame(self, padding=12)
        toolbar.pack(fill="x", side="top")

        ttk.Label(toolbar, text="🔍 Ara:").pack(side="left", padx=(0, 5))
        entry_search = ttk.Entry(toolbar, textvariable=self.search_var, width=25)
        entry_search.pack(side="left", padx=(0, 15))
        self.search_var.trace_add("write", lambda *args: self.load_teachers())

        ttk.Label(toolbar, text="Durum:").pack(side="left", padx=(0, 5))
        cb_filter = ttk.Combobox(toolbar, textvariable=self.filter_active_var, values=["Tümü", "Aktifler", "Pasifler"], state="readonly", width=12)
        cb_filter.pack(side="left", padx=(0, 15))
        cb_filter.bind("<<ComboboxSelected>>", lambda e: self.load_teachers())

        btn_add = ttk.Button(toolbar, text="➕ Yeni Öğretmen", style="Primary.TButton", command=self.add_teacher)
        btn_add.pack(side="right", padx=(5, 0))

        # Liste Tablosu (Treeview)
        table_frame = ttk.Frame(self, padding=(12, 0, 12, 12))
        table_frame.pack(fill="both", expand=True)

        columns = ("id", "name", "branch", "devre", "phone", "status", "unavail", "notes")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Adı Soyadı")
        self.tree.heading("branch", text="Branş")
        self.tree.heading("devre", text="Devre")
        self.tree.heading("phone", text="Telefon")
        self.tree.heading("status", text="Durum")
        self.tree.heading("unavail", text="Müsait Olmadığı Günler")
        self.tree.heading("notes", text="Not")

        self.tree.column("id", width=70, stretch=False)
        self.tree.column("name", width=180)
        self.tree.column("branch", width=130)
        self.tree.column("devre", width=90, anchor="center")
        self.tree.column("phone", width=110, anchor="center")
        self.tree.column("status", width=80, anchor="center")
        self.tree.column("unavail", width=160)
        self.tree.column("notes", width=130)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-Button-1>", lambda e: self.edit_teacher())

        # Alt Butonlar
        bottom_bar = ttk.Frame(self, padding=12)
        bottom_bar.pack(fill="x", side="bottom")

        btn_edit = ttk.Button(bottom_bar, text="✏️ Düzenle", command=self.edit_teacher)
        btn_edit.pack(side="left", padx=(0, 8))

        btn_toggle = ttk.Button(bottom_bar, text="🔄 Aktif/Pasif Yap", command=self.toggle_active)
        btn_toggle.pack(side="left", padx=(0, 8))

        btn_delete = ttk.Button(bottom_bar, text="🗑️ Sil", style="Danger.TButton", command=self.delete_teacher)
        btn_delete.pack(side="left")

        self.lbl_count = ttk.Label(bottom_bar, text="Toplam: 0 öğretmen", font=(FONT_FAMILY, 9, "italic"))
        self.lbl_count.pack(side="right")

    def load_teachers(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        teachers = self.db.get_teachers()
        query = self.search_var.get().strip().lower()
        filter_status = self.filter_active_var.get()

        count = 0
        for t in teachers:
            # Filtre
            if filter_status == "Aktifler" and not t.is_active:
                continue
            if filter_status == "Pasifler" and t.is_active:
                continue

            # Arama
            if query and (query not in t.name.lower() and query not in t.branch.lower()):
                continue

            status_text = "Aktif" if t.is_active else "Pasif"
            unavail_text = ", ".join(t.unavailable_days) if t.unavailable_days else "-"

            self.tree.insert("", "end", values=(
                t.id[:8] + "...",
                t.name,
                t.branch,
                getattr(t, "shift_group", "Tümü"),
                getattr(t, "phone", "") or "-",
                status_text,
                unavail_text,
                t.notes
            ), tags=(t.id,))
            count += 1

        self.lbl_count.configure(text=f"Listelenen: {count} öğretmen")

    def add_teacher(self):
        def on_save(new_t: Teacher):
            self.db.save_teacher(new_t)
            self.load_teachers()
            if self.on_data_changed:
                self.on_data_changed()
        TeacherEditDialog(self, teacher=None, on_save=on_save)

    def edit_teacher(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Bilgi", "Lütfen düzenlemek için bir öğretmen seçiniz.")
            return
        t_id = self.tree.item(sel[0], "tags")[0]
        teacher = self.db.get_teacher_by_id(t_id)
        if not teacher:
            return

        def on_save(updated_t: Teacher):
            self.db.save_teacher(updated_t)
            self.load_teachers()
            if self.on_data_changed:
                self.on_data_changed()

        TeacherEditDialog(self, teacher=teacher, on_save=on_save)

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

        if messagebox.askyesno("Onay", f"'{teacher.name}' adlı öğretmeni silmek istediğinizden emin misiniz?\n(Varsa geçmiş atamaları boşa düşecektir)"):
            self.db.delete_teacher(teacher.id)
            self.load_teachers()
            if self.on_data_changed:
                self.on_data_changed()
