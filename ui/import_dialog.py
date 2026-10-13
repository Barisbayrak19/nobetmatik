"""
Kapsamlı İçe Aktarma Merkezi (Universal Import Center)
Excel (.xlsx), CSV, JSON ve e-Okul PDF formatlarından:
1. Öğretmen Listesi ve Branşlar (Öğretmen ve Alan Bazında Seçim Özgürlüğü ile)
2. Haftalık Öğretmen Ders Programı (Öğretmen, Saat, Sınıf ve Ders Kodu Seçenekleri ile)
3. Geçmiş / Eski Nöbet Çizelgesi (Seçili görevlendirmeler)
4. Nöbet Yerleri ve Sınıf Listesi
kullanıcının seçtiği filtre ve alanlar doğrultusunda esnek ve güvenli aktarılmasını sağlar.
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


class ImportView(ttk.Frame):
    def __init__(self, parent: tk.Widget, db: Database, on_imported: Optional[Callable[[], None]] = None, on_finish: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.db = db
        self.on_imported = on_imported
        self.on_finish = on_finish
        self.sub_service = SubstitutionService(self.db)
        self.duty_service = DutyService(self.db)
        self.asc_service = AscBilsaService(self.db)

        self._build_ui()

    def close_view(self):
        if self.on_finish:
            self.on_finish()
        elif isinstance(self.master, tk.Toplevel):
            self.master.destroy()

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
            text="Dosyadaki tüm veriler yerine sadece istediğiniz öğretmen, ders ve alanları seçerek esnek ve güvenli aktarım yapın.",
            font=(FONT_FAMILY, 9),
            fg="#94A3B8",
            bg="#0F172A"
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        # 2. Notebook (Sekmeler)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=10)

        self._build_teachers_tab()
        self._build_timetables_tab()
        self._build_past_duty_tab()
        self._build_locations_tab()

    # ==========================================
    # GENEL YARDIMCI: SEÇİLEBİLİR TREEVIEW BIND
    # ==========================================
    def _bind_checkable_tree(self, tree: ttk.Treeview, get_item_fn: Callable[[str], Optional[Dict[str, Any]]], on_change_fn: Callable[[], None]):
        """Treeview satırlarına tıklama, çift tıklama veya boşluk tuşu ile ☑️ / ⬜ geçişi sağlar."""
        def toggle_item(item_id: str):
            item_data = get_item_fn(item_id)
            if item_data is not None:
                item_data["selected"] = not item_data.get("selected", True)
                vals = list(tree.item(item_id, "values"))
                if vals:
                    vals[0] = "☑️" if item_data["selected"] else "⬜"
                    tree.item(item_id, values=vals)
                if on_change_fn:
                    on_change_fn()

        def on_click(event):
            col = tree.identify_column(event.x)
            row = tree.identify_row(event.y)
            if row and col == "#1":
                toggle_item(row)

        def on_double_click(event):
            row = tree.identify_row(event.y)
            if row:
                toggle_item(row)

        def on_space(event):
            sel = tree.selection()
            if sel:
                for row in sel:
                    toggle_item(row)
            return "break"

        tree.bind("<Button-1>", on_click, add="+")
        tree.bind("<Double-Button-1>", on_double_click, add="+")
        tree.bind("<space>", on_space, add="+")

    # ==========================================
    # SEKME 1: ÖĞRETMENLER AKTAR
    # ==========================================
    def _build_teachers_tab(self):
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="👥 Öğretmen Listesi")

        self.teacher_file_var = tk.StringVar()
        self.parsed_teachers: List[Dict[str, Any]] = []
        self.teacher_map_by_iid: Dict[str, Dict[str, Any]] = {}
        self.teacher_filter_var = tk.StringVar()
        self.teacher_filter_var.trace_add("write", lambda *_: self._refresh_teachers_tree())

        # Dosya Seçim Alanı
        f_file = ttk.Frame(tab)
        f_file.pack(fill="x", pady=(0, 8))
        ttk.Label(f_file, text="Dosya Seç:", font=(FONT_FAMILY, 9, "bold")).pack(side="left", padx=(0, 6))
        ttk.Entry(f_file, textvariable=self.teacher_file_var, font=(FONT_FAMILY, 9)).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(f_file, text="Gözat (.xlsx / .csv / .pdf)...", command=self._browse_teacher_file).pack(side="left")

        # Aktarılacak Veri Alanları ve Seçenekler (Kart)
        f_fields = ttk.LabelFrame(tab, text="⚙️ Aktarılacak Alanlar ve Kurallar (İstediğinizi Seçin)", padding=8)
        f_fields.pack(fill="x", pady=(0, 8))

        self.teacher_opt_import_branch = tk.BooleanVar(value=True)
        self.teacher_opt_update_existing_branch = tk.BooleanVar(value=True)
        self.teacher_opt_set_active = tk.BooleanVar(value=True)
        self.teacher_opt_skip_existing = tk.BooleanVar(value=False)

        f_opts_row = ttk.Frame(f_fields)
        f_opts_row.pack(fill="x")

        ttk.Checkbutton(
            f_opts_row,
            text="🏷️ Branş Bilgilerini Aktar",
            variable=self.teacher_opt_import_branch
        ).pack(side="left", padx=(0, 15))

        ttk.Checkbutton(
            f_opts_row,
            text="🔄 Mevcut Öğretmenlerin Boş Branşlarını Güncelle",
            variable=self.teacher_opt_update_existing_branch
        ).pack(side="left", padx=(0, 15))

        ttk.Checkbutton(
            f_opts_row,
            text="🟢 Öğretmenleri Varsayılan Olarak 'Aktif' Yap",
            variable=self.teacher_opt_set_active
        ).pack(side="left", padx=(0, 15))

        ttk.Checkbutton(
            f_opts_row,
            text="⏭️ Mevcut Öğretmenleri Atla (Yalnızca Yenileri Ekle)",
            variable=self.teacher_opt_skip_existing
        ).pack(side="left")

        # Araç Çubuğu (Seçim butonları + Filtre + Sayaç)
        f_tools = ttk.Frame(tab)
        f_tools.pack(fill="x", pady=(0, 6))

        ttk.Button(f_tools, text="☑️ Tümünü Seç", command=lambda: self._toggle_all_teachers(True)).pack(side="left", padx=(0, 4))
        ttk.Button(f_tools, text="⬜ Seçimi Kaldır", command=lambda: self._toggle_all_teachers(False)).pack(side="left", padx=(0, 4))
        ttk.Button(f_tools, text="🔄 Tersine Çevir", command=self._invert_teachers_selection).pack(side="left", padx=(0, 12))

        ttk.Label(f_tools, text="🔍 Hızlı Filtre:", font=(FONT_FAMILY, 9)).pack(side="left", padx=(0, 4))
        ttk.Entry(f_tools, textvariable=self.teacher_filter_var, width=22, font=(FONT_FAMILY, 9)).pack(side="left", padx=(0, 12))

        self.lbl_teacher_select_count = ttk.Label(
            f_tools,
            text="Seçilen: 0 / 0 Öğretmen",
            font=(FONT_FAMILY, 9, "bold"),
            foreground=COLOR_PRIMARY
        )
        self.lbl_teacher_select_count.pack(side="right")

        # Önizleme Tablosu
        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill="both", expand=True, pady=(0, 8))

        self.tree_teachers = ttk.Treeview(
            tree_frame,
            columns=("select", "name", "branch"),
            show="headings",
            height=11,
            selectmode="extended"
        )
        self.tree_teachers.heading("select", text="☑️ Seç", anchor="center")
        self.tree_teachers.heading("name", text="Dosyadaki Öğretmen Adı", anchor="w")
        self.tree_teachers.heading("branch", text="Branşı", anchor="w")

        self.tree_teachers.column("select", width=55, minwidth=50, anchor="center")
        self.tree_teachers.column("name", width=360, minwidth=200, anchor="w")
        self.tree_teachers.column("branch", width=280, minwidth=150, anchor="w")

        sb_teach = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_teachers.yview)
        self.tree_teachers.configure(yscrollcommand=sb_teach.set)
        self.tree_teachers.pack(side="left", fill="both", expand=True)
        sb_teach.pack(side="right", fill="y")

        self._bind_checkable_tree(
            self.tree_teachers,
            lambda iid: self.teacher_map_by_iid.get(iid),
            self._update_teacher_selection_count
        )

        # Alt Buton Çubuğu
        btn_bar = ttk.Frame(tab)
        btn_bar.pack(fill="x")

        ttk.Label(
            btn_bar,
            text="💡 Satıra tıklayarak veya Boşluk (Space) tuşuna basarak aktarmak istemediğiniz öğretmenlerin işaretini kaldırabilirsiniz.",
            font=(FONT_FAMILY, 8),
            foreground=COLOR_TEXT_MUTED
        ).pack(side="left")

        self.btn_import_teachers = ttk.Button(
            btn_bar,
            text="✔ Seçili Öğretmenleri İçeri Aktar",
            style="Primary.TButton",
            state="disabled",
            command=self._start_teacher_import
        )
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
        self.teacher_map_by_iid.clear()

        try:
            if file_path.suffix.lower() == ".pdf":
                parsed = self.sub_service.parse_eokul_timetable_pdf(str(file_path))
                for idx, (t_name, t_info) in enumerate(sorted(parsed["teachers"].items())):
                    branch = t_info["branch"]
                    item = {"id": f"t_{idx}", "name": t_name, "branch": branch, "selected": True}
                    self.parsed_teachers.append(item)
                    self.teacher_map_by_iid[item["id"]] = item

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

                count = 0
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
                        item = {"id": f"t_{count}", "name": full_name, "branch": branch, "selected": True}
                        self.parsed_teachers.append(item)
                        self.teacher_map_by_iid[item["id"]] = item
                        count += 1

            elif file_path.suffix.lower() == ".csv":
                with open(file_path, "r", encoding="utf-8-sig") as f:
                    sample = f.read(2048)
                    f.seek(0)
                    delim = ";" if ";" in sample else ","
                    reader = csv.reader(f, delimiter=delim)
                    count = 0
                    for r in reader:
                        if not r or not any(r):
                            continue
                        name = r[0].strip()
                        branch = r[1].strip() if len(r) > 1 else ""
                        if name and name.lower() not in ["adı soyadı", "öğretmen adı", "ad soyad"]:
                            item = {"id": f"t_{count}", "name": name, "branch": branch, "selected": True}
                            self.parsed_teachers.append(item)
                            self.teacher_map_by_iid[item["id"]] = item
                            count += 1

            self._refresh_teachers_tree()

            if self.parsed_teachers:
                self.btn_import_teachers.configure(state="normal")
            else:
                self.btn_import_teachers.configure(state="disabled")
                messagebox.showwarning("Uyarı", "Dosyadan öğretmen verisi okunamadı.", parent=self)
        except Exception as e:
            logger.error(f"Öğretmen dosyası okunurken hata: {e}")
            messagebox.showerror("Hata", f"Dosya okunurken hata oluştu:\n{e}", parent=self)

    def _refresh_teachers_tree(self):
        for item in self.tree_teachers.get_children():
            self.tree_teachers.delete(item)

        q = self.teacher_filter_var.get().strip().lower()
        for t in self.parsed_teachers:
            if not q or q in t["name"].lower() or q in t["branch"].lower():
                icon = "☑️" if t.get("selected", True) else "⬜"
                self.tree_teachers.insert("", "end", iid=t["id"], values=(icon, t["name"], t["branch"]))

        self._update_teacher_selection_count()

    def _update_teacher_selection_count(self):
        total = len(self.parsed_teachers)
        selected = sum(1 for t in self.parsed_teachers if t.get("selected", True))
        self.lbl_teacher_select_count.configure(text=f"Seçilen: {selected} / {total} Öğretmen")
        if selected > 0:
            self.btn_import_teachers.configure(state="normal")
        else:
            self.btn_import_teachers.configure(state="disabled")

    def _toggle_all_teachers(self, select_all: bool):
        q = self.teacher_filter_var.get().strip().lower()
        for t in self.parsed_teachers:
            if not q or q in t["name"].lower() or q in t["branch"].lower():
                t["selected"] = select_all
        self._refresh_teachers_tree()

    def _invert_teachers_selection(self):
        q = self.teacher_filter_var.get().strip().lower()
        for t in self.parsed_teachers:
            if not q or q in t["name"].lower() or q in t["branch"].lower():
                t["selected"] = not t.get("selected", True)
        self._refresh_teachers_tree()

    def _start_teacher_import(self):
        selected_teachers = [t for t in self.parsed_teachers if t.get("selected", True)]
        if not selected_teachers:
            messagebox.showwarning("Uyarı", "Lütfen içeri aktarmak için en az bir öğretmen seçiniz.", parent=self)
            return

        import_branch = self.teacher_opt_import_branch.get()
        update_existing = self.teacher_opt_update_existing_branch.get()
        set_active = self.teacher_opt_set_active.get()
        skip_existing = self.teacher_opt_skip_existing.get()

        existing_teachers = self.db.get_teachers()
        existing_names = [t.name for t in existing_teachers]
        name_to_teacher = {t.name: t for t in existing_teachers}

        imported_count = 0
        matched_count = 0
        skipped_count = 0

        for item in selected_teachers:
            raw_name = item["name"]
            branch = item["branch"] if import_branch else ""

            exact_match = next((t for t in existing_teachers if t.name.lower() == raw_name.lower()), None)
            if exact_match:
                if skip_existing:
                    skipped_count += 1
                    continue
                if update_existing and branch and not exact_match.branch:
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
                    if matched_teacher and update_existing and branch and not matched_teacher.branch:
                        matched_teacher.branch = branch
                        self.db.save_teacher(matched_teacher)
                    matched_count += 1
                elif dlg.decision == "create_new":
                    new_t = Teacher(name=raw_name, branch=branch, is_active=set_active)
                    self.db.save_teacher(new_t)
                    existing_names.append(raw_name)
                    name_to_teacher[raw_name] = new_t
                    imported_count += 1
                else:
                    skipped_count += 1
            else:
                new_t = Teacher(name=raw_name, branch=branch, is_active=set_active)
                self.db.save_teacher(new_t)
                existing_names.append(raw_name)
                name_to_teacher[raw_name] = new_t
                imported_count += 1

        messagebox.showinfo(
            "Başarılı",
            f"Öğretmen İçe Aktarımı Tamamlandı!\n\n"
            f"• Seçilen Öğretmen: {len(selected_teachers)}\n"
            f"• Yeni Eklenen: {imported_count}\n"
            f"• Mevcutla Eşleşen / Güncellenen: {matched_count}\n"
            f"• Atlanan: {skipped_count}",
            parent=self
        )
        if self.on_imported:
            self.on_imported()

    # ==========================================
    # SEKME 2: DERS PROGRAMI AKTAR
    # ==========================================
    def _build_timetables_tab(self):
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="📚 Ders Programı")

        self.timetable_file_var = tk.StringVar()
        self.parsed_lessons: List[TeacherLesson] = []
        self.parsed_tt_teachers: List[Dict[str, Any]] = []
        self.tt_teacher_map_by_iid: Dict[str, Dict[str, Any]] = {}
        self.tt_teacher_filter_var = tk.StringVar()
        self.tt_teacher_filter_var.trace_add("write", lambda *_: self._refresh_tt_teachers_tree())

        # Dosya Seçimi
        f_file = ttk.Frame(tab)
        f_file.pack(fill="x", pady=(0, 6))
        ttk.Label(f_file, text="Dosya Seç:", font=(FONT_FAMILY, 9, "bold")).pack(side="left", padx=(0, 6))
        ttk.Entry(f_file, textvariable=self.timetable_file_var, font=(FONT_FAMILY, 9)).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(f_file, text="Gözat (.xml / .pdf / .xlsx / .csv / .json)...", command=self._browse_timetable_file).pack(side="left")

        # Seçenekler ve Kurallar Paneli (Kart)
        f_opts = ttk.LabelFrame(tab, text="⚙️ Aktarılacak Veri Alanları ve Kurallar (İstediğinizi Seçin)", padding=8)
        f_opts.pack(fill="x", pady=(0, 8))

        self.auto_create_teachers_var = tk.BooleanVar(value=True)
        self.clear_timetables_var = tk.BooleanVar(value=False)
        self.tt_opt_include_classes = tk.BooleanVar(value=True)
        self.tt_opt_include_subjects = tk.BooleanVar(value=True)

        row1 = ttk.Frame(f_opts)
        row1.pack(fill="x", pady=(0, 4))

        ttk.Checkbutton(
            row1,
            text="🏫 Sınıf / Şube Bilgisini Al (Örn: 5-A, 8-B)",
            variable=self.tt_opt_include_classes
        ).pack(side="left", padx=(0, 16))

        ttk.Checkbutton(
            row1,
            text="📖 Ders Adı / Kodunu Al (Örn: MAT, TÜRKÇE)",
            variable=self.tt_opt_include_subjects
        ).pack(side="left", padx=(0, 16))

        ttk.Checkbutton(
            row1,
            text="👤 Programdaki Yeni Öğretmenleri Otomatik Tanımla",
            variable=self.auto_create_teachers_var
        ).pack(side="left")

        row2 = ttk.Frame(f_opts)
        row2.pack(fill="x")

        ttk.Checkbutton(
            row2,
            text="🗑️ Tüm Okulun Mevcut Ders Programını Sıfırla (İşaretlenmezse sadece seçilen öğretmenlerin programı güncellenir)",
            variable=self.clear_timetables_var
        ).pack(side="left")

        ttk.Button(
            row2,
            text="🧹 Sadece Mevcut Programı Temizle",
            command=self._quick_reset_timetables
        ).pack(side="right")

        # Bölünmüş Alan (PanedWindow): Sol -> Öğretmen Seçimi, Sağ -> Ders Detay Önizlemesi
        paned = ttk.PanedWindow(tab, orient="horizontal")
        paned.pack(fill="both", expand=True, pady=(0, 8))

        # --- SOL PANEL: ÖĞRETMEN SEÇİMİ ---
        f_left = ttk.LabelFrame(paned, text="1. Aktarılacak Öğretmenleri Seçin", padding=6)
        paned.add(f_left, weight=1)

        f_left_tools = ttk.Frame(f_left)
        f_left_tools.pack(fill="x", pady=(0, 4))
        ttk.Button(f_left_tools, text="☑️ Tümü", width=6, command=lambda: self._toggle_all_tt_teachers(True)).pack(side="left", padx=(0, 2))
        ttk.Button(f_left_tools, text="⬜ Kaldır", width=6, command=lambda: self._toggle_all_tt_teachers(False)).pack(side="left", padx=(0, 2))
        ttk.Button(f_left_tools, text="🔄 Ters", width=6, command=self._invert_tt_teachers_selection).pack(side="left", padx=(0, 6))

        ttk.Entry(f_left_tools, textvariable=self.tt_teacher_filter_var, font=(FONT_FAMILY, 9)).pack(side="left", fill="x", expand=True)

        f_tree_tt = ttk.Frame(f_left)
        f_tree_tt.pack(fill="both", expand=True, pady=(0, 4))

        self.tree_tt_teachers = ttk.Treeview(
            f_tree_tt,
            columns=("select", "name", "branch", "count"),
            show="headings",
            height=9,
            selectmode="extended"
        )
        self.tree_tt_teachers.heading("select", text="Seç", anchor="center")
        self.tree_tt_teachers.heading("name", text="Öğretmen", anchor="w")
        self.tree_tt_teachers.heading("branch", text="Branş", anchor="w")
        self.tree_tt_teachers.heading("count", text="Saat", anchor="center")

        self.tree_tt_teachers.column("select", width=42, minwidth=40, anchor="center")
        self.tree_tt_teachers.column("name", width=140, minwidth=100, anchor="w")
        self.tree_tt_teachers.column("branch", width=95, minwidth=70, anchor="w")
        self.tree_tt_teachers.column("count", width=55, minwidth=45, anchor="center")

        sb_tt = ttk.Scrollbar(f_tree_tt, orient="vertical", command=self.tree_tt_teachers.yview)
        self.tree_tt_teachers.configure(yscrollcommand=sb_tt.set)
        self.tree_tt_teachers.pack(side="left", fill="both", expand=True)
        sb_tt.pack(side="right", fill="y")

        self._bind_checkable_tree(
            self.tree_tt_teachers,
            lambda iid: self.tt_teacher_map_by_iid.get(iid),
            self._on_tt_teacher_selection_changed
        )

        self.lbl_tt_teachers_status = ttk.Label(
            f_left,
            text="Seçilen: 0 / 0 Öğretmen",
            font=(FONT_FAMILY, 8, "bold"),
            foreground=COLOR_PRIMARY
        )
        self.lbl_tt_teachers_status.pack(anchor="w")

        # --- SAĞ PANEL: DERS DETAYLARI ÖNİZLEMESİ ---
        f_right = ttk.LabelFrame(paned, text="2. Program Önizlemesi (Seçili Öğretmenler)", padding=6)
        paned.add(f_right, weight=2)

        f_tree_dt = ttk.Frame(f_right)
        f_tree_dt.pack(fill="both", expand=True, pady=(0, 4))

        self.tree_timetables = ttk.Treeview(
            f_tree_dt,
            columns=("teacher", "day", "period", "class", "subject", "status"),
            show="headings",
            height=9
        )
        self.tree_timetables.heading("teacher", text="Öğretmen", anchor="w")
        self.tree_timetables.heading("day", text="Gün", anchor="center")
        self.tree_timetables.heading("period", text="Saat", anchor="center")
        self.tree_timetables.heading("class", text="Sınıf", anchor="center")
        self.tree_timetables.heading("subject", text="Ders", anchor="center")
        self.tree_timetables.heading("status", text="Durum", anchor="center")

        self.tree_timetables.column("teacher", width=140, anchor="w")
        self.tree_timetables.column("day", width=85, anchor="center")
        self.tree_timetables.column("period", width=50, anchor="center")
        self.tree_timetables.column("class", width=70, anchor="center")
        self.tree_timetables.column("subject", width=90, anchor="center")
        self.tree_timetables.column("status", width=75, anchor="center")

        sb_dt = ttk.Scrollbar(f_tree_dt, orient="vertical", command=self.tree_timetables.yview)
        self.tree_timetables.configure(yscrollcommand=sb_dt.set)
        self.tree_timetables.pack(side="left", fill="both", expand=True)
        sb_dt.pack(side="right", fill="y")

        self.lbl_timetable_info = ttk.Label(
            f_right,
            text="Henüz dosya seçilmedi.",
            font=(FONT_FAMILY, 8),
            foreground=COLOR_TEXT_MUTED
        )
        self.lbl_timetable_info.pack(anchor="w")

        # Alt Buton Çubuğu
        btn_bar = ttk.Frame(tab)
        btn_bar.pack(fill="x")

        self.btn_import_timetables = ttk.Button(
            btn_bar,
            text="✔ Seçili Ders Programını Aktar",
            style="Primary.TButton",
            state="disabled",
            command=self._start_timetable_import
        )
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
            self.db.clear_teacher_lessons()
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
                ("CSV Dosyaları (*.csv)", "*.csv")
            ],
            parent=self
        )
        if not path:
            return
        self.timetable_file_var.set(path)
        self._load_timetable_file(Path(path))

    def _load_timetable_file(self, file_path: Path):
        self.parsed_lessons.clear()
        self.parsed_tt_teachers.clear()
        self.tt_teacher_map_by_iid.clear()

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
                    l.teacher_id = t_id
                    branch = teachers_dict.get(raw_name.upper(), {}).get("branch", "Genel")
                    l.temp_branch = branch
                    self.parsed_lessons.append(l)

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
                    sched = t_info["schedule"]
                    branch = t_info.get("branch", "Genel")

                    for day_name in days:
                        day_lessons = sched.get(day_name, {})
                        for p_num in range(1, 8):
                            if p_num in day_lessons:
                                c_name, s_name = day_lessons[p_num]
                                is_free = False
                            else:
                                c_name, s_name = "", ""
                                is_free = True

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
                    l.teacher_id = t_id
                    branch = teachers_dict.get(raw_name.upper(), {}).get("branch", "Genel")
                    l.temp_branch = branch
                    self.parsed_lessons.append(l)

            elif file_path.suffix.lower() == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for t_name, days_data in data.items():
                    matched_t = next((t for t in teachers if t.name.lower() in t_name.lower() or t_name.lower() in t.name.lower()), None)
                    t_id = matched_t.id if matched_t else ""

                    for day_name, p_list in days_data.items():
                        for p_idx, item in enumerate(p_list, start=1):
                            if isinstance(item, dict):
                                c_name = item.get("class", "")
                                s_code = item.get("subject", "")
                                is_free = item.get("is_free", False) or not (c_name or s_code)
                            else:
                                is_free = True
                                c_name, s_code = "", ""
                            l = TeacherLesson(
                                teacher_id=t_id,
                                day_name=day_name,
                                period=p_idx,
                                class_name=c_name,
                                subject_code=s_code,
                                is_free=is_free
                            )
                            l.temp_teacher_name = t_name
                            l.temp_branch = "Genel"
                            self.parsed_lessons.append(l)

            # Öğretmen bazında grupla ve özet oluştur
            t_groups: Dict[str, Dict[str, Any]] = {}
            for l in self.parsed_lessons:
                raw = getattr(l, "temp_teacher_name", "") or "Bilinmeyen"
                if raw not in t_groups:
                    t_groups[raw] = {
                        "id": f"tt_t_{len(t_groups)}",
                        "name": raw,
                        "branch": getattr(l, "temp_branch", "Genel") or "Genel",
                        "lesson_count": 0,
                        "selected": True
                    }
                if not l.is_free:
                    t_groups[raw]["lesson_count"] += 1

            self.parsed_tt_teachers = sorted(list(t_groups.values()), key=lambda x: x["name"])
            self.tt_teacher_map_by_iid = {t["id"]: t for t in self.parsed_tt_teachers}

            self._refresh_tt_teachers_tree()
            self._refresh_timetable_preview()

            if self.parsed_lessons:
                self.btn_import_timetables.configure(state="normal")
            else:
                self.btn_import_timetables.configure(state="disabled")
                messagebox.showwarning("Uyarı", "Ders programı verisi okunamadı.", parent=self)
        except Exception as e:
            logger.error(f"Ders programı dosyası okunurken hata: {e}")
            messagebox.showerror("Hata", f"Ders programı okunurken hata oluştu:\n{e}", parent=self)

    def _refresh_tt_teachers_tree(self):
        for item in self.tree_tt_teachers.get_children():
            self.tree_tt_teachers.delete(item)

        q = self.tt_teacher_filter_var.get().strip().lower()
        for t in self.parsed_tt_teachers:
            if not q or q in t["name"].lower() or q in t["branch"].lower():
                icon = "☑️" if t.get("selected", True) else "⬜"
                self.tree_tt_teachers.insert(
                    "", "end",
                    iid=t["id"],
                    values=(icon, t["name"], t["branch"], f"{t['lesson_count']} saat")
                )

        self._update_tt_teachers_status()

    def _on_tt_teacher_selection_changed(self):
        self._update_tt_teachers_status()
        self._refresh_timetable_preview()

    def _update_tt_teachers_status(self):
        total = len(self.parsed_tt_teachers)
        selected = sum(1 for t in self.parsed_tt_teachers if t.get("selected", True))
        selected_lessons = sum(t["lesson_count"] for t in self.parsed_tt_teachers if t.get("selected", True))
        self.lbl_tt_teachers_status.configure(
            text=f"Seçilen: {selected} / {total} Öğretmen (Toplam {selected_lessons} saat ders)"
        )
        if selected > 0:
            self.btn_import_timetables.configure(state="normal")
        else:
            self.btn_import_timetables.configure(state="disabled")

    def _toggle_all_tt_teachers(self, select_all: bool):
        q = self.tt_teacher_filter_var.get().strip().lower()
        for t in self.parsed_tt_teachers:
            if not q or q in t["name"].lower() or q in t["branch"].lower():
                t["selected"] = select_all
        self._refresh_tt_teachers_tree()
        self._refresh_timetable_preview()

    def _invert_tt_teachers_selection(self):
        q = self.tt_teacher_filter_var.get().strip().lower()
        for t in self.parsed_tt_teachers:
            if not q or q in t["name"].lower() or q in t["branch"].lower():
                t["selected"] = not t.get("selected", True)
        self._refresh_tt_teachers_tree()
        self._refresh_timetable_preview()

    def _refresh_timetable_preview(self):
        for item in self.tree_timetables.get_children():
            self.tree_timetables.delete(item)

        selected_names = {t["name"] for t in self.parsed_tt_teachers if t.get("selected", True)}
        shown_count = 0
        total_selected_lessons = 0

        for l in self.parsed_lessons:
            raw_name = getattr(l, "temp_teacher_name", "")
            if raw_name in selected_names:
                total_selected_lessons += 1
                if shown_count < 350:
                    status_txt = "🟢 BOŞ" if l.is_free else "🔴 DOLU"
                    c_txt = l.class_name if self.tt_opt_include_classes.get() else ""
                    s_txt = l.subject_code if self.tt_opt_include_subjects.get() else ""
                    self.tree_timetables.insert(
                        "", "end",
                        values=(raw_name, l.day_name, l.period, c_txt, s_txt, status_txt)
                    )
                    shown_count += 1

        self.lbl_timetable_info.configure(
            text=f"📊 Seçili {len(selected_names)} öğretmene ait toplam {total_selected_lessons} ders saati (İlk {shown_count} kayıt gösteriliyor)"
        )

    def _start_timetable_import(self):
        selected_teacher_infos = [t for t in self.parsed_tt_teachers if t.get("selected", True)]
        selected_names = {t["name"] for t in selected_teacher_infos}

        if not selected_names:
            messagebox.showwarning("Uyarı", "Lütfen ders programını aktarmak için en az bir öğretmen seçiniz.", parent=self)
            return

        parent_ref = self.master
        inc_classes = self.tt_opt_include_classes.get()
        inc_subjects = self.tt_opt_include_subjects.get()
        auto_create = self.auto_create_teachers_var.get()
        clear_all = self.clear_timetables_var.get()

        existing_teachers = self.db.get_teachers()
        existing_map = {t.name.upper(): t for t in existing_teachers}
        new_created_count = 0

        # Yeni öğretmen oluşturma kontrolü
        for t_info in selected_teacher_infos:
            t_name = t_info["name"]
            name_key = t_name.strip().upper()
            matched_t = existing_map.get(name_key)
            if not matched_t:
                for ex_t in existing_teachers:
                    if ex_t.name.upper() in name_key or name_key in ex_t.name.upper():
                        matched_t = ex_t
                        break
            if not matched_t and auto_create:
                new_t = Teacher(name=t_name.strip(), branch=t_info.get("branch", "Genel"), is_active=True)
                self.db.save_teacher(new_t)
                existing_map[name_key] = new_t
                existing_teachers.append(new_t)
                matched_t = new_t
                new_created_count += 1
            if matched_t:
                existing_map[name_key] = matched_t

        # Dersleri filtrele ve öğretmen kimliğini bağla
        lessons_to_save: List[TeacherLesson] = []
        for l in self.parsed_lessons:
            raw_name = getattr(l, "temp_teacher_name", "")
            if raw_name in selected_names:
                name_key = raw_name.strip().upper()
                matched_t = existing_map.get(name_key)
                if not matched_t:
                    for k, v in existing_map.items():
                        if k in name_key or name_key in k:
                            matched_t = v
                            break
                if matched_t:
                    l.teacher_id = matched_t.id
                    if not inc_classes:
                        l.class_name = ""
                    if not inc_subjects:
                        l.subject_code = ""
                    lessons_to_save.append(l)

        if not lessons_to_save:
            messagebox.showwarning(
                "Uyarı",
                "Seçilen öğretmenler sistemde bulunamadı.\n"
                "Lütfen 'Yeni öğretmenleri otomatik tanımla' seçeneğini işaretleyiniz.",
                parent=self
            )
            return

        # Veritabanını güncelle
        if clear_all:
            self.db.clear_teacher_lessons()
        else:
            # Sadece seçilen öğretmenlerin önceki derslerini sıfırla, diğer öğretmenlerin dersleri korunsun!
            target_t_ids = {l.teacher_id for l in lessons_to_save if l.teacher_id}
            for t_id in target_t_ids:
                self.db.clear_teacher_lessons(t_id)

        self.db.save_teacher_lessons_batch(lessons_to_save)

        ask_export = messagebox.askyesno(
            "Başarılı",
            f"Seçili Ders Programı Başarıyla Aktarıldı!\n\n"
            f"• Aktarılan Öğretmen Sayısı: {len(selected_names)}\n"
            f"• Toplam Ders Saati: {len(lessons_to_save)}\n"
            f"• Yeni Oluşturulan Öğretmen: {new_created_count}\n"
            f"• Sınıf Bilgisi: {'Eklendi' if inc_classes else 'Atlandı'}\n"
            f"• Ders Kodu Bilgisi: {'Eklendi' if inc_subjects else 'Atlandı'}\n\n"
            f"Şimdi ders programı çıktılarını (Öğretmen El Programı, Sınıf Programları, Çarşaf Tablo) almak veya incelemek ister misiniz?",
            parent=self
        )
        if self.on_imported:
            self.on_imported()
        self.close_view()
        if ask_export:
            TimetableExportDialog(parent_ref, self.db)

    # ==========================================
    # SEKME 3: ESKİ / GEÇMİŞ NÖBET ÇİZELGESİ AKTAR
    # ==========================================
    def _build_past_duty_tab(self):
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="📋 Eski Nöbet Çizelgesi")

        self.past_file_var = tk.StringVar()
        self.target_week_var = tk.StringVar(value=datetime.date.today().strftime("%Y-%m-%d"))
        self.parsed_duties: List[Dict[str, Any]] = []
        self.past_map_by_iid: Dict[str, Dict[str, Any]] = {}

        f_inputs = ttk.Frame(tab)
        f_inputs.pack(fill="x", pady=(0, 6))

        ttk.Label(f_inputs, text="Hedef Hafta (Pzt):", font=(FONT_FAMILY, 9, "bold")).pack(side="left", padx=(0, 6))
        ttk.Entry(f_inputs, textvariable=self.target_week_var, width=12, font=(FONT_FAMILY, 9)).pack(side="left", padx=(0, 15))

        ttk.Label(f_inputs, text="Nöbet Dosyası:", font=(FONT_FAMILY, 9, "bold")).pack(side="left", padx=(0, 6))
        ttk.Entry(f_inputs, textvariable=self.past_file_var, font=(FONT_FAMILY, 9)).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(f_inputs, text="Gözat (.pdf / .xlsx / .csv)...", command=self._browse_past_file).pack(side="left")

        # Seçenekler
        f_opts = ttk.LabelFrame(tab, text="⚙️ Aktarım Seçenekleri", padding=8)
        f_opts.pack(fill="x", pady=(0, 8))

        self.past_opt_clear_existing = tk.BooleanVar(value=True)
        self.past_opt_registered_only = tk.BooleanVar(value=True)

        ttk.Checkbutton(
            f_opts,
            text="🗑️ Hedef haftadaki mevcut nöbet atamalarını temizle",
            variable=self.past_opt_clear_existing
        ).pack(side="left", padx=(0, 16))

        ttk.Checkbutton(
            f_opts,
            text="👤 Sadece sistemde kayıtlı öğretmenlerin nöbetlerini aktar",
            variable=self.past_opt_registered_only
        ).pack(side="left")

        # Araç çubuğu
        f_tools = ttk.Frame(tab)
        f_tools.pack(fill="x", pady=(0, 6))

        ttk.Button(f_tools, text="☑️ Tümünü Seç", command=lambda: self._toggle_all_past(True)).pack(side="left", padx=(0, 4))
        ttk.Button(f_tools, text="⬜ Seçimi Kaldır", command=lambda: self._toggle_all_past(False)).pack(side="left", padx=(0, 4))
        ttk.Button(f_tools, text="🔄 Tersine Çevir", command=self._invert_past_selection).pack(side="left", padx=(0, 12))

        self.lbl_past_select_count = ttk.Label(
            f_tools,
            text="Seçilen: 0 / 0 Nöbet Görevi",
            font=(FONT_FAMILY, 9, "bold"),
            foreground=COLOR_PRIMARY
        )
        self.lbl_past_select_count.pack(side="right")

        # Önizleme tablosu
        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill="both", expand=True, pady=(0, 8))

        self.tree_past = ttk.Treeview(
            tree_frame,
            columns=("select", "day", "location", "teacher"),
            show="headings",
            height=10,
            selectmode="extended"
        )
        self.tree_past.heading("select", text="☑️ Seç", anchor="center")
        self.tree_past.heading("day", text="Gün", anchor="center")
        self.tree_past.heading("location", text="Nöbet Yeri", anchor="w")
        self.tree_past.heading("teacher", text="Nöbetçi Öğretmen", anchor="w")

        self.tree_past.column("select", width=55, minwidth=50, anchor="center")
        self.tree_past.column("day", width=120, anchor="center")
        self.tree_past.column("location", width=220, anchor="w")
        self.tree_past.column("teacher", width=280, anchor="w")

        sb_past = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_past.yview)
        self.tree_past.configure(yscrollcommand=sb_past.set)
        self.tree_past.pack(side="left", fill="both", expand=True)
        sb_past.pack(side="right", fill="y")

        self._bind_checkable_tree(
            self.tree_past,
            lambda iid: self.past_map_by_iid.get(iid),
            self._update_past_selection_count
        )

        btn_bar = ttk.Frame(tab)
        btn_bar.pack(fill="x")
        self.btn_import_past = ttk.Button(
            btn_bar,
            text="✔ Seçili Nöbet Çizelgesini Aktar",
            style="Primary.TButton",
            state="disabled",
            command=self._start_past_import
        )
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
        self.past_map_by_iid.clear()

        days = self.db.get_days()
        day_map = {d.id: d for d in days}
        locations = self.db.get_locations()
        loc_map = {l.id: l for l in locations}
        teachers = self.db.get_teachers()
        t_map = {t.id: t for t in teachers}
        week_str = self.target_week_var.get().strip() or "2026-09-28"

        try:
            raw_assignments: List[Tuple[Assignment, str, str, str]] = []

            if file_path.suffix.lower() == ".pdf":
                assignments = self.duty_service.parse_duty_table_pdf(str(file_path), week_str)
                for asg in assignments:
                    d_obj = day_map.get(asg.day_id)
                    l_obj = loc_map.get(asg.location_id)
                    t_obj = t_map.get(asg.teacher_id) if asg.teacher_id else None
                    d_name = d_obj.name if d_obj else ""
                    l_name = l_obj.name if l_obj else ""
                    t_name = t_obj.name if t_obj else "Tanımsız Öğretmen"
                    raw_assignments.append((asg, d_name, l_name, t_name))

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

                        matched_loc = next((l for l in locations if l.name.lower() in loc_header.lower() or loc_header.lower() in l.name.lower()), None)
                        if not matched_loc:
                            continue

                        matched_t = next((t for t in teachers if t.name.lower() in t_cell.lower() or t_cell.lower() in t.name.lower()), None)
                        t_id = matched_t.id if matched_t else None

                        asg = Assignment(
                            week_start=week_str,
                            day_id=matched_day.id,
                            location_id=matched_loc.id,
                            teacher_id=t_id
                        )
                        raw_assignments.append((asg, matched_day.name, matched_loc.name, matched_t.name if matched_t else t_cell))

            for idx, (asg, d_name, l_name, t_name) in enumerate(raw_assignments):
                item = {
                    "id": f"p_{idx}",
                    "assignment": asg,
                    "day_name": d_name,
                    "location_name": l_name,
                    "teacher_name": t_name,
                    "selected": True
                }
                self.parsed_duties.append(item)
                self.past_map_by_iid[item["id"]] = item

            self._refresh_past_tree()

            if self.parsed_duties:
                self.btn_import_past.configure(state="normal")
            else:
                self.btn_import_past.configure(state="disabled")
                messagebox.showwarning("Uyarı", "Nöbet çizelgesinden geçerli eşleşme bulunamadı.", parent=self)
        except Exception as e:
            logger.error(f"Eski nöbet dosyası okunurken hata: {e}")
            messagebox.showerror("Hata", f"Dosya okunurken hata oluştu:\n{e}", parent=self)

    def _refresh_past_tree(self):
        for item in self.tree_past.get_children():
            self.tree_past.delete(item)

        for d in self.parsed_duties:
            icon = "☑️" if d.get("selected", True) else "⬜"
            self.tree_past.insert("", "end", iid=d["id"], values=(icon, d["day_name"], d["location_name"], d["teacher_name"]))

        self._update_past_selection_count()

    def _update_past_selection_count(self):
        total = len(self.parsed_duties)
        selected = sum(1 for d in self.parsed_duties if d.get("selected", True))
        self.lbl_past_select_count.configure(text=f"Seçilen: {selected} / {total} Nöbet Görevi")
        if selected > 0:
            self.btn_import_past.configure(state="normal")
        else:
            self.btn_import_past.configure(state="disabled")

    def _toggle_all_past(self, select_all: bool):
        for d in self.parsed_duties:
            d["selected"] = select_all
        self._refresh_past_tree()

    def _invert_past_selection(self):
        for d in self.parsed_duties:
            d["selected"] = not d.get("selected", True)
        self._refresh_past_tree()

    def _start_past_import(self):
        selected_items = [d for d in self.parsed_duties if d.get("selected", True)]
        if not selected_items:
            messagebox.showwarning("Uyarı", "Lütfen aktarmak için en az bir nöbet görevi seçiniz.", parent=self)
            return

        week_str = self.target_week_var.get().strip()
        clear_existing = self.past_opt_clear_existing.get()
        reg_only = self.past_opt_registered_only.get()

        if clear_existing:
            self.db.clear_assignments(week_str)

        saved_count = 0
        for item in selected_items:
            asg: Assignment = item["assignment"]
            if reg_only and not asg.teacher_id:
                continue
            asg.week_start = week_str
            self.db.save_assignment(asg)
            saved_count += 1

        messagebox.showinfo("Başarılı", f"{saved_count} nöbet görevi {week_str} haftasına aktarıldı!", parent=self)
        if self.on_imported:
            self.on_imported()
        self.close_view()

    # ==========================================
    # SEKME 4: NÖBET YERLERİ AKTAR
    # ==========================================
    def _build_locations_tab(self):
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="📍 Nöbet Yerleri")

        self.loc_file_var = tk.StringVar()
        self.parsed_locs: List[Dict[str, Any]] = []
        self.loc_map_by_iid: Dict[str, Dict[str, Any]] = {}

        f_file = ttk.Frame(tab)
        f_file.pack(fill="x", pady=(0, 8))
        ttk.Label(f_file, text="Dosya Seç:", font=(FONT_FAMILY, 9, "bold")).pack(side="left", padx=(0, 6))
        ttk.Entry(f_file, textvariable=self.loc_file_var, font=(FONT_FAMILY, 9)).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(f_file, text="Gözat (.xlsx / .csv)...", command=self._browse_loc_file).pack(side="left")

        # Araç çubuğu
        f_tools = ttk.Frame(tab)
        f_tools.pack(fill="x", pady=(0, 6))

        ttk.Button(f_tools, text="☑️ Tümünü Seç", command=lambda: self._toggle_all_locs(True)).pack(side="left", padx=(0, 4))
        ttk.Button(f_tools, text="⬜ Seçimi Kaldır", command=lambda: self._toggle_all_locs(False)).pack(side="left", padx=(0, 4))
        ttk.Button(f_tools, text="🔄 Tersine Çevir", command=self._invert_locs_selection).pack(side="left", padx=(0, 12))

        self.lbl_loc_select_count = ttk.Label(
            f_tools,
            text="Seçilen: 0 / 0 Nöbet Yeri",
            font=(FONT_FAMILY, 9, "bold"),
            foreground=COLOR_PRIMARY
        )
        self.lbl_loc_select_count.pack(side="right")

        # Önizleme tablosu
        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill="both", expand=True, pady=(0, 8))

        self.tree_locs = ttk.Treeview(
            tree_frame,
            columns=("select", "name"),
            show="headings",
            height=10,
            selectmode="extended"
        )
        self.tree_locs.heading("select", text="☑️ Seç", anchor="center")
        self.tree_locs.heading("name", text="Nöbet Yeri Adı", anchor="w")

        self.tree_locs.column("select", width=55, minwidth=50, anchor="center")
        self.tree_locs.column("name", width=420, minwidth=250, anchor="w")

        sb_loc = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_locs.yview)
        self.tree_locs.configure(yscrollcommand=sb_loc.set)
        self.tree_locs.pack(side="left", fill="both", expand=True)
        sb_loc.pack(side="right", fill="y")

        self._bind_checkable_tree(
            self.tree_locs,
            lambda iid: self.loc_map_by_iid.get(iid),
            self._update_loc_selection_count
        )

        btn_bar = ttk.Frame(tab)
        btn_bar.pack(fill="x")
        self.btn_import_locs = ttk.Button(
            btn_bar,
            text="✔ Seçili Nöbet Yerlerini Aktar",
            style="Primary.TButton",
            state="disabled",
            command=self._start_loc_import
        )
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
        self.loc_map_by_iid.clear()

        try:
            raw_names = []
            if file_path.suffix.lower() == ".xlsx":
                wb = openpyxl.load_workbook(file_path, data_only=True)
                ws = wb.active
                for r in ws.iter_rows(values_only=True):
                    if r and r[0]:
                        name = str(r[0]).strip()
                        if name.lower() not in ["nöbet yeri", "yer", "yer adı"]:
                            raw_names.append(name)
            elif file_path.suffix.lower() == ".csv":
                with open(file_path, "r", encoding="utf-8-sig") as f:
                    for line in f:
                        name = line.strip().split(";")[0].split(",")[0].strip()
                        if name and name.lower() not in ["nöbet yeri", "yer", "yer adı"]:
                            raw_names.append(name)

            for idx, name in enumerate(raw_names):
                item = {"id": f"loc_{idx}", "name": name, "selected": True}
                self.parsed_locs.append(item)
                self.loc_map_by_iid[item["id"]] = item

            self._refresh_loc_tree()

            if self.parsed_locs:
                self.btn_import_locs.configure(state="normal")
            else:
                self.btn_import_locs.configure(state="disabled")
        except Exception as e:
            logger.error(f"Nöbet yerleri dosyası okunurken hata: {e}")
            messagebox.showerror("Hata", f"Dosya okunurken hata oluştu:\n{e}", parent=self)

    def _refresh_loc_tree(self):
        for item in self.tree_locs.get_children():
            self.tree_locs.delete(item)

        for l in self.parsed_locs:
            icon = "☑️" if l.get("selected", True) else "⬜"
            self.tree_locs.insert("", "end", iid=l["id"], values=(icon, l["name"]))

        self._update_loc_selection_count()

    def _update_loc_selection_count(self):
        total = len(self.parsed_locs)
        selected = sum(1 for l in self.parsed_locs if l.get("selected", True))
        self.lbl_loc_select_count.configure(text=f"Seçilen: {selected} / {total} Nöbet Yeri")
        if selected > 0:
            self.btn_import_locs.configure(state="normal")
        else:
            self.btn_import_locs.configure(state="disabled")

    def _toggle_all_locs(self, select_all: bool):
        for l in self.parsed_locs:
            l["selected"] = select_all
        self._refresh_loc_tree()

    def _invert_locs_selection(self):
        for l in self.parsed_locs:
            l["selected"] = not l.get("selected", True)
        self._refresh_loc_tree()

    def _start_loc_import(self):
        selected_items = [l for l in self.parsed_locs if l.get("selected", True)]
        if not selected_items:
            messagebox.showwarning("Uyarı", "Lütfen aktarmak için en az bir nöbet yeri seçiniz.", parent=self)
            return

        existing_locs = self.db.get_locations(active_only=False)
        existing_names = [l.name.lower() for l in existing_locs]

        added = 0
        for item in selected_items:
            name = item["name"]
            if name.lower() not in existing_names:
                new_l = Location(name=name, order_index=len(existing_locs) + added + 1)
                self.db.save_location(new_l)
                existing_names.append(name.lower())
                added += 1

        messagebox.showinfo("Başarılı", f"{added} adet yeni nöbet yeri sisteme eklendi!", parent=self)
        if self.on_imported:
            self.on_imported()


class ImportDialog(tk.Toplevel):
    """Geriye dönük uyumluluk için Toplevel sarmalayıcı."""
    def __init__(self, parent: tk.Widget, db: Database, on_imported: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.title("📥 İçe Aktarma Merkezi (Excel / CSV / JSON / PDF)")
        self.geometry("960x680")
        self.minsize(800, 560)
        self.transient(parent)
        self.view = ImportView(self, db, on_imported=on_imported, on_finish=self.destroy)
        self.view.pack(fill="both", expand=True)

    def __getattr__(self, name):
        if "view" in self.__dict__ and hasattr(self.view, name):
            return getattr(self.view, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
