"""
Otomatik Nöbet Dağıtımı ve Önizleme Ekranı
Adalet analizi, kural yapılandırması ve kullanıcı onaylı uygulama.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional, List, Dict
from core.models import Assignment, DutyFairnessReport
from core.database import Database
from logic.auto_scheduler import AutoScheduler
from ui.theme import COLOR_CARD, COLOR_PRIMARY, COLOR_SUCCESS, FONT_FAMILY

class DistributionDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Widget,
        db: Database,
        week_start: str,
        on_applied: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent)
        self.db = db
        self.week_start = week_start
        self.on_applied = on_applied
        self.scheduler = AutoScheduler(db)

        self.title("Otomatik Nöbet Dağıtımı & Adalet Analizi")
        self.geometry("820x620")
        self.transient(parent)
        self.grab_set()

        self.avoid_consecutive_var = tk.BooleanVar(value=True)
        self.preserve_fixed_var = tk.BooleanVar(value=True)

        self.preview_assignments: Optional[List[Assignment]] = None
        self.fairness_report: Optional[DutyFairnessReport] = None

        self._build_ui()
        self.calculate_preview()

    def _build_ui(self):
        top_frame = ttk.Frame(self, padding=15)
        top_frame.pack(fill="x")

        ttk.Label(
            top_frame,
            text="⚖️ Akıllı ve Dengeli Nöbet Dağıtım Motoru",
            font=(FONT_FAMILY, 12, "bold"),
            foreground=COLOR_PRIMARY
        ).pack(anchor="w", pady=(0, 5))

        # Kural Seçenekleri
        opts_frame = ttk.Frame(top_frame)
        opts_frame.pack(fill="x", pady=5)

        ttk.Checkbutton(
            opts_frame,
            text="Sabit nöbetleri koru (🔒 Değiştirme)",
            variable=self.preserve_fixed_var
        ).pack(side="left", padx=(0, 15))

        ttk.Checkbutton(
            opts_frame,
            text="Ardışık günleri engelle (Üst üste gün verme)",
            variable=self.avoid_consecutive_var
        ).pack(side="left", padx=(0, 15))

        btn_recalc = ttk.Button(
            opts_frame,
            text="🔄 Yeniden Hesapla",
            command=self.calculate_preview
        )
        btn_recalc.pack(side="right")

        # Orta Bölüm: Sekmeli Görünüm (Önizleme Listesi & Adalet Raporu)
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=15, pady=5)

        # Sekme 1: Önizleme Tablosu
        self.tab_preview = ttk.Frame(notebook)
        notebook.add(self.tab_preview, text="📋 Dağıtım Önizlemesi")

        preview_table_frame = ttk.Frame(self.tab_preview, padding=5)
        preview_table_frame.pack(fill="both", expand=True)

        cols = ("day", "loc", "slot", "teacher")
        self.tree_preview = ttk.Treeview(preview_table_frame, columns=cols, show="headings")
        self.tree_preview.heading("day", text="Gün")
        self.tree_preview.heading("loc", text="Nöbet Yeri")
        self.tree_preview.heading("slot", text="Slot")
        self.tree_preview.heading("teacher", text="Atanan Öğretmen")

        self.tree_preview.column("day", width=120)
        self.tree_preview.column("loc", width=180)
        self.tree_preview.column("slot", width=80, anchor="center")
        self.tree_preview.column("teacher", width=250)

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
        bottom_frame = ttk.Frame(self, padding=15)
        bottom_frame.pack(fill="x", side="bottom")

        self.lbl_status = ttk.Label(bottom_frame, text="", font=(FONT_FAMILY, 9, "bold"))
        self.lbl_status.pack(side="left")

        ttk.Button(bottom_frame, text="Vazgeç", command=self.destroy).pack(side="right", padx=(5, 0))
        btn_apply = ttk.Button(
            bottom_frame,
            text="✔ Dağıtımı Uygula ve Kaydet",
            style="Success.TButton",
            command=self.apply_schedule
        )
        btn_apply.pack(side="right")

    def calculate_preview(self):
        try:
            assignments, report = self.scheduler.generate_schedule(
                week_start=self.week_start,
                avoid_consecutive_days=self.avoid_consecutive_var.get()
            )
            self.preview_assignments = assignments
            self.fairness_report = report

            # Önizleme tablosunu doldur
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
                self.tree_preview.insert("", "end", values=(d_name, l_name, a.slot_index + 1, f"{t_name}{lock}"))

            # Adalet Raporu Metni
            self.report_text.delete("1.0", tk.END)
            self.report_text.insert(tk.END, "=== NÖBET DAĞILIM ADALETİ RAPORU ===\n\n")
            self.report_text.insert(tk.END, f"🎯 Nöbet Adalet Skoru: %{report.fairness_score}\n")
            self.report_text.insert(tk.END, f"📊 Ortalama Nöbet Sayısı: {report.average_duties} nöbet/öğretmen\n")
            self.report_text.insert(tk.END, f"📉 En Az Nöbet: {report.min_duties} | 📈 En Çok Nöbet: {report.max_duties}\n\n")

            if report.warnings:
                self.report_text.insert(tk.END, "⚠️ UYARILAR VE ÇÖZÜLEMEYEN KISITLAR:\n")
                for w in report.warnings:
                    self.report_text.insert(tk.END, f" - {w}\n")
                self.report_text.insert(tk.END, "\n")

            self.report_text.insert(tk.END, "📋 ÖĞRETMEN BAZLI NÖBET DAĞILIMI:\n")
            sorted_teachers = sorted(report.teacher_counts.items(), key=lambda x: x[1], reverse=True)
            for t_id, count in sorted_teachers:
                name = report.teacher_names.get(t_id, t_id)
                self.report_text.insert(tk.END, f" • {name:<35}: {count} Nöbet\n")

            self.lbl_status.configure(
                text=f"Adalet Skoru: %{report.fairness_score} | Toplam {len(assignments)} slot hesaplandı.",
                foreground=COLOR_SUCCESS if report.fairness_score >= 80 else "#D97706"
            )

        except Exception as e:
            logger.error(f"Dağıtım önizleme hatası: {e}")
            messagebox.showerror("Hata", f"Otomatik dağıtım hesaplanırken hata oluştu:\n{e}")

    def apply_schedule(self):
        if not self.preview_assignments:
            messagebox.showwarning("Uyarı", "Uygulanacak bir dağıtım önizlemesi bulunamadı.")
            return

        if messagebox.askyesno("Onay", "Hesaplanan dağıtım haftalık çizelgeye kaydedilecek. Onaylıyor musunuz?"):
            self.scheduler.apply_schedule(self.preview_assignments)
            messagebox.showinfo("Başarılı", "Otomatik nöbet dağıtımı başarıyla uygulandı!")
            if self.on_applied:
                self.on_applied()
            self.destroy()
