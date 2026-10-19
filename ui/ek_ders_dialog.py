"""
Ay Sonu İkame ve Ek Ders Tahakkuk İcmali Dialogu
Okulda gelmeyen öğretmenlerin yerine boş derse giren nöbetçi ve branş öğretmenlerinin
aylık ek ders hak edişlerini ve nöbet nezareti saatlerini MEB mevzuatına (Md. 44) göre
özetler, listeler, PDF ve Excel çıktılarını üretir.
"""
import os
import datetime
import webbrowser
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from core.database import Database
from logic.export_service import ExportService
from logic.substitution_service import get_monthly_ek_ders_summary, get_teacher_substitutions_summary
from core.config import EXPORTS_DIR
from core.logger import logger
from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_PRIMARY_HOVER,
    COLOR_SUCCESS, COLOR_DANGER, COLOR_BORDER, COLOR_BORDER_STRONG,
    COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, FONT_FAMILY,
    create_modern_button
)

TURKISH_MONTHS = [
    ("01", "Ocak"),
    ("02", "Şubat"),
    ("03", "Mart"),
    ("04", "Nisan"),
    ("05", "Mayıs"),
    ("06", "Haziran"),
    ("07", "Temmuz"),
    ("08", "Ağustos"),
    ("09", "Eylül"),
    ("10", "Ekim"),
    ("11", "Kasım"),
    ("12", "Aralık")
]


class EkDersMonthlySummaryDialog(tk.Toplevel):
    """
    Ay Sonu İkame & Ek Ders Takip ve Puantaj Penceresi
    """
    def __init__(
        self,
        parent: tk.Widget,
        db: Database,
        initial_month_str: Optional[str] = None,
        on_select_teacher: Optional[Callable[[str], None]] = None
    ):
        super().__init__(parent)
        self.db = db
        self.export_service = ExportService(db)
        self.on_select_teacher = on_select_teacher

        self.title("Ay Sonu İkame ve Ek Ders Tahakkuk İcmali")
        self.geometry("1120x720")
        self.minsize(980, 600)
        self.configure(bg=COLOR_BG)

        # Varsayılan Yıl ve Ay
        now = datetime.datetime.now()
        cur_year = str(now.year)
        cur_month_idx = now.month - 1

        if initial_month_str and "-" in initial_month_str:
            parts = initial_month_str.split("-")
            cur_year = parts[0]
            try:
                cur_month_idx = int(parts[1]) - 1
            except Exception:
                cur_month_idx = now.month - 1

        self.year_var = tk.StringVar(value=cur_year)
        self.month_var = tk.StringVar(value=TURKISH_MONTHS[cur_month_idx][1])
        self.filter_type_var = tk.StringVar(value="Tümü")
        self.search_var = tk.StringVar(value="")

        self.current_summary_data: Dict[str, Any] = {}
        self.selected_teacher_id: Optional[str] = None

        self._build_ui()
        self.refresh_data()

    def _get_current_month_str(self) -> str:
        month_name = self.month_var.get()
        month_num = "10"
        for num, name in TURKISH_MONTHS:
            if name == month_name:
                month_num = num
                break
        return f"{self.year_var.get()}-{month_num}"

    def _build_ui(self):
        # 1. Üst Başlık Kartı
        header_frame = tk.Frame(self, bg="#1E3A8A", padx=20, pady=14)
        header_frame.pack(fill="x", side="top")

        lbl_title = tk.Label(
            header_frame,
            text="💰 AY SONU İKAME DERS VE EK DERS TAKİP MERKEZİ",
            font=(FONT_FAMILY, 13, "bold"),
            bg="#1E3A8A",
            fg="#FFFFFF"
        )
        lbl_title.pack(anchor="w")

        lbl_sub = tk.Label(
            header_frame,
            text="Boş ders ikamelerine giren öğretmenlerin MEB Yönetmeliği (Md. 44) uyarınca ek ders tahakkuk ve nöbet nezareti icmali",
            font=(FONT_FAMILY, 9),
            bg="#1E3A8A",
            fg="#93C5FD"
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # 2. Filtre & Kontrol Çubuğu
        controls_frame = tk.Frame(self, bg=COLOR_CARD, padx=16, pady=10, relief="solid", bd=1)
        controls_frame.pack(fill="x", padx=16, pady=(12, 8))

        # Yıl
        tk.Label(controls_frame, text="Yıl:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, fg=COLOR_TEXT_MAIN).pack(side="left", padx=(0, 4))
        cb_year = ttk.Combobox(controls_frame, textvariable=self.year_var, values=["2024", "2025", "2026", "2027"], width=6, state="readonly")
        cb_year.pack(side="left", padx=(0, 12))
        cb_year.bind("<<ComboboxSelected>>", lambda e: self.refresh_data())

        # Ay
        tk.Label(controls_frame, text="Ay:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, fg=COLOR_TEXT_MAIN).pack(side="left", padx=(0, 4))
        cb_month = ttk.Combobox(controls_frame, textvariable=self.month_var, values=[m[1] for m in TURKISH_MONTHS], width=10, state="readonly")
        cb_month.pack(side="left", padx=(0, 16))
        cb_month.bind("<<ComboboxSelected>>", lambda e: self.refresh_data())

        # Filtre Türü
        tk.Label(controls_frame, text="Görünüm:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, fg=COLOR_TEXT_MAIN).pack(side="left", padx=(0, 4))
        cb_filter = ttk.Combobox(
            controls_frame,
            textvariable=self.filter_type_var,
            values=["Tümü", "⭐ Sadece Ek Ders Hak Edenler", "Sadece Nöbet Nezareti Yapanlar"],
            width=24,
            state="readonly"
        )
        cb_filter.pack(side="left", padx=(0, 16))
        cb_filter.bind("<<ComboboxSelected>>", lambda e: self._populate_table())

        # Arama
        tk.Label(controls_frame, text="🔍 Ara:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, fg=COLOR_TEXT_MAIN).pack(side="left", padx=(0, 4))
        ent_search = ttk.Entry(controls_frame, textvariable=self.search_var, width=18)
        ent_search.pack(side="left", padx=(0, 8))
        self.search_var.trace_add("write", lambda *args: self._populate_table())

        btn_refresh = create_modern_button(controls_frame, text="🔄 Yenile", variant="default", command=self.refresh_data)
        btn_refresh.pack(side="right")

        # 3. KPI İstatistik Kartları (4 Sayaç)
        kpi_container = tk.Frame(self, bg=COLOR_BG)
        kpi_container.pack(fill="x", padx=16, pady=(0, 8))

        self.kpi_cards = {}
        cards_def = [
            ("total_sub", "TOPLAM İKAME SAATİ", "0 Saat", "#1E40AF", "#DBEAFE"),
            ("ek_ders", "EK DERS HAK EDİLEN", "0 Saat ⭐", "#15803D", "#DCFCE7"),
            ("supervision", "NÖBET NEZARETİ (ÜCRETSİZ)", "0 Saat", "#475569", "#F1F5F9"),
            ("eligible_teachers", "EK DERS ALACAK PERSONEL", "0 Kişi", "#B45309", "#FEF3C7"),
        ]

        for key, title, initial_val, text_col, bg_col in cards_def:
            card = tk.Frame(kpi_container, bg=bg_col, relief="solid", bd=1, padx=12, pady=8)
            card.pack(side="left", fill="x", expand=True, padx=4)

            lbl_t = tk.Label(card, text=title, font=(FONT_FAMILY, 8, "bold"), bg=bg_col, fg="#64748B")
            lbl_t.pack(anchor="w")

            lbl_v = tk.Label(card, text=initial_val, font=(FONT_FAMILY, 14, "bold"), bg=bg_col, fg=text_col)
            lbl_v.pack(anchor="w", pady=(2, 0))
            self.kpi_cards[key] = lbl_v

        # 4. Ana Bölünmüş İçerik (Üst: Öğretmen Tablosu, Alt: Seçili Öğretmenin Ders Detayları)
        main_paned = ttk.PanedWindow(self, orient="vertical")
        main_paned.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        # ÜST PANEL: Öğretmenler İcmal Tablosu
        top_frame = ttk.Frame(main_paned)
        main_paned.add(top_frame, weight=3)

        lbl_tbl_title = ttk.Label(top_frame, text="📋 Öğretmen Bazında Aylık İkame ve Ek Ders Puantajı", font=(FONT_FAMILY, 9, "bold"))
        lbl_tbl_title.pack(anchor="w", pady=(0, 4))

        tree_frame = ttk.Frame(top_frame)
        tree_frame.pack(fill="both", expand=True)

        cols = ("name", "branch", "total", "ek_ders", "supervision", "classes", "note")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("name", text="Öğretmen Adı Soyadı")
        self.tree.heading("branch", text="Branşı")
        self.tree.heading("total", text="Toplam İkame")
        self.tree.heading("ek_ders", text="Ek Ders Hak Ediş ⭐")
        self.tree.heading("supervision", text="Nöbet Nezareti")
        self.tree.heading("classes", text="Girdiği Sınıflar")
        self.tree.heading("note", text="Mevzuat Durumu")

        self.tree.column("name", width=190)
        self.tree.column("branch", width=130)
        self.tree.column("total", width=95, anchor="center")
        self.tree.column("ek_ders", width=125, anchor="center")
        self.tree.column("supervision", width=105, anchor="center")
        self.tree.column("classes", width=160)
        self.tree.column("note", width=180)

        sb_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb_y.set)

        self.tree.pack(side="left", fill="both", expand=True)
        sb_y.pack(side="right", fill="y")

        self.tree.tag_configure("eligible", background="#ECFDF5", font=(FONT_FAMILY, 9, "bold"))
        self.tree.tag_configure("even", background="#FFFFFF")
        self.tree.tag_configure("odd", background="#F8FAFC")

        self.tree.bind("<<TreeviewSelect>>", self._on_teacher_selected)
        self.tree.bind("<Double-Button-1>", lambda e: self._go_to_teacher_profile())

        # ALT PANEL: Seçilen Öğretmenin Ders Detayı
        bottom_frame = ttk.Frame(main_paned)
        main_paned.add(bottom_frame, weight=2)

        self.lbl_detail_title = ttk.Label(
            bottom_frame,
            text="🔍 Seçili Öğretmenin Ders Dökümü (Lütfen listeden bir öğretmen seçiniz)",
            font=(FONT_FAMILY, 9, "bold")
        )
        self.lbl_detail_title.pack(anchor="w", pady=(4, 4))

        detail_frame = ttk.Frame(bottom_frame)
        detail_frame.pack(fill="both", expand=True)

        d_cols = ("date", "period", "class", "absent", "absent_branch", "status", "reason")
        self.detail_tree = ttk.Treeview(detail_frame, columns=d_cols, show="headings", selectmode="browse")

        self.detail_tree.heading("date", text="Tarih")
        self.detail_tree.heading("period", text="Ders")
        self.detail_tree.heading("class", text="Sınıf")
        self.detail_tree.heading("absent", text="Gelmeyen Öğretmen")
        self.detail_tree.heading("absent_branch", text="Gelmeyen Branş")
        self.detail_tree.heading("status", text="Ek Ders Durumu")
        self.detail_tree.heading("reason", text="Gerekçe / Açıklama")

        self.detail_tree.column("date", width=90, anchor="center")
        self.detail_tree.column("period", width=55, anchor="center")
        self.detail_tree.column("class", width=75, anchor="center")
        self.detail_tree.column("absent", width=150)
        self.detail_tree.column("absent_branch", width=120)
        self.detail_tree.column("status", width=120, anchor="center")
        self.detail_tree.column("reason", width=180)

        sb_d = ttk.Scrollbar(detail_frame, orient="vertical", command=self.detail_tree.yview)
        self.detail_tree.configure(yscrollcommand=sb_d.set)

        self.detail_tree.pack(side="left", fill="both", expand=True)
        sb_d.pack(side="right", fill="y")

        self.detail_tree.tag_configure("ek_yes", background="#DCFCE7")
        self.detail_tree.tag_configure("ek_no", background="#F8FAFC")

        # 5. Alt Aksiyon Barı
        action_bar = tk.Frame(self, bg=COLOR_BG, padx=16, pady=8)
        action_bar.pack(fill="x", side="bottom")

        self.btn_go_profile = create_modern_button(
            action_bar,
            text="👤 Seçili Öğretmen Profiline Git",
            variant="default",
            command=self._go_to_teacher_profile
        )
        self.btn_go_profile.pack(side="left", padx=(0, 8))

        create_modern_button(
            action_bar,
            text="Kapat",
            variant="default",
            command=self.destroy
        ).pack(side="right")

        create_modern_button(
            action_bar,
            text="📊 Excel Puantaj Tablosu (.xlsx)",
            variant="success",
            command=self.export_excel
        ).pack(side="right", padx=(0, 8))

        create_modern_button(
            action_bar,
            text="📄 MEB Resmi İcmal PDF'i (.pdf)",
            variant="primary",
            command=self.export_pdf
        ).pack(side="right", padx=(0, 8))

    def refresh_data(self):
        month_str = self._get_current_month_str()
        self.current_summary_data = get_monthly_ek_ders_summary(self.db, month_str)

        # KPI Sayaçlarını Güncelle
        self.kpi_cards["total_sub"].configure(text=f"{self.current_summary_data['total_hours']} Saat")
        self.kpi_cards["ek_ders"].configure(text=f"{self.current_summary_data['total_ek_ders_hours']} Saat ⭐")
        self.kpi_cards["supervision"].configure(text=f"{self.current_summary_data['total_supervision_hours']} Saat")
        self.kpi_cards["eligible_teachers"].configure(text=f"{self.current_summary_data['eligible_teacher_count']} Kişi")

        self._populate_table()

    def _populate_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        filter_type = self.filter_type_var.get()
        query = self.search_var.get().strip().lower()

        teachers = self.current_summary_data.get("teachers", [])

        row_count = 0
        for st in teachers:
            # Filtreleme
            if filter_type == "⭐ Sadece Ek Ders Hak Edenler" and st["ek_ders_hours"] <= 0:
                continue
            if filter_type == "Sadece Nöbet Nezareti Yapanlar" and st["ek_ders_hours"] > 0:
                continue

            if query and (query not in st["teacher_name"].lower() and query not in st["branch"].lower()):
                continue

            is_eligible = st["ek_ders_hours"] > 0
            ek_text = f"{st['ek_ders_hours']} Saat ⭐" if is_eligible else "0"
            mevzuat = "MEB Yön. Md. 44 (Ek Ders Hak Eder)" if is_eligible else "Nöbet Gözetim Görevi"

            tag = "eligible" if is_eligible else ("even" if row_count % 2 == 0 else "odd")

            self.tree.insert(
                "",
                "end",
                values=(
                    st["teacher_name"],
                    st["branch"] or "-",
                    f"{st['total_substitutions']} Saat",
                    ek_text,
                    f"{st['supervision_hours']} Saat",
                    st["classes_str"],
                    mevzuat
                ),
                tags=(st["teacher_id"], tag)
            )
            row_count += 1

        # Eğer listede eleman varsa ilkini seç
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children[0])
            self._on_teacher_selected()
        else:
            self._clear_details()

    def _on_teacher_selected(self, event=None):
        sel = self.tree.selection()
        if not sel:
            self._clear_details()
            return

        t_id = self.tree.item(sel[0], "tags")[0]
        self.selected_teacher_id = t_id

        # Öğretmenin detaylarını bul
        st = next((item for item in self.current_summary_data.get("teachers", []) if item["teacher_id"] == t_id), None)
        if not st:
            self._clear_details()
            return

        self.lbl_detail_title.configure(
            text=f"🔍 {st['teacher_name']} ({st['branch']}) — Girdiği Derslerin Detayları (Toplam: {st['total_substitutions']} Saat, Ek Ders: {st['ek_ders_hours']} Saat)"
        )

        for item in self.detail_tree.get_children():
            self.detail_tree.delete(item)

        for d in st["details"]:
            status_text = "⭐ Ek Ders Hak Etti" if d["is_ek_ders"] else "Nöbet Nezareti"
            tag = "ek_yes" if d["is_ek_ders"] else "ek_no"

            self.detail_tree.insert(
                "",
                "end",
                values=(
                    d["date_str"],
                    f"{d['period']}. Ders",
                    d["class_name"] or "-",
                    d["absent_teacher_name"],
                    d["absent_teacher_branch"],
                    status_text,
                    d["reason"]
                ),
                tags=(tag,)
            )

    def _clear_details(self):
        self.selected_teacher_id = None
        self.lbl_detail_title.configure(text="🔍 Seçili Öğretmenin Ders Dökümü (Kayıt bulunamadı)")
        for item in self.detail_tree.get_children():
            self.detail_tree.delete(item)

    def _go_to_teacher_profile(self):
        if not self.selected_teacher_id:
            messagebox.showinfo("Bilgi", "Lütfen profilini incelemek için bir öğretmen seçiniz.", parent=self)
            return

        if self.on_select_teacher:
            t_id = self.selected_teacher_id
            self.destroy()
            self.on_select_teacher(t_id)

    def export_excel(self):
        month_str = self._get_current_month_str()
        default_name = f"Ay_Sonu_Ek_Ders_Icmali_{month_str}.xlsx"
        path = filedialog.asksaveasfilename(
            title="Ek Ders İcmali Excel Olarak Kaydet",
            initialdir=str(EXPORTS_DIR),
            initialfile=default_name,
            filetypes=[("Excel Dosyası", "*.xlsx")],
            parent=self
        )
        if not path:
            return

        try:
            out_p = self.export_service.export_monthly_ek_ders_excel(month_str, Path(path))
            if messagebox.askyesno("Başarılı", f"Ek ders icmali başarıyla kaydedildi:\n{out_p}\n\nDosyayı şimdi açmak ister misiniz?", parent=self):
                try:
                    os.startfile(str(out_p))
                except Exception:
                    webbrowser.open(str(out_p))
        except Exception as e:
            logger.error(f"Excel export error: {e}", exc_info=True)
            messagebox.showerror("Hata", f"Excel çıktısı oluşturulurken hata oluştu:\n{e}", parent=self)

    def export_pdf(self):
        month_str = self._get_current_month_str()
        default_name = f"Ay_Sonu_Ek_Ders_Icmali_{month_str}.pdf"
        path = filedialog.asksaveasfilename(
            title="MEB Resmi Ek Ders İcmali PDF Kaydet",
            initialdir=str(EXPORTS_DIR),
            initialfile=default_name,
            filetypes=[("PDF Dosyası", "*.pdf")],
            parent=self
        )
        if not path:
            return

        try:
            out_p = self.export_service.export_monthly_ek_ders_pdf(month_str, Path(path))
            if messagebox.askyesno("Başarılı", f"Resmi MEB ek ders icmali başarıyla oluşturuldu:\n{out_p}\n\nPDF belgesini şimdi açmak ister misiniz?", parent=self):
                try:
                    os.startfile(str(out_p))
                except Exception:
                    webbrowser.open(str(out_p))
        except Exception as e:
            logger.error(f"PDF export error: {e}", exc_info=True)
            messagebox.showerror("Hata", f"PDF çıktısı oluşturulurken hata oluştu:\n{e}", parent=self)
