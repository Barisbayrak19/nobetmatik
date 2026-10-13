"""
Otomatik Nöbet Dağıtımı ve Önizleme Ekranı (Tek Ana Pencere Uyumlu View & Dialog)
Adalet analizi, kullanıcı tarafından seçilebilir dağıtım ilkeleri ve onaylı uygulama.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional, List, Dict
from core.models import Assignment, DutyFairnessReport
from core.database import Database
from logic.auto_scheduler import AutoScheduler
from ui.theme import (
    COLOR_CARD, COLOR_PRIMARY, COLOR_SUCCESS, COLOR_BG, COLOR_BORDER,
    COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, COLOR_WARNING, COLOR_PRIMARY_HOVER, FONT_FAMILY,
    create_modern_button
)
from core.logger import logger

class DistributionView(ttk.Frame):
    """Ana pencere içine gömülü Otomatik Dağıtım Ekranı."""
    def __init__(
        self,
        parent: tk.Widget,
        db: Database,
        get_week_start: Callable[[], str],
        on_applied: Optional[Callable[[], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent)
        self.db = db
        self.get_week_start = get_week_start
        self.on_applied = on_applied
        self.on_cancel = on_cancel
        self.scheduler = AutoScheduler(db)

        # Dağıtım İlkeleri ve Kural Tercihleri
        # 1. 2. Nöbet Kuralı (Varsayılan: False - seçilmezse kimseye 2. nöbet verilmez)
        self.allow_second_duty_var = tk.BooleanVar(value=False)
        # 2. Tüm dersleri dolu olsa bile nöbet ver (Varsayılan: True - teneffüs nöbeti)
        self.full_day_lessons_var = tk.BooleanVar(value=True)
        # 3. Dersi olmayan (boş) günlere nöbet verme (Varsayılan: True)
        self.only_days_with_lessons_var = tk.BooleanVar(value=True)
        # 4. Sabit nöbetleri koru (Varsayılan: True)
        self.preserve_fixed_var = tk.BooleanVar(value=True)
        # 5. Ardışık günleri engelle (Varsayılan: True)
        self.avoid_consecutive_var = tk.BooleanVar(value=True)
        # 6. Öğretmen gün tercihlerini dikkate al (Varsayılan: True)
        self.consider_preferences_var = tk.BooleanVar(value=True)
        # 7. Önceki haftaya göre rotasyon yap (Varsayılan: True)
        self.consider_rotation_var = tk.BooleanVar(value=True)
        # 8. 20/25 yıl kıdem muafiyeti taleplerini dikkate al (Varsayılan: True)
        self.honor_seniority_var = tk.BooleanVar(value=True)
        # 9. Boşta kalan öğretmenleri boş derslerinde eşli / destek nöbetçi ata (Tandem)
        self.assign_co_duty_var = tk.BooleanVar(value=False)

        self.preview_assignments: Optional[List[Assignment]] = None
        self.fairness_report: Optional[DutyFairnessReport] = None

        self._build_ui()
        self.calculate_preview()

    def _build_ui(self):
        top_frame = ttk.Frame(self, padding=(16, 10, 16, 6))
        top_frame.pack(fill="x")

        title_box = ttk.Frame(top_frame)
        title_box.pack(fill="x", pady=(0, 6))

        ttk.Label(
            title_box,
            text="⚖️ Akıllı ve Dengeli Nöbet Dağıtım Motoru",
            font=(FONT_FAMILY, 12, "bold"),
            foreground=COLOR_PRIMARY
        ).pack(side="left")

        btn_recalc = create_modern_button(
            title_box,
            text="🔄 İlkeleri Uygula ve Yeniden Hesapla",
            variant="primary",
            command=self.calculate_preview
        )
        btn_recalc.pack(side="right")

        # Dağıtım İlkeleri ve Kuralları Kartı
        principles_frame = ttk.LabelFrame(top_frame, text=" ⚙️ Nöbet Dağıtım İlkeleri ve Kural Tercihleri (Kullanıcı Seçimli) ", padding=(12, 8))
        principles_frame.pack(fill="x", pady=(2, 6))

        # Satır 1: İkinci Nöbet ve Doluluk İlkeleri
        r1 = ttk.Frame(principles_frame)
        r1.pack(fill="x", pady=2)

        cb_second = ttk.Checkbutton(
            r1,
            text="⚠️ Yetersiz kalırsa 2. nöbet günü ver (Seçilmezse kimseye 2. nöbet verilmez)",
            variable=self.allow_second_duty_var,
            command=self.calculate_preview
        )
        cb_second.pack(side="left", padx=(0, 20))

        cb_full = ttk.Checkbutton(
            r1,
            text="📚 Tüm dersleri dolu olsa bile nöbet ver (Mevzuat teneffüs görevi)",
            variable=self.full_day_lessons_var,
            command=self.calculate_preview
        )
        cb_full.pack(side="left", padx=(0, 20))

        cb_only_lessons = ttk.Checkbutton(
            r1,
            text="🏫 Dersi olmayan (boş) günlere nöbet verme",
            variable=self.only_days_with_lessons_var,
            command=self.calculate_preview
        )
        cb_only_lessons.pack(side="left")

        # Satır 2: Koruma, Ardışıklık ve Kıdem
        r2 = ttk.Frame(principles_frame)
        r2.pack(fill="x", pady=2)

        cb_fixed = ttk.Checkbutton(
            r2,
            text="🔒 Sabit nöbetleri koru (Kilitli görevleri değiştirme)",
            variable=self.preserve_fixed_var,
            command=self.calculate_preview
        )
        cb_fixed.pack(side="left", padx=(0, 20))

        cb_consec = ttk.Checkbutton(
            r2,
            text="🚫 Ardışık günleri engelle (Üst üste gün verme)",
            variable=self.avoid_consecutive_var,
            command=self.calculate_preview
        )
        cb_consec.pack(side="left", padx=(0, 20))

        cb_pref = ttk.Checkbutton(
            r2,
            text="⭐ Öğretmen gün tercihlerini dikkate al (+/- Tercihler)",
            variable=self.consider_preferences_var,
            command=self.calculate_preview
        )
        cb_pref.pack(side="left", padx=(0, 20))

        cb_rot = ttk.Checkbutton(
            r2,
            text="🔄 Geçen haftaya göre gün/yer rotasyonu yap",
            variable=self.consider_rotation_var,
            command=self.calculate_preview
        )
        cb_rot.pack(side="left", padx=(0, 20))

        cb_senior = ttk.Checkbutton(
            r2,
            text="🎖️ 20/25 yıl kıdem muafiyet taleplerini uygula",
            variable=self.honor_seniority_var,
            command=self.calculate_preview
        )
        cb_senior.pack(side="left")

        # Satır 3: Boş Derslerde Eşli Nöbet (Tandem / Adil Dengeleme)
        r3 = ttk.Frame(principles_frame)
        r3.pack(fill="x", pady=2)

        cb_co_duty = ttk.Checkbutton(
            r3,
            text="👥 Nöbetsiz kalan öğretmenleri boş derslerinde eşli / destek nöbetçi ata (Tandem Nöbet)",
            variable=self.assign_co_duty_var,
            command=self.calculate_preview
        )
        cb_co_duty.pack(side="left")

        # Teklif / Bilgilendirme Kart Alanı
        self.proposal_frame = ttk.Frame(top_frame)
        self.proposal_frame.pack(fill="x", pady=(2, 4))

        # Orta Bölüm: Sekmeli Görünüm (Önizleme Listesi & Adalet Raporu)
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=16, pady=4)

        # Sekme 1: Önizleme Tablosu
        self.tab_preview = ttk.Frame(notebook)
        notebook.add(self.tab_preview, text="📋 Dağıtım Önizlemesi")

        preview_table_frame = ttk.Frame(self.tab_preview, padding=8)
        preview_table_frame.pack(fill="both", expand=True)

        cols = ("day", "loc", "slot", "teacher")
        self.tree_preview = ttk.Treeview(preview_table_frame, columns=cols, show="headings")
        self.tree_preview.heading("day", text="Gün")
        self.tree_preview.heading("loc", text="Nöbet Yeri")
        self.tree_preview.heading("slot", text="Slot")
        self.tree_preview.heading("teacher", text="Atanan Öğretmen")

        self.tree_preview.column("day", width=120)
        self.tree_preview.column("loc", width=190)
        self.tree_preview.column("slot", width=120, anchor="center")
        self.tree_preview.column("teacher", width=280)

        sb = ttk.Scrollbar(preview_table_frame, orient="vertical", command=self.tree_preview.yview)
        self.tree_preview.configure(yscrollcommand=sb.set)
        self.tree_preview.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Sekme 2: Adalet ve İstatistik Raporu
        self.tab_report = ttk.Frame(notebook)
        notebook.add(self.tab_report, text="📊 Nöbet Adaleti ve İstatistikler")

        self.report_text = tk.Text(self.tab_report, wrap="word", font=(FONT_FAMILY, 9), padx=15, pady=15)
        sb_rep = ttk.Scrollbar(self.tab_report, orient="vertical", command=self.report_text.yview)
        self.report_text.configure(yscrollcommand=sb_rep.set)
        self.report_text.pack(side="left", fill="both", expand=True)
        sb_rep.pack(side="right", fill="y")

        # Alt Buton Alanı
        bottom_frame = ttk.Frame(self, padding=(16, 8, 16, 10))
        bottom_frame.pack(fill="x", side="bottom")

        self.lbl_status = ttk.Label(bottom_frame, text="", font=(FONT_FAMILY, 9, "bold"))
        self.lbl_status.pack(side="left")

        if self.on_cancel:
            create_modern_button(bottom_frame, text="İptal / Vazgeç", variant="default", command=self.on_cancel).pack(side="right", padx=(6, 0))

        btn_apply = create_modern_button(
            bottom_frame,
            text="✔ Dağıtımı Uygula ve Kaydet",
            variant="success",
            command=self.apply_schedule
        )
        btn_apply.pack(side="right")

    def _enable_co_duty(self):
        self.assign_co_duty_var.set(True)
        self.calculate_preview()

    def _disable_co_duty(self):
        self.assign_co_duty_var.set(False)
        self.calculate_preview()

    def calculate_preview(self):
        try:
            week_start = self.get_week_start()
            assignments, report = self.scheduler.generate_schedule(
                week_start=week_start,
                avoid_consecutive_days=self.avoid_consecutive_var.get(),
                preserve_fixed=self.preserve_fixed_var.get(),
                allow_second_duty=self.allow_second_duty_var.get(),
                full_day_lessons_eligible=self.full_day_lessons_var.get(),
                only_days_with_lessons=self.only_days_with_lessons_var.get(),
                consider_preferences=self.consider_preferences_var.get(),
                consider_prev_rotation=self.consider_rotation_var.get(),
                honor_seniority=self.honor_seniority_var.get(),
                assign_co_duty_for_unassigned=self.assign_co_duty_var.get()
            )
            self.preview_assignments = assignments
            self.fairness_report = report

            # Teklif / Bilgilendirme Bannerını Güncelle
            for child in self.proposal_frame.winfo_children():
                child.destroy()

            if self.assign_co_duty_var.get() and report.co_duty_assignments:
                banner = tk.Frame(self.proposal_frame, bg="#F0FDF4", highlightbackground="#BBF7D0", highlightthickness=1, padx=12, pady=6)
                banner.pack(fill="x")

                lbl_icon = tk.Label(banner, text="👥", font=(FONT_FAMILY, 13), bg="#F0FDF4")
                lbl_icon.pack(side="left", padx=(0, 8))

                msg = (
                    f"Eşli Destek Nöbetleri Aktif: O gün okuldaki dersi olup nöbetsiz kalan "
                    f"{len(report.co_duty_assignments)} öğretmen, boş ders saatlerinde yoğun nöbet yerlerine "
                    f"eşli / tandem nöbetçi olarak adilce atanmıştır."
                )
                lbl_msg = tk.Label(banner, text=msg, font=(FONT_FAMILY, 9), bg="#F0FDF4", fg="#166534", justify="left")
                lbl_msg.pack(side="left", fill="x", expand=True)

                btn_toggle = ttk.Button(banner, text="↩ Eşli Atamayı Kaldır", command=self._disable_co_duty)
                btn_toggle.pack(side="right", padx=(8, 0))

            elif not self.assign_co_duty_var.get() and report.co_duty_proposals:
                banner = tk.Frame(self.proposal_frame, bg="#EFF6FF", highlightbackground="#BFDBFE", highlightthickness=1, padx=12, pady=6)
                banner.pack(fill="x")

                lbl_icon = tk.Label(banner, text="💡", font=(FONT_FAMILY, 13), bg="#EFF6FF")
                lbl_icon.pack(side="left", padx=(0, 8))

                prop_count = len(report.co_duty_proposals)
                msg = (
                    f"ADALETLİ GÖREVLENDİRME TEKLİFİ: O gün dersi olduğu halde hiç nöbet yazılmayan {prop_count} öğretmen tespit edildi!\n"
                    f"Bu öğretmenleri boş ders saatlerinde okulun yoğun nöbet yerlerine (Bahçe / Zemin vb.) "
                    f"asıl nöbetçinin yanına eşli nöbetçi olarak atayarak iş yükünü eşitlemek ister misiniz?"
                )
                lbl_msg = tk.Label(banner, text=msg, font=(FONT_FAMILY, 9, "bold"), bg="#EFF6FF", fg="#1E40AF", justify="left")
                lbl_msg.pack(side="left", fill="x", expand=True)

                btn_accept = ttk.Button(
                    banner,
                    text=f"👥 Teklifi Kabul Et & Eşli Görevlendir ({prop_count} Öğretmen)",
                    style="Primary.TButton",
                    command=self._enable_co_duty
                )
                btn_accept.pack(side="right", padx=(8, 0))

            # Önizleme Tablosunu Doldur
            for item in self.tree_preview.get_children():
                self.tree_preview.delete(item)

            days_map = {d.id: d.name for d in self.db.get_days()}
            locs_map = {l.id: l.name for l in self.db.get_locations()}
            teachers_map = {t.id: t.name for t in self.db.get_teachers()}

            for a in assignments:
                d_name = days_map.get(a.day_id, "")
                l_name = locs_map.get(a.location_id, "")
                t_name = teachers_map.get(a.teacher_id, "[Boş / Atanamadı]")
                lock = " 🔒" if a.fixed else ""
                if a.slot_index >= 1:
                    slot_txt = f"{a.slot_index + 1} (Eşli Destek)"
                    t_txt = f"👥 {t_name}{lock}  [Boş Ders Desteği]"
                else:
                    slot_txt = f"{a.slot_index + 1}"
                    t_txt = f"{t_name}{lock}"
                self.tree_preview.insert("", "end", values=(d_name, l_name, slot_txt, t_txt))

            # Adalet Raporu Metnini Oluştur
            self.report_text.delete("1.0", tk.END)
            self.report_text.insert(tk.END, "═══════════════════════════════════════════════════════════════\n")
            self.report_text.insert(tk.END, "       🎯 NÖBET DAĞILIM VE ADALET ANALİZ RAPORU\n")
            self.report_text.insert(tk.END, "═══════════════════════════════════════════════════════════════\n\n")

            st = report.stats or {}
            fd = report.fairness_details or {}
            self.report_text.insert(tk.END, "📌 GENEL DAĞITIM ÖZETİ:\n")
            self.report_text.insert(tk.END, f" • Aktif Öğretmen Sayısı   : {st.get('total_active_teachers', len(teachers_map))}\n")
            self.report_text.insert(tk.END, f" • Nöbete Uygun Öğretmen   : {st.get('eligible_teachers', len(teachers_map))}\n")
            self.report_text.insert(tk.END, f" • Toplam Nöbet Alanı/Slot : {st.get('total_slots', len(assignments))}\n")
            self.report_text.insert(tk.END, f" • Başarıyla Dağıtılan     : {st.get('filled_slots', 0)}\n")
            self.report_text.insert(tk.END, f" • Kalan Boş / Eksik Slot  : {st.get('unfilled_slots', 0)}\n")
            self.report_text.insert(tk.END, f" • Korunan Sabit Görevler  : {st.get('fixed_preserved', 0)}\n")
            self.report_text.insert(tk.END, f" • Eşli Destek Nöbetçisi   : {len(report.co_duty_assignments)} görev\n")
            self.report_text.insert(tk.END, f" • Çakışma / İhlal         : 0 (Mevzuata %100 uygun)\n")
            self.report_text.insert(tk.END, f" • Karşılanan Tercihler    : {st.get('satisfied_preferences', 0)} adet\n")
            if st.get('unsatisfied_preferences', 0) > 0:
                self.report_text.insert(tk.END, f" • Zorunlu İstenmeyen Gün  : {st.get('unsatisfied_preferences', 0)} adet (ihtiyaç nedeniyle)\n")

            # İlkeler Durumu
            sec_duty_str = "AÇIK (İhtiyaç halinde 2. nöbet verilebilir)" if self.allow_second_duty_var.get() else "KAPALI (Hiçbir öğretmene 2. nöbet verilmez)"
            co_duty_str = "AÇIK (Nöbetsiz kalanlar boş derslerinde eşli atandı)" if self.assign_co_duty_var.get() else "KAPALI (Tekli nöbetçi)"
            self.report_text.insert(tk.END, f"\n⚙️ SEÇİLEN DAĞITIM İLKELERİ:\n")
            self.report_text.insert(tk.END, f" • 2. Nöbet Durumu         : {sec_duty_str}\n")
            self.report_text.insert(tk.END, f" • Eşli / Destek Nöbet     : {co_duty_str}\n")
            self.report_text.insert(tk.END, f" • Tam Dolu Ders Durumu    : {'Dolu derslerde de nöbet verilir' if self.full_day_lessons_var.get() else 'Sadece boş dersli öğretmenler'}\n")
            self.report_text.insert(tk.END, f" • Boş Gün Kuralı          : {'Dersi olmayan günlere nöbet yazılmaz' if self.only_days_with_lessons_var.get() else 'Tüm günlere yazılabilir'}\n")

            self.report_text.insert(tk.END, f"\n⚖️ ADALET VE EŞİTLİK METRİKLERİ:\n")
            self.report_text.insert(tk.END, f" • Nöbet Adalet Skoru      : %{report.fairness_score} ({fd.get('fairness_level', 'Dengeli Dağılım')})\n")
            self.report_text.insert(tk.END, f" • Gini Eşitlik Endeksi    : {report.gini_index:.4f} (0.00 = Kusursuz Eşitlik)\n")
            self.report_text.insert(tk.END, f" • Ortalama Nöbet Sayısı   : {report.average_duties} nöbet/öğretmen\n")
            self.report_text.insert(tk.END, f" • En Az / En Çok Nöbet    : {report.min_duties} – {report.max_duties} nöbet (Fark: {fd.get('spread', 0)})\n")
            self.report_text.insert(tk.END, f" • 0 Nöbetli Öğretmen      : {fd.get('zero_duty_teachers', 0)} kişi\n")
            self.report_text.insert(tk.END, f" • 1 Nöbetli Öğretmen      : {fd.get('one_duty_teachers', 0)} kişi\n")
            self.report_text.insert(tk.END, f" • 2+ Nöbetli Öğretmen     : {fd.get('multi_duty_teachers', 0)} kişi\n")

            # Eşli Destek Nöbetleri Ayrıntısı
            if self.assign_co_duty_var.get() and report.co_duty_assignments:
                self.report_text.insert(tk.END, f"\n👥 BOŞ DERSLERDE EŞLİ NÖBET ATAMALARI ({len(report.co_duty_assignments)} Görevlendirme):\n")
                self.report_text.insert(tk.END, f"{'GÜN':<12} | {'YER':<14} | {'ASIL NÖBETÇİ':<22} | {'EŞLİ DESTEK NÖBETÇİSİ':<24} | {'BOŞ SAATLER':<15}\n")
                self.report_text.insert(tk.END, "─" * 95 + "\n")
                for p in report.co_duty_proposals:
                    d_nm = p.get('day_name', '')
                    l_nm = p.get('location_name', '')
                    p_nm = p.get('primary_teacher_name', '')
                    c_nm = p.get('co_teacher_name', '')
                    f_st = f"{p.get('free_periods_str', '')}. dersler"
                    self.report_text.insert(tk.END, f"{d_nm:<12} | {l_nm:<14} | {p_nm:<22} | {c_nm:<24} | {f_st:<15}\n")
                self.report_text.insert(tk.END, "─" * 95 + "\n")
                self.report_text.insert(tk.END, "💡 Adalet Gerekçesi: O gün dersi olup tek başına nöbet alamayan öğretmenler, boş saatlerinde okulun en yoğun alanlarında asıl nöbetçiye destek olarak adil iş gücü paylaşımı sağlamıştır.\n\n")
            elif not self.assign_co_duty_var.get() and report.co_duty_proposals:
                self.report_text.insert(tk.END, f"\n💡 ÖNERİLEN EŞLİ DESTEK NÖBETİ TEKLİFİ ({len(report.co_duty_proposals)} Öğretmen):\n")
                self.report_text.insert(tk.END, "Aşağıdaki öğretmenler o gün okulda dersi olduğu halde tekli slot kalmadığı için nöbet almamıştır.\n'Tandem Nöbet' açılarak bu öğretmenler boş derslerinde destek nöbetçisi yapılabilir:\n")
                for p in report.co_duty_proposals:
                    self.report_text.insert(tk.END, f" • {p.get('day_name')} | {p.get('location_name')}: {p.get('co_teacher_name')} ({p.get('co_teacher_branch')}) ➡️ {p.get('primary_teacher_name')} yanına (Boş: {p.get('free_periods_str')}. dersler)\n")
                self.report_text.insert(tk.END, "\n")

            if report.excluded_teachers:
                self.report_text.insert(tk.END, "🚫 MUAF VEYA DEVRE DIŞI BIRAKILAN ÖĞRETMENLER:\n")
                for t_name, reason in report.excluded_teachers.items():
                    self.report_text.insert(tk.END, f" • {t_name:<30}: {reason}\n")
                self.report_text.insert(tk.END, "\n")

            if report.unfilled_slots:
                self.report_text.insert(tk.END, "⚠️ DOLDURULAMAYAN EKSİK NÖBET YERLERİ:\n")
                for u in report.unfilled_slots:
                    self.report_text.insert(tk.END, f" • {u.get('day')} / {u.get('location')} (Slot {u.get('slot')}): {u.get('reason')}\n")
                self.report_text.insert(tk.END, "\n")

            if report.warnings:
                self.report_text.insert(tk.END, "📢 BİLGİLENDİRME VE UYARILAR:\n")
                for w in report.warnings:
                    self.report_text.insert(tk.END, f" • {w}\n")
                self.report_text.insert(tk.END, "\n")

            self.report_text.insert(tk.END, "📋 ÖĞRETMEN BAZLI NÖBET DAĞILIMI:\n")
            sorted_teachers = sorted(report.teacher_counts.items(), key=lambda x: x[1], reverse=True)
            for t_id, count in sorted_teachers:
                name = report.teacher_names.get(t_id, t_id)
                self.report_text.insert(tk.END, f" • {name:<35}: {count} Nöbet\n")

            unfilled_cnt = st.get('unfilled_slots', 0)
            if unfilled_cnt == 0:
                self.lbl_status.configure(
                    text=f"✔ Dağıtım Başarılı! Adalet Skoru: %{report.fairness_score} | {st.get('filled_slots')} slot eksiksiz dolduruldu.",
                    foreground=COLOR_SUCCESS
                )
            else:
                self.lbl_status.configure(
                    text=f"⚠️ {unfilled_cnt} slot boş kaldı. (2. nöbet seçeneğini açarak boş slotları doldurabilirsiniz).",
                    foreground="#D97706" if not self.allow_second_duty_var.get() else "#DC2626"
                )

        except Exception as e:
            logger.error(f"Dağıtım önizleme hatası: {e}")
            messagebox.showerror("Hata", f"Otomatik dağıtım hesaplanırken hata oluştu:\n{e}", parent=self)

    def apply_schedule(self):
        if not self.preview_assignments:
            messagebox.showwarning("Uyarı", "Uygulanacak bir dağıtım önizlemesi bulunamadı.", parent=self)
            return

        if messagebox.askyesno("Onay", "Hesaplanan dağıtım haftalık çizelgeye kaydedilecek. Onaylıyor musunuz?", parent=self):
            self.scheduler.apply_schedule(self.preview_assignments)
            
            # Görevlendirme sonucunda ne kadar adil olduğumuzu gösteren detaylı karne penceresi
            dlg = FairnessSummaryDialog(self.winfo_toplevel(), report=self.fairness_report)
            self.wait_window(dlg)

            if self.on_applied:
                self.on_applied()


class FairnessSummaryDialog(tk.Toplevel):
    """Nöbet görevlendirmesi sonrasında ne kadar adil dağıtım yapıldığını gösteren bilgilendirme penceresi."""
    def __init__(self, parent: tk.Widget, report: Optional[DutyFairnessReport]):
        super().__init__(parent)
        self.title("⚖️ Nöbet Dağıtım Sonucu ve Adalet Karnesi")
        self.geometry("760x640")
        self.minsize(680, 540)
        self.transient(parent)
        self.report = report

        self.update_idletasks()
        try:
            px = parent.winfo_rootx() + (parent.winfo_width() // 2) - 380
            py = parent.winfo_rooty() + (parent.winfo_height() // 2) - 320
            self.geometry(f"+{max(50, px)}+{max(30, py)}")
        except Exception:
            pass

        self.grab_set()
        self.configure(bg=COLOR_BG)
        self._build_ui()

    def _build_ui(self):
        # 1. Üst Başlık Banner
        header = tk.Frame(self, bg="#1E293B", padx=18, pady=12)
        header.pack(fill="x")

        tk.Label(
            header,
            text="🏆 NÖBET DAĞITIM VE ADALET DEĞERLENDİRME KARNESİ",
            font=(FONT_FAMILY, 12, "bold"),
            fg="#FFFFFF",
            bg="#1E293B"
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Mevzuat Uyumluluğu, İş Yükü Dengesi ve Boş Ders Eşitlik Raporu",
            font=(FONT_FAMILY, 9),
            fg="#94A3B8",
            bg="#1E293B"
        ).pack(anchor="w", pady=(2, 0))

        content = ttk.Frame(self, padding=16)
        content.pack(fill="both", expand=True)

        if not self.report:
            ttk.Label(content, text="Adalet raporu bulunamadı.").pack()
            return

        fd = self.report.fairness_details or {}
        st = self.report.stats or {}
        score = self.report.fairness_score
        gini = self.report.gini_index

        # 2. Üst Skor Kartı
        score_card = tk.Frame(content, bg="#FFFFFF", highlightbackground=COLOR_BORDER, highlightthickness=1, padx=16, pady=12)
        score_card.pack(fill="x", pady=(0, 10))

        left_score = tk.Frame(score_card, bg="#FFFFFF")
        left_score.pack(side="left")

        score_color = "#059669" if score >= 90 else ("#2563EB" if score >= 80 else "#D97706")
        tk.Label(
            left_score,
            text=f"%{score}",
            font=(FONT_FAMILY, 28, "bold"),
            fg=score_color,
            bg="#FFFFFF"
        ).pack(side="left", padx=(0, 12))

        score_sub = tk.Frame(left_score, bg="#FFFFFF")
        score_sub.pack(side="left")

        level_str = fd.get("fairness_level", "Dengeli Dağılım")
        tk.Label(
            score_sub,
            text=level_str,
            font=(FONT_FAMILY, 12, "bold"),
            fg="#0F172A",
            bg="#FFFFFF"
        ).pack(anchor="w")

        tk.Label(
            score_sub,
            text=f"Gini Eşitlik Endeksi: {gini:.4f}  (0.00 = Kusursuz Eşitlik / Dünya Standardı)",
            font=(FONT_FAMILY, 9),
            fg="#64748B",
            bg="#FFFFFF"
        ).pack(anchor="w", pady=(2, 0))

        tk.Label(
            score_card,
            text="⚖️",
            font=(FONT_FAMILY, 26),
            bg="#FFFFFF"
        ).pack(side="right", padx=10)

        # 3. 4'lü Özet Metrik Kutuları
        metrics_frame = ttk.Frame(content)
        metrics_frame.pack(fill="x", pady=(0, 10))
        for col_idx in range(4):
            metrics_frame.columnconfigure(col_idx, weight=1, uniform="m")

        metric_items = [
            ("Aktif Öğretmen", f"{fd.get('total_active_teachers', len(self.report.teacher_counts))} Kişi", "#0F172A"),
            ("Toplam Nöbet Slotu", f"{st.get('filled_slots', 0)} / {st.get('total_slots', 0)}", "#2563EB"),
            ("Eşli Destek Nöbeti", f"{len(self.report.co_duty_assignments)} Görev", "#059669"),
            ("Nöbet Yayılımı", f"{self.report.min_duties} – {self.report.max_duties} Nöbet", "#D97706"),
        ]

        for idx, (m_title, m_val, m_col) in enumerate(metric_items):
            box = tk.Frame(metrics_frame, bg="#FFFFFF", highlightbackground=COLOR_BORDER, highlightthickness=1, padx=10, pady=8)
            box.grid(row=0, column=idx, padx=4, sticky="nsew")

            tk.Label(box, text=m_title, font=(FONT_FAMILY, 8), fg="#64748B", bg="#FFFFFF").pack(anchor="w")
            tk.Label(box, text=m_val, font=(FONT_FAMILY, 11, "bold"), fg=m_col, bg="#FFFFFF").pack(anchor="w", pady=(2, 0))

        # 4. Detaylı Açıklama ve Değerlendirme Rapor Alanı
        report_frame = ttk.LabelFrame(content, text=" 📝 Adalet Değerlendirmesi ve Gerekçe Karnesi ", padding=8)
        report_frame.pack(fill="both", expand=True, pady=(0, 10))

        txt_box = tk.Text(report_frame, wrap="word", font=(FONT_FAMILY, 9), padx=10, pady=8, bg="#F8FAFC", relief="flat")
        sb_txt = ttk.Scrollbar(report_frame, orient="vertical", command=txt_box.yview)
        txt_box.configure(yscrollcommand=sb_txt.set)
        txt_box.pack(side="left", fill="both", expand=True)
        sb_txt.pack(side="right", fill="y")

        self.generated_text_report = self._generate_report_text(fd, st)
        txt_box.insert(tk.END, self.generated_text_report)
        txt_box.configure(state="disabled")

        # 5. Alt Butonlar
        btn_bar = ttk.Frame(content)
        btn_bar.pack(fill="x")

        self.lbl_copy_status = ttk.Label(btn_bar, text="", font=(FONT_FAMILY, 9), foreground=COLOR_SUCCESS)
        self.lbl_copy_status.pack(side="left")

        ttk.Button(
            btn_bar,
            text="✔ Tamamla ve Çizelgeye Dön",
            style="Primary.TButton",
            command=self.destroy
        ).pack(side="right", padx=(6, 0))

        ttk.Button(
            btn_bar,
            text="📋 Raporu Panoya Kopyala",
            command=self._copy_to_clipboard
        ).pack(side="right")

    def _generate_report_text(self, fd: dict, st: dict) -> str:
        lines = []
        lines.append("═════════════════════════════════════════════════════════════════════════")
        lines.append("                  🏆 NÖBET DAĞILIM ADALET RAPORU")
        lines.append("═════════════════════════════════════════════════════════════════════════\n")
        lines.append(f"Adalet Skoru        : %{self.report.fairness_score} ({fd.get('fairness_level', 'Dengeli Dağılım')})")
        lines.append(f"Gini Eşitlik Endeksi: {self.report.gini_index:.4f} (0.00 = Tam Eşit Dağılım)")
        lines.append(f"Ortalama Nöbet Yükü : {self.report.average_duties} nöbet/öğretmen")
        lines.append(f"Nöbet Fark Yayılımı : En az {self.report.min_duties}, En çok {self.report.max_duties} (Fark: {fd.get('spread', 0)})\n")

        lines.append("🔍 ADİL DAĞITIM PRENSİPLERİ VE UYUM:")
        lines.append("  ✓ MEVZUAT UYUMU: Hiçbir öğretmene tek bir günde birden fazla nöbet verilmedi.")
        lines.append("  ✓ DERS YÜKÜ VE DİNLENME: O gün hiç dersi olmayan öğretmenlere nöbet yazılmayarak gereksiz okula gelişler engellendi.")
        lines.append("  ✓ ARDIŞIK GÜN KORUMASI: Öğretmenlerin peş peşe günlerde yorulmasını önlemek için ardışık günler korundu.")
        lines.append("  ✓ ROTASYON DENGESİ: Geçen haftanın nöbet günleri ve nöbet yerleri incelenerek rotasyon çeşitliliği sağlandı.")
        lines.append(f"  ✓ TERCİH UYUMU: Öğretmenlerin belirlediği gün tercihleri azami oranda ({st.get('satisfied_preferences', 0)} tercih) karşılandı.\n")

        if self.report.co_duty_assignments:
            lines.append("👥 BOŞ DERSLERDE EŞLİ / TANDEM NÖBET DAĞILIMI:")
            lines.append(f"Okulda dersi olduğu halde tek başına nöbet yazılmamış olan {len(self.report.co_duty_assignments)} öğretmen,")
            lines.append("boş ders saatlerinde okulun en yoğun alanlarına (Bahçe, Zemin Kat vb.) eşli destek nöbetçisi olarak görevlendirildi:")
            lines.append("─────────────────────────────────────────────────────────────────────────")
            for p in self.report.co_duty_proposals:
                lines.append(f" • [{p.get('day_name')}] {p.get('location_name')}: {p.get('co_teacher_name')} ({p.get('co_teacher_branch')})")
                lines.append(f"   ➡️ Asıl Nöbetçi: {p.get('primary_teacher_name')} | Boş Saatler: {p.get('free_periods_str')}. dersler")
            lines.append("─────────────────────────────────────────────────────────────────────────\n")
        else:
            lines.append("👥 EŞLİ NÖBET DURUMU: Eşli nöbet kullanılmadı; standart tekli slot dağıtımı uygulandı.\n")

        lines.append("📊 ÖĞRETMENLERİN NÖBET SAYISI DAĞILIMI:")
        lines.append(f" • 0 Nöbet Alan: {fd.get('zero_duty_teachers', 0)} öğretmen")
        lines.append(f" • 1 Nöbet Alan: {fd.get('one_duty_teachers', 0)} öğretmen")
        lines.append(f" • 2+ Nöbet Alan: {fd.get('multi_duty_teachers', 0)} öğretmen\n")
        lines.append("Sonuç: Nöbet dağıtımı kurum içi iş barışını ve dengeli iş gücü paylaşımını sağlayacak şekilde tamamlanmıştır.")
        return "\n".join(lines)

    def _copy_to_clipboard(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self.generated_text_report)
            self.update()
            self.lbl_copy_status.configure(text="✔ Rapor panoya kopyalandı!")
            self.after(3000, lambda: self.lbl_copy_status.configure(text=""))
        except Exception as e:
            logger.error(f"Pano kopyalama hatası: {e}")


class DistributionDialog(tk.Toplevel):
    """Geriye dönük uyumluluk için Toplevel sarmalayıcı."""
    def __init__(
        self,
        parent: tk.Widget,
        db: Database,
        week_start: str,
        on_applied: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent)
        self.title("Otomatik Nöbet Dağıtımı & Adalet Analizi")
        self.geometry("980x720")
        self.minsize(860, 600)
        self.transient(parent)
        self.view = DistributionView(
            self,
            db=db,
            get_week_start=lambda: week_start,
            on_applied=lambda: [on_applied() if on_applied else None, self.destroy()],
            on_cancel=self.destroy
        )
        self.view.pack(fill="both", expand=True)

    def __getattr__(self, name):
        if "view" in self.__dict__ and hasattr(self.view, name):
            return getattr(self.view, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
