"""
İlk Kurulum Sihirbazı (Setup Wizard)
Her okulun ve kullanıcının kendi kurumuna göre sıfırdan temiz kurulum yapmasını sağlar.
İsteğe bağlı olarak sistemi hemen incelemek isteyenler için demo verisi yükleme seçeneği sunar.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, Any, List
from core.models import SchoolInfo, Day, Location, Teacher, Assignment
from core.database import Database
from data.reference_data import (
    REFERENCE_SCHOOL, REFERENCE_DAYS, REFERENCE_LOCATIONS,
    REFERENCE_TEACHERS, REFERENCE_DUTY_TABLE
)
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

        # Form Değişkenleri (Temiz başlangıç için boş varsayılanlar)
        self.school_name_var = tk.StringVar(value="")
        self.district_var = tk.StringVar(value="")
        self.city_var = tk.StringVar(value="")
        self.year_var = tk.StringVar(value="2026-2027")
        self.principal_var = tk.StringVar(value="")
        self.school_level_var = tk.StringVar(value="Ortaokul")
        self.education_type_var = tk.StringVar(value="Normal (Tekli)")
        self.daily_periods_var = tk.IntVar(value=7)

        # Kurulum Modu: 0 = Temiz Kurulum (Varsayılan), 1 = Örnek Demo Veriler
        self.setup_mode_var = tk.IntVar(value=0)

        self._build_ui()

    def _build_ui(self):
        # Üst Başlık Banner
        header_frame = tk.Frame(self, bg="#1E293B", height=85)
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
            text="Hoş geldiniz! Okulunuzun nöbet ve ders takip sistemini kurmak için lütfen bilgileri giriniz.",
            font=(FONT_FAMILY, 9),
            fg="#94A3B8",
            bg="#1E293B"
        )
        lbl_sub.pack(pady=(0, 12))

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
            padx=16,
            pady=16,
            relief="solid",
            bd=1
        )
        left_card.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Alanlar
        fields = [
            ("Okul Adı:", self.school_name_var, "Örn: Atatürk Ortaokulu"),
            ("İlçe:", self.district_var, "Örn: Çankaya"),
            ("İl:", self.city_var, "Örn: Ankara"),
            ("Eğitim Öğretim Yılı:", self.year_var, "2026-2027"),
            ("Okul Müdürü:", self.principal_var, "Örn: Ad Soyad"),
        ]

        for i, (label_text, var, hint) in enumerate(fields):
            lbl = tk.Label(left_card, text=label_text, font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, anchor="w")
            lbl.grid(row=i*2, column=0, sticky="w", pady=(4, 2))
            entry = ttk.Entry(left_card, textvariable=var, font=(FONT_FAMILY, 10))
            entry.grid(row=i*2 + 1, column=0, sticky="ew", pady=(0, 4))

        # Ek Kurum Ayarları
        row_offset = len(fields) * 2

        lbl_level = tk.Label(left_card, text="Okul Kademesi:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, anchor="w")
        lbl_level.grid(row=row_offset, column=0, sticky="w", pady=(4, 2))
        cmb_level = ttk.Combobox(
            left_card,
            textvariable=self.school_level_var,
            values=["İlkokul", "Ortaokul", "İmam Hatip Ortaokulu", "Anadolu Lisesi", "Fen Lisesi", "Mesleki ve Teknik Anadolu Lisesi", "Diğer"],
            state="readonly",
            font=(FONT_FAMILY, 9)
        )
        cmb_level.grid(row=row_offset + 1, column=0, sticky="ew", pady=(0, 4))

        lbl_edu = tk.Label(left_card, text="Eğitim Şekli:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, anchor="w")
        lbl_edu.grid(row=row_offset + 2, column=0, sticky="w", pady=(4, 2))
        cmb_edu = ttk.Combobox(
            left_card,
            textvariable=self.education_type_var,
            values=["Normal (Tekli)", "İkili Eğitim (Sabahçı/Öğlenci)"],
            state="readonly",
            font=(FONT_FAMILY, 9)
        )
        cmb_edu.grid(row=row_offset + 3, column=0, sticky="ew", pady=(0, 4))

        lbl_period = tk.Label(left_card, text="Günlük Ders Saati Sayısı:", font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, anchor="w")
        lbl_period.grid(row=row_offset + 4, column=0, sticky="w", pady=(4, 2))
        cmb_period = ttk.Combobox(
            left_card,
            textvariable=self.daily_periods_var,
            values=[6, 7, 8],
            state="readonly",
            font=(FONT_FAMILY, 9)
        )
        cmb_period.grid(row=row_offset + 5, column=0, sticky="ew", pady=(0, 4))

        left_card.columnconfigure(0, weight=1)

        # Sağ Kart: Başlangıç Yapılandırması ve Seçenekler
        right_card = tk.LabelFrame(
            content_frame,
            text=" ⚙️ Başlangıç Yapılandırması ve Kurulum Seçenekleri ",
            font=(FONT_FAMILY, 10, "bold"),
            bg=COLOR_CARD,
            fg=COLOR_PRIMARY,
            padx=16,
            pady=16,
            relief="solid",
            bd=1
        )
        right_card.pack(side="right", fill="both", expand=True, padx=(10, 0))

        # Bilgilendirme ve Standart Tanımlar
        configs = [
            ("Nöbet Günleri:", "Pazartesi - Cuma (5 Gün)"),
            ("Standart Nöbet Alanları:", "Bahçe, Zemin Kat, 1. Kat, 2. Kat (İstediğiniz zaman artırabilirsiniz)"),
            ("Nöbet Mevzuatı:", "MEB Nöbetçi Öğretmen Görev ve Sorumlulukları (Resmi 7 Madde)")
        ]
        for k, v in configs:
            f = tk.Frame(right_card, bg=COLOR_CARD)
            f.pack(fill="x", pady=4)
            tk.Label(f, text=k, font=(FONT_FAMILY, 9, "bold"), bg=COLOR_CARD, fg=COLOR_TEXT_MAIN, width=22, anchor="w").pack(side="left")
            tk.Label(f, text=v, font=(FONT_FAMILY, 9), bg=COLOR_CARD, fg="#2563EB", anchor="w").pack(side="left", fill="x", expand=True)

        sep = ttk.Separator(right_card, orient="horizontal")
        sep.pack(fill="x", pady=12)

        tk.Label(
            right_card,
            text="Başlangıç Veri Seçimi:",
            font=(FONT_FAMILY, 9, "bold"),
            bg=COLOR_CARD,
            fg=COLOR_TEXT_MAIN,
            anchor="w"
        ).pack(fill="x", pady=(0, 6))

        # Radyo Butonları: Temiz vs Demo
        rb_clean = tk.Radiobutton(
            right_card,
            text="✔ Temiz Kurulum (Önerilen)\nSistemi sıfırdan başlat. Öğretmenlerimi ve ders programımı daha sonra Excel veya e-Okul'dan yükleyeceğim.",
            variable=self.setup_mode_var,
            value=0,
            font=(FONT_FAMILY, 9),
            bg=COLOR_CARD,
            fg="#047857",
            activebackground=COLOR_CARD,
            justify="left",
            anchor="w"
        )
        rb_clean.pack(fill="x", pady=4)

        rb_demo = tk.Radiobutton(
            right_card,
            text="🧪 Örnek (Demo) Verilerle Başla\nSistemi hızlıca incelemek için örnek (fictional) öğretmenler ve nöbet şablonu oluştur.",
            variable=self.setup_mode_var,
            value=1,
            font=(FONT_FAMILY, 9),
            bg=COLOR_CARD,
            fg="#475569",
            activebackground=COLOR_CARD,
            justify="left",
            anchor="w"
        )
        rb_demo.pack(fill="x", pady=4)

        # İpucu Kutusu
        tip_frame = tk.Frame(right_card, bg="#F0FDF4", bd=1, relief="solid")
        tip_frame.pack(fill="x", pady=(15, 0), ipady=6, ipadx=8)

        tk.Label(
            tip_frame,
            text="💡 İpucu: Kurulum tamamlandıktan sonra ana ekrandaki 'İçe Aktar' menüsünü kullanarak okulunuzun e-Okul haftalık ders programını ve öğretmen listesini tek tıkla yükleyebilirsiniz.",
            font=(FONT_FAMILY, 8, "italic"),
            bg="#F0FDF4",
            fg="#15803D",
            wraplength=440,
            justify="left"
        ).pack(fill="x")

        # Alt Buton Alanı
        bottom_frame = tk.Frame(self, bg=COLOR_BG, height=60)
        bottom_frame.pack(fill="x", side="bottom", padx=20, pady=15)

        btn_finish = ttk.Button(
            bottom_frame,
            text="✔ Kurulumu Tamamla ve Sistemi Başlat",
            style="Success.TButton",
            command=self._complete_setup
        )
        btn_finish.pack(side="right")

    def _complete_setup(self):
        """
        Kullanıcı tercihlerine göre okul bilgilerini ve başlangıç kayıtlarını veritabanına işler.
        """
        try:
            school_name = self.school_name_var.get().strip() or "Okul Adı Belirtilmedi"
            district = self.district_var.get().strip()
            city = self.city_var.get().strip()
            academic_year = self.year_var.get().strip() or "2026-2027"
            principal = self.principal_var.get().strip()
            level = self.school_level_var.get()
            edu_type = self.education_type_var.get()
            periods = self.daily_periods_var.get()

            # 1. Okul Bilgisi
            school = SchoolInfo(
                name=school_name,
                city=city,
                district=district,
                academic_year=academic_year,
                principal_name=principal,
                school_level=level,
                education_type=edu_type,
                daily_periods=periods,
                duty_rules=REFERENCE_SCHOOL["duty_rules"],
                installed=True
            )
            self.db.save_school_info(school)

            # 2. Günler (Pazartesi - Cuma)
            day_objects: Dict[str, Day] = {}
            for d_data in REFERENCE_DAYS:
                d = Day(name=d_data["name"], order_num=d_data["order_num"])
                self.db.save_day(d)
                day_objects[d.name] = d

            # 3. Nöbet Yerleri (Temel Standart Alanlar)
            loc_objects: Dict[str, Location] = {}
            for loc_data in REFERENCE_LOCATIONS:
                loc = Location(
                    name=loc_data["name"],
                    order_num=loc_data["order_num"],
                    capacity=loc_data["capacity"]
                )
                self.db.save_location(loc)
                loc_objects[loc.name] = loc

            # 4. Öğretmenler ve Atamalar (Sadece Demo Modu Seçildiyse)
            if self.setup_mode_var.get() == 1:
                # Demo Verileri Yükle
                teacher_objects: Dict[str, Teacher] = {}
                for t_data in REFERENCE_TEACHERS:
                    t = Teacher(
                        name=t_data["name"],
                        branch=t_data["branch"],
                        is_active=t_data.get("is_active", True),
                        notes=t_data.get("notes", "")
                    )
                    self.db.save_teacher(t)
                    teacher_objects[t.name] = t

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

                logger.info("Demo verileri ile kurulum tamamlandı.")
                messagebox.showinfo("Kurulum Tamamlandı", f"{school_name} için örnek verilerle kurulum tamamlandı!\nAna yönetim paneline yönlendiriliyorsunuz.")
            else:
                # Temiz Kurulum (Öğretmenler boş, kullanıcı kendi okulunu kuracak)
                logger.info("Temiz veritabanı ile kurulum tamamlandı.")
                messagebox.showinfo(
                    "Kurulum Tamamlandı",
                    f"{school_name} için sistem başarıyla kuruldu!\n\n"
                    "Öğretmenlerinizi ve ders programınızı 'İçe Aktar' menüsünden Excel veya e-Okul dosyasıyla yükleyebilirsiniz."
                )

            self.on_complete()

        except Exception as e:
            logger.error(f"Kurulum sırasında hata: {e}", exc_info=True)
            messagebox.showerror("Hata", f"Kurulum sırasında bir hata oluştu:\n{e}")
