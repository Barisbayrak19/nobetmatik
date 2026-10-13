"""
Yedekleme ve Geri Yükleme Yönetim Ekranı (Tek Ana Pencere Uyumlu View & Dialog)
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
from pathlib import Path
import os
import subprocess
import sys
from logic.backup_service import BackupService
from ui.theme import COLOR_PRIMARY, COLOR_SUCCESS, COLOR_DANGER, FONT_FAMILY, create_modern_button

class BackupView(ttk.Frame):
    """Ana pencere içine gömülü Veri Yedekleme ve Geri Yükleme Ekranı."""
    def __init__(
        self,
        parent: tk.Widget,
        backup_service: BackupService,
        on_restore_complete: Optional[Callable[[], None]] = None,
        on_finish: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent)
        self.backup_service = backup_service
        self.on_restore_complete = on_restore_complete
        self.on_finish = on_finish

        self._build_ui()
        self.load_backups()

    def _build_ui(self):
        container = ttk.Frame(self, padding=(16, 12, 16, 12))
        container.pack(fill="both", expand=True)

        top_box = ttk.Frame(container)
        top_box.pack(fill="x", pady=(0, 10))

        ttk.Label(
            top_box,
            text="💾 Sistem Veritabanı Yedekleme ve Geri Yükleme",
            font=(FONT_FAMILY, 12, "bold"),
            foreground=COLOR_PRIMARY
        ).pack(side="left")

        btn_new_backup = create_modern_button(
            top_box,
            text="➕ Şimdi Yedek Al",
            variant="success",
            command=self.create_backup
        )
        btn_new_backup.pack(side="right")

        btn_folder = create_modern_button(
            top_box,
            text="📂 Klasörü Aç",
            variant="default",
            command=self.open_backup_folder
        )
        btn_folder.pack(side="right", padx=(0, 8))

        # Yedekler Tablosu
        cols = ("name", "date", "size")
        self.tree = ttk.Treeview(container, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("name", text="Yedek Dosyası Adı")
        self.tree.heading("date", text="Yedekleme Tarihi")
        self.tree.heading("size", text="Boyut (KB)")

        self.tree.column("name", width=340)
        self.tree.column("date", width=180, anchor="center")
        self.tree.column("size", width=100, anchor="center")

        sb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Alt Butonlar
        bottom_box = ttk.Frame(self, padding=(16, 8, 16, 12))
        bottom_box.pack(fill="x", side="bottom")

        btn_restore = create_modern_button(
            bottom_box,
            text="🔄 Seçilen Yedekten Geri Yükle",
            variant="primary",
            command=self.restore_selected
        )
        btn_restore.pack(side="left")

        btn_delete = create_modern_button(
            bottom_box,
            text="🗑️ Yedeği Sil",
            variant="danger",
            command=self.delete_selected
        )
        btn_delete.pack(side="left", padx=(8, 0))

        if self.on_finish:
            create_modern_button(bottom_box, text="Kapat", variant="default", command=self.on_finish).pack(side="right")

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
            messagebox.showinfo("Başarılı", f"Yedek başarıyla oluşturuldu:\n{dest.name}", parent=self)
            self.load_backups()
        except Exception as e:
            messagebox.showerror("Hata", f"Yedek alınırken hata oluştu:\n{e}", parent=self)

    def restore_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Bilgi", "Lütfen geri yüklemek istediğiniz bir yedek seçiniz.", parent=self)
            return

        backup_path_str = self.tree.item(sel[0], "tags")[0]
        backup_path = Path(backup_path_str)

        if messagebox.askyesno(
            "Geri Yükleme Onayı",
            f"Seçili yedek: {backup_path.name}\n\n"
            "Mevcut veritabanının üzerine yazılacaktır. Devam etmek istiyor musunuz?",
            parent=self
        ):
            try:
                self.backup_service.restore_backup(backup_path)
                messagebox.showinfo("Başarılı", "Yedek başarıyla geri yüklendi! Sistem verileri güncellendi.", parent=self)
                if self.on_restore_complete:
                    self.on_restore_complete()
            except Exception as e:
                messagebox.showerror("Hata", f"Geri yükleme sırasında hata oluştu:\n{e}", parent=self)

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Bilgi", "Lütfen silmek istediğiniz yedeği seçiniz.", parent=self)
            return

        backup_path_str = self.tree.item(sel[0], "tags")[0]
        backup_path = Path(backup_path_str)

        if messagebox.askyesno("Silme Onayı", f"'{backup_path.name}' yedek dosyasını silmek istediğinizden emin misiniz?", parent=self):
            try:
                if backup_path.exists():
                    backup_path.unlink()
                self.load_backups()
                messagebox.showinfo("Başarılı", "Yedek dosyası silindi.", parent=self)
            except Exception as e:
                messagebox.showerror("Hata", f"Silme sırasında hata oluştu: {e}", parent=self)

    def open_backup_folder(self):
        from core.config import BACKUP_DIR
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(BACKUP_DIR))
            else:
                subprocess.Popen(["xdg-open", str(BACKUP_DIR)])
        except Exception as e:
            messagebox.showerror("Hata", f"Klasör açılamadı: {e}", parent=self)


class BackupDialog(tk.Toplevel):
    """Geriye dönük uyumluluk için Toplevel sarmalayıcı."""
    def __init__(self, parent: tk.Widget, backup_service: BackupService, on_restore_complete: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.title("Veritabanı Yedekleme ve Geri Yükleme")
        self.geometry("720x480")
        self.transient(parent)
        self.view = BackupView(self, backup_service, on_restore_complete=on_restore_complete, on_finish=self.destroy)
        self.view.pack(fill="both", expand=True)

    def __getattr__(self, name):
        if "view" in self.__dict__ and hasattr(self.view, name):
            return getattr(self.view, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

