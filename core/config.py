"""
Sistem Genel Konfigürasyonu
"""
import sys
import os
from pathlib import Path

APP_NAME = "Nöbet Yönetim Sistemi"
APP_VERSION = "2.1.1"
DEFAULT_GITHUB_REPO = "Barisbayrak19/nobetmatik"

if getattr(sys, 'frozen', False):
    # PyInstaller paketlenmiş çalışma zamanı
    BUNDLE_DIR = Path(getattr(sys, '_MEIPASS', Path(sys.executable).resolve().parent))
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BUNDLE_DIR = Path(__file__).resolve().parent.parent
    BASE_DIR = BUNDLE_DIR

ASSETS_DIR = BUNDLE_DIR / "assets"
try:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
ICON_PATH = ASSETS_DIR / "app_icon.ico"
ICON_PNG_PATH = ASSETS_DIR / "app_icon.png"

def _is_dir_writable(path: Path) -> bool:
    """Belirtilen klasöre yazma izni olup olmadığını test eder."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / f".write_test_{os.getpid()}"
        test_file.touch()
        test_file.unlink()
        return True
    except Exception:
        return False

# Program Files gibi salt-okunur sistem dizinlerine kurulmuşsa verileri %APPDATA%/NobetMatik altına taşı.
# Taşınabilir (Portable) veya geliştirme modunda yazılabilirse doğrudan BASE_DIR kullan.
if getattr(sys, 'frozen', False) and not _is_dir_writable(BASE_DIR / "logs"):
    appdata_env = os.environ.get("APPDATA")
    appdata_root = Path(appdata_env) if appdata_env else (Path.home() / "AppData" / "Roaming")
    USER_DATA_ROOT = appdata_root / "NobetMatik"
else:
    USER_DATA_ROOT = BASE_DIR

DATA_DIR = USER_DATA_ROOT / "data"
LOG_DIR = USER_DATA_ROOT / "logs"
BACKUP_DIR = USER_DATA_ROOT / "backups"
EXPORTS_DIR = USER_DATA_ROOT / "exports"

for d in (DATA_DIR, LOG_DIR, BACKUP_DIR, EXPORTS_DIR):
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

DB_PATH = DATA_DIR / "nobet.db"
LOG_PATH = LOG_DIR / "app.log"

# Şablon veritabanı ve duyuru dosyasını ilk açılışta USER_DATA_ROOT'a aktar
if USER_DATA_ROOT != BASE_DIR:
    try:
        src_db = BASE_DIR / "data" / "nobet.db"
        if src_db.exists() and not DB_PATH.exists():
            import shutil
            shutil.copy2(src_db, DB_PATH)
        src_ann = BASE_DIR / "data" / "announcements.json"
        dest_ann = DATA_DIR / "announcements.json"
        if src_ann.exists() and not dest_ann.exists():
            import shutil
            shutil.copy2(src_ann, dest_ann)
    except Exception:
        pass

WEEKDAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]

DEVELOPER_EMAIL = "barisbayrak19@gmail.com"
ANNOUNCEMENTS_URL = f"https://raw.githubusercontent.com/{DEFAULT_GITHUB_REPO}/main/data/announcements.json"
FEEDBACK_WEBHOOK_URL = ""  # Özel webhook URL (İsteğe bağlı)

# Telegram Geri Bildirim Botu Entegrasyonu
TELEGRAM_BOT_TOKEN = "8673798021:AAFzfXm1a_zTTx94Eb469cVqz8WgfQ8aXSI"  # @BotFather'dan alınan Bot Token
TELEGRAM_CHAT_ID = "852517487"    # Mesajın geleceği Telegram ID'niz
