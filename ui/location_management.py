"""
Nöbet Yerleri Yönetim Paneli (Tek Ana Pencere Uyumlu View & Dialog)
Nöbet yerlerini ekleme, düzenleme, silme, sıralama ve kapasite yönetimi.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
from core.models import Location
from core.database import Database
from ui.theme import FONT_FAMILY, create_modern_button

class LocationManagementView(ttk.Frame):
    """Ana pencere içine gömülü Nöbet Yerleri Yönetimi Ekranı."""
    def __init__(self, parent: tk.Widget, db: Database, on_data_changed: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.db = db
        self.on_data_changed = on_data_changed

        self.current_editing_location: Optional[Location] = None

        self._build_ui()
        self.load_locations()

    def _build_ui(self):
        # 1. Üst Araç Çubuğu
        toolbar = ttk.Frame(self, padding=(16, 12, 16, 10))
        toolbar.pack(fill="x", side="top")

        btn_add = create_modern_button(toolbar, text="➕ Yeni Nöbet Yeri", variant="primary", command=self.add_location)
        btn_add.pack(side="left")

        btn_down = create_modern_button(toolbar, text="⬇️ Aşağı Taşı", variant="default", command=lambda: self.move_order(1))
        btn_down.pack(side="right")

        btn_up = create_modern_button(toolbar, text="⬆️ Yukarı Taşı", variant="default", command=lambda: self.move_order(-1))
        btn_up.pack(side="right", padx=(0, 6))

        # 2. Orta İçerik Alanı (Tablo + Sağ Düzenleme Paneli)
        self.content_area = ttk.Frame(self, padding=(16, 0, 16, 10))
        self.content_area.pack(fill="both", expand=True)

        self.table_frame = ttk.Frame(self.content_area)
        self.table_frame.pack(side="left", fill="both", expand=True)

        columns = ("order", "name", "capacity", "devre", "status")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("order", text="Sıra")
        self.tree.heading("name", text="Nöbet Yeri Adı")
        self.tree.heading("capacity", text="Kapasite")
        self.tree.heading("devre", text="Devre")
        self.tree.heading("status", text="Durum")

        self.tree.column("order", width=60, anchor="center")
        self.tree.column("name", width=220)
        self.tree.column("capacity", width=90, anchor="center")
        self.tree.column("devre", width=90, anchor="center")
        self.tree.column("status", width=80, anchor="center")

        scrollbar = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.tag_configure("even", background="#FFFFFF")
        self.tree.tag_configure("odd", background="#F8FAFC")

        self.tree.bind("<Double-Button-1>", lambda e: self.edit_location())

        # Sağ Düzenleme Paneli
        self._build_edit_panel()

        # 3. Alt Buton Barı
        bottom_bar = ttk.Frame(self, padding=(16, 8, 16, 12))
        bottom_bar.pack(fill="x", side="bottom")

        btn_edit = create_modern_button(bottom_bar, text="✏️ Düzenle", variant="default", command=self.edit_location)
        btn_edit.pack(side="left", padx=(0, 8))

        btn_toggle = create_modern_button(bottom_bar, text="🔄 Aktif/Pasif Yap", variant="default", command=self.toggle_active)
        btn_toggle.pack(side="left", padx=(0, 8))

        btn_delete = create_modern_button(bottom_bar, text="🗑️ Sil", variant="danger", command=self.delete_location)
        btn_delete.pack(side="left")

        self.lbl_count = ttk.Label(bottom_bar, text="Toplam: 0 yer", font=(FONT_FAMILY, 9, "italic"))
        self.lbl_count.pack(side="right")

    def _build_edit_panel(self):
        self.edit_panel = ttk.LabelFrame(self.content_area, text=" Nöbet Yeri Bilgileri ", padding=14)

        self.name_var = tk.StringVar()
        self.capacity_var = tk.IntVar(value=1)
        self.shift_var = tk.StringVar(value="Tümü")
        self.active_var = tk.BooleanVar(value=True)

        ttk.Label(self.edit_panel, text="Nöbet Yeri Adı:*", font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", pady=(0, 2))
        self.entry_name = ttk.Entry(self.edit_panel, textvariable=self.name_var, font=(FONT_FAMILY, 9), width=28)
        self.entry_name.pack(fill="x", pady=(0, 8))

        ttk.Label(self.edit_panel, text="Öğretmen Kapasitesi:", font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", pady=(0, 2))
        spin = ttk.Spinbox(self.edit_panel, from_=1, to=5, textvariable=self.capacity_var, width=8)
        spin.pack(anchor="w", pady=(0, 8))

        ttk.Label(self.edit_panel, text="Nöbet Devresi:", font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", pady=(0, 2))
        cb_shift = ttk.Combobox(self.edit_panel, textvariable=self.shift_var, values=["Tümü", "Sabahçı", "Öğlenci"], state="readonly", width=14)
        cb_shift.pack(fill="x", pady=(0, 10))

        chk = ttk.Checkbutton(self.edit_panel, text="Aktif (Çizelgede görünsün)", variable=self.active_var)
        chk.pack(anchor="w", pady=(0, 14))

        f_btns = ttk.Frame(self.edit_panel)
        f_btns.pack(fill="x")

        btn_save = create_modern_button(f_btns, text="💾 Kaydet", variant="success", command=self._save_inline)
        btn_save.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_cancel = create_modern_button(f_btns, text="İptal", variant="default", command=self.hide_edit_panel)
        btn_cancel.pack(side="left", fill="x", expand=True)

    def show_edit_panel(self, location: Optional[Location] = None):
        self.current_editing_location = location
        if location:
            self.edit_panel.configure(text=f" ✏️ {location.name} Düzenle ")
            self.name_var.set(location.name)
            self.capacity_var.set(location.capacity)
            self.shift_var.set(getattr(location, "shift_group", "Tümü"))
            self.active_var.set(location.is_active)
        else:
            self.edit_panel.configure(text=" ➕ Yeni Nöbet Yeri Ekle ")
            self.name_var.set("")
            self.capacity_var.set(1)
            self.shift_var.set("Tümü")
            self.active_var.set(True)

        self.edit_panel.pack(side="right", fill="y", padx=(12, 0))
        self.entry_name.focus()

    def hide_edit_panel(self):
        self.edit_panel.pack_forget()
        self.current_editing_location = None

    def _save_inline(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Uyarı", "Lütfen nöbet yeri adını giriniz.", parent=self)
            return

        loc = self.current_editing_location or Location()
        if not self.current_editing_location:
            locs = self.db.get_locations()
            loc.order_num = max([l.order_num for l in locs], default=0) + 1

        loc.name = name
        loc.capacity = max(1, self.capacity_var.get())
        loc.shift_group = self.shift_var.get().strip()
        loc.is_active = self.active_var.get()

        self.db.save_location(loc)
        self.hide_edit_panel()
        self.load_locations()
        if self.on_data_changed:
            self.on_data_changed()

    def load_locations(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        locs = self.db.get_locations()
        for idx, loc in enumerate(locs):
            status_text = "Aktif" if loc.is_active else "Pasif"
            tag_stripe = "even" if idx % 2 == 0 else "odd"
            self.tree.insert("", "end", values=(
                loc.order_num,
                loc.name,
                f"{loc.capacity} Kişi",
                getattr(loc, "shift_group", "Tümü"),
                status_text
            ), tags=(loc.id, tag_stripe))

        self.lbl_count.configure(text=f"Toplam: {len(locs)} yer")

    def add_location(self):
        self.show_edit_panel(location=None)

    def edit_location(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Bilgi", "Lütfen düzenlemek için bir nöbet yeri seçiniz.", parent=self)
            return
        loc_id = self.tree.item(sel[0], "tags")[0]
        loc = self.db.get_location_by_id(loc_id)
        if loc:
            self.show_edit_panel(location=loc)

    def toggle_active(self):
        sel = self.tree.selection()
        if not sel:
            return
        loc_id = self.tree.item(sel[0], "tags")[0]
        loc = self.db.get_location_by_id(loc_id)
        if loc:
            loc.is_active = not loc.is_active
            self.db.save_location(loc)
            self.load_locations()
            if self.on_data_changed:
                self.on_data_changed()

    def move_order(self, direction: int):
        sel = self.tree.selection()
        if not sel:
            return
        loc_id = self.tree.item(sel[0], "tags")[0]
        locs = self.db.get_locations()
        idx = next((i for i, l in enumerate(locs) if l.id == loc_id), None)
        if idx is None:
            return

        new_idx = idx + direction
        if 0 <= new_idx < len(locs):
            locs[idx].order_num, locs[new_idx].order_num = locs[new_idx].order_num, locs[idx].order_num
            self.db.save_location(locs[idx])
            self.db.save_location(locs[new_idx])
            self.load_locations()
            if self.on_data_changed:
                self.on_data_changed()
            # Select moved item
            for item in self.tree.get_children():
                if self.tree.item(item, "tags")[0] == loc_id:
                    self.tree.selection_set(item)
                    break

    def delete_location(self):
        sel = self.tree.selection()
        if not sel:
            return
        loc_id = self.tree.item(sel[0], "tags")[0]
        loc = self.db.get_location_by_id(loc_id)
        if not loc:
            return

        if messagebox.askyesno("Onay", f"'{loc.name}' nöbet yerini silmek istediğinizden emin misiniz?", parent=self):
            self.db.delete_location(loc.id)
            if self.current_editing_location and self.current_editing_location.id == loc.id:
                self.hide_edit_panel()
            self.load_locations()
            if self.on_data_changed:
                self.on_data_changed()


class LocationManagementDialog(tk.Toplevel):
    """Geriye dönük uyumluluk için Toplevel sarmalayıcı."""
    def __init__(self, parent: tk.Widget, db: Database, on_data_changed: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.title("Nöbet Yerleri Yönetimi")
        self.geometry("750x500")
        self.transient(parent)
        self.view = LocationManagementView(self, db, on_data_changed)
        self.view.pack(fill="both", expand=True)

    def __getattr__(self, name):
        if "view" in self.__dict__ and hasattr(self.view, name):
            return getattr(self.view, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

