"""
Nöbet Yerleri Yönetim Paneli
Nöbet yerlerini ekleme, düzenleme, silme, sıralama ve kapasite yönetimi.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
from core.models import Location
from core.database import Database
from ui.theme import FONT_FAMILY

class LocationEditDialog(tk.Toplevel):
    def __init__(self, parent: tk.Widget, location: Optional[Location] = None, on_save: Optional[Callable[[Location], None]] = None):
        super().__init__(parent)
        self.location = location or Location()
        self.is_new = location is None
        self.on_save = on_save

        self.title("Nöbet Yeri Düzenle" if not self.is_new else "Yeni Nöbet Yeri Ekle")
        self.geometry("380x330")
        self.transient(parent)
        self.grab_set()

        self.name_var = tk.StringVar(value=self.location.name)
        self.capacity_var = tk.IntVar(value=self.location.capacity)
        self.shift_var = tk.StringVar(value=getattr(self.location, "shift_group", "Tümü"))
        self.active_var = tk.BooleanVar(value=self.location.is_active)

        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Nöbet Yeri Adı:*", font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", pady=(0, 2))
        entry_name = ttk.Entry(frame, textvariable=self.name_var, font=(FONT_FAMILY, 10))
        entry_name.pack(fill="x", pady=(0, 10))
        entry_name.focus()

        ttk.Label(frame, text="Öğretmen Kapasitesi (Slot Sayısı):", font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", pady=(0, 2))
        spin = ttk.Spinbox(frame, from_=1, to=5, textvariable=self.capacity_var, width=5)
        spin.pack(anchor="w", pady=(0, 10))

        ttk.Label(frame, text="Nöbet Devresi (İkili Eğitim):", font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", pady=(0, 2))
        cb_shift = ttk.Combobox(frame, textvariable=self.shift_var, values=["Tümü", "Sabahçı", "Öğlenci"], state="readonly")
        cb_shift.pack(fill="x", pady=(0, 10))

        chk = ttk.Checkbutton(frame, text="Aktif (Çizelgede görünsün)", variable=self.active_var)
        chk.pack(anchor="w", pady=(0, 15))

        btn_box = ttk.Frame(frame)
        btn_box.pack(fill="x", side="bottom")

        ttk.Button(btn_box, text="İptal", command=self.destroy).pack(side="right", padx=(5, 0))
        ttk.Button(btn_box, text="Kaydet", style="Primary.TButton", command=self._save).pack(side="right")

    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Uyarı", "Lütfen nöbet yeri adını giriniz.")
            return

        self.location.name = name
        self.location.capacity = max(1, self.capacity_var.get())
        self.location.shift_group = self.shift_var.get().strip()
        self.location.is_active = self.active_var.get()

        if self.on_save:
            self.on_save(self.location)

        self.destroy()


class LocationManagementDialog(tk.Toplevel):
    def __init__(self, parent: tk.Widget, db: Database, on_data_changed: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.db = db
        self.on_data_changed = on_data_changed

        self.title("Nöbet Yerleri Yönetimi")
        self.geometry("650x450")
        self.transient(parent)

        self._build_ui()
        self.load_locations()

    def _build_ui(self):
        toolbar = ttk.Frame(self, padding=12)
        toolbar.pack(fill="x", side="top")

        btn_add = ttk.Button(toolbar, text="➕ Yeni Nöbet Yeri", style="Primary.TButton", command=self.add_location)
        btn_add.pack(side="left")

        btn_up = ttk.Button(toolbar, text="⬆️ Yukarı Taşı", command=lambda: self.move_order(-1))
        btn_up.pack(side="right", padx=(5, 0))

        btn_down = ttk.Button(toolbar, text="⬇️ Aşağı Taşı", command=lambda: self.move_order(1))
        btn_down.pack(side="right")

        table_frame = ttk.Frame(self, padding=(12, 0, 12, 12))
        table_frame.pack(fill="both", expand=True)

        columns = ("order", "name", "capacity", "devre", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("order", text="Sıra")
        self.tree.heading("name", text="Nöbet Yeri Adı")
        self.tree.heading("capacity", text="Kapasite")
        self.tree.heading("devre", text="Devre")
        self.tree.heading("status", text="Durum")

        self.tree.column("order", width=60, anchor="center")
        self.tree.column("name", width=230)
        self.tree.column("capacity", width=90, anchor="center")
        self.tree.column("devre", width=90, anchor="center")
        self.tree.column("status", width=80, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-Button-1>", lambda e: self.edit_location())

        bottom_bar = ttk.Frame(self, padding=12)
        bottom_bar.pack(fill="x", side="bottom")

        btn_edit = ttk.Button(bottom_bar, text="✏️ Düzenle", command=self.edit_location)
        btn_edit.pack(side="left", padx=(0, 8))

        btn_toggle = ttk.Button(bottom_bar, text="🔄 Aktif/Pasif", command=self.toggle_active)
        btn_toggle.pack(side="left", padx=(0, 8))

        btn_delete = ttk.Button(bottom_bar, text="🗑️ Sil", style="Danger.TButton", command=self.delete_location)
        btn_delete.pack(side="left")

    def load_locations(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        locs = self.db.get_locations()
        for loc in locs:
            status_text = "Aktif" if loc.is_active else "Pasif"
            self.tree.insert("", "end", values=(
                loc.order_num,
                loc.name,
                f"{loc.capacity} Kişi",
                getattr(loc, "shift_group", "Tümü"),
                status_text
            ), tags=(loc.id,))

    def add_location(self):
        locs = self.db.get_locations()
        next_order = max([l.order_num for l in locs], default=0) + 1

        def on_save(new_loc: Location):
            new_loc.order_num = next_order
            self.db.save_location(new_loc)
            self.load_locations()
            if self.on_data_changed:
                self.on_data_changed()

        LocationEditDialog(self, location=None, on_save=on_save)

    def edit_location(self):
        sel = self.tree.selection()
        if not sel:
            return
        loc_id = self.tree.item(sel[0], "tags")[0]
        loc = self.db.get_location_by_id(loc_id)
        if not loc:
            return

        def on_save(upd: Location):
            self.db.save_location(upd)
            self.load_locations()
            if self.on_data_changed:
                self.on_data_changed()

        LocationEditDialog(self, location=loc, on_save=on_save)

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
            # Swap order_num
            locs[idx].order_num, locs[new_idx].order_num = locs[new_idx].order_num, locs[idx].order_num
            self.db.save_location(locs[idx])
            self.db.save_location(locs[new_idx])
            self.load_locations()
            if self.on_data_changed:
                self.on_data_changed()

    def delete_location(self, loc_id: str = None):
        sel = self.tree.selection()
        if not sel:
            return
        loc_id = self.tree.item(sel[0], "tags")[0]
        loc = self.db.get_location_by_id(loc_id)
        if not loc:
            return

        if messagebox.askyesno("Onay", f"'{loc.name}' nöbet yerini silmek istediğinizden emin misiniz?"):
            self.db.delete_location(loc.id)
            self.load_locations()
            if self.on_data_changed:
                self.on_data_changed()
