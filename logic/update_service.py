"""
GitHub Otomatik Güncelleme Servisi (GitHub Releases Update Service)
GitHub Releases API üzerinden en son sürümü denetler, sürüm notlarını çeker,
yeni yükleyiciyi arka planda indirir ve kurulumu başlatır.
"""
import sys
import os
import re
import json
import ssl
import urllib.request
import urllib.error
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from core.config import APP_VERSION, APP_NAME, DEFAULT_GITHUB_REPO
from core.logger import logger

def parse_version(v_str: str) -> tuple:
    """Sürüm metnini ('v2.1.0' -> (2, 1, 0)) sayı demetine dönüştürür."""
    if not v_str:
        return (0, 0, 0)
    cleaned = re.sub(r'^[vV]', '', str(v_str).strip())
    parts = []
    for p in re.split(r'[-._]', cleaned):
        if p.isdigit():
            parts.append(int(p))
        else:
            break
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])

def _make_ssl_context(unverified: bool = False) -> ssl.SSLContext:
    """MEB ağı, kurumsal proxy ve Windows sertifika deposuyla uyumlu SSL context oluşturur."""
    if unverified:
        ctx = ssl._create_unverified_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    try:
        return ssl.create_default_context()
    except Exception:
        return ssl._create_unverified_context()

def _urlopen_with_fallback(req: urllib.request.Request, timeout: int = 10):
    """
    Önce standart doğrulamalı SSL dener;
    MEB/Kurumsal proxy SSL denetimi veya handshake hatasında otomatik esnek SSL fallback yapar.
    """
    try:
        ctx = _make_ssl_context(unverified=False)
        return urllib.request.urlopen(req, timeout=timeout, context=ctx)
    except Exception as e:
        err_str = str(e)
        is_ssl_err = (
            isinstance(getattr(e, "reason", None), ssl.SSLError)
            or isinstance(e, ssl.SSLError)
            or "CERTIFICATE_VERIFY_FAILED" in err_str
            or "Authority Key Identifier" in err_str
            or "_ssl.c" in err_str
            or "SSL" in err_str
        )
        if is_ssl_err:
            logger.info("SSL sertifika uyuşmazlığı tespit edildi (MEB/Kurumsal ağ). Güvenli esnek bağlantı ile deneniyor...")
            ctx_unver = _make_ssl_context(unverified=True)
            return urllib.request.urlopen(req, timeout=timeout, context=ctx_unver)
        raise

class UpdateService:
    def __init__(self, repo: Optional[str] = None):
        target = repo if (repo and repo.strip()) else DEFAULT_GITHUB_REPO
        self.repo = target.strip().strip("/")
        self.api_url = f"https://api.github.com/repos/{self.repo}/releases/latest"

    def check_for_updates(self, timeout: int = 8) -> Dict[str, Any]:
        """
        GitHub Releases API üzerinden en son yayınlanan sürümü sorgular.
        Dönen sözlük has_update, latest_version, body, download_url vb. içerir.
        """
        if not self.repo:
            return {"success": False, "error": "GitHub deposu belirtilmemiş."}

        req = urllib.request.Request(
            self.api_url,
            headers={
                "User-Agent": f"NobetMatik-Updater/{APP_VERSION}",
                "Accept": "application/vnd.github.v3+json"
            }
        )

        try:
            with _urlopen_with_fallback(req, timeout=timeout) as response:
                if response.status != 200:
                    return {
                        "success": False,
                        "error": f"Sunucu yanıt vermedi (HTTP {response.status})"
                    }
                data = json.loads(response.read().decode("utf-8"))

            latest_tag = data.get("tag_name", "").strip()
            if not latest_tag:
                return {"success": False, "error": "Geçerli bir sürüm etiketi bulunamadı."}

            cur_v = parse_version(APP_VERSION)
            lat_v = parse_version(latest_tag)
            has_update = lat_v > cur_v

            # Windows yükleyici (.exe) veya taşınabilir paket (.zip) varlığını araştır
            assets = data.get("assets", [])
            target_asset = None
            # 1. Öncelik: Kurulum/Çalıştırılabilir dosya (.exe)
            for a in assets:
                a_name = a.get("name", "").lower()
                if a_name.endswith(".exe") and not a_name.startswith("unins"):
                    target_asset = a
                    break
            # 2. Öncelik: Taşınabilir ZIP paketi (.zip)
            if not target_asset:
                for a in assets:
                    a_name = a.get("name", "").lower()
                    if a_name.endswith(".zip"):
                        target_asset = a
                        break

            download_url = target_asset.get("browser_download_url") if target_asset else None
            asset_name = target_asset.get("name") if target_asset else None
            asset_size = target_asset.get("size", 0) if target_asset else 0

            return {
                "success": True,
                "has_update": has_update,
                "current_version": APP_VERSION,
                "latest_version": latest_tag,
                "title": data.get("name") or latest_tag,
                "body": data.get("body", "Sürüm notu girilmemiş."),
                "html_url": data.get("html_url", f"https://github.com/{self.repo}/releases"),
                "published_at": data.get("published_at", ""),
                "download_url": download_url,
                "asset_name": asset_name,
                "asset_size": asset_size
            }

        except urllib.error.HTTPError as e:
            if e.code == 404:
                # GitHub üzerinde henüz bir Release yayınlanmamışsa mevcut sürüm günceldir
                logger.info(f"GitHub deposunda ({self.repo}) yeni bir sürüm yayını bulunamadı (HTTP 404). Mevcut sürüm güncel.")
                return {
                    "success": True,
                    "has_update": False,
                    "current_version": APP_VERSION,
                    "latest_version": APP_VERSION,
                    "title": "Sürüm Güncel",
                    "body": "Depoda henüz yayınlanmış yeni bir sürüm bulunamadı.",
                    "html_url": f"https://github.com/{self.repo}",
                    "published_at": "",
                    "download_url": None,
                    "asset_name": None,
                    "asset_size": 0
                }
            elif e.code == 403:
                return {
                    "success": False,
                    "error": "GitHub API istek sınırı aşıldı. Lütfen daha sonra tekrar deneyiniz."
                }
            return {"success": False, "error": f"HTTP Hatası: {e.code} - {e.reason}"}

        except urllib.error.URLError as e:
            logger.warning(f"Güncelleme kontrolü bağlantı hatası: {e}")
            return {
                "success": False,
                "error": "İnternet bağlantısı kurulamadı veya GitHub sunucusuna ulaşılamadı. Lütfen ağ bağlantınızı kontrol ediniz."
            }
        except Exception as e:
            logger.error(f"Güncelleme denetlenirken beklenmeyen hata: {e}", exc_info=True)
            return {"success": False, "error": f"Güncelleme sorgulanamadı: {e}"}

    def download_installer(
        self,
        download_url: str,
        target_path: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> bool:
        """
        Yükleyici dosyasını belirtilen hedefe indirir.
        progress_callback(indirilen_byte, toplam_byte) çağrılır.
        """
        req = urllib.request.Request(
            download_url,
            headers={"User-Agent": f"NobetMatik-Updater/{APP_VERSION}"}
        )

        try:
            with _urlopen_with_fallback(req, timeout=30) as response:
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0
                chunk_size = 64 * 1024  # 64 KB

                target_path.parent.mkdir(parents=True, exist_ok=True)
                with open(target_path, "wb") as f:
                    while True:
                        if cancel_check and cancel_check():
                            logger.info("İndirme kullanıcı tarafından iptal edildi.")
                            return False

                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback:
                            progress_callback(downloaded, total_size)

            logger.info(f"Güncelleme dosyası indirildi: {target_path} ({downloaded} byte)")
            return True

        except Exception as e:
            logger.error(f"Güncelleme indirme hatası: {e}", exc_info=True)
            if target_path.exists():
                try:
                    target_path.unlink()
                except Exception:
                    pass
            raise e

    @staticmethod
    def launch_installer_and_exit(installer_path: Path):
        """İndirilen kurulum dosyasını başlatır veya zip paketini klasörde gösterir."""
        if not installer_path.exists():
            raise FileNotFoundError(f"Kurulum dosyası bulunamadı: {installer_path}")

        logger.info(f"Yeni sürüm dosyası açılıyor: {installer_path}")
        is_zip = str(installer_path).lower().endswith(".zip")
        if is_zip:
            if sys.platform.startswith("win"):
                import subprocess
                subprocess.Popen(f'explorer /select,"{installer_path}"')
            else:
                import subprocess
                subprocess.Popen(["xdg-open", str(installer_path.parent)])
            return

        if sys.platform.startswith("win"):
            os.startfile(str(installer_path))
        else:
            import subprocess
            subprocess.Popen([str(installer_path)])

        # Kurulum programı başlatıldığında mevcut süreci temiz bir şekilde sonlandır
        sys.exit(0)
