"""
UI Teması ve Stil Tanımları (Modern Educational & Professional Academic Dashboard)
Tailwind CSS Slate & Indigo/Emerald estetiği ile optimize edilmiş arayüz:
- Modern Slate Arka Plan (#F8FAFC)
- Profesyonel Kurumsal Lacivert Başlık (#0F172A)
- Canlı ve Güven Veren Aksiyon Mavisi (#2563EB) ve Zümrüt Yeşili (#059669)
- Yumuşak, modern kart sınırları (#E2E8F0) ve yüksek kontrastlı tipografi (#0F172A)
"""
import tkinter as tk
from tkinter import ttk

# Modern Renk Paleti (Tailwind Slate & Emerald / Blue)
COLOR_BG = "#F8FAFC"             # Slate-50: Ferah, temiz çalışma alanı
COLOR_CARD = "#FFFFFF"           # Pure White kart yüzeyleri
COLOR_PRIMARY = "#2563EB"        # Blue-600: Güvenilir kurumsal aksiyon rengi
COLOR_PRIMARY_HOVER = "#1D4ED8"  # Blue-700
COLOR_PRIMARY_ACTIVE = "#1E40AF"
COLOR_SECONDARY = "#0284C7"      # Sky-600
COLOR_SUCCESS = "#059669"        # Emerald-600: Canlı, net onay yeşili
COLOR_SUCCESS_HOVER = "#047857"  # Emerald-700
COLOR_WARNING = "#D97706"        # Amber-600
COLOR_DANGER = "#DC2626"         # Red-600
COLOR_BORDER = "#E2E8F0"         # Slate-200: Gözü yormayan yumuşak sınır
COLOR_BORDER_STRONG = "#CBD5E1"  # Slate-300
COLOR_TEXT_MAIN = "#0F172A"      # Slate-900: Derin, net tipografi
COLOR_TEXT_MUTED = "#64748B"     # Slate-500: İkincil açıklamalar
COLOR_HEADER_BG = "#0F172A"      # Slate-900: Kurumsal derin grafit
COLOR_HEADER_TEXT = "#FFFFFF"
COLOR_FIXED = "#FEF3C7"          # Amber-100: Sabit nöbet kibar sarı
COLOR_FIXED_BORDER = "#F59E0B"   # Amber-500: Sabit nöbet turuncu sınır
COLOR_CELL_BG = "#FFFFFF"        # Beyaz kart görünümü
COLOR_CELL_EMPTY = "#F8FAFC"     # Boş slot zemini
COLOR_CELL_HOVER = "#EFF6FF"     # Blue-50: Hücre üzerine gelme rengi
COLOR_CELL_DRAG = "#DBEAFE"      # Blue-100: Sürükleme vurgusu
COLOR_CELL_SELECTED = "#EFF6FF"  # Seçili hücre hafif mavi
COLOR_CELL_SELECTED_BORDER = "#2563EB" # Seçili hücre canlı mavi sınır

COLOR_SIDEBAR_BG = "#0F172A"      # Koyu lacivert modern sidebar
COLOR_SIDEBAR_HOVER = "#1E293B"   # Sidebar hover
COLOR_SIDEBAR_ACTIVE = "#2563EB"  # Sidebar aktif menü
COLOR_SIDEBAR_TEXT = "#F8FAFC"
COLOR_SIDEBAR_MUTED = "#94A3B8"

COLOR_BADGE_FREE = "#DCFCE7"
COLOR_BADGE_FREE_TXT = "#15803D"
COLOR_BADGE_FIXED = "#FEF3C7"
COLOR_BADGE_FIXED_TXT = "#B45309"
COLOR_BADGE_EMPTY = "#FEE2E2"
COLOR_BADGE_EMPTY_TXT = "#B91C1C"

FONT_FAMILY = "Segoe UI"
FONT_SIZE_BASE = 9
FONT_SIZE_UI = 10

# Tablo Ayırıcı Çizgi Ayarları (Grid Borders)
GRID_BORDER_COLOR = "#CBD5E1"
GRID_BORDER_WIDTH = 1
GRID_RELIEF = "solid"

def load_theme_settings(db=None):
    """Veritabanından kullanıcı yazı tipi ve tablo çizgisi tercihlerini yükler."""
    global FONT_FAMILY, FONT_SIZE_BASE, FONT_SIZE_UI, GRID_BORDER_COLOR, GRID_BORDER_WIDTH, GRID_RELIEF
    if db:
        try:
            fam = db.get_setting("font_family", "Segoe UI")
            if fam:
                FONT_FAMILY = fam
            size_str = db.get_setting("font_size", "9")
            if size_str and size_str.isdigit():
                FONT_SIZE_BASE = max(7, min(16, int(size_str)))
            ui_size_str = db.get_setting("ui_font_size", "10")
            if ui_size_str and ui_size_str.isdigit():
                FONT_SIZE_UI = max(8, min(14, int(ui_size_str)))
            col = db.get_setting("grid_border_color", "#CBD5E1")
            if col:
                GRID_BORDER_COLOR = col
            w_str = db.get_setting("grid_border_width", "1")
            if w_str and w_str.isdigit():
                GRID_BORDER_WIDTH = max(1, min(4, int(w_str)))
        except Exception:
            pass

def setup_customtkinter():
    """CustomTkinter genel tema ve görünüm ayarlarını yapılandırır."""
    try:
        import customtkinter as ctk
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
    except Exception as e:
        pass

def setup_styles(root: tk.Tk, db=None):
    load_theme_settings(db)
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")

    # Genel Pencere Zemini
    root.configure(bg=COLOR_BG)

    # Tkinter Named Fonts güncelle (Tüm menüler, diyaloglar ve varsayılan widgetlar için)
    try:
        import tkinter.font as tkfont
        for name in ["TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont", "TkTooltipFont"]:
            try:
                f = tkfont.nametofont(name)
                f.configure(family=FONT_FAMILY, size=FONT_SIZE_UI)
            except Exception:
                pass
    except Exception:
        pass

    # Frame Stilleri
    style.configure("TFrame", background=COLOR_BG)
    style.configure("Card.TFrame", background=COLOR_CARD, relief="flat")
    style.configure("Header.TFrame", background=COLOR_HEADER_BG)
    style.configure("Toolbar.TFrame", background="#FFFFFF", relief="flat")

    f_base = (FONT_FAMILY, FONT_SIZE_BASE)
    f_base_bold = (FONT_FAMILY, FONT_SIZE_BASE, "bold")
    f_ui = (FONT_FAMILY, FONT_SIZE_UI)
    f_ui_bold = (FONT_FAMILY, FONT_SIZE_UI, "bold")
    f_small = (FONT_FAMILY, max(7, FONT_SIZE_BASE - 1))
    f_title = (FONT_FAMILY, FONT_SIZE_BASE + 4, "bold")
    f_card_title = (FONT_FAMILY, FONT_SIZE_BASE + 2, "bold")

    # Label Stilleri
    style.configure("TLabel", background=COLOR_BG, foreground=COLOR_TEXT_MAIN, font=f_base)
    style.configure("Card.TLabel", background=COLOR_CARD, foreground=COLOR_TEXT_MAIN, font=f_base)
    style.configure("Muted.TLabel", background=COLOR_BG, foreground=COLOR_TEXT_MUTED, font=f_small)
    style.configure("HeaderTitle.TLabel", background=COLOR_HEADER_BG, foreground=COLOR_HEADER_TEXT, font=f_title)
    style.configure("HeaderSubtitle.TLabel", background=COLOR_HEADER_BG, foreground="#94A3B8", font=f_small)
    style.configure("Title.TLabel", background=COLOR_BG, foreground=COLOR_TEXT_MAIN, font=f_title)
    style.configure("CardTitle.TLabel", background=COLOR_CARD, foreground=COLOR_PRIMARY, font=f_card_title)

    # Buton Stilleri (Modern Compact & Elegant)
    style.configure(
        "TButton",
        background="#FFFFFF",
        foreground=COLOR_TEXT_MAIN,
        font=f_ui_bold,
        borderwidth=1,
        bordercolor=COLOR_BORDER_STRONG,
        darkcolor=COLOR_BORDER_STRONG,
        lightcolor=COLOR_BORDER_STRONG,
        relief="solid",
        focuscolor="none",
        padding=(8, 4)
    )
    style.map(
        "TButton",
        background=[("active", "#F1F5F9"), ("disabled", "#F8FAFC")],
        foreground=[("disabled", "#94A3B8")]
    )

    style.configure(
        "Primary.TButton",
        background=COLOR_PRIMARY,
        foreground="#FFFFFF",
        font=f_ui_bold,
        borderwidth=0,
        focuscolor="none",
        padding=(10, 5)
    )
    style.map(
        "Primary.TButton",
        background=[("active", COLOR_PRIMARY_HOVER), ("disabled", "#CBD5E1")]
    )

    style.configure(
        "Secondary.TButton",
        background="#FFFFFF",
        foreground=COLOR_PRIMARY,
        font=f_ui_bold,
        borderwidth=1,
        bordercolor=COLOR_PRIMARY,
        relief="solid",
        padding=(8, 4)
    )
    style.map(
        "Secondary.TButton",
        background=[("active", "#EFF6FF")]
    )

    style.configure(
        "Success.TButton",
        background=COLOR_SUCCESS,
        foreground="#FFFFFF",
        font=f_ui_bold,
        borderwidth=0,
        padding=(10, 5)
    )
    style.map(
        "Success.TButton",
        background=[("active", COLOR_SUCCESS_HOVER)]
    )

    style.configure(
        "Danger.TButton",
        background=COLOR_DANGER,
        foreground="#FFFFFF",
        font=f_ui_bold,
        borderwidth=0,
        padding=(8, 4)
    )
    style.map(
        "Danger.TButton",
        background=[("active", "#B91C1C")]
    )

    # Menubutton (Açılır Menüler)
    style.configure(
        "TMenubutton",
        background="#FFFFFF",
        foreground=COLOR_TEXT_MAIN,
        font=f_ui_bold,
        borderwidth=1,
        bordercolor=COLOR_BORDER_STRONG,
        relief="solid",
        padding=(8, 4)
    )
    style.map(
        "TMenubutton",
        background=[("active", "#F1F5F9")]
    )

    # Treeview Stilleri (Modern Clean Table View)
    style.configure(
        "Treeview",
        background="#FFFFFF",
        foreground=COLOR_TEXT_MAIN,
        fieldbackground="#FFFFFF",
        rowheight=28,
        font=(FONT_FAMILY, 9),
        borderwidth=0
    )
    style.configure(
        "Treeview.Heading",
        background="#F1F5F9",
        foreground="#0F172A",
        font=(FONT_FAMILY, 9, "bold"),
        relief="flat",
        padding=(5, 5)
    )
    style.map(
        "Treeview",
        background=[("selected", COLOR_PRIMARY)],
        foreground=[("selected", "#FFFFFF")]
    )

    # Notebook Stilleri (Modern Segments)
    style.configure("TNotebook", background=COLOR_BG, borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background="#E2E8F0",
        foreground=COLOR_TEXT_MAIN,
        font=(FONT_FAMILY, 9, "bold"),
        padding=(12, 5),
        borderwidth=0
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", "#FFFFFF"), ("active", "#CBD5E1")],
        foreground=[("selected", COLOR_PRIMARY)]
    )

    # Form Elemanları
    style.configure("TCombobox", padding=3, font=(FONT_FAMILY, 9))
    style.configure("TEntry", padding=3, font=(FONT_FAMILY, 9))
    style.configure("TCheckbutton", background=COLOR_CARD, font=(FONT_FAMILY, 9))
    style.configure("TRadiobutton", background=COLOR_BG, font=(FONT_FAMILY, 9))
