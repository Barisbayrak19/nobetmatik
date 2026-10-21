"""
WhatsApp Görevlendirme ve Nöbet Bildirim Merkezi
Boş ders ikamelerini ve nöbet görevlerini öğretmenlere veya Okul WhatsApp Grubuna
tek tıkla göndermek için mesaj şablonları ve WhatsApp Web entegrasyonu sunar.
"""
import urllib.parse
import webbrowser
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from typing import List, Dict, Any, Optional

from core.database import Database
from core.models import Teacher, Location, Assignment
from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_SUCCESS,
    COLOR_BORDER, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, FONT_FAMILY
)

class WhatsAppNotifyDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent: tk.Widget,
        school_name: str,
        date_str: str,
        day_name: str,
        tasks: List[Dict[str, Any]]
    ):
        super().__init__(parent)
        self.school_name = school_name
        self.date_str = date_str
        self.day_name = day_name
        self.tasks = tasks # [{"period": 3, "class": "9-A", "subject": "MAT", "duty_teacher": "Ahmet Y.", "absent_teacher": "Mehmet D.", "phone": "5551234567"}]

        self.title("📱 WhatsApp Görevlendirme Bildirimi")
        self.geometry("780x620")
        self.minsize(680, 500)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        # 1. Başlık Barı (WhatsApp Yeşili Temalı)
        header = ctk.CTkFrame(self, fg_color="#075E54", height=65, corner_radius=0)
        header.pack(fill="x", side="top")

        lbl_head = ctk.CTkLabel(
            header,
            text="📱 WhatsApp Görev Bildirim Merkezi",
            font=(FONT_FAMILY, 15, "bold"),
            text_color="#FFFFFF"
        )
        lbl_head.pack(side="left", padx=20, pady=16)

        lbl_sub = ctk.CTkLabel(
            header,
            text=f"📅 {self.date_str} {self.day_name}",
            font=(FONT_FAMILY, 11),
            text_color="#DCF8C6"
        )
        lbl_sub.pack(side="right", padx=20, pady=16)

        # 2. Ana Gövde
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=15)

        # Üst Bilgi
        ttk_info = ctk.CTkLabel(
            body,
            text="Öğretmenlere bireysel görev mesajı gönderebilir veya tüm günün özetini okul WhatsApp grubunda paylaşabilirsiniz.",
            font=(FONT_FAMILY, 10),
            text_color=COLOR_TEXT_MUTED,
            wraplength=720,
            justify="left"
        )
        ttk_info.pack(anchor="w", pady=(0, 10))

        # Sekmeli Yapı: [1. Okul Grubu Mesajı (Tüm Liste)]  [2. Bireysel Öğretmen Mesajı]
        tabview = ctk.CTkTabview(body)
        tabview.pack(fill="both", expand=True)

        tab_group = tabview.add("👥 Okul Grubu Toplu Özeti")
        tab_single = tabview.add("👤 Bireysel Öğretmen Bildirimi")

        # --- SEKME 1: Okul Grubu Toplu Özeti ---
        group_text = self._generate_group_message()
        
        self.txt_group = ctk.CTkTextbox(tab_group, font=(FONT_FAMILY, 10), wrap="word")
        self.txt_group.pack(fill="both", expand=True, padx=10, pady=(10, 10))
        self.txt_group.insert("1.0", group_text)

        bar_group = ctk.CTkFrame(tab_group, fg_color="transparent")
        bar_group.pack(fill="x", padx=10, pady=(0, 10))

        btn_copy_grp = ctk.CTkButton(
            bar_group,
            text="📋 Metni Kopyala",
            font=(FONT_FAMILY, 10, "bold"),
            fg_color="#334155",
            hover_color="#1E293B",
            command=lambda: self._copy_to_clipboard(self.txt_group.get("1.0", "end-1c"))
        )
        btn_copy_grp.pack(side="left", padx=(0, 10))

        btn_open_grp = ctk.CTkButton(
            bar_group,
            text="🌐 WhatsApp Web'de Aç (Grupta Paylaş)",
            font=(FONT_FAMILY, 10, "bold"),
            fg_color="#25D366",
            hover_color="#128C7E",
            text_color="#FFFFFF",
            command=lambda: self._open_whatsapp(phone="", text=self.txt_group.get("1.0", "end-1c"))
        )
        btn_open_grp.pack(side="left")

        # --- SEKME 2: Bireysel Öğretmen Bildirimi ---
        f_select = ctk.CTkFrame(tab_single, fg_color="transparent")
        f_select.pack(fill="x", padx=10, pady=(10, 8))

        ctk.CTkLabel(f_select, text="Görevlendirilen Öğretmen Seçin:", font=(FONT_FAMILY, 10, "bold")).pack(side="left", padx=(0, 10))

        # Görev alan benzersiz öğretmenler
        duty_teachers = sorted(list(set(t["duty_teacher"] for t in self.tasks if t.get("duty_teacher"))))
        if not duty_teachers:
            duty_teachers = ["(Görevlendirilmiş öğretmen bulunamadı)"]

        self.sel_teacher_var = ctk.StringVar(value=duty_teachers[0])
        self.cmb_teacher = ctk.CTkComboBox(
            f_select,
            values=duty_teachers,
            variable=self.sel_teacher_var,
            width=240,
            command=self._on_teacher_changed
        )
        self.cmb_teacher.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(f_select, text="Telefon (Opsiyonel):", font=(FONT_FAMILY, 10)).pack(side="left", padx=(0, 5))
        self.ent_phone = ctk.CTkEntry(f_select, placeholder_text="05xxxxxxxxx", width=130)
        self.ent_phone.pack(side="left")

        # Bireysel Mesaj Alanı
        self.txt_single = ctk.CTkTextbox(tab_single, font=(FONT_FAMILY, 10), wrap="word")
        self.txt_single.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        bar_single = ctk.CTkFrame(tab_single, fg_color="transparent")
        bar_single.pack(fill="x", padx=10, pady=(0, 10))

        btn_copy_single = ctk.CTkButton(
            bar_single,
            text="📋 Metni Kopyala",
            font=(FONT_FAMILY, 10, "bold"),
            fg_color="#334155",
            hover_color="#1E293B",
            command=lambda: self._copy_to_clipboard(self.txt_single.get("1.0", "end-1c"))
        )
        btn_copy_single.pack(side="left", padx=(0, 10))

        btn_open_single = ctk.CTkButton(
            bar_single,
            text="📱 Bu Öğretmene WhatsApp Gönder",
            font=(FONT_FAMILY, 10, "bold"),
            fg_color="#25D366",
            hover_color="#128C7E",
            text_color="#FFFFFF",
            command=self._send_to_single_teacher
        )
        btn_open_single.pack(side="left")

        # İlk öğretmen mesajını yükle
        self._on_teacher_changed(self.sel_teacher_var.get())

        # 3. Kapat Butonu
        btn_close = ctk.CTkButton(
            self,
            text="Kapat",
            font=(FONT_FAMILY, 10, "bold"),
            fg_color="#64748B",
            hover_color="#475569",
            width=90,
            command=self.destroy
        )
        btn_close.pack(side="bottom", anchor="e", padx=20, pady=(0, 15))

    def _generate_group_message(self) -> str:
        lines = [
            f"📢 *{self.school_name.upper()}*",
            f"📋 *GÜNLÜK BOŞ DERS GÖREVLENDİRME LİSTESİ*",
            f"📅 *Tarih:* {self.date_str} {self.day_name}",
            "────────────────────────",
            ""
        ]
        if not self.tasks:
            lines.append("Bugün için boş ders görevlendirmesi bulunmamaktadır.")
        else:
            lines.append("Sayın Öğretmenlerimiz, bugün boş derslerde görevlendirilen nöbetçi/ikame öğretmen listesi aşağıdadır:")
            lines.append("")
            # Saate göre sırala
            sorted_tasks = sorted(self.tasks, key=lambda x: x.get("period", 1))
            for t in sorted_tasks:
                period = t.get("period", 1)
                cls = t.get("class", "-")
                sbj = t.get("subject", "-")
                duty_t = t.get("duty_teacher", "Atanmadı")
                abs_t = t.get("absent_teacher", "")
                is_ek = " (Ek Ders)" if t.get("is_ek_ders") else ""
                lines.append(f"• *{period}. Saat:* {cls} ({sbj}) ➔ *{duty_t}*{is_ek}")
                if abs_t:
                    lines.append(f"   _(Gelmeyen: {abs_t})_")
            lines.append("")
            lines.append("────────────────────────")
            lines.append("Görevli öğretmenlerimize iyi dersler diler, kolaylıklar dileriz.")
            lines.append(f"*{self.school_name} İdaresi*")

        return "\n".join(lines)

    def _on_teacher_changed(self, teacher_name: str):
        self.txt_single.delete("1.0", "end")
        t_tasks = [t for t in self.tasks if t.get("duty_teacher") == teacher_name]
        if not t_tasks:
            self.txt_single.insert("1.0", f"Sayın {teacher_name},\n\nBugün için adınıza atanmış bir görevlendirme bulunmamaktadır.")
            return

        # Varsa telefon numarasını doldur
        phone = t_tasks[0].get("phone", "")
        self.ent_phone.delete(0, "end")
        if phone:
            self.ent_phone.insert(0, phone)

        lines = [
            f"Sayın *{teacher_name}*,",
            "",
            f"*{self.date_str} {self.day_name}* günü okulumuzda aşağıdaki ders/saatlerde nöbetçi/ikame öğretmen olarak görevlendirildiniz:",
            ""
        ]
        for t in t_tasks:
            period = t.get("period", 1)
            cls = t.get("class", "-")
            sbj = t.get("subject", "-")
            abs_t = t.get("absent_teacher", "")
            is_ek = " [Ek Ders]" if t.get("is_ek_ders") else " [Nöbet Görevi]"
            lines.append(f"• *{period}. Ders:* {cls} - {sbj}{is_ek}")
            if abs_t:
                lines.append(f"  (Gelmeyen Öğretmen: {abs_t})")

        lines.append("")
        lines.append("Bilgilerinize rica eder, iyi dersler dileriz.")
        lines.append(f"*{self.school_name} Okul İdaresi*")

        self.txt_single.insert("1.0", "\n".join(lines))

    def _send_to_single_teacher(self):
        text = self.txt_single.get("1.0", "end-1c").strip()
        phone = self.ent_phone.get().strip()
        # Telefon numarasını temizle (sadece rakamlar)
        clean_phone = "".join(c for c in phone if c.isdigit())
        if clean_phone.startswith("0"):
            clean_phone = "90" + clean_phone[1:]
        elif len(clean_phone) == 10:
            clean_phone = "90" + clean_phone

        self._open_whatsapp(phone=clean_phone, text=text)

    def _open_whatsapp(self, phone: str, text: str):
        encoded_text = urllib.parse.quote(text)
        if phone:
            url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_text}"
        else:
            url = f"https://web.whatsapp.com/send?text={encoded_text}"

        try:
            webbrowser.open(url)
        except Exception as e:
            messagebox.showerror("Hata", f"Tarayıcı açılamadı:\n{e}", parent=self)

    def _copy_to_clipboard(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Kopyalandı", "WhatsApp mesaj metni panoya kopyalandı!\nİstediğiniz sohbet veya gruba yapıştırabilirsiniz (Ctrl+V).", parent=self)


class WhatsAppDutyNoticeDialog(ctk.CTkToplevel):
    """
    Haftalık Nöbet Görevlerini Öğretmenlere veya Okul Grubuna
    WhatsApp üzerinden tek tıkla bildirme merkezi.
    """
    DAY_NAMES_TR = {
        "monday": "Pazartesi",
        "tuesday": "Salı",
        "wednesday": "Çarşamba",
        "thursday": "Perşembe",
        "friday": "Cuma"
    }

    def __init__(
        self,
        parent: tk.Widget,
        db: Database,
        week_start: str,
        initial_teacher_id: Optional[str] = None
    ):
        super().__init__(parent)
        self.db = db
        self.week_start = week_start
        self.initial_teacher_id = initial_teacher_id

        school = self.db.get_school_info()
        self.school_name = school.name or "Okul İdaresi"

        self.teachers = self.db.get_teachers(active_only=True)
        self.teachers_map = {t.id: t for t in self.teachers}
        self.locations = self.db.get_locations()
        self.locations_map = {loc.id: loc.name for loc in self.locations}
        self.assignments = self.db.get_assignments_for_week(self.week_start)

        self.title("📱 Haftalık Nöbet WhatsApp Bildirim Merkezi")
        self.geometry("820x640")
        self.minsize(700, 520)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        # 1. Başlık Barı
        header = ctk.CTkFrame(self, fg_color="#075E54", height=65, corner_radius=0)
        header.pack(fill="x", side="top")

        lbl_head = ctk.CTkLabel(
            header,
            text="📱 Haftalık Nöbet WhatsApp Bildirim Merkezi",
            font=(FONT_FAMILY, 15, "bold"),
            text_color="#FFFFFF"
        )
        lbl_head.pack(side="left", padx=20, pady=16)

        lbl_sub = ctk.CTkLabel(
            header,
            text=f"📅 Hafta: {self.week_start}",
            font=(FONT_FAMILY, 11),
            text_color="#DCF8C6"
        )
        lbl_sub.pack(side="right", padx=20, pady=16)

        # 2. Ana Gövde
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=15)

        tabview = ctk.CTkTabview(body)
        tabview.pack(fill="both", expand=True)

        tab_single = tabview.add("👤 Bireysel Nöbet Bildirimi")
        tab_group = tabview.add("👥 Haftalık Okul Grubu Çizelgesi")

        # --- SEKME 1: Bireysel Bildirim ---
        f_select = ctk.CTkFrame(tab_single, fg_color="transparent")
        f_select.pack(fill="x", padx=10, pady=(10, 8))

        ctk.CTkLabel(f_select, text="Öğretmen Seçin:", font=(FONT_FAMILY, 10, "bold")).pack(side="left", padx=(0, 10))

        teacher_names = [t.name for t in sorted(self.teachers, key=lambda x: x.name)]
        if not teacher_names:
            teacher_names = ["(Öğretmen bulunamadı)"]

        # Varsayılan öğretmen seçimi
        default_name = teacher_names[0]
        if self.initial_teacher_id and self.initial_teacher_id in self.teachers_map:
            default_name = self.teachers_map[self.initial_teacher_id].name

        self.sel_teacher_var = ctk.StringVar(value=default_name)
        self.cmb_teacher = ctk.CTkComboBox(
            f_select,
            values=teacher_names,
            variable=self.sel_teacher_var,
            width=240,
            command=self._on_teacher_changed
        )
        self.cmb_teacher.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(f_select, text="Telefon:", font=(FONT_FAMILY, 10)).pack(side="left", padx=(0, 5))
        self.ent_phone = ctk.CTkEntry(f_select, placeholder_text="05xxxxxxxxx", width=130)
        self.ent_phone.pack(side="left", padx=(0, 8))

        btn_save_phone = ctk.CTkButton(
            f_select,
            text="💾 No Kaydet",
            font=(FONT_FAMILY, 9),
            width=75,
            height=28,
            fg_color="#475569",
            hover_color="#334155",
            command=self._save_teacher_phone
        )
        btn_save_phone.pack(side="left")

        # Mesaj Alanı
        self.txt_single = ctk.CTkTextbox(tab_single, font=(FONT_FAMILY, 10), wrap="word")
        self.txt_single.pack(fill="both", expand=True, padx=10, pady=(8, 10))

        bar_single = ctk.CTkFrame(tab_single, fg_color="transparent")
        bar_single.pack(fill="x", padx=10, pady=(0, 10))

        btn_copy_single = ctk.CTkButton(
            bar_single,
            text="📋 Metni Kopyala",
            font=(FONT_FAMILY, 10, "bold"),
            fg_color="#334155",
            hover_color="#1E293B",
            command=lambda: self._copy_to_clipboard(self.txt_single.get("1.0", "end-1c"))
        )
        btn_copy_single.pack(side="left", padx=(0, 10))

        btn_open_single = ctk.CTkButton(
            bar_single,
            text="📱 Öğretmene WhatsApp Gönder",
            font=(FONT_FAMILY, 10, "bold"),
            fg_color="#25D366",
            hover_color="#128C7E",
            text_color="#FFFFFF",
            command=self._send_to_single_teacher
        )
        btn_open_single.pack(side="left")

        # --- SEKME 2: Okul Grubu Haftalık Çizelge ---
        group_text = self._generate_group_weekly_message()
        self.txt_group = ctk.CTkTextbox(tab_group, font=(FONT_FAMILY, 10), wrap="word")
        self.txt_group.pack(fill="both", expand=True, padx=10, pady=(10, 10))
        self.txt_group.insert("1.0", group_text)

        bar_group = ctk.CTkFrame(tab_group, fg_color="transparent")
        bar_group.pack(fill="x", padx=10, pady=(0, 10))

        btn_copy_grp = ctk.CTkButton(
            bar_group,
            text="📋 Metni Kopyala",
            font=(FONT_FAMILY, 10, "bold"),
            fg_color="#334155",
            hover_color="#1E293B",
            command=lambda: self._copy_to_clipboard(self.txt_group.get("1.0", "end-1c"))
        )
        btn_copy_grp.pack(side="left", padx=(0, 10))

        btn_open_grp = ctk.CTkButton(
            bar_group,
            text="🌐 WhatsApp Web'de Aç (Grupta Paylaş)",
            font=(FONT_FAMILY, 10, "bold"),
            fg_color="#25D366",
            hover_color="#128C7E",
            text_color="#FFFFFF",
            command=lambda: self._open_whatsapp(phone="", text=self.txt_group.get("1.0", "end-1c"))
        )
        btn_open_grp.pack(side="left")

        # Kapat Butonu
        btn_close = ctk.CTkButton(
            self,
            text="Kapat",
            font=(FONT_FAMILY, 10, "bold"),
            fg_color="#64748B",
            hover_color="#475569",
            width=90,
            command=self.destroy
        )
        btn_close.pack(side="bottom", anchor="e", padx=20, pady=(0, 15))

        # İlk öğretmeni yükle
        self._on_teacher_changed(self.sel_teacher_var.get())

    def _get_teacher_by_name(self, name: str) -> Optional[Teacher]:
        for t in self.teachers:
            if t.name == name:
                return t
        return None

    def _save_teacher_phone(self):
        t_name = self.sel_teacher_var.get()
        t = self._get_teacher_by_name(t_name)
        if not t:
            return
        new_phone = self.ent_phone.get().strip()
        t.phone = new_phone
        self.db.save_teacher(t)
        messagebox.showinfo("Kayıt", f"{t.name} telefon numarası güncellendi.", parent=self)

    def _on_teacher_changed(self, teacher_name: str):
        self.txt_single.delete("1.0", "end")
        t = self._get_teacher_by_name(teacher_name)
        if not t:
            return

        self.ent_phone.delete(0, "end")
        if t.phone:
            self.ent_phone.insert(0, t.phone)

        # Bu öğretmenin haftalık nöbetleri
        t_assignments = [a for a in self.assignments if a.teacher_id == t.id]

        lines = [
            f"Sayın *{t.name}*,",
            "",
            f"*{self.week_start}* haftası nöbet görevi bilgileriniz aşağıdadır:",
            ""
        ]

        if not t_assignments:
            lines.append("Bu hafta için planlanmış bir nöbet göreviniz bulunmamaktadır.")
        else:
            for a in t_assignments:
                day_tr = self.DAY_NAMES_TR.get(a.day_id, a.day_id)
                loc_name = self.locations_map.get(a.location_id, "Nöbet Yeri")
                lines.append(f"📅 *Gün:* {day_tr}")
                lines.append(f"📍 *Nöbet Alanı:* {loc_name}")
                lines.append("")

            lines.append("Nöbet günü ders başlangıcından en az 15 dakika önce okulda hazır bulunmanız, nöbet defterini imzalamanız ve görev alanınızda öğrencileri gözetlemeniz rica olunur.")

        lines.append("")
        lines.append("İyi dersler ve başarılı bir hafta dileriz.")
        lines.append(f"*{self.school_name} İdaresi*")

        self.txt_single.insert("1.0", "\n".join(lines))

    def _generate_group_weekly_message(self) -> str:
        lines = [
            f"📢 *{self.school_name.upper()}*",
            f"📋 *HAFTALIK ÖĞRETMEN NÖBET ÇİZELGESİ*",
            f"📅 *Hafta Başlangıcı:* {self.week_start}",
            "────────────────────────",
            ""
        ]

        day_order = ["monday", "tuesday", "wednesday", "thursday", "friday"]
        has_any = False

        for day_id in day_order:
            day_tr = self.DAY_NAMES_TR.get(day_id, day_id).upper()
            day_assignments = [a for a in self.assignments if a.day_id == day_id]
            if not day_assignments:
                continue

            has_any = True
            lines.append(f"📌 *{day_tr}*")
            for a in day_assignments:
                loc_name = self.locations_map.get(a.location_id, "Nöbet")
                t_name = self.teachers_map[a.teacher_id].name if a.teacher_id in self.teachers_map else "Boş"
                lines.append(f"  • *{loc_name}:* {t_name}")
            lines.append("")

        if not has_any:
            lines.append("Bu hafta için nöbet çizelgesi henüz oluşturulmamıştır.")

        lines.append("────────────────────────")
        lines.append("Tüm nöbetçi öğretmenlerimize görevlerinde kolaylıklar ve iyi dersler dileriz.")
        lines.append(f"*{self.school_name} İdaresi*")

        return "\n".join(lines)

    def _send_to_single_teacher(self):
        text = self.txt_single.get("1.0", "end-1c").strip()
        phone = self.ent_phone.get().strip()
        clean_phone = "".join(c for c in phone if c.isdigit())
        if clean_phone.startswith("0"):
            clean_phone = "90" + clean_phone[1:]
        elif len(clean_phone) == 10:
            clean_phone = "90" + clean_phone

        self._open_whatsapp(phone=clean_phone, text=text)

    def _open_whatsapp(self, phone: str, text: str):
        encoded_text = urllib.parse.quote(text)
        if phone:
            url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_text}"
        else:
            url = f"https://web.whatsapp.com/send?text={encoded_text}"

        try:
            webbrowser.open(url)
        except Exception as e:
            messagebox.showerror("Hata", f"Tarayıcı açılamadı:\n{e}", parent=self)

    def _copy_to_clipboard(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Kopyalandı", "WhatsApp mesaj metni panoya kopyalandı!\nİstediğiniz sohbet veya gruba yapıştırabilirsiniz (Ctrl+V).", parent=self)

