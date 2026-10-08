"""
Nöbet Listesini Manuel Kaydırma, Rotasyon ve Hafta Aktarma Ekranı
"""
import tkinter as tk
from tkinter import ttk, messagebox
import datetime
from typing import Callable, Optional
from core.database import Database
from logic.duty_service import DutyService
from ui.theme import COLOR_PRIMARY, COLOR_SUCCESS, FONT_FAMILY

def execute_shift(
    duty_service: DutyService,
    week_str: str,
    mode: str,
    preserve: bool = True,
    preserve_fixed: Optional[bool] = None
) -> str:
    """
    Belirtilen mod ve parametrelerle nöbet kaydırma veya sonraki haftaya aktarma işlemini uygular.
    Uygulanan işlemin açıklamasını döner.
    """
    if preserve_fixed is not None:
        preserve = preserve_fixed

    if mode == "day_forward":
        duty_service.shift_schedule(week_str, shift_type="day", steps=1, preserve_fixed=preserve)
        return "Günler 1 Gün İleri Kaydırıldı (Pzt ➔ Sal ... Cum ➔ Pzt)"
    elif mode == "day_backward":
        duty_service.shift_schedule(week_str, shift_type="day", steps=-1, preserve_fixed=preserve)
        return "Günler 1 Gün Geri Kaydırıldı (Sal ➔ Pzt ... Pzt ➔ Cum)"
    elif mode == "loc_forward":
        duty_service.shift_schedule(week_str, shift_type="location", steps=1, preserve_fixed=preserve)
        return "Nöbet Yerleri 1 Sıra İleri Kaydırıldı"
    elif mode == "loc_backward":
        duty_service.shift_schedule(week_str, shift_type="location", steps=-1, preserve_fixed=preserve)
        return "Nöbet Yerleri Ters Yönde Kaydırıldı"
    elif mode in ("copy_next_week", "copy_next_shift_day"):
        cur_dt = datetime.date.fromisoformat(week_str)
        next_week_str = (cur_dt + datetime.timedelta(days=7)).isoformat()
        duty_service.copy_week_to_next(
            source_week=week_str,
            target_week=next_week_str,
            shift_mode="shift_day",
            shift_steps=1,
            preserve_fixed=preserve
        )
        return f"Nöbetler 1 Gün Kaydırılarak {next_week_str} Haftasına Aktarıldı"
    elif mode == "copy_next_shift_loc":
        cur_dt = datetime.date.fromisoformat(week_str)
        next_week_str = (cur_dt + datetime.timedelta(days=7)).isoformat()
        duty_service.copy_week_to_next(
            source_week=week_str,
            target_week=next_week_str,
            shift_mode="shift_loc",
            shift_steps=1,
            preserve_fixed=preserve
        )
        return f"Nöbet Yerleri 1 Sıra Kaydırılarak {next_week_str} Haftasına Aktarıldı"
    elif mode == "copy_next_same":
        cur_dt = datetime.date.fromisoformat(week_str)
        next_week_str = (cur_dt + datetime.timedelta(days=7)).isoformat()
        duty_service.copy_week_to_next(
            source_week=week_str,
            target_week=next_week_str,
            shift_mode="same",
            preserve_fixed=preserve
        )
        return f"Nöbetler Birebir Aynı Şekilde {next_week_str} Haftasına Aktarıldı"
    return "Kaydırma Tamamlandı"


class ShiftDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Widget,
        db: Database,
        duty_service: DutyService,
        current_week_str: str,
        on_applied: Optional[Callable[[], None]] = None,
        advance_week_callback: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent)
        self.db = db
        self.duty_service = duty_service
        self.current_week = current_week_str
        self.on_applied = on_applied
        self.advance_week_callback = advance_week_callback

        self.title("Nöbet Rotasyonu ve Hafta Aktarma Ayarları")
        self.geometry("620x560")
        self.minsize(580, 520)
        self.transient(parent)
        self.grab_set()

        saved_mode = self.db.get_setting("last_shift_mode", "copy_next_shift_day")
        saved_preserve = self.db.get_setting("last_shift_preserve", "1") == "1"
        saved_carry = self.db.get_setting("week_carry_mode", "same")

        self.mode_var = tk.StringVar(value=saved_mode)
        self.preserve_fixed_var = tk.BooleanVar(value=saved_preserve)
        self.carry_var = tk.StringVar(value=saved_carry)

        self._build_ui()

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=16)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(
            main_frame,
            text="🔄 Nöbet Listesini Kaydır, Rotasyon ve Hafta Aktarma",
            font=(FONT_FAMILY, 12, "bold"),
            foreground=COLOR_PRIMARY
        ).pack(anchor="w", pady=(0, 3))

        ttk.Label(
            main_frame,
            text=f"Kaynak Hafta: {self.current_week}  |  (Seçimleriniz kaydedilir ve ana ekranda hızlı butonlarla uygulanır)",
            font=(FONT_FAMILY, 9, "italic"),
            foreground="#64748B"
        ).pack(anchor="w", pady=(0, 10))

        # 1. GRUP: Sonraki Haftaya Aktar ve Haftayı İlerlet (Hafta Değişir)
        grp_next = tk.LabelFrame(
            main_frame,
            text=" ⏩ Sonraki Haftaya Aktar ve Haftayı İlerlet (Hafta Değişir) ",
            font=(FONT_FAMILY, 9, "bold"),
            padx=12,
            pady=8,
            relief="solid",
            bd=1
        )
        grp_next.pack(fill="x", pady=(0, 10))

        next_options = [
            ("copy_next_shift_day", "🔄 Günleri 1 Gün Kaydırarak Sonraki Haftaya Aktar (Pzt ➔ Sal, Sal ➔ Çar... + Hafta İlerler)"),
            ("copy_next_shift_loc", "📍 Nöbet Yerlerini Kaydırarak Sonraki Haftaya Aktar (1. Kat ➔ 2. Kat... + Hafta İlerler)"),
            ("copy_next_same", "📋 Aynısını Sonraki Haftaya Aktar (Birebir Kopyala + Hafta İlerler)"),
        ]
        for val, label in next_options:
            rb = ttk.Radiobutton(grp_next, text=label, value=val, variable=self.mode_var)
            rb.pack(anchor="w", pady=3)

        # 2. GRUP: Mevcut Hafta İçinde Kaydır (Aynı Haftada Kalır)
        grp_curr = tk.LabelFrame(
            main_frame,
            text=" 🔄 Mevcut Hafta İçinde Kaydır (Aynı Haftada Kalır) ",
            font=(FONT_FAMILY, 9, "bold"),
            padx=12,
            pady=8,
            relief="solid",
            bd=1
        )
        grp_curr.pack(fill="x", pady=(0, 10))

        curr_options = [
            ("day_forward", "➡️ Günleri 1 Gün İleri Kaydır (Pzt ➔ Sal, Sal ➔ Çar ... Cum ➔ Pzt)"),
            ("day_backward", "⬅️ Günleri 1 Gün Geri Kaydır (Sal ➔ Pzt, Çar ➔ Sal ... Pzt ➔ Cum)"),
            ("loc_forward", "⬇️ Nöbet Yerlerini 1 Sıra Kaydır (1. Kat ➔ 2. Kat ... Zemin ➔ 1. Kat)"),
            ("loc_backward", "⬆️ Nöbet Yerlerini Ters Yönde Kaydır"),
        ]
        for val, label in curr_options:
            rb = ttk.Radiobutton(grp_curr, text=label, value=val, variable=self.mode_var)
            rb.pack(anchor="w", pady=2)

        # 3. GRUP: Otomatik Hafta Gezinme Tercihi
        grp_auto = tk.LabelFrame(
            main_frame,
            text=" ⚙️ Hafta Gezinme Otomasyonu ('Sonraki Hafta ▶' Butonu Tıklandığında) ",
            font=(FONT_FAMILY, 9, "bold"),
            padx=12,
            pady=8,
            relief="solid",
            bd=1
        )
        grp_auto.pack(fill="x", pady=(0, 10))

        auto_options = [
            ("same", "📋 Sonraki haftaya geçerken boşsa: Önceki haftanın aynısını otomatik aktar (Önerilen)"),
            ("shift_day", "🔄 Sonraki haftaya geçerken boşsa: 1 gün kaydırarak otomatik aktar"),
            ("shift_loc", "📍 Sonraki haftaya geçerken boşsa: Yerleri kaydırarak otomatik aktar"),
            ("none", "⬜ Sonraki haftaya geçerken boşsa: Boş bırak (Otomatik doldurma)"),
        ]
        for val, label in auto_options:
            rb = ttk.Radiobutton(grp_auto, text=label, value=val, variable=self.carry_var)
            rb.pack(anchor="w", pady=2)

        # Sabit Nöbet Koruması
        chk_fixed = ttk.Checkbutton(
            main_frame,
            text="🔒 Sabit (Kilitli) nöbetlerin yerini koru (Kaydırmadan muaf tut)",
            variable=self.preserve_fixed_var
        )
        chk_fixed.pack(anchor="w", pady=(0, 12))

        # Butonlar
        btn_box = ttk.Frame(main_frame)
        btn_box.pack(fill="x", side="bottom")

        ttk.Button(btn_box, text="Vazgeç", command=self.destroy).pack(side="right", padx=(5, 0))

        btn_apply = ttk.Button(
            btn_box,
            text="✔ Kaydet ve Şimdi Uygula",
            style="Primary.TButton",
            command=self._apply_shift
        )
        btn_apply.pack(side="right")

    def _apply_shift(self):
        mode = self.mode_var.get()
        preserve = self.preserve_fixed_var.get()
        carry_mode = self.carry_var.get()

        try:
            self.db.set_setting("last_shift_mode", mode)
            self.db.set_setting("last_shift_preserve", "1" if preserve else "0")
            self.db.set_setting("week_carry_mode", carry_mode)

            desc = execute_shift(self.duty_service, self.current_week, mode, preserve)

            # Eğer sonraki haftaya aktarma modu seçildiyse ana ekranda haftayı ilerlet!
            if mode in ("copy_next_week", "copy_next_shift_day", "copy_next_shift_loc", "copy_next_same"):
                if self.advance_week_callback:
                    self.advance_week_callback()

            if self.on_applied:
                self.on_applied()

            messagebox.showinfo(
                "Başarılı",
                f"İşlem başarıyla uygulandı:\n{desc}\n\nTercihleriniz kaydedildi."
            )
            self.destroy()

        except Exception as e:
            messagebox.showerror("Hata", f"İşlem sırasında hata oluştu:\n{e}")
