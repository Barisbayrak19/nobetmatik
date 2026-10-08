"""
NöbetMatik - Otomatik Derleme ve Paketleme Betiği
PyInstaller kullanarak bağımsız çalıştırılabilir Windows uygulamasını derler ve taşınabilir ZIP paketi üretir.
"""
import sys
import subprocess
import shutil
import zipfile
from pathlib import Path

def build():
    root_dir = Path(__file__).resolve().parent.parent
    dist_dir = root_dir / "dist"
    app_dist_dir = dist_dir / "NobetMatik"
    spec_file = root_dir / "NobetMatik.spec"

    print("[*] 1. PyInstaller ile derleme baslatiliyor...")
    cmd = [sys.executable, "-m", "PyInstaller", str(spec_file), "--clean", "-y"]
    result = subprocess.run(cmd, cwd=root_dir)
    if result.returncode != 0:
        print("[HATA] PyInstaller derleme sirasinda hata olustu.")
        sys.exit(result.returncode)

    print("[OK] Derleme basariyla tamamlandi.")

    # 2. dist/NobetMatik içine başlangıç veri klasörlerini ve varsayılan db kopyala
    print("[*] 2. Veri klasorleri ve veritabani yapisi hazirlaniyor...")
    target_data_dir = app_dist_dir / "data"
    target_data_dir.mkdir(parents=True, exist_ok=True)
    target_logs_dir = app_dist_dir / "logs"
    target_logs_dir.mkdir(parents=True, exist_ok=True)
    target_backups_dir = app_dist_dir / "backups"
    target_backups_dir.mkdir(parents=True, exist_ok=True)
    target_exports_dir = app_dist_dir / "exports"
    target_exports_dir.mkdir(parents=True, exist_ok=True)

    src_db = root_dir / "data" / "nobet.db"
    if src_db.exists():
        shutil.copy2(src_db, target_data_dir / "nobet.db")
        print(f"[OK] Varsayilan veritabani kopyalandi: {target_data_dir / 'nobet.db'}")

    # 3. Taşınabilir (Portable) ZIP arşivi oluştur
    print("[*] 3. Tasinabilir (Portable) ZIP paketi olusturuluyor...")
    portable_zip = dist_dir / "NobetMatik_v2.0.0_Tasinabilir.zip"
    with zipfile.ZipFile(portable_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in app_dist_dir.rglob("*"):
            arcname = file_path.relative_to(dist_dir)
            zipf.write(file_path, arcname)

    zip_size_mb = portable_zip.stat().st_size / (1024 * 1024)
    print(f"[BASARILI] Tasinabilir paket olusturuldu: {portable_zip} ({zip_size_mb:.2f} MB)")

    # Masaüstüne de kopyala
    desktop_dir = Path.home() / "Desktop"
    if desktop_dir.exists():
        desktop_zip = desktop_dir / "NobetMatik_v2.0.0_Tasinabilir.zip"
        shutil.copy2(portable_zip, desktop_zip)
        print(f"[BASARILI] Masaustune kopyalandi: {desktop_zip}")

    print("\n==========================================")
    print("DERLEME ISLEMI TAMAMLANDI!")
    print(f"Uygulama Dizini: {app_dist_dir}")
    print(f"Calistirilabilir Dosya: {app_dist_dir / 'NobetMatik.exe'}")
    print(f"Tasinabilir Zip: {portable_zip}")
    print("==========================================\n")

if __name__ == "__main__":
    build()
