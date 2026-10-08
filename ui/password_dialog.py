"""
Yönetici Şifre Doğrulama Penceresi (Admin Password Modal)
Sisteme yetkisiz müdahaleleri önlemek için kritik işlem ve ayar ekranları öncesinde şifre doğrulaması yapar.
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from typing import Callable, Optional

from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_DANGER,
    COLOR_BORDER, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, FONT_FAMILY
)

class AdminPasswordDialog(ctk.CTkToplevel):
    def __init__(self, parent: tk.Widget, db, on_success: Callable[[], None], title_text: str = "Yönetici Doğrulaması"):
        super().__init__(parent)
        self.db = db
        self.on_success = on_success
        self.verified = False

        self.title("🔐 " + title_text)
        self.geometry("420x260")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self.after(100, self._focus_entry)

    def _focus_entry(self):
        self.ent_pwd.focus_set()

    def _build_ui(self):
        # Üst İkon ve Bilgi
        f_top = ctk.CTkFrame(self, fg_color="transparent")
        f_top.pack(fill="x", padx=24, pady=(20, 10))

        lbl_icon = ctk.CTkLabel(f_top, text="🔒", font=(FONT_FAMILY, 32))
        lbl_icon.pack(side="left", padx=(0, 14))

        f_txt = ctk.CTkFrame(f_top, fg_color="transparent")
        f_txt.pack(side="left", fill="both", expand=True)

        lbl_title = ctk.CTkLabel(
            f_txt,
            text="Yönetici Şifresi Gereklidir",
            font=(FONT_FAMILY, 12, "bold"),
            text_color=COLOR_TEXT_MAIN
        )
        lbl_title.pack(anchor="w")

        lbl_desc = ctk.CTkLabel(
            f_txt,
            text="Bu işlem okul idaresi tarafından koruma altına alınmıştır. Devam etmek için şifrenizi giriniz:",
            font=(FONT_FAMILY, 9),
            text_color=COLOR_TEXT_MUTED,
            wraplength=280,
            justify="left"
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        # Şifre Giriş Alanı
        self.pwd_var = tk.StringVar()
        self.ent_pwd = ctk.CTkEntry(
            self,
            textvariable=self.pwd_var,
            show="●",
            font=(FONT_FAMILY, 13),
            placeholder_text="Şifrenizi yazınız...",
            height=38
        )
        self.ent_pwd.pack(fill="x", padx=24, pady=12)
        self.ent_pwd.bind("<Return>", lambda e: self._verify())

        # Butonlar
        f_btns = ctk.CTkFrame(self, fg_color="transparent")
        f_btns.pack(fill="x", padx=24, pady=(10, 20))

        btn_cancel = ctk.CTkButton(
            f_btns,
            text="İptal",
            fg_color="#64748B",
            hover_color="#475569",
            width=90,
            command=self.destroy
        )
        btn_cancel.pack(side="left")

        btn_ok = ctk.CTkButton(
            f_btns,
            text="Giriş Yap",
            fg_color=COLOR_PRIMARY,
            hover_color="#1D4ED8",
            width=110,
            command=self._verify
        )
        btn_ok.pack(side="right")

    def _verify(self):
        entered = self.pwd_var.get().strip()
        if self.db.verify_admin_password(entered):
            self.verified = True
            self.destroy()
            if self.on_success:
                self.on_success()
        else:
            messagebox.showerror(
                "Hatalı Şifre",
                "Girdiğiniz yönetici şifresi yanlış!\nLütfen kontrol edip tekrar deneyiniz.",
                parent=self
            )
            self.pwd_var.set("")
            self.ent_pwd.focus_set()
