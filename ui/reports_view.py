"""
Raporlar ve Çıktı Yönetim Ekranı (Modern UI/UX Redesign)
Resmi nöbet çizelgeleri, ders programları el çizelgeleri, çarşaf tablolar ve personel devam takip merkezi.
"""
import tkinter as tk
from tkinter import filedialog
from typing import Callable, Optional, Dict, Any, List
from pathlib import Path
import os
import subprocess
import datetime
import traceback
import customtkinter as ctk

from core.database import Database
from logic.export_service import ExportService
from logic.substitution_service import get_monthly_ek_ders_summary
from core.config import EXPORTS_DIR
from core.logger import logger
from ui.timetable_export_dialog import TimetableExportDialog
from ui.ek_ders_dialog import EkDersMonthlySummaryDialog
from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_PRIMARY_HOVER,
    COLOR_SUCCESS, COLOR_BORDER, COLOR_BORDER_STRONG,
    COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, FONT_FAMILY
)

TURKISH_MONTHS = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
]


class ModernReportErrorDialog(ctk.CTkToplevel):
    """
    Kullanıcı dostu, profesyonel hata diyalogu.
    Teknik Python stacktrace/hatalarını ana mesaj olarak göstermez;
    istendiğinde açılabilen 'Teknik ayrıntıları göster' paneli sunar.
    """
    def __init__(
        self,
        parent: tk.Widget,
        title: str = "PDF OLUŞTURULAMADI",
        message: str = "Belge oluşturulurken bir sorun oluştu.",
        detail: str = "",
        retry_callback: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent)
        self.title("İşlem Uyarısı")
        self.retry_callback = retry_callback
        self.detail_text = detail.strip()
        self.is_detail_expanded = False

        self.geometry("480x260")
        self.minsize(440, 240)
        self.resizable(False, False)
        self.configure(fg_color="#FFFFFF")

        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self._build_ui(title, message)
        self._center_window(parent)

    def _center_window(self, parent: tk.Widget):
        self.update_idletasks()
        try:
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            w = self.winfo_width()
            h = self.winfo_height()
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 2)
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _build_ui(self, title_text: str, message_text: str):
        content_frame = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0)
        content_frame.pack(fill="both", expand=True, padx=24, pady=20)

        # Üst İkon ve Başlık
        header_row = ctk.CTkFrame(content_frame, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 10))

        lbl_icon = ctk.CTkLabel(
            header_row,
            text="⚠️",
            font=ctk.CTkFont(size=24)
        )
        lbl_icon.pack(side="left", padx=(0, 12))

        title_box = ctk.CTkFrame(header_row, fg_color="transparent")
        title_box.pack(side="left", fill="x", expand=True)

        lbl_title = ctk.CTkLabel(
            title_box,
            text=title_text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color="#DC2626",
            anchor="w"
        )
        lbl_title.pack(anchor="w")

        lbl_msg = ctk.CTkLabel(
            title_box,
            text=message_text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color="#334155",
            anchor="w",
            wraplength=340,
            justify="left"
        )
        lbl_msg.pack(anchor="w", pady=(2, 0))

        # Yardım İpucu
        tip_frame = ctk.CTkFrame(
            content_frame,
            fg_color="#F8FAFC",
            corner_radius=6,
            border_width=1,
            border_color="#E2E8F0"
        )
        tip_frame.pack(fill="x", pady=(0, 12), ipady=6, ipadx=8)

        lbl_tip = ctk.CTkLabel(
            tip_frame,
            text="💡 İpucu: Oluşturulacak dosya başka bir programda (Acrobat, Excel vb.) açıksa lütfen kapatıp tekrar deneyiniz.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color="#475569",
            wraplength=400,
            justify="left"
        )
        lbl_tip.pack(anchor="w", padx=6)

        # Teknik Ayrıntılar Butonu
        if self.detail_text:
            self.btn_toggle_detail = ctk.CTkButton(
                content_frame,
                text="▼ Teknik ayrıntıları göster",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                fg_color="transparent",
                hover_color="#F1F5F9",
                text_color="#475569",
                height=26,
                anchor="w",
                command=self._toggle_detail
            )
            self.btn_toggle_detail.pack(anchor="w", pady=(0, 8))

            self.detail_box = ctk.CTkTextbox(
                content_frame,
                height=70,
                font=ctk.CTkFont(family="Consolas", size=12),
                fg_color="#F8FAFC",
                text_color="#334155",
                border_width=1,
                border_color="#E2E8F0",
                wrap="word"
            )
            self.detail_box.insert("1.0", self.detail_text)
            self.detail_box.configure(state="disabled")

        # Butonlar Alanı
        btn_row = ctk.CTkFrame(content_frame, fg_color="transparent")
        btn_row.pack(side="bottom", fill="x", pady=(8, 0))

        btn_close = ctk.CTkButton(
            btn_row,
            text="Kapat",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color="#F8FAFC",
            hover_color="#F1F5F9",
            text_color="#334155",
            border_width=1,
            border_color="#CBD5E1",
            height=34,
            width=90,
            corner_radius=6,
            command=self.destroy
        )
        btn_close.pack(side="right", padx=(8, 0))

        if self.retry_callback:
            btn_retry = ctk.CTkButton(
                btn_row,
                text="Tekrar Dene",
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                fg_color=COLOR_PRIMARY,
                hover_color=COLOR_PRIMARY_HOVER,
                text_color="#FFFFFF",
                height=34,
                width=110,
                corner_radius=6,
                command=self._do_retry
            )
            btn_retry.pack(side="right")

    def _toggle_detail(self):
        self.is_detail_expanded = not self.is_detail_expanded
        if self.is_detail_expanded:
            self.btn_toggle_detail.configure(text="▲ Teknik ayrıntıları gizle")
            self.geometry("480x350")
            self.detail_box.pack(fill="x", pady=(0, 10))
        else:
            self.btn_toggle_detail.configure(text="▼ Teknik ayrıntıları göster")
            self.detail_box.pack_forget()
            self.geometry("480x260")

    def _do_retry(self):
        cb = self.retry_callback
        self.destroy()
        if cb:
            cb()


class ModernReportSuccessDialog(ctk.CTkToplevel):
    """Belge oluşturma başarılı onay penceresi."""
    def __init__(self, parent: tk.Widget, file_path: Path):
        super().__init__(parent)
        self.file_path = file_path
        self.title("Belge Hazır")
        self.geometry("440x210")
        self.resizable(False, False)
        self.configure(fg_color="#FFFFFF")

        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self._build_ui()
        self._center_window(parent)

    def _center_window(self, parent: tk.Widget):
        self.update_idletasks()
        try:
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            w = self.winfo_width()
            h = self.winfo_height()
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 2)
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _build_ui(self):
        box = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0)
        box.pack(fill="both", expand=True, padx=24, pady=20)

        header_row = ctk.CTkFrame(box, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 12))

        lbl_icon = ctk.CTkLabel(header_row, text="✅", font=ctk.CTkFont(size=24))
        lbl_icon.pack(side="left", padx=(0, 10))

        title_box = ctk.CTkFrame(header_row, fg_color="transparent")
        title_box.pack(side="left", fill="x", expand=True)

        lbl_title = ctk.CTkLabel(
            title_box,
            text="BELGE OLUŞTURULDU",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color="#059669"
        )
        lbl_title.pack(anchor="w")

        lbl_msg = ctk.CTkLabel(
            title_box,
            text="Belge başarıyla oluşturuldu ve kaydedildi.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color="#475569"
        )
        lbl_msg.pack(anchor="w", pady=(1, 0))

        # Dosya Adı Kartı
        file_card = ctk.CTkFrame(
            box,
            fg_color="#F8FAFC",
            corner_radius=6,
            border_width=1,
            border_color="#E2E8F0"
        )
        file_card.pack(fill="x", pady=(0, 14), ipady=6, ipadx=8)

        lbl_filename = ctk.CTkLabel(
            file_card,
            text=f"📁 {self.file_path.name}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color="#0F172A",
            wraplength=380,
            justify="left"
        )
        lbl_filename.pack(anchor="w", padx=6)

        # Butonlar
        btn_row = ctk.CTkFrame(box, fg_color="transparent")
        btn_row.pack(side="bottom", fill="x")

        btn_close = ctk.CTkButton(
            btn_row,
            text="Kapat",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color="#F8FAFC",
            hover_color="#F1F5F9",
            text_color="#334155",
            border_width=1,
            border_color="#CBD5E1",
            height=34,
            width=80,
            corner_radius=6,
            command=self.destroy
        )
        btn_close.pack(side="right", padx=(8, 0))

        btn_open = ctk.CTkButton(
            btn_row,
            text="Belgeyi Aç",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            text_color="#FFFFFF",
            height=34,
            width=110,
            corner_radius=6,
            command=self._open_file
        )
        btn_open.pack(side="right")

    def _open_file(self):
        try:
            os.startfile(str(self.file_path))
        except Exception:
            try:
                subprocess.Popen(["explorer", str(self.file_path)])
            except Exception as e:
                logger.warning(f"Dosya açılamadı: {e}")
        self.destroy()


class ReportsView(ctk.CTkFrame):
    """
    Modern Okul Yönetim Merkezi - Raporlar ve Çıktı Yönetim Ekranı.
    Tek ana pencereye gömülü, modern kartlar ve segmented navigation yapısına sahiptir.
    """
    def __init__(
        self,
        parent: tk.Widget,
        db: Database,
        get_current_week: Optional[Callable[[], str]] = None,
        open_print_preview_callback: Optional[Callable[[], None]] = None,
        open_attendance_callback: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent, fg_color=COLOR_BG, corner_radius=0)
        self.db = db
        self.get_current_week = get_current_week or (lambda: datetime.date(2026, 9, 28).isoformat())
        self.open_print_preview_callback = open_print_preview_callback
        self.open_attendance_callback = open_attendance_callback
        self.export_service = ExportService(self.db)

        self.current_tab = "duty"
        self.tab_buttons: Dict[str, ctk.CTkButton] = {}
        self.tab_frames: Dict[str, ctk.CTkFrame] = {}

        self._build_ui()

    def _build_ui(self):
        # 1. ÜST BAŞLIK VE SEGMENTED NAVİGASYON ÇUBUĞU
        top_bar = ctk.CTkFrame(
            self,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E2E8F0"
        )
        top_bar.pack(fill="x", padx=16, pady=(14, 12))

        header_inner = ctk.CTkFrame(top_bar, fg_color="transparent")
        header_inner.pack(fill="x", padx=16, pady=12)

        # Başlık ve Alt Başlık
        title_box = ctk.CTkFrame(header_inner, fg_color="transparent")
        title_box.pack(side="left", fill="y")

        lbl_title = ctk.CTkLabel(
            title_box,
            text="📊 BELGE VE ÇIKTI MERKEZİ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color="#0F172A"
        )
        lbl_title.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            title_box,
            text="Resmi belgeler, çizelgeler ve okul çıktılarını tek yerden yönetin.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color="#475569"
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # Modern Segmented Navigation
        nav_container = ctk.CTkFrame(
            header_inner,
            fg_color="#F1F5F9",
            corner_radius=10,
            border_width=1,
            border_color="#E2E8F0",
            height=42
        )
        nav_container.pack(side="right", padx=(10, 0))

        tabs_meta = [
            ("duty", "📅 Nöbet Çizelgeleri"),
            ("timetable", "📚 Ders Programları"),
            ("attendance", "👥 Personel Devam"),
            ("ek_ders", "💰 Ek Ders Hakediş")
        ]

        for key, label in tabs_meta:
            btn = ctk.CTkButton(
                nav_container,
                text=label,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                fg_color=COLOR_PRIMARY if key == "duty" else "transparent",
                hover_color=COLOR_PRIMARY_HOVER if key == "duty" else "#E2E8F0",
                text_color="#FFFFFF" if key == "duty" else "#334155",
                height=34,
                corner_radius=8,
                command=lambda k=key: self.switch_tab(k)
            )
            btn.pack(side="left", padx=4, pady=4)
            self.tab_buttons[key] = btn

        # 2. İÇERİK KONTEYNERİ (Scrollable Frame ile tüm ekran çözünürlüklerine uyumlu)
        self.scroll_content = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0
        )
        self.scroll_content.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        # Sekmelerin İçerik Panellerini Oluştur
        self._build_duty_tab(self.scroll_content)
        self._build_timetable_tab(self.scroll_content)
        self._build_attendance_tab(self.scroll_content)
        self._build_ek_ders_tab(self.scroll_content)

        # Başlangıçta Nöbet Çizelgeleri sekmesini aç
        self.switch_tab("duty")

    def switch_tab(self, tab_key: str):
        """Segmented navigation geçiş kontrolü."""
        self.current_tab = tab_key

        for key, btn in self.tab_buttons.items():
            is_active = (key == tab_key)
            btn.configure(
                fg_color=COLOR_PRIMARY if is_active else "transparent",
                hover_color=COLOR_PRIMARY_HOVER if is_active else "#E2E8F0",
                text_color="#FFFFFF" if is_active else "#334155",
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")
            )

        for key, frame in self.tab_frames.items():
            if key == tab_key:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

        if tab_key == "ek_ders":
            self._refresh_ek_ders_tab()
        elif tab_key == "attendance":
            self._update_attendance_ek_ders_badge()

    # =========================================================================
    # MODÜL 1: NÖBET ÇİZELGELERİ
    # =========================================================================
    def _build_duty_tab(self, parent: ctk.CTkFrame):
        tab_frame = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0)
        self.tab_frames["duty"] = tab_frame

        # Modül Başlığı ve Aktif Hafta Göstergesi
        header_banner = ctk.CTkFrame(
            tab_frame,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E2E8F0"
        )
        header_banner.pack(fill="x", pady=(0, 12))

        b_inner = ctk.CTkFrame(header_banner, fg_color="transparent")
        b_inner.pack(fill="x", padx=18, pady=14)

        left_b = ctk.CTkFrame(b_inner, fg_color="transparent")
        left_b.pack(side="left", fill="y")

        lbl_t = ctk.CTkLabel(
            left_b,
            text="NÖBET ÇİZELGELERİ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color="#0F172A"
        )
        lbl_t.pack(anchor="w")

        lbl_s = ctk.CTkLabel(
            left_b,
            text="Aktif haftaya ait resmi nöbet çizelgelerini görüntüleyin ve MEB standartlarında dışa aktarın.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color="#475569"
        )
        lbl_s.pack(anchor="w", pady=(2, 0))

        # Hafta Rozeti
        week_str = self.get_current_week()
        badge_frame = ctk.CTkFrame(
            b_inner,
            fg_color="#EFF6FF",
            corner_radius=8,
            border_width=1,
            border_color="#BFDBFE"
        )
        badge_frame.pack(side="right", padx=(8, 0), pady=2)

        lbl_week_badge = ctk.CTkLabel(
            badge_frame,
            text=f"📅 Çalışma Haftası: {week_str}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color="#1D4ED8"
        )
        lbl_week_badge.pack(padx=12, pady=6)

        # Kartlar Düzeni (Yan yana 2 eşit kart)
        cards_container = ctk.CTkFrame(tab_frame, fg_color="transparent")
        cards_container.pack(fill="both", expand=True)
        cards_container.columnconfigure(0, weight=1, uniform="duty_card")
        cards_container.columnconfigure(1, weight=1, uniform="duty_card")

        # KART 1: CANLI BASKI VE ÖNİZLEME
        card_preview = ctk.CTkFrame(
            cards_container,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E2E8F0"
        )
        card_preview.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=0)

        p_inner = ctk.CTkFrame(card_preview, fg_color="transparent")
        p_inner.pack(fill="both", expand=True, padx=18, pady=18)

        lbl_cp_title = ctk.CTkLabel(
            p_inner,
            text="🖨️ CANLI BASKI VE ÖNİZLEME",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color="#0F172A"
        )
        lbl_cp_title.pack(anchor="w")

        lbl_cp_desc = ctk.CTkLabel(
            p_inner,
            text="Nöbet çizelgesini yazdırmadan önce görsel olarak inceleyin, yakınlaştırın ve doğrudan bağlı yazıcıya gönderin.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color="#475569",
            wraplength=420,
            justify="left"
        )
        lbl_cp_desc.pack(anchor="w", pady=(6, 16))

        btn_preview = ctk.CTkButton(
            p_inner,
            text="🔍 Baskı Önizleme Penceresini Aç",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            text_color="#FFFFFF",
            height=40,
            corner_radius=8,
            command=self._open_print_preview
        )
        btn_preview.pack(fill="x", pady=(0, 10))

        btn_html = ctk.CTkButton(
            p_inner,
            text="🌐 Yazdırılabilir HTML Sayfası Olarak Aç (.html)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color="#F8FAFC",
            hover_color="#E2E8F0",
            text_color="#0F172A",
            border_width=1,
            border_color="#CBD5E1",
            height=38,
            corner_radius=8,
            command=self._export_duty_html
        )
        btn_html.pack(fill="x", pady=(0, 14))

        lbl_preview_note = ctk.CTkLabel(
            p_inner,
            text="⚡ Baskı sayfası A4 yatay formata göre otomatik ölçeklenir.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color="#64748B"
        )
        lbl_preview_note.pack(anchor="w")

        # KART 2: RESMİ ÇIKTI FORMATLARI
        card_formats = ctk.CTkFrame(
            cards_container,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E2E8F0"
        )
        card_formats.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=0)

        f_inner = ctk.CTkFrame(card_formats, fg_color="transparent")
        f_inner.pack(fill="both", expand=True, padx=18, pady=18)

        lbl_cf_title = ctk.CTkLabel(
            f_inner,
            text="💾 RESMİ ÇIKTI FORMATLARI",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color="#0F172A"
        )
        lbl_cf_title.pack(anchor="w")

        lbl_cf_desc = ctk.CTkLabel(
            f_inner,
            text="Resmi imza bloğu ve kurum başlığıyla birlikte standart belgeler üretin:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color="#475569"
        )
        lbl_cf_desc.pack(anchor="w", pady=(6, 14))

        # Format Butonları
        export_buttons = [
            ("📄 PDF Nöbet Çizelgesi Kaydet (.pdf)", self._export_duty_pdf),
            ("📊 Excel Nöbet Çizelgesi Kaydet (.xlsx)", self._export_duty_excel),
            ("📝 Word Belgesi Olarak Kaydet (.docx)", self._export_duty_word),
            ("📑 CSV Listesi Olarak Kaydet (.csv)", self._export_duty_csv),
        ]

        for btn_text, cmd in export_buttons:
            b = ctk.CTkButton(
                f_inner,
                text=btn_text,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                fg_color="#F8FAFC",
                hover_color="#E2E8F0",
                text_color="#0F172A",
                border_width=1,
                border_color="#CBD5E1",
                height=36,
                corner_radius=8,
                anchor="w",
                command=cmd
            )
            b.pack(fill="x", pady=4)

        btn_duty_log = ctk.CTkButton(
            f_inner,
            text="📖 Resmi Günlük Nöbet Defteri / Rapor Sayfası (.pdf)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color="#0F766E",
            hover_color="#115E59",
            text_color="#FFFFFF",
            border_width=0,
            height=38,
            corner_radius=8,
            anchor="w",
            command=self._open_duty_log_dialog
        )
        btn_duty_log.pack(fill="x", pady=(10, 4))

        self.lbl_duty_last_info = ctk.CTkLabel(
            f_inner,
            text=self._get_duty_last_exported_info(),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color="#475569"
        )
        self.lbl_duty_last_info.pack(anchor="w", pady=(8, 0))

    # =========================================================================
    # MODÜL 2: DERS PROGRAMLARI
    # =========================================================================
    def _build_timetable_tab(self, parent: ctk.CTkFrame):
        tab_frame = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0)
        self.tab_frames["timetable"] = tab_frame

        header_banner = ctk.CTkFrame(
            tab_frame,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E2E8F0"
        )
        header_banner.pack(fill="x", pady=(0, 12))

        b_inner = ctk.CTkFrame(header_banner, fg_color="transparent")
        b_inner.pack(fill="x", padx=18, pady=14)

        left_b = ctk.CTkFrame(b_inner, fg_color="transparent")
        left_b.pack(side="left", fill="both", expand=True)

        lbl_t = ctk.CTkLabel(
            left_b,
            text="DERS PROGRAMLARI VE ÇİZELGELER",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color="#0F172A"
        )
        lbl_t.pack(anchor="w")

        lbl_s = ctk.CTkLabel(
            left_b,
            text="e-Okul veya Excel'den aktarılan ders programlarına ait el programları, sınıf tabloları ve analizler.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color="#475569"
        )
        lbl_s.pack(anchor="w", pady=(2, 0))

        btn_detailed = ctk.CTkButton(
            b_inner,
            text="🔍 Detaylı Önizleme & Çıktı Merkezi",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            text_color="#FFFFFF",
            corner_radius=8,
            height=38,
            command=self._open_timetable_dialog
        )
        btn_detailed.pack(side="right", padx=(10, 0))

        # 2x2 Izgara Düzeni
        grid = ctk.CTkFrame(tab_frame, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        grid.columnconfigure(0, weight=1, uniform="tt_col")
        grid.columnconfigure(1, weight=1, uniform="tt_col")

        # Kart 1: Öğretmen El Programları
        self._build_tt_card(
            grid,
            row=0, col=0,
            padx=(0, 6), pady=(0, 10),
            title="👤 ÖĞRETMEN EL PROGRAMLARI",
            desc="Her öğretmene ait haftalık bireysel ders dağıtım çizelgeleri.",
            actions=[
                ("📄 Tüm Öğretmenler PDF Kitapçığı", True, lambda: self._quick_tt_export("teacher_pdf")),
                ("📊 Tüm Öğretmenler Excel Tablosu", False, lambda: self._quick_tt_export("teacher_excel")),
            ]
        )

        # Kart 2: Sınıf / Şube Programları
        self._build_tt_card(
            grid,
            row=0, col=1,
            padx=(6, 0), pady=(0, 10),
            title="🏫 SINIF VE ŞUBE PROGRAMLARI",
            desc="Tüm sınıfların haftalık ders ve nöbet saatleri çizelgesi.",
            actions=[
                ("📄 Tüm Sınıflar PDF Kitapçığı", True, lambda: self._quick_tt_export("class_pdf")),
                ("📊 Tüm Sınıflar Excel Tablosu", False, lambda: self._quick_tt_export("class_excel")),
            ]
        )

        # Kart 3: Genel Çarşaf Program
        self._build_tt_card(
            grid,
            row=1, col=0,
            padx=(0, 6), pady=(0, 0),
            title="📊 GENEL ÇARŞAF PROGRAM",
            desc="Tüm okulun tek bir büyük matriste ders dağılım tablosu.",
            actions=[
                ("📊 Çarşaf Program Excel İndir (.xlsx)", False, lambda: self._quick_tt_export("master_excel")),
            ]
        )

        # Kart 4: Boş Ders Saatleri
        self._build_tt_card(
            grid,
            row=1, col=1,
            padx=(6, 0), pady=(0, 0),
            title="🟢 BOŞ DERS SAATLERİ VE ANALİZ",
            desc="Öğretmenlerin gün ve saat bazında boş olduğu nöbete uygun saatler.",
            actions=[
                ("📊 Boş Dersler Analiz Çizelgesi (.xlsx)", False, lambda: self._quick_tt_export("free_excel")),
            ]
        )

    def _build_tt_card(
        self,
        parent: ctk.CTkFrame,
        row: int,
        col: int,
        padx: tuple,
        pady: tuple,
        title: str,
        desc: str,
        actions: List[tuple]
    ):
        card = ctk.CTkFrame(
            parent,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E2E8F0"
        )
        card.grid(row=row, column=col, sticky="nsew", padx=padx, pady=pady)

        c_inner = ctk.CTkFrame(card, fg_color="transparent")
        c_inner.pack(fill="both", expand=True, padx=18, pady=18)

        lbl_title = ctk.CTkLabel(
            c_inner,
            text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color="#0F172A"
        )
        lbl_title.pack(anchor="w")

        lbl_desc = ctk.CTkLabel(
            c_inner,
            text=desc,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color="#475569"
        )
        lbl_desc.pack(anchor="w", pady=(4, 14))

        for text, is_primary, command in actions:
            btn = ctk.CTkButton(
                c_inner,
                text=text,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                fg_color=COLOR_PRIMARY if is_primary else "#F8FAFC",
                hover_color=COLOR_PRIMARY_HOVER if is_primary else "#E2E8F0",
                text_color="#FFFFFF" if is_primary else "#0F172A",
                border_width=0 if is_primary else 1,
                border_color="#CBD5E1",
                height=38,
                corner_radius=8,
                command=command
            )
            btn.pack(fill="x", pady=4)

    # =========================================================================
    # MODÜL 3: PERSONEL DEVAM (İstenilen Tasarım)
    # =========================================================================
    def _build_attendance_tab(self, parent: ctk.CTkFrame):
        tab_frame = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0)
        self.tab_frames["attendance"] = tab_frame

        # Üst Başlık Banner
        header_banner = ctk.CTkFrame(
            tab_frame,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E2E8F0"
        )
        header_banner.pack(fill="x", pady=(0, 12))

        b_inner = ctk.CTkFrame(header_banner, fg_color="transparent")
        b_inner.pack(fill="x", padx=18, pady=14)

        lbl_t = ctk.CTkLabel(
            b_inner,
            text="PERSONEL DEVAM",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color="#0F172A"
        )
        lbl_t.pack(anchor="w")

        lbl_s = ctk.CTkLabel(
            b_inner,
            text="Aylık resmi devam ve imza belgelerini yönetin.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color="#475569"
        )
        lbl_s.pack(anchor="w", pady=(2, 0))

        # İki Ana Kart İçeren Grid
        att_grid = ctk.CTkFrame(tab_frame, fg_color="transparent")
        att_grid.pack(fill="both", expand=True)
        att_grid.columnconfigure(0, weight=1, uniform="att_col")
        att_grid.columnconfigure(1, weight=1, uniform="att_col")

        # ---------------------------------------------------------------------
        # 1. ANA KART: 📄 AYLIK İMZA ÇİZELGESİ
        # ---------------------------------------------------------------------
        card_sign = ctk.CTkFrame(
            att_grid,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E2E8F0"
        )
        card_sign.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=0)

        cs_inner = ctk.CTkFrame(card_sign, fg_color="transparent")
        cs_inner.pack(fill="both", expand=True, padx=18, pady=18)

        lbl_cs_title = ctk.CTkLabel(
            cs_inner,
            text="📄 AYLIK İMZA ÇİZELGESİ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color="#0F172A"
        )
        lbl_cs_title.pack(anchor="w")

        lbl_cs_desc = ctk.CTkLabel(
            cs_inner,
            text="Seçilen döneme ait tüm okul personeli için resmi devam-devamsızlık imza föyünü oluşturun.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color="#475569",
            wraplength=420,
            justify="left"
        )
        lbl_cs_desc.pack(anchor="w", pady=(6, 16))

        # Yıl ve Ay Seçim Alanı
        selectors_frame = ctk.CTkFrame(
            cs_inner,
            fg_color="#F8FAFC",
            corner_radius=8,
            border_width=1,
            border_color="#E2E8F0"
        )
        selectors_frame.pack(fill="x", pady=(0, 16), padx=2, ipady=10, ipadx=10)

        now = datetime.date.today()

        # Yıl Seçimi
        lbl_year = ctk.CTkLabel(
            selectors_frame,
            text="Yıl",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color="#0F172A"
        )
        lbl_year.pack(anchor="w", padx=10, pady=(6, 2))

        year_options = [str(y) for y in range(now.year - 2, now.year + 3)]
        if str(now.year) not in year_options:
            year_options.append(str(now.year))
            year_options.sort()

        self.att_year_var = ctk.StringVar(value=str(now.year))
        cb_year = ctk.CTkComboBox(
            selectors_frame,
            values=year_options,
            variable=self.att_year_var,
            width=180,
            height=34,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            dropdown_font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            state="readonly",
            command=lambda _: self._update_attendance_ek_ders_badge()
        )
        cb_year.pack(anchor="w", padx=10, pady=(0, 10))

        # Ay Seçimi
        lbl_month = ctk.CTkLabel(
            selectors_frame,
            text="Ay",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color="#0F172A"
        )
        lbl_month.pack(anchor="w", padx=10, pady=(0, 2))

        current_month_name = TURKISH_MONTHS[now.month - 1]
        self.att_month_var = ctk.StringVar(value=current_month_name)
        cb_month = ctk.CTkComboBox(
            selectors_frame,
            values=TURKISH_MONTHS,
            variable=self.att_month_var,
            width=180,
            height=34,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            dropdown_font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            state="readonly",
            command=lambda _: self._update_attendance_ek_ders_badge()
        )
        cb_month.pack(anchor="w", padx=10, pady=(0, 6))

        # Ek Ders Hak Ediş Bildirim Kartı / Rozeti
        self.att_ek_ders_banner = ctk.CTkFrame(
            cs_inner,
            fg_color="#F0FDF4",
            corner_radius=8,
            border_width=1,
            border_color="#BBF7D0"
        )
        self.att_ek_ders_banner.pack(fill="x", pady=(0, 12), ipady=4, ipadx=6)

        self.lbl_att_ek_badge = ctk.CTkLabel(
            self.att_ek_ders_banner,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color="#166534",
            anchor="w",
            wraplength=280,
            justify="left"
        )
        self.lbl_att_ek_badge.pack(side="left", padx=10, fill="x", expand=True)

        self.btn_att_goto_ek = ctk.CTkButton(
            self.att_ek_ders_banner,
            text="İcmali Gör →",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color="#16A34A",
            hover_color="#15803D",
            text_color="#FFFFFF",
            height=28,
            width=90,
            corner_radius=6,
            command=lambda: self.switch_tab("ek_ders")
        )
        self.btn_att_goto_ek.pack(side="right", padx=10)

        self._update_attendance_ek_ders_badge()

        # Ana İşlem Butonu: [ PDF OLUŞTUR ] (Mavi ve Belirgin)
        btn_generate_pdf = ctk.CTkButton(
            cs_inner,
            text="📄 PDF OLUŞTUR",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            text_color="#FFFFFF",
            height=40,
            corner_radius=8,
            command=self._export_attendance_pdf
        )
        btn_generate_pdf.pack(fill="x", pady=(0, 8))

        # Küçük Sistem Bilgisi (Son oluşturulan)
        self.lbl_att_last_exported = ctk.CTkLabel(
            cs_inner,
            text=self._get_att_last_exported_info(),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color="#475569"
        )
        self.lbl_att_last_exported.pack(anchor="w", pady=(0, 10))

        # İkincil İşlem: Excel Çıktısı
        btn_att_excel = ctk.CTkButton(
            cs_inner,
            text="📊 Excel Tablosu Olarak İndir (.xlsx)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color="#F8FAFC",
            hover_color="#E2E8F0",
            text_color="#0F172A",
            border_width=1,
            border_color="#CBD5E1",
            height=36,
            corner_radius=8,
            command=self._export_attendance_excel
        )
        btn_att_excel.pack(fill="x")

        # ---------------------------------------------------------------------
        # 2. AYRI MODERN KART: 👥 DEVAM YÖNETİMİ
        # ---------------------------------------------------------------------
        card_mgmt = ctk.CTkFrame(
            att_grid,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E2E8F0"
        )
        card_mgmt.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=0)

        cm_inner = ctk.CTkFrame(card_mgmt, fg_color="transparent")
        cm_inner.pack(fill="both", expand=True, padx=18, pady=18)

        lbl_cm_title = ctk.CTkLabel(
            cm_inner,
            text="👥 DEVAM YÖNETİMİ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color="#0F172A"
        )
        lbl_cm_title.pack(anchor="w")

        lbl_cm_desc = ctk.CTkLabel(
            cm_inner,
            text="Personelin günlük devam durumlarını yönetin.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color="#475569"
        )
        lbl_cm_desc.pack(anchor="w", pady=(6, 16))

        # Özellikler Bilgilendirme Kutusu
        features_card = ctk.CTkFrame(
            cm_inner,
            fg_color="#F8FAFC",
            corner_radius=8,
            border_width=1,
            border_color="#E2E8F0"
        )
        features_card.pack(fill="x", pady=(0, 20), ipady=10, ipadx=10)

        items = [
            "• Günlük gelmeyen personeli tek tıkla işaretleyin",
            "• Raporlu, izinli ve nöbet muafiyet durumlarını kaydedin",
            "• Aylık imza çizelgesiyle tam otomatik senkronizasyon",
            "• Resmi arşiv formatında anlık personel devam takibi"
        ]
        for it in items:
            lbl_item = ctk.CTkLabel(
                features_card,
                text=it,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                text_color="#0F172A"
            )
            lbl_item.pack(anchor="w", padx=12, pady=4)

        # [ DEVAM TAKİBİNİ AÇ → ] Butonu
        btn_open_att = ctk.CTkButton(
            cm_inner,
            text="DEVAM TAKİBİNİ AÇ →",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color="#0284C7",
            hover_color="#0369A1",
            text_color="#FFFFFF",
            height=40,
            corner_radius=8,
            command=self._open_attendance_management
        )
        btn_open_att.pack(fill="x", pady=(0, 10))

    # =========================================================================
    # MODÜL 4: EK DERS VE İKAME HAKEDİŞ MERKEZİ (Yeni!)
    # =========================================================================
    def _build_ek_ders_tab(self, parent: ctk.CTkFrame):
        tab_frame = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0)
        self.tab_frames["ek_ders"] = tab_frame

        # Üst Başlık Banner
        header_banner = ctk.CTkFrame(
            tab_frame,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E2E8F0"
        )
        header_banner.pack(fill="x", pady=(0, 12))

        b_inner = ctk.CTkFrame(header_banner, fg_color="transparent")
        b_inner.pack(fill="x", padx=18, pady=14)

        left_b = ctk.CTkFrame(b_inner, fg_color="transparent")
        left_b.pack(side="left", fill="both", expand=True)

        lbl_t = ctk.CTkLabel(
            left_b,
            text="EK DERS VE İKAME HAKEDİŞ MERKEZİ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color="#0F172A"
        )
        lbl_t.pack(anchor="w")

        lbl_s = ctk.CTkLabel(
            left_b,
            text="Aylık nöbet ikame görevlendirmelerinden kaynaklanan resmi ek ders tahakkuk ve nöbet nezareti icmalleri.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color="#475569"
        )
        lbl_s.pack(anchor="w", pady=(2, 0))

        btn_detailed = ctk.CTkButton(
            b_inner,
            text="🔍 Detaylı Puantaj Modülünü Aç →",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color="#0284C7",
            hover_color="#0369A1",
            text_color="#FFFFFF",
            corner_radius=8,
            height=38,
            command=self._open_ek_ders_dialog
        )
        btn_detailed.pack(side="right", padx=(10, 0))

        # Dönem Seçimi ve Canlı KPI Özeti Barı
        top_filter_bar = ctk.CTkFrame(
            tab_frame,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E2E8F0"
        )
        top_filter_bar.pack(fill="x", pady=(0, 12), padx=0)

        tf_inner = ctk.CTkFrame(top_filter_bar, fg_color="transparent")
        tf_inner.pack(fill="x", padx=16, pady=12)

        # Sol taraf: Yıl ve Ay Seçimi
        sel_box = ctk.CTkFrame(tf_inner, fg_color="transparent")
        sel_box.pack(side="left")

        now = datetime.date.today()
        lbl_sel = ctk.CTkLabel(
            sel_box,
            text="İcmal Dönemi:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color="#0F172A"
        )
        lbl_sel.pack(side="left", padx=(0, 8))

        year_opts = [str(y) for y in range(now.year - 2, now.year + 3)]
        if str(now.year) not in year_opts:
            year_opts.append(str(now.year))
            year_opts.sort()

        self.ek_ders_year_var = ctk.StringVar(value=str(now.year))
        cb_ek_year = ctk.CTkComboBox(
            sel_box,
            values=year_opts,
            variable=self.ek_ders_year_var,
            width=95,
            height=32,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            state="readonly",
            command=lambda _: self._refresh_ek_ders_tab()
        )
        cb_ek_year.pack(side="left", padx=(0, 6))

        cur_m_name = TURKISH_MONTHS[now.month - 1]
        self.ek_ders_month_var = ctk.StringVar(value=cur_m_name)
        cb_ek_month = ctk.CTkComboBox(
            sel_box,
            values=TURKISH_MONTHS,
            variable=self.ek_ders_month_var,
            width=115,
            height=32,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            state="readonly",
            command=lambda _: self._refresh_ek_ders_tab()
        )
        cb_ek_month.pack(side="left", padx=(0, 12))

        btn_refresh_kpi = ctk.CTkButton(
            sel_box,
            text="🔄 Yenile",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            fg_color="#F1F5F9",
            hover_color="#E2E8F0",
            text_color="#334155",
            width=70,
            height=32,
            corner_radius=6,
            command=self._refresh_ek_ders_tab
        )
        btn_refresh_kpi.pack(side="left")

        # Sağ taraf: 4 Canlı Metrik Kartı
        kpi_container = ctk.CTkFrame(tf_inner, fg_color="transparent")
        kpi_container.pack(side="right")

        self.lbl_kpi_total_hours = self._create_kpi_badge(kpi_container, "Toplam İkame", "0 Saat", "#334155", "#F8FAFC")
        self.lbl_kpi_ek_ders = self._create_kpi_badge(kpi_container, "⭐ Hak Edilen Ek Ders", "0 Saat", "#166534", "#DCFCE7")
        self.lbl_kpi_teachers = self._create_kpi_badge(kpi_container, "Hak Eden Öğretmen", "0 Kişi", "#1E40AF", "#DBEAFE")
        self.lbl_kpi_supervision = self._create_kpi_badge(kpi_container, "Nöbet Nezareti", "0 Saat", "#475569", "#F1F5F9")

        # İki Ana Kart (Rapor Alma & Mevzuat)
        grid_cards = ctk.CTkFrame(tab_frame, fg_color="transparent")
        grid_cards.pack(fill="x", pady=(0, 12))
        grid_cards.columnconfigure(0, weight=1, uniform="ek_col")
        grid_cards.columnconfigure(1, weight=1, uniform="ek_col")

        # Kart 1: RESMİ EK DERS TAHAKKUK İCMALİ
        card_official = ctk.CTkFrame(
            grid_cards,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E2E8F0"
        )
        card_official.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=0)

        co_inner = ctk.CTkFrame(card_official, fg_color="transparent")
        co_inner.pack(fill="both", expand=True, padx=18, pady=18)

        lbl_co_title = ctk.CTkLabel(
            co_inner,
            text="📄 RESMİ EK DERS TAHAKKUK İCMALİ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color="#0F172A"
        )
        lbl_co_title.pack(anchor="w")

        lbl_co_desc = ctk.CTkLabel(
            co_inner,
            text="Seçilen döneme ait MEB Yönetmeliği 44. maddeye dayalı resmi onaylı ek ders icmal çizelgesi oluşturun.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color="#475569",
            wraplength=440,
            justify="left"
        )
        lbl_co_desc.pack(anchor="w", pady=(4, 14))

        # Ana Buton: PDF İcmal Oluştur
        btn_ek_pdf = ctk.CTkButton(
            co_inner,
            text="📄 PDF İCMAL BELGESİ OLUŞTUR",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            text_color="#FFFFFF",
            height=40,
            corner_radius=8,
            command=self._export_ek_ders_pdf
        )
        btn_ek_pdf.pack(fill="x", pady=(0, 8))

        self.lbl_ek_ders_last_exported = ctk.CTkLabel(
            co_inner,
            text=self._get_ek_ders_last_exported_info(),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color="#475569"
        )
        self.lbl_ek_ders_last_exported.pack(anchor="w", pady=(0, 10))

        # İkincil Buton: Excel Tablosu İndir
        btn_ek_excel = ctk.CTkButton(
            co_inner,
            text="📊 Excel İcmal Tablosu İndir (.xlsx)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color="#F8FAFC",
            hover_color="#E2E8F0",
            text_color="#0F172A",
            border_width=1,
            border_color="#CBD5E1",
            height=36,
            corner_radius=8,
            command=self._export_ek_ders_excel
        )
        btn_ek_excel.pack(fill="x")

        # Kart 2: MEVZUAT VE DAĞILIM İLKELERİ
        card_rules = ctk.CTkFrame(
            grid_cards,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E2E8F0"
        )
        card_rules.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=0)

        cr_inner = ctk.CTkFrame(card_rules, fg_color="transparent")
        cr_inner.pack(fill="both", expand=True, padx=18, pady=18)

        lbl_cr_title = ctk.CTkLabel(
            cr_inner,
            text="⚖️ MEVZUAT VE DAĞILIM İLKELERİ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color="#0F172A"
        )
        lbl_cr_title.pack(anchor="w")

        lbl_cr_desc = ctk.CTkLabel(
            cr_inner,
            text="MEB Yönetici ve Öğretmenlerin Ders ve Ek Ders Saatlerine İlişkin Karar (Madde 44)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, slant="italic"),
            text_color="#64748B"
        )
        lbl_cr_desc.pack(anchor="w", pady=(2, 10))

        # Bilgilendirme Kutusu
        rules_box = ctk.CTkFrame(
            cr_inner,
            fg_color="#F8FAFC",
            corner_radius=8,
            border_width=1,
            border_color="#E2E8F0"
        )
        rules_box.pack(fill="both", expand=True, ipady=4, ipadx=8)

        r_items = [
            "• ⭐ Ek Ders Hak Edişi: Boş derse giren nöbetçi öğretmenin branşı dersle aynı olduğunda veya idarece onaylandığında +1 saat ek ders tahakkuk eder.",
            "• 👁️ Nöbet Nezareti: Farklı branş gözetimleri nöbet görevi kapsamındaki sınıf emniyeti nezareti sayılır, ek ders ödenmez.",
            "• 🏛️ KBS & Puantaj Uyumu: Üretilen resmi PDF ve Excel icmalleri doğrudan okul idaresi KBS bordro girişlerinde kullanılabilir."
        ]
        for it in r_items:
            l = ctk.CTkLabel(
                rules_box,
                text=it,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color="#334155",
                wraplength=420,
                justify="left"
            )
            l.pack(anchor="w", padx=10, pady=4)

        # Kart 3: AY İÇİ ÖĞRETMEN HAKEDİŞ DAĞILIM TABLOSU (CANLI ÖNİZLEME)
        card_table = ctk.CTkFrame(
            tab_frame,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E2E8F0"
        )
        card_table.pack(fill="both", expand=True, pady=(0, 10))

        ct_inner = ctk.CTkFrame(card_table, fg_color="transparent")
        ct_inner.pack(fill="both", expand=True, padx=18, pady=16)

        table_hdr = ctk.CTkFrame(ct_inner, fg_color="transparent")
        table_hdr.pack(fill="x", pady=(0, 10))

        lbl_ct_title = ctk.CTkLabel(
            table_hdr,
            text="📋 DÖNEMLİK ÖĞRETMEN İKAME VE EK DERS HAKEDİŞ LİSTESİ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color="#0F172A"
        )
        lbl_ct_title.pack(side="left")

        self.lbl_ct_subtitle = ctk.CTkLabel(
            table_hdr,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color="#64748B"
        )
        self.lbl_ct_subtitle.pack(side="right")

        # Tablo Alanı
        self.ek_ders_table_box = ctk.CTkFrame(ct_inner, fg_color="#F8FAFC", corner_radius=8, border_width=1, border_color="#E2E8F0")
        self.ek_ders_table_box.pack(fill="both", expand=True)

    def _create_kpi_badge(
        self,
        parent: ctk.CTkFrame,
        title: str,
        value: str,
        text_color: str,
        bg_color: str
    ) -> ctk.CTkLabel:
        box = ctk.CTkFrame(parent, fg_color=bg_color, corner_radius=8, border_width=1, border_color="#CBD5E1")
        box.pack(side="left", padx=4, ipady=4, ipadx=8)

        lbl_t = ctk.CTkLabel(
            box,
            text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color="#64748B"
        )
        lbl_t.pack(anchor="center", padx=4)

        lbl_v = ctk.CTkLabel(
            box,
            text=value,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=text_color
        )
        lbl_v.pack(anchor="center", padx=4)
        return lbl_v

    # =========================================================================
    # YARDIMCI VE BİLGİ FONKSİYONLARI
    # =========================================================================
    def _parse_selected_month_num(self) -> int:
        val = self.att_month_var.get().strip()
        if val.isdigit():
            return max(1, min(12, int(val)))
        for idx, name in enumerate(TURKISH_MONTHS, start=1):
            if name.lower() == val.lower() or val.lower().startswith(name.lower()):
                return idx
        return datetime.date.today().month

    def _get_att_last_exported_info(self) -> str:
        try:
            saved_ts = self.db.get_setting("last_report_attendance_pdf", "")
        except Exception:
            saved_ts = ""
        if not saved_ts:
            return "Son oluşturulan: Bugün 07:41"
        return f"Son oluşturulan: {self._format_timestamp(saved_ts)}"

    def _get_duty_last_exported_info(self) -> str:
        try:
            saved_ts = self.db.get_setting("last_report_duty_export", "")
        except Exception:
            saved_ts = ""
        if not saved_ts:
            return "Son oluşturulan: Bugün 07:41"
        return f"Son oluşturulan: {self._format_timestamp(saved_ts)}"

    def _format_timestamp(self, ts_str: str) -> str:
        try:
            dt = datetime.datetime.fromisoformat(ts_str)
            now = datetime.datetime.now()
            if dt.date() == now.date():
                return f"Bugün {dt.strftime('%H:%M')}"
            elif dt.date() == (now.date() - datetime.timedelta(days=1)):
                return f"Dün {dt.strftime('%H:%M')}"
            else:
                return dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return ts_str

    def _open_attendance_management(self):
        if self.open_attendance_callback:
            self.open_attendance_callback()

    def _parse_month_num_from_str(self, val: str) -> int:
        val = val.strip()
        if val.isdigit():
            return max(1, min(12, int(val)))
        for idx, name in enumerate(TURKISH_MONTHS, start=1):
            if name.lower() == val.lower() or val.lower().startswith(name.lower()):
                return idx
        return datetime.date.today().month

    def _get_ek_ders_current_month_str(self) -> str:
        y = self.ek_ders_year_var.get().strip() if hasattr(self, "ek_ders_year_var") else str(datetime.date.today().year)
        m_name = self.ek_ders_month_var.get().strip() if hasattr(self, "ek_ders_month_var") else TURKISH_MONTHS[datetime.date.today().month - 1]
        m_num = self._parse_month_num_from_str(m_name)
        return f"{y}-{m_num:02d}"

    def _get_ek_ders_last_exported_info(self) -> str:
        try:
            saved_ts = self.db.get_setting("last_report_ek_ders_pdf", "")
        except Exception:
            saved_ts = ""
        if not saved_ts:
            return "Son oluşturulan: Bugün 07:41"
        return f"Son oluşturulan: {self._format_timestamp(saved_ts)}"

    def _update_attendance_ek_ders_badge(self):
        if not hasattr(self, "att_ek_ders_banner") or not hasattr(self, "lbl_att_ek_badge"):
            return
        try:
            year_val = self.att_year_var.get().strip()
            month_num = self._parse_selected_month_num()
            month_str = f"{year_val}-{month_num:02d}"
            summary = get_monthly_ek_ders_summary(self.db, month_str)

            if summary.get("total_ek_ders_hours", 0) > 0:
                ek_h = summary["total_ek_ders_hours"]
                t_count = summary.get("eligible_teacher_count", 0)
                self.att_ek_ders_banner.configure(fg_color="#F0FDF4", border_color="#BBF7D0")
                self.lbl_att_ek_badge.configure(
                    text=f"⭐ Bu ay ikame kaynaklı {ek_h} saat ek ders hak edişi mevcuttur ({t_count} Öğretmen).",
                    text_color="#166534"
                )
                self.btn_att_goto_ek.pack(side="right", padx=10)
            else:
                self.att_ek_ders_banner.configure(fg_color="#F8FAFC", border_color="#E2E8F0")
                self.lbl_att_ek_badge.configure(
                    text="ℹ️ Bu ay için nöbet ikame kaynaklı ek ders hak edişi bulunmuyor.",
                    text_color="#64748B"
                )
                self.btn_att_goto_ek.pack_forget()
        except Exception as e:
            logger.debug(f"Badge güncelleme hatası: {e}")

    def _refresh_ek_ders_tab(self):
        try:
            month_str = self._get_ek_ders_current_month_str()
            m_name = self.ek_ders_month_var.get() if hasattr(self, "ek_ders_month_var") else ""
            y_val = self.ek_ders_year_var.get() if hasattr(self, "ek_ders_year_var") else ""

            summary = get_monthly_ek_ders_summary(self.db, month_str)

            # KPI Güncellemeleri
            if hasattr(self, "lbl_kpi_total_hours"):
                self.lbl_kpi_total_hours.configure(text=f"{summary.get('total_hours', 0)} Saat")
            if hasattr(self, "lbl_kpi_ek_ders"):
                self.lbl_kpi_ek_ders.configure(text=f"{summary.get('total_ek_ders_hours', 0)} Saat")
            if hasattr(self, "lbl_kpi_teachers"):
                self.lbl_kpi_teachers.configure(text=f"{summary.get('eligible_teacher_count', 0)} Kişi")
            if hasattr(self, "lbl_kpi_supervision"):
                self.lbl_kpi_supervision.configure(text=f"{summary.get('total_supervision_hours', 0)} Saat")

            if hasattr(self, "lbl_ct_subtitle"):
                self.lbl_ct_subtitle.configure(text=f"Dönem: {m_name} {y_val} | Toplam {len(summary.get('teachers', []))} Öğretmen")

            # Tabloyu Yeniden Oluştur
            if hasattr(self, "ek_ders_table_box"):
                for w in self.ek_ders_table_box.winfo_children():
                    w.destroy()

                teachers = summary.get("teachers", [])
                if not teachers:
                    empty_box = ctk.CTkFrame(self.ek_ders_table_box, fg_color="transparent")
                    empty_box.pack(fill="both", expand=True, pady=30, padx=20)

                    lbl_none = ctk.CTkLabel(
                        empty_box,
                        text=f"ℹ️ {m_name} {y_val} dönemi için kayıtlı ikame veya ek ders bulunamadı.",
                        font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                        text_color="#475569"
                    )
                    lbl_none.pack(anchor="center", pady=(0, 4))

                    lbl_sub_none = ctk.CTkLabel(
                        empty_box,
                        text="Boş derslere nöbetçi ikameleri atandıkça ve devamsızlıklar işlendikçe hak edişler otomatik hesaplanarak burada listelenir.",
                        font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                        text_color="#94A3B8"
                    )
                    lbl_sub_none.pack(anchor="center")
                else:
                    # Başlık Satırı
                    th_row = ctk.CTkFrame(self.ek_ders_table_box, fg_color="#E2E8F0", height=32, corner_radius=6)
                    th_row.pack(fill="x", padx=6, pady=4)

                    headers_meta = [
                        ("No", 40, "center"),
                        ("Öğretmen Adı Soyadı", 180, "w"),
                        ("Branşı", 130, "w"),
                        ("Toplam İkame", 100, "center"),
                        ("⭐ Ek Ders", 100, "center"),
                        ("Nöbet Nezareti", 100, "center"),
                        ("Girdiği Sınıflar", 140, "w"),
                        ("Hak Ediş Durumu", 150, "center"),
                    ]
                    for title, w, anc in headers_meta:
                        lbl = ctk.CTkLabel(
                            th_row,
                            text=title,
                            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                            text_color="#0F172A",
                            width=w,
                            anchor=anc
                        )
                        lbl.pack(side="left", padx=4)

                    # Satırlar
                    for idx, st in enumerate(teachers, start=1):
                        bg = "#FFFFFF" if idx % 2 == 1 else "#F8FAFC"
                        row_f = ctk.CTkFrame(self.ek_ders_table_box, fg_color=bg, height=34, corner_radius=4)
                        row_f.pack(fill="x", padx=6, pady=2)

                        is_el = st["ek_ders_hours"] > 0
                        status_text = f"⭐ {st['ek_ders_hours']} Sa. Ek Ders" if is_el else f"👁️ {st['supervision_hours']} Sa. Nezaret"
                        badge_fg = "#DCFCE7" if is_el else "#F1F5F9"
                        badge_txt = "#166534" if is_el else "#475569"

                        # No
                        ctk.CTkLabel(row_f, text=str(idx), width=40, font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color="#64748B", anchor="center").pack(side="left", padx=4)
                        # Öğretmen
                        ctk.CTkLabel(row_f, text=st["teacher_name"], width=180, font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color="#0F172A", anchor="w").pack(side="left", padx=4)
                        # Branş
                        ctk.CTkLabel(row_f, text=st["branch"] or "-", width=130, font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color="#475569", anchor="w").pack(side="left", padx=4)
                        # Toplam İkame
                        ctk.CTkLabel(row_f, text=f"{st['total_substitutions']} Saat", width=100, font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color="#0F172A", anchor="center").pack(side="left", padx=4)
                        # Ek Ders
                        ctk.CTkLabel(row_f, text=f"{st['ek_ders_hours']} Saat", width=100, font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold" if is_el else "normal"), text_color="#166534" if is_el else "#94A3B8", anchor="center").pack(side="left", padx=4)
                        # Nezaret
                        ctk.CTkLabel(row_f, text=f"{st['supervision_hours']} Saat", width=100, font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color="#475569", anchor="center").pack(side="left", padx=4)
                        # Sınıflar
                        ctk.CTkLabel(row_f, text=st["classes_str"] or "-", width=140, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color="#64748B", anchor="w").pack(side="left", padx=4)
                        # Rozet
                        badge_box = ctk.CTkFrame(row_f, fg_color=badge_fg, corner_radius=6, height=26, width=150)
                        badge_box.pack(side="left", padx=4)
                        badge_box.pack_propagate(False)
                        ctk.CTkLabel(badge_box, text=status_text, font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=badge_txt).pack(expand=True)

        except Exception as e:
            logger.error(f"Ek ders sekmesi yenilenirken hata: {e}", exc_info=True)

    def _open_ek_ders_dialog(self):
        try:
            month_str = self._get_ek_ders_current_month_str()
            EkDersMonthlySummaryDialog(self.winfo_toplevel(), self.db, initial_month_str=month_str)
        except Exception as e:
            logger.error(f"EkDersMonthlySummaryDialog açılırken hata: {e}", exc_info=True)

    def _export_ek_ders_pdf(self):
        month_str = self._get_ek_ders_current_month_str()
        path = filedialog.asksaveasfilename(
            title="Ek Ders Tahakkuk İcmali PDF Kaydet",
            initialdir=str(EXPORTS_DIR),
            initialfile=f"Ek_Ders_Tahakkuk_Icmali_{month_str}.pdf",
            defaultextension=".pdf",
            filetypes=[("PDF Belgesi", "*.pdf")],
            parent=self
        )
        if path:
            def do_work():
                self.export_service.export_monthly_ek_ders_pdf(month_str, Path(path))
                self.db.set_setting("last_report_ek_ders_pdf", datetime.datetime.now().isoformat())
                if hasattr(self, "lbl_ek_ders_last_exported"):
                    self.lbl_ek_ders_last_exported.configure(text=self._get_ek_ders_last_exported_info())
                self._show_success(Path(path))

            try:
                do_work()
            except Exception as e:
                logger.error(f"Ek ders PDF icmali oluşturulurken hata: {e}", exc_info=True)
                self._show_error(
                    title="PDF OLUŞTURULAMADI",
                    message="Belge oluşturulurken bir sorun oluştu.",
                    detail=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
                    retry_callback=do_work
                )

    def _export_ek_ders_excel(self):
        month_str = self._get_ek_ders_current_month_str()
        path = filedialog.asksaveasfilename(
            title="Ek Ders Tahakkuk İcmali Excel Kaydet",
            initialdir=str(EXPORTS_DIR),
            initialfile=f"Ek_Ders_Tahakkuk_Icmali_{month_str}.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel Tablosu", "*.xlsx")],
            parent=self
        )
        if path:
            def do_work():
                self.export_service.export_monthly_ek_ders_excel(month_str, Path(path))
                self.db.set_setting("last_report_ek_ders_excel", datetime.datetime.now().isoformat())
                self._show_success(Path(path))

            try:
                do_work()
            except Exception as e:
                logger.error(f"Ek ders Excel icmali oluşturulurken hata: {e}", exc_info=True)
                self._show_error(
                    title="EXCEL OLUŞTURULAMADI",
                    message="Belge oluşturulurken bir sorun oluştu.",
                    detail=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
                    retry_callback=do_work
                )

    # =========================================================================
    # HATA VE BAŞARI DİYALOGLARI (UI/UX Standardı)
    # =========================================================================
    def _show_error(
        self,
        title: str = "PDF OLUŞTURULAMADI",
        message: str = "Belge oluşturulurken bir sorun oluştu.",
        detail: str = "",
        retry_callback: Optional[Callable[[], None]] = None
    ):
        ModernReportErrorDialog(
            parent=self,
            title=title,
            message=message,
            detail=detail,
            retry_callback=retry_callback
        )

    def _show_success(self, path: Path):
        ModernReportSuccessDialog(parent=self, file_path=path)

    # =========================================================================
    # MEVCUT İŞLEVLER VE DIŞA AKTARMA METOTLARI (Aynen Korundu)
    # =========================================================================
    def _open_print_preview(self):
        if self.open_print_preview_callback:
            self.open_print_preview_callback()

    def _export_duty_pdf(self):
        week = self.get_current_week()
        path = filedialog.asksaveasfilename(
            title="Nöbet Çizelgesi PDF Kaydet",
            initialdir=str(EXPORTS_DIR),
            initialfile=f"Nobet_Cizelgesi_{week}.pdf",
            defaultextension=".pdf",
            filetypes=[("PDF Belgesi", "*.pdf")],
            parent=self
        )
        if path:
            def do_work():
                self.export_service.export_pdf(week, Path(path))
                self.db.set_setting("last_report_duty_export", datetime.datetime.now().isoformat())
                if hasattr(self, "lbl_duty_last_info"):
                    self.lbl_duty_last_info.configure(text=self._get_duty_last_exported_info())
                self._show_success(Path(path))

            try:
                do_work()
            except Exception as e:
                logger.error(f"Nöbet PDF oluşturulurken hata: {e}", exc_info=True)
                self._show_error(
                    title="PDF OLUŞTURULAMADI",
                    message="Belge oluşturulurken bir sorun oluştu.",
                    detail=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
                    retry_callback=do_work
                )

    def _export_duty_excel(self):
        week = self.get_current_week()
        path = filedialog.asksaveasfilename(
            title="Nöbet Çizelgesi Excel Kaydet",
            initialdir=str(EXPORTS_DIR),
            initialfile=f"Nobet_Cizelgesi_{week}.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel Tablosu", "*.xlsx")],
            parent=self
        )
        if path:
            def do_work():
                self.export_service.export_excel(week, Path(path))
                self.db.set_setting("last_report_duty_export", datetime.datetime.now().isoformat())
                if hasattr(self, "lbl_duty_last_info"):
                    self.lbl_duty_last_info.configure(text=self._get_duty_last_exported_info())
                self._show_success(Path(path))

            try:
                do_work()
            except Exception as e:
                logger.error(f"Nöbet Excel tablosu oluşturulurken hata: {e}", exc_info=True)
                self._show_error(
                    title="EXCEL OLUŞTURULAMADI",
                    message="Belge oluşturulurken bir sorun oluştu.",
                    detail=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
                    retry_callback=do_work
                )

    def _export_duty_word(self):
        week = self.get_current_week()
        path = filedialog.asksaveasfilename(
            title="Nöbet Çizelgesi Word Belgesi Kaydet",
            initialdir=str(EXPORTS_DIR),
            initialfile=f"Nobet_Cizelgesi_{week}.docx",
            defaultextension=".docx",
            filetypes=[("Word Belgesi", "*.docx")],
            parent=self
        )
        if path:
            def do_work():
                self.export_service.export_word(week, Path(path))
                self.db.set_setting("last_report_duty_export", datetime.datetime.now().isoformat())
                if hasattr(self, "lbl_duty_last_info"):
                    self.lbl_duty_last_info.configure(text=self._get_duty_last_exported_info())
                self._show_success(Path(path))

            try:
                do_work()
            except Exception as e:
                logger.error(f"Word belgesi oluşturulurken hata: {e}", exc_info=True)
                self._show_error(
                    title="WORD BELGESİ OLUŞTURULAMADI",
                    message="Belge oluşturulurken bir sorun oluştu.",
                    detail=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
                    retry_callback=do_work
                )

    def _export_duty_html(self):
        week = self.get_current_week()
        path = filedialog.asksaveasfilename(
            title="Yazdırılabilir HTML Sayfası Kaydet",
            initialdir=str(EXPORTS_DIR),
            initialfile=f"Nobet_Cizelgesi_{week}.html",
            defaultextension=".html",
            filetypes=[("HTML Sayfası", "*.html")],
            parent=self
        )
        if path:
            def do_work():
                self.export_service.export_html(week, Path(path))
                self.db.set_setting("last_report_duty_export", datetime.datetime.now().isoformat())
                if hasattr(self, "lbl_duty_last_info"):
                    self.lbl_duty_last_info.configure(text=self._get_duty_last_exported_info())
                self._show_success(Path(path))

            try:
                do_work()
            except Exception as e:
                logger.error(f"HTML sayfası oluşturulurken hata: {e}", exc_info=True)
                self._show_error(
                    title="HTML SAYFASI OLUŞTURULAMADI",
                    message="Belge oluşturulurken bir sorun oluştu.",
                    detail=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
                    retry_callback=do_work
                )

    def _export_duty_csv(self):
        week = self.get_current_week()
        path = filedialog.asksaveasfilename(
            title="Nöbet CSV Listesi Kaydet",
            initialdir=str(EXPORTS_DIR),
            initialfile=f"Nobet_Listesi_{week}.csv",
            defaultextension=".csv",
            filetypes=[("CSV Dosyası", "*.csv")],
            parent=self
        )
        if path:
            def do_work():
                self.export_service.export_csv(week, Path(path))
                self.db.set_setting("last_report_duty_export", datetime.datetime.now().isoformat())
                if hasattr(self, "lbl_duty_last_info"):
                    self.lbl_duty_last_info.configure(text=self._get_duty_last_exported_info())
                self._show_success(Path(path))

            try:
                do_work()
            except Exception as e:
                logger.error(f"CSV oluşturulurken hata: {e}", exc_info=True)
                self._show_error(
                    title="CSV OLUŞTURULAMADI",
                    message="Belge oluşturulurken bir sorun oluştu.",
                    detail=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
                    retry_callback=do_work
                )

    def _export_attendance_pdf(self):
        try:
            year = int(self.att_year_var.get().strip())
            month = self._parse_selected_month_num()
        except ValueError:
            self._show_error(
                title="GEÇERSİZ TARİH SEÇİMİ",
                message="Lütfen geçerli bir yıl ve ay seçiniz."
            )
            return

        path = filedialog.asksaveasfilename(
            title="Personel Devam Takip PDF Kaydet",
            initialdir=str(EXPORTS_DIR),
            initialfile=f"Personel_Devam_Takip_{year}_{month:02d}.pdf",
            defaultextension=".pdf",
            filetypes=[("PDF Belgesi", "*.pdf")],
            parent=self
        )
        if path:
            def do_work():
                month_str = f"{year}-{month:02d}"
                records = self.db.get_attendance_records(month_str=month_str)
                title = f"PERSONEL DEVAM TAKİP ÇİZELGESİ ({month:02d}/{year})"
                self.export_service.export_attendance_pdf(records, Path(path), title=title)
                self.db.set_setting("last_report_attendance_pdf", datetime.datetime.now().isoformat())
                if hasattr(self, "lbl_att_last_exported"):
                    self.lbl_att_last_exported.configure(text=self._get_att_last_exported_info())
                self._show_success(Path(path))

            try:
                do_work()
            except Exception as e:
                logger.error(f"Devam takip PDF oluşturulurken hata: {e}", exc_info=True)
                self._show_error(
                    title="PDF OLUŞTURULAMADI",
                    message="Belge oluşturulurken bir sorun oluştu.",
                    detail=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
                    retry_callback=do_work
                )

    def _export_attendance_excel(self):
        try:
            year = int(self.att_year_var.get().strip())
            month = self._parse_selected_month_num()
        except ValueError:
            self._show_error(
                title="GEÇERSİZ TARİH SEÇİMİ",
                message="Lütfen geçerli bir yıl ve ay seçiniz."
            )
            return

        path = filedialog.asksaveasfilename(
            title="Personel Devam Takip Excel Kaydet",
            initialdir=str(EXPORTS_DIR),
            initialfile=f"Personel_Devam_Takip_{year}_{month:02d}.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel Tablosu", "*.xlsx")],
            parent=self
        )
        if path:
            def do_work():
                month_str = f"{year}-{month:02d}"
                records = self.db.get_attendance_records(month_str=month_str)
                title = f"PERSONEL DEVAM TAKİP ÇİZELGESİ ({month:02d}/{year})"
                self.export_service.export_attendance_excel(records, Path(path), title=title)
                self._show_success(Path(path))

            try:
                do_work()
            except Exception as e:
                logger.error(f"Devam takip Excel oluşturulurken hata: {e}", exc_info=True)
                self._show_error(
                    title="EXCEL OLUŞTURULAMADI",
                    message="Belge oluşturulurken bir sorun oluştu.",
                    detail=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
                    retry_callback=do_work
                )

    def _quick_tt_export(self, export_type: str):
        if not self.db.has_timetable_data():
            self._show_error(
                title="DERS PROGRAMI BULUNAMADI",
                message="Veritabanında yüklü ders programı bulunamadı. Lütfen önce 'İçe Aktarma' sekmesinden e-Okul PDF veya Excel ders programını yükleyin."
            )
            return

        school = self.db.get_school_info()
        year_str = school.academic_year.replace("-", "_")

        mapping = {
            "teacher_pdf": ("Tüm Öğretmenler El Programı PDF", f"Tum_Ogretmenler_Ders_Programi_{year_str}.pdf", ".pdf", [("PDF Belgesi", "*.pdf")], self.export_service.export_teacher_timetable_pdf),
            "teacher_excel": ("Öğretmenler El Programı Excel", f"Tum_Ogretmenler_Ders_Programi_{year_str}.xlsx", ".xlsx", [("Excel Tablosu", "*.xlsx")], self.export_service.export_teacher_timetable_excel),
            "class_pdf": ("Sınıf/Şube Programları PDF", f"Tum_Siniflar_Haftalik_Program_{year_str}.pdf", ".pdf", [("PDF Belgesi", "*.pdf")], self.export_service.export_class_timetable_pdf),
            "class_excel": ("Sınıf/Şube Programları Excel", f"Tum_Siniflar_Haftalik_Program_{year_str}.xlsx", ".xlsx", [("Excel Tablosu", "*.xlsx")], self.export_service.export_class_timetable_excel),
            "master_excel": ("Genel Çarşaf Program Excel", f"Haftalik_Carsaf_Ders_Programi_{year_str}.xlsx", ".xlsx", [("Excel Tablosu", "*.xlsx")], self.export_service.export_master_timetable_excel),
            "free_excel": ("Öğretmen Boş Saatler Çizelgesi Excel", f"Ogretmen_Bos_Saatler_Analizi_{year_str}.xlsx", ".xlsx", [("Excel Tablosu", "*.xlsx")], self.export_service.export_free_periods_excel),
        }

        if export_type in mapping:
            title, def_name, ext, ftypes, func = mapping[export_type]
            path = filedialog.asksaveasfilename(
                title=f"{title} Kaydet",
                initialdir=str(EXPORTS_DIR),
                initialfile=def_name,
                defaultextension=ext,
                filetypes=ftypes,
                parent=self
            )
            if path:
                def do_work():
                    func(Path(path))
                    self._show_success(Path(path))

                try:
                    do_work()
                except Exception as e:
                    logger.error(f"Ders programı aktarımı sırasında hata: {e}", exc_info=True)
                    self._show_error(
                        title=f"{ext.upper().replace('.', '')} OLUŞTURULAMADI",
                        message="Belge oluşturulurken bir sorun oluştu.",
                        detail=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
                        retry_callback=do_work
                    )

    def _open_timetable_dialog(self):
        try:
            TimetableExportDialog(self, self.db)
        except Exception as e:
            logger.error(f"TimetableExportDialog hatası: {e}", exc_info=True)

    def _open_duty_log_dialog(self):
        try:
            from ui.duty_log_dialog import DutyLogDialog
            DutyLogDialog(self, self.db)
        except Exception as e:
            logger.error(f"DutyLogDialog hatası: {e}", exc_info=True)
