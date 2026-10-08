"""
Yedekleme ve Geri Yükleme Servisi
Tarih/saat damgalı SQLite yedekleri oluşturur ve geri yükler.
"""
import shutil
import datetime
from pathlib import Path
from typing import List, Dict, Any
from core.config import BACKUP_DIR, DB_PATH
from core.logger import logger

class BackupService:
    def __init__(self, db_path: Path = DB_PATH, backup_dir: Path = BACKUP_DIR):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self) -> Path:
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"nobet_backup_{now_str}.db"
        dest_path = self.backup_dir / backup_filename

        if self.db_path.exists():
            shutil.copy2(self.db_path, dest_path)
            logger.info(f"Yedek başarıyla oluşturuldu: {dest_path}")
            return dest_path
        else:
            raise FileNotFoundError(f"Veritabanı dosyası bulunamadı: {self.db_path}")

    def list_backups(self) -> List[Dict[str, Any]]:
        backups = []
        for file in self.backup_dir.glob("nobet_backup_*.db"):
            stat = file.stat()
            backups.append({
                "path": file,
                "name": file.name,
                "size_kb": round(stat.st_size / 1024, 1),
                "created_at": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M:%S")
            })
        backups.sort(key=lambda x: x["path"].stat().st_mtime, reverse=True)
        return backups

    def restore_backup(self, backup_path: Path) -> bool:
        if not backup_path.exists():
            raise FileNotFoundError(f"Yedek dosyası bulunamadı: {backup_path}")

        # Mevcut veritabanını güvenlik amacıyla geçici olarak yedekle
        temp_backup = self.backup_dir / "pre_restore_safety.db"
        if self.db_path.exists():
            shutil.copy2(self.db_path, temp_backup)

        try:
            shutil.copy2(backup_path, self.db_path)
            logger.info(f"Yedek geri yüklendi: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Geri yükleme hatası: {e}")
            if temp_backup.exists():
                shutil.copy2(temp_backup, self.db_path)
            raise e
