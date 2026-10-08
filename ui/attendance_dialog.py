"""
Personel Devam-Devamsızlık Takip Çizelgesi Dialogu (Attendance Dialog)
Gelmeyen/raporlu/izinli öğretmenlerin devam-devamsızlık kayıtlarını listeler,
filtreleme, manuel kayıt ekleme/düzenleme/silme, görevlendirme fişlerini saklama/açma
ve resmi MEB formatında Excel (.xlsx) ile PDF çıktılarını üretir.
"""
import os
import datetime
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Optional, List, Dict, Any

from core.models import Teacher, AttendanceRecord
from core.database import Database
from logic.export_service import ExportService
from logic.substitution_service import SubstitutionService
from core.logger import logger
from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_SECONDARY, COLOR_SUCCESS,
    COLOR_DANGER, COLOR_BORDER, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, FONT_FAMILY
)

class AttendanceRecordEditModal(tk.Toplevel):
    """
    Manuel Devamsızlık Kaydı Ekleme veya Düzenleme Modalı
    """
    def __init__(self, parent: tk.Widget, db: Database, record: Optional[AttendanceRecord] = None, on_saved: Optional[callable] = None):
        super().__init__(parent)
        self.db = db
        self.record = record
        self.on_saved = on_saved

        self.title("Devamsızlık Kaydı Düzenle" if record else "Yeni Devamsızlık Kaydı Ekle")
        self.geometry("540x440")
        self.resizable(False, False)
        self.configure(bg=COLOR_BG)
        self.transient(parent)
        self.grab_set()

        self.teachers = self.db.get_teachers(active_only=False)
        self.teacher_map = {t.name: t for t in self.teachers}
        teacher_names = sorted(list(self.teacher_map.keys()))

        today_str = datetime.date.today().strftime("%Y-%m-%d")

        self.date_var = tk.StringVar(value=record.date_str if record else today_str)
        self.teacher_name_var = tk.StringVar(value=record.teacher_name if record else (teacher_names[0] if teacher_names else ""))
        self.status_var = tk.StringVar(value=record.status if record else "Raporlu")
        self.periods_var = tk.StringVar(value=record.periods_missed if record else "Tüm Gün")
        self.lessons_var = tk.StringVar(value=record.lessons_missed if record else "")
        self.slip_var = tk.StringVar(value=record.slip_path if record else "")
        self.notes_var = tk.StringVar(value=record.notes if record else "")

        self._build_ui(teacher_names)

    def _build_ui(self, teacher_names: List[str]):
        card = tk.LabelFrame(
            self,
            text=" 📝 Devamsızlık ve Ders Bilgileri ",
            font=(FONT_FAMILY, 9, "bold"),
            bg=COLOR_CARD,
            fg=COLOR_TEXT_MAIN,
            padx=15,
            pady=15,
            relief="solid",
            bd=1
        )
        card.pack(fill="both", expand=True, padx=15, pady=15)

        # 1. Tarih
        tk.Label(card, text="Tarih (YYYY-AA-GG):", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=0, column=0, sticky="w", pady=5)
        ent_date = ttk.Entry(card, textvariable=self.date_var, width=28, font=(FONT_FAMILY, 9))
        ent_date.grid(row=0, column=1, sticky="w", pady=5)

        # 2. Öğretmen
        tk.Label(card, text="Öğretmen:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=1, column=0, sticky="w", pady=5)
        cb_teacher = ttk.Combobox(
            card,
            textvariable=self.teacher_name_var,
            values=teacher_names,
            state="readonly",
            width=26,
            font=(FONT_FAMILY, 9)
        )
        cb_teacher.grid(row=1, column=1, sticky="w", pady=5)

        # 3. Durum / Neden
        tk.Label(card, text="Devamsızlık Nedeni:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=2, column=0, sticky="w", pady=5)
        cb_status = ttk.Combobox(
            card,
            textvariable=self.status_var,
            values=["Raporlu", "İzinli", "Sevkli", "Görevli", "Mazeretli"],
            state="readonly",
            width=26,
            font=(FONT_FAMILY, 9)
        )
        cb_status.grid(row=2, column=1, sticky="w", pady=5)

        # 4. Girilmeyen Saatler
        tk.Label(card, text="Girilmeyen Saatler:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=3, column=0, sticky="w", pady=5)
        ent_periods = ttk.Entry(card, textvariable=self.periods_var, width=28, font=(FONT_FAMILY, 9))
        ent_periods.grid(row=3, column=1, sticky="w", pady=5)
        tk.Label(card, text="(Örn: 1, 2, 3)", font=(FONT_FAMILY, 8), fg=COLOR_TEXT_MUTED, bg=COLOR_CARD).grid(row=3, column=2, sticky="w", padx=5)

        # 5. Girilmeyen Şubeler & Dersler
        tk.Label(card, text="Şubeler & Dersler:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=4, column=0, sticky="w", pady=5)
        ent_lessons = ttk.Entry(card, textvariable=self.lessons_var, width=28, font=(FONT_FAMILY, 9))
        ent_lessons.grid(row=4, column=1, sticky="w", pady=5)
        tk.Label(card, text="(Örn: 5-A (MAT), 6-B)", font=(FONT_FAMILY, 8), fg=COLOR_TEXT_MUTED, bg=COLOR_CARD).grid(row=4, column=2, sticky="w", padx=5)

        # 6. Görevlendirme Fişi Yolu
        tk.Label(card, text="Görevlendirme Fişi:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=5, column=0, sticky="w", pady=5)
        f_slip = tk.Frame(card, bg=COLOR_CARD)
        f_slip.grid(row=5, column=1, sticky="w", pady=5)
        ent_slip = ttk.Entry(f_slip, textvariable=self.slip_var, width=20, font=(FONT_FAMILY, 9))
        ent_slip.pack(side="left", padx=(0, 4))
        btn_browse_slip = ttk.Button(f_slip, text="Seç...", width=5, command=self._browse_slip)
        btn_browse_slip.pack(side="left")

        # 7. Açıklama / Not
        tk.Label(card, text="Açıklama / Not:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).grid(row=6, column=0, sticky="w", pady=5)
        ent_notes = ttk.Entry(card, textvariable=self.notes_var, width=28, font=(FONT_FAMILY, 9))
        ent_notes.grid(row=6, column=1, sticky="w", pady=5)

        # Butonlar
        btn_bar = tk.Frame(self, bg=COLOR_BG)
        btn_bar.pack(fill="x", padx=15, pady=(0, 15))

        btn_save = ttk.Button(btn_bar, text="💾 Kaydet", style="Primary.TButton", command=self._save)
        btn_save.pack(side="right", padx=(6, 0))

        btn_cancel = ttk.Button(btn_bar, text="İptal", command=self.destroy)
        btn_cancel.pack(side="right")

    def _browse_slip(self):
        f = filedialog.askopenfilename(
            title="Görevlendirme Fişi Seç",
            filetypes=[("Fiş Belgeleri", "*.pdf;*.html"), ("PDF Dosyaları", "*.pdf"), ("HTML Dosyaları", "*.html")],
            parent=self
        )
        if f:
            self.slip_var.set(f)

    def _save(self):
        date_str = self.date_var.get().strip()
        t_name = self.teacher_name_var.get().strip()
        status = self.status_var.get().strip() or "Raporlu"
        periods = self.periods_var.get().strip() or "Tüm Gün"
        lessons = self.lessons_var.get().strip()
        slip = self.slip_var.get().strip()
        notes = self.notes_var.get().strip()

        if not date_str:
            messagebox.showwarning("Uyarı", "Lütfen bir tarih belirtin.", parent=self)
            return

        try:
            datetime.date.fromisoformat(date_str)
        except Exception:
            messagebox.showwarning("Uyarı", "Tarih biçimi geçersiz! (YYYY-AA-GG şeklinde olmalı)", parent=self)
            return

        t_obj = self.teacher_map.get(t_name)
        teacher_id = t_obj.id if t_obj else ""
        branch = t_obj.branch if t_obj else ""

        rec_id = self.record.id if self.record else None

        rec = AttendanceRecord(
            id=rec_id or str(datetime.datetime.now().timestamp()),
            date_str=date_str,
            teacher_id=teacher_id,
            teacher_name=t_name,
            branch=branch,
            status=status,
            periods_missed=periods,
            lessons_missed=lessons,
            slip_path=slip,
            notes=notes
        )

        self.db.save_attendance_record(rec)
        if self.on_saved:
            self.on_saved()
        self.destroy()


class AttendanceDialog(tk.Toplevel):
    def __init__(self, parent: tk.Widget, db: Database):
        super().__init__(parent)
        self.title("Personel Devam-Devamsızlık Takip Çizelgesi")
        self.geometry("1160x700")
        self.minsize(980, 580)
        self.configure(bg=COLOR_BG)

        self.db = db
        self.export_service = ExportService(db)
        self.sub_service = SubstitutionService(db)

        self.teachers = self.db.get_teachers(active_only=False)
        self.teacher_map = {t.id: t for t in self.teachers}

        # Filtre değişkenleri
        cur_year_month = datetime.date.today().strftime("%Y-%m")
        self.month_filter_var = tk.StringVar(value=cur_year_month)
        self.teacher_filter_var = tk.StringVar(value="Tüm Öğretmenler")
        self.status_filter_var = tk.StringVar(value="Tümü")

        self.records: List[AttendanceRecord] = []

        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        # 1. Üst Başlık (Apple Sleek Titanium Slate)
        top_frame = tk.Frame(self, bg="#0F172A", padx=20, pady=12)
        top_frame.pack(fill="x", side="top")

        lbl_title = tk.Label(
            top_frame,
            text="📅 PERSONEL DEVAM-DEVAMSIZLIK TAKİP VE GÖREVLENDİRME DEFTERİ",
            font=(FONT_FAMILY, 12, "bold"),
            fg="#FFFFFF",
            bg="#0F172A"
        )
        lbl_title.pack(anchor="w")

        lbl_desc = tk.Label(
            top_frame,
            text="Gelmeyen/raporlu öğretmenleri, girilmeyen dersleri ve şubeleri listeler. Arşivlenen görevlendirme fişlerine tek tıkla ulaşabilirsiniz.",
            font=(FONT_FAMILY, 9),
            fg="#94A3B8",
            bg="#0F172A"
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        # 2. Filtre ve Kontrol Çubuğu (Apple Clean Card)
        filter_card = tk.LabelFrame(
            self,
            text=" 🔍 Arama ve Filtreleme Ölçütleri ",
            font=(FONT_FAMILY, 9, "bold"),
            bg=COLOR_CARD,
            fg=COLOR_TEXT_MAIN,
            padx=12,
            pady=10,
            relief="solid",
            bd=1
        )
        filter_card.pack(fill="x", padx=15, pady=(10, 5))

        f_row = tk.Frame(filter_card, bg=COLOR_CARD)
        f_row.pack(fill="x")

        # Ay Seçimi
        tk.Label(f_row, text="Ay (YYYY-AA):", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).pack(side="left", padx=(0, 4))
        months = ["Tümü"]
        now = datetime.date.today()
        for offset in range(-6, 3):
            m_dt = now + datetime.timedelta(days=offset * 30)
            m_str = m_dt.strftime("%Y-%m")
            if m_str not in months:
                months.append(m_str)

        cb_month = ttk.Combobox(
            f_row,
            textvariable=self.month_filter_var,
            values=months,
            width=10,
            font=(FONT_FAMILY, 9)
        )
        cb_month.pack(side="left", padx=(0, 15))
        cb_month.bind("<<ComboboxSelected>>", lambda e: self.refresh_data())

        # Öğretmen Seçimi
        tk.Label(f_row, text="Öğretmen:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).pack(side="left", padx=(0, 4))
        teacher_names = ["Tüm Öğretmenler"] + sorted([t.name for t in self.teachers])
        cb_teacher = ttk.Combobox(
            f_row,
            textvariable=self.teacher_filter_var,
            values=teacher_names,
            state="readonly",
            width=20,
            font=(FONT_FAMILY, 9)
        )
        cb_teacher.pack(side="left", padx=(0, 15))
        cb_teacher.bind("<<ComboboxSelected>>", lambda e: self.refresh_data())

        # Durum Seçimi
        tk.Label(f_row, text="Durum:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD).pack(side="left", padx=(0, 4))
        statuses = ["Tümü", "Raporlu", "İzinli", "Sevkli", "Görevli", "Mazeretli"]
        cb_status = ttk.Combobox(
            f_row,
            textvariable=self.status_filter_var,
            values=statuses,
            state="readonly",
            width=10,
            font=(FONT_FAMILY, 9)
        )
        cb_status.pack(side="left", padx=(0, 15))
        cb_status.bind("<<ComboboxSelected>>", lambda e: self.refresh_data())

        btn_filter = ttk.Button(f_row, text="🔄 Yenile", command=self.refresh_data)
        btn_filter.pack(side="left", padx=4)

        # 3. Eylem Butonları
        action_bar = tk.Frame(self, bg=COLOR_BG)
        action_bar.pack(fill="x", padx=15, pady=(5, 5))

        btn_open_slip = ttk.Button(
            action_bar,
            text="📄 Görevlendirme Fişini Aç",
            style="Primary.TButton",
            command=self.open_slip
        )
        btn_open_slip.pack(side="left", padx=(0, 8))

        btn_add = ttk.Button(action_bar, text="➕ Manuel Kayıt Ekle", command=self.add_record)
        btn_add.pack(side="left", padx=(0, 6))

        btn_edit = ttk.Button(action_bar, text="✏️ Düzenle", command=self.edit_selected_record)
        btn_edit.pack(side="left", padx=(0, 6))

        btn_del = ttk.Button(action_bar, text="🗑️ Kaydı Sil", command=self.delete_selected_record)
        btn_del.pack(side="left", padx=(0, 15))

        btn_excel = ttk.Button(action_bar, text="📊 Excel'e Aktar (.xlsx)", command=self.export_excel)
        btn_excel.pack(side="left", padx=(0, 6))

        btn_pdf = ttk.Button(action_bar, text="📄 Aylık Çizelge Yazdır (PDF)", command=self.export_pdf)
        btn_pdf.pack(side="left", padx=(0, 6))

        # 4. Tablo (Treeview)
        table_container = tk.Frame(self, bg=COLOR_CARD, relief="solid", bd=1)
        table_container.pack(fill="both", expand=True, padx=15, pady=5)

        cols = ("date", "teacher", "branch", "status", "periods", "lessons", "slip", "notes", "created")
        self.tree = ttk.Treeview(table_container, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("date", text="Tarih", anchor="center")
        self.tree.heading("teacher", text="Öğretmen Adı Soyadı", anchor="w")
        self.tree.heading("branch", text="Branşı", anchor="center")
        self.tree.heading("status", text="Durumu", anchor="center")
        self.tree.heading("periods", text="Saatler", anchor="center")
        self.tree.heading("lessons", text="Girmediği Şubeler & Dersler", anchor="w")
        self.tree.heading("slip", text="Görevlendirme Fişi", anchor="center")
        self.tree.heading("notes", text="Açıklama / İkame Notu", anchor="w")
        self.tree.heading("created", text="İşlem Zamanı", anchor="center")

        self.tree.column("date", width=90, anchor="center")
        self.tree.column("teacher", width=175, anchor="w")
        self.tree.column("branch", width=125, anchor="center")
        self.tree.column("status", width=95, anchor="center")
        self.tree.column("periods", width=90, anchor="center")
        self.tree.column("lessons", width=170, anchor="w")
        self.tree.column("slip", width=120, anchor="center")
        self.tree.column("notes", width=180, anchor="w")
        self.tree.column("created", width=110, anchor="center")

        tree_scroll_y = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(table_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        tree_scroll_y.pack(side="right", fill="y")
        tree_scroll_x.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<Double-1>", lambda e: self.open_slip())

        # 5. Alt İstatistik ve Kapatma Çubuğu
        bottom_bar = tk.Frame(self, bg=COLOR_BG, height=45)
        bottom_bar.pack(fill="x", side="bottom", padx=15, pady=(5, 12))

        self.lbl_stats = tk.Label(
            bottom_bar,
            text="Yükleniyor...",
            font=(FONT_FAMILY, 9, "bold"),
            bg=COLOR_BG,
            fg=COLOR_TEXT_MAIN
        )
        self.lbl_stats.pack(side="left")

        btn_close = ttk.Button(bottom_bar, text="Kapat", command=self.destroy)
        btn_close.pack(side="right")

    def refresh_data(self):
        m_filter = self.month_filter_var.get().strip()
        month_param = None if m_filter == "Tümü" or not m_filter else m_filter

        t_filter = self.teacher_filter_var.get().strip()
        teacher_id_param = None
        if t_filter != "Tüm Öğretmenler":
            matched = next((t for t in self.teachers if t.name == t_filter), None)
            if matched:
                teacher_id_param = matched.id

        status_filter = self.status_filter_var.get().strip()

        all_recs = self.db.get_attendance_records(
            month_str=month_param,
            teacher_id=teacher_id_param
        )

        if status_filter != "Tümü":
            self.records = [r for r in all_recs if r.status == status_filter]
        else:
            self.records = all_recs

        for item in self.tree.get_children():
            self.tree.delete(item)

        status_counts = {"Raporlu": 0, "İzinli": 0, "Sevkli": 0, "Görevli": 0, "Mazeretli": 0}

        for r in self.records:
            status_counts[r.status] = status_counts.get(r.status, 0) + 1

            try:
                d_obj = datetime.date.fromisoformat(r.date_str)
                d_str = d_obj.strftime("%d.%m.%Y")
            except Exception:
                d_str = r.date_str

            c_str = r.created_at[:16].replace("T", " ") if r.created_at else "-"

            # Fiş durumu
            has_slip = bool(r.slip_path and os.path.exists(r.slip_path))
            slip_label = "📄 Fişi Aç" if has_slip else "-"

            self.tree.insert(
                "",
                "end",
                iid=r.id,
                values=(d_str, r.teacher_name, r.branch, r.status, r.periods_missed,
                        r.lessons_missed or "-", slip_label, r.notes, c_str)
            )

        summary = (
            f"📊 Toplam Kayıt: {len(self.records)} adet  |  "
            f"Raporlu: {status_counts.get('Raporlu', 0)}  |  "
            f"İzinli: {status_counts.get('İzinli', 0)}  |  "
            f"Sevkli: {status_counts.get('Sevkli', 0)}  |  "
            f"Görevli: {status_counts.get('Görevli', 0)}  |  "
            f"Mazeretli: {status_counts.get('Mazeretli', 0)}"
        )
        self.lbl_stats.configure(text=summary)

    def _get_selected_record(self) -> Optional[AttendanceRecord]:
        sel = self.tree.selection()
        if not sel:
            return None
        rec_id = sel[0]
        return next((r for r in self.records if r.id == rec_id), None)

    def open_slip(self):
        rec = self._get_selected_record()
        if not rec:
            messagebox.showinfo("Bilgi", "Lütfen fişini görüntülemek istediğiniz kaydı tablodan seçin.", parent=self)
            return

        # 1. Kayıtlı fiş yolu var ve dosya mevcut mu?
        if rec.slip_path and os.path.exists(rec.slip_path):
            try:
                if os.name == "nt":
                    os.startfile(rec.slip_path)
                else:
                    webbrowser.open(f"file://{os.path.abspath(rec.slip_path)}")
                return
            except Exception as e:
                logger.error(f"Fiş açılırken hata: {e}")

        # 2. Kayıtlı dosya yoksa, veritabanındaki ikame görevlendirmelerinden anında üretip aç
        subs = self.db.get_substitutions_for_date(rec.date_str)
        matched_subs = [s for s in subs if s.absent_teacher_id == rec.teacher_id or s.absent_teacher_id == rec.id]

        if matched_subs:
            slips_dir = Path("exports/slips")
            slips_dir.mkdir(parents=True, exist_ok=True)
            safe_name = rec.teacher_name.replace(" ", "_")
            out_file = slips_dir / f"Gorevlendirme_{rec.date_str}_{safe_name}.html"
            t_obj = self.teacher_map.get(rec.teacher_id) or Teacher(id=rec.teacher_id, name=rec.teacher_name, branch=rec.branch)
            try:
                self.sub_service.export_substitution_html(
                    output_path=str(out_file),
                    date_str=rec.date_str,
                    day_name="Pazartesi", # default
                    absent_teacher=t_obj,
                    assignments=matched_subs
                )
                rec.slip_path = str(out_file.resolve())
                self.db.save_attendance_record(rec)
                self.refresh_data()
                webbrowser.open(f"file://{out_file.resolve()}")
                return
            except Exception as e:
                logger.error(f"Fiş anlık üretilirken hata: {e}")

        # 3. İkame kaydı da yoksa
        ans = messagebox.askyesno(
            "Fiş Bulunamadı",
            f"'{rec.teacher_name}' isimli öğretmenin {rec.date_str} tarihi için arşivlenmiş görevlendirme fişi bulunamadı.\n\n"
            f"Bu gün için şimdi Boş Ders Görevlendirme Asistanı'nı açmak ister misiniz?",
            parent=self
        )
        if ans:
            from ui.substitution_dialog import SubstitutionDialog
            SubstitutionDialog(self, self.db, current_week_start=rec.date_str)

    def add_record(self):
        AttendanceRecordEditModal(self, self.db, on_saved=self.refresh_data)

    def edit_selected_record(self):
        rec = self._get_selected_record()
        if not rec:
            messagebox.showinfo("Bilgi", "Lütfen düzenlemek için bir kayıt seçin.", parent=self)
            return
        AttendanceRecordEditModal(self, self.db, record=rec, on_saved=self.refresh_data)

    def delete_selected_record(self):
        rec = self._get_selected_record()
        if not rec:
            messagebox.showinfo("Bilgi", "Lütfen silmek için bir kayıt seçin.", parent=self)
            return

        confirm = messagebox.askyesno(
            "Kayıt Silme Onayı",
            f"'{rec.teacher_name}' isimli öğretmenin {rec.date_str} tarihli {rec.status} kaydını silmek istediğinize emin misiniz?",
            parent=self
        )
        if confirm:
            self.db.delete_attendance_record(rec.id)
            self.refresh_data()
            messagebox.showinfo("Başarılı", "Devamsızlık kaydı başarıyla silindi.", parent=self)

    def export_excel(self):
        if not self.records:
            messagebox.showwarning("Uyarı", "Dışa aktarılacak devamsızlık kaydı bulunamadı.", parent=self)
            return

        m_str = self.month_filter_var.get().strip() or "Genel"
        default_file = f"Personel_Devam_Takip_{m_str}.xlsx"
        out_path = filedialog.asksaveasfilename(
            title="Personel Devam Çizelgesini Excel Olarak Kaydet",
            initialfile=default_file,
            defaultextension=".xlsx",
            filetypes=[("Excel Dosyası", "*.xlsx")],
            parent=self
        )
        if not out_path:
            return

        try:
            title = f"PERSONEL DEVAM-DEVAMSIZLIK TAKİP ÇİZELGESİ ({m_str})" if m_str != "Tümü" else "PERSONEL DEVAM-DEVAMSIZLIK TAKİP ÇİZELGESİ"
            self.export_service.export_attendance_excel(
                records=self.records,
                output_path=Path(out_path),
                title=title
            )
            messagebox.showinfo("Başarılı", f"Excel çizelgesi oluşturuldu:\n{out_path}", parent=self)
            if os.name == "nt":
                os.startfile(out_path)
        except Exception as e:
            logger.error(f"Devam takip Excel çıktısı alınırken hata: {e}", exc_info=True)
            messagebox.showerror("Hata", f"Excel belgesi oluşturulamadı:\n{e}", parent=self)

    def export_pdf(self):
        if not self.records:
            messagebox.showwarning("Uyarı", "Dışa aktarılacak devamsızlık kaydı bulunamadı.", parent=self)
            return

        m_str = self.month_filter_var.get().strip() or "Genel"
        default_file = f"Personel_Devam_Takip_{m_str}.pdf"
        out_path = filedialog.asksaveasfilename(
            title="Personel Devam Çizelgesini PDF Olarak Kaydet",
            initialfile=default_file,
            defaultextension=".pdf",
            filetypes=[("PDF Dosyası", "*.pdf")],
            parent=self
        )
        if not out_path:
            return

        try:
            title = f"PERSONEL DEVAM TAKİP ÇİZELGESİ ({m_str})" if m_str != "Tümü" else "PERSONEL DEVAM TAKİP ÇİZELGESİ"
            self.export_service.export_attendance_pdf(
                records=self.records,
                output_path=Path(out_path),
                title=title
            )
            messagebox.showinfo("Başarılı", f"PDF belgesi oluşturuldu:\n{out_path}", parent=self)
            if os.name == "nt":
                os.startfile(out_path)
        except Exception as e:
            logger.error(f"Devam takip PDF çıktısı alınırken hata: {e}", exc_info=True)
            messagebox.showerror("Hata", f"PDF belgesi oluşturulamadı:\n{e}", parent=self)
