"""
Haftalık Nöbet Çizelgesi Tablosu
Sürükle-bırak (Drag & Drop), Takas (Swap), Sabitleme ve Sağ Tık Alternatifi.
"""
import tkinter as tk
from tkinter import ttk, messagebox
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


class GridTooltip:
    """
    Hücre üzerine gelindiğinde öğretmenin o günkü 7 saatlik ders programını
    ve boş ders saatlerini gösteren zengin tooltip penceresi.
    """
    def __init__(self, widgets: List[tk.Widget], text_func: Callable[[], Optional[str]]):
        self.widgets = widgets
        self.text_func = text_func
        self.tip_window = None
        self._after_id = None
        for w in self.widgets:
            w.bind("<Enter>", self._on_enter, add="+")
            w.bind("<Leave>", self._on_leave, add="+")
            w.bind("<ButtonPress>", self.hide_tip, add="+")

    def _on_enter(self, event=None):
        self._cancel()
        if self.widgets:
            self._after_id = self.widgets[0].after(180, self.show_tip)

    def _on_leave(self, event=None):
        self._cancel()
        if self.widgets:
            self._after_id = self.widgets[0].after(120, self.hide_tip)

    def _cancel(self):
        if self._after_id and self.widgets:
            try:
                self.widgets[0].after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def show_tip(self):
        if self.tip_window or not self.text_func or not self.widgets:
            return
        text = self.text_func()
        if not text:
            return
        try:
            x = self.widgets[0].winfo_rootx() + 20
            y = self.widgets[0].winfo_rooty() + self.widgets[0].winfo_height() + 4
            self.tip_window = tw = tk.Toplevel(self.widgets[0])
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            tw.attributes("-topmost", True)
            frame = tk.Frame(tw, bg="#0F172A", relief="solid", bd=1)
            frame.pack()
            lbl = tk.Label(
                frame,
                text=text,
                justify="left",
                bg="#0F172A",
                fg="#F8FAFC",
                font=(FONT_FAMILY, 8),
                padx=10,
                pady=7
            )
            lbl.pack()
        except Exception:
            pass

    def hide_tip(self, event=None):
        self._cancel()
        if self.tip_window:
            try:
                self.tip_window.destroy()
            except Exception:
                pass
            self.tip_window = None

class CellWidget(tk.Frame):
    """
    Çizelgedeki tek bir nöbet slotunu temsil eden kart widget'ı.
    Modern okul yönetim paneli kart tasarımı: 1px ince sınır, net tipografi ve durum rozetleri.
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
        self._drag_started = False
        self._drag_start_x = 0
        self._drag_start_y = 0

        card_bg = self._default_bg()
        border_col = theme.COLOR_FIXED_BORDER if assignment.fixed else theme.GRID_BORDER_COLOR
        super().__init__(
            parent,
            bg=card_bg,
            relief=theme.GRID_RELIEF,
            bd=theme.GRID_BORDER_WIDTH,
            highlightbackground=border_col,
            highlightthickness=1
        )

        self._build_ui()
        self._bind_events()

    def _default_bg(self) -> str:
        if self.assignment.fixed:
            return COLOR_FIXED
        elif self.teacher:
            return COLOR_CARD
        return COLOR_CELL_EMPTY

    def set_selected(self, selected: bool):
        self.is_selected = selected
        if selected:
            self.configure(
                bg=theme.COLOR_CELL_SELECTED,
                highlightbackground=theme.COLOR_CELL_SELECTED_BORDER,
                highlightcolor=theme.COLOR_CELL_SELECTED_BORDER,
                highlightthickness=2
            )
            if hasattr(self, "lbl_name"):
                self.lbl_name.configure(bg=theme.COLOR_CELL_SELECTED)
            if hasattr(self, "lbl_branch"):
                self.lbl_branch.configure(bg=theme.COLOR_CELL_SELECTED)
        else:
            bg_col = self._default_bg()
            border_col = theme.COLOR_FIXED_BORDER if self.assignment.fixed else theme.GRID_BORDER_COLOR
            self.configure(
                bg=bg_col,
                highlightbackground=border_col,
                highlightcolor=border_col,
                highlightthickness=1
            )
            if hasattr(self, "lbl_name"):
                self.lbl_name.configure(bg=bg_col)
            if hasattr(self, "lbl_branch"):
                self.lbl_branch.configure(bg=bg_col)

    def _build_ui(self):
        bg_color = self._default_bg()
        border_col = theme.COLOR_FIXED_BORDER if self.assignment.fixed else theme.GRID_BORDER_COLOR
        self.configure(
            bg=bg_color,
            relief=theme.GRID_RELIEF,
            bd=theme.GRID_BORDER_WIDTH,
            highlightbackground=border_col,
            highlightthickness=1
        )

        # Üst Satır (Sabit Nöbet Rozeti)
        if self.assignment.fixed:
            top_frame = tk.Frame(self, bg=bg_color)
            top_frame.pack(fill="x", padx=4, pady=(2, 0))
            lbl_lock = tk.Label(
                top_frame,
                text="🔒 Sabit",
                font=(theme.FONT_FAMILY, max(7, theme.FONT_SIZE_BASE - 2), "bold"),
                fg="#B45309",
                bg="#FEF3C7",
                padx=4,
                pady=1
            )
            lbl_lock.pack(side="right")

        # Öğretmen Adı
        if self.teacher:
            name_text = self.teacher.name
            fg_color = COLOR_TEXT_MAIN
            font_spec = (theme.FONT_FAMILY, theme.FONT_SIZE_BASE, "bold")
        else:
            name_text = "+ Boş Slot"
            fg_color = "#94A3B8"
            font_spec = (theme.FONT_FAMILY, max(7, theme.FONT_SIZE_BASE - 1), "italic")

        self.lbl_name = tk.Label(
            self,
            text=name_text,
            font=font_spec,
            fg=fg_color,
            bg=bg_color,
            wraplength=125,
            justify="center",
            cursor="hand2"
        )
        self.lbl_name.pack(expand=True, fill="both", padx=4, pady=(4, 1))

        # Branş Bilgisi
        if self.teacher and self.teacher.branch:
            self.lbl_branch = tk.Label(
                self,
                text=f"◉ {self.teacher.branch}",
                font=(theme.FONT_FAMILY, max(7, theme.FONT_SIZE_BASE - 2)),
                fg=COLOR_TEXT_MUTED,
                bg=bg_color,
                cursor="hand2"
            )
            self.lbl_branch.pack(fill="x", side="bottom", pady=(0, 2))

        # Boş Dersler Bilgisi (Nöbet Gününde Boş Olduğu Ders Saatleri - Küçük Şık Yeşil Rozet)
        if self.teacher:
            free_periods = self.controller.get_teacher_free_periods(self.teacher.id, self.day.name)
            if free_periods:
                free_str = ", ".join(map(str, free_periods))
                f_badge = tk.Frame(self, bg=theme.COLOR_BADGE_FREE)
                f_badge.pack(fill="x", side="bottom", padx=4, pady=(1, 3))
                self.lbl_free = tk.Label(
                    f_badge,
                    text=f"🟢 Boş: {free_str}. Ders",
                    font=(theme.FONT_FAMILY, max(7, theme.FONT_SIZE_BASE - 2), "bold"),
                    fg=theme.COLOR_BADGE_FREE_TXT,
                    bg=theme.COLOR_BADGE_FREE,
                    cursor="hand2",
                    pady=1
                )
                self.lbl_free.pack(fill="x")

    def _bind_events(self):
        widgets = [self, self.lbl_name]
        if hasattr(self, "lbl_branch"):
            widgets.append(self.lbl_branch)
        if hasattr(self, "lbl_free"):
            widgets.append(self.lbl_free)

        for w in widgets:
            w.bind("<Button-1>", self._on_press)
            w.bind("<B1-Motion>", self._on_motion)
            w.bind("<ButtonRelease-1>", self._on_release)
            w.bind("<Button-3>", self._on_right_click)
            w.bind("<Double-Button-1>", self._on_double_click)

        self.tooltip = GridTooltip(widgets, self._get_tooltip_text)

    def _get_tooltip_text(self) -> Optional[str]:
        if not self.teacher:
            return None
        lessons = self.controller.get_teacher_schedule(self.teacher.id, self.day.name)
        if not lessons:
            return f"👤 {self.teacher.name} ({self.teacher.branch})\n📍 Nöbet Yeri: {self.location.name} | Gün: {self.day.name}"

        lines = [
            f"👤 {self.teacher.name} ({self.teacher.branch})",
            f"📍 Nöbet Yeri: {self.location.name} | Gün: {self.day.name}",
            "─" * 40
        ]
        free_count = 0
        for l in lessons:
            time_str = PERIOD_TIMES.get(l.period, "")
            if l.is_free:
                lines.append(f"  {l.period}. Ders ({time_str}): [BOŞ DERS] 🟢")
                free_count += 1
            else:
                lines.append(f"  {l.period}. Ders ({time_str}): {l.class_name} ({l.subject_code})")
        lines.append("─" * 40)
        lines.append(f"Toplam Boş Ders: {free_count} Saat (İkameye Uygun)")
        return "\n".join(lines)

    def _on_press(self, event):
        self.controller.select_cell(self)
        if not self.teacher or self.assignment.fixed:
            return
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        self._drag_started = False

    def _on_motion(self, event):
        if not self.teacher or self.assignment.fixed:
            return
        if not self._drag_started:
            if abs(event.x - self._drag_start_x) > 4 or abs(event.y - self._drag_start_y) > 4:
                self._drag_started = True
                self.controller.start_drag(self)
        if self._drag_started:
            self.controller.on_drag_motion(event)

    def _on_release(self, event):
        if self._drag_started:
            self.controller.on_drag_release(event)
        self._drag_started = False

    def _on_right_click(self, event):
        self.controller.select_cell(self)
        self.controller.show_context_menu(self, event)

    def _on_double_click(self, event):
        self.controller.select_cell(self)
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

        self._build_container()
        self.refresh()

    def select_cell(self, cell: CellWidget):
        """Hücre seçildiğinde görsel sınırları günceller ve üst kontrolcüye haber verir."""
        if self.selected_cell and self.selected_cell != cell:
            try:
                self.selected_cell.set_selected(False)
            except Exception:
                pass
        self.selected_cell = cell
        cell.set_selected(True)
        if self.on_cell_selected:
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
        self.banner_frame = tk.Frame(self, bg="#EFF6FF", highlightbackground="#BFDBFE", highlightthickness=1)
        
        lbl_info = tk.Label(
            self.banner_frame,
            text="💡 Bu haftada henüz nöbet planlanmamış.",
            font=(FONT_FAMILY, 9, "bold"),
            fg="#1E40AF",
            bg="#EFF6FF"
        )
        lbl_info.pack(side="left", padx=10, pady=5)

        btn_copy_same = tk.Button(
            self.banner_frame,
            text="📋 Önceki Haftanın Aynısını Aktar",
            font=(FONT_FAMILY, 8, "bold"),
            bg="#2563EB",
            fg="#FFFFFF",
            activebackground="#1D4ED8",
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
            bg="#059669",
            fg="#FFFFFF",
            activebackground="#047857",
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
            bg="#475569",
            fg="#FFFFFF",
            activebackground="#334155",
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
        
        self.table_frame = tk.Frame(self.canvas, bg=COLOR_BORDER_STRONG, bd=1, relief="solid")
        self.table_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.table_frame, anchor="nw")
        self.canvas.configure(xscrollcommand=self.scrollbar_x.set, yscrollcommand=self.scrollbar_y.set)

        self.scrollbar_y.pack(side="right", fill="y")
        self.scrollbar_x.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel)

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
        req_width = self.table_frame.winfo_reqwidth()
        new_width = max(canvas_width, req_width)
        self.canvas.itemconfig(self.canvas_window, width=new_width)

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

    def refresh(self):
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

        # Sütun Başlıkları: Günler / Nöbet Yerleri
        # Sütun Başlıkları: Günler / Nöbet Yerleri
        lbl_corner = tk.Label(
            self.table_frame,
            text="📍 Nöbet Yerleri ➔",
            font=(theme.FONT_FAMILY, max(8, theme.FONT_SIZE_BASE), "bold"),
            bg="#0F172A",
            fg="#F8FAFC",
            relief="solid",
            bd=theme.GRID_BORDER_WIDTH,
            highlightbackground=theme.GRID_BORDER_COLOR,
            highlightthickness=1,
            padx=8,
            pady=8
        )
        lbl_corner.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        col_idx = 1
        # Sütun başlıkları (Nöbet Yerleri ve Slotları)
        loc_col_map: Dict[Tuple[str, int], int] = {}
        for loc in locations:
            for slot in range(loc.capacity):
                slot_label = loc.name
                if loc.capacity > 1:
                    slot_label += f" ({slot + 1})"
                icon = get_location_icon(loc.name)
                
                lbl_loc = tk.Label(
                    self.table_frame,
                    text=f"{icon}{slot_label}",
                    font=(theme.FONT_FAMILY, max(8, theme.FONT_SIZE_BASE), "bold"),
                    bg="#1E293B",
                    fg="#F8FAFC",
                    relief="solid",
                    bd=theme.GRID_BORDER_WIDTH,
                    highlightbackground=theme.GRID_BORDER_COLOR,
                    highlightthickness=1,
                    padx=6,
                    pady=8,
                    width=14
                )
                lbl_loc.grid(row=0, column=col_idx, sticky="nsew", padx=1, pady=1)
                loc_col_map[(loc.id, slot)] = col_idx
                col_idx += 1

        # Satırlar (Günler - 2 Satırlı Gün Adı + Tarih)
        for row_idx, d in enumerate(days, start=1):
            day_dt = cur_dt + datetime.timedelta(days=row_idx - 1)
            month_name = TURKISH_MONTHS[day_dt.month] if 1 <= day_dt.month <= 12 else ""
            day_label_text = f"{d.name.upper()}\n{day_dt.day} {month_name}"

            lbl_day = tk.Label(
                self.table_frame,
                text=day_label_text,
                font=(theme.FONT_FAMILY, max(8, theme.FONT_SIZE_BASE), "bold"),
                bg="#F1F5F9",
                fg="#0F172A",
                relief="solid",
                bd=theme.GRID_BORDER_WIDTH,
                highlightbackground=theme.GRID_BORDER_COLOR,
                highlightthickness=1,
                padx=8,
                pady=6,
                width=11,
                justify="center"
            )
            lbl_day.grid(row=row_idx, column=0, sticky="nsew", padx=1, pady=1)

            # Slot Hücreleri
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
                    cell.grid(row=row_idx, column=col, sticky="nsew", padx=1, pady=1)

        # Izgara boyutlandırma ağırlıkları
        for c in range(col_idx):
            self.table_frame.columnconfigure(c, weight=1)
        for r in range(len(days) + 1):
            self.table_frame.rowconfigure(r, weight=1)

    # --- Sürükle ve Bırak (Drag & Drop) Mekanizması ---
    def start_drag(self, source_cell: CellWidget):
        self.drag_source_cell = source_cell
        self.drag_state = DragState(
            source_assignment_id=source_cell.assignment.id,
            source_teacher_id=source_cell.teacher.id if source_cell.teacher else "",
            source_day_id=source_cell.day.id,
            source_location_id=source_cell.location.id,
            source_slot_index=source_cell.slot_index
        )
        source_cell.configure(bg=COLOR_CELL_DRAG)
        logger.debug(f"Drag başlatıldı: {source_cell.teacher.name if source_cell.teacher else 'None'}")

    def on_drag_motion(self, event):
        if not self.drag_source_cell:
            return

        # İmlecin altındaki widget'ı bul
        widget_under_cursor = self.winfo_containing(event.x_root, event.y_root)
        target_cell = self._find_cell_parent(widget_under_cursor)

        if target_cell != self.active_hover_cell:
            # Önceki hover rengini eski haline getir
            if self.active_hover_cell and self.active_hover_cell != self.drag_source_cell:
                orig_bg = COLOR_FIXED if self.active_hover_cell.assignment.fixed else (COLOR_CARD if self.active_hover_cell.teacher else COLOR_CELL_EMPTY)
                self.active_hover_cell.configure(bg=orig_bg)
            
            self.active_hover_cell = target_cell
            if target_cell and target_cell != self.drag_source_cell:
                target_cell.configure(bg=COLOR_CELL_HOVER)

    def on_drag_release(self, event):
        if not self.drag_source_cell:
            return

        widget_under_cursor = self.winfo_containing(event.x_root, event.y_root)
        target_cell = self._find_cell_parent(widget_under_cursor)

        # Görsel vurguları sıfırla
        if self.active_hover_cell:
            orig_bg = COLOR_FIXED if self.active_hover_cell.assignment.fixed else (COLOR_CARD if self.active_hover_cell.teacher else COLOR_CELL_EMPTY)
            self.active_hover_cell.configure(bg=orig_bg)
            self.active_hover_cell = None

        source = self.drag_source_cell
        self.drag_source_cell = None

        if not target_cell:
            self.refresh()
            return

        # 1. Kural: Aynı hücreye bırakıldıysa NO-OP (hiçbir işlem yapma, hata verme)
        if (target_cell.day.id == source.day.id and
            target_cell.location.id == source.location.id and
            target_cell.slot_index == source.slot_index):
            self.refresh()
            return

        # 2. Kural: Hedef kilitli (sabit) ise taşıma/takas yapma
        if target_cell.assignment.fixed:
            messagebox.showwarning(
                "Sabit Nöbet",
                f"{target_cell.day.name} {target_cell.location.name} hücresindeki nöbet kilitlidir. Önce kilidi kaldırınız."
            )
            self.refresh()
            return

        # 3. Kural: Dolu hücreye bırakma = TAKAS (SWAP), Boş hücreye bırakma = TAŞIMA
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
                    self.duty_service.assign_teacher(cell.assignment, matched_t.id)

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
