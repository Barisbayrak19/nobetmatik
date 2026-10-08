"""
Haftalık Ders Programı Çıktı ve Rapor Merkezi
Öğretmen El Programı, Sınıf/Şube Programları, Genel Çarşaf Program ve Boş Ders Listesi
için profesyonel PDF, Excel ve önizleme yönetim penceresi.
"""
import os
import subprocess
import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional, List, Dict

from core.database import Database
from core.models import Teacher, TeacherLesson
from logic.export_service import ExportService, PERIOD_TIMES
from core.config import EXPORTS_DIR
from core.logger import logger
from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_SUCCESS, COLOR_BORDER,
    COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, FONT_FAMILY
)

class TimetableExportDialog(tk.Toplevel):
    def __init__(self, parent: tk.Widget, db: Database, default_tab: int = 0):
        super().__init__(parent)
        self.db = db
        self.export_service = ExportService(self.db)

        self.title("📚 Haftalık Ders Programı Çıktı ve Rapor Merkezi")
        self.geometry("860x650")
        self.minsize(780, 560)
        self.configure(bg=COLOR_BG)
        self.transient(parent)
        self.grab_set()

        self._build_ui(default_tab)

    def _build_ui(self, default_tab: int):
        # 1. Başlık Barı (Modern Header)
        top_frame = tk.Frame(self, bg="#0F172A", padx=20, pady=12)
        top_frame.pack(fill="x", side="top")

        lbl_title = tk.Label(
            top_frame,
            text="📚 HAFTALIK DERS PROGRAMI ÇIKTI VE RAPOR MERKEZİ",
            font=(FONT_FAMILY, 12, "bold"),
            fg="#FFFFFF",
            bg="#0F172A"
        )
        lbl_title.pack(anchor="w")

        lbl_desc = tk.Label(
            top_frame,
            text="Öğretmen el programları, sınıf/şube haftalık çizelgeleri, genel çarşaf program ve nöbet boş ders analizleri.",
            font=(FONT_FAMILY, 9),
            fg="#94A3B8",
            bg="#0F172A"
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        # 2. Sekmeler (Notebook)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=12)

        self._build_teacher_tab()
        self._build_class_tab()
        self._build_master_tab()
        self._build_free_periods_tab()

        if 0 <= default_tab < 4:
            self.notebook.select(default_tab)

    # ==========================================
    # SEKME 1: ÖĞRETMEN EL PROGRAMI
    # ==========================================
    def _build_teacher_tab(self):
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="👤 Öğretmen El Programı")

        # Üst Seçim Kontrolleri
        ctrl_frame = ttk.Frame(tab)
        ctrl_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(ctrl_frame, text="Kapsam:", font=(FONT_FAMILY, 9, "bold")).pack(side="left", padx=(0, 6))

        self.teacher_scope_var = tk.StringVar(value="single")
        rb_all = ttk.Radiobutton(
            ctrl_frame,
            text="Tüm Öğretmenler (Toplu Kitapçık)",
            variable=self.teacher_scope_var,
            value="all",
            command=self._on_teacher_scope_change
        )
        rb_all.pack(side="left", padx=(0, 12))

        rb_single = ttk.Radiobutton(
            ctrl_frame,
            text="Tek Öğretmen Seç:",
            variable=self.teacher_scope_var,
            value="single",
            command=self._on_teacher_scope_change
        )
        rb_single.pack(side="left", padx=(0, 6))

        teachers = self.db.get_teachers(active_only=True)
        self.teacher_dict = {f"{t.name} ({t.branch or 'Genel'})": t.id for t in teachers}
        teacher_names = list(self.teacher_dict.keys())

        self.cmb_teacher = ttk.Combobox(ctrl_frame, values=teacher_names, state="readonly", width=34)
        if teacher_names:
            self.cmb_teacher.current(0)
        self.cmb_teacher.pack(side="left", padx=(0, 10))
        self.cmb_teacher.bind("<<ComboboxSelected>>", lambda e: self._preview_teacher_schedule())

        # Canlı Önizleme Çizelgesi
        self.f_preview_teacher = ttk.LabelFrame(tab, text="Haftalık Program Önizleme", padding=8)
        self.f_preview_teacher.pack(fill="both", expand=True, pady=(0, 10))

        cols = ("period", "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma")
        self.tree_teacher_prev = ttk.Treeview(self.f_preview_teacher, columns=cols, show="headings", height=8)
        self.tree_teacher_prev.heading("period", text="Ders Saati", anchor="center")
        self.tree_teacher_prev.column("period", width=120, anchor="center")
        for d in ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"):
            self.tree_teacher_prev.heading(d, text=d, anchor="center")
            self.tree_teacher_prev.column(d, width=120, anchor="center")

        self.tree_teacher_prev.pack(fill="both", expand=True)

        # Alt Buton Barı
        btn_bar = ttk.Frame(tab)
        btn_bar.pack(fill="x")

        self.lbl_teacher_stats = ttk.Label(btn_bar, text="", font=(FONT_FAMILY, 9, "bold"), foreground=COLOR_PRIMARY)
        self.lbl_teacher_stats.pack(side="left")

        ttk.Button(
            btn_bar,
            text="📊 Excel Olarak Kaydet (.xlsx)",
            command=self._export_teacher_excel
        ).pack(side="right", padx=(6, 0))

        ttk.Button(
            btn_bar,
            text="📄 PDF Olarak Kaydet (.pdf)",
            style="Primary.TButton",
            command=self._export_teacher_pdf
        ).pack(side="right")

        self._preview_teacher_schedule()

    def _on_teacher_scope_change(self):
        is_single = (self.teacher_scope_var.get() == "single")
        self.cmb_teacher.configure(state="readonly" if is_single else "disabled")
        if is_single:
            self._preview_teacher_schedule()
        else:
            self.tree_teacher_prev.delete(*self.tree_teacher_prev.get_children())
            teachers_count = len(self.teacher_dict)
            self.lbl_teacher_stats.configure(
                text=f"Tüm {teachers_count} aktif öğretmen için toplu resmi çıktılar hazırlanacak."
            )

    def _preview_teacher_schedule(self):
        if self.teacher_scope_var.get() != "single":
            return
        self.tree_teacher_prev.delete(*self.tree_teacher_prev.get_children())
        selected = self.cmb_teacher.get()
        if not selected or selected not in self.teacher_dict:
            return
        t_id = self.teacher_dict[selected]
        lessons = self.db.get_teacher_lessons(t_id)
        l_map = {(l.day_name, l.period): l for l in lessons}

        days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
        active_count = 0
        for p in range(1, 8):
            time_str = PERIOD_TIMES.get(p, "")
            row = [f"{p}. Ders ({time_str})"]
            for d in days:
                item = l_map.get((d, p))
                if item and not item.is_free and (item.class_name or item.subject_code):
                    row.append(f"{item.class_name} ({item.subject_code})")
                    active_count += 1
                else:
                    row.append("— Boş —")
            self.tree_teacher_prev.insert("", "end", values=tuple(row))

        self.lbl_teacher_stats.configure(text=f"Toplam Haftalık Ders: {active_count} Saat | Boş Saat: {35 - active_count} Saat")

    def _export_teacher_pdf(self):
        is_all = (self.teacher_scope_var.get() == "all")
        t_id = None if is_all else self.teacher_dict.get(self.cmb_teacher.get())
        default_name = "Tum_Ogretmenler_Ders_Programi.pdf" if is_all else f"Ders_Programi_{self.cmb_teacher.get().split(' (')[0].replace(' ', '_')}.pdf"

        out_path = filedialog.asksaveasfilename(
            title="Öğretmen Ders Programı PDF Kaydet",
            initialdir=str(EXPORTS_DIR),
            initialfile=default_name,
            filetypes=[("PDF Belgesi", "*.pdf")],
            parent=self
        )
        if not out_path:
            return
        try:
            self.export_service.export_teacher_timetable_pdf(Path(out_path), teacher_id=t_id)
            self._notify_export_success(out_path)
        except Exception as e:
            logger.error(f"Öğretmen PDF çıktısı hatası: {e}")
            messagebox.showerror("Hata", f"PDF belgesi oluşturulurken hata oluştu:\n{e}", parent=self)

    def _export_teacher_excel(self):
        is_all = (self.teacher_scope_var.get() == "all")
        t_id = None if is_all else self.teacher_dict.get(self.cmb_teacher.get())
        default_name = "Ogretmenler_Ders_Programi.xlsx" if is_all else f"Ders_Programi_{self.cmb_teacher.get().split(' (')[0].replace(' ', '_')}.xlsx"

        out_path = filedialog.asksaveasfilename(
            title="Öğretmen Ders Programı Excel Kaydet",
            initialdir=str(EXPORTS_DIR),
            initialfile=default_name,
            filetypes=[("Excel Tablosu", "*.xlsx")],
            parent=self
        )
        if not out_path:
            return
        try:
            self.export_service.export_teacher_timetable_excel(Path(out_path), teacher_id=t_id)
            self._notify_export_success(out_path)
        except Exception as e:
            logger.error(f"Öğretmen Excel çıktısı hatası: {e}")
            messagebox.showerror("Hata", f"Excel dosyası oluşturulurken hata oluştu:\n{e}", parent=self)

    # ==========================================
    # SEKME 2: SINIF / ŞUBE PROGRAMI
    # ==========================================
    def _build_class_tab(self):
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="🏫 Sınıf / Şube Programı")

        ctrl_frame = ttk.Frame(tab)
        ctrl_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(ctrl_frame, text="Kapsam:", font=(FONT_FAMILY, 9, "bold")).pack(side="left", padx=(0, 6))

        self.class_scope_var = tk.StringVar(value="single")
        rb_all = ttk.Radiobutton(
            ctrl_frame,
            text="Tüm Sınıflar (Toplu Belge)",
            variable=self.class_scope_var,
            value="all",
            command=self._on_class_scope_change
        )
        rb_all.pack(side="left", padx=(0, 12))

        rb_single = ttk.Radiobutton(
            ctrl_frame,
            text="Tek Sınıf Seç:",
            variable=self.class_scope_var,
            value="single",
            command=self._on_class_scope_change
        )
        rb_single.pack(side="left", padx=(0, 6))

        classes = self.db.get_distinct_classes()
        if not classes:
            classes = ["5-A", "5-B", "6-A", "6-B", "7-A", "7-B", "8-A", "8-B"]

        self.cmb_class = ttk.Combobox(ctrl_frame, values=classes, state="readonly", width=18)
        if classes:
            self.cmb_class.current(0)
        self.cmb_class.pack(side="left", padx=(0, 10))
        self.cmb_class.bind("<<ComboboxSelected>>", lambda e: self._preview_class_schedule())

        # Önizleme
        self.f_preview_class = ttk.LabelFrame(tab, text="Sınıf Haftalık Program Önizleme", padding=8)
        self.f_preview_class.pack(fill="both", expand=True, pady=(0, 10))

        cols = ("period", "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma")
        self.tree_class_prev = ttk.Treeview(self.f_preview_class, columns=cols, show="headings", height=8)
        self.tree_class_prev.heading("period", text="Ders Saati", anchor="center")
        self.tree_class_prev.column("period", width=120, anchor="center")
        for d in ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"):
            self.tree_class_prev.heading(d, text=d, anchor="center")
            self.tree_class_prev.column(d, width=120, anchor="center")

        self.tree_class_prev.pack(fill="both", expand=True)

        # Butonlar
        btn_bar = ttk.Frame(tab)
        btn_bar.pack(fill="x")

        self.lbl_class_stats = ttk.Label(btn_bar, text="", font=(FONT_FAMILY, 9, "bold"), foreground=COLOR_PRIMARY)
        self.lbl_class_stats.pack(side="left")

        ttk.Button(
            btn_bar,
            text="📊 Excel Olarak Kaydet (.xlsx)",
            command=self._export_class_excel
        ).pack(side="right", padx=(6, 0))

        ttk.Button(
            btn_bar,
            text="📄 PDF Olarak Kaydet (.pdf)",
            style="Primary.TButton",
            command=self._export_class_pdf
        ).pack(side="right")

        self._preview_class_schedule()

    def _on_class_scope_change(self):
        is_single = (self.class_scope_var.get() == "single")
        self.cmb_class.configure(state="readonly" if is_single else "disabled")
        if is_single:
            self._preview_class_schedule()
        else:
            self.tree_class_prev.delete(*self.tree_class_prev.get_children())
            classes = self.db.get_distinct_classes()
            self.lbl_class_stats.configure(
                text=f"Tüm {len(classes)} şube için toplu resmi sınıf ders programı çıktıları hazırlanacak."
            )

    def _preview_class_schedule(self):
        if self.class_scope_var.get() != "single":
            return
        self.tree_class_prev.delete(*self.tree_class_prev.get_children())
        c_name = self.cmb_class.get()
        if not c_name:
            return

        lessons = self.db.get_class_lessons(c_name)
        l_map = {(l.day_name, l.period): l for l in lessons}
        teachers_map = {t.id: t.name for t in self.db.get_teachers()}

        days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
        active_count = 0
        for p in range(1, 8):
            time_str = PERIOD_TIMES.get(p, "")
            row = [f"{p}. Ders ({time_str})"]
            for d in days:
                item = l_map.get((d, p))
                if item and (item.subject_code or item.class_name):
                    t_name = teachers_map.get(item.teacher_id, "")
                    t_short = t_name.split()[-1] if t_name else ""
                    row.append(f"{item.subject_code} ({t_short})")
                    active_count += 1
                else:
                    row.append("— Boş —")
            self.tree_class_prev.insert("", "end", values=tuple(row))

        self.lbl_class_stats.configure(text=f"Sınıf: {c_name} | Toplam Ders: {active_count} Saat")

    def _export_class_pdf(self):
        is_all = (self.class_scope_var.get() == "all")
        c_name = None if is_all else self.cmb_class.get()
        default_name = "Tum_Siniflar_Ders_Programi.pdf" if is_all else f"Sinif_Programi_{self.cmb_class.get()}.pdf"

        out_path = filedialog.asksaveasfilename(
            title="Sınıf Ders Programı PDF Kaydet",
            initialdir=str(EXPORTS_DIR),
            initialfile=default_name,
            filetypes=[("PDF Belgesi", "*.pdf")],
            parent=self
        )
        if not out_path:
            return
        try:
            self.export_service.export_class_timetable_pdf(Path(out_path), class_name=c_name)
            self._notify_export_success(out_path)
        except Exception as e:
            logger.error(f"Sınıf PDF çıktısı hatası: {e}")
            messagebox.showerror("Hata", f"PDF belgesi oluşturulurken hata oluştu:\n{e}", parent=self)

    def _export_class_excel(self):
        is_all = (self.class_scope_var.get() == "all")
        c_name = None if is_all else self.cmb_class.get()
        default_name = "Siniflar_Haftalik_Ders_Programi.xlsx" if is_all else f"Sinif_Programi_{self.cmb_class.get()}.xlsx"

        out_path = filedialog.asksaveasfilename(
            title="Sınıf Ders Programı Excel Kaydet",
            initialdir=str(EXPORTS_DIR),
            initialfile=default_name,
            filetypes=[("Excel Tablosu", "*.xlsx")],
            parent=self
        )
        if not out_path:
            return
        try:
            self.export_service.export_class_timetable_excel(Path(out_path), class_name=c_name)
            self._notify_export_success(out_path)
        except Exception as e:
            logger.error(f"Sınıf Excel çıktısı hatası: {e}")
            messagebox.showerror("Hata", f"Excel dosyası oluşturulurken hata oluştu:\n{e}", parent=self)

    # ==========================================
    # SEKME 3: GENEL ÇARŞAF DERS PROGRAMI
    # ==========================================
    def _build_master_tab(self):
        tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(tab, text="📊 Genel Çarşaf Program")

        f_card = ttk.Frame(tab, style="Card.TFrame", padding=20)
        f_card.pack(fill="both", expand=True)

        ttk.Label(
            f_card,
            text="📊 Kurumsal Genel Haftalık Çarşaf Ders Programı",
            font=(FONT_FAMILY, 12, "bold"),
            foreground=COLOR_PRIMARY
        ).pack(anchor="w", pady=(0, 10))

        desc = (
            "Genel Çarşaf Program, okuldaki tüm öğretmenlerin haftanın 5 günü boyunca 7 ders saatindeki "
            "tüm görev dağılımını (hangi sınıfta hangi derse girdiğini) tek bir ana matriste gösterir.\n\n"
            "Özellikler:\n"
            "• Tüm öğretmenler, branşları ve haftalık toplam ders saatleri\n"
            "• Pazartesi'den Cuma'ya kadar 35 ders saatinin tamamı\n"
            "• Resmi okul idaresi onay formatında renkli ve net hücreler\n"
            "• Excel formatında filtreleme ve yazdırmaya hazır düzen"
        )
        ttk.Label(f_card, text=desc, font=(FONT_FAMILY, 9), wraplength=700, justify="left").pack(anchor="w", pady=(0, 20))

        ttk.Button(
            f_card,
            text="📊 Genel Çarşaf Programı İndir (.xlsx)",
            style="Primary.TButton",
            command=self._export_master_excel
        ).pack(anchor="w")

    def _export_master_excel(self):
        school = self.db.get_school_info()
        default_name = f"Genel_Carsaf_Ders_Programi_{school.academic_year.replace('-', '_')}.xlsx"
        out_path = filedialog.asksaveasfilename(
            title="Genel Çarşaf Program Kaydet",
            initialdir=str(EXPORTS_DIR),
            initialfile=default_name,
            filetypes=[("Excel Tablosu", "*.xlsx")],
            parent=self
        )
        if not out_path:
            return
        try:
            self.export_service.export_master_timetable_excel(Path(out_path))
            self._notify_export_success(out_path)
        except Exception as e:
            logger.error(f"Genel Çarşaf Excel hatası: {e}")
            messagebox.showerror("Hata", f"Çarşaf program oluşturulurken hata oluştu:\n{e}", parent=self)

    # ==========================================
    # SEKME 4: BOŞ DERSLER VE NÖBET UYGUNLUĞU
    # ==========================================
    def _build_free_periods_tab(self):
        tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(tab, text="🟢 Boş Ders & Nöbet Analizi")

        f_card = ttk.Frame(tab, style="Card.TFrame", padding=20)
        f_card.pack(fill="both", expand=True)

        ttk.Label(
            f_card,
            text="🟢 Öğretmen Günlük Boş Ders ve İkame Uygunluk Çizelgesi",
            font=(FONT_FAMILY, 12, "bold"),
            foreground=COLOR_SUCCESS
        ).pack(anchor="w", pady=(0, 10))

        desc = (
            "Nöbetçi öğretmenlerin nöbet günlerinde boş olduğu saatleri veya raporlu öğretmenlerin yerine "
            "derse girebilecek uygun öğretmenleri hızlıca tespit etmek için hazırlanan resmi analiz çizelgesidir.\n\n"
            "Çıktı Kapsamı:\n"
            "• Her öğretmen için gün bazında boş olan ders saatleri (Örn: 2, 4, 5. Ders)\n"
            "• Tüm gün boş olan öğretmenler için özel yeşil durum vurgusu\n"
            "• Nöbetçi öğretmen ikame görevlendirmelerinde referans belge olarak kullanılır"
        )
        ttk.Label(f_card, text=desc, font=(FONT_FAMILY, 9), wraplength=700, justify="left").pack(anchor="w", pady=(0, 20))

        btn_box = ttk.Frame(f_card)
        btn_box.pack(anchor="w", pady=(10, 0))

        ttk.Button(
            btn_box,
            text="📊 Boş Dersler Çizelgesi İndir (.xlsx)",
            style="Success.TButton",
            command=self._export_free_excel
        ).pack(side="left", padx=(0, 10))

    def _export_free_excel(self):
        default_name = f"Ogretmen_Bos_Dersler_Cizelgesi.xlsx"
        out_path = filedialog.asksaveasfilename(
            title="Boş Dersler Çizelgesi Kaydet",
            initialdir=str(EXPORTS_DIR),
            initialfile=default_name,
            filetypes=[("Excel Tablosu", "*.xlsx")],
            parent=self
        )
        if not out_path:
            return
        try:
            self.export_service.export_free_periods_excel(Path(out_path))
            self._notify_export_success(out_path)
        except Exception as e:
            logger.error(f"Boş ders çizelgesi hatası: {e}")
            messagebox.showerror("Hata", f"Boş ders çizelgesi oluşturulurken hata oluştu:\n{e}", parent=self)

    # --- Yardımcı Başarı Penceresi ---
    def _notify_export_success(self, file_path_str: str):
        path = Path(file_path_str)
        if not path.exists():
            return

        win = tk.Toplevel(self)
        win.title("Çıktı Başarıyla Oluşturuldu")
        win.geometry("450x180")
        win.configure(bg=COLOR_BG)
        win.transient(self)
        win.grab_set()

        f = ttk.Frame(win, padding=16)
        f.pack(fill="both", expand=True)

        ttk.Label(
            f,
            text="✔ Belge Başarıyla Oluşturuldu!",
            font=(FONT_FAMILY, 11, "bold"),
            foreground=COLOR_SUCCESS
        ).pack(anchor="w", pady=(0, 6))

        ttk.Label(
            f,
            text=f"Dosya Adı: {path.name}\nKonum: {path.parent}",
            font=(FONT_FAMILY, 9),
            foreground=COLOR_TEXT_MAIN
        ).pack(anchor="w", pady=(0, 12))

        b_box = ttk.Frame(f)
        b_box.pack(fill="x", side="bottom")

        def _open_file():
            try:
                os.startfile(str(path))
            except Exception:
                subprocess.Popen(["explorer", str(path)])
            win.destroy()

        def _open_folder():
            try:
                subprocess.Popen(["explorer", str(path.parent)])
            except Exception:
                pass
            win.destroy()

        ttk.Button(b_box, text="Belgeyi Aç", style="Primary.TButton", command=_open_file).pack(side="left", padx=(0, 6))
        ttk.Button(b_box, text="Klasörde Göster", command=_open_folder).pack(side="left", padx=(0, 6))
        ttk.Button(b_box, text="Kapat", command=win.destroy).pack(side="right")
