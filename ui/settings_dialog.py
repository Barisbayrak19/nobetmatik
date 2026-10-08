"""
Kapsamlı Sistem, Okul ve Yönetim Ayarları Ekranı (Comprehensive Settings Center)
Apple Human Interface Guidelines esintileriyle:
- Okul ve Yönetim Bilgileri (Müdür & Müdür Yardımcısı)
- Ders ve Nöbet Zaman Çizelgesi
- Nöbet Kaydırma ve Otomatik Rotasyon Tercihleri
- Boş Ders, Ek Ders ve İş Yükü Dengeleme Kuralları
- Nöbetçi Öğretmen Görev Talimatnamesi
- Sistem ve Veritabanı İstatistikleri / Bakım
"""
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Callable, Optional

from core.models import SchoolInfo
from core.database import Database
from core.config import APP_VERSION, DEFAULT_GITHUB_REPO
from core.logger import logger
from logic.update_service import UpdateService
from ui.update_dialog import UpdateDialog
from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_SECONDARY, COLOR_SUCCESS,
    COLOR_DANGER, COLOR_BORDER, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, FONT_FAMILY
)
from logic.network_service import (
    get_global_host_service, is_global_host_running, stop_global_host_service,
    NetworkDiscoveryClient, get_local_ip, get_hostname
)

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent: tk.Widget, db: Database, on_saved: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.db = db
        self.on_saved = on_saved
        self.school = self.db.get_school_info()

        self.title("⚙️ Sistem ve Okul Yönetim Ayarları")
        self.geometry("780x640")
        self.minsize(700, 540)
        self.configure(bg=COLOR_BG)
        self.transient(parent)
        self.grab_set()

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
        self.duty_start_offset_var = tk.StringVar(value=self.db.get_setting("duty_start_offset", "30")) # dk önce
        self.duty_end_offset_var = tk.StringVar(value=self.db.get_setting("duty_end_offset", "30"))     # dk sonra

        # 3. Kaydırma Tercihleri
        self.shift_mode_var = tk.StringVar(value=self.db.get_setting("last_shift_mode", "day_forward"))
        self.shift_preserve_var = tk.BooleanVar(value=self.db.get_setting("last_shift_preserve", "1") == "1")

        # 4. Boş Ders & Ek Ders Kuralları
        self.branch_priority_var = tk.BooleanVar(value=self.db.get_setting("branch_priority_enabled", "1") == "1")
        self.workload_sharing_var = tk.BooleanVar(value=self.db.get_setting("workload_sharing_enabled", "1") == "1")
        self.ek_ders_alert_var = tk.BooleanVar(value=self.db.get_setting("ek_ders_alert_enabled", "1") == "1")
        self.default_duty_per_lesson_var = tk.StringVar(value=self.db.get_setting("default_duty_per_lesson", "1"))

        # 5. Görünüm, Yazı Tipi ve Tablo Çizgileri
        self.font_family_var = tk.StringVar(value=self.db.get_setting("font_family", "Segoe UI"))
        self.font_size_var = tk.StringVar(value=self.db.get_setting("font_size", "9"))
        self.ui_font_size_var = tk.StringVar(value=self.db.get_setting("ui_font_size", "10"))
        self.grid_border_width_var = tk.StringVar(value=self.db.get_setting("grid_border_width", "1"))
        self.grid_border_color_var = tk.StringVar(value=self.db.get_setting("grid_border_color", "#CBD5E1"))

        # 6. Yazılım Güncelleme Tercihleri
        self.github_repo_var = tk.StringVar(value=self.db.get_setting("github_repo", DEFAULT_GITHUB_REPO))
        self.auto_check_updates_var = tk.BooleanVar(value=self.db.get_setting("auto_check_updates", "1") == "1")

        self._build_ui()

    def _build_ui(self):
        # Üst Apple Başlığı
        top_frame = tk.Frame(self, bg="#0F172A", padx=20, pady=12)
        top_frame.pack(fill="x", side="top")

        lbl_title = tk.Label(
            top_frame,
            text="⚙️ SİSTEM, KURUM VE YÖNETİM AYARLARI",
            font=(FONT_FAMILY, 12, "bold"),
            fg="#FFFFFF",
            bg="#0F172A"
        )
        lbl_title.pack(anchor="w")

        lbl_desc = tk.Label(
            top_frame,
            text="Okul bilgileri, nöbet saatleri, otomatik kaydırma kuralları ve mevzuat parametrelerini yönetin.",
            font=(FONT_FAMILY, 9),
            fg="#94A3B8",
            bg="#0F172A"
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        # Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=12)

        self._build_tab_school()
        self._build_tab_schedule()
        self._build_tab_shift()
        self._build_tab_rules()
        self._build_tab_duty_rules()
        self._build_tab_appearance()
        self._build_tab_security()
        self._build_tab_maintenance()

        # Alt Butonlar
        bottom_bar = tk.Frame(self, bg=COLOR_BG, height=50)
        bottom_bar.pack(fill="x", side="bottom", padx=15, pady=(0, 15))

        btn_cancel = ttk.Button(bottom_bar, text="Vazgeç", command=self.destroy)
        btn_cancel.pack(side="right", padx=(6, 0))

        btn_save = ttk.Button(
            bottom_bar,
            text="💾 Tüm Ayarları Kaydet",
            style="Primary.TButton",
            command=self._save_all
        )
        btn_save.pack(side="right")

    # Sekme 1: Okul & İdare
    def _build_tab_school(self):
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="🏫 Okul ve İdare")

        card = tk.LabelFrame(tab, text=" Kurum Bilgileri ", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, padx=15, pady=12, relief="solid", bd=1)
        card.pack(fill="x", pady=(0, 10))

        fields = [
            ("Okul Adı:", self.school_name_var),
            ("İlçe:", self.district_var),
            ("İl:", self.city_var),
            ("Eğitim Öğretim Yılı:", self.year_var),
        ]
        for idx, (lbl, var) in enumerate(fields):
            tk.Label(card, text=lbl, font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=idx, column=0, sticky="w", pady=4)
            ttk.Entry(card, textvariable=var, width=38, font=(FONT_FAMILY, 9)).grid(row=idx, column=1, sticky="w", pady=4, padx=(10, 0))

        # Okul Kademesi ve Eğitim Şekli
        tk.Label(card, text="Okul Kademesi (Türü):", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=4, column=0, sticky="w", pady=4)
        cb_level = ttk.Combobox(
            card,
            textvariable=self.school_level_var,
            values=["İlkokul", "Ortaokul", "İmam Hatip Ortaokulu", "Anadolu Lisesi", "Fen Lisesi", "Mesleki ve Teknik Anadolu Lisesi", "Diğer"],
            state="readonly",
            width=36
        )
        cb_level.grid(row=4, column=1, sticky="w", pady=4, padx=(10, 0))
        cb_level.bind("<<ComboboxSelected>>", self._on_school_level_changed)

        tk.Label(card, text="Eğitim Şekli:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=5, column=0, sticky="w", pady=4)
        cb_edu = ttk.Combobox(
            card,
            textvariable=self.education_type_var,
            values=["Normal (Tekli)", "İkili Eğitim (Sabahçı - Öğlenci)"],
            state="readonly",
            width=36
        )
        cb_edu.grid(row=5, column=1, sticky="w", pady=4, padx=(10, 0))

        card_admin = tk.LabelFrame(tab, text=" İdare ve Yetkililer (Belge İmzaları) ", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, padx=15, pady=12, relief="solid", bd=1)
        card_admin.pack(fill="x")

        tk.Label(card_admin, text="Okul Müdürü:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(card_admin, textvariable=self.principal_var, width=38, font=(FONT_FAMILY, 9)).grid(row=0, column=1, sticky="w", pady=4, padx=(10, 0))

        tk.Label(card_admin, text="Müdür Yardımcısı:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(card_admin, textvariable=self.vice_principal_var, width=38, font=(FONT_FAMILY, 9)).grid(row=1, column=1, sticky="w", pady=4, padx=(10, 0))

    # Sekme 2: Ders ve Nöbet Saatleri
    def _build_tab_schedule(self):
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="⏰ Ders & Nöbet Saatleri")

        card = tk.LabelFrame(tab, text=" Zaman Çizelgesi ", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, padx=15, pady=12, relief="solid", bd=1)
        card.pack(fill="x", pady=(0, 10))

        tk.Label(card, text="Günlük Ders Sayısı:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=0, column=0, sticky="w", pady=6)
        cb_count = ttk.Combobox(card, textvariable=self.lesson_count_var, values=["6", "7", "8"], state="readonly", width=8)
        cb_count.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=6)

        tk.Label(card, text="İlk Ders Başlama Saati:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(card, textvariable=self.lesson_start_var, width=10).grid(row=1, column=1, sticky="w", padx=(10, 0), pady=6)

        tk.Label(card, text="Son Ders Bitiş Saati:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(card, textvariable=self.lesson_end_var, width=10).grid(row=2, column=1, sticky="w", padx=(10, 0), pady=6)

        card_duty = tk.LabelFrame(tab, text=" Nöbet Görev Süresi (MEB Yönetmeliği) ", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, padx=15, pady=12, relief="solid", bd=1)
        card_duty.pack(fill="x")

        tk.Label(card_duty, text="Nöbet Başlama (Ders Başlamadan):", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=0, column=0, sticky="w", pady=6)
        f_start = tk.Frame(card_duty, bg=COLOR_CARD)
        f_start.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=6)
        ttk.Entry(f_start, textvariable=self.duty_start_offset_var, width=6).pack(side="left")
        tk.Label(f_start, text="dakika önce", font=(FONT_FAMILY, 9), bg=COLOR_CARD).pack(side="left", padx=4)

        tk.Label(card_duty, text="Nöbet Bitiş (Ders Bittikten):", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=1, column=0, sticky="w", pady=6)
        f_end = tk.Frame(card_duty, bg=COLOR_CARD)
        f_end.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=6)
        ttk.Entry(f_end, textvariable=self.duty_end_offset_var, width=6).pack(side="left")
        tk.Label(f_end, text="dakika sonra", font=(FONT_FAMILY, 9), bg=COLOR_CARD).pack(side="left", padx=4)

    # Sekme 3: Kaydırma ve Rotasyon Kuralları
    def _build_tab_shift(self):
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="🔄 Nöbet Kaydırma")

        card = tk.LabelFrame(tab, text=" 'Nöbet Kaydır' Tuşu Varsayılan Davranışı ", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, padx=15, pady=15, relief="solid", bd=1)
        card.pack(fill="x", pady=(0, 10))

        tk.Label(card, text="Ana ekrandaki '🔄 Nöbet Kaydır' tuşuna tıklandığında doğrudan uygulanacak kural:", font=(FONT_FAMILY, 9), fg=COLOR_TEXT_MUTED, bg=COLOR_CARD).pack(anchor="w", pady=(0, 10))

        options = [
            ("day_forward", "➡️ Günleri 1 Gün İleri Kaydır (Pazartesi ➔ Salı, Salı ➔ Çarşamba ... Cuma ➔ Pazartesi)"),
            ("day_backward", "⬅️ Günleri 1 Gün Geri Kaydır (Salı ➔ Pazartesi, Çarşamba ➔ Salı ... Pazartesi ➔ Cuma)"),
            ("loc_forward", "⬇️ Nöbet Yerlerini 1 Sıra Kaydır (1. Kat ➔ 2. Kat ... Zemin ➔ 1. Kat)"),
            ("loc_backward", "⬆️ Nöbet Yerlerini Ters Yönde Kaydır"),
            ("copy_next_week", "📅 Mevcut Nöbetleri 1 Gün Kaydırarak Sonraki Haftaya Kopyala"),
        ]

        for val, lbl in options:
            ttk.Radiobutton(card, text=lbl, value=val, variable=self.shift_mode_var).pack(anchor="w", pady=3)

        card_sec = tk.LabelFrame(tab, text=" Güvenlik ve Kilit Koruması ", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, padx=15, pady=12, relief="solid", bd=1)
        card_sec.pack(fill="x")

        ttk.Checkbutton(card_sec, text="🔒 Sabit (Kilitli) nöbetlerin yerini otomatik koru (Kaydırmadan muaf tut)", variable=self.shift_preserve_var).pack(anchor="w", pady=4)

    # Sekme 4: Boş Ders, Ek Ders & İş Yükü
    def _build_tab_rules(self):
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="⚖️ Boş Ders & Ek Ders")

        card = tk.LabelFrame(tab, text=" Akıllı İkame Kuralları ", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, padx=15, pady=15, relief="solid", bd=1)
        card.pack(fill="x", pady=(0, 10))

        ttk.Checkbutton(card, text="⭐ Aynı Branş Önceliği: Gelmeyen öğretmenle aynı branştaki boş nöbetçiyi en üst öncelikle ata", variable=self.branch_priority_var).pack(anchor="w", pady=6)
        ttk.Checkbutton(card, text="📜 Ek Ders Rozeti: Resmi fişlerde '[⭐ Ek Ders Hak Eder - Branş Öğretmeni]' ibaresini ve mevzuat dipnotunu göster", variable=self.ek_ders_alert_var).pack(anchor="w", pady=6)
        ttk.Checkbutton(card, text="🤝 İş Yükü Dengeleme: O gün boş nöbetçi varsa tek kalan derslere 'Ortak Gözetim' olarak otomatik ata", variable=self.workload_sharing_var).pack(anchor="w", pady=6)

        f_count = tk.Frame(card, bg=COLOR_CARD)
        f_count.pack(anchor="w", pady=(8, 0))
        tk.Label(f_count, text="Ders Başına Varsayılan Nöbetçi Sayısı:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).pack(side="left", padx=(0, 8))
        cb = ttk.Combobox(f_count, textvariable=self.default_duty_per_lesson_var, values=["1", "2"], state="readonly", width=4)
        cb.pack(side="left")

    # Sekme 5: Nöbet Talimatnamesi
    def _build_tab_duty_rules(self):
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="📜 Görev Talimatnamesi")

        ttk.Label(tab, text="Resmi Nöbet Çizelgesi ve Görevlendirme Fişlerinin altında basılacak kurallar:", font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", pady=(0, 6))

        self.txt_rules = tk.Text(tab, font=(FONT_FAMILY, 9), wrap="word", height=14)
        self.txt_rules.pack(fill="both", expand=True, pady=(0, 5))
        self.txt_rules.insert(tk.END, self.school.duty_rules)

    # Sekme 6: Bakım ve Sistem Bilgisi
    def _build_tab_maintenance(self):
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="💾 Sistem & Bilgi")

        card_stats = tk.LabelFrame(tab, text=" Veritabanı ve Sistem İstatistikleri ", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, padx=15, pady=12, relief="solid", bd=1)
        card_stats.pack(fill="x", pady=(0, 15))

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
            tk.Label(card_stats, text=s, font=(FONT_FAMILY, 9), bg=COLOR_CARD).pack(anchor="w", pady=2)

        card_act = tk.LabelFrame(tab, text=" Sistem Bakım Araçları ", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, padx=15, pady=12, relief="solid", bd=1)
        card_act.pack(fill="x", pady=(0, 15))

        btn_vac = ttk.Button(card_act, text="🧹 Veritabanını Optimize Et (VACUUM)", command=self._vacuum_db)
        btn_vac.pack(anchor="w", pady=4)

        # Yazılım Güncellemeleri (GitHub Releases)
        card_update = tk.LabelFrame(tab, text=" 🔄 Yazılım Güncellemeleri (GitHub Releases) ", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, padx=15, pady=12, relief="solid", bd=1)
        card_update.pack(fill="x", pady=(0, 15))

        f_up_top = ttk.Frame(card_update)
        f_up_top.pack(fill="x", pady=(0, 6))

        tk.Label(f_up_top, text=f"• Mevcut NöbetMatik Sürümü: v{APP_VERSION}", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, fg="#0F172A").pack(side="left")

        f_repo = ttk.Frame(card_update)
        f_repo.pack(fill="x", pady=(0, 6))

        tk.Label(f_repo, text="GitHub Deposu (Kullanıcı/Depo):", font=(FONT_FAMILY, 9), bg=COLOR_CARD).pack(side="left", padx=(0, 6))
        ent_repo = ttk.Entry(f_repo, textvariable=self.github_repo_var, width=28)
        ent_repo.pack(side="left", padx=(0, 12))

        chk_auto = ttk.Checkbutton(card_update, text="Uygulama açılışında yeni sürümleri otomatik denetle", variable=self.auto_check_updates_var)
        chk_auto.pack(anchor="w", pady=(0, 8))

        self.btn_check_update = ttk.Button(card_update, text="🔄 Güncellemeleri Şimdi Denetle", command=self._check_for_updates)
        self.btn_check_update.pack(anchor="w")

        # Sıfırlama ve Temiz Başlangıç Bölümü
        card_reset = tk.LabelFrame(tab, text=" Veri ve Sistem Sıfırlama (Temiz Başlangıç) ", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, padx=15, pady=12, relief="solid", bd=1)
        card_reset.pack(fill="x")

        tk.Label(
            card_reset,
            text="💡 Sıfırlama işlemlerinden önce otomatik olarak veritabanı yedeği alınır.",
            font=(FONT_FAMILY, 8, "italic"),
            bg=COLOR_CARD,
            fg="#64748B"
        ).pack(anchor="w", pady=(0, 8))

        f_reset_btns = ttk.Frame(card_reset)
        f_reset_btns.pack(fill="x")

        btn_reset_timetables = ttk.Button(
            f_reset_btns,
            text="📚 Sadece Ders Programını Sıfırla",
            command=self._reset_timetables
        )
        btn_reset_timetables.pack(side="left", padx=(0, 10))

        btn_reset_all = ttk.Button(
            f_reset_btns,
            text="⚠️ Tüm Verileri Sıfırla (Temiz Kurulum)",
            style="Danger.TButton",
            command=self._reset_all_data
        )
        btn_reset_all.pack(side="left")

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
                self.destroy()
            except Exception as e:
                messagebox.showerror("Hata", f"Sıfırlama sırasında hata oluştu: {e}", parent=self)

    def _vacuum_db(self):
        try:
            with self.db.connection() as conn:
                conn.execute("VACUUM;")
            messagebox.showinfo("Başarılı", "Veritabanı indeksleri optimize edildi ve disk alanı temizlendi.", parent=self)
        except Exception as e:
            messagebox.showerror("Hata", f"Optimize işlemi sırasında hata: {e}", parent=self)

    def _check_for_updates(self):
        repo = self.github_repo_var.get().strip() or DEFAULT_GITHUB_REPO
        svc = UpdateService(repo)
        if hasattr(self, "btn_check_update"):
            self.btn_check_update.configure(state="disabled", text="⏳ Denetleniyor...")

        def worker():
            info = svc.check_for_updates()
            self.after(0, lambda: self._on_update_checked(info, svc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_update_checked(self, info: dict, svc: UpdateService):
        if hasattr(self, "btn_check_update"):
            self.btn_check_update.configure(state="normal", text="🔄 Güncellemeleri Şimdi Denetle")

        if not info.get("success"):
            messagebox.showwarning("Güncelleme Denetimi", f"Güncelleme kontrolü tamamlanamadı:\n{info.get('error')}", parent=self)
            return

        if info.get("has_update"):
            UpdateDialog(self, info, svc)
        else:
            messagebox.showinfo(
                "Yazılım Güncel",
                f"Tebrikler! En güncel NöbetMatik sürümünü (v{APP_VERSION}) kullanıyorsunuz.",
                parent=self
            )

    # Sekme 6: Görünüm ve Tablo Çizgileri
    def _build_tab_appearance(self):
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="🎨 Görünüm & Tablo Çizgileri")

        card_font = tk.LabelFrame(
            tab,
            text=" 🔤 Program Geneli Yazı Tipi (Font) Ayarları ",
            font=(FONT_FAMILY, 9, "bold"),
            bg=COLOR_CARD,
            padx=15,
            pady=12,
            relief="solid",
            bd=1
        )
        card_font.pack(fill="x", pady=(0, 10))

        tk.Label(card_font, text="Yazı Tipi (Font Ailesi):", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=0, column=0, sticky="w", pady=5)
        fonts = ["Segoe UI", "Arial", "Calibri", "Tahoma", "Verdana", "Trebuchet MS", "Roboto"]
        cb_font = ttk.Combobox(card_font, textvariable=self.font_family_var, values=fonts, state="readonly", width=22, font=(FONT_FAMILY, 9))
        cb_font.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=5)
        cb_font.bind("<<ComboboxSelected>>", lambda e: self._update_appearance_preview())

        tk.Label(card_font, text="Tablo / Çizelge Font Boyutu:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=1, column=0, sticky="w", pady=5)
        sizes = ["8", "9", "10", "11", "12"]
        cb_size = ttk.Combobox(card_font, textvariable=self.font_size_var, values=sizes, state="readonly", width=8, font=(FONT_FAMILY, 9))
        cb_size.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=5)
        cb_size.bind("<<ComboboxSelected>>", lambda e: self._update_appearance_preview())
        tk.Label(card_font, text="punto (Hücre içi isim ve branşlar)", font=(FONT_FAMILY, 8), fg=COLOR_TEXT_MUTED, bg=COLOR_CARD).grid(row=1, column=2, sticky="w", padx=(6, 0))

        tk.Label(card_font, text="Buton ve Menü Font Boyutu:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=2, column=0, sticky="w", pady=5)
        cb_ui_size = ttk.Combobox(card_font, textvariable=self.ui_font_size_var, values=sizes, state="readonly", width=8, font=(FONT_FAMILY, 9))
        cb_ui_size.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=5)
        cb_ui_size.bind("<<ComboboxSelected>>", lambda e: self._update_appearance_preview())
        tk.Label(card_font, text="punto (Araç çubuğu, butonlar ve menüler)", font=(FONT_FAMILY, 8), fg=COLOR_TEXT_MUTED, bg=COLOR_CARD).grid(row=2, column=2, sticky="w", padx=(6, 0))

        card_grid = tk.LabelFrame(
            tab,
            text=" 📐 Çizelge & Tablo Ayırıcı Çizgi Ayarları ",
            font=(FONT_FAMILY, 9, "bold"),
            bg=COLOR_CARD,
            padx=15,
            pady=10,
            relief="solid",
            bd=1
        )
        card_grid.pack(fill="x", pady=(0, 10))

        tk.Label(card_grid, text="Çizgi Kalınlığı:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=0, column=0, sticky="w", pady=5)
        widths = ["1", "2", "3"]
        cb_width = ttk.Combobox(card_grid, textvariable=self.grid_border_width_var, values=widths, state="readonly", width=8, font=(FONT_FAMILY, 9))
        cb_width.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=5)
        cb_width.bind("<<ComboboxSelected>>", lambda e: self._update_appearance_preview())
        tk.Label(card_grid, text="piksel (px)", font=(FONT_FAMILY, 8), fg=COLOR_TEXT_MUTED, bg=COLOR_CARD).grid(row=0, column=2, sticky="w", padx=(6, 0))

        tk.Label(card_grid, text="Çizgi Rengi:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=1, column=0, sticky="w", pady=5)
        colors = ["#CBD5E1", "#94A3B8", "#64748B", "#0F172A", "#2563EB"]
        cb_color = ttk.Combobox(card_grid, textvariable=self.grid_border_color_var, values=colors, state="readonly", width=12, font=(FONT_FAMILY, 9))
        cb_color.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=5)
        cb_color.bind("<<ComboboxSelected>>", lambda e: self._update_appearance_preview())

        color_labels = {
            "#CBD5E1": "Yumuşak Açık Gri (Standart)",
            "#94A3B8": "Belirgin Orta Gri",
            "#64748B": "Koyu Grafit",
            "#0F172A": "Koyu Lacivert / Siyah",
            "#2563EB": "Kurumsal Mavi"
        }
        self.lbl_color_hint = tk.Label(card_grid, text=color_labels.get(self.grid_border_color_var.get(), ""), font=(FONT_FAMILY, 8), fg=COLOR_TEXT_MUTED, bg=COLOR_CARD)
        self.lbl_color_hint.grid(row=1, column=2, sticky="w", padx=(6, 0))

        # Canlı Önizleme Kutusu
        card_preview = tk.LabelFrame(
            tab,
            text=" 👁️ Canlı Tablo Hücresi, Buton ve Menü Önizlemesi ",
            font=(FONT_FAMILY, 9, "bold"),
            bg=COLOR_CARD,
            padx=15,
            pady=10,
            relief="solid",
            bd=1
        )
        card_preview.pack(fill="both", expand=True)

        f_sample_row = tk.Frame(card_preview, bg="#F8FAFC", padx=16, pady=10)
        f_sample_row.pack(fill="x", pady=4)

        # 1. Örnek Tablo Hücresi
        f_col_cell = tk.Frame(f_sample_row, bg="#F8FAFC")
        f_col_cell.pack(side="left", padx=(10, 30))
        tk.Label(f_col_cell, text="Tablo Hücresi:", font=(FONT_FAMILY, 8, "bold"), bg="#F8FAFC", fg=COLOR_TEXT_MUTED).pack(anchor="w", pady=(0, 4))

        self.f_sample_cell = tk.Frame(
            f_col_cell,
            bg="#FFFFFF",
            relief="solid",
            bd=int(self.grid_border_width_var.get() or 1),
            highlightbackground=self.grid_border_color_var.get() or "#CBD5E1",
            highlightthickness=1,
            padx=16,
            pady=8
        )
        self.f_sample_cell.pack()

        self.lbl_sample_teacher = tk.Label(
            self.f_sample_cell,
            text="Ahmet YILMAZ",
            font=(self.font_family_var.get(), int(self.font_size_var.get() or 9), "bold"),
            bg="#FFFFFF",
            fg="#0F172A"
        )
        self.lbl_sample_teacher.pack()

        self.lbl_sample_branch = tk.Label(
            self.f_sample_cell,
            text="Matematik (1. Kat)",
            font=(self.font_family_var.get(), max(7, int(self.font_size_var.get() or 9) - 2)),
            bg="#FFFFFF",
            fg="#64748B"
        )
        self.lbl_sample_branch.pack(pady=(2, 0))

        # 2. Örnek Buton ve Menü
        f_col_ui = tk.Frame(f_sample_row, bg="#F8FAFC")
        f_col_ui.pack(side="left", padx=10)
        tk.Label(f_col_ui, text="Buton & Menü:", font=(FONT_FAMILY, 8, "bold"), bg="#F8FAFC", fg=COLOR_TEXT_MUTED).pack(anchor="w", pady=(0, 4))

        f_sample_btns = tk.Frame(f_col_ui, bg="#F8FAFC")
        f_sample_btns.pack(anchor="w")

        self.btn_sample_action = tk.Button(
            f_sample_btns,
            text="⚡ Otomatik Dağıt",
            bg=COLOR_PRIMARY,
            fg="#FFFFFF",
            font=(self.font_family_var.get(), int(self.ui_font_size_var.get() or 10), "bold"),
            relief="flat",
            padx=10,
            pady=4
        )
        self.btn_sample_action.pack(side="left", padx=(0, 8))

        self.lbl_sample_menu = tk.Label(
            f_sample_btns,
            text="📤 Nöbet Çıktıları ▾",
            bg="#FFFFFF",
            fg=COLOR_TEXT_MAIN,
            font=(self.font_family_var.get(), int(self.ui_font_size_var.get() or 10), "bold"),
            relief="solid",
            bd=1,
            padx=8,
            pady=4
        )
        self.lbl_sample_menu.pack(side="left")

        self._update_appearance_preview()

    def _update_appearance_preview(self):
        try:
            fam = self.font_family_var.get() or "Segoe UI"
            size_table = int(self.font_size_var.get() or 9)
            size_ui = int(self.ui_font_size_var.get() or 10)
            width = int(self.grid_border_width_var.get() or 1)
            color = self.grid_border_color_var.get() or "#CBD5E1"

            self.f_sample_cell.configure(
                bd=width,
                highlightbackground=color,
                highlightthickness=1
            )
            self.lbl_sample_teacher.configure(
                font=(fam, size_table, "bold")
            )
            self.lbl_sample_branch.configure(
                font=(fam, max(7, size_table - 2))
            )
            self.btn_sample_action.configure(
                font=(fam, size_ui, "bold")
            )
            self.lbl_sample_menu.configure(
                font=(fam, size_ui, "bold")
            )

            color_labels = {
                "#CBD5E1": "Yumuşak Açık Gri (Standart)",
                "#94A3B8": "Belirgin Orta Gri",
                "#64748B": "Koyu Grafit",
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

    def _build_tab_security(self):
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="🔒 Güvenlik & Ağ (LAN)")

        # 1. Yönetici Giriş Şifresi
        card_pwd = tk.LabelFrame(
            tab,
            text=" 🔐 Yönetici Giriş Şifresi ve Koruması ",
            font=(FONT_FAMILY, 9, "bold"),
            bg=COLOR_CARD,
            padx=15,
            pady=12,
            relief="solid",
            bd=1
        )
        card_pwd.pack(fill="x", pady=(0, 15))

        is_prot = self.db.is_password_protected()
        status_txt = "🟢 Şifre Koruması AKTİF (Kritik ekranlar şifreyle açılır)" if is_prot else "⚪ Şifre Koruması DEVRE DIŞI (Korumasız mod)"
        status_color = "#059669" if is_prot else "#64748B"

        self.lbl_pwd_status = tk.Label(
            card_pwd,
            text=status_txt,
            font=(FONT_FAMILY, 9, "bold"),
            fg=status_color,
            bg=COLOR_CARD
        )
        self.lbl_pwd_status.pack(anchor="w", pady=(0, 8))

        f_pwd = tk.Frame(card_pwd, bg=COLOR_CARD)
        f_pwd.pack(fill="x", pady=4)

        tk.Label(f_pwd, text="Yeni Şifre:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, width=15, anchor="w").grid(row=0, column=0, pady=4)
        self.ent_new_pwd = ttk.Entry(f_pwd, show="●", width=20)
        self.ent_new_pwd.grid(row=0, column=1, pady=4, padx=(5, 15))

        tk.Label(f_pwd, text="Şifre Tekrar:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, width=15, anchor="w").grid(row=1, column=0, pady=4)
        self.ent_new_pwd_rep = ttk.Entry(f_pwd, show="●", width=20)
        self.ent_new_pwd_rep.grid(row=1, column=1, pady=4, padx=(5, 15))

        f_pwd_btns = tk.Frame(card_pwd, bg=COLOR_CARD)
        f_pwd_btns.pack(fill="x", pady=(8, 0))

        ttk.Button(f_pwd_btns, text="💾 Şifreyi Kaydet / Değiştir", style="Primary.TButton", command=self._save_password).pack(side="left", padx=(0, 8))
        if is_prot:
            ttk.Button(f_pwd_btns, text="🔓 Şifreyi Kaldır", command=self._remove_password).pack(side="left")

        # 2. Yerel Ağ (LAN) Otomatik Paylaşım & Bağlantı Sihirbazı
        card_lan = tk.LabelFrame(
            tab,
            text=" 🌐 Yerel Ağ (LAN) Otomatik Paylaşım & Bağlantı Sihirbazı ",
            font=(FONT_FAMILY, 9, "bold"),
            bg=COLOR_CARD,
            padx=15,
            pady=12,
            relief="solid",
            bd=1
        )
        card_lan.pack(fill="x")

        # --- A. BU BİLGİSAYARI ANA SUNUCU (HOST) YAP ---
        f_host_box = tk.LabelFrame(
            card_lan,
            text=" 🖥️ 1. Bu Bilgisayarı Ana Sunucu Yap (Paylaşıma Aç) ",
            font=(FONT_FAMILY, 8, "bold"),
            bg="#F8FAFC",
            padx=12,
            pady=8,
            relief="solid",
            bd=1
        )
        f_host_box.pack(fill="x", pady=(0, 10))

        self.lbl_host_status = tk.Label(
            f_host_box,
            text="⚪ Paylaşım Kapalı (Yalnızca bu bilgisayarda çalışılıyor)",
            font=(FONT_FAMILY, 8, "bold"),
            fg="#64748B",
            bg="#F8FAFC"
        )
        self.lbl_host_status.pack(anchor="w", pady=(0, 3))

        self.lbl_host_details = tk.Label(
            f_host_box,
            text=f"Bilgisayar: {get_hostname()} | Yerel IP: {get_local_ip()}",
            font=(FONT_FAMILY, 8),
            fg=COLOR_TEXT_MUTED,
            bg="#F8FAFC"
        )
        self.lbl_host_details.pack(anchor="w", pady=(0, 6))

        f_host_btns = tk.Frame(f_host_box, bg="#F8FAFC")
        f_host_btns.pack(fill="x")

        self.btn_start_host = ttk.Button(
            f_host_btns,
            text="▶️ Ağ Paylaşımını Başlat (Ana Sunucu Yap)",
            style="Primary.TButton",
            command=self._start_host
        )
        self.btn_start_host.pack(side="left", padx=(0, 8))

        self.btn_stop_host = ttk.Button(
            f_host_btns,
            text="⏹️ Paylaşımı Durdur",
            command=self._stop_host,
            state="disabled"
        )
        self.btn_stop_host.pack(side="left")

        # --- B. AĞDAKİ ANA BİLGİSAYARA BAĞLAN (İSTEMCİ) ---
        f_client_box = tk.LabelFrame(
            card_lan,
            text=" 🔗 2. Ağdaki Ana Bilgisayara Bağlan (İstemci / Diğer Bilgisayarlar) ",
            font=(FONT_FAMILY, 8, "bold"),
            bg="#F8FAFC",
            padx=12,
            pady=8,
            relief="solid",
            bd=1
        )
        f_client_box.pack(fill="x", pady=(0, 10))

        tk.Label(
            f_client_box,
            text="Okul ağındaki aktif NöbetMatik sunucusunu tek tıkla arayıp eşitleyin:",
            font=(FONT_FAMILY, 8),
            fg=COLOR_TEXT_MUTED,
            bg="#F8FAFC"
        ).pack(anchor="w", pady=(0, 6))

        f_scan_bar = tk.Frame(f_client_box, bg="#F8FAFC")
        f_scan_bar.pack(fill="x", pady=(0, 6))

        self.btn_scan_hosts = ttk.Button(
            f_scan_bar,
            text="🔍 Ağdaki Okul Sunucusunu Otomatik Bul",
            command=self._scan_network_hosts
        )
        self.btn_scan_hosts.pack(side="left", padx=(0, 8))

        self.lbl_scan_status = tk.Label(
            f_scan_bar,
            text="",
            font=(FONT_FAMILY, 8, "italic"),
            bg="#F8FAFC",
            fg=COLOR_PRIMARY
        )
        self.lbl_scan_status.pack(side="left")

        # Bulunan sunucular konteyneri
        self.f_hosts_list = tk.Frame(f_client_box, bg="#F8FAFC")
        self.f_hosts_list.pack(fill="x")

        # --- C. AKTİF VERİTABANI VE GELİŞMİŞ AYARLAR ---
        f_cur_db = tk.Frame(card_lan, bg=COLOR_CARD)
        f_cur_db.pack(fill="x", pady=(4, 0))

        tk.Label(f_cur_db, text="Aktif Veritabanı Konumu:", font=(FONT_FAMILY, 8, "bold"), bg=COLOR_CARD).pack(anchor="w")
        self.lbl_cur_db = tk.Label(
            f_cur_db,
            text=str(self.db.db_path),
            font=(FONT_FAMILY, 8, "italic"),
            fg=COLOR_PRIMARY,
            bg=COLOR_CARD,
            wraplength=650,
            justify="left"
        )
        self.lbl_cur_db.pack(anchor="w", pady=(2, 6))

        f_lan_adv_btns = tk.Frame(card_lan, bg=COLOR_CARD)
        f_lan_adv_btns.pack(fill="x")

        ttk.Button(f_lan_adv_btns, text="🔄 Varsayılan Yerel Veritabanına Geri Dön", command=self._reset_to_default_db).pack(side="left", padx=(0, 8))
        ttk.Button(f_lan_adv_btns, text="📂 Manuel Dosya / Ağ Konumu Seç (.db)...", command=self._browse_lan_db).pack(side="left")

        self._update_host_ui()

    def _update_host_ui(self):
        if is_global_host_running():
            self.lbl_host_status.configure(
                text="🟢 AĞ PAYLAŞIMI AKTİF (Diğer bilgisayarlar anında bağlanabilir)",
                fg="#059669"
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
                fg="#64748B"
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
            f_empty = tk.Frame(self.f_hosts_list, bg="#FEF2F2", padx=10, pady=8, highlightbackground="#FCA5A5", highlightthickness=1)
            f_empty.pack(fill="x", pady=4)
            tk.Label(f_empty, text="⚠️ Yerel ağda açık bir NöbetMatik ana sunucusu bulunamadı.", font=(FONT_FAMILY, 8, "bold"), fg="#DC2626", bg="#FEF2F2").pack(anchor="w")
            tk.Label(f_empty, text="İpucu: Ana bilgisayarda 'Ağ Paylaşımını Başlat' butonuna basıldığından ve aynı ağda (Wi-Fi veya kablolu) olduğunuzdan emin olunuz.", font=(FONT_FAMILY, 8), fg="#7F1D1D", bg="#FEF2F2").pack(anchor="w")
            return

        tk.Label(self.f_hosts_list, text=f"🎉 Bulunan Okul Sunucuları ({len(hosts)}):", font=(FONT_FAMILY, 8, "bold"), fg="#059669", bg="#F8FAFC").pack(anchor="w", pady=(0, 4))
        for h in hosts:
            card_h = tk.Frame(self.f_hosts_list, bg="#ECFDF5", padx=10, pady=8, highlightbackground="#A7F3D0", highlightthickness=1)
            card_h.pack(fill="x", pady=2)

            f_text = tk.Frame(card_h, bg="#ECFDF5")
            f_text.pack(side="left", fill="x", expand=True)

            school = h.get("school_name", "Okul")
            hname = h.get("hostname", "")
            ip = h.get("ip", "")
            tk.Label(f_text, text=f"🏫 {school} ({hname} - {ip})", font=(FONT_FAMILY, 9, "bold"), fg="#065F46", bg="#ECFDF5").pack(anchor="w")
            share_info = h.get("share_path") or f"http://{ip}:{h.get('http_port', 52520)}"
            tk.Label(f_text, text=f"Ağ Adresi: {share_info}", font=(FONT_FAMILY, 8), fg="#047857", bg="#ECFDF5").pack(anchor="w")

            btn_conn = ttk.Button(card_h, text="⚡ Tek Tıkla Bağlan", style="Primary.TButton", command=lambda host=h: self._connect_to_host(host))
            btn_conn.pack(side="right", padx=6)

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
        self.lbl_pwd_status.configure(text="🟢 Şifre Koruması AKTİF (Kritik ekranlar şifreyle açılır)", fg="#059669")
        self.ent_new_pwd.delete(0, tk.END)
        self.ent_new_pwd_rep.delete(0, tk.END)

    def _remove_password(self):
        if messagebox.askyesno("Onay", "Yönetici şifresi kaldırılacak ve koruma devre dışı bırakılacaktır.\nOnaylıyor musunuz?", parent=self):
            self.db.set_admin_password("")
            messagebox.showinfo("Başarılı", "Yönetici şifresi kaldırıldı.", parent=self)
            self.lbl_pwd_status.configure(text="⚪ Şifre Koruması DEVRE DIŞI (Korumasız mod)", fg="#64748B")

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
            try:
                self.school.daily_periods = int(self.lesson_count_var.get().strip())
            except ValueError:
                self.school.daily_periods = 7
            self.db.save_school_info(self.school)

            # 2. Ayarlar (Key-Value)
            self.db.set_setting("vice_principal_name", self.vice_principal_var.get().strip())
            self.db.set_setting("daily_lesson_count", self.lesson_count_var.get().strip())
            self.db.set_setting("first_lesson_start", self.lesson_start_var.get().strip())
            self.db.set_setting("last_lesson_end", self.lesson_end_var.get().strip())
            self.db.set_setting("duty_start_offset", self.duty_start_offset_var.get().strip())
            self.db.set_setting("duty_end_offset", self.duty_end_offset_var.get().strip())

            self.db.set_setting("last_shift_mode", self.shift_mode_var.get().strip())
            self.db.set_setting("last_shift_preserve", "1" if self.shift_preserve_var.get() else "0")

            self.db.set_setting("branch_priority_enabled", "1" if self.branch_priority_var.get() else "0")
            self.db.set_setting("workload_sharing_enabled", "1" if self.workload_sharing_var.get() else "0")
            self.db.set_setting("ek_ders_alert_enabled", "1" if self.ek_ders_alert_var.get() else "0")
            self.db.set_setting("default_duty_per_lesson", self.default_duty_per_lesson_var.get().strip())

            # 3. Görünüm, Yazı Tipi ve Tablo Çizgileri
            self.db.set_setting("font_family", self.font_family_var.get().strip())
            self.db.set_setting("font_size", self.font_size_var.get().strip())
            self.db.set_setting("ui_font_size", self.ui_font_size_var.get().strip())
            self.db.set_setting("grid_border_width", self.grid_border_width_var.get().strip())
            self.db.set_setting("grid_border_color", self.grid_border_color_var.get().strip())

            # 4. Yazılım Güncelleme Ayarları
            self.db.set_setting("github_repo", self.github_repo_var.get().strip())
            self.db.set_setting("auto_check_updates", "1" if self.auto_check_updates_var.get() else "0")

            from ui.theme import load_theme_settings, setup_styles
            load_theme_settings(self.db)
            setup_styles(self.master, self.db)

            messagebox.showinfo("Başarılı", "Tüm sistem, görünüm ve yönetim ayarları kaydedildi!", parent=self)
            if self.on_saved:
                self.on_saved()
            self.destroy()

        except Exception as e:
            logger.error(f"Ayarlar kaydedilirken hata: {e}")
            messagebox.showerror("Hata", f"Ayarlar kaydedilemedi:\n{e}", parent=self)
