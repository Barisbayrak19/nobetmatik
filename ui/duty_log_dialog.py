"""
Resmi MEB Günlük Nöbet Defteri ve Kontrol Raporu Penceresi
Günlük nöbetçi öğretmenler, devamsızlıklar, ikame dersler, emniyet kontrolleri ve olay tutanaklarını
resmi A4 defter sayfası ve haftalık toplu kitapçık olarak dışa aktarır.
"""
import os
import subprocess
import datetime
from pathlib import Path
from typing import Optional, List, Dict
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from core.database import Database
from logic.export_service import ExportService
from core.config import EXPORTS_DIR
from core.logger import logger
from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_SUCCESS,
    COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, FONT_FAMILY, create_modern_button
)


class DutyLogDialog(ctk.CTkToplevel):
    def __init__(self, parent: tk.Widget, db: Database, initial_date: Optional[str] = None):
        super().__init__(parent)
        self.db = db
        self.export_service = ExportService(self.db)
        self.school = self.db.get_school_info()

        self.title("📖 Resmi Günlük Nöbet Defteri ve Kontrol Raporu")
        self.geometry("780x680")
        self.minsize(720, 600)
        self.configure(fg_color=COLOR_BG)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        today = datetime.date.today()
        self.selected_date = datetime.date.fromisoformat(initial_date) if initial_date else today
        self.day_names_tr = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

        self._build_ui()
        self._refresh_day_preview()

    def _build_ui(self):
        # 1. Alt Sabit Çıktı Butonları Barı
        bottom_bar = ctk.CTkFrame(
            self,
            fg_color="#FFFFFF",
            height=60,
            corner_radius=0,
            border_width=1,
            border_color="#E2E8F0"
        )
        bottom_bar.pack(fill="x", side="bottom")
        bottom_bar.pack_propagate(False)

        btn_cancel = ctk.CTkButton(
            bottom_bar,
            text="Kapat",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            fg_color="#F1F5F9",
            hover_color="#E2E8F0",
            text_color="#475569",
            width=100,
            height=38,
            corner_radius=8,
            command=self.destroy
        )
        btn_cancel.pack(side="left", padx=16, pady=11)

        btn_week = ctk.CTkButton(
            bottom_bar,
            text="📑 5 Günlük Haftalık Kitapçık (.pdf)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color="#0F766E",
            hover_color="#115E59",
            text_color="#FFFFFF",
            height=38,
            corner_radius=8,
            command=self._export_weekly_pdf
        )
        btn_week.pack(side="right", padx=(0, 16), pady=11)

        btn_single = ctk.CTkButton(
            bottom_bar,
            text="📄 Seçili Günün Nöbet Defteri (.pdf)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            text_color="#FFFFFF",
            height=38,
            corner_radius=8,
            command=self._export_single_day_pdf
        )
        btn_single.pack(side="right", padx=10, pady=11)

        # 2. Üst Modern Başlık Kartı
        header_card = ctk.CTkFrame(self, fg_color="#0F172A", corner_radius=0)
        header_card.pack(fill="x")

        h_inner = ctk.CTkFrame(header_card, fg_color="transparent")
        h_inner.pack(fill="x", padx=20, pady=14)

        ctk.CTkLabel(
            h_inner,
            text="📖 RESMİ GÜNLÜK NÖBET DEFTERİ VE KONTROL RAPORU",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color="#FFFFFF"
        ).pack(anchor="w")

        desc_txt = (
            "MEB Yönetmeliği gereği nöbetçi idareci ve öğretmenlerin günlük görev teslimi, okul emniyet kontrolleri, "
            "gelmeyen öğretmen ve boş ders ikame durumlarını tek sayfalık resmi A4 tutanağı olarak üretir."
        )
        ctk.CTkLabel(
            h_inner,
            text=desc_txt,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color="#94A3B8",
            wraplength=720,
            justify="left"
        ).pack(anchor="w", pady=(3, 0))

        # 3. Ana İçerik Kaydırılabilir Alan
        scroll_content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll_content.pack(fill="both", expand=True, padx=16, pady=12)

        # KART 1: TARİH VE GÜN SEÇİCİ
        card_date = self._create_card(scroll_content, "📅 Rapor Tarihi ve Çalışma Günü")
        
        row_date = ctk.CTkFrame(card_date, fg_color="transparent")
        row_date.pack(fill="x", pady=6)

        ctk.CTkLabel(
            row_date,
            text="Tarih Seçin:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color="#0F172A",
            width=90,
            anchor="w"
        ).pack(side="left")

        self.date_entry_var = tk.StringVar(value=self.selected_date.strftime("%d.%m.%Y"))
        self.entry_date = ctk.CTkEntry(
            row_date,
            textvariable=self.date_entry_var,
            width=120,
            height=34,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            fg_color="#FFFFFF",
            border_color="#CBD5E1"
        )
        self.entry_date.pack(side="left", padx=(0, 10))
        self.entry_date.bind("<Return>", lambda e: self._on_date_entry_change())

        btn_apply_date = ctk.CTkButton(
            row_date,
            text="Getir",
            width=70,
            height=34,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color="#E2E8F0",
            hover_color="#CBD5E1",
            text_color="#0F172A",
            command=self._on_date_entry_change
        )
        btn_apply_date.pack(side="left", padx=(0, 15))

        # Hızlı Gün Butonları (Pzt, Sal, Çar, Per, Cum)
        lbl_quick = ctk.CTkLabel(
            row_date,
            text="Bu Hafta:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color="#64748B"
        )
        lbl_quick.pack(side="left", padx=(0, 6))

        monday_dt = self.selected_date - datetime.timedelta(days=self.selected_date.weekday())
        self.day_buttons = []
        for d_idx, d_name in enumerate(["Pzt", "Sal", "Çar", "Per", "Cum"]):
            target_d = monday_dt + datetime.timedelta(days=d_idx)
            is_active = (target_d == self.selected_date)
            btn_d = ctk.CTkButton(
                row_date,
                text=d_name,
                width=50,
                height=32,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                fg_color=COLOR_PRIMARY if is_active else "#F1F5F9",
                hover_color=COLOR_PRIMARY_HOVER if is_active else "#E2E8F0",
                text_color="#FFFFFF" if is_active else "#334155",
                corner_radius=6,
                command=lambda d=target_d: self._select_date(d)
            )
            btn_d.pack(side="left", padx=2)
            self.day_buttons.append((target_d, btn_d))

        # KART 2: CANLI ÖZET VE NÖBETÇİ KADROSU
        self.card_summary = self._create_card(scroll_content, "👥 Günlük Görevli ve Devamsızlık Özeti")
        self.lbl_summary_info = ctk.CTkLabel(
            self.card_summary,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color="#334155",
            justify="left",
            anchor="w"
        )
        self.lbl_summary_info.pack(fill="x", pady=(2, 6))

        # Nöbetçiler Tablosu / Listesi
        self.frame_teachers_list = ctk.CTkFrame(self.card_summary, fg_color="#F8FAFC", corner_radius=6, border_width=1, border_color="#E2E8F0")
        self.frame_teachers_list.pack(fill="x", pady=4, padx=2)

        # KART 3: MEYDANA GELEN OLAYLAR VE AÇIKLAMA (OPSİYONEL)
        card_notes = self._create_card(
            scroll_content,
            "📝 Nöbet Esnasında Meydana Gelen Olaylar ve Alınan Tedbirler",
            "İsteğe bağlı: Nöbet günü özel bir durum veya resmi olay tutanağı varsa yazabilirsiniz. Boş bırakırsanız nöbetçi öğretmenlerin elle yazabilmesi için resmi noktalı satırlar basılır."
        )
        self.txt_notes = ctk.CTkTextbox(
            card_notes,
            height=85,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            fg_color="#FFFFFF",
            border_width=1,
            border_color="#CBD5E1",
            corner_radius=6
        )
        self.txt_notes.pack(fill="x", pady=6)

    def _create_card(self, parent, title: str, subtitle: str = "") -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E2E8F0"
        )
        card.pack(fill="x", pady=(0, 10))

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color="#0F172A"
        ).pack(anchor="w")

        if subtitle:
            ctk.CTkLabel(
                header,
                text=subtitle,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color="#64748B",
                wraplength=680,
                justify="left"
            ).pack(anchor="w", pady=(2, 0))

        sep = ctk.CTkFrame(card, fg_color="#F1F5F9", height=1)
        sep.pack(fill="x", padx=14, pady=(0, 6))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=16, pady=(2, 12))
        return body

    def _select_date(self, d: datetime.date):
        self.selected_date = d
        self.date_entry_var.set(d.strftime("%d.%m.%Y"))
        self._refresh_day_buttons()
        self._refresh_day_preview()

    def _on_date_entry_change(self):
        val = self.date_entry_var.get().strip()
        try:
            parts = val.split(".")
            if len(parts) == 3:
                d = datetime.date(int(parts[2]), int(parts[1]), int(parts[0]))
                self._select_date(d)
                return
        except Exception:
            pass
        messagebox.showwarning("Geçersiz Tarih", "Lütfen GG.AA.YYYY formatında geçerli bir tarih giriniz (Örn: 21.10.2026).", parent=self)

    def _refresh_day_buttons(self):
        for target_d, btn in self.day_buttons:
            is_active = (target_d == self.selected_date)
            btn.configure(
                fg_color=COLOR_PRIMARY if is_active else "#F1F5F9",
                hover_color=COLOR_PRIMARY_HOVER if is_active else "#E2E8F0",
                text_color="#FFFFFF" if is_active else "#334155"
            )

    def _refresh_day_preview(self):
        for w in self.frame_teachers_list.winfo_children():
            w.destroy()

        iso_date = self.selected_date.isoformat()
        tr_date = self.selected_date.strftime("%d.%m.%Y")
        day_name = self.day_names_tr[self.selected_date.weekday()]
        week_start = (self.selected_date - datetime.timedelta(days=self.selected_date.weekday())).isoformat()

        days = self.db.get_days()
        day_map = {d.name: d.id for d in days}
        cur_day_id = day_map.get(day_name)

        locations = {loc.id: loc for loc in self.db.get_locations(active_only=True)}
        teachers = {t.id: t for t in self.db.get_teachers()}

        all_assigns = self.db.get_assignments_for_week(week_start)
        cur_assigns = [a for a in all_assigns if a.day_id == cur_day_id and a.teacher_id]
        cur_assigns.sort(key=lambda a: (getattr(locations.get(a.location_id), 'order_num', 99) if a.location_id in locations else 99, a.slot_index))

        att_records = self.db.get_attendance_records(date_str=iso_date)
        subs = self.db.get_substitutions_for_date(date_str=iso_date)

        summary_text = (
            f"📅 Seçili Gün: {tr_date} {day_name}   |   "
            f"🛡️ Nöbetçi Öğretmen Sayısı: {len(cur_assigns)}   |   "
            f"⚠️ Gelmeyen Öğretmen: {len(att_records)}   |   "
            f"🔄 Boş Ders İkame: {len(subs)}"
        )
        self.lbl_summary_info.configure(text=summary_text)

        # Tablo başlığı
        hdr_row = ctk.CTkFrame(self.frame_teachers_list, fg_color="#1E293B", corner_radius=4)
        hdr_row.pack(fill="x", padx=4, pady=4)
        ctk.CTkLabel(hdr_row, text="Nöbet / Görev Yeri", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#FFFFFF", width=180, anchor="w").pack(side="left", padx=8, pady=4)
        ctk.CTkLabel(hdr_row, text="Nöbetçi Öğretmen", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#FFFFFF", width=220, anchor="w").pack(side="left", padx=8)
        ctk.CTkLabel(hdr_row, text="Branş", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#FFFFFF", width=160, anchor="w").pack(side="left", padx=8)

        if cur_assigns:
            for idx, a in enumerate(cur_assigns):
                loc = locations.get(a.location_id)
                loc_name = loc.name if loc else "-"
                t = teachers.get(a.teacher_id)
                t_name = t.name if t else "-"
                t_branch = t.branch if (t and t.branch) else "-"

                bg_c = "#FFFFFF" if idx % 2 == 0 else "#F8FAFC"
                r = ctk.CTkFrame(self.frame_teachers_list, fg_color=bg_c, corner_radius=2)
                r.pack(fill="x", padx=4, pady=1)
                ctk.CTkLabel(r, text=f"📍 {loc_name}", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#1E293B", width=180, anchor="w").pack(side="left", padx=8, pady=3)
                ctk.CTkLabel(r, text=f"👤 {t_name}", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color="#0F172A", width=220, anchor="w").pack(side="left", padx=8)
                ctk.CTkLabel(r, text=t_branch, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color="#64748B", width=160, anchor="w").pack(side="left", padx=8)
        else:
            no_row = ctk.CTkFrame(self.frame_teachers_list, fg_color="transparent")
            no_row.pack(fill="x", padx=8, pady=8)
            ctk.CTkLabel(
                no_row,
                text="ℹ️ Bu tarihe ait nöbet ataması bulunamadı. Ana ekrandan ilgili haftanın nöbet dağıtımını kontrol ediniz.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color="#94A3B8"
            ).pack(anchor="w")

    def _export_single_day_pdf(self):
        tr_date = self.selected_date.strftime("%d_%m_%Y")
        day_name = self.day_names_tr[self.selected_date.weekday()]
        default_name = f"Nobet_Defteri_{tr_date}_{day_name}.pdf"

        out_path = filedialog.asksaveasfilename(
            title="Günlük Nöbet Defteri PDF Kaydet",
            initialdir=str(EXPORTS_DIR),
            initialfile=default_name,
            filetypes=[("PDF Belgesi", "*.pdf")],
            parent=self
        )
        if not out_path:
            return

        try:
            notes = self.txt_notes.get("1.0", tk.END).strip()
            self.export_service.export_daily_duty_log_pdf(
                date_str=self.selected_date.isoformat(),
                output_path=Path(out_path),
                custom_notes=notes,
                include_full_week=False
            )
            self._notify_success(out_path)
        except Exception as e:
            logger.error(f"Nöbet defteri PDF çıktısı hatası: {e}", exc_info=True)
            messagebox.showerror("Hata", f"PDF belgesi oluşturulurken hata oluştu:\n{e}", parent=self)

    def _export_weekly_pdf(self):
        monday_dt = self.selected_date - datetime.timedelta(days=self.selected_date.weekday())
        friday_dt = monday_dt + datetime.timedelta(days=4)
        range_str = f"{monday_dt.strftime('%d_%m')}_{friday_dt.strftime('%d_%m_%Y')}"
        default_name = f"Haftalik_Nobet_Defteri_{range_str}.pdf"

        out_path = filedialog.asksaveasfilename(
            title="5 Günlük Haftalık Nöbet Defteri Kitapçığı PDF Kaydet",
            initialdir=str(EXPORTS_DIR),
            initialfile=default_name,
            filetypes=[("PDF Belgesi", "*.pdf")],
            parent=self
        )
        if not out_path:
            return

        try:
            notes = self.txt_notes.get("1.0", tk.END).strip()
            self.export_service.export_daily_duty_log_pdf(
                date_str=self.selected_date.isoformat(),
                output_path=Path(out_path),
                custom_notes=notes,
                include_full_week=True
            )
            self._notify_success(out_path)
        except Exception as e:
            logger.error(f"Haftalık nöbet defteri PDF hatası: {e}", exc_info=True)
            messagebox.showerror("Hata", f"PDF belgesi oluşturulurken hata oluştu:\n{e}", parent=self)

    def _notify_success(self, file_path: str):
        p = Path(file_path)
        msg = f"Resmi Nöbet Defteri belgesi başarıyla oluşturuldu:\n\n📁 {p.name}\n\nBelgeyi şimdi açmak ister misiniz?"
        if messagebox.askyesno("Başarılı", msg, parent=self):
            try:
                if os.name == 'nt':
                    os.startfile(p)
                else:
                    subprocess.run(["xdg-open", str(p)])
            except Exception as e:
                logger.warning(f"Belge açılamadı: {e}")
