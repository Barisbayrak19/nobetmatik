"""
Kapsamlı İçe Aktarma Merkezi (Universal Import Center)
Excel (.xlsx), CSV ve JSON formatlarından:
1. Öğretmen Listesi ve Branşlar (Akıllı Benzerlik Eşleştirmesi ile)
2. Haftalık Öğretmen Ders Programı (Saat, Şube ve Ders Kodu)
3. Geçmiş / Eski Nöbet Çizelgesi (Belirli bir haftaya nöbet atamaları)
4. Nöbet Yerleri ve Sınıf Listesi
içe aktarılmasını sağlar.
"""
import os
import csv
import json
import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Callable, Optional, List, Dict, Tuple, Any

import openpyxl

from core.models import Teacher, Location, Day, Assignment, TeacherLesson
from core.database import Database
from logic.matching_service import MatchingService
from logic.substitution_service import SubstitutionService
from logic.duty_service import DutyService
from logic.asc_service import AscBilsaService
from core.logger import logger
from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_SECONDARY, COLOR_SUCCESS,
    COLOR_DANGER, COLOR_BORDER, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, FONT_FAMILY
)
from ui.timetable_export_dialog import TimetableExportDialog


class ImportConflictDialog(tk.Toplevel):
    """
    İsim çelişkisinde kullanıcıya karar seçeneği sunan modal:
    [X olarak kullan] [Yeni öğretmen oluştur] [Atla]
    """
    def __init__(self, parent: tk.Widget, raw_name: str, candidate_name: str, score: float):
        super().__init__(parent)
        self.raw_name = raw_name
        self.candidate_name = candidate_name
        self.score = score
        self.decision: Optional[str] = None

        self.title("İsim Eşleştirme Kararı")
        self.geometry("460x270")
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="⚠️ İsim Birebir Eşleşmedi!",
            font=(FONT_FAMILY, 11, "bold"),
            foreground="#B45309"
        ).pack(anchor="w", pady=(0, 10))

        ttk.Label(
            frame,
            text=f"Dosyadan Okunan İsim:  {self.raw_name}",
            font=(FONT_FAMILY, 10, "bold")
        ).pack(anchor="w", pady=2)

        ttk.Label(
            frame,
            text=f"Sistemdeki Olası Eşleşme:  {self.candidate_name} (Benzerlik: %{int(self.score * 100)})",
            font=(FONT_FAMILY, 10),
            foreground=COLOR_PRIMARY
        ).pack(anchor="w", pady=(2, 15))

        btn_box = ttk.Frame(frame)
        btn_box.pack(fill="x", side="bottom", pady=5)

        ttk.Button(
            btn_box,
            text=f"'{self.candidate_name}' Olarak Eşle",
            style="Success.TButton",
            command=self._match
        ).pack(fill="x", pady=2)

        ttk.Button(
            btn_box,
            text=f"'{self.raw_name}' İçin Yeni Öğretmen Oluştur",
            style="Primary.TButton",
            command=self._create_new
        ).pack(fill="x", pady=2)

        ttk.Button(
            btn_box,
            text="Bu Kaydı Atla",
            command=self._skip
        ).pack(fill="x", pady=2)

    def _match(self):
        self.decision = "match"
        self.destroy()

    def _create_new(self):
        self.decision = "create_new"
        self.destroy()

    def _skip(self):
        self.decision = "skip"
        self.destroy()


class ImportDialog(tk.Toplevel):
    def __init__(self, parent: tk.Widget, db: Database, on_imported: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.db = db
        self.on_imported = on_imported
        self.sub_service = SubstitutionService(self.db)
        self.duty_service = DutyService(self.db)
        self.asc_service = AscBilsaService(self.db)

        self.title("📥 İçe Aktarma Merkezi (Excel / CSV / JSON / PDF)")
        self.geometry("820x620")
        self.minsize(720, 520)
        self.configure(bg=COLOR_BG)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        # 1. Başlık
        top_frame = tk.Frame(self, bg="#0F172A", padx=20, pady=12)
        top_frame.pack(fill="x", side="top")

        lbl_title = tk.Label(
            top_frame,
            text="📥 KURUMSAL VERİ VE ÇİZELGE İÇE AKTARMA MERKEZİ",
            font=(FONT_FAMILY, 12, "bold"),
            fg="#FFFFFF",
            bg="#0F172A"
        )
        lbl_title.pack(anchor="w")

        lbl_desc = tk.Label(
            top_frame,
            text="Öğretmen listeleri, haftalık ders programları, eski nöbet çizelgeleri ve nöbet yerlerini toplu olarak sisteme aktarın.",
            font=(FONT_FAMILY, 9),
            fg="#94A3B8",
            bg="#0F172A"
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        # 2. Notebook (Sekmeler)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=12)

        self._build_teachers_tab()
        self._build_timetables_tab()
        self._build_past_duty_tab()
        self._build_locations_tab()

    # ==========================================
    # SEKME 1: ÖĞRETMENLER AKTAR
    # ==========================================
    def _build_teachers_tab(self):
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="👥 Öğretmen Listesi")

        self.teacher_file_var = tk.StringVar()
        self.parsed_teachers: List[Dict[str, str]] = []

        f_file = ttk.Frame(tab)
        f_file.pack(fill="x", pady=(0, 10))
        ttk.Label(f_file, text="Dosya Seç:", font=(FONT_FAMILY, 9, "bold")).pack(side="left", padx=(0, 6))
        ttk.Entry(f_file, textvariable=self.teacher_file_var, font=(FONT_FAMILY, 9)).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(f_file, text="Gözat...", command=self._browse_teacher_file).pack(side="left")

        ttk.Label(
            tab,
            text="💡 Sütunlar 'Ad Soyad' (veya 'Adı', 'Soyadı') ve isteğe bağlı 'Branş' içermelidir. Sistem mevcut öğretmenlerle akıllı eşleştirme yapar.",
            font=(FONT_FAMILY, 8),
            foreground=COLOR_TEXT_MUTED
        ).pack(anchor="w", pady=(0, 8))

        # Önizleme
        self.tree_teachers = ttk.Treeview(tab, columns=("name", "branch"), show="headings", height=10)
        self.tree_teachers.heading("name", text="Dosyadaki Öğretmen Adı", anchor="w")
        self.tree_teachers.heading("branch", text="Branşı", anchor="w")
        self.tree_teachers.column("name", width=340, anchor="w")
        self.tree_teachers.column("branch", width=260, anchor="w")
        self.tree_teachers.pack(fill="both", expand=True, pady=(0, 10))

        btn_bar = ttk.Frame(tab)
        btn_bar.pack(fill="x")
        self.btn_import_teachers = ttk.Button(btn_bar, text="✔ Öğretmenleri İçeri Aktar", style="Primary.TButton", state="disabled", command=self._start_teacher_import)
        self.btn_import_teachers.pack(side="right")

    def _browse_teacher_file(self):
        path = filedialog.askopenfilename(
            title="Öğretmen Listesi veya e-Okul PDF Seç",
            filetypes=[
                ("Desteklenen Belgeler (*.xlsx, *.csv, *.pdf)", "*.xlsx;*.csv;*.pdf"),
                ("e-Okul PDF Belgesi (*.pdf)", "*.pdf"),
                ("Excel Dosyaları (*.xlsx)", "*.xlsx"),
                ("CSV Dosyaları (*.csv)", "*.csv")
            ],
            parent=self
        )
        if not path:
            return
        self.teacher_file_var.set(path)
        self._load_teacher_file(Path(path))

    def _load_teacher_file(self, file_path: Path):
        self.parsed_teachers.clear()
        for item in self.tree_teachers.get_children():
            self.tree_teachers.delete(item)

        try:
            if file_path.suffix.lower() == ".pdf":
                # e-Okul PDF belgesinden öğretmenleri ve branşları otomatik ayrıştır
                parsed = self.sub_service.parse_eokul_timetable_pdf(str(file_path))
                for t_name, t_info in sorted(parsed["teachers"].items()):
                    branch = t_info["branch"]
                    self.parsed_teachers.append({"name": t_name, "branch": branch})
                    self.tree_teachers.insert("", "end", values=(t_name, branch))

            elif file_path.suffix.lower() == ".xlsx":
                wb = openpyxl.load_workbook(file_path, data_only=True)
                ws = wb.active
                rows = list(ws.iter_rows(values_only=True))
                if not rows:
                    return

                header = [str(c).strip().lower() if c else "" for c in rows[0]]
                name_idx = None
                surname_idx = None
                branch_idx = None

                for idx, col_name in enumerate(header):
                    if "adı" in col_name and "soyad" not in col_name:
                        name_idx = idx
                    elif "soyad" in col_name:
                        surname_idx = idx
                    elif "ad soyad" in col_name or "öğretmen" in col_name:
                        name_idx = idx
                    elif "alan" in col_name or "branş" in col_name:
                        branch_idx = idx

                for r in rows[1:]:
                    if not any(r):
                        continue
                    full_name = ""
                    if name_idx is not None and surname_idx is not None:
                        f = str(r[name_idx]).strip() if r[name_idx] else ""
                        l = str(r[surname_idx]).strip() if r[surname_idx] else ""
                        full_name = f"{f} {l}".strip()
                    elif name_idx is not None:
                        full_name = str(r[name_idx]).strip() if r[name_idx] else ""
                    elif r[0]:
                        full_name = str(r[0]).strip()

                    branch = str(r[branch_idx]).strip() if branch_idx is not None and r[branch_idx] else ""
                    if full_name:
                        self.parsed_teachers.append({"name": full_name, "branch": branch})
                        self.tree_teachers.insert("", "end", values=(full_name, branch))

            elif file_path.suffix.lower() == ".csv":
                with open(file_path, "r", encoding="utf-8-sig") as f:
                    sample = f.read(2048)
                    f.seek(0)
                    delim = ";" if ";" in sample else ","
                    reader = csv.reader(f, delimiter=delim)
                    for r in reader:
                        if not r or not any(r):
                            continue
                        name = r[0].strip()
                        branch = r[1].strip() if len(r) > 1 else ""
                        self.parsed_teachers.append({"name": name, "branch": branch})
                        self.tree_teachers.insert("", "end", values=(name, branch))

            if self.parsed_teachers:
                self.btn_import_teachers.configure(state="normal")
            else:
                messagebox.showwarning("Uyarı", "Dosyadan öğretmen verisi okunamadı.", parent=self)
        except Exception as e:
            logger.error(f"Öğretmen dosyası okunurken hata: {e}")
            messagebox.showerror("Hata", f"Dosya okunurken hata oluştu:\n{e}", parent=self)

    def _start_teacher_import(self):
        existing_teachers = self.db.get_teachers()
        existing_names = [t.name for t in existing_teachers]
        name_to_teacher = {t.name: t for t in existing_teachers}

        imported_count = 0
        matched_count = 0
        skipped_count = 0

        for item in self.parsed_teachers:
            raw_name = item["name"]
            branch = item["branch"]

            exact_match = next((t for t in existing_teachers if t.name.lower() == raw_name.lower()), None)
            if exact_match:
                if branch and not exact_match.branch:
                    exact_match.branch = branch
                    self.db.save_teacher(exact_match)
                matched_count += 1
                continue

            best_matches = MatchingService.find_best_matches(raw_name, existing_names, threshold=0.7)
            if best_matches:
                candidate_name, score = best_matches[0]
                dlg = ImportConflictDialog(self, raw_name, candidate_name, score)
                self.wait_window(dlg)

                if dlg.decision == "match":
                    matched_teacher = name_to_teacher.get(candidate_name)
                    if matched_teacher and branch and not matched_teacher.branch:
                        matched_teacher.branch = branch
                        self.db.save_teacher(matched_teacher)
                    matched_count += 1
                elif dlg.decision == "create_new":
                    new_t = Teacher(name=raw_name, branch=branch)
                    self.db.save_teacher(new_t)
                    existing_names.append(raw_name)
                    name_to_teacher[raw_name] = new_t
                    imported_count += 1
                else:
                    skipped_count += 1
            else:
                new_t = Teacher(name=raw_name, branch=branch)
                self.db.save_teacher(new_t)
                existing_names.append(raw_name)
                name_to_teacher[raw_name] = new_t
                imported_count += 1

        messagebox.showinfo(
            "Başarılı",
            f"Öğretmen İçe Aktarımı Tamamlandı!\n\n"
            f"• Yeni Eklenen: {imported_count}\n"
            f"• Mevcutla Eşleşen: {matched_count}\n"
            f"• Atlanan: {skipped_count}",
            parent=self
        )
        if self.on_imported:
            self.on_imported()

    # ==========================================
    # SEKME 2: DERS PROGRAMI AKTAR
    # ==========================================
    def _build_timetables_tab(self):
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="📚 Ders Programı")

        self.timetable_file_var = tk.StringVar()
        self.parsed_lessons: List[TeacherLesson] = []

        f_file = ttk.Frame(tab)
        f_file.pack(fill="x", pady=(0, 6))
        ttk.Label(f_file, text="Dosya Seç:", font=(FONT_FAMILY, 9, "bold")).pack(side="left", padx=(0, 6))
        ttk.Entry(f_file, textvariable=self.timetable_file_var, font=(FONT_FAMILY, 9)).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(f_file, text="Gözat (.pdf / .json / .xlsx / .csv)...", command=self._browse_timetable_file).pack(side="left")

        # Seçenekler ve Hızlı Sıfırlama Barı
        f_opts = ttk.Frame(tab)
        f_opts.pack(fill="x", pady=(0, 8))

        self.auto_create_teachers_var = tk.BooleanVar(value=True)
        self.clear_timetables_var = tk.BooleanVar(value=True)

        ttk.Checkbutton(
            f_opts,
            text="👤 PDF'teki yeni öğretmenleri veritabanına otomatik ekle",
            variable=self.auto_create_teachers_var
        ).pack(side="left", padx=(0, 15))

        ttk.Checkbutton(
            f_opts,
            text="🗑️ Aktarımdan önce mevcut ders programını temizle",
            variable=self.clear_timetables_var
        ).pack(side="left", padx=(0, 15))

        ttk.Button(
            f_opts,
            text="🧹 Sadece Ders Programını Sıfırla",
            command=self._quick_reset_timetables
        ).pack(side="right")

        ttk.Label(
            tab,
            text="💡 aSc Timetables XML (.xml), aSc / Bilsa Çarşaf Excel (.xlsx) veya e-Okul PDF dosyasını seçin. Tüm öğretmenler, sınıflar ve ders dağıtımı otomatik ayrıştırılır.",
            font=(FONT_FAMILY, 8),
            foreground=COLOR_TEXT_MUTED
        ).pack(anchor="w", pady=(0, 8))

        self.tree_timetables = ttk.Treeview(tab, columns=("teacher", "day", "period", "class", "subject", "status"), show="headings", height=10)
        self.tree_timetables.heading("teacher", text="Öğretmen", anchor="w")
        self.tree_timetables.heading("day", text="Gün", anchor="center")
        self.tree_timetables.heading("period", text="Saat", anchor="center")
        self.tree_timetables.heading("class", text="Sınıf", anchor="center")
        self.tree_timetables.heading("subject", text="Ders", anchor="center")
        self.tree_timetables.heading("status", text="Durum", anchor="center")

        self.tree_timetables.column("teacher", width=180, anchor="w")
        self.tree_timetables.column("day", width=100, anchor="center")
        self.tree_timetables.column("period", width=60, anchor="center")
        self.tree_timetables.column("class", width=80, anchor="center")
        self.tree_timetables.column("subject", width=110, anchor="center")
        self.tree_timetables.column("status", width=90, anchor="center")
        self.tree_timetables.pack(fill="both", expand=True, pady=(0, 10))

        btn_bar = ttk.Frame(tab)
        btn_bar.pack(fill="x")
        self.lbl_timetable_info = ttk.Label(btn_bar, text="", font=(FONT_FAMILY, 9, "bold"), foreground=COLOR_PRIMARY)
        self.lbl_timetable_info.pack(side="left")

        self.btn_import_timetables = ttk.Button(btn_bar, text="✔ Ders Programını Aktar", style="Primary.TButton", state="disabled", command=self._start_timetable_import)
        self.btn_import_timetables.pack(side="right")

        ttk.Button(
            btn_bar,
            text="📚 Ders Programı Çıktılarını Aç",
            command=self._open_timetable_exports
        ).pack(side="right", padx=(0, 6))

    def _open_timetable_exports(self):
        TimetableExportDialog(self, self.db)

    def _quick_reset_timetables(self):
        if messagebox.askyesno("Onay", "Veritabanındaki tüm haftalık ders programı kayıtları silinecektir.\nDevam etmek istiyor musunuz?", parent=self):
            self.db.reset_timetables()
            messagebox.showinfo("Başarılı", "Mevcut ders programı kayıtları temizlendi.", parent=self)
            if self.on_imported:
                self.on_imported()

    def _browse_timetable_file(self):
        path = filedialog.askopenfilename(
            title="Ders Dağıtım veya Program Dosyası Seç (aSc / e-Okul / Bilsa / Excel)",
            filetypes=[
                ("Tüm Desteklenen Formatlar (*.xml, *.pdf, *.xlsx, *.csv, *.json)", "*.xml;*.pdf;*.xlsx;*.csv;*.json"),
                ("aSc Timetables XML (*.xml)", "*.xml"),
                ("e-Okul PDF Ders Programı (*.pdf)", "*.pdf"),
                ("aSc / Bilsa / Excel (*.xlsx)", "*.xlsx"),
                ("JSON Dosyası (*.json)", "*.json"),
                ("CSV Dosyası (*.csv)", "*.csv")
            ],
            parent=self
        )
        if not path:
            return
        self.timetable_file_var.set(path)
        self._load_timetable_file(Path(path))

    def _load_timetable_file(self, file_path: Path):
        self.parsed_lessons.clear()
        for item in self.tree_timetables.get_children():
            self.tree_timetables.delete(item)

        teachers = self.db.get_teachers()
        teacher_map = {t.name.upper(): t for t in teachers}

        try:
            if file_path.suffix.lower() == ".xml":
                parsed = self.asc_service.parse_asc_xml(str(file_path))
                asc_lessons = parsed.get("lessons", [])
                teachers_dict = {t["name"].upper(): t for t in parsed.get("teachers", [])}

                for l in asc_lessons:
                    raw_name = getattr(l, "temp_teacher_name", "")
                    matched_t = teacher_map.get(raw_name.upper())
                    if not matched_t:
                        for ex_t in teachers:
                            if ex_t.name.upper() in raw_name.upper() or raw_name.upper() in ex_t.name.upper():
                                matched_t = ex_t
                                break

                    t_id = matched_t.id if matched_t else ""
                    actual_name = matched_t.name if matched_t else f"{raw_name} (Yeni)"
                    l.teacher_id = t_id
                    branch = teachers_dict.get(raw_name.upper(), {}).get("branch", "Genel")
                    l.temp_branch = branch
                    self.parsed_lessons.append(l)

                    status_txt = "🟢 BOŞ" if l.is_free else "🔴 DOLU"
                    if len(self.tree_timetables.get_children()) < 500:
                        self.tree_timetables.insert(
                            "", "end",
                            values=(actual_name, l.day_name, l.period, l.class_name, l.subject_code, status_txt)
                        )

                self.lbl_timetable_info.configure(
                    text=f"🌟 aSc Timetables XML: {len(parsed['teachers'])} Öğretmen, {len(parsed['classes'])} Sınıf, {len(asc_lessons)} Ders Saati"
                )

            elif file_path.suffix.lower() == ".pdf":
                parsed = self.sub_service.parse_eokul_timetable_pdf(str(file_path))
                teachers_data = parsed["teachers"]
                days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]

                for t_name, t_info in sorted(teachers_data.items()):
                    matched_t = teacher_map.get(t_name)
                    if not matched_t:
                        for ex_t in teachers:
                            if ex_t.name.upper() in t_name or t_name in ex_t.name.upper():
                                matched_t = ex_t
                                break

                    t_id = matched_t.id if matched_t else ""
                    actual_name = matched_t.name if matched_t else f"{t_name} (Yeni)"
                    sched = t_info["schedule"]
                    branch = t_info.get("branch", "Genel")

                    for day_name in days:
                        day_lessons = sched.get(day_name, {})
                        for p_num in range(1, 8):
                            if p_num in day_lessons:
                                c_name, s_name = day_lessons[p_num]
                                is_free = False
                                status_txt = "🔴 DOLU"
                            else:
                                c_name, s_name = "", ""
                                is_free = True
                                status_txt = "🟢 BOŞ"

                            l = TeacherLesson(
                                teacher_id=t_id,
                                day_name=day_name,
                                period=p_num,
                                class_name=c_name,
                                subject_code=s_name,
                                is_free=is_free
                            )
                            l.temp_teacher_name = t_name
                            l.temp_branch = branch
                            self.parsed_lessons.append(l)
                            if len(self.tree_timetables.get_children()) < 500:
                                self.tree_timetables.insert(
                                    "", "end",
                                    values=(actual_name, day_name, p_num, c_name, s_name, status_txt)
                                )

                self.lbl_timetable_info.configure(
                    text=f"📄 e-Okul PDF: {len(teachers_data)} Öğretmen, {len(parsed['classes'])} Sınıf/Şube, {parsed['total_lessons']} Ders Saati"
                )

            elif file_path.suffix.lower() == ".xlsx":
                parsed = self.asc_service.parse_asc_bilsa_excel(str(file_path))
                excel_lessons = parsed.get("lessons", [])
                teachers_dict = {t["name"].upper(): t for t in parsed.get("teachers", [])}

                for l in excel_lessons:
                    raw_name = getattr(l, "temp_teacher_name", "")
                    matched_t = teacher_map.get(raw_name.upper())
                    if not matched_t:
                        for ex_t in teachers:
                            if ex_t.name.upper() in raw_name.upper() or raw_name.upper() in ex_t.name.upper():
                                matched_t = ex_t
                                break

                    t_id = matched_t.id if matched_t else ""
                    actual_name = matched_t.name if matched_t else f"{raw_name} (Yeni)"
                    l.teacher_id = t_id
                    branch = teachers_dict.get(raw_name.upper(), {}).get("branch", "Genel")
                    l.temp_branch = branch
                    self.parsed_lessons.append(l)

                    status_txt = "🟢 BOŞ" if l.is_free else "🔴 DOLU"
                    if len(self.tree_timetables.get_children()) < 500:
                        self.tree_timetables.insert(
                            "", "end",
                            values=(actual_name, l.day_name, l.period, l.class_name, l.subject_code, status_txt)
                        )

                self.lbl_timetable_info.configure(
                    text=f"📊 aSc / Bilsa Excel: {len(parsed.get('teachers', []))} Öğretmen, {len(excel_lessons)} Ders Saati"
                )

            elif file_path.suffix.lower() == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for t_name, days_data in data.items():
                    matched_t = next((t for t in teachers if t.name.lower() in t_name.lower() or t_name.lower() in t.name.lower()), None)
                    t_id = matched_t.id if matched_t else ""
                    actual_name = matched_t.name if matched_t else t_name

                    for day_name, p_list in days_data.items():
                        for p_idx, item in enumerate(p_list, start=1):
                            if isinstance(item, dict):
                                c_name = item.get("class", "")
                                s_code = item.get("subject", "")
                                is_free = item.get("is_free", False) or not (c_name or s_code)
                            else:
                                is_free = True
                                c_name, s_code = "", ""
                            l = TeacherLesson(teacher_id=t_id, day_name=day_name, period=p_idx, class_name=c_name, subject_code=s_code, is_free=is_free)
                            l.temp_teacher_name = t_name
                            self.parsed_lessons.append(l)
                            status_txt = "🟢 BOŞ" if is_free else "🔴 DOLU"
                            if len(self.tree_timetables.get_children()) < 500:
                                self.tree_timetables.insert("", "end", values=(actual_name, day_name, p_idx, c_name, s_code, status_txt))

            if self.parsed_lessons:
                self.btn_import_timetables.configure(state="normal")
            else:
                messagebox.showwarning("Uyarı", "Ders programı verisi okunamadı.", parent=self)
        except Exception as e:
            logger.error(f"Ders programı dosyası okunurken hata: {e}")
            messagebox.showerror("Hata", f"Ders programı okunurken hata oluştu:\n{e}", parent=self)

    def _start_timetable_import(self):
        file_str = self.timetable_file_var.get()
        parent_ref = self.master

        if file_str.lower().endswith(".pdf"):
            try:
                res = self.sub_service.import_timetables_from_pdf(
                    file_str,
                    auto_create_missing_teachers=self.auto_create_teachers_var.get(),
                    clear_existing=self.clear_timetables_var.get()
                )
                ask_export = messagebox.askyesno(
                    "Başarılı",
                    f"e-Okul Ders Programı Başarıyla Aktarıldı!\n\n"
                    f"• Toplam Ders Kaydı: {res['lessons_count']} saat\n"
                    f"• Programdaki Öğretmen Sayısı: {res['teachers_count']}\n"
                    f"• Yeni Eklenen Öğretmen: {res['new_teachers_count']}\n"
                    f"• İşlenen Sınıf / Şube Sayısı: {res['classes_count']}\n\n"
                    f"Şimdi ders programı çıktılarını (Öğretmen El Programı, Sınıf Programları, Çarşaf Tablo) almak veya incelemek ister misiniz?",
                    parent=self
                )
                if self.on_imported:
                    self.on_imported()
                self.destroy()
                if ask_export:
                    TimetableExportDialog(parent_ref, self.db)
                return
            except Exception as e:
                logger.error(f"PDF ders programı içe aktarılırken hata: {e}")
                messagebox.showerror("Hata", f"PDF içe aktarılırken hata oluştu:\n{e}", parent=self)
                return

        # aSc XML, aSc/Bilsa Excel veya JSON aktarımı
        new_created_count = 0
        if self.auto_create_teachers_var.get():
            existing_teachers = self.db.get_teachers()
            existing_map = {t.name.upper(): t for t in existing_teachers}

            for l in self.parsed_lessons:
                raw_name = getattr(l, "temp_teacher_name", None)
                if not l.teacher_id and raw_name:
                    name_key = raw_name.strip().upper()
                    if name_key not in existing_map:
                        branch = getattr(l, "temp_branch", "Genel")
                        new_t = Teacher(name=raw_name.strip(), branch=branch)
                        self.db.add_teacher(new_t)
                        existing_map[name_key] = new_t
                        new_created_count += 1
                    l.teacher_id = existing_map[name_key].id

        valid_lessons = [l for l in self.parsed_lessons if l.teacher_id]
        if not valid_lessons:
            messagebox.showwarning(
                "Uyarı",
                "Ders programındaki öğretmenler sistemdeki öğretmenlerle eşleşemedi.\n"
                "Lütfen 'Yeni öğretmenleri veritabanına otomatik ekle' seçeneğini işaretleyiniz.",
                parent=self
            )
            return

        if self.clear_timetables_var.get():
            self.db.clear_teacher_lessons()

        self.db.save_teacher_lessons_batch(valid_lessons)
        ask_export = messagebox.askyesno(
            "Başarılı",
            f"Ders Programı Başarıyla Aktarıldı!\n\n"
            f"• Toplam Ders Kaydı: {len(valid_lessons)} saat\n"
            f"• Yeni Oluşturulan Öğretmen: {new_created_count}\n\n"
            f"Şimdi ders programı çıktılarını (Öğretmen El Programı, Sınıf Programları, Çarşaf Tablo) almak veya incelemek ister misiniz?",
            parent=self
        )
        if self.on_imported:
            self.on_imported()
        self.destroy()
        if ask_export:
            TimetableExportDialog(parent_ref, self.db)

    # ==========================================
    # SEKME 3: ESKİ / GEÇMİŞ NÖBET ÇİZELGESİ AKTAR
    # ==========================================
    def _build_past_duty_tab(self):
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="📋 Eski Nöbet Çizelgesi")

        self.past_file_var = tk.StringVar()
        self.target_week_var = tk.StringVar(value=datetime.date.today().strftime("%Y-%m-%d"))
        self.parsed_duties: List[Assignment] = []

        f_inputs = ttk.Frame(tab)
        f_inputs.pack(fill="x", pady=(0, 10))

        ttk.Label(f_inputs, text="Hedef Hafta (Pzt):", font=(FONT_FAMILY, 9, "bold")).pack(side="left", padx=(0, 6))
        ttk.Entry(f_inputs, textvariable=self.target_week_var, width=12, font=(FONT_FAMILY, 9)).pack(side="left", padx=(0, 15))

        ttk.Label(f_inputs, text="Nöbet Dosyası:", font=(FONT_FAMILY, 9, "bold")).pack(side="left", padx=(0, 6))
        ttk.Entry(f_inputs, textvariable=self.past_file_var, font=(FONT_FAMILY, 9)).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(f_inputs, text="Gözat (.pdf / .xlsx / .csv)...", command=self._browse_past_file).pack(side="left")

        ttk.Label(
            tab,
            text="💡 Format: PDF (resmi MEB / sistem çıktısı), Excel veya CSV tablosundan nöbet görevlendirmelerini otomatik okur ve seçilen haftaya aktarır.",
            font=(FONT_FAMILY, 8),
            foreground=COLOR_TEXT_MUTED
        ).pack(anchor="w", pady=(0, 8))

        self.tree_past = ttk.Treeview(tab, columns=("day", "location", "teacher"), show="headings", height=10)
        self.tree_past.heading("day", text="Gün", anchor="center")
        self.tree_past.heading("location", text="Nöbet Yeri", anchor="w")
        self.tree_past.heading("teacher", text="Nöbetçi Öğretmen", anchor="w")

        self.tree_past.column("day", width=120, anchor="center")
        self.tree_past.column("location", width=220, anchor="w")
        self.tree_past.column("teacher", width=280, anchor="w")
        self.tree_past.pack(fill="both", expand=True, pady=(0, 10))

        btn_bar = ttk.Frame(tab)
        btn_bar.pack(fill="x")
        self.btn_import_past = ttk.Button(btn_bar, text="✔ Eski Nöbet Çizelgesini Aktar", style="Primary.TButton", state="disabled", command=self._start_past_import)
        self.btn_import_past.pack(side="right")

    def _browse_past_file(self):
        path = filedialog.askopenfilename(
            title="Eski Nöbet Çizelgesi Seç",
            filetypes=[
                ("Tüm Desteklenen Çizelgeler (*.pdf, *.xlsx, *.csv)", "*.pdf;*.xlsx;*.csv"),
                ("PDF Nöbet Çizelgesi (*.pdf)", "*.pdf"),
                ("Excel Çizelgeleri (*.xlsx)", "*.xlsx"),
                ("CSV Dosyaları (*.csv)", "*.csv")
            ],
            parent=self
        )
        if not path:
            return
        self.past_file_var.set(path)
        self._load_past_file(Path(path))

    def _load_past_file(self, file_path: Path):
        self.parsed_duties.clear()
        for item in self.tree_past.get_children():
            self.tree_past.delete(item)

        days = self.db.get_days()
        day_map = {d.id: d for d in days}

        locations = self.db.get_locations()
        loc_map = {l.id: l for l in locations}

        teachers = self.db.get_teachers()
        t_map = {t.id: t for t in teachers}

        week_str = self.target_week_var.get().strip() or "2026-09-28"

        try:
            if file_path.suffix.lower() == ".pdf":
                assignments = self.duty_service.parse_duty_table_pdf(str(file_path), week_str)
                self.parsed_duties.extend(assignments)
                for asg in assignments:
                    d_obj = day_map.get(asg.day_id)
                    l_obj = loc_map.get(asg.location_id)
                    t_obj = t_map.get(asg.teacher_id) if asg.teacher_id else None
                    d_name = d_obj.name if d_obj else ""
                    l_name = l_obj.name if l_obj else ""
                    t_name = t_obj.name if t_obj else "Tanımsız Öğretmen"
                    self.tree_past.insert("", "end", values=(d_name, l_name, t_name))

            elif file_path.suffix.lower() in [".xlsx", ".csv"]:
                rows: List[List[Any]] = []
                if file_path.suffix.lower() == ".xlsx":
                    wb = openpyxl.load_workbook(file_path, data_only=True)
                    ws = wb.active
                    rows = [list(r) for r in ws.iter_rows(values_only=True)]
                else:
                    content = ""
                    for enc in ["utf-8-sig", "utf-8", "cp1254", "latin-1"]:
                        try:
                            with open(file_path, "r", encoding=enc) as f:
                                content = f.read()
                            break
                        except Exception:
                            continue
                    delimiter = ";" if ";" in content else ","
                    reader = csv.reader(content.splitlines(), delimiter=delimiter)
                    rows = [list(r) for r in reader]

                header_idx = None
                for r_idx, row in enumerate(rows):
                    row_texts = [str(c).strip().lower() for c in row if c]
                    if any("gün" in x or "pazartesi" in x or "kat" in x or "bahçe" in x for x in row_texts):
                        header_idx = r_idx
                        break

                if header_idx is None:
                    header_idx = 0

                headers = [str(c).strip() if c else "" for c in rows[header_idx]]

                for row in rows[header_idx + 1:]:
                    if not any(row):
                        continue
                    first_cell = str(row[0]).strip().lower()
                    matched_day = next((d for d in days if d.name.lower() in first_cell or first_cell in d.name.lower()), None)
                    if not matched_day:
                        continue

                    for c_idx in range(1, len(row)):
                        if c_idx >= len(headers):
                            continue
                        loc_header = headers[c_idx]
                        if not loc_header:
                            continue
                        t_cell = str(row[c_idx]).strip() if row[c_idx] else ""
                        if not t_cell or t_cell == "-":
                            continue

                        # Location match
                        matched_loc = next((l for l in locations if l.name.lower() in loc_header.lower() or loc_header.lower() in l.name.lower()), None)
                        if not matched_loc:
                            continue

                        # Teacher match
                        matched_t = next((t for t in teachers if t.name.lower() in t_cell.lower() or t_cell.lower() in t.name.lower()), None)
                        t_id = matched_t.id if matched_t else None

                        asg = Assignment(
                            week_start=week_str,
                            day_id=matched_day.id,
                            location_id=matched_loc.id,
                            teacher_id=t_id
                        )
                        self.parsed_duties.append(asg)
                        self.tree_past.insert("", "end", values=(matched_day.name, matched_loc.name, matched_t.name if matched_t else t_cell))

            if self.parsed_duties:
                self.btn_import_past.configure(state="normal")
            else:
                messagebox.showwarning("Uyarı", "Nöbet çizelgesinden geçerli eşleşme bulunamadı.", parent=self)
        except Exception as e:
            logger.error(f"Eski nöbet dosyası okunurken hata: {e}")
            messagebox.showerror("Hata", f"Dosya okunurken hata oluştu:\n{e}", parent=self)

    def _start_past_import(self):
        if not self.parsed_duties:
            return
        week_str = self.target_week_var.get().strip()
        self.db.clear_assignments(week_str)
        for a in self.parsed_duties:
            a.week_start = week_str
            self.db.save_assignment(a)

        messagebox.showinfo("Başarılı", f"{len(self.parsed_duties)} nöbet ataması {week_str} haftasına aktarıldı!", parent=self)
        if self.on_imported:
            self.on_imported()
        self.destroy()

    # ==========================================
    # SEKME 4: NÖBET YERLERİ VE SINIFLAR AKTAR
    # ==========================================
    def _build_locations_tab(self):
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="📍 Nöbet Yerleri")

        self.loc_file_var = tk.StringVar()
        self.parsed_locs: List[str] = []

        f_file = ttk.Frame(tab)
        f_file.pack(fill="x", pady=(0, 10))
        ttk.Label(f_file, text="Dosya Seç:", font=(FONT_FAMILY, 9, "bold")).pack(side="left", padx=(0, 6))
        ttk.Entry(f_file, textvariable=self.loc_file_var, font=(FONT_FAMILY, 9)).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(f_file, text="Gözat (.xlsx / .csv)...", command=self._browse_loc_file).pack(side="left")

        ttk.Label(
            tab,
            text="💡 Format: İlk sütunda 'Bahçe 1', 'Bahçe 2', '1. Kat', '2. Kat' gibi nöbet yerleri listesi.",
            font=(FONT_FAMILY, 8),
            foreground=COLOR_TEXT_MUTED
        ).pack(anchor="w", pady=(0, 8))

        self.tree_locs = ttk.Treeview(tab, columns=("name",), show="headings", height=10)
        self.tree_locs.heading("name", text="Nöbet Yeri Adı", anchor="w")
        self.tree_locs.column("name", width=400, anchor="w")
        self.tree_locs.pack(fill="both", expand=True, pady=(0, 10))

        btn_bar = ttk.Frame(tab)
        btn_bar.pack(fill="x")
        self.btn_import_locs = ttk.Button(btn_bar, text="✔ Nöbet Yerlerini Aktar", style="Primary.TButton", state="disabled", command=self._start_loc_import)
        self.btn_import_locs.pack(side="right")

    def _browse_loc_file(self):
        path = filedialog.askopenfilename(
            title="Nöbet Yerleri Listesi Seç",
            filetypes=[("Excel ve CSV", "*.xlsx;*.csv"), ("Excel Dosyaları", "*.xlsx"), ("CSV Dosyaları", "*.csv")],
            parent=self
        )
        if not path:
            return
        self.loc_file_var.set(path)
        self._load_loc_file(Path(path))

    def _load_loc_file(self, file_path: Path):
        self.parsed_locs.clear()
        for item in self.tree_locs.get_children():
            self.tree_locs.delete(item)

        try:
            if file_path.suffix.lower() == ".xlsx":
                wb = openpyxl.load_workbook(file_path, data_only=True)
                ws = wb.active
                for r in ws.iter_rows(values_only=True):
                    if r and r[0]:
                        name = str(r[0]).strip()
                        if name.lower() not in ["nöbet yeri", "yer", "yer adı"]:
                            self.parsed_locs.append(name)
                            self.tree_locs.insert("", "end", values=(name,))
            elif file_path.suffix.lower() == ".csv":
                with open(file_path, "r", encoding="utf-8-sig") as f:
                    for line in f:
                        name = line.strip().split(";")[0].split(",")[0].strip()
                        if name and name.lower() not in ["nöbet yeri", "yer", "yer adı"]:
                            self.parsed_locs.append(name)
                            self.tree_locs.insert("", "end", values=(name,))

            if self.parsed_locs:
                self.btn_import_locs.configure(state="normal")
        except Exception as e:
            logger.error(f"Nöbet yerleri dosyası okunurken hata: {e}")
            messagebox.showerror("Hata", f"Dosya okunurken hata oluştu:\n{e}", parent=self)

    def _start_loc_import(self):
        existing_locs = self.db.get_locations(active_only=False)
        existing_names = [l.name.lower() for l in existing_locs]

        added = 0
        for name in self.parsed_locs:
            if name.lower() not in existing_names:
                new_l = Location(name=name, order_index=len(existing_locs) + added + 1)
                self.db.save_location(new_l)
                existing_names.append(name.lower())
                added += 1

        messagebox.showinfo("Başarılı", f"{added} adet yeni nöbet yeri sisteme eklendi!", parent=self)
        if self.on_imported:
            self.on_imported()
