"""
İlk Kurulum Sihirbazı ve Veri Doğrulama Ekranı
Gerçek okul verilerini önceden doldurur, özetler ve kullanıcı onayıyla veritabanına aktarır.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, Any, List
from core.models import SchoolInfo, Day, Location, Teacher, Assignment
from core.database import Database
from data.reference_data import (
    REFERENCE_SCHOOL, REFERENCE_DAYS, REFERENCE_LOCATIONS,
    REFERENCE_TEACHERS, REFERENCE_DUTY_TABLE, NAME_ALIASES
)
from logic.matching_service import MatchingService
from logic.substitution_service import SubstitutionService
from core.logger import logger
from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_SUCCESS,
    COLOR_BORDER, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, FONT_FAMILY
)

class WizardView(ttk.Frame):
    def __init__(self, parent: tk.Widget, db: Database, on_complete: Callable[[], None]):
        super().__init__(parent)
        self.db = db
        self.on_complete = on_complete

        # Sihirbaz Form Verileri
        self.school_name_var = tk.StringVar(value=REFERENCE_SCHOOL["name"])
        self.district_var = tk.StringVar(value=REFERENCE_SCHOOL["district"])
        self.city_var = tk.StringVar(value=REFERENCE_SCHOOL["city"])
        self.year_var = tk.StringVar(value=REFERENCE_SCHOOL["academic_year"])
        self.principal_var = tk.StringVar(value=REFERENCE_SCHOOL["principal_name"])

        # Eşleştirme ve Çelişki Verileri
        self.detected_conflicts: List[Dict[str, Any]] = []
        self._analyze_reference_data()

        self._build_ui()

    def _analyze_reference_data(self):
        """
        Belgedeki kısaltmalar veya farklı görünen isimleri analiz eder.
        """
        teacher_names = [t["name"] for t in REFERENCE_TEACHERS]
        for alias, real_name in NAME_ALIASES.items():
            if alias != real_name:
                matches = MatchingService.find_best_matches(alias, teacher_names, threshold=0.7)
                self.detected_conflicts.append({
                    "raw": alias,
                    "candidate": real_name,
                    "score": matches[0][1] if matches else 0.85,
                    "decision": real_name # Varsayılan olarak aday
                })

    def _build_ui(self):
        # Üst Başlık Banner
        header_frame = tk.Frame(self, bg="#1E293B", height=80)
        header_frame.pack(fill="x", side="top")

        lbl_top = tk.Label(
            header_frame,
            text="NÖBET YÖNETİM SİSTEMİ - İLK KURULUM SİHİRBAZI",
            font=(FONT_FAMILY, 15, "bold"),
            fg="#FFFFFF",
            bg="#1E293B"
        )
        lbl_top.pack(pady=(15, 2))

        lbl_sub = tk.Label(
            header_frame,
            text="Resmi okul nöbet belgelerinden çıkarılan gerçek veriler önceden yüklenmiştir.",
            font=(FONT_FAMILY, 9),
            fg="#94A3B8",
            bg="#1E293B"
        )
        lbl_sub.pack(pady=(0, 10))

        # Ana İçerik Konteyneri (İki sütunlu kartlar)
        content_frame = ttk.Frame(self, padding=20)
        content_frame.pack(fill="both", expand=True)

        # Sol Kart: Okul ve Kurum Bilgileri
        left_card = tk.LabelFrame(
            content_frame,
            text=" 🏫 Okul ve Kurum Bilgileri ",
            font=(FONT_FAMILY, 10, "bold"),
            bg=COLOR_CARD,
            fg=COLOR_PRIMARY,
            padx=15,
            pady=15,
            relief="solid",
            bd=1
        )
        left_card.pack(side="left", fill="both", expand=True, padx=(0, 10))

        fields = [
            ("Okul Adı:", self.school_name_var),
            ("İlçe:", self.district_var),
            ("İl:", self.city_var),
            ("Eğitim Öğretim Yılı:", self.year_var),
            ("Okul Müdürü:", self.principal_var),
        ]

        for i, (label_text, var) in enumerate(fields):
            lbl = tk.Label(left_card, text=label_text, font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, anchor="w")
            lbl.grid(row=i*2, column=0, sticky="w", pady=(8, 2))
            entry = ttk.Entry(left_card, textvariable=var, font=(FONT_FAMILY, 10))
            entry.grid(row=i*2 + 1, column=0, sticky="ew", pady=(0, 5))
        left_card.columnconfigure(0, weight=1)

        # Sağ Kart: Çıkarılan Verilerin Özeti ve Doğrulama
        right_card = tk.LabelFrame(
            content_frame,
            text=" 📋 Çıkarılan Veri Özeti (VERİLERİ KONTROL ET) ",
            font=(FONT_FAMILY, 10, "bold"),
            bg=COLOR_CARD,
            fg=COLOR_PRIMARY,
            padx=15,
            pady=15,
            relief="solid",
            bd=1
        )
        right_card.pack(side="right", fill="both", expand=True, padx=(10, 0))

        active_count = sum(1 for t in REFERENCE_TEACHERS if t.get("is_active", True))
        passive_count = len(REFERENCE_TEACHERS) - active_count
        stats = [
            ("Öğretmen Sayısı:", f"{len(REFERENCE_TEACHERS)} Öğretmen ({active_count} Aktif Nöbetçi, {passive_count} Muaf/Pasif)"),
            ("Nöbet Yeri Sayısı:", f"{len(REFERENCE_LOCATIONS)} Nöbet Yeri (1. Kat, 2. Kat, 3. Kat, Bahçe 1, Bahçe 2, Zemin Kat)"),
            ("Haftalık Gün Sayısı:", f"{len(REFERENCE_DAYS)} Gün (Pazartesi - Cuma)"),
            ("Mevcut Atama Sayısı:", "30 Haftalık Gerçek Nöbet Görevi"),
            ("Ders Programları:", "35 Öğretmen (Haftalık 7 Saatlik Müfredat ve Boş Dersler)"),
            ("Nöbet Kuralları:", "7 Maddelik Resmi MEB Nöbetçi Öğretmen Görevleri")
        ]

        for i, (k, v) in enumerate(stats):
            f = tk.Frame(right_card, bg=COLOR_CARD)
            f.pack(fill="x", pady=4)
            lbl_k = tk.Label(f, text=k, font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, fg=COLOR_TEXT_MAIN, width=18, anchor="w")
            lbl_k.pack(side="left")
            lbl_v = tk.Label(f, text=v, font=(FONT_FAMILY, 9), bg=COLOR_CARD, fg="#2563EB", anchor="w")
            lbl_v.pack(side="left", fill="x", expand=True)

        # Çelişki / Eşleştirme Bilgisi
        sep = ttk.Separator(right_card, orient="horizontal")
        sep.pack(fill="x", pady=10)

        lbl_alias_title = tk.Label(
            right_card,
            text=f"🔍 Eşleştirilen İsim Kısaltmaları ({len(self.detected_conflicts)} Adet):",
            font=(FONT_FAMILY, 9, "bold"),
            bg=COLOR_CARD,
            fg=COLOR_TEXT_MAIN,
            anchor="w"
        )
        lbl_alias_title.pack(fill="x")

        # Treeview veya Listbox ile kısaltmalar
        tree_frame = ttk.Frame(right_card)
        tree_frame.pack(fill="both", expand=True, pady=5)

        tree = ttk.Treeview(tree_frame, columns=("raw", "matched"), show="headings", height=5)
        tree.heading("raw", text="Belgedeki Gösterim")
        tree.heading("matched", text="Eşleşen Gerçek Öğretmen")
        tree.column("raw", width=130)
        tree.column("matched", width=220)

        for c in self.detected_conflicts[:6]:
            tree.insert("", "end", values=(c["raw"], c["candidate"]))
        tree.pack(side="left", fill="both", expand=True)

        lbl_hint = tk.Label(
            right_card,
            text="* İsimler ve atamalar tam Türkçe karakter uyumuyla SQLite veritabanına aktarılacaktır.",
            font=(FONT_FAMILY, 8, "italic"),
            bg=COLOR_CARD,
            fg=COLOR_TEXT_MUTED
        )
        lbl_hint.pack(fill="x", pady=(5, 0))

        # Alt Buton Alanı
        bottom_frame = tk.Frame(self, bg=COLOR_BG, height=60)
        bottom_frame.pack(fill="x", side="bottom", padx=20, pady=15)

        btn_finish = ttk.Button(
            bottom_frame,
            text="✔ Kurulumu Tamamla ve Verileri Kaydet",
            style="Success.TButton",
            command=self._complete_setup
        )
        btn_finish.pack(side="right")

    def _complete_setup(self):
        """
        Gerçek verileri veritabanına aktarır ve ana ekrana geçer.
        """
        try:
            # 1. Okul Bilgisi
            school = SchoolInfo(
                name=self.school_name_var.get().strip(),
                city=self.city_var.get().strip(),
                district=self.district_var.get().strip(),
                academic_year=self.year_var.get().strip(),
                principal_name=self.principal_var.get().strip(),
                duty_rules=REFERENCE_SCHOOL["duty_rules"],
                installed=True
            )
            self.db.save_school_info(school)

            # 2. Günler
            day_objects: Dict[str, Day] = {}
            for d_data in REFERENCE_DAYS:
                d = Day(name=d_data["name"], order_num=d_data["order_num"])
                self.db.save_day(d)
                day_objects[d.name] = d

            # 3. Nöbet Yerleri
            loc_objects: Dict[str, Location] = {}
            for loc_data in REFERENCE_LOCATIONS:
                loc = Location(
                    name=loc_data["name"],
                    order_num=loc_data["order_num"],
                    capacity=loc_data["capacity"]
                )
                self.db.save_location(loc)
                loc_objects[loc.name] = loc

            # 4. Öğretmenler
            teacher_objects: Dict[str, Teacher] = {}
            for t_data in REFERENCE_TEACHERS:
                t = Teacher(
                    name=t_data["name"],
                    branch=t_data["branch"],
                    is_active=t_data.get("is_active", True),
                    notes=t_data["notes"]
                )
                self.db.save_teacher(t)
                teacher_objects[t.name] = t

            # 5. Atamalar (Referans Haftası: 2026-09-28)
            week_start = "2026-09-28"
            for day_name, loc_assignments in REFERENCE_DUTY_TABLE.items():
                day_obj = day_objects.get(day_name)
                if not day_obj:
                    continue
                for loc_name, teacher_names in loc_assignments.items():
                    loc_obj = loc_objects.get(loc_name)
                    if not loc_obj:
                        continue
                    for slot_idx, t_name in enumerate(teacher_names):
                        # İsmi öğretmen objesiyle eşle
                        teacher_obj = teacher_objects.get(t_name)
                        assign = Assignment(
                            week_start=week_start,
                            day_id=day_obj.id,
                            location_id=loc_obj.id,
                            slot_index=slot_idx,
                            teacher_id=teacher_obj.id if teacher_obj else None,
                            fixed=False
                        )
                        self.db.save_assignment(assign)

            # 6. Öğretmen Ders Programları (35 Öğretmen, 5 Gün, 7 Saat)
            sub_service = SubstitutionService(self.db)
            sub_service.import_timetables_from_json()

            logger.info("İlk kurulum başarıyla veritabanına aktarıldı.")
            messagebox.showinfo("Kurulum Tamamlandı", "Gerçek okul nöbet verileri başarıyla sisteme aktarıldı!")
            self.on_complete()

        except Exception as e:
            logger.error(f"İlk kurulum sırasında hata: {e}", exc_info=True)
            messagebox.showerror("Hata", f"Kurulum sırasında bir hata oluştu:\n{e}")
