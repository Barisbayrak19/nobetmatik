"""
Apple Spotlight Tarzı Hızlı Arama ve Komut Merkezi (Ctrl + K)
Öğretmenler, nöbet yerleri, ders programları ve hızlı aksiyonlar arasında
anında filtreleme, arama ve gezinme sağlar.
"""
import datetime
import webbrowser
import urllib.parse
from typing import List, Dict, Any, Optional, Callable

import tkinter as tk
import customtkinter as ctk

from core.database import Database
from core.models import Teacher, Location, Assignment
from logic.duty_service import DutyService
from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_PRIMARY_HOVER,
    COLOR_SUCCESS, COLOR_DANGER, COLOR_BORDER, COLOR_BORDER_STRONG,
    COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, FONT_FAMILY,
    COLOR_SIDEBAR_ACTIVE, COLOR_SIDEBAR_HOVER
)

DAY_KEYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]
DAY_NAMES_TR = {
    "monday": "Pazartesi",
    "tuesday": "Salı",
    "wednesday": "Çarşamba",
    "thursday": "Perşembe",
    "friday": "Cuma"
}
DAY_INDEX_MAP = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday"
}


class SpotlightDialog(ctk.CTkToplevel):
    """
    macOS Spotlight tarzında ortalanmış, klavye dostu hızlı arama penceresi.
    """
    def __init__(
        self,
        parent: tk.Widget,
        db: Database,
        duty_service: DutyService,
        current_week_start: str,
        on_navigate_teacher: Optional[Callable[[str], None]] = None,
        on_open_whatsapp: Optional[Callable[[Teacher, str], None]] = None,
        on_open_kiosk: Optional[Callable[[], None]] = None,
        on_open_kbs: Optional[Callable[[], None]] = None,
        on_run_distribution: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent)
        self.parent_app = parent
        self.db = db
        self.duty_service = duty_service
        self.current_week_start = current_week_start
        self.on_navigate_teacher = on_navigate_teacher
        self.on_open_whatsapp = on_open_whatsapp
        self.on_open_kiosk = on_open_kiosk
        self.on_open_kbs = on_open_kbs
        self.on_run_distribution = on_run_distribution

        self.title("Spotlight Hızlı Arama")
        self.geometry("700x520")
        self.minsize(620, 440)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Pencereyi ana pencerenin tam ortasına yerleştir
        self._center_window()

        # Veri Hazırlığı
        self.teachers = self.db.get_teachers(active_only=True)
        self.locations = self.db.get_locations()
        self.assignments = self.db.get_assignments_for_week(self.current_week_start)
        self.loc_map = {loc.id: loc.name for loc in self.locations}

        # Güncel gün
        today = datetime.date.today()
        self.today_day_id = DAY_INDEX_MAP.get(today.weekday(), "monday")
        self.today_name_tr = DAY_NAMES_TR.get(self.today_day_id, "Pazartesi")

        self.filtered_results: List[Dict[str, Any]] = []
        self.selected_index: int = 0
        self.item_widgets: List[ctk.CTkFrame] = []

        self._build_ui()
        self._bind_keys()
        self._search()

    def _center_window(self):
        self.update_idletasks()
        try:
            pw = self.parent_app.winfo_width()
            ph = self.parent_app.winfo_height()
            px = self.parent_app.winfo_rootx()
            py = self.parent_app.winfo_rooty()
            w, h = 700, 520
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 3)  # Apple Spotlight gibi biraz daha yukarıda
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            self.geometry("700x520")

    def _build_ui(self):
        # Arka Plan
        self.configure(fg_color="#F5F5F7")

        # Spotlight Kapsayıcı Kartı
        self.container = ctk.CTkFrame(
            self,
            fg_color="#FFFFFF",
            corner_radius=16,
            border_width=1,
            border_color="#D1D1D6"
        )
        self.container.pack(fill="both", expand=True, padx=12, pady=12)

        # 1. Arama Giriş Çubuğu (Spotlight Search Bar)
        search_bar = ctk.CTkFrame(self.container, fg_color="transparent", height=56)
        search_bar.pack(fill="x", padx=16, pady=(14, 8))

        lbl_icon = ctk.CTkLabel(
            search_bar,
            text="🔍",
            font=(FONT_FAMILY, 16),
            text_color="#8E8E93"
        )
        lbl_icon.pack(side="left", padx=(4, 10))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self._on_search_change())

        self.entry_search = ctk.CTkEntry(
            search_bar,
            textvariable=self.search_var,
            placeholder_text="Öğretmen, nöbet yeri veya hızlı komut arayın... (ör. Ahmet, Bahçe, Puantaj)",
            font=(FONT_FAMILY, 13),
            fg_color="transparent",
            border_width=0,
            text_color="#1C1C1E"
        )
        self.entry_search.pack(side="left", fill="both", expand=True)
        self.entry_search.focus_set()

        # ESC Rozeti
        lbl_esc = ctk.CTkLabel(
            search_bar,
            text="ESC ile Kapat",
            font=(FONT_FAMILY, 9),
            text_color="#8E8E93",
            fg_color="#F2F2F7",
            corner_radius=6,
            padx=8,
            pady=3
        )
        lbl_esc.pack(side="right", padx=4)

        # İnce ayırıcı çizgi
        sep = ctk.CTkFrame(self.container, height=1, fg_color="#E5E5EA")
        sep.pack(fill="x", padx=12, pady=(0, 6))

        # 2. Sonuç Listesi (Kaydırılabilir Alan)
        self.scroll_results = ctk.CTkScrollableFrame(
            self.container,
            fg_color="transparent",
            corner_radius=0
        )
        self.scroll_results.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        # 3. Alt Durum Çubuğu (Keyboard hints)
        footer = ctk.CTkFrame(self.container, height=34, fg_color="#F9F9FB", corner_radius=10)
        footer.pack(fill="x", padx=8, pady=(0, 8), side="bottom")

        lbl_hint = ctk.CTkLabel(
            footer,
            text="⬆ ⬇ Gezin  •  ↵ Seç / Aç  •  💬 W: WhatsApp  •  Ctrl+K: Arama",
            font=(FONT_FAMILY, 9),
            text_color="#636366"
        )
        lbl_hint.pack(side="left", padx=12, pady=6)

        self.lbl_count = ctk.CTkLabel(
            footer,
            text="0 sonuç",
            font=(FONT_FAMILY, 9),
            text_color="#8E8E93"
        )
        self.lbl_count.pack(side="right", padx=12, pady=6)

    def _bind_keys(self):
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Down>", self._on_arrow_down)
        self.bind("<Up>", self._on_arrow_up)
        self.bind("<Return>", self._on_enter)
        self.entry_search.bind("<Down>", self._on_arrow_down)
        self.entry_search.bind("<Up>", self._on_arrow_up)
        self.entry_search.bind("<Return>", self._on_enter)

    def _on_search_change(self):
        self.selected_index = 0
        self._search()

    def _search(self):
        query = self.search_var.get().strip().lower()
        results: List[Dict[str, Any]] = []

        # 1. Hızlı Komutlar
        commands = [
            {
                "type": "command",
                "title": "📺 Canlı Nöbet Panosu (Kiosk / TV Modu)",
                "subtitle": "Öğretmenler odası ekranı için tam ekran canlı nöbet tablosu (F11)",
                "action": "kiosk",
                "icon": "📺"
            },
            {
                "type": "command",
                "title": "📊 Aylık Nöbet Puantajı & Ek Ders Çizelgesi (KBS)",
                "subtitle": "Ay sonu fiili nöbet tutulma günleri ve ek ders ücret icmali Excel dökümü",
                "action": "kbs",
                "icon": "📊"
            },
            {
                "type": "command",
                "title": "⚡ Otomatik Nöbet Dağıtımı Yap",
                "subtitle": "Adaletli kurallara göre haftalık nöbetleri yapay zekayla otomatik ata",
                "action": "distribution",
                "icon": "⚡"
            }
        ]

        for cmd in commands:
            if not query or query in cmd["title"].lower() or query in cmd["subtitle"].lower() or query in cmd["action"]:
                results.append(cmd)

        # 2. Öğretmenler
        for t in self.teachers:
            match_name = query in t.name.lower()
            match_branch = query in t.branch.lower()
            match_phone = bool(t.phone and query in t.phone.lower())

            if not query or match_name or match_branch or match_phone:
                # Bu öğretmenin haftalık nöbet görevleri
                t_assignments = [a for a in self.assignments if a.teacher_id == t.id]
                duties_desc = []
                today_duty = None

                for a in t_assignments:
                    day_name = DAY_NAMES_TR.get(a.day_id, a.day_id)
                    loc_name = self.loc_map.get(a.location_id, "Nöbet")
                    fixed_str = " (Sabit)" if getattr(a, "fixed", False) else ""
                    duties_desc.append(f"{day_name}: {loc_name}{fixed_str}")
                    if a.day_id == self.today_day_id:
                        today_duty = loc_name

                if duties_desc:
                    duty_summary = " • ".join(duties_desc)
                else:
                    duty_summary = "Bu hafta nöbeti yok"

                # Bugün durumu
                today_info = f"Bugün: {today_duty} Nöbetçisi" if today_duty else "Bugün nöbeti yok"

                results.append({
                    "type": "teacher",
                    "teacher": t,
                    "title": t.name,
                    "subtitle": f"{t.branch or 'Genel'}  |  {duty_summary}",
                    "badge": today_info,
                    "is_today_duty": bool(today_duty),
                    "assignments": t_assignments,
                    "icon": "👤"
                })

        # 3. Nöbet Yerleri
        for loc in self.locations:
            if not query or query in loc.name.lower():
                loc_assignments = [a for a in self.assignments if a.location_id == loc.id]
                assigned_teachers = []
                for a in loc_assignments:
                    for t in self.teachers:
                        if t.id == a.teacher_id:
                            day_name = DAY_NAMES_TR.get(a.day_id, a.day_id)[:3]
                            assigned_teachers.append(f"{day_name}: {t.name.split()[0]}")
                            break
                t_str = " • ".join(assigned_teachers) if assigned_teachers else "Henüz atama yok"

                results.append({
                    "type": "location",
                    "location": loc,
                    "title": f"Nöbet Yeri: {loc.name}",
                    "subtitle": f"Kapasite: {loc.capacity}  |  {t_str}",
                    "badge": f"{len(loc_assignments)} Görev",
                    "icon": "📍"
                })

        self.filtered_results = results
        self.lbl_count.configure(text=f"{len(results)} sonuç")
        self._render_results()

    def _render_results(self):
        for w in self.item_widgets:
            w.destroy()
        self.item_widgets.clear()

        if not self.filtered_results:
            lbl_empty = ctk.CTkLabel(
                self.scroll_results,
                text="Aramanızla eşleşen öğretmen veya komut bulunamadı.",
                font=(FONT_FAMILY, 11),
                text_color="#8E8E93",
                pady=40
            )
            lbl_empty.pack()
            self.item_widgets.append(lbl_empty)
            return

        for idx, item in enumerate(self.filtered_results[:30]):  # İlk 30 sonucu listele
            is_selected = (idx == self.selected_index)
            item_frame = self._create_result_row(item, idx, is_selected)
            item_frame.pack(fill="x", pady=2)
            self.item_widgets.append(item_frame)

    def _create_result_row(self, item: Dict[str, Any], index: int, is_selected: bool) -> ctk.CTkFrame:
        bg_col = "#EBF5FF" if is_selected else "transparent"
        border_col = "#007AFF" if is_selected else "#F2F2F7"
        border_w = 1 if is_selected else 0

        row = ctk.CTkFrame(
            self.scroll_results,
            fg_color=bg_col,
            corner_radius=10,
            border_width=border_w,
            border_color=border_col,
            height=48
        )

        # Tıklanma olayı
        row.bind("<Button-1>", lambda e, i=index: self._select_and_execute(i))

        # Sol İkon Kutucuğu
        icon_box = ctk.CTkLabel(
            row,
            text=item.get("icon", "•"),
            font=(FONT_FAMILY, 14),
            width=36
        )
        icon_box.pack(side="left", padx=(8, 6), pady=6)
        icon_box.bind("<Button-1>", lambda e, i=index: self._select_and_execute(i))

        # Orta Başlık ve Alt Başlık
        text_frame = ctk.CTkFrame(row, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True, pady=6)
        text_frame.bind("<Button-1>", lambda e, i=index: self._select_and_execute(i))

        title_col = "#007AFF" if is_selected else "#1C1C1E"
        lbl_title = ctk.CTkLabel(
            text_frame,
            text=item.get("title", ""),
            font=(FONT_FAMILY, 11, "bold"),
            text_color=title_col,
            anchor="w"
        )
        lbl_title.pack(fill="x", anchor="w")
        lbl_title.bind("<Button-1>", lambda e, i=index: self._select_and_execute(i))

        lbl_sub = ctk.CTkLabel(
            text_frame,
            text=item.get("subtitle", ""),
            font=(FONT_FAMILY, 9),
            text_color="#636366",
            anchor="w"
        )
        lbl_sub.pack(fill="x", anchor="w")
        lbl_sub.bind("<Button-1>", lambda e, i=index: self._select_and_execute(i))

        # Sağ Rozet / Aksiyon
        if item.get("badge"):
            is_duty = item.get("is_today_duty", False)
            badge_bg = "#E8F5E9" if is_duty else "#F2F2F7"
            badge_fg = "#2E7D32" if is_duty else "#636366"
            lbl_badge = ctk.CTkLabel(
                row,
                text=item["badge"],
                font=(FONT_FAMILY, 9, "bold" if is_duty else "normal"),
                fg_color=badge_bg,
                text_color=badge_fg,
                corner_radius=6,
                padx=8,
                pady=2
            )
            lbl_badge.pack(side="right", padx=(6, 10))

        # Eğer öğretmen ise ve WhatsApp butonu eklenebilirse
        if item.get("type") == "teacher" and is_selected:
            btn_wa = ctk.CTkButton(
                row,
                text="💬 WhatsApp",
                font=(FONT_FAMILY, 9, "bold"),
                fg_color="#25D366",
                hover_color="#128C7E",
                text_color="#FFFFFF",
                width=80,
                height=26,
                corner_radius=6,
                command=lambda t=item["teacher"]: self._trigger_whatsapp(t)
            )
            btn_wa.pack(side="right", padx=(0, 6))

        return row

    def _on_arrow_down(self, event=None):
        if not self.filtered_results:
            return "break"
        if self.selected_index < len(self.filtered_results) - 1:
            self.selected_index += 1
            self._render_results()
            self._ensure_visible(self.selected_index)
        return "break"

    def _on_arrow_up(self, event=None):
        if not self.filtered_results:
            return "break"
        if self.selected_index > 0:
            self.selected_index -= 1
            self._render_results()
            self._ensure_visible(self.selected_index)
        return "break"

    def _ensure_visible(self, index: int):
        # Seçili öğenin görünür olmasını sağla
        try:
            total = len(self.filtered_results)
            if total > 0:
                fraction = index / total
                self.scroll_results._parent_canvas.yview_moveto(fraction)
        except Exception:
            pass

    def _on_enter(self, event=None):
        if 0 <= self.selected_index < len(self.filtered_results):
            self._execute_action(self.filtered_results[self.selected_index])
        return "break"

    def _select_and_execute(self, index: int):
        self.selected_index = index
        self._render_results()
        if 0 <= index < len(self.filtered_results):
            self._execute_action(self.filtered_results[index])

    def _execute_action(self, item: Dict[str, Any]):
        item_type = item.get("type")

        if item_type == "command":
            action = item.get("action")
            self.destroy()
            if action == "kiosk" and self.on_open_kiosk:
                self.on_open_kiosk()
            elif action == "kbs" and self.on_open_kbs:
                self.on_open_kbs()
            elif action == "distribution" and self.on_run_distribution:
                self.on_run_distribution()

        elif item_type == "teacher":
            teacher: Teacher = item["teacher"]
            self.destroy()
            if self.on_navigate_teacher:
                self.on_navigate_teacher(teacher.id)

        elif item_type == "location":
            location: Location = item["location"]
            self.destroy()
            # Nöbet yeri odaklama
            if hasattr(self.parent_app, "show_locations_view"):
                self.parent_app.show_locations_view()

    def _trigger_whatsapp(self, teacher: Teacher):
        self.destroy()
        if self.on_open_whatsapp:
            self.on_open_whatsapp(teacher, self.current_week_start)
