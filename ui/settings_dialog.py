"""
Kapsamlı Sistem, Okul ve Yönetim Ayarları Ekranı (Modern CustomTkinter Design)
- Okul ve Yönetim Bilgileri (Müdür & Müdür Yardımcısı)
- Ders ve Nöbet Zaman Çizelgesi
- Nöbet Kaydırma ve Otomatik Rotasyon Tercihleri
- Boş Ders, Ek Ders ve İş Yükü Dengeleme Kuralları
- Nöbetçi Öğretmen Görev Talimatnamesi
- Sistem Font & Görünüm Ayarları
- Güvenlik & Yerel Ağ (LAN) Paylaşımı
- Sistem ve Veritabanı İstatistikleri / Bakım
"""
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Callable, Optional, Dict
import customtkinter as ctk

from core.models import SchoolInfo
from core.database import Database
from core.config import APP_VERSION, DEFAULT_GITHUB_REPO
from core.logger import logger
from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_SECONDARY, COLOR_SUCCESS,
    COLOR_DANGER, COLOR_BORDER, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, FONT_FAMILY, create_modern_button
)
from logic.network_service import (
    get_global_host_service, is_global_host_running, stop_global_host_service,
    NetworkDiscoveryClient, get_local_ip, get_hostname
)


class _NotebookCompatShim:
    """Geriye dönük test/kod uyumluluğu için self.notebook.select(idx) sarmalayıcısı."""
    def __init__(self, view: "SettingsView"):
        self._view = view
        self._keys = [
            "school", "schedule", "shift", "rules",
            "duty_rules", "appearance", "security", "maintenance"
        ]

    def select(self, index_or_key=None):
        if index_or_key is None:
            return self._view.current_tab_key
        if isinstance(index_or_key, int) and 0 <= index_or_key < len(self._keys):
            self._view.switch_tab(self._keys[index_or_key])
        elif isinstance(index_or_key, str):
            self._view.select_tab(index_or_key)


class SettingsView(ctk.CTkFrame):
    """Ana pencere içine gömülü Modern CustomTkinter Sistem Ayarları Ekranı."""
    def __init__(
        self,
        parent: tk.Widget,
        db: Database,
        on_saved: Optional[Callable[[], None]] = None,
        on_finish: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent, fg_color=COLOR_BG, corner_radius=0)
        self.db = db
        self.on_saved = on_saved
        self.on_finish = on_finish
        self.school = self.db.get_school_info()

        # 1. Okul ve İdare
        self.school_name_var = tk.StringVar(value=self.school.name)
        self.city_var = tk.StringVar(value=self.school.city)
        self.district_var = tk.StringVar(value=self.school.district)
        self.year_var = tk.StringVar(value=self.school.academic_year)
        self.principal_var = tk.StringVar(value=self.school.principal_name)
        self.vice_principal_var = tk.StringVar(value=self.db.get_setting("vice_principal_name", "Nöbetten Sorumlu Müdür Yrd."))
        self.school_level_var = tk.StringVar(value=getattr(self.school, "school_level", "Ortaokul"))
        self.education_type_var = tk.StringVar(value=getattr(self.school, "education_type", "Normal (Tekli)"))

        # 2. Ders ve Nöbet Saatleri
        self.lesson_count_var = tk.StringVar(value=self.db.get_setting("daily_lesson_count", "7"))
        self.lesson_start_var = tk.StringVar(value=self.db.get_setting("first_lesson_start", "08:30"))
        self.lesson_end_var = tk.StringVar(value=self.db.get_setting("last_lesson_end", "15:00"))
        self.lesson_duration_var = tk.StringVar(value=self.db.get_setting("lesson_duration_minutes", "40"))
        self.break_duration_var = tk.StringVar(value=self.db.get_setting("break_duration_minutes", "10"))
        self.duty_start_offset_var = tk.StringVar(value=self.db.get_setting("duty_start_offset", "30"))
        self.duty_end_offset_var = tk.StringVar(value=self.db.get_setting("duty_end_offset", "30"))
        self.period_time_vars: Dict[int, Tuple[tk.StringVar, tk.StringVar]] = {}
        self._init_period_time_vars()

        # 3. Kaydırma Tercihleri
        self.shift_mode_var = tk.StringVar(value=self.db.get_setting("last_shift_mode", "day_forward"))
        self.shift_preserve_var = tk.BooleanVar(value=self.db.get_setting("last_shift_preserve", "1") == "1")

        # 4. Boş Ders & Ek Ders Kuralları
        self.branch_priority_var = tk.BooleanVar(value=self.db.get_setting("branch_priority_enabled", "1") == "1")
        self.workload_sharing_var = tk.BooleanVar(value=self.db.get_setting("workload_sharing_enabled", "1") == "1")
        self.ek_ders_alert_var = tk.BooleanVar(value=self.db.get_setting("ek_ders_alert_enabled", "1") == "1")
        self.default_duty_per_lesson_var = tk.StringVar(value=self.db.get_setting("default_duty_per_lesson", "1"))

        # 5. Görünüm, Yazı Tipi ve Sistem Font Ayarları
        self.font_family_var = tk.StringVar(value=self.db.get_setting("font_family", "Segoe UI"))
        self.font_preset_var = tk.StringVar(value=self.db.get_setting("font_scale_preset", "Standart (%100 - Önerilen)"))

        t_sz = self.db.get_setting("font_size_teacher", "")
        if not t_sz:
            old_sz = self.db.get_setting("font_size", "15")
            t_sz = old_sz if (old_sz and old_sz.isdigit() and int(old_sz) >= 14) else "15"
        if str(t_sz) == "12":
            t_sz = "15"
        self.font_size_teacher_var = tk.StringVar(value=str(t_sz))
        self.font_size_secondary_var = tk.StringVar(value=str(self.db.get_setting("font_size_secondary", "12") or "12"))
        self.font_size_header_var = tk.StringVar(value=str(self.db.get_setting("font_size_header", "13") or "13"))
        self.ui_font_size_var = tk.StringVar(value=str(self.db.get_setting("ui_font_size", "13") or "13"))
        self.font_size_title_var = tk.StringVar(value=str(self.db.get_setting("font_size_page_title", "18") or "18"))
        self.font_size_kpi_var = tk.StringVar(value=str(self.db.get_setting("font_size_kpi_value", "22") or "22"))
        saved_sb_mode = self.db.get_setting("sidebar_theme", "dark")
        sb_display = "Saf Beyaz / Açık Gri (macOS Light)" if saved_sb_mode == "light" else "Koyu Antrasit (macOS Pro Dark)"
        self.sidebar_theme_var = tk.StringVar(value=sb_display)

        w_val = self.db.get_setting("font_weight_teacher", "bold")
        self.font_weight_teacher_var = tk.StringVar(value="Normal" if "normal" in w_val.lower() else "Kalın (Bold)")

        self.grid_border_width_var = tk.StringVar(value=self.db.get_setting("grid_border_width", "1"))
        col_setting = self.db.get_setting("grid_border_color", "#CBD5E1")
        if col_setting and col_setting.upper() == "#94A3B8":
            col_setting = "#CBD5E1"
        self.grid_border_color_var = tk.StringVar(value=col_setting or "#CBD5E1")

        # 6. Yazılım Güncelleme ve Telegram Geri Bildirim Tercihleri
        self.github_repo_var = tk.StringVar(value=self.db.get_setting("github_repo", DEFAULT_GITHUB_REPO))
        self.auto_check_updates_var = tk.BooleanVar(value=self.db.get_setting("auto_check_updates", "1") == "1")
        from core.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
        self.telegram_bot_token_var = tk.StringVar(value=self.db.get_setting("telegram_bot_token", TELEGRAM_BOT_TOKEN))
        self.telegram_chat_id_var = tk.StringVar(value=self.db.get_setting("telegram_chat_id", TELEGRAM_CHAT_ID))

        self.current_tab_key = "school"
        self.tab_buttons: Dict[str, ctk.CTkButton] = {}
        self.tab_frames: Dict[str, ctk.CTkFrame] = {}
        self.notebook = _NotebookCompatShim(self)

        self._build_ui()

    def _create_section_card(self, parent, title: str, subtitle: str = "") -> ctk.CTkFrame:
        """Windows 95 LabelFrame yerine modern, yuvarlatılmış, beyaz tasarım kartı oluşturur."""
        card = ctk.CTkFrame(
            parent,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E2E8F0"
        )
        card.pack(fill="x", pady=(0, 10))

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(12, 6))

        ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color="#0F172A"
        ).pack(anchor="w")

        if subtitle:
            ctk.CTkLabel(
                header,
                text=subtitle,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                text_color="#475569",
                justify="left"
            ).pack(anchor="w", pady=(1, 0))

        sep = ctk.CTkFrame(card, fg_color="#F1F5F9", height=1)
        sep.pack(fill="x", padx=14, pady=(0, 6))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=18, pady=(2, 12))
        return body

    def _create_entry(self, parent, textvariable: tk.StringVar, width: int = 320, show: str = "") -> ctk.CTkEntry:
        kwargs = {
            "master": parent,
            "textvariable": textvariable,
            "width": width,
            "height": 34,
            "font": ctk.CTkFont(family=FONT_FAMILY, size=13),
            "fg_color": "#F8FAFC",
            "border_color": "#CBD5E1",
            "text_color": "#0F172A",
            "corner_radius": 8
        }
        if show:
            kwargs["show"] = show
        return ctk.CTkEntry(**kwargs)

    def _create_combobox(
        self,
        parent,
        variable: tk.StringVar,
        values: list,
        width: int = 240,
        command=None,
        state: str = "readonly"
    ) -> ctk.CTkComboBox:
        cb = ctk.CTkComboBox(
            parent,
            variable=variable,
            values=values,
            width=width,
            height=34,
            state=state,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            dropdown_font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            fg_color="#F8FAFC",
            border_color="#CBD5E1",
            button_color="#E2E8F0",
            button_hover_color="#CBD5E1",
            text_color="#0F172A",
            corner_radius=8,
            command=command
        )
        return cb

    def _build_ui(self):
        # 1. ALT SABİT KAYDET BAR (Her zaman en altta görünür)
        bottom_bar = ctk.CTkFrame(
            self,
            fg_color="#FFFFFF",
            height=50,
            corner_radius=0,
            border_width=1,
            border_color="#E2E8F0"
        )
        bottom_bar.pack(fill="x", side="bottom")
        bottom_bar.pack_propagate(False)

        ctk.CTkLabel(
            bottom_bar,
            text="💡 Ayarlarınızı değiştirdikten sonra sağdaki '✓ Tüm Ayarları Kaydet' butonuna basınız.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color="#475569"
        ).pack(side="left", padx=20)

        btn_cancel = create_modern_button(
            bottom_bar,
            text="Vazgeç / Kapat",
            command=self.close_view,
            variant="default",
            height=34,
            width=130
        )
        btn_cancel.pack(side="right", padx=(8, 20), pady=8)

        btn_save = create_modern_button(
            bottom_bar,
            text="✓ Tüm Ayarları Kaydet",
            command=self._save_all,
            variant="success",
            height=34,
            width=185
        )
        btn_save.pack(side="right", pady=8)

        # 2. ÜST MODERN SEGMENTED PILL SEKME BARI + HIZLI KAYDET
        nav_card = ctk.CTkFrame(
            self,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E2E8F0"
        )
        nav_card.pack(fill="x", padx=16, pady=(8, 8))

        nav_inner = ctk.CTkFrame(nav_card, fg_color="transparent")
        nav_inner.pack(fill="x", padx=10, pady=6)

        # Önce sağdaki Kaydet butonunu yerleştir ki sekme barı tarafından ekran dışına itilmesin
        btn_top_save = create_modern_button(
            nav_inner,
            text="✓ Kaydet",
            command=self._save_all,
            variant="success",
            height=68,
            width=100
        )
        btn_top_save.pack(side="right", padx=(8, 0))

        # Segmented Pill Kapsülü (8 Sekme -> 4x2 Dengeli Grid, hiçbir ekranda taşmaz)
        pills_box = ctk.CTkFrame(
            nav_inner,
            fg_color="#F1F5F9",
            corner_radius=10,
            border_width=0
        )
        pills_box.pack(side="left", fill="both", expand=True)
        for col_i in range(4):
            pills_box.columnconfigure(col_i, weight=1, uniform="settings_tab")

        tabs_meta = [
            ("school", "🏫 Okul & İdare"),
            ("schedule", "⏰ Saatler"),
            ("shift", "🔄 Kaydırma"),
            ("rules", "⚖️ Boş Ders"),
            ("duty_rules", "📜 Talimatname"),
            ("appearance", "🔤 Görünüm"),
            ("security", "🔒 Güvenlik & Ağ"),
            ("maintenance", "💾 Sistem & Bakım"),
        ]

        for idx, (key, label) in enumerate(tabs_meta):
            r = idx // 4
            c = idx % 4
            btn = ctk.CTkButton(
                pills_box,
                text=label,
                width=0,
                height=30,
                corner_radius=7,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                fg_color=COLOR_PRIMARY if key == "school" else "transparent",
                hover_color=COLOR_PRIMARY_HOVER if key == "school" else "#E2E8F0",
                text_color="#FFFFFF" if key == "school" else "#334155",
                command=lambda k=key: self.switch_tab(k)
            )
            btn.grid(row=r, column=c, padx=3, pady=3, sticky="nsew")
            self.tab_buttons[key] = btn

        # 3. KAYDIRILABİLİR ANA İÇERİK KONTEYNERİ
        self.scroll_container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0
        )
        self.scroll_container.pack(fill="both", expand=True, padx=16, pady=(0, 6))

        self._build_tab_school()
        self._build_tab_schedule()
        self._build_tab_shift()
        self._build_tab_rules()
        self._build_tab_duty_rules()
        self._build_tab_appearance()
        self._build_tab_security()
        self._build_tab_maintenance()

        self._bind_mousewheel_recursive(self.scroll_container)
        self.switch_tab("school")

    def _bind_mousewheel_recursive(self, widget):
        """Fare tekerleği ile tüm ayar kartları üzerinde akıcı kaydırma sağlar."""
        def _on_mousewheel(event):
            try:
                if hasattr(self, "scroll_container") and hasattr(self.scroll_container, "_parent_canvas"):
                    # CTkTextbox içindeyse kendi kaydırmasını bozma
                    if isinstance(event.widget, tk.Text):
                        return
                    delta = int(-1 * (event.delta / 120))
                    self.scroll_container._parent_canvas.yview_scroll(delta, "units")
            except Exception:
                pass

        try:
            widget.bind("<MouseWheel>", _on_mousewheel, add="+")
            for child in widget.winfo_children():
                self._bind_mousewheel_recursive(child)
        except Exception:
            pass

    def switch_tab(self, tab_key: str):
        self.current_tab_key = tab_key
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

        try:
            if hasattr(self, "scroll_container") and hasattr(self.scroll_container, "_parent_canvas"):
                self.scroll_container._parent_canvas.yview_moveto(0.0)
        except Exception:
            pass

    def close_view(self):
        if self.on_finish:
            self.on_finish()
        elif isinstance(self.master, tk.Toplevel):
            self.master.destroy()

    def select_tab(self, tab_name: str):
        """İstenen ayar sekmesini doğrudan odaklar."""
        try:
            t = str(tab_name).lower()
            if t in ("font", "appearance", "görünüm", "yazı tipi", "fonts"):
                self.switch_tab("appearance")
            elif t in ("school", "okul"):
                self.switch_tab("school")
            elif t in ("schedule", "ders", "saat"):
                self.switch_tab("schedule")
            elif t in ("shift", "kaydırma"):
                self.switch_tab("shift")
            elif t in ("security", "güvenlik", "lan"):
                self.switch_tab("security")
            elif t in ("maintenance", "sistem"):
                self.switch_tab("maintenance")
        except Exception:
            pass

    # =========================================================================
    # SEKME 1: OKUL & İDARE (2 Sütunlu Kompakt Yerleşim - Tek Ekrana Tam Sığar)
    # =========================================================================
    def _build_tab_school(self):
        tab = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        self.tab_frames["school"] = tab

        body_school = self._create_section_card(
            tab,
            "🏫 Kurum Bilgileri",
            "Resmi nöbet çizelgeleri, PDF çıktıları ve antet başlığında yer alacak kurum bilgileri."
        )
        body_school.columnconfigure(0, weight=0, minsize=155)
        body_school.columnconfigure(1, weight=1)
        body_school.columnconfigure(2, weight=0, minsize=155)
        body_school.columnconfigure(3, weight=1)

        # Satır 0: Okul Adı (Tam Genişlik) ve Eğitim Yılı
        ctk.CTkLabel(
            body_school, text="Okul Adı:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A"
        ).grid(row=0, column=0, sticky="w", pady=5)
        self._create_entry(body_school, self.school_name_var, width=280).grid(
            row=0, column=1, sticky="ew", pady=5, padx=(8, 20)
        )

        ctk.CTkLabel(
            body_school, text="Eğitim Öğretim Yılı:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A"
        ).grid(row=0, column=2, sticky="w", pady=5)
        self._create_entry(body_school, self.year_var, width=220).grid(
            row=0, column=3, sticky="ew", pady=5, padx=(8, 0)
        )

        # Satır 1: İl ve İlçe (Yan Yana)
        ctk.CTkLabel(
            body_school, text="İl:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A"
        ).grid(row=1, column=0, sticky="w", pady=5)
        self._create_entry(body_school, self.city_var, width=220).grid(
            row=1, column=1, sticky="ew", pady=5, padx=(8, 20)
        )

        ctk.CTkLabel(
            body_school, text="İlçe:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A"
        ).grid(row=1, column=2, sticky="w", pady=5)
        self._create_entry(body_school, self.district_var, width=220).grid(
            row=1, column=3, sticky="ew", pady=5, padx=(8, 0)
        )

        # Satır 2: Okul Kademesi ve Eğitim Şekli (Yan Yana)
        ctk.CTkLabel(
            body_school, text="Okul Kademesi (Türü):",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A"
        ).grid(row=2, column=0, sticky="w", pady=5)
        cb_level = self._create_combobox(
            body_school,
            variable=self.school_level_var,
            values=["İlkokul", "Ortaokul", "İmam Hatip Ortaokulu", "Anadolu Lisesi", "Fen Lisesi", "Mesleki ve Teknik Anadolu Lisesi", "Diğer"],
            width=240,
            command=lambda _: self._on_school_level_changed()
        )
        cb_level.grid(row=2, column=1, sticky="ew", pady=5, padx=(8, 20))

        ctk.CTkLabel(
            body_school, text="Eğitim Şekli:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A"
        ).grid(row=2, column=2, sticky="w", pady=5)
        cb_edu = self._create_combobox(
            body_school,
            variable=self.education_type_var,
            values=["Normal (Tekli)", "İkili Eğitim (Sabahçı - Öğlenci)"],
            width=240
        )
        cb_edu.grid(row=2, column=3, sticky="ew", pady=5, padx=(8, 0))

        # Kart 2: İdare ve Yetkililer (Yan Yana)
        body_admin = self._create_section_card(
            tab,
            "✍️ İdare ve Yetkililer (Belge İmzaları)",
            "Çıktıların altındaki resmi onay ve imza bloklarında görünecek yönetici isimleri."
        )
        body_admin.columnconfigure(0, weight=0, minsize=155)
        body_admin.columnconfigure(1, weight=1)
        body_admin.columnconfigure(2, weight=0, minsize=155)
        body_admin.columnconfigure(3, weight=1)

        ctk.CTkLabel(
            body_admin, text="Okul Müdürü:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A"
        ).grid(row=0, column=0, sticky="w", pady=5)
        self._create_entry(body_admin, self.principal_var, width=250).grid(
            row=0, column=1, sticky="ew", pady=5, padx=(8, 20)
        )

        ctk.CTkLabel(
            body_admin, text="Müdür Yardımcısı:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A"
        ).grid(row=0, column=2, sticky="w", pady=5)
        self._create_entry(body_admin, self.vice_principal_var, width=250).grid(
            row=0, column=3, sticky="ew", pady=5, padx=(8, 0)
        )

    # =========================================================================
    # SEKME 2: DERS VE NÖBET SAATLERİ
    # =========================================================================
    def _init_period_time_vars(self):
        curr_periods = self.db.get_period_times()
        for p in range(1, 11):
            t_str = curr_periods.get(p, "")
            parts = t_str.split(" - ") if " - " in t_str else ["", ""]
            s_val = parts[0].strip()
            e_val = parts[1].strip() if len(parts) > 1 else ""
            self.period_time_vars[p] = (tk.StringVar(value=s_val), tk.StringVar(value=e_val))

    def _auto_calculate_periods(self):
        try:
            start_str = self.lesson_start_var.get().strip() or "08:30"
            count = int(self.lesson_count_var.get().strip() or "7")
            l_dur = int(self.lesson_duration_var.get().strip() or "40")
            b_dur = int(self.break_duration_var.get().strip() or "10")
            calculated = self.db.calculate_period_times(start_str, count, l_dur, b_dur)
            for p, val in calculated.items():
                if p in self.period_time_vars:
                    parts = val.split(" - ")
                    self.period_time_vars[p][0].set(parts[0].strip())
                    self.period_time_vars[p][1].set(parts[1].strip() if len(parts) > 1 else "")
            if count in calculated:
                last_end = calculated[count].split(" - ")[-1].strip()
                self.lesson_end_var.set(last_end)
        except Exception as e:
            logger.warning(f"Ders saatleri otomatik hesaplama hatası: {e}")

    def _on_lesson_count_changed(self):
        self._render_period_rows()

    def _render_period_rows(self):
        if not hasattr(self, "period_container") or not self.period_container:
            return
        for w in self.period_container.winfo_children():
            w.destroy()

        try:
            count = int(self.lesson_count_var.get().strip() or "7")
        except ValueError:
            count = 7

        half = (count + 1) // 2
        for col_idx in (0, 1):
            self.period_container.columnconfigure(col_idx, weight=1, uniform="col")

        for i in range(1, count + 1):
            col = 0 if i <= half else 1
            row = (i - 1) if col == 0 else (i - 1 - half)

            cell_frame = ctk.CTkFrame(self.period_container, fg_color="#F8FAFC", corner_radius=6, border_width=1, border_color="#E2E8F0")
            cell_frame.grid(row=row, column=col, sticky="ew", padx=6, pady=4, ipady=3)

            ctk.CTkLabel(
                cell_frame,
                text=f"{i}. Ders:",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                text_color="#1E293B",
                width=65,
                anchor="w"
            ).pack(side="left", padx=(10, 6))

            s_var, e_var = self.period_time_vars.get(i, (tk.StringVar(), tk.StringVar()))
            self.period_time_vars[i] = (s_var, e_var)

            self._create_entry(cell_frame, s_var, width=70).pack(side="left")
            ctk.CTkLabel(
                cell_frame,
                text="—",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                text_color="#64748B"
            ).pack(side="left", padx=4)
            self._create_entry(cell_frame, e_var, width=70).pack(side="left")

    def _build_tab_schedule(self):
        tab = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        self.tab_frames["schedule"] = tab

        body_time = self._create_section_card(
            tab,
            "⏰ Günlük Ders Zaman Çizelgesi",
            "Okuldaki günlük ders saati sayısı, başlama/bitiş saatleri ve ders/teneffüs sürelerini belirleyin."
        )
        body_time.columnconfigure(0, weight=0, minsize=185)
        body_time.columnconfigure(1, weight=1)
        body_time.columnconfigure(2, weight=0, minsize=185)
        body_time.columnconfigure(3, weight=1)

        ctk.CTkLabel(
            body_time, text="Günlük Ders Sayısı:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A"
        ).grid(row=0, column=0, sticky="w", pady=5)
        self._create_combobox(
            body_time, self.lesson_count_var, ["6", "7", "8", "9", "10"],
            width=120, command=lambda _: self._on_lesson_count_changed()
        ).grid(row=0, column=1, sticky="w", padx=(8, 0), pady=5)

        ctk.CTkLabel(
            body_time, text="İlk Ders Başlama Saati:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A"
        ).grid(row=1, column=0, sticky="w", pady=5)
        self._create_entry(body_time, self.lesson_start_var, width=120).grid(
            row=1, column=1, sticky="w", padx=(8, 20), pady=5
        )

        ctk.CTkLabel(
            body_time, text="Son Ders Bitiş Saati:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A"
        ).grid(row=1, column=2, sticky="w", pady=5)
        self._create_entry(body_time, self.lesson_end_var, width=120).grid(
            row=1, column=3, sticky="w", padx=(8, 0), pady=5
        )

        # Ders Süresi & Teneffüs & Hesapla Butonu
        ctk.CTkLabel(
            body_time, text="Ders Süresi (Dakika):",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A"
        ).grid(row=2, column=0, sticky="w", pady=5)
        self._create_entry(body_time, self.lesson_duration_var, width=120).grid(
            row=2, column=1, sticky="w", padx=(8, 20), pady=5
        )

        ctk.CTkLabel(
            body_time, text="Teneffüs Süresi (Dakika):",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A"
        ).grid(row=2, column=2, sticky="w", pady=5)
        f_break = ctk.CTkFrame(body_time, fg_color="transparent")
        f_break.grid(row=2, column=3, sticky="w", padx=(8, 0), pady=5)
        self._create_entry(f_break, self.break_duration_var, width=65).pack(side="left")

        btn_calc = ctk.CTkButton(
            f_break,
            text="⚡ Saatleri Dağıt",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color="#0284C7",
            hover_color="#0369A1",
            text_color="#FFFFFF",
            width=110,
            height=32,
            command=self._auto_calculate_periods
        )
        btn_calc.pack(side="left", padx=(10, 0))

        # Detaylı Ders Saatleri Kartı
        body_periods = self._create_section_card(
            tab,
            "📋 Ders Saatleri Çizelgesi (Tüm Çıktılara Yansır)",
            "Her dersin başlangıç ve bitiş saatini doğrudan düzenleyebilirsiniz. '⚡ Saatleri Dağıt' ile otomatik doldurabilirsiniz."
        )
        self.period_container = ctk.CTkFrame(body_periods, fg_color="transparent")
        self.period_container.pack(fill="x", pady=4)
        self._render_period_rows()

        body_duty = self._create_section_card(
            tab,
            "🛡️ Nöbet Görev Süresi (MEB Yönetmeliği)",
            "Nöbet görevinin ilk dersten kaç dakika önce başlayıp son dersten kaç dakika sonra biteceğini belirleyin."
        )
        body_duty.columnconfigure(0, weight=0, minsize=185)
        body_duty.columnconfigure(1, weight=1)
        body_duty.columnconfigure(2, weight=0, minsize=185)
        body_duty.columnconfigure(3, weight=1)

        ctk.CTkLabel(
            body_duty, text="Nöbet Başlama (Dersten Önce):",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A"
        ).grid(row=0, column=0, sticky="w", pady=5)
        f_start = ctk.CTkFrame(body_duty, fg_color="transparent")
        f_start.grid(row=0, column=1, sticky="w", padx=(8, 20), pady=5)
        self._create_entry(f_start, self.duty_start_offset_var, width=75).pack(side="left")
        ctk.CTkLabel(f_start, text="dk önce", font=ctk.CTkFont(family=FONT_FAMILY, size=13), text_color="#334155").pack(side="left", padx=6)

        ctk.CTkLabel(
            body_duty, text="Nöbet Bitiş (Dersten Sonra):",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A"
        ).grid(row=0, column=2, sticky="w", pady=5)
        f_end = ctk.CTkFrame(body_duty, fg_color="transparent")
        f_end.grid(row=0, column=3, sticky="w", padx=(8, 0), pady=5)
        self._create_entry(f_end, self.duty_end_offset_var, width=75).pack(side="left")
        ctk.CTkLabel(f_end, text="dk sonra", font=ctk.CTkFont(family=FONT_FAMILY, size=13), text_color="#334155").pack(side="left", padx=6)

    # =========================================================================
    # SEKME 3: NÖBET KAYDIRMA VE ROTASYON
    # =========================================================================
    def _build_tab_shift(self):
        tab = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        self.tab_frames["shift"] = tab

        body_shift = self._create_section_card(
            tab,
            "🔄 Hızlı Nöbet Kaydırma Varsayılan Davranışı",
            "Ana ekrandaki Hızlı Kaydır işleminde doğrudan uygulanacak rotasyon kuralını seçin."
        )

        options = [
            ("day_forward", "➡️ Günleri 1 Gün İleri Kaydır (Pazartesi ➔ Salı, Salı ➔ Çarşamba ... Cuma ➔ Pazartesi)"),
            ("day_backward", "⬅️ Günleri 1 Gün Geri Kaydır (Salı ➔ Pazartesi, Çarşamba ➔ Salı ... Pazartesi ➔ Cuma)"),
            ("loc_forward", "⬇️ Nöbet Yerlerini 1 Sıra Kaydır (1. Kat ➔ 2. Kat ... Zemin ➔ 1. Kat)"),
            ("loc_backward", "⬆️ Nöbet Yerlerini Ters Yönde Kaydır"),
            ("copy_next_week", "📅 Mevcut Nöbetleri 1 Gün Kaydırarak Sonraki Haftaya Kopyala"),
        ]

        for val, lbl in options:
            rb = ctk.CTkRadioButton(
                body_shift,
                text=lbl,
                value=val,
                variable=self.shift_mode_var,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                text_color="#0F172A",
                fg_color=COLOR_PRIMARY,
                hover_color=COLOR_PRIMARY_HOVER
            )
            rb.pack(anchor="w", pady=6)

        body_sec = self._create_section_card(
            tab,
            "🔒 Sabit Nöbet ve Kilit Koruması",
            "Özel durumu olan öğretmenlerin sabitlenmiş nöbetlerini kaydırma işleminden koruyun."
        )
        cb_lock = ctk.CTkCheckBox(
            body_sec,
            text="🔒 Sabit (Kilitli) nöbetlerin yerini otomatik koru (Kaydırmadan muaf tut)",
            variable=self.shift_preserve_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color="#0F172A",
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER
        )
        cb_lock.pack(anchor="w", pady=4)

    # =========================================================================
    # SEKME 4: BOŞ DERS, EK DERS & İŞ YÜKÜ
    # =========================================================================
    def _build_tab_rules(self):
        tab = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        self.tab_frames["rules"] = tab

        body_rules = self._create_section_card(
            tab,
            "⚖️ Akıllı Boş Ders Doldurma (İkame) Kuralları",
            "Gelmeyen öğretmenlerin derslerine nöbetçi öğretmen görevlendirirken uygulanacak öncelik kuralları."
        )

        checks = [
            (self.branch_priority_var, "⭐ Aynı Branş Önceliği: Gelmeyen öğretmenle aynı branştaki boş nöbetçiyi en üst öncelikle ata"),
            (self.ek_ders_alert_var, "📜 Ek Ders Rozeti: Resmi fişlerde '[⭐ Ek Ders Hak Eder - Branş Öğretmeni]' ibaresini ve mevzuat dipnotunu göster"),
            (self.workload_sharing_var, "🤝 İş Yükü Dengeleme: O gün boş nöbetçi varsa tek kalan derslere 'Ortak Gözetim' olarak otomatik ata"),
        ]
        for var, txt in checks:
            ctk.CTkCheckBox(
                body_rules,
                text=txt,
                variable=var,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                text_color="#0F172A",
                fg_color=COLOR_PRIMARY,
                hover_color=COLOR_PRIMARY_HOVER
            ).pack(anchor="w", pady=7)

        f_count = ctk.CTkFrame(body_rules, fg_color="transparent")
        f_count.pack(anchor="w", pady=(12, 2))
        ctk.CTkLabel(
            f_count,
            text="Ders Başına Varsayılan Nöbetçi Sayısı:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color="#0F172A"
        ).pack(side="left", padx=(0, 12))
        self._create_combobox(f_count, self.default_duty_per_lesson_var, ["1", "2"], width=90).pack(side="left")

    # =========================================================================
    # SEKME 5: NÖBET TALİMATNAMESİ
    # =========================================================================
    def _build_tab_duty_rules(self):
        tab = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        self.tab_frames["duty_rules"] = tab

        body_txt = self._create_section_card(
            tab,
            "📜 Nöbetçi Öğretmen Görev Talimatnamesi",
            "Resmi Nöbet Çizelgesi ve Görevlendirme Fişlerinin altında basılacak kurallar metni."
        )

        self.txt_rules = ctk.CTkTextbox(
            body_txt,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            height=230,
            fg_color="#F8FAFC",
            text_color="#0F172A",
            border_width=1,
            border_color="#CBD5E1",
            corner_radius=8,
            wrap="word"
        )
        self.txt_rules.pack(fill="both", expand=True, pady=(4, 4))
        self.txt_rules.insert("1.0", self.school.duty_rules)

    # =========================================================================
    # SEKME 6: SİSTEM FONT VE GÖRÜNÜM AYARLARI
    # =========================================================================
    def _build_tab_appearance(self):
        tab = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        self.tab_frames["appearance"] = tab

        # 0. SOL MENÜ TEMASI (AÇIK / KOYU)
        body_theme = self._create_section_card(
            tab,
            "🎨 Sol Menü Teması (Sidebar Style)",
            "Sol navigasyon menüsünün açık veya koyu görünümünü seçin."
        )
        body_theme.columnconfigure(0, weight=0, minsize=170)
        body_theme.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            body_theme,
            text="Sol Menü Rengi:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color="#0F172A"
        ).grid(row=0, column=0, sticky="w", pady=5)

        cb_sb_theme = self._create_combobox(
            body_theme,
            variable=self.sidebar_theme_var,
            values=["Koyu Antrasit (macOS Pro Dark)", "Saf Beyaz / Açık Gri (macOS Light)"],
            width=280
        )
        cb_sb_theme.grid(row=0, column=1, sticky="w", padx=(8, 0), pady=5)

        # 1. HIZLI FONT BOYUT ÖNAYARI VE YAZI TİPİ AİLESİ
        body_preset = self._create_section_card(
            tab,
            "🔤 1. Hızlı Font Boyut Önayarı ve Yazı Tipi Ailesi",
            "Tüm çizelge, buton, menü ve başlıklara uygulanacak yazı tipini ve ölçeği seçin."
        )
        body_preset.columnconfigure(0, weight=0, minsize=170)
        body_preset.columnconfigure(1, weight=1)
        body_preset.columnconfigure(2, weight=0, minsize=150)
        body_preset.columnconfigure(3, weight=1)

        ctk.CTkLabel(
            body_preset,
            text="Yazı Tipi (Font Ailesi):",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color="#0F172A"
        ).grid(row=0, column=0, sticky="w", pady=5)

        try:
            import tkinter.font as tkfont
            sys_fonts = sorted(list(set(f for f in tkfont.families(self) if not f.startswith("@") and not f.startswith("Wingdings"))))
        except Exception:
            sys_fonts = []
        popular_fonts = ["Segoe UI", "Calibri", "Arial", "Aptos", "Tahoma", "Verdana", "Trebuchet MS", "Roboto", "Georgia", "Consolas"]
        merged_fonts = []
        for pf in popular_fonts:
            if pf not in merged_fonts:
                merged_fonts.append(pf)
        for sf in sys_fonts:
            if sf not in merged_fonts:
                merged_fonts.append(sf)

        cb_font = self._create_combobox(
            body_preset,
            variable=self.font_family_var,
            values=merged_fonts,
            width=220,
            command=lambda _: self._update_appearance_preview()
        )
        cb_font.grid(row=0, column=1, sticky="ew", padx=(8, 20), pady=5)

        ctk.CTkLabel(
            body_preset,
            text="Genel Boyut Ölçeği:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color="#0F172A"
        ).grid(row=0, column=2, sticky="w", pady=5)

        preset_values = [
            "Standart (%100 - Önerilen)",
            "Büyük (%115 - Rahat Okuma)",
            "Çok Büyük (%130 - Geniş Ekran)",
            "Kompakt (%90 - Küçük Ekran)",
            "Özel (Detaylı Ayar)"
        ]
        cb_preset = self._create_combobox(
            body_preset,
            variable=self.font_preset_var,
            values=preset_values,
            width=220,
            command=lambda _: self._apply_preset_choice()
        )
        cb_preset.grid(row=0, column=3, sticky="ew", padx=(8, 0), pady=5)

        ctk.CTkLabel(
            body_preset,
            text="Hızlı Ölçek Seçimi:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color="#0F172A"
        ).grid(row=1, column=0, sticky="w", pady=(6, 2))

        f_preset_btns = ctk.CTkFrame(body_preset, fg_color="transparent")
        f_preset_btns.grid(row=1, column=1, columnspan=3, sticky="w", padx=(8, 0), pady=(6, 2))

        for p_name, short_label in [
            ("Standart (%100 - Önerilen)", "Standart (%100)"),
            ("Büyük (%115 - Rahat Okuma)", "Büyük (%115)"),
            ("Çok Büyük (%130 - Geniş Ekran)", "Çok Büyük (%130)"),
            ("Kompakt (%90 - Küçük Ekran)", "Kompakt (%90)")
        ]:
            b = create_modern_button(
                f_preset_btns,
                text=short_label,
                command=lambda name=p_name: self._set_preset(name),
                variant="primary" if "Standart" in short_label else "default",
                height=30
            )
            b.pack(side="left", padx=(0, 6))

        # 2. DETAYLI ALAN BAZLI FONT BOYUTLARI KARTI
        body_details = self._create_section_card(
            tab,
            "🔍 2. Detaylı / Alan Bazlı Font Boyutları",
            "İsterseniz her ekran elemanının piksel boyutunu bağımsız olarak özelleştirin."
        )

        f_cols = ctk.CTkFrame(body_details, fg_color="transparent")
        f_cols.pack(fill="x")

        f_left = ctk.CTkFrame(f_cols, fg_color="transparent")
        f_left.pack(side="left", fill="both", expand=True, padx=(0, 12))

        ctk.CTkLabel(
            f_left,
            text="📋 TABLO VE ÇİZELGE ELEMANLARI",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_PRIMARY
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        left_rows = [
            ("Öğretmen İsimleri:", self.font_size_teacher_var, ["13", "14", "15", "16", "17", "18", "20"], "px (Hücre ana metni)"),
            ("Öğretmen Yazı Kalınlığı:", self.font_weight_teacher_var, ["Kalın (Bold)", "Normal"], ""),
            ("Branş & Boş Dersler:", self.font_size_secondary_var, ["11", "12", "13", "14", "15"], "px (Hücre alt detayları)"),
            ("Tablo / Gün Başlıkları:", self.font_size_header_var, ["12", "13", "14", "15", "16"], "px (Katlar & Gün sütunu)"),
        ]
        for idx, (lbl_txt, var, vals, hint) in enumerate(left_rows, start=1):
            ctk.CTkLabel(f_left, text=lbl_txt, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A").grid(row=idx, column=0, sticky="w", pady=5)
            w_cb = 140 if len(vals[0]) > 3 else 85
            self._create_combobox(f_left, var, vals, width=w_cb, command=lambda _: self._on_custom_font_change()).grid(row=idx, column=1, sticky="w", padx=8, pady=5)
            if hint:
                ctk.CTkLabel(f_left, text=hint, font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color="#475569").grid(row=idx, column=2, sticky="w")

        f_right = ctk.CTkFrame(f_cols, fg_color="transparent")
        f_right.pack(side="right", fill="both", expand=True, padx=(12, 0))

        ctk.CTkLabel(
            f_right,
            text="🖥️ ARAYÜZ, BAŞLIK VE KONTROLLER",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_PRIMARY
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        right_rows = [
            ("Butonlar ve Menüler:", self.ui_font_size_var, ["12", "13", "14", "15", "16"], "px (Araç çubuğu, butonlar)"),
            ("Sayfa Başlıkları:", self.font_size_title_var, ["15", "16", "18", "20", "22"], "px (Üst başlık yazısı)"),
            ("Özet Kart Rakamları (KPI):", self.font_size_kpi_var, ["18", "20", "22", "24", "26", "28"], "px (İstatistik rakamları)"),
        ]
        for idx, (lbl_txt, var, vals, hint) in enumerate(right_rows, start=1):
            ctk.CTkLabel(f_right, text=lbl_txt, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A").grid(row=idx, column=0, sticky="w", pady=5)
            self._create_combobox(f_right, var, vals, width=85, command=lambda _: self._on_custom_font_change()).grid(row=idx, column=1, sticky="w", padx=8, pady=5)
            ctk.CTkLabel(f_right, text=hint, font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color="#475569").grid(row=idx, column=2, sticky="w")

        # 3. TABLO ÇİZGİLERİ VE CANLI ÖNİZLEME
        body_grid = self._create_section_card(
            tab,
            "📐 3. Tablo Çizgileri ve Canlı Önizleme",
            "Seçtiğiniz yazı tipi ve boyutların çizelge üzerinde nasıl görüneceğini canlı olarak inceleyin."
        )

        f_grid_row = ctk.CTkFrame(body_grid, fg_color="transparent")
        f_grid_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(f_grid_row, text="Çizgi Kalınlığı:", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A").pack(side="left")
        self._create_combobox(f_grid_row, self.grid_border_width_var, ["1", "2", "3"], width=80, command=lambda _: self._update_appearance_preview()).pack(side="left", padx=(8, 20))

        ctk.CTkLabel(f_grid_row, text="Çizgi Rengi:", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A").pack(side="left")
        colors = ["#CBD5E1", "#E2E8F0", "#94A3B8", "#64748B", "#2563EB"]
        self._create_combobox(f_grid_row, self.grid_border_color_var, colors, width=130, command=lambda _: self._update_appearance_preview()).pack(side="left", padx=8)

        self.lbl_color_hint = ctk.CTkLabel(f_grid_row, text="", font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color="#475569")
        self.lbl_color_hint.pack(side="left", padx=6)

        create_modern_button(
            f_grid_row,
            text="🔄 Varsayılan Fontlara Dön",
            command=self._reset_font_defaults,
            variant="default",
            height=32
        ).pack(side="right")

        # Canlı Önizleme Kutusu
        f_sample_row = tk.Frame(body_grid, bg="#F8FAFC", padx=14, pady=12, highlightbackground="#E2E8F0", highlightthickness=1)
        f_sample_row.pack(fill="x", pady=4)

        f_col_hdr = tk.Frame(f_sample_row, bg="#F8FAFC")
        f_col_hdr.pack(side="left", padx=(4, 16))
        tk.Label(f_col_hdr, text="Tablo Başlığı:", font=(FONT_FAMILY, 9, "bold"), bg="#F8FAFC", fg="#475569").pack(anchor="w", pady=(0, 3))

        self.f_sample_hdr = tk.Frame(f_col_hdr, bg="#1E293B", padx=12, pady=6)
        self.f_sample_hdr.pack()
        self.lbl_sample_hdr = tk.Label(
            self.f_sample_hdr,
            text="📍 1. Kat (A Blok)",
            font=(self.font_family_var.get(), -int(self.font_size_header_var.get() or 13), "bold"),
            bg="#1E293B",
            fg="#FFFFFF"
        )
        self.lbl_sample_hdr.pack()

        f_col_cell = tk.Frame(f_sample_row, bg="#F8FAFC")
        f_col_cell.pack(side="left", padx=(10, 16))
        tk.Label(f_col_cell, text="Tablo Hücresi:", font=(FONT_FAMILY, 9, "bold"), bg="#F8FAFC", fg="#475569").pack(anchor="w", pady=(0, 3))

        self.f_sample_cell = tk.Frame(
            f_col_cell,
            bg="#FFFFFF",
            relief="flat",
            bd=0,
            highlightbackground=self.grid_border_color_var.get() or "#CBD5E1",
            highlightthickness=int(self.grid_border_width_var.get() or 1),
            padx=14,
            pady=6
        )
        self.f_sample_cell.pack()

        self.lbl_sample_teacher = tk.Label(
            self.f_sample_cell,
            text="Ahmet YILMAZ",
            font=(self.font_family_var.get(), -int(self.font_size_teacher_var.get() or 15), "bold"),
            bg="#FFFFFF",
            fg="#0F172A"
        )
        self.lbl_sample_teacher.pack()

        self.lbl_sample_free = tk.Label(
            self.f_sample_cell,
            text="Boş: 3, 4. Ders",
            font=(self.font_family_var.get(), -int(self.font_size_secondary_var.get() or 12), "bold"),
            bg="#FFFFFF",
            fg="#047857"
        )
        self.lbl_sample_free.pack(pady=(1, 0))

        self.lbl_sample_branch = tk.Label(
            self.f_sample_cell,
            text="Matematik",
            font=(self.font_family_var.get(), -int(self.font_size_secondary_var.get() or 12)),
            bg="#FFFFFF",
            fg="#334155"
        )
        self.lbl_sample_branch.pack(pady=(1, 0))

        f_col_ui = tk.Frame(f_sample_row, bg="#F8FAFC")
        f_col_ui.pack(side="left", padx=(10, 16))
        tk.Label(f_col_ui, text="Butonlar:", font=(FONT_FAMILY, 9, "bold"), bg="#F8FAFC", fg="#475569").pack(anchor="w", pady=(0, 3))

        f_sample_btns = tk.Frame(f_col_ui, bg="#F8FAFC")
        f_sample_btns.pack(anchor="w")

        self.btn_sample_action = tk.Button(
            f_sample_btns,
            text="⚡ Dağıt",
            bg="#DBEAFE",
            fg="#1D4ED8",
            font=(self.font_family_var.get(), -int(self.ui_font_size_var.get() or 13), "bold"),
            relief="flat",
            bd=0,
            padx=10,
            pady=4
        )
        self.btn_sample_action.pack(side="left", padx=(0, 6))

        self.btn_sample_save = tk.Button(
            f_sample_btns,
            text="✓ Kaydet",
            bg="#D1FAE5",
            fg="#047857",
            font=(self.font_family_var.get(), -int(self.ui_font_size_var.get() or 13), "bold"),
            relief="flat",
            bd=0,
            padx=10,
            pady=4
        )
        self.btn_sample_save.pack(side="left")

        f_col_kpi = tk.Frame(f_sample_row, bg="#F8FAFC")
        f_col_kpi.pack(side="left", padx=10)
        tk.Label(f_col_kpi, text="İstatistik Kartı:", font=(FONT_FAMILY, 9, "bold"), bg="#F8FAFC", fg="#475569").pack(anchor="w", pady=(0, 3))

        self.f_sample_kpi = tk.Frame(f_col_kpi, bg="#FFFFFF", relief="flat", bd=0, highlightbackground="#E2E8F0", highlightthickness=1, padx=12, pady=4)
        self.f_sample_kpi.pack()

        self.lbl_sample_kpi_val = tk.Label(
            self.f_sample_kpi,
            text="35",
            font=(self.font_family_var.get(), -int(self.font_size_kpi_var.get() or 22), "bold"),
            bg="#FFFFFF",
            fg=COLOR_PRIMARY
        )
        self.lbl_sample_kpi_val.pack()

        self.lbl_sample_kpi_txt = tk.Label(
            self.f_sample_kpi,
            text="Aktif Öğretmen",
            font=(self.font_family_var.get(), -int(self.font_size_secondary_var.get() or 12), "bold"),
            bg="#FFFFFF",
            fg="#334155"
        )
        self.lbl_sample_kpi_txt.pack()

        self._update_appearance_preview()

    def _set_preset(self, preset_name: str):
        self.font_preset_var.set(preset_name)
        self._apply_preset_choice()

    def _apply_preset_choice(self):
        preset_name = self.font_preset_var.get()
        from ui.theme import FONT_PRESETS
        if preset_name in FONT_PRESETS:
            cfg = FONT_PRESETS[preset_name]
            self.font_size_teacher_var.set(str(cfg["teacher"]))
            self.font_size_secondary_var.set(str(cfg["secondary"]))
            self.font_size_header_var.set(str(cfg["header"]))
            self.ui_font_size_var.set(str(cfg["ui"]))
            self.font_size_title_var.set(str(cfg["title"]))
            self.font_size_kpi_var.set(str(cfg["kpi"]))
            self.font_weight_teacher_var.set("Kalın (Bold)" if cfg.get("weight") == "bold" else "Normal")
        self._update_appearance_preview()

    def _on_custom_font_change(self):
        self.font_preset_var.set("Özel (Detaylı Ayar)")
        self._update_appearance_preview()

    def _reset_font_defaults(self):
        self.font_family_var.set("Segoe UI")
        self.grid_border_width_var.set("1")
        self.grid_border_color_var.set("#CBD5E1")
        self._set_preset("Standart (%100 - Önerilen)")

    def _update_appearance_preview(self):
        try:
            fam = self.font_family_var.get() or "Segoe UI"
            t_size = int(self.font_size_teacher_var.get() or 15)
            sec_size = int(self.font_size_secondary_var.get() or 12)
            hdr_size = int(self.font_size_header_var.get() or 13)
            ui_size = int(self.ui_font_size_var.get() or 13)
            kpi_size = int(self.font_size_kpi_var.get() or 22)
            t_weight = "bold" if "kalın" in self.font_weight_teacher_var.get().lower() or "bold" in self.font_weight_teacher_var.get().lower() else "normal"
            width = int(self.grid_border_width_var.get() or 1)
            color = self.grid_border_color_var.get() or "#CBD5E1"

            if hasattr(self, "f_sample_cell"):
                self.f_sample_cell.configure(
                    highlightbackground=color,
                    highlightthickness=width
                )
            if hasattr(self, "lbl_sample_hdr"):
                self.lbl_sample_hdr.configure(font=(fam, -hdr_size, "bold"))
            if hasattr(self, "lbl_sample_teacher"):
                self.lbl_sample_teacher.configure(font=(fam, -t_size, t_weight))
            if hasattr(self, "lbl_sample_free"):
                self.lbl_sample_free.configure(font=(fam, -sec_size, "bold"))
            if hasattr(self, "lbl_sample_branch"):
                self.lbl_sample_branch.configure(font=(fam, -sec_size))
            if hasattr(self, "btn_sample_action"):
                self.btn_sample_action.configure(font=(fam, -ui_size, "bold"))
            if hasattr(self, "btn_sample_save"):
                self.btn_sample_save.configure(font=(fam, -ui_size, "bold"))
            if hasattr(self, "lbl_sample_kpi_val"):
                self.lbl_sample_kpi_val.configure(font=(fam, -kpi_size, "bold"))
            if hasattr(self, "lbl_sample_kpi_txt"):
                self.lbl_sample_kpi_txt.configure(font=(fam, -sec_size, "bold"))

            color_labels = {
                "#CBD5E1": "Yumuşak Açık Gri (#CBD5E1)",
                "#E2E8F0": "Çok Açık Gri (#E2E8F0)",
                "#94A3B8": "Belirgin Orta Gri (#94A3B8)",
                "#64748B": "Koyu Grafit (#64748B)",
                "#0F172A": "Koyu Lacivert / Siyah",
                "#2563EB": "Kurumsal Mavi"
            }
            if hasattr(self, "lbl_color_hint"):
                self.lbl_color_hint.configure(text=color_labels.get(color, color))
        except Exception:
            pass

    def _on_school_level_changed(self, event=None):
        level = self.school_level_var.get()
        if "İlkokul" in level:
            self.lesson_count_var.set("6")
        elif "Ortaokul" in level:
            self.lesson_count_var.set("7")
        elif "Lise" in level:
            self.lesson_count_var.set("8")

    # =========================================================================
    # SEKME 7: GÜVENLİK & YEREL AĞ (LAN)
    # =========================================================================
    def _build_tab_security(self):
        tab = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        self.tab_frames["security"] = tab

        body_pwd = self._create_section_card(
            tab,
            "🔐 Yönetici Giriş Şifresi ve Koruması",
            "Öğretmenler, Nöbet Yerleri ve Ayarlar ekranlarını yetkisiz değişikliklere karşı şifreyle koruyun."
        )

        is_prot = self.db.is_password_protected()
        status_txt = "🟢 Şifre Koruması AKTİF (Kritik ekranlar şifreyle açılır)" if is_prot else "⚪ Şifre Koruması DEVRE DIŞI (Korumasız mod)"
        status_color = "#059669" if is_prot else "#475569"

        self.lbl_pwd_status = ctk.CTkLabel(
            body_pwd,
            text=status_txt,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=status_color
        )
        self.lbl_pwd_status.pack(anchor="w", pady=(0, 10))

        f_pwd = ctk.CTkFrame(body_pwd, fg_color="transparent")
        f_pwd.pack(fill="x", pady=4)

        ctk.CTkLabel(f_pwd, text="Yeni Şifre:", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A", width=130, anchor="w").grid(row=0, column=0, pady=5, sticky="w")
        self.ent_new_pwd = self._create_entry(f_pwd, tk.StringVar(), width=220, show="●")
        self.ent_new_pwd.grid(row=0, column=1, pady=5, padx=(8, 16))

        ctk.CTkLabel(f_pwd, text="Şifre Tekrar:", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A", width=130, anchor="w").grid(row=1, column=0, pady=5, sticky="w")
        self.ent_new_pwd_rep = self._create_entry(f_pwd, tk.StringVar(), width=220, show="●")
        self.ent_new_pwd_rep.grid(row=1, column=1, pady=5, padx=(8, 16))

        f_pwd_btns = ctk.CTkFrame(body_pwd, fg_color="transparent")
        f_pwd_btns.pack(fill="x", pady=(10, 0))

        create_modern_button(f_pwd_btns, text="💾 Şifreyi Kaydet / Değiştir", command=self._save_password, variant="primary", height=34).pack(side="left", padx=(0, 8))
        if is_prot:
            create_modern_button(f_pwd_btns, text="🔓 Şifreyi Kaldır", command=self._remove_password, variant="danger", height=34).pack(side="left")

        # 2. YEREL AĞ (LAN) PAYLAŞIMI
        body_lan = self._create_section_card(
            tab,
            "🌐 Yerel Ağ (LAN) Otomatik Paylaşım & Bağlantı Sihirbazı",
            "Aynı okul ağındaki müdür ve müdür yardımcısı bilgisayarları arasında veritabanını ortak kullanın."
        )

        # A. Ana Sunucu Kutusu
        f_host_box = ctk.CTkFrame(body_lan, fg_color="#F8FAFC", corner_radius=8, border_width=1, border_color="#E2E8F0")
        f_host_box.pack(fill="x", pady=(0, 12))
        f_host_in = ctk.CTkFrame(f_host_box, fg_color="transparent")
        f_host_in.pack(fill="x", padx=14, pady=12)

        ctk.CTkLabel(f_host_in, text="🖥️ 1. Bu Bilgisayarı Ana Sunucu Yap (Paylaşıma Aç)", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color="#0F172A").pack(anchor="w")

        self.lbl_host_status = ctk.CTkLabel(
            f_host_in,
            text="⚪ Paylaşım Kapalı (Yalnızca bu bilgisayarda çalışılıyor)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color="#475569"
        )
        self.lbl_host_status.pack(anchor="w", pady=(4, 2))

        self.lbl_host_details = ctk.CTkLabel(
            f_host_in,
            text=f"Bilgisayar: {get_hostname()} | Yerel IP: {get_local_ip()}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color="#475569"
        )
        self.lbl_host_details.pack(anchor="w", pady=(0, 8))

        f_host_btns = ctk.CTkFrame(f_host_in, fg_color="transparent")
        f_host_btns.pack(fill="x")

        self.btn_start_host = create_modern_button(
            f_host_btns,
            text="▶️ Ağ Paylaşımını Başlat (Ana Sunucu Yap)",
            command=self._start_host,
            variant="primary",
            height=34
        )
        self.btn_start_host.pack(side="left", padx=(0, 8))

        self.btn_stop_host = create_modern_button(
            f_host_btns,
            text="⏹️ Paylaşımı Durdur",
            command=self._stop_host,
            variant="default",
            height=34
        )
        self.btn_stop_host.pack(side="left")

        # B. İstemci Kutusu
        f_client_box = ctk.CTkFrame(body_lan, fg_color="#F8FAFC", corner_radius=8, border_width=1, border_color="#E2E8F0")
        f_client_box.pack(fill="x", pady=(0, 12))
        f_client_in = ctk.CTkFrame(f_client_box, fg_color="transparent")
        f_client_in.pack(fill="x", padx=14, pady=12)

        ctk.CTkLabel(f_client_in, text="🔗 2. Ağdaki Ana Bilgisayara Bağlan (İstemci)", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color="#0F172A").pack(anchor="w")
        ctk.CTkLabel(f_client_in, text="Okul ağındaki aktif NöbetMatik sunucusunu tek tıkla arayıp eşitleyin:", font=ctk.CTkFont(family=FONT_FAMILY, size=13), text_color="#475569").pack(anchor="w", pady=(2, 8))

        f_scan_bar = ctk.CTkFrame(f_client_in, fg_color="transparent")
        f_scan_bar.pack(fill="x", pady=(0, 6))

        self.btn_scan_hosts = create_modern_button(
            f_scan_bar,
            text="🔍 Ağdaki Okul Sunucusunu Otomatik Bul",
            command=self._scan_network_hosts,
            variant="primary",
            height=34
        )
        self.btn_scan_hosts.pack(side="left", padx=(0, 10))

        self.lbl_scan_status = ctk.CTkLabel(
            f_scan_bar,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_PRIMARY
        )
        self.lbl_scan_status.pack(side="left")

        self.f_hosts_list = ctk.CTkFrame(f_client_in, fg_color="transparent")
        self.f_hosts_list.pack(fill="x")

        # C. Aktif Veritabanı
        f_cur_db = ctk.CTkFrame(body_lan, fg_color="transparent")
        f_cur_db.pack(fill="x", pady=(4, 0))

        ctk.CTkLabel(f_cur_db, text="Aktif Veritabanı Konumu:", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#0F172A").pack(anchor="w")
        self.lbl_cur_db = ctk.CTkLabel(
            f_cur_db,
            text=str(self.db.db_path),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_PRIMARY,
            wraplength=650,
            justify="left"
        )
        self.lbl_cur_db.pack(anchor="w", pady=(2, 8))

        f_lan_adv_btns = ctk.CTkFrame(body_lan, fg_color="transparent")
        f_lan_adv_btns.pack(fill="x")

        create_modern_button(f_lan_adv_btns, text="🔄 Varsayılan Yerel Veritabanına Geri Dön", command=self._reset_to_default_db, variant="default", height=32).pack(side="left", padx=(0, 8))
        create_modern_button(f_lan_adv_btns, text="📂 Manuel Dosya / Ağ Konumu Seç (.db)...", command=self._browse_lan_db, variant="default", height=32).pack(side="left")

        self._update_host_ui()

    # =========================================================================
    # SEKME 8: SİSTEM VE BAKIM
    # =========================================================================
    def _build_tab_maintenance(self):
        tab = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        self.tab_frames["maintenance"] = tab

        body_stats = self._create_section_card(
            tab,
            "📊 Veritabanı ve Sistem İstatistikleri",
            "Sistemde kayıtlı güncel veri büyüklüğü ve veritabanı dosya bilgileri."
        )

        teachers_count = len(self.db.get_teachers(active_only=False))
        active_t_count = len(self.db.get_teachers(active_only=True))
        loc_count = len(self.db.get_locations(active_only=False))
        att_count = len(self.db.get_attendance_records())

        stats = [
            f"• Toplam Kayıtlı Öğretmen: {teachers_count} (Aktif: {active_t_count})",
            f"• Toplam Nöbet Yeri: {loc_count}",
            f"• Arşivlenen Devamsızlık / İkame Kaydı: {att_count}",
            f"• Veritabanı Dosyası: {self.db.db_path}",
        ]
        for s in stats:
            ctk.CTkLabel(
                body_stats,
                text=s,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                text_color="#0F172A"
            ).pack(anchor="w", pady=3)

        body_act = self._create_section_card(
            tab,
            "🧹 Sistem Bakım ve Optimizasyon Araçları",
            "Veritabanı indekslerini hızlandırın ve gereksiz disk alanını temizleyin."
        )
        create_modern_button(
            body_act,
            text="🧹 Veritabanını Optimize Et (VACUUM)",
            command=self._vacuum_db,
            variant="primary",
            height=34
        ).pack(anchor="w", pady=4)

        body_reset = self._create_section_card(
            tab,
            "⚠️ Veri ve Sistem Sıfırlama (Temiz Başlangıç)",
            "💡 Sıfırlama işlemlerinden önce otomatik olarak güvenlik yedeği alınır."
        )

        f_reset_btns = ctk.CTkFrame(body_reset, fg_color="transparent")
        f_reset_btns.pack(fill="x", pady=4)

        create_modern_button(
            f_reset_btns,
            text="📚 Sadece Ders Programını Sıfırla",
            command=self._reset_timetables,
            variant="default",
            height=34
        ).pack(side="left", padx=(0, 10))

        create_modern_button(
            f_reset_btns,
            text="⚠️ Tüm Verileri Sıfırla (Temiz Kurulum)",
            command=self._reset_all_data,
            variant="danger",
            height=34
        ).pack(side="left")

        # 4. Yazılım Güncellemeleri Kartı
        body_update = self._create_section_card(
            tab,
            "🔄 Yazılım Güncellemeleri",
            "En son kararlı sürümü denetleyin ve güncelleme tercihlerini yönetin."
        )

        f_up_info = ctk.CTkFrame(body_update, fg_color="#F8FAFC", corner_radius=8, border_width=1, border_color="#E2E8F0")
        f_up_info.pack(fill="x", pady=(0, 10), padx=2)

        ctk.CTkLabel(
            f_up_info,
            text=f"• Mevcut NöbetMatik Sürümü: v{APP_VERSION} (Kararlı Dağıtım)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color="#059669"
        ).pack(side="left", padx=12, pady=8)

        f_chk_row = ctk.CTkFrame(body_update, fg_color="transparent")
        f_chk_row.pack(fill="x", pady=(2, 8))
        ctk.CTkCheckBox(
            f_chk_row,
            text="Uygulama açılışında yeni sürümleri arka planda otomatik denetle",
            variable=self.auto_check_updates_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13)
        ).pack(side="left")

        f_btn_row = ctk.CTkFrame(body_update, fg_color="transparent")
        f_btn_row.pack(fill="x", pady=(2, 0))
        self.btn_check_update = create_modern_button(
            f_btn_row,
            text="🔄 Güncellemeleri Şimdi Denetle",
            command=self._check_for_updates,
            variant="primary",
            height=34
        )
        self.btn_check_update.pack(side="left")

        self.btn_preview_update = create_modern_button(
            f_btn_row,
            text="✨ Bildirimi Önizle (Test)",
            command=self._preview_update_banner,
            variant="secondary",
            height=34
        )
        self.btn_preview_update.pack(side="left", padx=(8, 0))

    def _preview_update_banner(self):
        if hasattr(self.parent, "check_updates_manual"):
            self.parent.check_updates_manual(simulate_preview=True)
            self.destroy()

    def _check_for_updates(self):
        from logic.update_service import UpdateService
        repo = DEFAULT_GITHUB_REPO
        svc = UpdateService(repo)
        if hasattr(self, "btn_check_update"):
            self.btn_check_update.configure(state="disabled", text="⏳ Denetleniyor...")

        def worker():
            info = svc.check_for_updates()
            self.after(0, lambda: self._on_update_checked(info, svc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_update_checked(self, info: dict, svc):
        from ui.update_dialog import UpdateDialog
        if hasattr(self, "btn_check_update"):
            self.btn_check_update.configure(state="normal", text="🔄 Güncellemeleri Şimdi Denetle")

        if not info.get("success"):
            messagebox.showwarning(
                "Güncelleme Denetimi",
                f"Güncelleme kontrolü tamamlanamadı:\n{info.get('error')}\n\nİnternet bağlantınızı kontrol ediniz.",
                parent=self
            )
            return

        if info.get("has_update"):
            if hasattr(self.parent, "_on_startup_update_found"):
                self.parent._on_startup_update_found(info, svc)
            UpdateDialog(self, info, svc)
        else:
            messagebox.showinfo(
                "Yazılım Güncel",
                f"🎉 Tebrikler! En güncel NöbetMatik sürümünü (v{APP_VERSION}) kullanıyorsunuz.\n\n"
                f"Yeni bir güncelleme bulunmuyor.",
                parent=self
            )

    def _test_telegram_connection(self):
        from core.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
        from logic.feedback_service import FeedbackService, FeedbackData

        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            messagebox.showwarning(
                "Bilgi",
                "Telegram bot bilgileri henüz yapılandırılmamış.",
                parent=self
            )
            return

        sample = FeedbackData(
            category="✅ Doğrulama Testi",
            school_name=self.school_name_var.get().strip() or "Test Okulu",
            sender_name=self.principal_var.get().strip() or "Sistem Yöneticisi",
            contact="Telegram Doğrulama",
            subject="NöbetMatik Telegram Destek Hattı Test Mesajı",
            message="NöbetMatik doğrudan geliştirici destek ve geri bildirim hattı başarıyla aktiftir.",
            include_logs=False,
            system_info=FeedbackService.get_system_info_str()
        )
        ok, msg = FeedbackService.send_via_telegram(sample, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
        if ok:
            messagebox.showinfo("Başarılı", f"🎉 {msg}\n\nTelegram destek hattı bağlantısı başarıyla doğrulandı.", parent=self)
        else:
            messagebox.showerror(
                "Bağlantı Hatası",
                f"Mesaj iletilemedi:\n{msg}\n\nİnternet bağlantınızı kontrol ediniz.",
                parent=self
            )

    def _reset_timetables(self):
        if messagebox.askyesno("Onay", "Tüm öğretmen ders programı kayıtları silinecektir.\nİşleme başlamadan önce otomatik yedek alınacaktır.\nDevam etmek istiyor musunuz?", parent=self):
            try:
                from logic.backup_service import BackupService
                BackupService(self.db.db_path).create_backup()
                self.db.reset_timetables()
                messagebox.showinfo("Başarılı", "Ders programı sıfırlandı. Otomatik yedek alındı.", parent=self)
                if self.on_saved:
                    self.on_saved()
            except Exception as e:
                messagebox.showerror("Hata", f"Sıfırlama sırasında hata: {e}", parent=self)

    def _reset_all_data(self):
        confirm = messagebox.askyesno(
            "DİKKAT: Sistemi Sıfırla",
            "Bu işlem tüm öğretmenleri, haftalık ders programlarını ve nöbet atamalarını tamamen silecektir!\n\n"
            "İşlem öncesinde güvenlik amacıyla otomatik bir veritabanı yedeği alınacaktır.\n\n"
            "Sıfırlama işlemini onaylıyor musunuz?",
            parent=self
        )
        if confirm:
            try:
                from logic.backup_service import BackupService
                backup_path = BackupService(self.db.db_path).create_backup()
                self.db.reset_all_data(keep_school_info=True, keep_locations=True)
                messagebox.showinfo(
                    "Sıfırlama Tamamlandı",
                    f"Sistem temiz başlangıç durumuna getirildi.\n\n"
                    f"Güvenlik yedeğiniz oluşturuldu:\n{backup_path.name}\n\n"
                    f"Artık 'İçe Aktar' menüsünden e-Okul PDF belgenizi seçerek sıfırdan aktarım yapabilirsiniz.",
                    parent=self
                )
                if self.on_saved:
                    self.on_saved()
                self.close_view()
            except Exception as e:
                messagebox.showerror("Hata", f"Sıfırlama sırasında hata oluştu: {e}", parent=self)

    def _vacuum_db(self):
        try:
            with self.db.connection() as conn:
                conn.execute("VACUUM;")
            messagebox.showinfo("Başarılı", "Veritabanı indeksleri optimize edildi ve disk alanı temizlendi.", parent=self)
        except Exception as e:
            messagebox.showerror("Hata", f"Optimize işlemi sırasında hata: {e}", parent=self)

    def _update_host_ui(self):
        if is_global_host_running():
            self.lbl_host_status.configure(
                text="🟢 AĞ PAYLAŞIMI AKTİF (Diğer bilgisayarlar anında bağlanabilir)",
                text_color="#059669"
            )
            srv = get_global_host_service()
            path_info = srv.unc_share_path or "HTTP Port 52520"
            self.lbl_host_details.configure(
                text=f"Bilgisayar: {get_hostname()} | Yerel IP: {get_local_ip()} | Ağ Yolu: {path_info}"
            )
            self.btn_start_host.configure(state="disabled")
            self.btn_stop_host.configure(state="normal")
        else:
            self.lbl_host_status.configure(
                text="⚪ Paylaşım Kapalı (Yalnızca bu bilgisayarda çalışılıyor)",
                text_color="#475569"
            )
            self.lbl_host_details.configure(
                text=f"Bilgisayar: {get_hostname()} | Yerel IP: {get_local_ip()}"
            )
            self.btn_start_host.configure(state="normal")
            self.btn_stop_host.configure(state="disabled")

    def _start_host(self):
        school_name = self.school_name_var.get().strip() or "Okul"
        srv = get_global_host_service(self.db.db_path, school_name)
        ok, msg = srv.start()
        self._update_host_ui()
        if ok:
            messagebox.showinfo(
                "Ağ Paylaşımı Başlatıldı",
                f"Bu bilgisayar başarıyla NöbetMatik Ana Sunucusu yapıldı!\n\n"
                f"• Sunucu Adı: {get_hostname()}\n"
                f"• Yerel IP: {get_local_ip()}\n"
                f"• Ağ Yolu: {srv.unc_share_path or 'Dahili Ağ Servisi'}\n\n"
                f"Diğer bilgisayarlardaki idareciler, Ayarlar ekranından 'Ağdaki Okul Sunucusunu Otomatik Bul' butonuna basarak tek tıkla bağlanabilir.",
                parent=self
            )

    def _stop_host(self):
        if messagebox.askyesno("Onay", "Ağ paylaşımı durdurulacaktır. Diğer bilgisayarlar bu sunucuya erişemeyecektir.\nOnaylıyor musunuz?", parent=self):
            stop_global_host_service()
            self._update_host_ui()
            messagebox.showinfo("Bilgi", "Ağ paylaşımı durduruldu.", parent=self)

    def _scan_network_hosts(self):
        self.lbl_scan_status.configure(text="⏳ Yerel ağ taranıyor, lütfen bekleyiniz...")
        self.btn_scan_hosts.configure(state="disabled")
        for w in self.f_hosts_list.winfo_children():
            w.destroy()

        def worker():
            hosts = NetworkDiscoveryClient.discover_hosts(timeout=1.8)
            self.after(0, lambda: self._on_scan_completed(hosts))

        threading.Thread(target=worker, daemon=True).start()

    def _on_scan_completed(self, hosts: list):
        self.lbl_scan_status.configure(text="")
        self.btn_scan_hosts.configure(state="normal")
        for w in self.f_hosts_list.winfo_children():
            w.destroy()

        if not hosts:
            f_empty = ctk.CTkFrame(self.f_hosts_list, fg_color="#FEF2F2", corner_radius=8, border_width=1, border_color="#FCA5A5")
            f_empty.pack(fill="x", pady=4)
            ctk.CTkLabel(f_empty, text="⚠️ Yerel ağda açık bir NöbetMatik ana sunucusu bulunamadı.", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#DC2626").pack(anchor="w", padx=12, pady=(8, 2))
            ctk.CTkLabel(f_empty, text="İpucu: Ana bilgisayarda 'Ağ Paylaşımını Başlat' butonuna basıldığından ve aynı ağda olduğunuzdan emin olunuz.", font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color="#7F1D1D").pack(anchor="w", padx=12, pady=(0, 8))
            return

        ctk.CTkLabel(self.f_hosts_list, text=f"🎉 Bulunan Okul Sunucuları ({len(hosts)}):", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#059669").pack(anchor="w", pady=(0, 4))
        for h in hosts:
            card_h = ctk.CTkFrame(self.f_hosts_list, fg_color="#ECFDF5", corner_radius=8, border_width=1, border_color="#A7F3D0")
            card_h.pack(fill="x", pady=3)

            f_text = ctk.CTkFrame(card_h, fg_color="transparent")
            f_text.pack(side="left", fill="x", expand=True, padx=12, pady=8)

            school = h.get("school_name", "Okul")
            hname = h.get("hostname", "")
            ip = h.get("ip", "")
            ctk.CTkLabel(f_text, text=f"🏫 {school} ({hname} - {ip})", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#065F46").pack(anchor="w")
            share_info = h.get("share_path") or f"http://{ip}:{h.get('http_port', 52520)}"
            ctk.CTkLabel(f_text, text=f"Ağ Adresi: {share_info}", font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color="#047857").pack(anchor="w")

            create_modern_button(card_h, text="⚡ Tek Tıkla Bağlan", command=lambda host=h: self._connect_to_host(host), variant="primary", height=32).pack(side="right", padx=12, pady=8)

    def _connect_to_host(self, host_info: dict):
        local_data_dir = self.db.db_path.parent
        ok, db_path, msg = NetworkDiscoveryClient.test_and_connect(host_info, local_data_dir)
        if ok:
            self.db.set_setting("custom_db_path", db_path)
            self.lbl_cur_db.configure(text=db_path)
            messagebox.showinfo(
                "Ağ Bağlantısı Başarılı",
                f"{msg}\n\nDeğişikliğin tam olarak geçerli olması ve ağdaki güncel verilerin yüklenmesi için programı yeniden başlatınız.",
                parent=self
            )
            if self.on_saved:
                self.on_saved()
        else:
            messagebox.showerror("Bağlantı Hatası", msg, parent=self)

    def _save_password(self):
        p1 = self.ent_new_pwd.get().strip()
        p2 = self.ent_new_pwd_rep.get().strip()
        if not p1:
            messagebox.showwarning("Uyarı", "Lütfen bir şifre giriniz.", parent=self)
            return
        if p1 != p2:
            messagebox.showerror("Hata", "Girdiğiniz şifreler birbiriyle eşleşmiyor!", parent=self)
            return
        self.db.set_admin_password(p1)
        messagebox.showinfo("Başarılı", "Yönetici giriş şifresi başarıyla ayarlandı!", parent=self)
        self.lbl_pwd_status.configure(text="🟢 Şifre Koruması AKTİF (Kritik ekranlar şifreyle açılır)", text_color="#059669")
        self.ent_new_pwd.delete(0, tk.END)
        self.ent_new_pwd_rep.delete(0, tk.END)

    def _remove_password(self):
        if messagebox.askyesno("Onay", "Yönetici şifresi kaldırılacak ve koruma devre dışı bırakılacaktır.\nOnaylıyor musunuz?", parent=self):
            self.db.set_admin_password("")
            messagebox.showinfo("Başarılı", "Yönetici şifresi kaldırıldı.", parent=self)
            self.lbl_pwd_status.configure(text="⚪ Şifre Koruması DEVRE DIŞI (Korumasız mod)", text_color="#475569")

    def _browse_lan_db(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Ortak Ağ Veritabanı Seç (.db)",
            filetypes=[("SQLite Veritabanı (*.db)", "*.db"), ("Tüm Dosyalar (*.*)", "*.*")],
            parent=self
        )
        if path:
            messagebox.showinfo(
                "Veritabanı Değiştirildi",
                f"Yeni veritabanı konumu seçildi:\n{path}\n\nDeğişikliğin tam olarak geçerli olması için programı yeniden başlatınız.",
                parent=self
            )
            self.db.set_setting("custom_db_path", path)
            self.lbl_cur_db.configure(text=path)

    def _reset_to_default_db(self):
        if messagebox.askyesno("Onay", "Veritabanı konumu yerel varsayılan 'data/nobet.db' konumuna döndürülecektir.\nOnaylıyor musunuz?", parent=self):
            self.db.set_setting("custom_db_path", "")
            from core.config import DB_PATH
            self.lbl_cur_db.configure(text=str(DB_PATH))
            messagebox.showinfo("Başarılı", "Yerel varsayılan veritabanı aktif edildi.", parent=self)

    def _save_all(self):
        try:
            # 1. Okul
            self.school.name = self.school_name_var.get().strip()
            self.school.city = self.city_var.get().strip()
            self.school.district = self.district_var.get().strip()
            self.school.academic_year = self.year_var.get().strip()
            self.school.principal_name = self.principal_var.get().strip()
            self.school.duty_rules = self.txt_rules.get("1.0", tk.END).strip()
            self.school.school_level = self.school_level_var.get().strip()
            self.school.education_type = self.education_type_var.get().strip()
            count = 7
            try:
                count = int(self.lesson_count_var.get().strip())
            except ValueError:
                count = 7
            self.school.daily_periods = count
            self.db.save_school_info(self.school)

            # 2. Ayarlar (Key-Value)
            self.db.set_setting("vice_principal_name", self.vice_principal_var.get().strip())
            self.db.set_setting("daily_lesson_count", str(count))
            self.db.set_setting("first_lesson_start", self.lesson_start_var.get().strip())
            self.db.set_setting("last_lesson_end", self.lesson_end_var.get().strip())
            self.db.set_setting("lesson_duration_minutes", self.lesson_duration_var.get().strip())
            self.db.set_setting("break_duration_minutes", self.break_duration_var.get().strip())
            self.db.set_setting("duty_start_offset", self.duty_start_offset_var.get().strip())
            self.db.set_setting("duty_end_offset", self.duty_end_offset_var.get().strip())

            # 2.1 Detaylı Ders Saatleri Sözlüğü
            period_dict = {}
            for p in range(1, count + 1):
                if p in self.period_time_vars:
                    s_v, e_v = self.period_time_vars[p]
                    s = s_v.get().strip()
                    e = e_v.get().strip()
                    if s and e:
                        period_dict[p] = f"{s} - {e}"
            if period_dict:
                self.db.set_period_times(period_dict)
                if 1 in period_dict:
                    self.db.set_setting("first_lesson_start", period_dict[1].split(" - ")[0].strip())
                if count in period_dict:
                    self.db.set_setting("last_lesson_end", period_dict[count].split(" - ")[-1].strip())

            self.db.set_setting("last_shift_mode", self.shift_mode_var.get().strip())
            self.db.set_setting("last_shift_preserve", "1" if self.shift_preserve_var.get() else "0")

            self.db.set_setting("branch_priority_enabled", "1" if self.branch_priority_var.get() else "0")
            self.db.set_setting("workload_sharing_enabled", "1" if self.workload_sharing_var.get() else "0")
            self.db.set_setting("ek_ders_alert_enabled", "1" if self.ek_ders_alert_var.get() else "0")
            self.db.set_setting("default_duty_per_lesson", self.default_duty_per_lesson_var.get().strip())

            # 3. Görünüm, Yazı Tipi ve Sistem Font Ayarları
            sb_choice = self.sidebar_theme_var.get().lower()
            new_sb_val = "light" if "açık" in sb_choice or "light" in sb_choice or "beyaz" in sb_choice else "dark"
            self.db.set_setting("sidebar_theme", new_sb_val)
            self.db.set_setting("font_family", self.font_family_var.get().strip())
            self.db.set_setting("font_scale_preset", self.font_preset_var.get().strip())
            self.db.set_setting("font_size_teacher", self.font_size_teacher_var.get().strip())
            self.db.set_setting("font_size_secondary", self.font_size_secondary_var.get().strip())
            self.db.set_setting("font_size_header", self.font_size_header_var.get().strip())
            self.db.set_setting("ui_font_size", self.ui_font_size_var.get().strip())
            self.db.set_setting("font_size_page_title", self.font_size_title_var.get().strip())
            self.db.set_setting("font_size_kpi_value", self.font_size_kpi_var.get().strip())
            w_val = "bold" if "kalın" in self.font_weight_teacher_var.get().lower() or "bold" in self.font_weight_teacher_var.get().lower() else "normal"
            self.db.set_setting("font_weight_teacher", w_val)
            self.db.set_setting("grid_border_width", self.grid_border_width_var.get().strip())
            self.db.set_setting("grid_border_color", self.grid_border_color_var.get().strip())
            self.db.set_setting("font_size", self.font_size_teacher_var.get().strip())

            from ui.theme import load_theme_settings, setup_styles
            load_theme_settings(self.db)
            try:
                setup_styles(self.winfo_toplevel(), self.db)
            except Exception as e_style:
                logger.warning(f"Tema yenilenirken uyarı: {e_style}")

            messagebox.showinfo("Başarılı", "Tüm sistem, görünüm ve yönetim ayarları kaydedildi!", parent=self)
            if self.on_saved:
                self.on_saved()
            self.close_view()

        except Exception as e:
            logger.error(f"Ayarlar kaydedilirken hata: {e}")
            messagebox.showerror("Hata", f"Ayarlar kaydedilemedi:\n{e}", parent=self)


class SettingsDialog(tk.Toplevel):
    """Geriye dönük uyumluluk için Toplevel sarmalayıcı."""
    def __init__(self, parent: tk.Widget, db: Database, on_saved: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.title("⚙️ Sistem ve Okul Yönetim Ayarları")
        self.geometry("920x680")
        self.minsize(760, 560)
        self.transient(parent)
        self.view = SettingsView(self, db, on_saved=on_saved, on_finish=self.destroy)
        self.view.pack(fill="both", expand=True)

    def __getattr__(self, name):
        if "view" in self.__dict__ and hasattr(self.view, name):
            return getattr(self.view, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
