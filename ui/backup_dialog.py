"""
Yedekleme ve Geri Yükleme Yönetim Ekranı
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
from pathlib import Path
from logic.backup_service import BackupService
from ui.theme import COLOR_PRIMARY, COLOR_SUCCESS, COLOR_DANGER, FONT_FAMILY

class BackupDialog(tk.Toplevel):
    def __init__(self, parent: tk.Widget, backup_service: BackupService, on_restore_complete: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.backup_service = backup_service
        self.on_restore_complete = on_restore_complete

        self.title("Veritabanı Yedekleme ve Geri Yükleme")
        self.geometry("680x450")
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self.load_backups()

    def _build_ui(self):
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)

        top_box = ttk.Frame(frame)
        top_box.pack(fill="x", pady=(0, 10))

        ttk.Label(
            top_box,
            text="💾 Sistem Yedekleme ve Geri Yükleme",
            font=(FONT_FAMILY, 12, "bold"),
            foreground=COLOR_PRIMARY
        ).pack(side="left")

        btn_new_backup = ttk.Button(
            top_box,
            text="➕ Şimdi Yedek Al",
            style="Success.TButton",
            command=self.create_backup
        )
        btn_new_backup.pack(side="right")

        # Yedekler Tablosu
        cols = ("name", "date", "size")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("name", text="Yedek Dosyası Adı")
        self.tree.heading("date", text="Yedekleme Tarihi")
        self.tree.heading("size", text="Boyut (KB)")

        self.tree.column("name", width=320)
        self.tree.column("date", width=180, anchor="center")
        self.tree.column("size", width=100, anchor="center")

        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Alt Butonlar
        bottom_box = ttk.Frame(self, padding=15)
        bottom_box.pack(fill="x", side="bottom")

        btn_restore = ttk.Button(
            bottom_box,
            text="🔄 Seçilen Yedekten Geri Yükle",
            style="Primary.TButton",
            command=self.restore_selected
        )
        btn_restore.pack(side="left")

        ttk.Button(bottom_box, text="Kapat", command=self.destroy).pack(side="right")

    def load_backups(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        backups = self.backup_service.list_backups()
        for b in backups:
            self.tree.insert("", "end", values=(
                b["name"],
                b["created_at"],
                f"{b['size_kb']} KB"
            ), tags=(str(b["path"]),))

    def create_backup(self):
        try:
            dest = self.backup_service.create_backup()
            messagebox.showinfo("Başarılı", f"Yedek başarıyla oluşturuldu:\n{dest.name}")
            self.load_backups()
        except Exception as e:
            messagebox.showerror("Hata", f"Yedek alınırken hata oluştu:\n{e}")

    def restore_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Bilgi", "Lütfen geri yüklemek istediğiniz bir yedek seçiniz.")
            return

        backup_path_str = self.tree.item(sel[0], "tags")[0]
        backup_path = Path(backup_path_str)

        if messagebox.askyesno(
            "Geri Yükleme Onayı",
            f"Seçili yedek: {backup_path.name}\n\n"
            "Mevcut veritabanının üzerine yazılacaktır. Devam etmek istiyor musunuz?"
        ):
            try:
                self.backup_service.restore_backup(backup_path)
                messagebox.showinfo("Başarılı", "Yedek başarıyla geri yüklendi! Sistem verileri güncellendi.")
                if self.on_restore_complete:
                    self.on_restore_complete()
                self.destroy()
            except Exception as e:
                messagebox.showerror("Hata", f"Geri yükleme sırasında hata oluştu:\n{e}")
