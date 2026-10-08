"""
Sistem Genel Konfigürasyonu
"""
import sys
import os
from pathlib import Path

APP_NAME = "Nöbet Yönetim Sistemi"
APP_VERSION = "2.0.0"
DEFAULT_GITHUB_REPO = "Barisbayrak19/nobetmatik"

if getattr(sys, 'frozen', False):
    # PyInstaller paketlenmiş çalışma zamanı
    BUNDLE_DIR = Path(getattr(sys, '_MEIPASS', Path(sys.executable).resolve().parent))
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BUNDLE_DIR = Path(__file__).resolve().parent.parent
    BASE_DIR = BUNDLE_DIR

ASSETS_DIR = BUNDLE_DIR / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
ICON_PATH = ASSETS_DIR / "app_icon.ico"
ICON_PNG_PATH = ASSETS_DIR / "app_icon.png"

DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
BACKUP_DIR = BASE_DIR / "backups"
EXPORTS_DIR = BASE_DIR / "exports"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "nobet.db"
LOG_PATH = LOG_DIR / "app.log"

WEEKDAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
