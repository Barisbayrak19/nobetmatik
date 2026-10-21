"""
Haftalık Nöbet Çizelgesi Tablosu
Sürükle-bırak (Drag & Drop), Takas (Swap), Sabitleme ve Sağ Tık Alternatifi.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import datetime
from typing import Dict, Tuple, Optional, Callable, List, Any
from core.models import Assignment, Teacher, Location, Day, DragState, TeacherLesson
from core.database import Database
from logic.duty_service import DutyService
from logic.substitution_service import SubstitutionService, PERIOD_TIMES
from core.logger import logger
import ui.theme as theme
from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_SECONDARY,
    COLOR_BORDER, COLOR_BORDER_STRONG, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED,
    COLOR_FIXED, COLOR_FIXED_BORDER, COLOR_CELL_BG, COLOR_CELL_EMPTY, COLOR_CELL_HOVER, COLOR_CELL_DRAG,
    COLOR_CELL_SELECTED, COLOR_CELL_SELECTED_BORDER, COLOR_BADGE_FREE, COLOR_BADGE_FREE_TXT,
    FONT_FAMILY, FONT_SIZE_BASE, GRID_BORDER_COLOR, GRID_BORDER_WIDTH, GRID_RELIEF
)

TURKISH_MONTHS = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

def to_title_case(text: str) -> str:
    """Türkçe karakterleri gözeterek metni Başlık Düzeni (Title Case) formatına dönüştürür."""
    if not text:
        return ""
    words = text.strip().split()
    result = []
    for w in words:
        if not w:
            continue
        first = w[0].replace('i', 'İ').replace('ı', 'I').upper()
        rest = w[1:].replace('I', 'ı').replace('İ', 'i').lower()
        result.append(first + rest)
    return " ".join(result)

def format_branch_display(branch: str) -> str:
    """Branş metnini döndürür; metni kesmeden veya kırpmadan tam olarak korur."""
    if not branch:
        return ""
    return branch.strip()

def get_location_icon(name: str) -> str:
    """Nöbet yeri adına uygun modern sembol döndürür."""
    lower = name.lower()
    if "bahçe" in lower or "bahce" in lower:
        return "🌳 "
    if "zemin" in lower or "kat" in lower or "blok" in lower or "koridor" in lower:
        return "🏢 "
    if "salon" in lower or "spor" in lower:
        return "🏀 "
    if "kantin" in lower or "yemek" in lower:
        return "☕ "
    if "kütüphane" in lower or "kutuphane" in lower or "laboratuvar" in lower:
        return "🔬 "
    return "📍 "


class TeacherInfoPopover:
    """
    Öğretmen kartındaki bilgi butonuna (ℹ) veya çift tıklamaya bağlı olarak açılan,
    kompakt, şık, ekran taşma kontrollü ve gerektiğinde kaydırılabilen bilgi penceresi.
    Sürükle-bırak sırasında ASLA açılmaz; sürükleme başladığında derhal kapatılır.
    """
    def __init__(self, cell_widget: "CellWidget"):
        self.cell = cell_widget
        self.tip_window: Optional[tk.Toplevel] = None

    def show(self):
        if self.tip_window or not self.cell or not self.cell.teacher:
            return

        ref_w = self.cell
        try:
            rx = ref_w.winfo_rootx()
            ry = ref_w.winfo_rooty()
            rw = ref_w.winfo_width()
            rh = ref_w.winfo_height()
            sw = ref_w.winfo_screenwidth()
            sh = ref_w.winfo_screenheight()
        except Exception:
            return

        pop_w = 270
        # Mümkünse ilgili hücrenin SAĞINDA aç
        target_x = rx + rw + 6
        if target_x + pop_w > sw - 12:
            # Sağda yer yoksa SOLUNDA aç
            target_x = rx - pop_w - 6
            if target_x < 8:
                target_x = max(8, rx)

        target_y = ry
        max_pop_h = 240
        if target_y + max_pop_h > sh - 35:
            target_y = max(10, sh - max_pop_h - 35)

        self.tip_window = tw = tk.Toplevel(ref_w)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{target_x}+{target_y}")
        tw.attributes("-topmost", True)

        main_box = tk.Frame(
            tw,
            bg="#FFFFFF",
            highlightbackground="#E5E5EA",
            highlightthickness=1,
            relief="flat",
            bd=0
        )
        main_box.pack(fill="both", expand=True)

        t = self.cell.teacher
        day_name = self.cell.day.name
        loc_name = self.cell.location.name
        branch_str = t.branch if t.branch else "Genel"

        # 1. Başlık Alanı (Koyu Lacivert #1E293B, beyaz metin, kapat butonu)
        header_fr = tk.Frame(main_box, bg="#1C1C1E", padx=10, pady=6)
        header_fr.pack(fill="x")

        top_row = tk.Frame(header_fr, bg="#1C1C1E")
        top_row.pack(fill="x")

        lbl_tname = tk.Label(
            top_row,
            text=f"👤 {to_title_case(t.name)}",
            font=(FONT_FAMILY, 9, "bold"),
            fg="#F8FAFC",
            bg="#1C1C1E",
            anchor="w"
        )
        lbl_tname.pack(side="left", fill="x", expand=True)

        btn_close = tk.Label(
            top_row,
            text="✕",
            font=(FONT_FAMILY, 9, "bold"),
            fg="#86868B",
            bg="#1C1C1E",
            cursor="hand2"
        )
        btn_close.pack(side="right")
        btn_close.bind("<Button-1>", lambda e: self.hide())
        btn_close.bind("<Enter>", lambda e: btn_close.configure(fg="#FF3B30"))
        btn_close.bind("<Leave>", lambda e: btn_close.configure(fg="#86868B"))

        lbl_sub = tk.Label(
            header_fr,
            text=f"◉ {branch_str}  •  📍 {loc_name} ({day_name})",
            font=(FONT_FAMILY, 8),
            fg="#86868B",
            bg="#1C1C1E",
            anchor="w"
        )
        lbl_sub.pack(fill="x", pady=(2, 0))

        # 2. Ders Programı (Uzun listelerde kaydırma destekli)
        lessons = self.cell.controller.get_teacher_schedule(t.id, day_name)
        free_count = 0

        list_container = tk.Frame(main_box, bg="#FFFFFF", padx=6, pady=4)
        list_container.pack(fill="both", expand=True)

        needs_scroll = len(lessons) > 5
        if needs_scroll:
            canvas_h = min(120, len(lessons) * 22)
            l_canvas = tk.Canvas(list_container, bg="#FFFFFF", height=canvas_h, width=pop_w - 24, highlightthickness=0)
            l_scroll = tk.Scrollbar(list_container, orient="vertical", command=l_canvas.yview, width=8)
            l_frame = tk.Frame(l_canvas, bg="#FFFFFF")
            l_canvas.create_window((0, 0), window=l_frame, anchor="nw")
            l_canvas.configure(yscrollcommand=l_scroll.set)
            l_frame.bind("<Configure>", lambda e: l_canvas.configure(scrollregion=l_canvas.bbox("all")))
            l_canvas.pack(side="left", fill="both", expand=True)
            l_scroll.pack(side="right", fill="y")
            parent_for_rows = l_frame
        else:
            parent_for_rows = list_container

        if lessons:
            ctrl_db = getattr(self.cell.controller, "db", None) if (self.cell and hasattr(self.cell, "controller")) else None
            period_times = ctrl_db.get_period_times() if (ctrl_db and hasattr(ctrl_db, "get_period_times")) else PERIOD_TIMES
            for l in lessons:
                time_str = period_times.get(l.period, "")
                r_item = tk.Frame(parent_for_rows, bg="#FFFFFF")
                r_item.pack(fill="x", pady=1)

                if l.is_free:
                    free_count += 1
                    lbl_row = tk.Label(
                        r_item,
                        text=f"  {l.period}. Ders ({time_str}): 🟢 BOŞ DERS",
                        font=(FONT_FAMILY, 8, "bold"),
                        fg="#15803D",
                        bg="#FFFFFF",
                        anchor="w"
                    )
                else:
                    c_text = f"{l.class_name} ({l.subject_code})" if l.class_name else (l.subject_code or "Ders")
                    lbl_row = tk.Label(
                        r_item,
                        text=f"  {l.period}. Ders ({time_str}): {c_text}",
                        font=(FONT_FAMILY, 8),
                        fg="#334155",
                        bg="#FFFFFF",
                        anchor="w"
                    )
                lbl_row.pack(fill="x")
        else:
            lbl_empty = tk.Label(
                parent_for_rows,
                text="  Bugün kayıtlı ders programı bulunmuyor.",
                font=(FONT_FAMILY, 8, "italic"),
                fg="#64748B",
                bg="#FFFFFF",
                pady=4
            )
            lbl_empty.pack(fill="x")

        # 3. Alt Özet Çubuğu
        foot_fr = tk.Frame(main_box, bg="#F8FAFC", padx=10, pady=4, highlightbackground="#E2E8F0", highlightthickness=1)
        foot_fr.pack(fill="x")

        lock_txt = " • 🔒 Sabit" if self.cell.assignment.fixed else ""
        lbl_summary = tk.Label(
            foot_fr,
            text=f"🟢 Boş Ders: {free_count} Saat{lock_txt}",
            font=(FONT_FAMILY, 8, "bold"),
            fg="#15803D" if free_count > 0 else "#64748B",
            bg="#F8FAFC",
            anchor="w"
        )
        lbl_summary.pack(fill="x")

    def hide(self):
        if self.tip_window:
            try:
                self.tip_window.destroy()
            except Exception:
                pass
            self.tip_window = None

    show_tip = show
    hide_tip = hide

# Geriye dönük uyumluluk için takma ad
GridTooltip = TeacherInfoPopover


class DragGhostWindow(tk.Toplevel):
    """
    Sürükleme sırasında farenin peşinden giden şık, yarı saydam kopya kart (Ghost).
    """
    def __init__(self, master: tk.Widget, teacher_name: str, branch: str):
        super().__init__(master)
        self.wm_overrideredirect(True)
        self.attributes("-topmost", True)
        try:
            self.attributes("-alpha", 0.88)
        except Exception:
            pass

        card = tk.Frame(
            self,
            bg="#007AFF",
            highlightbackground="#0062D2",
            highlightthickness=1,
            padx=10,
            pady=6
        )
        card.pack()

        lbl_name = tk.Label(
            card,
            text=f"👤 {teacher_name}",
            font=(FONT_FAMILY, 10, "bold"),
            fg="#FFFFFF",
            bg="#007AFF"
        )
        lbl_name.pack(anchor="w")

        if branch:
            lbl_branch = tk.Label(
                card,
                text=branch,
                font=(FONT_FAMILY, 8),
                fg="#EBF5FF",
                bg="#007AFF"
            )
            lbl_branch.pack(anchor="w", pady=(1, 0))

    def move_to(self, x_root: int, y_root: int):
        self.wm_geometry(f"+{x_root + 12}+{y_root + 12}")


class CellWidget(ctk.CTkFrame):
    """
    Çizelgedeki tek bir nöbet slotunu temsil eden kart widget'ı.
    1 px açık gri-mavi (#CBD5E1) kenarlık, ~8 px yuvarlak köşe, dengeli dikey yerleşim.
    Tıklama, sürükleme ve bilgi penceresi davranışları birbirinden tamamen ayrılmıştır.
    """
    def __init__(
        self,
        parent: tk.Widget,
        assignment: Assignment,
        teacher: Optional[Teacher],
        day: Day,
        location: Location,
        slot_index: int,
        grid_controller: "ScheduleGrid"
    ):
        self.assignment = assignment
        self.teacher = teacher
        self.day = day
        self.location = location
        self.slot_index = slot_index
        self.controller = grid_controller
        self.is_selected = False
        self._is_dragging = False
        self._press_x_root = 0
        self._press_y_root = 0

        card_bg = self._default_bg()
        border_col = self._default_border()
        super().__init__(
            parent,
            corner_radius=10,
            border_width=1,
            border_color=border_col,
            fg_color=card_bg
        )

        self._build_ui()
        self._bind_events()
        self.tooltip = TeacherInfoPopover(self)
        self.popover = self.tooltip

    def _default_bg(self) -> str:
        if self.assignment.fixed:
            return COLOR_FIXED
        elif self.teacher:
            return COLOR_CARD
        return COLOR_CELL_EMPTY

    def _default_border(self) -> str:
        if self.assignment.fixed:
            return COLOR_FIXED_BORDER
        elif self.teacher:
            return theme.GRID_BORDER_COLOR
        return theme.COLOR_CELL_EMPTY_BORDER

    def configure(self, **kwargs):
        if "bg" in kwargs:
            kwargs["fg_color"] = kwargs.pop("bg")
        if "highlightbackground" in kwargs:
            kwargs["border_color"] = kwargs.pop("highlightbackground")
        if "highlightthickness" in kwargs:
            kwargs["border_width"] = kwargs.pop("highlightthickness")
        if "relief" in kwargs:
            kwargs.pop("relief")
        if "bd" in kwargs:
            kwargs.pop("bd")
        super().configure(**kwargs)

    def cget(self, key):
        if key == "highlightbackground":
            return self._border_color
        if key == "highlightthickness":
            return self._border_width
        if key == "relief":
            return "flat"
        return super().cget(key)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        if selected:
            self.configure(
                fg_color=theme.COLOR_CELL_SELECTED,
                border_color=theme.COLOR_CELL_SELECTED_BORDER,
                border_width=2
            )
        else:
            bg_col = self._default_bg()
            border_col = self._default_border()
            self.configure(
                fg_color=bg_col,
                border_color=border_col,
                border_width=1
            )

    def _build_ui(self):
        bg_color = self._default_bg()
        border_col = self._default_border()
        self.configure(fg_color=bg_color, border_color=border_col, border_width=1)

        self.btn_info = None

        if self.assignment.fixed:
            # Üst Küçük Rozet (Sadece Sabit Kilitliyse göster - ferah aralıklarla)
            self.top_bar = ctk.CTkFrame(self, fg_color="transparent")
            self.top_bar.pack(fill="x", padx=6, pady=(4, 2))
            self.badge_lock = ctk.CTkFrame(
                self.top_bar,
                fg_color="#FFF8ED",
                border_width=1,
                border_color="#FF9500",
                corner_radius=5,
                height=18
            )
            self.badge_lock.pack(side="left")
            self.lbl_lock = ctk.CTkLabel(
                self.badge_lock,
                text="🔒 Sabit",
                font=ctk.CTkFont(family=theme.FONT_FAMILY, size=10, weight="bold"),
                text_color="#B45309"
            )
            self.lbl_lock.pack(padx=5, pady=1)

        # Dikey ortalanmış içerik kutusu
        self.center_box = ctk.CTkFrame(self, fg_color="transparent")
        self.center_box.pack(expand=True, fill="both", padx=4, pady=(2, 2))

        if self.teacher:
            # 1. Satır: İsim (2 satıra sarkan uzun isimlerin hizayı bozmaması için sabit min-h kutusu)
            name_text = to_title_case(self.teacher.name)
            self.name_container = ctk.CTkFrame(self.center_box, fg_color="transparent", height=38)
            self.name_container.pack(fill="x", pady=(0, 1))
            self.name_container.pack_propagate(False)

            self.lbl_name = ctk.CTkLabel(
                self.name_container,
                text=name_text,
                font=ctk.CTkFont(family=theme.FONT_FAMILY, size=theme.FONT_SIZE_TEACHER, weight=theme.FONT_WEIGHT_TEACHER),
                text_color="#1D1D1F",
                wraplength=135,
                justify="center",
                cursor="hand2"
            )
            self.lbl_name.pack(expand=True, fill="both")

            # 2. Satır: Branş Bilgisi (1 kademe daha küçük text-xs slate-500, kırpma yok, wrap destekli)
            branch_raw = self.teacher.branch if self.teacher.branch else ""
            branch_disp = format_branch_display(branch_raw)
            if branch_disp:
                self.lbl_branch = ctk.CTkLabel(
                    self.center_box,
                    text=branch_disp,
                    font=ctk.CTkFont(family=theme.FONT_FAMILY, size=max(10, theme.FONT_SIZE_SECONDARY - 1), weight="normal"),
                    text_color="#86868B",
                    wraplength=135,
                    justify="center",
                    cursor="hand2"
                )
                self.lbl_branch.pack(fill="x", pady=(0, 2))

            # 3. Satır: Boş Ders Rozeti (Nötr, sade bilgilendirme stili: bg-slate-100 text-slate-600)
            free_periods = self.controller.get_teacher_free_periods(self.teacher.id, self.day.name)
            if free_periods:
                free_str = ", ".join(map(str, free_periods))
                badge_text = f"Boş: {free_str}. Ders"
                badge_bg = "#F5F5F7"
                badge_fg = "#6E6E73"
                badge_border = "#E5E5EA"
            else:
                badge_text = "Tüm saatler dolu"
                badge_bg = "#FBFBFD"
                badge_fg = "#86868B"
                badge_border = "#E5E5EA"

            self.badge_free = ctk.CTkFrame(
                self.center_box,
                fg_color=badge_bg,
                border_width=1,
                border_color=badge_border,
                corner_radius=6
            )
            self.badge_free.pack(pady=(0, 2))
            self.lbl_free = ctk.CTkLabel(
                self.badge_free,
                text=badge_text,
                font=ctk.CTkFont(family=theme.FONT_FAMILY, size=theme.FONT_SIZE_SMALL, weight="normal"),
                text_color=badge_fg,
                cursor="hand2"
            )
            self.lbl_free.pack(padx=6, pady=2)

        else:
            # Boş Slot (+ Nöbetçi Ata - Davetkar yumuşak mavi stil)
            self.lbl_empty = ctk.CTkLabel(
                self.center_box,
                text="+ Nöbetçi Ata",
                font=ctk.CTkFont(family=theme.FONT_FAMILY, size=max(12, theme.FONT_SIZE_TEACHER - 2), weight="bold"),
                text_color=theme.COLOR_CELL_EMPTY_TXT,
                cursor="hand2"
            )
            self.lbl_empty.pack(expand=True, pady=10)

    def _bind_events(self):
        widgets_to_bind = [self, self._canvas, self.center_box]
        if hasattr(self.center_box, "_canvas"):
            widgets_to_bind.append(self.center_box._canvas)
        if hasattr(self, "name_container"):
            widgets_to_bind.append(self.name_container)
        if hasattr(self, "lbl_name"):
            widgets_to_bind.append(self.lbl_name)
        if hasattr(self, "lbl_branch"):
            widgets_to_bind.append(self.lbl_branch)
        if hasattr(self, "badge_free"):
            widgets_to_bind.append(self.badge_free)
        if hasattr(self, "lbl_free"):
            widgets_to_bind.append(self.lbl_free)
        if hasattr(self, "lbl_empty"):
            widgets_to_bind.append(self.lbl_empty)
        if hasattr(self, "badge_lock"):
            widgets_to_bind.append(self.badge_lock)
        if hasattr(self, "lbl_lock"):
            widgets_to_bind.append(self.lbl_lock)

        for w in widgets_to_bind:
            w.bind("<Button-1>", self._on_press)
            w.bind("<B1-Motion>", self._on_motion)
            w.bind("<ButtonRelease-1>", self._on_release)
            w.bind("<Button-3>", self._on_right_click)
            w.bind("<Double-Button-1>", self._on_double_click)
            w.bind("<Enter>", self._on_hover_enter, add="+")
            w.bind("<Leave>", self._on_hover_leave, add="+")

    def _on_hover_enter(self, event=None):
        if not self.is_selected and not self.assignment.fixed:
            if self.teacher:
                self.configure(fg_color="#F5F5F7", border_color="#E5E5EA")
            else:
                self.configure(fg_color="#EBF5FF", border_color="#007AFF")

    def _on_hover_leave(self, event=None):
        if not self.is_selected:
            bg_col = self._default_bg()
            border_col = self._default_border()
            self.configure(fg_color=bg_col, border_color=border_col)

    def _on_info_clicked(self):
        self.controller.select_cell(self, trigger_detail=True)
        self.controller.toggle_info_popover(self)

    def _on_press(self, event):
        self.controller.select_cell(self, trigger_detail=False)
        self.controller.close_info_popover()
        if not self.teacher or self.assignment.fixed:
            return
        self._press_x_root = getattr(event, "x_root", getattr(event, "x", 0))
        self._press_y_root = getattr(event, "y_root", getattr(event, "y", 0))
        self._is_dragging = False

    def _on_motion(self, event):
        if not self.teacher or self.assignment.fixed:
            return
        x_root = getattr(event, "x_root", getattr(event, "x", 0))
        y_root = getattr(event, "y_root", getattr(event, "y", 0))
        if not self._is_dragging:
            dx = x_root - self._press_x_root
            dy = y_root - self._press_y_root
            if (dx * dx + dy * dy) >= 36:  # 6 px hareket eşiği
                self._is_dragging = True
                self.controller.close_info_popover()
                self.controller.start_drag(self, event)
        if self._is_dragging:
            self.controller.on_drag_motion(event)

    def _on_release(self, event):
        if self._is_dragging:
            self._is_dragging = False
            self.controller.on_drag_release(event)
        # Normal sol tıklamada kart/bilgi balonu AÇILMAZ. Sadece hücre seçili kalır.

    def _on_right_click(self, event):
        self.controller.select_cell(self, trigger_detail=True)
        self.controller.close_info_popover()
        self.controller.show_context_menu(self, event)

    def _on_double_click(self, event):
        self.controller.select_cell(self, trigger_detail=True)
        if self.teacher:
            self.controller.toggle_info_popover(self)
        else:
            self.controller.open_teacher_picker(self)


class ScheduleGrid(ttk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        db: Database,
        duty_service: DutyService,
        get_current_week: Callable[[], str],
        on_data_changed: Callable[[], None],
        on_cell_selected: Optional[Callable[[CellWidget], None]] = None
    ):
        super().__init__(parent)
        self.db = db
        self.duty_service = duty_service
        self.sub_service = SubstitutionService(self.db)
        self.get_current_week = get_current_week
        self.on_data_changed = on_data_changed
        self.on_cell_selected = on_cell_selected

        self.selected_cell: Optional[CellWidget] = None
        self.drag_source_cell: Optional[CellWidget] = None
        self.drag_state: Optional[DragState] = None
        self.active_hover_cell: Optional[CellWidget] = None
        self.active_popover: Optional[TeacherInfoPopover] = None
        self.drag_ghost: Optional[DragGhostWindow] = None

        self._build_container()
        self.refresh()

    def close_info_popover(self):
        """Açık olan öğretmen bilgi penceresini (popover) kapatır."""
        if self.active_popover:
            try:
                self.active_popover.hide()
            except Exception:
                pass
            self.active_popover = None

    def toggle_info_popover(self, cell: CellWidget):
        """Belirtilen hücre için bilgi penceresini açar veya açıksa kapatır."""
        if self.active_popover and self.active_popover.cell == cell:
            self.close_info_popover()
            return
        self.close_info_popover()
        if cell.teacher:
            self.active_popover = TeacherInfoPopover(cell)
            self.active_popover.show()

    def select_cell(self, cell: CellWidget, trigger_detail: bool = False):
        """Hücre seçildiğinde görsel sınırları günceller; sadece istenirse (sağ tık) detay kartını açar."""
        if self.selected_cell and self.selected_cell != cell:
            try:
                self.selected_cell.set_selected(False)
            except Exception:
                pass
        self.selected_cell = cell
        cell.set_selected(True)
        if trigger_detail and self.on_cell_selected:
            self.on_cell_selected(cell)

    def deselect_cell(self):
        """Seçili hücreyi kaldırır."""
        if self.selected_cell:
            try:
                self.selected_cell.set_selected(False)
            except Exception:
                pass
            self.selected_cell = None

    def build_grid(self):
        """Arayüz yenileme takma adı."""
        self.refresh()

    def get_teacher_free_periods(self, teacher_id: str, day_name: str) -> List[int]:
        return self.sub_service.get_teacher_free_periods(teacher_id, day_name)

    def get_teacher_schedule(self, teacher_id: str, day_name: str) -> List[TeacherLesson]:
        return self.sub_service.get_teacher_schedule(teacher_id, day_name)

    def _build_container(self):
        # Boş hafta bildirim bandı (Önceki haftanın nöbetlerini hızlı aktarma)
        self.banner_frame = tk.Frame(self, bg="#EBF5FF", highlightbackground="#B9E1FF", highlightthickness=1)
        
        lbl_info = tk.Label(
            self.banner_frame,
            text="💡 Bu haftada henüz nöbet planlanmamış.",
            font=(FONT_FAMILY, 9, "bold"),
            fg="#007AFF",
            bg="#EBF5FF"
        )
        lbl_info.pack(side="left", padx=10, pady=5)

        btn_copy_same = tk.Button(
            self.banner_frame,
            text="📋 Önceki Haftanın Aynısını Aktar",
            font=(FONT_FAMILY, 8, "bold"),
            bg="#007AFF",
            fg="#FFFFFF",
            activebackground="#0062D2",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._banner_copy_same
        )
        btn_copy_same.pack(side="left", padx=4, pady=5)

        btn_copy_shift = tk.Button(
            self.banner_frame,
            text="🔄 1 Gün Kaydırarak Aktar",
            font=(FONT_FAMILY, 8, "bold"),
            bg="#34C759",
            fg="#FFFFFF",
            activebackground="#28A745",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._banner_copy_shift_day
        )
        btn_copy_shift.pack(side="left", padx=4, pady=5)

        btn_copy_loc = tk.Button(
            self.banner_frame,
            text="📍 Yerleri Kaydırarak Aktar",
            font=(FONT_FAMILY, 8),
            bg="#5856D6",
            fg="#FFFFFF",
            activebackground="#4745B8",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._banner_copy_shift_loc
        )
        btn_copy_loc.pack(side="left", padx=4, pady=5)

        # Kaydırılabilir tablo konteyneri
        self.canvas = tk.Canvas(self, bg=COLOR_BG, highlightthickness=0)
        self.scrollbar_y = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollbar_x = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        
        self.table_frame = tk.Frame(self.canvas, bg=COLOR_BG, bd=0, relief="flat")
        self.table_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.table_frame, anchor="nw")
        self.canvas.configure(xscrollcommand=self.scrollbar_x.set, yscrollcommand=self.scrollbar_y.set)

        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel)
        self.canvas.bind("<Button-1>", lambda e: self.close_info_popover(), add="+")
        self.table_frame.bind("<Button-1>", lambda e: self.close_info_popover(), add="+")

    def _banner_copy_same(self):
        week_start = self.get_current_week()
        cur_dt = datetime.date.fromisoformat(week_start)
        prev_week_str = (cur_dt - datetime.timedelta(days=7)).isoformat()
        if self.duty_service.copy_week_to_next(prev_week_str, week_start, shift_mode="same"):
            self.refresh()
            if self.on_data_changed:
                self.on_data_changed()

    def _banner_copy_shift_day(self):
        week_start = self.get_current_week()
        cur_dt = datetime.date.fromisoformat(week_start)
        prev_week_str = (cur_dt - datetime.timedelta(days=7)).isoformat()
        if self.duty_service.copy_week_to_next(prev_week_str, week_start, shift_mode="shift_day", shift_steps=1):
            self.refresh()
            if self.on_data_changed:
                self.on_data_changed()

    def _banner_copy_shift_loc(self):
        week_start = self.get_current_week()
        cur_dt = datetime.date.fromisoformat(week_start)
        prev_week_str = (cur_dt - datetime.timedelta(days=7)).isoformat()
        if self.duty_service.copy_week_to_next(prev_week_str, week_start, shift_mode="shift_loc", shift_steps=1):
            self.refresh()
            if self.on_data_changed:
                self.on_data_changed()

    def _on_canvas_configure(self, event):
        canvas_width = event.width
        canvas_height = event.height
        req_width = self.table_frame.winfo_reqwidth()
        req_height = self.table_frame.winfo_reqheight()

        min_width = 800
        min_height = 320

        # Yatay kaydırma çubuğu kontrolü: sadece pencere çok daraldığında görünsün
        if canvas_width >= min_width:
            new_width = canvas_width
            if self.scrollbar_x.winfo_ismapped():
                self.scrollbar_x.pack_forget()
        else:
            new_width = max(min_width, req_width)
            if not self.scrollbar_x.winfo_ismapped():
                self.scrollbar_x.pack(side="bottom", fill="x", before=self.canvas)

        # Dikey kaydırma çubuğu kontrolü: sadece pencere gerçekten küçüldüğünde çıksın
        if canvas_height >= min_height:
            new_height = canvas_height
            if self.scrollbar_y.winfo_ismapped():
                self.scrollbar_y.pack_forget()
        else:
            new_height = max(min_height, req_height)
            if not self.scrollbar_y.winfo_ismapped():
                self.scrollbar_y.pack(side="right", fill="y", before=self.canvas)

        self.canvas.itemconfig(self.canvas_window, width=new_width, height=new_height)

    def _on_mousewheel(self, event):
        try:
            if event.delta:
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    def _on_shift_mousewheel(self, event):
        try:
            if event.delta:
                self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    _shift_mousewheel = _on_shift_mousewheel

    def refresh(self):
        self.close_info_popover()
        if self.drag_ghost:
            try:
                self.drag_ghost.destroy()
            except Exception:
                pass
            self.drag_ghost = None

        # Mevcut çizelgeyi temizle
        for widget in self.table_frame.winfo_children():
            widget.destroy()

        self.selected_cell = None
        week_start = self.get_current_week()
        try:
            cur_dt = datetime.date.fromisoformat(week_start)
        except Exception:
            cur_dt = datetime.date.today()

        data = self.duty_service.get_grid_matrix(week_start)
        days = data["days"]
        locations = data["locations"]
        assign_map = data["assignments"]
        teachers = data["teachers"]

        # Boş hafta kontrolü ve bildirim bandı
        has_curr_duties = any(a.teacher_id for a in assign_map.values())
        try:
            prev_week_str = (cur_dt - datetime.timedelta(days=7)).isoformat()
            has_prev_duties = self.db.has_assigned_duties_for_week(prev_week_str)
        except Exception:
            has_prev_duties = False

        if not has_curr_duties and has_prev_duties:
            self.banner_frame.pack(side="top", fill="x", pady=(0, 6), before=self.canvas)
        else:
            self.banner_frame.pack_forget()

        if not days or not locations:
            lbl = tk.Label(
                self.table_frame,
                text="Görüntülenecek gün veya nöbet yeri bulunamadı.",
                font=(FONT_FAMILY, 11),
                bg=COLOR_BG
            )
            lbl.pack(pady=40)
            return

        # Sütun Başlıkları: Günler / Nöbet Yerleri (Apple Canvas #F5F5F7, 1px #E5E5EA)
        corner_frame = ctk.CTkFrame(
            self.table_frame,
            corner_radius=10,
            fg_color="#F5F5F7",
            border_width=1,
            border_color="#E5E5EA"
        )
        lbl_corner = ctk.CTkLabel(
            corner_frame,
            text="Gün / Nöbet Yeri",
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=theme.FONT_SIZE_HEADER, weight="bold"),
            text_color="#1D1D1F"
        )
        lbl_corner.pack(expand=True, fill="both", padx=6, pady=4)
        corner_frame.grid(row=0, column=0, sticky="nsew", padx=3, pady=3)

        col_idx = 1
        # Sütun başlıkları (Nöbet Yerleri ve Slotları - Açık gri-mavi #F1F5F9 zemin, ince border)
        loc_col_map: Dict[Tuple[str, int], int] = {}
        for loc in locations:
            for slot in range(loc.capacity):
                slot_label = loc.name
                if loc.capacity > 1:
                    slot_label += f" ({slot + 1})"
                icon = get_location_icon(loc.name)
                
                loc_frame = ctk.CTkFrame(
                    self.table_frame,
                    corner_radius=10,
                    fg_color="#F5F5F7",
                    border_width=1,
                    border_color="#E5E5EA"
                )
                lbl_loc = ctk.CTkLabel(
                    loc_frame,
                    text=f"{icon}{slot_label}",
                    font=ctk.CTkFont(family=theme.FONT_FAMILY, size=theme.FONT_SIZE_HEADER, weight="bold"),
                    text_color="#1D1D1F"
                )
                lbl_loc.pack(expand=True, fill="both", padx=6, pady=4)
                loc_frame.grid(row=0, column=col_idx, sticky="nsew", padx=3, pady=3)
                loc_col_map[(loc.id, slot)] = col_idx
                col_idx += 1

        # Satırlar (Günler - Açık gri-mavi #F1F5F9 zeminli, ~8px yuvarlak köşe)
        for row_idx, d in enumerate(days, start=1):
            day_dt = cur_dt + datetime.timedelta(days=row_idx - 1)
            month_name = TURKISH_MONTHS[day_dt.month] if 1 <= day_dt.month <= 12 else ""

            day_frame = ctk.CTkFrame(
                self.table_frame,
                corner_radius=10,
                fg_color="#F5F5F7",
                border_width=1,
                border_color="#E5E5EA"
            )
            day_center = ctk.CTkFrame(day_frame, fg_color="transparent")
            day_center.pack(expand=True)
            lbl_day_name = ctk.CTkLabel(
                day_center,
                text=d.name.upper(),
                font=ctk.CTkFont(family=theme.FONT_FAMILY, size=theme.FONT_SIZE_HEADER, weight="bold"),
                text_color="#1D1D1F"
            )
            lbl_day_name.pack(side="top", pady=(0, 1))
            lbl_day_date = ctk.CTkLabel(
                day_center,
                text=f"{day_dt.day} {month_name}",
                font=ctk.CTkFont(family=theme.FONT_FAMILY, size=theme.FONT_SIZE_SECONDARY),
                text_color="#86868B"
            )
            lbl_day_date.pack(side="top", pady=0)
            day_frame.grid(row=row_idx, column=0, sticky="nsew", padx=3, pady=3)

            # Slot Hücreleri (Hücre arası 6px boşluk: padx=3, pady=3)
            for loc in locations:
                for slot in range(loc.capacity):
                    col = loc_col_map[(loc.id, slot)]
                    assign = assign_map.get((d.id, loc.id, slot))
                    teacher_obj = teachers.get(assign.teacher_id) if assign and assign.teacher_id else None

                    cell = CellWidget(
                        parent=self.table_frame,
                        assignment=assign,
                        teacher=teacher_obj,
                        day=d,
                        location=loc,
                        slot_index=slot,
                        grid_controller=self
                    )
                    cell.grid(row=row_idx, column=col, sticky="nsew", padx=3, pady=3)

        # Izgara boyutlandırma ağırlıkları: sütunlar eşit genişlikte dağıtılır, satırlar pencereye göre esner
        self.table_frame.columnconfigure(0, weight=0, minsize=88)
        for c in range(1, col_idx):
            self.table_frame.columnconfigure(c, weight=1, uniform="duty_col")
        self.table_frame.rowconfigure(0, weight=0, minsize=34)
        for r in range(1, len(days) + 1):
            self.table_frame.rowconfigure(r, weight=1, uniform="day_row", minsize=68)

    # --- Sürükle ve Bırak (Drag & Drop) Mekanizması ---
    def is_valid_drop_target(self, source_cell: CellWidget, target_cell: CellWidget) -> Tuple[bool, str]:
        """
        Sürükleme sırasında hedef hücrenin geçerliliğini kontrol eder.
        Dönüş: (is_valid, reason)
        """
        if not source_cell or not target_cell:
            return False, "Geçersiz hedef"
        if source_cell == target_cell:
            return True, "Aynı Hücre"
        # 1. Kural: Hedef kilitli (sabit) ise bırakılamaz
        if target_cell.assignment.fixed:
            return False, "Hedef nöbet kilitlidir (Sabit Görev). Önce kilidi kaldırınız."

        week_start = self.get_current_week()
        assignments = self.db.get_assignments_for_week(week_start)

        # 2. Kural: Kaynak öğretmen hedef günde zaten başka bir nöbette görevli mi?
        if source_cell.day.id != target_cell.day.id and source_cell.teacher:
            same_day_duties = [
                a for a in assignments
                if a.day_id == target_cell.day.id and a.teacher_id == source_cell.teacher.id
            ]
            if same_day_duties:
                return False, f"{source_cell.teacher.name} {target_cell.day.name} gününde zaten başka bir nöbette görevlidir (Günde 1 Nöbet kuralı)."

        # 3. Kural: Hedef doluysa (takas), hedef öğretmen kaynak günde başka bir nöbette mi?
        if target_cell.teacher and source_cell.day.id != target_cell.day.id:
            tgt_same_day = [
                a for a in assignments
                if a.day_id == source_cell.day.id and a.teacher_id == target_cell.teacher.id
            ]
            if tgt_same_day:
                return False, f"{target_cell.teacher.name} {source_cell.day.name} gününde zaten başka bir nöbette görevlidir (Günde 1 Nöbet kuralı)."

        return True, "Geçerli"

    def start_drag(self, source_cell: CellWidget, event=None):
        self.close_info_popover()
        self.drag_source_cell = source_cell
        self.drag_state = DragState(
            source_assignment_id=source_cell.assignment.id,
            source_teacher_id=source_cell.teacher.id if source_cell.teacher else "",
            source_day_id=source_cell.day.id,
            source_location_id=source_cell.location.id,
            source_slot_index=source_cell.slot_index
        )
        source_cell.configure(fg_color=COLOR_CELL_DRAG, border_color="#93C5FD", border_width=2)

        # İmleci takip eden yarı saydam ghost rozet
        if source_cell.teacher:
            branch_str = source_cell.teacher.branch or ""
            self.drag_ghost = DragGhostWindow(self, source_cell.teacher.name, branch_str)
            if event:
                rx = getattr(event, "x_root", getattr(event, "x", 0))
                ry = getattr(event, "y_root", getattr(event, "y", 0))
                self.drag_ghost.move_to(rx, ry)

        logger.debug(f"Drag başlatıldı: {source_cell.teacher.name if source_cell.teacher else 'None'}")

    def on_drag_motion(self, event):
        if not self.drag_source_cell:
            return

        rx = getattr(event, "x_root", getattr(event, "x", 0))
        ry = getattr(event, "y_root", getattr(event, "y", 0))

        if self.drag_ghost:
            self.drag_ghost.move_to(rx, ry)

        # İmlecin altındaki widget'ı bul
        widget_under_cursor = self.winfo_containing(rx, ry)
        target_cell = self._find_cell_parent(widget_under_cursor)

        if target_cell != self.active_hover_cell:
            # Önceki hover rengini eski haline getir
            if self.active_hover_cell and self.active_hover_cell != self.drag_source_cell:
                orig_bg = self.active_hover_cell._default_bg()
                orig_border = self.active_hover_cell._default_border()
                self.active_hover_cell.configure(fg_color=orig_bg, border_color=orig_border, border_width=1)

            self.active_hover_cell = target_cell
            if target_cell and target_cell != self.drag_source_cell:
                is_valid, _ = self.is_valid_drop_target(self.drag_source_cell, target_cell)
                if is_valid:
                    # Geçerli hedef hücre: mavi kenarlık ve hafif mavi arka plan (#EFF6FF, #2563EB)
                    target_cell.configure(fg_color="#EBF5FF", border_color="#007AFF", border_width=2)
                else:
                    # Geçersiz hedef hücre: kırmızı kenarlık ve hafif kırmızı arka plan (#FEE2E2, #EF4444)
                    target_cell.configure(fg_color="#FEE2E2", border_color="#FF3B30", border_width=2)

    def on_drag_release(self, event):
        if self.drag_ghost:
            try:
                self.drag_ghost.destroy()
            except Exception:
                pass
            self.drag_ghost = None

        if not self.drag_source_cell:
            return

        rx = getattr(event, "x_root", getattr(event, "x", 0))
        ry = getattr(event, "y_root", getattr(event, "y", 0))
        widget_under_cursor = self.winfo_containing(rx, ry)
        target_cell = self._find_cell_parent(widget_under_cursor)

        # Görsel vurguları sıfırla
        if self.active_hover_cell:
            orig_bg = self.active_hover_cell._default_bg()
            orig_border = self.active_hover_cell._default_border()
            self.active_hover_cell.configure(fg_color=orig_bg, border_color=orig_border, border_width=1)
            self.active_hover_cell = None

        source = self.drag_source_cell
        self.drag_source_cell = None

        if not target_cell or target_cell == source:
            self.refresh()
            return

        # 1. Kural: Geçerlilik kontrolü
        is_valid, reason = self.is_valid_drop_target(source, target_cell)
        if not is_valid:
            messagebox.showwarning(
                "Geçersiz Taşıma",
                f"Nöbet taşıma işlemi kurallara aykırı olduğu için reddedildi:\n\n{reason}"
            )
            self.refresh()
            return

        # 2. Taşıma / Takas İcrası
        week_start = self.get_current_week()
        success = self.duty_service.move_or_swap(
            week_start=week_start,
            source_day_id=source.day.id,
            source_loc_id=source.location.id,
            source_slot=source.slot_index,
            target_day_id=target_cell.day.id,
            target_loc_id=target_cell.location.id,
            target_slot=target_cell.slot_index
        )

        if success:
            self.on_data_changed()
        else:
            err = getattr(self.duty_service, "last_error", None) or "Nöbet taşıma kural ihlali nedeniyle tamamlanamadı."
            messagebox.showwarning("Kural İhlali / Çakışma", err)

        self.refresh()

    def _find_cell_parent(self, widget: Optional[tk.Widget]) -> Optional[CellWidget]:
        curr = widget
        while curr:
            if isinstance(curr, CellWidget):
                return curr
            curr = getattr(curr, "master", None)
        return None

    # --- Sağ Tık Menüsü & Alternatif Taşıma İşlemleri ---
    def show_context_menu(self, cell: CellWidget, event):
        menu = tk.Menu(self, tearoff=0)

        if cell.teacher:
            menu.add_command(
                label=f"📋 '{cell.teacher.name}' Nöbet ve Ders Kartı",
                command=lambda: self.on_cell_selected(cell) if self.on_cell_selected else None
            )
            menu.add_separator()
            menu.add_command(
                label=f"➡️ '{cell.teacher.name}' Öğretmenini Taşı...",
                command=lambda: self.open_move_dialog(cell)
            )
            menu.add_command(
                label=f"🔄 '{cell.teacher.name}' Öğretmenini Takas Et...",
                command=lambda: self.open_swap_dialog(cell)
            )
            menu.add_separator()
            fixed_label = "🔓 Nöbet Kilidini Aç" if cell.assignment.fixed else "🔒 Nöbeti Sabitle"
            menu.add_command(
                label=fixed_label,
                command=lambda: self.toggle_cell_fixed(cell)
            )
            menu.add_separator()
            menu.add_command(
                label="👤 Öğretmeni Değiştir...",
                command=lambda: self.open_teacher_picker(cell)
            )
            menu.add_command(
                label="❌ Atamayı Temizle",
                command=lambda: self.clear_cell(cell)
            )
        else:
            menu.add_command(
                label="➕ Öğretmen Ata...",
                command=lambda: self.open_teacher_picker(cell)
            )

        menu.tk_popup(event.x_root, event.y_root)

    def toggle_cell_fixed(self, cell: CellWidget):
        self.duty_service.toggle_fixed(cell.assignment.id)
        self.on_data_changed()
        self.refresh()

    def clear_cell(self, cell: CellWidget):
        if cell.assignment.fixed:
            messagebox.showwarning("Sabit Nöbet", "Sabit nöbet silinemez. Önce kilidi açınız.")
            return
        self.duty_service.assign_teacher(cell.assignment, None)
        self.on_data_changed()
        self.refresh()

    def open_teacher_picker(self, cell: CellWidget):
        if cell.assignment.fixed:
            messagebox.showwarning("Sabit Nöbet", "Sabit nöbet değiştirilemez. Önce kilidi kaldırınız.")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Öğretmen Seçimi")
        dialog.geometry("380x450")
        dialog.transient(self)
        dialog.grab_set()

        lbl_info = tk.Label(
            dialog,
            text=f"{cell.day.name} - {cell.location.name} (Slot {cell.slot_index + 1})",
            font=(FONT_FAMILY, 10, "bold"),
            fg=COLOR_PRIMARY
        )
        lbl_info.pack(pady=10)

        # Arama kutusu
        search_var = tk.StringVar()
        entry_search = ttk.Entry(dialog, textvariable=search_var)
        entry_search.pack(fill="x", padx=15, pady=(0, 5))

        listbox = tk.Listbox(dialog, font=(FONT_FAMILY, 10))
        listbox.pack(fill="both", expand=True, padx=15, pady=5)

        teachers = self.db.get_teachers(active_only=True)

        def populate(query=""):
            listbox.delete(0, tk.END)
            listbox.insert(tk.END, "[Boş Bırak / Temizle]")
            for t in teachers:
                if query.lower() in t.name.lower() or query.lower() in t.branch.lower():
                    branch_info = f" ({t.branch})" if t.branch else ""
                    listbox.insert(tk.END, f"{t.name}{branch_info}")

        populate()
        search_var.trace_add("write", lambda *args: populate(search_var.get()))

        def on_select():
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            if idx == 0:
                self.duty_service.assign_teacher(cell.assignment, None)
            else:
                # Seçilen öğretmen
                chosen_text = listbox.get(idx)
                chosen_name = chosen_text.split(" (")[0]
                matched_t = next((t for t in teachers if t.name == chosen_name), None)
                if matched_t:
                    ok = self.duty_service.assign_teacher(cell.assignment, matched_t.id)
                    if not ok and getattr(self.duty_service, "last_error", None):
                        messagebox.showwarning("Kural İhlali / Çakışma", self.duty_service.last_error, parent=dialog)
                        return

            dialog.destroy()
            self.on_data_changed()
            self.refresh()

        btn_select = ttk.Button(dialog, text="Seç ve Ata", style="Primary.TButton", command=on_select)
        btn_select.pack(pady=10)

    def open_move_dialog(self, source_cell: CellWidget):
        if not source_cell.teacher or source_cell.assignment.fixed:
            return

        dialog = tk.Toplevel(self)
        dialog.title("Öğretmeni Taşı")
        dialog.geometry("380x320")
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(
            dialog,
            text=f"Taşınacak Öğretmen:\n{source_cell.teacher.name}",
            font=(FONT_FAMILY, 10, "bold"),
            fg=COLOR_PRIMARY
        ).pack(pady=10)

        days = self.db.get_days()
        locations = self.db.get_locations(active_only=True)

        frame_fields = ttk.Frame(dialog, padding=15)
        frame_fields.pack(fill="both", expand=True)

        ttk.Label(frame_fields, text="Hedef Gün:").grid(row=0, column=0, sticky="w", pady=5)
        day_cb = ttk.Combobox(frame_fields, values=[d.name for d in days], state="readonly")
        day_cb.set(source_cell.day.name)
        day_cb.grid(row=0, column=1, sticky="ew", pady=5)

        ttk.Label(frame_fields, text="Hedef Nöbet Yeri:").grid(row=1, column=0, sticky="w", pady=5)
        loc_cb = ttk.Combobox(frame_fields, values=[loc.name for loc in locations], state="readonly")
        loc_cb.set(source_cell.location.name)
        loc_cb.grid(row=1, column=1, sticky="ew", pady=5)

        frame_fields.columnconfigure(1, weight=1)

        def do_move():
            target_day = next((d for d in days if d.name == day_cb.get()), None)
            target_loc = next((l for l in locations if l.name == loc_cb.get()), None)
            if not target_day or not target_loc:
                return

            week_start = self.get_current_week()
            self.duty_service.move_or_swap(
                week_start=week_start,
                source_day_id=source_cell.day.id,
                source_loc_id=source_cell.location.id,
                source_slot=source_cell.slot_index,
                target_day_id=target_day.id,
                target_loc_id=target_loc.id,
                target_slot=0
            )
            dialog.destroy()
            self.on_data_changed()
            self.refresh()

        btn_ok = ttk.Button(dialog, text="Taşı / Takas Et", style="Primary.TButton", command=do_move)
        btn_ok.pack(pady=15)

    def open_swap_dialog(self, source_cell: CellWidget):
        if not source_cell.teacher or source_cell.assignment.fixed:
            return

        dialog = tk.Toplevel(self)
        dialog.title("Öğretmenleri Takas Et")
        dialog.geometry("420x450")
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(
            dialog,
            text=f"Kaynak: {source_cell.teacher.name} ({source_cell.day.name} - {source_cell.location.name})\nKimle takas etmek istiyorsunuz?",
            font=(FONT_FAMILY, 9, "bold"),
            fg=COLOR_PRIMARY
        ).pack(pady=10)

        week_start = self.get_current_week()
        data = self.duty_service.get_grid_matrix(week_start)
        assign_map = data["assignments"]
        teachers = data["teachers"]
        days_dict = {d.id: d for d in data["days"]}
        locs_dict = {l.id: l for l in data["locations"]}

        listbox = tk.Listbox(dialog, font=(FONT_FAMILY, 9))
        listbox.pack(fill="both", expand=True, padx=15, pady=5)

        swap_targets = []
        for (d_id, l_id, s_idx), a in assign_map.items():
            if a.id == source_cell.assignment.id or a.fixed or not a.teacher_id:
                continue
            t_obj = teachers.get(a.teacher_id)
            if t_obj:
                d_name = days_dict[d_id].name if d_id in days_dict else ""
                l_name = locs_dict[l_id].name if l_id in locs_dict else ""
                label = f"{t_obj.name} -> {d_name} / {l_name} (Slot {s_idx + 1})"
                listbox.insert(tk.END, label)
                swap_targets.append((d_id, l_id, s_idx))

        def do_swap():
            sel = listbox.curselection()
            if not sel:
                return
            tgt_d_id, tgt_l_id, tgt_s_idx = swap_targets[sel[0]]
            self.duty_service.move_or_swap(
                week_start=week_start,
                source_day_id=source_cell.day.id,
                source_loc_id=source_cell.location.id,
                source_slot=source_cell.slot_index,
                target_day_id=tgt_d_id,
                target_loc_id=tgt_l_id,
                target_slot=tgt_s_idx
            )
            dialog.destroy()
            self.on_data_changed()
            self.refresh()

        btn_ok = ttk.Button(dialog, text="Seçilen Öğretmenle Takas Et", style="Primary.TButton", command=do_swap)
        btn_ok.pack(pady=15)
