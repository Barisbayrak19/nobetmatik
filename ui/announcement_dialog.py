"""
Geliştirici Mesajları ve Duyurular Diyaloğu
Kullanıcılara yeni sürüm notlarını, pratik ipuçlarını ve MEB yönetmelik duyurularını sunar.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from typing import Optional, List

from core.database import Database
from logic.announcement_service import AnnouncementService, Announcement
from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_SECONDARY, COLOR_SUCCESS,
    COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, FONT_FAMILY
)


class AnnouncementDialog(tk.Toplevel):
    def __init__(self, parent: tk.Widget, db: Database, announcements: Optional[List[Announcement]] = None):
        super().__init__(parent)
        self.db = db
        self.announcements = announcements or AnnouncementService.fetch_announcements()

        self.title("📢 Geliştirici Duyuruları ve Mesajları")
        self.geometry("840x580")
        self.minsize(740, 500)
        self.transient(parent)
        self.grab_set()

        self.selected_announcement: Optional[Announcement] = None

        self._build_ui()
        self._populate_list()

    def _build_ui(self):
        # 1. Üst Başlık
        top_frame = tk.Frame(self, bg="#0F172A", padx=20, pady=12)
        top_frame.pack(fill="x", side="top")

        lbl_title = tk.Label(
            top_frame,
            text="📢 GELİŞTİRİCİ DUYURULARI VE MESAJLARI",
            font=(FONT_FAMILY, 12, "bold"),
            fg="#FFFFFF",
            bg="#0F172A"
        )
        lbl_title.pack(anchor="w")

        lbl_desc = tk.Label(
            top_frame,
            text="NöbetMatik yenilikleri, sürüm notları, pratik kullanım ipuçları ve güncellemeler.",
            font=(FONT_FAMILY, 9),
            fg="#94A3B8",
            bg="#0F172A"
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        # 2. Alt Çubuk (Her zaman en altta kalması için önce pack edilir)
        bottom_bar = tk.Frame(self, bg="#F1F5F9", height=46, bd=1, relief="solid")
        bottom_bar.pack(fill="x", side="bottom")

        self.dont_show_again_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            bottom_bar,
            text="Bu duyuruyu açılışta tekrar gösterme",
            variable=self.dont_show_again_var,
            command=self._on_dont_show_toggle
        ).pack(side="left", padx=16, pady=8)

        ttk.Button(
            bottom_bar,
            text="Kapat",
            command=self.destroy
        ).pack(side="right", padx=(6, 16), pady=8)

        self.btn_mark_read = ttk.Button(
            bottom_bar,
            text="✔ Okundu Olarak İşaretle",
            style="Success.TButton",
            command=self._mark_current_as_read
        )
        self.btn_mark_read.pack(side="right", pady=8)

        # 3. İki Sütunlu Gövde (PanedWindow)
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=12, pady=10)

        # Sol Panel: Duyuru Listesi
        f_left = ttk.Frame(paned, padding=6)
        paned.add(f_left, weight=1)

        ttk.Label(f_left, text="Tüm Duyurular:", font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", pady=(0, 4))

        f_tree = ttk.Frame(f_left)
        f_tree.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(f_tree, columns=("status", "title", "date"), show="headings", height=15)
        self.tree.heading("status", text="Durum", anchor="center")
        self.tree.heading("title", text="Başlık", anchor="w")
        self.tree.heading("date", text="Tarih", anchor="center")

        self.tree.column("status", width=55, anchor="center")
        self.tree.column("title", width=180, anchor="w")
        self.tree.column("date", width=80, anchor="center")

        sb_list = ttk.Scrollbar(f_tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb_list.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb_list.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_select_announcement)

        # Sağ Panel: Detay Görüntüleyici
        self.f_right = ttk.Frame(paned, padding=12)
        paned.add(self.f_right, weight=2)

        # Başlık ve Meta Bilgisi
        self.lbl_detail_title = tk.Label(
            self.f_right,
            text="",
            font=(FONT_FAMILY, 12, "bold"),
            fg=COLOR_TEXT_MAIN,
            wraplength=480,
            justify="left",
            anchor="w"
        )
        self.lbl_detail_title.pack(fill="x", pady=(0, 4))

        f_meta = ttk.Frame(self.f_right)
        f_meta.pack(fill="x", pady=(0, 10))

        self.lbl_badge = tk.Label(
            f_meta,
            text="",
            font=(FONT_FAMILY, 8, "bold"),
            fg="#FFFFFF",
            bg=COLOR_PRIMARY,
            padx=8,
            pady=2
        )
        self.lbl_badge.pack(side="left", padx=(0, 8))

        self.lbl_detail_date = ttk.Label(
            f_meta,
            text="",
            font=(FONT_FAMILY, 8),
            foreground=COLOR_TEXT_MUTED
        )
        self.lbl_detail_date.pack(side="left")

        # Özet Kartı
        self.f_summary = tk.Frame(self.f_right, bg="#EFF6FF", bd=1, relief="solid", padx=10, pady=8)
        self.f_summary.pack(fill="x", pady=(0, 10))

        self.lbl_summary = tk.Label(
            self.f_summary,
            text="",
            font=(FONT_FAMILY, 9, "italic"),
            fg="#1E40AF",
            bg="#EFF6FF",
            wraplength=460,
            justify="left",
            anchor="w"
        )
        self.lbl_summary.pack(fill="x")

        # Detay Metin Alanı
        self.txt_content = tk.Text(
            self.f_right,
            wrap="word",
            font=(FONT_FAMILY, 10),
            bg=COLOR_CARD,
            fg=COLOR_TEXT_MAIN,
            padx=10,
            pady=10,
            bd=1,
            relief="solid",
            height=12
        )
        self.txt_content.pack(fill="both", expand=True, pady=(0, 10))

        # Harici Bağlantı Butonu
        self.btn_link = ttk.Button(
            self.f_right,
            text="🔗 Bağlantıyı Aç",
            command=self._open_link
        )
        self.btn_link.pack(anchor="w")

    def _populate_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        last_read_id = self.db.get_setting("last_read_announcement_id", "")
        for a in self.announcements:
            is_read = (a.id == last_read_id or not last_read_id)  # ilk açılışta mantıklı gösterim
            status_txt = "⚪ Okundu" if a.id == last_read_id else "🔵 YENİ"
            self.tree.insert("", "end", iid=a.id, values=(status_txt, a.title, a.date))

        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children[0])
            self.tree.focus(children[0])
            self._display_announcement(self.announcements[0])

    def _on_select_announcement(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        ann_id = sel[0]
        a = next((x for x in self.announcements if x.id == ann_id), None)
        if a:
            self._display_announcement(a)

    def _display_announcement(self, a: Announcement):
        self.selected_announcement = a
        self.lbl_detail_title.configure(text=a.title)
        self.lbl_badge.configure(text=a.badge, bg=a.badge_color or COLOR_PRIMARY)
        self.lbl_detail_date.configure(text=f"Tarih: {a.date}")

        if a.summary:
            self.f_summary.pack(fill="x", pady=(0, 10))
            self.lbl_summary.configure(text=a.summary)
        else:
            self.f_summary.pack_forget()

        self.txt_content.configure(state="normal")
        self.txt_content.delete("1.0", tk.END)
        self.txt_content.insert("1.0", a.content)
        self.txt_content.configure(state="disabled")

        if a.link_url:
            self.btn_link.pack(anchor="w")
            btn_txt = f"🔗 {a.link_text}" if a.link_text else "🔗 İlgili Sayfayı Aç"
            self.btn_link.configure(text=btn_txt)
        else:
            self.btn_link.pack_forget()

    def _open_link(self):
        if self.selected_announcement and self.selected_announcement.link_url:
            webbrowser.open(self.selected_announcement.link_url)

    def _mark_current_as_read(self):
        if self.selected_announcement:
            AnnouncementService.mark_as_read(self.db, self.selected_announcement.id)
            if self.tree.exists(self.selected_announcement.id):
                vals = list(self.tree.item(self.selected_announcement.id, "values"))
                vals[0] = "⚪ Okundu"
                self.tree.item(self.selected_announcement.id, values=vals)
            messagebox.showinfo("Başarılı", "Duyuru okundu olarak işaretlendi.", parent=self)

    def _on_dont_show_toggle(self):
        if self.dont_show_again_var.get() and self.selected_announcement:
            AnnouncementService.mark_as_read(self.db, self.selected_announcement.id)
