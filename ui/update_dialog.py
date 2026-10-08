"""
Yazılım Güncelleme Penceresi (Software Update Dialog - Modern CustomTkinter)
GitHub Releases üzerinden yeni sürüm bilgilerini, yenilikleri ve indirme sürecini yönetir.
"""
import os
import sys
import threading
import tempfile
import webbrowser
from pathlib import Path
from typing import Dict, Any, Optional
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk

from core.config import APP_NAME, APP_VERSION
from core.logger import logger
from logic.update_service import UpdateService
from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_SUCCESS, COLOR_BORDER,
    COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, FONT_FAMILY
)

class UpdateDialog(ctk.CTkToplevel):
    def __init__(self, parent: Any, update_info: Dict[str, Any], update_service: UpdateService):
        super().__init__(parent)
        self.title("🔄 Yazılım Güncelleme Merkezi")
        self.geometry("620x530")
        self.minsize(540, 440)
        self.configure(fg_color=COLOR_BG)

        self.update_info = update_info
        self.update_service = update_service
        self.is_downloading = False
        self._cancel_download = False

        self.transient(parent)
        self.after(100, self.lift)
        self.after(150, self.focus_force)

        self._build_ui()

    def _build_ui(self):
        # 1. Üst Başlık Kartı
        top_frame = ctk.CTkFrame(self, fg_color=COLOR_PRIMARY, corner_radius=0)
        top_frame.pack(fill="x", side="top", ipady=10)

        f_inner_top = ctk.CTkFrame(top_frame, fg_color="transparent")
        f_inner_top.pack(fill="x", padx=20)

        lbl_title = ctk.CTkLabel(
            f_inner_top,
            text=f"🚀 YENİ SÜRÜM MEVCUT: {self.update_info.get('latest_version', '')}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_title.pack(anchor="w")

        lbl_desc = ctk.CTkLabel(
            f_inner_top,
            text=f"Mevcut Sürüm: v{APP_VERSION} ➔ Yeni Sürüm: {self.update_info.get('latest_version', '')}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color="#CBD5E1"
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        # 2. Ana İçerik Kartı
        content_card = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        content_card.pack(fill="both", expand=True, padx=16, pady=12)

        # Sürüm Başlığı ve Tarih
        f_rel_info = ctk.CTkFrame(content_card, fg_color="transparent")
        f_rel_info.pack(fill="x", padx=16, pady=(12, 6))

        title_text = self.update_info.get("title", "")
        ctk.CTkLabel(
            f_rel_info,
            text=f"📌 {title_text}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        ).pack(anchor="w")

        pub_at = self.update_info.get("published_at", "")[:10]
        if pub_at:
            ctk.CTkLabel(
                f_rel_info,
                text=f"Yayınlanma Tarihi: {pub_at}",
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=COLOR_TEXT_MUTED
            ).pack(anchor="w", pady=(1, 0))

        # Sürüm Notları (Changelog) Başlığı
        ctk.CTkLabel(
            content_card,
            text="📋 Bu Sürümdeki Yenilikler ve Değişiklikler:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        ).pack(anchor="w", padx=16, pady=(8, 4))

        # Sürüm Notları Kutusu (Scrollable Text)
        txt_frame = ctk.CTkFrame(content_card, fg_color="#F8FAFC", corner_radius=6, border_width=1, border_color=COLOR_BORDER)
        txt_frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        self.txt_body = ctk.CTkTextbox(
            txt_frame,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLOR_TEXT_MAIN,
            fg_color="transparent",
            wrap="word"
        )
        self.txt_body.pack(fill="both", expand=True, padx=8, pady=8)
        self.txt_body.insert("1.0", self.update_info.get("body", "Sürüm notu bulunamadı."))
        self.txt_body.configure(state="disabled")

        # 3. İndirme ve İlerleme Durumu Alanı
        self.f_progress = ctk.CTkFrame(content_card, fg_color="transparent")
        self.f_progress.pack(fill="x", padx=16, pady=(0, 10))

        self.lbl_progress = ctk.CTkLabel(
            self.f_progress,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_progress.pack(anchor="w", pady=(0, 4))

        self.progress_bar = ctk.CTkProgressBar(self.f_progress)
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)
        self.f_progress.pack_forget()  # Başlangıçta gizli

        # 4. Alt Butonlar Alanı
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", side="bottom", padx=16, pady=(0, 14))

        download_url = self.update_info.get("download_url")
        if download_url:
            self.btn_download = ctk.CTkButton(
                bottom_frame,
                text="⬇️ Şimdi İndir ve Güncelle",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                fg_color=COLOR_SUCCESS,
                hover_color="#047857",
                height=34,
                corner_radius=6,
                command=self._start_download
            )
            self.btn_download.pack(side="left", padx=(0, 8))

        btn_github = ctk.CTkButton(
            bottom_frame,
            text="🌐 GitHub'da İncele",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            fg_color="#334155",
            hover_color="#1E293B",
            height=34,
            corner_radius=6,
            command=self._open_github
        )
        btn_github.pack(side="left", padx=(0, 8))

        self.btn_close = ctk.CTkButton(
            bottom_frame,
            text="Daha Sonra",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            fg_color="#94A3B8",
            hover_color="#64748B",
            height=34,
            width=90,
            corner_radius=6,
            command=self.destroy
        )
        self.btn_close.pack(side="right")

    def _open_github(self):
        url = self.update_info.get("html_url")
        if url:
            webbrowser.open(url)

    def _start_download(self):
        download_url = self.update_info.get("download_url")
        if not download_url:
            messagebox.showwarning("Uyarı", "Doğrudan indirilebilir kurulum dosyası (.exe) bulunamadı.\nLütfen 'GitHub'da İncele' butonunu kullanınız.", parent=self)
            return

        self.is_downloading = True
        self.btn_download.configure(state="disabled")
        self.btn_close.configure(text="İptal")
        self.f_progress.pack(fill="x", padx=16, pady=(0, 10))

        asset_name = self.update_info.get("asset_name") or f"NobetMatik_Setup_{self.update_info.get('latest_version')}.exe"
        temp_dir = Path(tempfile.gettempdir())
        self.target_path = temp_dir / asset_name

        threading.Thread(target=self._download_worker, daemon=True).start()

    def _download_worker(self):
        try:
            def progress(downloaded, total):
                if total > 0:
                    pct = downloaded / total
                    mb_cur = downloaded / (1024 * 1024)
                    mb_tot = total / (1024 * 1024)
                    self.after(0, lambda: self._update_progress_ui(pct, f"İndiriliyor: %{int(pct*100)} ({mb_cur:.1f} MB / {mb_tot:.1f} MB)"))
                else:
                    mb_cur = downloaded / (1024 * 1024)
                    self.after(0, lambda: self._update_progress_ui(0.5, f"İndiriliyor: {mb_cur:.1f} MB"))

            success = self.update_service.download_installer(
                download_url=self.update_info["download_url"],
                target_path=self.target_path,
                progress_callback=progress,
                cancel_check=lambda: self._cancel_download
            )

            if success:
                self.after(0, self._on_download_complete)
        except Exception as e:
            self.after(0, lambda err=e: self._on_download_error(err))

    def _update_progress_ui(self, pct: float, text: str):
        self.progress_bar.set(pct)
        self.lbl_progress.configure(text=text)

    def _on_download_complete(self):
        self.progress_bar.set(1.0)
        self.lbl_progress.configure(text="✔ İndirme tamamlandı! Kurulum başlatılıyor...", text_color=COLOR_SUCCESS)

        ask = messagebox.askyesno(
            "Güncelleme Hazır",
            f"Yeni sürüm ({self.update_info.get('latest_version')}) başarıyla indirildi.\n\n"
            f"Kurulumun tamamlanabilmesi için mevcut NöbetMatik uygulaması kapatılacaktır.\n"
            f"(Okul verileriniz korunacaktır).\n\n"
            f"Şimdi kurulsun mu?",
            parent=self
        )
        if ask:
            try:
                self.update_service.launch_installer_and_exit(self.target_path)
            except Exception as e:
                messagebox.showerror("Hata", f"Kurulum dosyası başlatılamadı:\n{e}", parent=self)
                self.btn_download.configure(state="normal")
                self.btn_close.configure(text="Kapat")
        else:
            self.btn_download.configure(state="normal", text="🚀 Kurulumu Başlat")
            self.btn_close.configure(text="Kapat")

    def _on_download_error(self, err: Exception):
        self.is_downloading = False
        self.lbl_progress.configure(text=f"❌ İndirme başarısız: {err}", text_color="#DC2626")
        self.btn_download.configure(state="normal")
        self.btn_close.configure(text="Kapat")
        messagebox.showerror("İndirme Hatası", f"Güncelleme dosyası indirilemedi:\n{err}", parent=self)
