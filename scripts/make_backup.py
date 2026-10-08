import os
import sys
import shutil
import zipfile
import datetime
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.database import Database
from logic.backup_service import BackupService

def create_full_backup():
    base_dir = Path(__file__).resolve().parent.parent
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Veritabanı Yedeği
    db_path = base_dir / "data" / "nobet.db"
    if db_path.exists():
        bs = BackupService(db_path, base_dir / "backups")
        db_backup_path = bs.create_backup()
        print(f"[OK] Veritabani yedegi alindi: {db_backup_path.name}")
    
    # 2. Tam Proje Kaynak Kod & Veri Zip Yedeği
    zip_name = f"nobet_tam_surum_yedek_{now_str}.zip"
    backups_dir = base_dir / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    zip_path = backups_dir / zip_name
    
    desktop_dir = Path.home() / "Desktop"
    desktop_zip = desktop_dir / zip_name

    ignore_dirs = {
        "__pycache__", ".git", ".gemini", "tmp", "venv", ".venv",
        ".env", ".pytest_cache", ".idea", ".vscode", "backups", "scratch"
    }
    ignore_extensions = {".pyc", ".pyo", ".tmp", ".log"}

    total_files = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
            for f in files:
                ext = Path(f).suffix.lower()
                if ext in ignore_extensions or f == zip_name:
                    continue
                fp = Path(root) / f
                arcname = fp.relative_to(base_dir)
                zf.write(fp, arcname)
                total_files += 1

    # Masaüstüne de bir kopyasını bırak
    try:
        shutil.copy2(zip_path, desktop_zip)
        print(f"[OK] Masaustu yedegi olusturuldu: {desktop_zip}")
    except Exception as e:
        print(f"Masaustune kopyalama atlandi: {e}")

    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"\n[BASARILI] TAM PROJE YEDEGI TAMAMLANDI!")
    print(f"Arsiv Adi: {zip_name}")
    print(f"Dosya Sayisi: {total_files}")
    print(f"Boyut: {zip_size_mb:.2f} MB")
    print(f"Proje Ici Konum: {zip_path}")
    print(f"Masaustu Konum: {desktop_zip}")
    return zip_path, desktop_zip

if __name__ == "__main__":
    create_full_backup()
