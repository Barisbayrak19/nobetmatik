"""
Geliştirici Geri Bildirim ve İstek Formu Diyaloğu (Modern CustomTkinter Design)
Kullanıcıların karşılaştıkları hataları, özellik önerilerini ve teşekkür/görüşlerini
doğrudan geliştiriciye güvenli ve pratik biçimde iletmesini sağlar.
"""
import tkinter as tk
from tkinter import messagebox
import webbrowser
from typing import Optional
import customtkinter as ctk

from core.database import Database
from logic.feedback_service import FeedbackService, FeedbackData
from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_SUCCESS, COLOR_DANGER,
    COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, FONT_FAMILY, create_modern_button
)


class FeedbackDialog(ctk.CTkToplevel):
    def __init__(self, parent: tk.Widget, db: Database):
        super().__init__(parent)
        self.db = db
        self.school = self.db.get_school_info()

        self.title("💬 Geliştiriciye Geri Bildirim Gönder")
        self.geometry("680x640")
        self.minsize(600, 560)
        self.configure(fg_color=COLOR_BG)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        # 1. Alt Sabit Bar
        bottom_bar = ctk.CTkFrame(
            self,
            fg_color="#FFFFFF",
            height=54,
            corner_radius=0,
            border_width=1,
            border_color="#E2E8F0"
        )
        bottom_bar.pack(fill="x", side="bottom")
        bottom_bar.pack_propagate(False)

        btn_email = create_modern_button(
            bottom_bar,
            text="✉️ E-posta ile Gönder",
            command=self._open_email_client,
            variant="default",
            height=34
        )
        btn_email.pack(side="left", padx=20, pady=10)

        btn_cancel = create_modern_button(
            bottom_bar,
            text="Kapat",
            command=self.destroy,
            variant="default",
            height=34,
            width=95
        )
        btn_cancel.pack(side="right", padx=(8, 20), pady=10)

        self.btn_submit = create_modern_button(
            bottom_bar,
            text="📤 Geri Bildirimi İlet",
            command=self._submit_feedback,
            variant="primary",
            height=34,
            width=165
        )
        self.btn_submit.pack(side="right", pady=10)

        # 2. Ana Kart
        card = ctk.CTkFrame(
            self,
            fg_color="#FFFFFF",
            corner_radius=12,
            border_width=1,
            border_color="#E2E8F0"
        )
        card.pack(fill="both", expand=True, padx=18, pady=16)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=22, pady=18)

        hdr_row = ctk.CTkFrame(inner, fg_color="transparent")
        hdr_row.pack(fill="x")

        ctk.CTkLabel(
            hdr_row,
            text="💬 GELİŞTİRİCİYE GERİ BİLDİRİM & ÖNERİ GÖNDER",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color="#0F172A"
        ).pack(side="left", anchor="w")

        used_today, remaining = FeedbackService.get_daily_stats(self.db)
        ctk.CTkLabel(
            hdr_row,
            text=f"🛡️ Günlük Kalan Hak: {remaining}/{FeedbackService.DAILY_LIMIT}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color="#047857" if remaining > 0 else "#B91C1C",
            fg_color="#ECFDF5" if remaining > 0 else "#FEF2F2",
            corner_radius=6,
            padx=8,
            pady=2
        ).pack(side="right", anchor="e")

        ctk.CTkLabel(
            inner,
            text="Görüşleriniz, tespit ettiğiniz hatalar ve geliştirme önerileriniz programı mükemmelleştirmemize yardımcı olur.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color="#475569",
            justify="left",
            wraplength=580
        ).pack(anchor="w", pady=(2, 12))

        sep = ctk.CTkFrame(inner, fg_color="#F1F5F9", height=1)
        sep.pack(fill="x", pady=(0, 12))

        # Kategori Seçimi
        ctk.CTkLabel(
            inner,
            text="Bildirim Türü:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color="#0F172A"
        ).pack(anchor="w", pady=(0, 4))

        self.category_var = tk.StringVar(value="💡 Yeni Özellik / İyileştirme İsteği")
        categories = [
            "💡 Yeni Özellik / İyileştirme İsteği",
            "🐛 Hata / Sorun Bildirimi",
            "⭐ Genel Görüş & Teşekkür"
        ]
        cb_cat = ctk.CTkComboBox(
            inner,
            variable=self.category_var,
            values=categories,
            state="readonly",
            height=34,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            dropdown_font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            fg_color="#F8FAFC",
            border_color="#CBD5E1",
            button_color="#E2E8F0",
            button_hover_color="#CBD5E1",
            text_color="#0F172A",
            corner_radius=8
        )
        cb_cat.pack(fill="x", pady=(0, 12))

        # Okul ve Gönderen Satırı (Yan Yana)
        f_row1 = ctk.CTkFrame(inner, fg_color="transparent")
        f_row1.pack(fill="x", pady=(0, 10))
        f_row1.columnconfigure(0, weight=1, uniform="fb")
        f_row1.columnconfigure(1, weight=1, uniform="fb")

        f_col1 = ctk.CTkFrame(f_row1, fg_color="transparent")
        f_col1.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(f_col1, text="Okul Adı:", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A").pack(anchor="w", pady=(0, 3))
        self.school_var = tk.StringVar(value=self.school.name or "")
        ctk.CTkEntry(
            f_col1,
            textvariable=self.school_var,
            height=34,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            fg_color="#F8FAFC",
            border_color="#CBD5E1",
            text_color="#0F172A",
            corner_radius=8
        ).pack(fill="x")

        f_col2 = ctk.CTkFrame(f_row1, fg_color="transparent")
        f_col2.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ctk.CTkLabel(f_col2, text="Ad Soyad / Görev (İsteğe bağlı):", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A").pack(anchor="w", pady=(0, 3))
        self.sender_var = tk.StringVar(value=f"{self.school.principal_name} (Müdür)" if self.school.principal_name else "")
        ctk.CTkEntry(
            f_col2,
            textvariable=self.sender_var,
            height=34,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            fg_color="#F8FAFC",
            border_color="#CBD5E1",
            text_color="#0F172A",
            corner_radius=8
        ).pack(fill="x")

        # İletişim & Konu
        f_row2 = ctk.CTkFrame(inner, fg_color="transparent")
        f_row2.pack(fill="x", pady=(0, 10))
        f_row2.columnconfigure(0, weight=1, uniform="fb2")
        f_row2.columnconfigure(1, weight=1, uniform="fb2")

        f_col3 = ctk.CTkFrame(f_row2, fg_color="transparent")
        f_col3.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(f_col3, text="İletişim (Tel / E-posta):", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A").pack(anchor="w", pady=(0, 3))
        self.contact_var = tk.StringVar()
        ctk.CTkEntry(
            f_col3,
            textvariable=self.contact_var,
            height=34,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            fg_color="#F8FAFC",
            border_color="#CBD5E1",
            text_color="#0F172A",
            corner_radius=8
        ).pack(fill="x")

        f_col4 = ctk.CTkFrame(f_row2, fg_color="transparent")
        f_col4.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ctk.CTkLabel(f_col4, text="Konu / Başlık:", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A").pack(anchor="w", pady=(0, 3))
        self.subject_var = tk.StringVar()
        ctk.CTkEntry(
            f_col4,
            textvariable=self.subject_var,
            height=34,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            fg_color="#F8FAFC",
            border_color="#CBD5E1",
            text_color="#0F172A",
            corner_radius=8
        ).pack(fill="x")

        # Mesaj Detayı
        ctk.CTkLabel(
            inner,
            text="Açıklama / Mesajınız:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color="#0F172A"
        ).pack(anchor="w", pady=(0, 4))

        self.txt_message = ctk.CTkTextbox(
            inner,
            wrap="word",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            height=130,
            fg_color="#F8FAFC",
            text_color="#0F172A",
            border_width=1,
            border_color="#CBD5E1",
            corner_radius=8
        )
        self.txt_message.pack(fill="both", expand=True, pady=(0, 10))

        # Log Ekleme Checkbox'ı
        self.include_logs_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            inner,
            text="📋 Sistem Bilgilerini ve Son Hata Kayıtlarını İliştir (Kişisel/öğrenci verisi içermez)",
            variable=self.include_logs_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color="#0F172A",
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER
        ).pack(anchor="w", pady=(0, 4))

    def _collect_data(self) -> Optional[FeedbackData]:
        subject = self.subject_var.get().strip()
        message = self.txt_message.get("1.0", tk.END).strip()

        if not subject:
            messagebox.showwarning("Uyarı", "Lütfen bir konu başlığı yazınız.", parent=self)
            return None
        if not message:
            messagebox.showwarning("Uyarı", "Lütfen açıklama mesajınızı yazınız.", parent=self)
            return None

        include_logs = self.include_logs_var.get()
        logs_txt = FeedbackService.get_recent_logs() if include_logs else ""

        return FeedbackData(
            category=self.category_var.get(),
            school_name=self.school_var.get().strip() or "Belirtilmedi",
            sender_name=self.sender_var.get().strip(),
            contact=self.contact_var.get().strip(),
            subject=subject,
            message=message,
            include_logs=include_logs,
            logs_snippet=logs_txt
        )

    def _submit_feedback(self):
        data = self._collect_data()
        if not data:
            return

        self.btn_submit.configure(state="disabled")
        try:
            ok, msg = FeedbackService.send_feedback(data, self.db)
            if ok:
                messagebox.showinfo("Başarılı", msg, parent=self)
                self.destroy()
            else:
                messagebox.showwarning("Bilgi", msg, parent=self)
        except Exception as e:
            messagebox.showerror("Hata", f"Geri bildirim işlenirken hata oluştu: {e}", parent=self)
        finally:
            self.btn_submit.configure(state="normal")

    def _open_email_client(self):
        data = self._collect_data()
        if not data:
            return
        FeedbackService.save_local_feedback(data)
        mailto_url = FeedbackService.get_mailto_url(data)
        try:
            webbrowser.open(mailto_url)
            messagebox.showinfo(
                "E-posta Hazırlandı",
                "Varsayılan e-posta uygulamanız açıldı ve mesajınız hazırlandı.\nGönder tuşuna basarak iletebilirsiniz.",
                parent=self
            )
            self.destroy()
        except Exception as e:
            messagebox.showerror("Hata", f"E-posta istemcisi açılamadı: {e}", parent=self)
