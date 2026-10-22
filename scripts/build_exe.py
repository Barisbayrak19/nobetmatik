"""
NöbetMatik - Otomatik Derleme ve Paketleme Betiği
PyInstaller kullanarak bağımsız çalıştırılabilir Windows uygulamasını derler ve taşınabilir ZIP paketi üretir.
"""
import sys
import subprocess
import shutil
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.config import APP_VERSION

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

    src_ann = root_dir / "data" / "announcements.json"
    if src_ann.exists():
        shutil.copy2(src_ann, target_data_dir / "announcements.json")
        print(f"[OK] Varsayilan duyurular kopyalandi: {target_data_dir / 'announcements.json'}")

    src_docs = root_dir / "docs"
    target_docs_dir = app_dist_dir / "docs"
    if src_docs.exists():
        if target_docs_dir.exists():
            shutil.rmtree(target_docs_dir)
        shutil.copytree(src_docs, target_docs_dir)
        print(f"[OK] Kullanim kilavuzu ve gorselleri kopyalandi: {target_docs_dir}")

    src_guide_md = root_dir / "KULLANIM_KILAVUZU.md"
    if src_guide_md.exists():
        shutil.copy2(src_guide_md, app_dist_dir / "KULLANIM_KILAVUZU.md")

    # 3. Taşınabilir (Portable) ZIP arşivi oluştur
    print("[*] 3. Tasinabilir (Portable) ZIP paketi olusturuluyor...")
    portable_zip = dist_dir / f"NobetMatik_v{APP_VERSION}_Tasinabilir.zip"
    with zipfile.ZipFile(portable_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in app_dist_dir.rglob("*"):
            arcname = file_path.relative_to(dist_dir)
            zipf.write(file_path, arcname)

    zip_size_mb = portable_zip.stat().st_size / (1024 * 1024)
    print(f"[BASARILI] Tasinabilir paket olusturuldu: {portable_zip} ({zip_size_mb:.2f} MB)")

    # Masaüstüne de kopyala
    desktop_dir = Path.home() / "Desktop"
    if desktop_dir.exists():
        desktop_zip = desktop_dir / f"NobetMatik_v{APP_VERSION}_Tasinabilir.zip"
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
