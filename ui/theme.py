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

"""
UI Teması ve Stil Tanımları (Apple Human Interface Guidelines & macOS Design System)
macOS Sonoma / Sequoia ve Apple HIG standartlarına göre optimize edilmiş arayüz:
- Apple Canvas Arka Plan (#F5F5F7) ve Saf Beyaz Kartlar (#FFFFFF)
- Apple System Blue (#007AFF), System Green (#34C759), System Orange (#FF9500), System Red (#FF3B30)
- macOS Pro Dark Sidebar (#18181B / #1C1C1E) ve Traffic Lights (#FF5F56, #FFBD2E, #27C93F)
- Apple Tipografisi: Segoe UI Variable / SF Pro uyumlu zengin antrasit (#1D1D1F) ve ikincil (#86868B)
- Ultra ince, pürüzsüz Apple kenarlıkları (#E5E5EA) ve squircle köşe yarıçapları (10-14px)
"""
import tkinter as tk
from tkinter import ttk

# --- APPLE macOS RENK PALETİ (APPLE HUMAN INTERFACE GUIDELINES) ---
COLOR_BG = "#F5F5F7"             # Apple Light Gray Canvas (Ferah, pürüzsüz çalışma alanı)
COLOR_CARD = "#FFFFFF"           # Pure White kart yüzeyleri
COLOR_CARD_HOVER = "#FAFAFC"     # Apple hafif kart hover vurgusu
COLOR_CARD_SECONDARY = "#FBFBFD" # İkincil hafif pastel kart zemini
COLOR_PRIMARY = "#007AFF"        # Apple System Blue: Canlı, güvenilir kurumsal aksiyon mavisi
COLOR_PRIMARY_HOVER = "#0062D2"  # Apple Blue Hover
COLOR_PRIMARY_ACTIVE = "#004CB3" # Apple Blue Active
COLOR_SECONDARY = "#5856D6"      # Apple System Indigo / Purple
COLOR_SUCCESS = "#34C759"        # Apple System Green: Onay / Kayıt yeşili
COLOR_SUCCESS_HOVER = "#28A745"  # Apple Green Hover
COLOR_WARNING = "#FF9500"        # Apple System Orange: Sabit nöbet ve dikkat uyarısı
COLOR_DANGER = "#FF3B30"         # Apple System Red: Eksik nöbet ve silme uyarısı
COLOR_BORDER = "#E5E5EA"         # Apple System Gray 5: İnce, gözü yormayan 1px sınır
COLOR_BORDER_STRONG = "#D1D1D6"  # Apple System Gray 4: İkincil net sınır
COLOR_TEXT_MAIN = "#1D1D1F"      # Apple Primary Label: Zengin antrasit-siyah net tipografi
COLOR_TEXT_MUTED = "#86868B"     # Apple Secondary Label: Zarif, okunaklı ikincil açıklamalar
COLOR_TEXT_TERTIARY = "#A1A1A6"  # Apple Tertiary Label
COLOR_HEADER_BG = "#FFFFFF"      # Apple macOS Window Header (Saf Beyaz Toolbar)
COLOR_HEADER_NAVY = "#1C1C1E"    # Apple Dark Graphite
COLOR_HEADER_DAY_BG = "#F5F5F7"  # Gün sütunu açık gri zemin
COLOR_HEADER_DAY_TXT = "#1D1D1F" # Gün sütunu yazı rengi
COLOR_HEADER_TEXT = "#1D1D1F"

# macOS Pencere Trafik Işıkları (Traffic Lights)
COLOR_TRAFFIC_RED = "#FF5F56"
COLOR_TRAFFIC_YELLOW = "#FFBD2E"
COLOR_TRAFFIC_GREEN = "#27C93F"

# --- DÜĞME TASARIM SİSTEMİ (APPLE HIG BUTTON SYSTEM) ---
BTN_RADIUS = 10                  # macOS Standart düğme köşe yuvarlatma (10 px)
CARD_RADIUS = 12                 # macOS Standart kart köşe yuvarlatma (12-14 px)

# 1. Primary Dark (macOS Koyu Buton: + Nöbet Ekle, Yayınla)
COLOR_BTN_PRIMARY_DARK_BG = "#1D1D1F"
COLOR_BTN_PRIMARY_DARK_HOVER = "#2D2D2F"
COLOR_BTN_PRIMARY_DARK_ACTIVE = "#000000"
COLOR_BTN_PRIMARY_DARK_TEXT = "#FFFFFF"

# 2. Primary Blue (Apple System Blue Aksiyon Butonları)
COLOR_BTN_BLUE_BG = "#007AFF"
COLOR_BTN_BLUE_HOVER = "#0062D2"
COLOR_BTN_BLUE_ACTIVE = "#004CB3"
COLOR_BTN_BLUE_TEXT = "#FFFFFF"

# 3. Secondary / Outline (Apple Beyaz Kart Butonlar)
COLOR_BTN_SECONDARY_BG = "#FFFFFF"
COLOR_BTN_SECONDARY_BORDER = "#D1D1D6"
COLOR_BTN_SECONDARY_HOVER = "#F5F5F7"
COLOR_BTN_SECONDARY_HOVER_BORDER = "#007AFF"
COLOR_BTN_SECONDARY_ACTIVE = "#E5E5EA"
COLOR_BTN_SECONDARY_TEXT = "#1D1D1F"

# 4. Success (Apple Green: ✓ Onayla)
COLOR_BTN_SUCCESS_BG = "#34C759"
COLOR_BTN_SUCCESS_HOVER = "#28A745"
COLOR_BTN_SUCCESS_ACTIVE = "#208637"
COLOR_BTN_SUCCESS_TEXT = "#FFFFFF"

# 5. Danger (Apple Red: ✕ Reddet / Sil)
COLOR_BTN_DANGER_BG = "#FF3B30"
COLOR_BTN_DANGER_HOVER = "#D72C23"
COLOR_BTN_DANGER_ACTIVE = "#B5221B"
COLOR_BTN_DANGER_TEXT = "#FFFFFF"

# 6. Warning / Pending (Apple Orange: ⏱ Beklemede)
COLOR_BTN_WARNING_BG = "#FF9500"
COLOR_BTN_WARNING_HOVER = "#E08300"
COLOR_BTN_WARNING_ACTIVE = "#C27100"
COLOR_BTN_WARNING_TEXT = "#FFFFFF"

# 7. Soft Tinted Pills (Pastel Apple Rozet & Butonlar)
COLOR_BTN_SOFT_BLUE_BG = "#EBF5FF"
COLOR_BTN_SOFT_BLUE_HOVER = "#D0E7FF"
COLOR_BTN_SOFT_BLUE_TEXT = "#007AFF"

COLOR_BTN_SOFT_EMERALD_BG = "#E8F8EE"
COLOR_BTN_SOFT_EMERALD_HOVER = "#D1F2DD"
COLOR_BTN_SOFT_EMERALD_TEXT = "#1E7E34"

# 8. Disabled State (Pasif Butonlar)
COLOR_BTN_DISABLED_BG = "#F5F5F7"
COLOR_BTN_DISABLED_BORDER = "#E5E5EA"
COLOR_BTN_DISABLED_TEXT = "#A1A1A6"

# Hücre Durum Renkleri (macOS Numbers / Calendar Temiz Stil)
COLOR_CELL_BG = "#FFFFFF"            # Normal görev: Saf beyaz squircle kart
COLOR_CELL_EMPTY = "#FBFBFD"         # Boş slot: Ferah açık zemin
COLOR_CELL_EMPTY_BORDER = "#E5E5EA"  # Boş slot: İnce zarif sınır
COLOR_CELL_EMPTY_TXT = "#007AFF"     # Boş slot: Apple Blue davetkar yazı
COLOR_FIXED = "#FFF8ED"              # Sabit nöbet: Apple Soft Amber Pastel
COLOR_FIXED_BORDER = "#FF9500"       # Sabit nöbet: Apple Orange sınır
COLOR_CELL_HOVER = "#F5F5F7"         # Fare üzerine gelince yumuşak hover
COLOR_CELL_DRAG = "#EBF5FF"          # Apple Blue Light Glow
COLOR_CELL_SELECTED = "#EBF5FF"      # Seçili hücre: Hafif mavi zemin
COLOR_CELL_SELECTED_BORDER = "#007AFF" # Seçili hücre: Canlı Apple Blue sınır

# Durum Rozet Renkleri (Apple Pastel Rozetler)
COLOR_BADGE_FREE = "#F5F5F7"         # Nötr gri zemin
COLOR_BADGE_FREE_TXT = "#6E6E73"     # Okunaklı Apple gri metin
COLOR_BADGE_FREE_BORDER = "#E5E5EA"  # İnce sınır
COLOR_BADGE_FIXED = "#FFF8ED"
COLOR_BADGE_FIXED_TXT = "#B45309"
COLOR_BADGE_EMPTY = "#FEECEB"
COLOR_BADGE_EMPTY_TXT = "#FF3B30"

# macOS Pro Dark Sidebar Renkleri
COLOR_SIDEBAR_BG = "#18181B"          # Apple Dark Slate / macOS Sidebar (#18181B)
COLOR_SIDEBAR_HOVER = "#27272A"       # Sidebar hover
COLOR_SIDEBAR_ACTIVE = "#007AFF"      # Sidebar aktif Apple Blue
COLOR_SIDEBAR_TEXT = "#F4F4F5"        # Okunaklı açık metin
COLOR_SIDEBAR_MUTED = "#A1A1AA"       # İkincil soluk gri metin

# Spacing / Boşluk Ölçeği (4, 8, 12, 16, 24 px)
SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 12
SPACING_LG = 16
SPACING_XL = 24

# Tipografi Hiyerarşisi (Apple Optik Boyutlandırma)
FONT_FAMILY = "Segoe UI Variable Text"
FONT_SIZE_PAGE_TITLE = 18        # Sayfa başlığı (18 px bold)
FONT_SIZE_SECTION_TITLE = 15     # Bölüm başlıkları (15 px bold)
FONT_SIZE_TEACHER = 15           # Öğretmen adı (15 px bold net görünüm)
FONT_SIZE_HEADER = 13            # Tablo kat ve gün başlıkları (13 px bold)
FONT_SIZE_BODY = 13              # Genel gövde yazısı (13 px)
FONT_SIZE_SECONDARY = 12         # İkincil / Branş / Açıklama (12 px)
FONT_SIZE_SMALL = 11             # Küçük etiket / Boş ders (11 px)
FONT_SIZE_KPI_VALUE = 22         # KPI büyük rakam (22 px bold)
FONT_SIZE_BASE = 10
FONT_SIZE_UI = 13
FONT_WEIGHT_TEACHER = "bold"     # Öğretmen adı kalınlık ('bold' veya 'normal')
FONT_SCALE_PRESET = "Standart (%100 - Önerilen)"

# Kullanıcı Dostu Hızlı Boyut Önayarları (Presets)
FONT_PRESETS = {
    "Standart (%100 - Önerilen)": {
        "teacher": 15,
        "secondary": 12,
        "header": 13,
        "ui": 13,
        "title": 18,
        "section": 15,
        "kpi": 22,
        "weight": "bold"
    },
    "Büyük (%115 - Rahat Okuma)": {
        "teacher": 16,
        "secondary": 13,
        "header": 14,
        "ui": 14,
        "title": 20,
        "section": 16,
        "kpi": 24,
        "weight": "bold"
    },
    "Çok Büyük (%130 - Geniş Ekran)": {
        "teacher": 18,
        "secondary": 14,
        "header": 15,
        "ui": 15,
        "title": 22,
        "section": 17,
        "kpi": 26,
        "weight": "bold"
    },
    "Kompakt (%90 - Küçük Ekran)": {
        "teacher": 13,
        "secondary": 11,
        "header": 12,
        "ui": 12,
        "title": 16,
        "section": 14,
        "kpi": 20,
        "weight": "bold"
    }
}

# Tablo Ayırıcı Çizgi ve Hücre Ayarları (Grid Borders)
GRID_BORDER_COLOR = "#CBD5E1"    # İnce (1 px) açık gri-mavi çizgi (#CBD5E1)
GRID_BORDER_WIDTH = 1
GRID_RELIEF = "flat"
GRID_CELL_RADIUS = 8             # Yuvarlatılmış köşe yarıçapı (~8 px)
GRID_CELL_GAP = 6                # Hücre arası boşluk (6-8 px)

def load_theme_settings(db=None):
    """Veritabanından tüm sistem yazı tipi, boyut ve tablo çizgisi tercihlerini yükler."""
    global FONT_FAMILY, FONT_SIZE_BASE, FONT_SIZE_UI, FONT_SIZE_TEACHER, FONT_SIZE_SECONDARY
    global FONT_SIZE_HEADER, FONT_SIZE_PAGE_TITLE, FONT_SIZE_SECTION_TITLE, FONT_SIZE_BODY
    global FONT_SIZE_SMALL, FONT_SIZE_KPI_VALUE, FONT_WEIGHT_TEACHER, FONT_SCALE_PRESET
    global GRID_BORDER_COLOR, GRID_BORDER_WIDTH, GRID_RELIEF
    if db:
        try:
            fam = db.get_setting("font_family", "Segoe UI")
            if fam:
                FONT_FAMILY = fam

            FONT_SCALE_PRESET = db.get_setting("font_scale_preset", "Standart (%100 - Önerilen)")

            teacher_sz = db.get_setting("font_size_teacher", "")
            if not teacher_sz:
                old_sz = db.get_setting("font_size", "15")
                teacher_sz = old_sz if (old_sz and old_sz.isdigit() and int(old_sz) >= 14) else "15"
            val_t = int(teacher_sz) if teacher_sz.isdigit() else 15
            if val_t == 12:
                val_t = 15  # Eski 12px varsayılanını otomatik net 15px'e yükselt
            FONT_SIZE_TEACHER = max(12, min(24, val_t))

            sec_sz = db.get_setting("font_size_secondary", "12")
            if sec_sz and sec_sz.isdigit():
                val_s = int(sec_sz)
                if val_s <= 10:
                    val_s = 12
                FONT_SIZE_SECONDARY = max(11, min(18, val_s))

            hdr_sz = db.get_setting("font_size_header", "13")
            if hdr_sz and hdr_sz.isdigit():
                val_h = int(hdr_sz)
                if val_h <= 11:
                    val_h = 13
                FONT_SIZE_HEADER = max(11, min(20, val_h))

            ui_size_str = db.get_setting("ui_font_size", "13")
            if ui_size_str and ui_size_str.isdigit():
                val_u = int(ui_size_str)
                if val_u <= 11:
                    val_u = 13
                FONT_SIZE_UI = max(11, min(18, val_u))

            title_sz = db.get_setting("font_size_page_title", "18")
            if title_sz and title_sz.isdigit():
                FONT_SIZE_PAGE_TITLE = max(14, min(28, int(title_sz)))

            sec_title_sz = db.get_setting("font_size_section_title", "15")
            if sec_title_sz and sec_title_sz.isdigit():
                FONT_SIZE_SECTION_TITLE = max(12, min(24, int(sec_title_sz)))

            kpi_sz = db.get_setting("font_size_kpi_value", "22")
            if kpi_sz and kpi_sz.isdigit():
                FONT_SIZE_KPI_VALUE = max(16, min(36, int(kpi_sz)))

            w_val = db.get_setting("font_weight_teacher", "bold")
            FONT_WEIGHT_TEACHER = "normal" if "normal" in w_val.lower() else "bold"

            FONT_SIZE_BASE = 10
            FONT_SIZE_BODY = FONT_SIZE_UI
            FONT_SIZE_SMALL = max(11, FONT_SIZE_SECONDARY - 1)

            col = db.get_setting("grid_border_color", "#CBD5E1")
            if col:
                if col.upper() == "#94A3B8":
                    col = "#CBD5E1"
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
    try:
        root.configure(bg=COLOR_BG)
    except Exception:
        try:
            root.configure(fg_color=COLOR_BG)
        except Exception:
            pass

    # Tkinter Named Fonts güncelle (Standart Tk/ttk punto bazlıdır: 10pt ≈ 13.3px)
    tk_pt_ui = max(9, min(12, round(FONT_SIZE_UI * 0.75)))
    try:
        import tkinter.font as tkfont
        for name in ["TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont", "TkTooltipFont"]:
            try:
                f = tkfont.nametofont(name)
                f.configure(family=FONT_FAMILY, size=tk_pt_ui)
            except Exception:
                pass
    except Exception:
        pass

    # Frame Stilleri
    style.configure("TFrame", background=COLOR_BG)
    style.configure("Card.TFrame", background=COLOR_CARD, relief="flat")
    style.configure("Header.TFrame", background=COLOR_HEADER_BG)
    style.configure("Toolbar.TFrame", background="#FFFFFF", relief="flat")

    f_base = (FONT_FAMILY, tk_pt_ui)
    f_base_bold = (FONT_FAMILY, tk_pt_ui, "bold")
    f_ui = (FONT_FAMILY, tk_pt_ui)
    f_ui_bold = (FONT_FAMILY, tk_pt_ui, "bold")
    f_small = (FONT_FAMILY, max(9, tk_pt_ui - 1))
    f_title = (FONT_FAMILY, tk_pt_ui + 3, "bold")
    f_card_title = (FONT_FAMILY, tk_pt_ui + 1, "bold")

    # Label & LabelFrame Stilleri (Modern Flat Card Görünümü)
    style.configure("TLabel", background=COLOR_BG, foreground=COLOR_TEXT_MAIN, font=f_base)
    style.configure("Card.TLabel", background=COLOR_CARD, foreground=COLOR_TEXT_MAIN, font=f_base)
    style.configure("Muted.TLabel", background=COLOR_BG, foreground=COLOR_TEXT_MUTED, font=f_small)
    style.configure("HeaderTitle.TLabel", background=COLOR_HEADER_BG, foreground=COLOR_HEADER_TEXT, font=f_title)
    style.configure("HeaderSubtitle.TLabel", background=COLOR_HEADER_BG, foreground="#94A3B8", font=f_small)
    style.configure("Title.TLabel", background=COLOR_BG, foreground=COLOR_TEXT_MAIN, font=f_title)
    style.configure("CardTitle.TLabel", background=COLOR_CARD, foreground=COLOR_PRIMARY, font=f_card_title)
    style.configure("TLabelframe", background=COLOR_CARD, bordercolor="#E2E8F0", relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label", background=COLOR_CARD, foreground="#0F172A", font=f_base_bold)

    # Buton Stilleri (Düğme Tasarım Sistemi Standartları: Solid & Outline)
    style.configure(
        "TButton",
        background="#FFFFFF",
        foreground=COLOR_BTN_SECONDARY_TEXT,
        bordercolor=COLOR_BTN_SECONDARY_BORDER,
        font=f_ui_bold,
        borderwidth=1,
        relief="solid",
        focuscolor="none",
        padding=(14, 6)
    )
    style.map(
        "TButton",
        background=[("active", COLOR_BTN_SECONDARY_HOVER), ("pressed", COLOR_BTN_SECONDARY_ACTIVE), ("disabled", COLOR_BTN_DISABLED_BG)],
        foreground=[("active", "#1D4ED8"), ("disabled", COLOR_BTN_DISABLED_TEXT)],
        bordercolor=[("active", COLOR_BTN_SECONDARY_HOVER_BORDER), ("disabled", COLOR_BTN_DISABLED_BORDER)]
    )

    style.configure(
        "Primary.TButton",
        background=COLOR_BTN_PRIMARY_DARK_BG,
        foreground=COLOR_BTN_PRIMARY_DARK_TEXT,
        font=f_ui_bold,
        borderwidth=0,
        relief="flat",
        focuscolor="none",
        padding=(16, 6)
    )
    style.map(
        "Primary.TButton",
        background=[("active", COLOR_BTN_PRIMARY_DARK_HOVER), ("pressed", COLOR_BTN_PRIMARY_DARK_ACTIVE), ("disabled", COLOR_BTN_DISABLED_BG)],
        foreground=[("disabled", COLOR_BTN_DISABLED_TEXT)]
    )

    style.configure(
        "PrimaryBlue.TButton",
        background=COLOR_BTN_BLUE_BG,
        foreground=COLOR_BTN_BLUE_TEXT,
        font=f_ui_bold,
        borderwidth=0,
        relief="flat",
        focuscolor="none",
        padding=(16, 6)
    )
    style.map(
        "PrimaryBlue.TButton",
        background=[("active", COLOR_BTN_BLUE_HOVER), ("pressed", COLOR_BTN_BLUE_ACTIVE), ("disabled", COLOR_BTN_DISABLED_BG)],
        foreground=[("disabled", COLOR_BTN_DISABLED_TEXT)]
    )

    style.configure(
        "Secondary.TButton",
        background=COLOR_BTN_SECONDARY_BG,
        foreground=COLOR_BTN_SECONDARY_TEXT,
        bordercolor=COLOR_BTN_SECONDARY_BORDER,
        font=f_ui_bold,
        borderwidth=1,
        relief="solid",
        focuscolor="none",
        padding=(14, 6)
    )
    style.map(
        "Secondary.TButton",
        background=[("active", COLOR_BTN_SECONDARY_HOVER), ("pressed", COLOR_BTN_SECONDARY_ACTIVE), ("disabled", COLOR_BTN_DISABLED_BG)],
        foreground=[("active", "#1D4ED8"), ("disabled", COLOR_BTN_DISABLED_TEXT)],
        bordercolor=[("active", COLOR_BTN_SECONDARY_HOVER_BORDER), ("disabled", COLOR_BTN_DISABLED_BORDER)]
    )

    style.configure(
        "Success.TButton",
        background=COLOR_BTN_SUCCESS_BG,
        foreground=COLOR_BTN_SUCCESS_TEXT,
        font=f_ui_bold,
        borderwidth=0,
        relief="flat",
        focuscolor="none",
        padding=(16, 6)
    )
    style.map(
        "Success.TButton",
        background=[("active", COLOR_BTN_SUCCESS_HOVER), ("pressed", COLOR_BTN_SUCCESS_ACTIVE), ("disabled", COLOR_BTN_DISABLED_BG)],
        foreground=[("disabled", COLOR_BTN_DISABLED_TEXT)]
    )

    style.configure(
        "Danger.TButton",
        background=COLOR_BTN_DANGER_BG,
        foreground=COLOR_BTN_DANGER_TEXT,
        font=f_ui_bold,
        borderwidth=0,
        relief="flat",
        focuscolor="none",
        padding=(14, 6)
    )
    style.map(
        "Danger.TButton",
        background=[("active", COLOR_BTN_DANGER_HOVER), ("pressed", COLOR_BTN_DANGER_ACTIVE), ("disabled", COLOR_BTN_DISABLED_BG)],
        foreground=[("disabled", COLOR_BTN_DISABLED_TEXT)]
    )

    # Menubutton (Açılır Menüler)
    style.configure(
        "TMenubutton",
        background="#F1F5F9",
        foreground=COLOR_TEXT_MAIN,
        font=f_ui_bold,
        borderwidth=0,
        relief="flat",
        padding=(12, 5)
    )
    style.map(
        "TMenubutton",
        background=[("active", "#E2E8F0")]
    )

    # Treeview Stilleri (Modern Clean Table View)
    style.configure(
        "Treeview",
        background="#FFFFFF",
        foreground=COLOR_TEXT_MAIN,
        fieldbackground="#FFFFFF",
        rowheight=30,
        font=(FONT_FAMILY, tk_pt_ui),
        borderwidth=0
    )
    style.configure(
        "Treeview.Heading",
        background="#F1F5F9",
        foreground="#0F172A",
        font=(FONT_FAMILY, tk_pt_ui, "bold"),
        relief="flat",
        padding=(6, 6)
    )
    style.map(
        "Treeview",
        background=[("selected", COLOR_PRIMARY)],
        foreground=[("selected", "#FFFFFF")]
    )

    # Notebook Stilleri (Modern Segments)
    style.configure("TNotebook", background=COLOR_BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
    style.configure(
        "TNotebook.Tab",
        background="#E2E8F0",
        foreground="#334155",
        font=(FONT_FAMILY, tk_pt_ui, "bold"),
        padding=(14, 7),
        borderwidth=0
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", "#FFFFFF"), ("active", "#CBD5E1")],
        foreground=[("selected", COLOR_PRIMARY)]
    )

    # Form Elemanları (Modern Flat Görünüm - Win95 Gri Gölgesi Yok)
    style.configure(
        "TCombobox",
        padding=5,
        font=(FONT_FAMILY, tk_pt_ui),
        fieldbackground="#FFFFFF",
        background="#F8FAFC",
        foreground="#0F172A",
        bordercolor="#CBD5E1",
        lightcolor="#FFFFFF",
        darkcolor="#FFFFFF",
        arrowcolor="#334155",
        relief="flat"
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", "#FFFFFF"), ("disabled", "#F1F5F9")],
        selectbackground=[("readonly", "#FFFFFF")],
        selectforeground=[("readonly", "#0F172A")],
        background=[("active", "#E2E8F0"), ("readonly", "#F8FAFC")]
    )
    style.configure(
        "TEntry",
        padding=5,
        font=(FONT_FAMILY, tk_pt_ui),
        fieldbackground="#FFFFFF",
        foreground="#0F172A",
        bordercolor="#CBD5E1",
        lightcolor="#FFFFFF",
        darkcolor="#FFFFFF",
        relief="flat"
    )
    style.configure("TCheckbutton", background=COLOR_CARD, foreground="#0F172A", font=(FONT_FAMILY, tk_pt_ui))
    style.configure("TRadiobutton", background=COLOR_CARD, foreground="#0F172A", font=(FONT_FAMILY, tk_pt_ui))


def create_modern_button(
    parent,
    text: str,
    command=None,
    variant: str = "default",
    width: int = 0,
    height: int = 34,
    corner_radius: int = BTN_RADIUS,
    state: str = "normal",
    font_size: int = None,
    font_weight: str = "bold",
    **extra_kwargs
):
    """
    Design System kılavuzuna tam uyumlu, modern CustomTkinter butonu üretir.
    variant seçenekleri:
      - 'primary' | 'primary_dark': Koyu Kurumsal Lacivert (#0F172A, hover: #1E293B, text: #FFFFFF)
      - 'primary_blue': Canlı Aksiyon Mavisi (#1D4ED8, hover: #2563EB, text: #FFFFFF)
      - 'default' | 'secondary' | 'outline': Beyaz zemin (#FFFFFF), ince sınır (#CBD5E1), koyu metin (#0F172A), açık mavi hover (#EFF6FF)
      - 'success': Zümrüt Yeşili (#059669, hover: #047857, text: #FFFFFF)
      - 'danger': Reddet / Sil Kırmızı (#DC2626, hover: #B91C1C, text: #FFFFFF)
      - 'warning' | 'pending': Beklemede Amber (#D97706, hover: #B45309, text: #FFFFFF)
      - 'warning_outline': Beyaz zemin, turuncu sınır (#F59E0B) ve metin (#D97706)
      - 'soft_blue' | 'pastel_blue': Pastel Mavi (#DBEAFE, hover: #BFDBFE, text: #1D4ED8)
      - 'soft_success' | 'pastel_success': Pastel Yeşil (#D1FAE5, hover: #A7F3D0, text: #047857)
      - 'soft_danger' | 'pastel_danger': Pastel Kırmızı (#FEE2E2, hover: #FECACA, text: #DC2626)
      - 'segmented_active': Koyu Lacivert aktif filtre/sekme (#0F172A, text: #FFFFFF)
      - 'segmented_inactive': Beyaz pasif filtre/sekme (#FFFFFF, border: #CBD5E1, text: #475569)
    """
    import customtkinter as ctk

    border_w = 0
    border_col = None

    v = variant.lower() if variant else "default"

    if v in ("primary", "primary_dark"):
        fg_col = COLOR_BTN_PRIMARY_DARK_BG
        hov_col = COLOR_BTN_PRIMARY_DARK_HOVER
        txt_col = COLOR_BTN_PRIMARY_DARK_TEXT
    elif v == "primary_blue":
        fg_col = COLOR_BTN_BLUE_BG
        hov_col = COLOR_BTN_BLUE_HOVER
        txt_col = COLOR_BTN_BLUE_TEXT
    elif v in ("default", "secondary", "outline"):
        fg_col = COLOR_BTN_SECONDARY_BG
        hov_col = COLOR_BTN_SECONDARY_HOVER
        txt_col = COLOR_BTN_SECONDARY_TEXT
        border_w = 1
        border_col = COLOR_BTN_SECONDARY_BORDER
    elif v == "success":
        fg_col = COLOR_BTN_SUCCESS_BG
        hov_col = COLOR_BTN_SUCCESS_HOVER
        txt_col = COLOR_BTN_SUCCESS_TEXT
    elif v == "danger":
        fg_col = COLOR_BTN_DANGER_BG
        hov_col = COLOR_BTN_DANGER_HOVER
        txt_col = COLOR_BTN_DANGER_TEXT
    elif v in ("warning", "pending"):
        fg_col = COLOR_BTN_WARNING_BG
        hov_col = COLOR_BTN_WARNING_HOVER
        txt_col = COLOR_BTN_WARNING_TEXT
    elif v == "warning_outline":
        fg_col = "#FFFFFF"
        hov_col = "#FFFBEB"
        txt_col = "#D97706"
        border_w = 1
        border_col = "#F59E0B"
    elif v in ("soft_blue", "pastel_blue"):
        fg_col = COLOR_BTN_SOFT_BLUE_BG
        hov_col = COLOR_BTN_SOFT_BLUE_HOVER
        txt_col = COLOR_BTN_SOFT_BLUE_TEXT
    elif v in ("soft_success", "pastel_success"):
        fg_col = COLOR_BTN_SOFT_EMERALD_BG
        hov_col = COLOR_BTN_SOFT_EMERALD_HOVER
        txt_col = COLOR_BTN_SOFT_EMERALD_TEXT
    elif v in ("soft_danger", "pastel_danger"):
        fg_col = "#FEE2E2"
        hov_col = "#FECACA"
        txt_col = "#DC2626"
    elif v == "segmented_active":
        fg_col = COLOR_BTN_PRIMARY_DARK_BG
        hov_col = COLOR_BTN_PRIMARY_DARK_HOVER
        txt_col = COLOR_BTN_PRIMARY_DARK_TEXT
    elif v == "segmented_inactive":
        fg_col = "#FFFFFF"
        hov_col = "#F1F5F9"
        txt_col = "#475569"
        border_w = 1
        border_col = "#CBD5E1"
    else:
        fg_col = COLOR_BTN_SECONDARY_BG
        hov_col = COLOR_BTN_SECONDARY_HOVER
        txt_col = COLOR_BTN_SECONDARY_TEXT
        border_w = 1
        border_col = COLOR_BTN_SECONDARY_BORDER

    f_sz = font_size if font_size is not None else FONT_SIZE_UI
    btn_font = ctk.CTkFont(family=FONT_FAMILY, size=f_sz, weight=font_weight)

    kwargs = {
        "text": text,
        "height": height,
        "corner_radius": corner_radius,
        "fg_color": fg_col,
        "hover_color": hov_col,
        "text_color": txt_col,
        "border_width": border_w,
        "font": btn_font,
        "command": command,
        "state": state,
        "text_color_disabled": COLOR_BTN_DISABLED_TEXT,
    }
    if border_col:
        kwargs["border_color"] = border_col
    if width > 0:
        kwargs["width"] = width

    kwargs.update(extra_kwargs)
    return ctk.CTkButton(parent, **kwargs)

