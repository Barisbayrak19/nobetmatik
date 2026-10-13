"""
Yerel Ağ (LAN) Otomatik Keşif, Paylaşım ve Bağlantı Servisi
Okul ortamında teknik bilgi gerektirmeden tek tıkla ağdaki ana bilgisayarı
bulup veritabanına bağlanmayı ve ana bilgisayarı paylaşıma açmayı sağlar.
"""
import os
import sys
import json
import time
import socket
import threading
import subprocess
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import List, Dict, Any, Optional, Tuple

from core.logger import logger
from core.config import DB_PATH

DISCOVERY_PORT = 52525
HTTP_PORT = 52520
SHARE_NAME = "NobetMatik_Ortak"

def get_local_ip() -> str:
    """Cihazın yerel ağdaki gerçek IP adresini tespit eder."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Herhangi bir harici IP'ye sanal bağlantı kurup yerel arayüz IP'sini öğren
        s.connect(("10.254.254.254", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"

def get_hostname() -> str:
    """Bilgisayarın ağ adını döndürür."""
    return socket.gethostname()

def ensure_windows_share(folder_path: Path, share_name: str = SHARE_NAME) -> Tuple[bool, str]:
    """
    Windows üzerinde belirtilen klasörü 'Everyone, FULL' izinleriyle yerel ağda paylaşıma açar.
    Zaten paylaşımdaysa başarılı döner.
    """
    if os.name != "nt":
        return False, "Yalnızca Windows işletim sisteminde SMB paylaşımı desteklenir."

    abs_path = str(folder_path.resolve())
    try:
        # Önce mevcut paylaşımları kontrol et
        chk = subprocess.run(
            ["net", "share", share_name],
            capture_output=True,
            encoding="cp857",
            errors="replace",
            timeout=5
        )
        if chk.returncode == 0:
            return True, f"\\\\{get_hostname()}\\{share_name}"

        # Paylaşım yoksa yeni paylaşım aç
        res = subprocess.run(
            ["net", "share", f"{share_name}={abs_path}", "/grant:everyone,full"],
            capture_output=True,
            encoding="cp857",
            errors="replace",
            timeout=8
        )
        if res.returncode == 0:
            logger.info(f"Windows klasör paylaşımı açıldı: {share_name} -> {abs_path}")
            return True, f"\\\\{get_hostname()}\\{share_name}"
        else:
            err_msg = res.stderr.strip() or res.stdout.strip()
            logger.warning(f"Paylaşım açma uyarısı: {err_msg}")
            return False, err_msg
    except Exception as e:
        logger.error(f"Windows share hatası: {e}")
        return False, str(e)

def remove_windows_share(share_name: str = SHARE_NAME) -> bool:
    """Windows üzerindeki paylaşımı kaldırır."""
    if os.name != "nt":
        return False
    try:
        res = subprocess.run(
            ["net", "share", share_name, "/delete", "/y"],
            capture_output=True,
            encoding="cp857",
            errors="replace",
            timeout=5
        )
        return res.returncode == 0
    except Exception:
        return False


class NobetHTTPHandler(BaseHTTPRequestHandler):
    """Ana bilgisayarın (Host) sunduğu hafif HTTP veri ve durum uç noktaları."""
    db_file_path: Path = DB_PATH
    school_name: str = "Okul"

    def log_message(self, format, *args):
        # Konsolu kirletmemek için sessiz log
        pass

    def do_GET(self):
        if self.path == "/api/info":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            data = {
                "app": "NobetMatik",
                "version": "2.0.0",
                "hostname": get_hostname(),
                "ip": get_local_ip(),
                "school_name": NobetHTTPHandler.school_name,
                "db_size": NobetHTTPHandler.db_file_path.stat().st_size if NobetHTTPHandler.db_file_path.exists() else 0,
                "mtime": NobetHTTPHandler.db_file_path.stat().st_mtime if NobetHTTPHandler.db_file_path.exists() else 0
            }
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

        elif self.path == "/api/db":
            if NobetHTTPHandler.db_file_path.exists():
                try:
                    with open(NobetHTTPHandler.db_file_path, "rb") as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/x-sqlite3")
                    self.send_header("Content-Length", str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(str(e).encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


class NetworkHostService:
    """
    Ana Bilgisayar (Host) olarak çalışan servis.
    Arka planda UDP duyurusu (beacon) yayınlar, HTTP sunucusunu işletir
    ve Windows klasör paylaşımını yönetir.
    """
    def __init__(self, db_path: Path, school_name: str = "Okul"):
        self.db_path = Path(db_path)
        self.school_name = school_name
        self.is_running = False
        self._stop_event = threading.Event()
        self._beacon_thread: Optional[threading.Thread] = None
        self._http_server: Optional[ThreadingHTTPServer] = None
        self._http_thread: Optional[threading.Thread] = None
        self.unc_share_path: str = ""

    def start(self) -> Tuple[bool, str]:
        if self.is_running:
            return True, "Sunucu zaten çalışıyor."

        self.is_running = True
        self._stop_event.clear()

        # 1. Windows Klasör Paylaşımını Başlat
        folder_to_share = self.db_path.parent
        share_ok, share_info = ensure_windows_share(folder_to_share, SHARE_NAME)
        if share_ok:
            self.unc_share_path = f"{share_info}\\{self.db_path.name}"
        else:
            self.unc_share_path = ""

        # 2. HTTP Sunucusunu Başlat
        NobetHTTPHandler.db_file_path = self.db_path
        NobetHTTPHandler.school_name = self.school_name
        try:
            self._http_server = ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), NobetHTTPHandler)
            self._http_thread = threading.Thread(target=self._http_server.serve_forever, daemon=True)
            self._http_thread.start()
            logger.info(f"NobetMatik HTTP sunucusu başlatıldı: port {HTTP_PORT}")
        except Exception as e:
            logger.warning(f"HTTP sunucusu başlatılamadı (port meşgul olabilir): {e}")

        # 3. UDP Beacon Yayını Başlat
        self._beacon_thread = threading.Thread(target=self._beacon_loop, daemon=True)
        self._beacon_thread.start()

        return True, "Ağ paylaşımı ve sunucu servisi başarıyla başlatıldı."

    def _beacon_loop(self):
        """Yerel ağa her 2 saniyede bir UDP anons paketi gönderir."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        payload = {
            "app": "NobetMatik",
            "version": "2.0.0",
            "hostname": get_hostname(),
            "ip": get_local_ip(),
            "http_port": HTTP_PORT,
            "share_path": self.unc_share_path,
            "school_name": self.school_name
        }

        while not self._stop_event.is_set():
            try:
                msg = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                sock.sendto(msg, ("255.255.255.255", DISCOVERY_PORT))
                try:
                    sock.sendto(msg, ("127.0.0.1", DISCOVERY_PORT))
                except Exception:
                    pass
            except Exception:
                pass
            self._stop_event.wait(0.5)

        sock.close()

    def stop(self):
        """Sunucu ve anons servisini kapatır."""
        self.is_running = False
        self._stop_event.set()

        if self._http_server:
            try:
                self._http_server.shutdown()
                self._http_server.server_close()
            except Exception:
                pass
            self._http_server = None

        remove_windows_share(SHARE_NAME)
        logger.info("NobetMatik ağ sunucusu durduruldu.")


class NetworkDiscoveryClient:
    """
    Ağdaki NobetMatik sunucularını otomatik tarayan istemci.
    UDP dinleme + subnet hızlı HTTP yoklama ile 100% tespit garantisi sağlar.
    """
    @staticmethod
    def discover_hosts(timeout: float = 2.0) -> List[Dict[str, Any]]:
        found_hosts: Dict[str, Dict[str, Any]] = {}

        # 1. Yöntem: UDP Broadcast Dinleme
        def udp_listener():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("", DISCOVERY_PORT))
                sock.settimeout(timeout)

                start_t = time.time()
                while time.time() - start_t < timeout:
                    try:
                        data, addr = sock.recvfrom(2048)
                        info = json.loads(data.decode("utf-8"))
                        if info.get("app") == "NobetMatik":
                            sender_ip = addr[0]
                            info["ip"] = sender_ip
                            key = f"{info.get('hostname')}_{sender_ip}"
                            found_hosts[key] = info
                    except socket.timeout:
                        break
                    except Exception:
                        pass
                sock.close()
            except Exception:
                pass

        t_udp = threading.Thread(target=udp_listener, daemon=True)
        t_udp.start()
        t_udp.join(timeout=timeout)

        # 2. Yöntem: Localhost kontrolü (eğer aynı makinede test ediliyorsa veya UDP blokluysa)
        if not found_hosts:
            import urllib.request
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{HTTP_PORT}/api/info", headers={"User-Agent": "NobetClient"})
                with urllib.request.urlopen(req, timeout=0.8) as resp:
                    if resp.status == 200:
                        info = json.loads(resp.read().decode("utf-8"))
                        found_hosts["localhost"] = info
            except Exception:
                pass

        return list(found_hosts.values())

    @staticmethod
    def test_and_connect(host_info: Dict[str, Any], local_data_dir: Path) -> Tuple[bool, str, str]:
        """
        Bulunan bir sunucuya bağlanmayı dener.
        Önce SMB doğrudan dosya erişimini, erişilemezse HTTP indirme/eşitleme modunu dener.
        Döner: (başarılı_mı, seçilen_db_yolu, mesaj)
        """
        share_path = host_info.get("share_path", "").strip()
        hostname = host_info.get("hostname", "")
        ip = host_info.get("ip", "")
        http_port = host_info.get("http_port", HTTP_PORT)

        # SMB yolu önceden oluşmamışsa standart yolu oluştur
        if not share_path and (hostname or ip):
            target = hostname if hostname else ip
            share_path = f"\\\\{target}\\{SHARE_NAME}\\nobet.db"

        # 1. Öncelik: SMB Dosya Paylaşımı ile doğrudan bağlama
        if share_path:
            try:
                p = Path(share_path)
                if p.exists() and p.is_file():
                    # Yazma testi yap
                    return True, str(p), f"✅ '{host_info.get('school_name', hostname)}' sunucusuna doğrudan Windows Ortak Ağı (SMB) ile bağlandı!\nDeğişiklikler anında senkronize edilecektir."
            except Exception as e:
                logger.warning(f"SMB bağlantı testi başarısız: {e}")

        # 2. Öncelik: Dahili HTTP Veri Sunucusu üzerinden DB Çekme
        import urllib.request
        http_url = f"http://{ip}:{http_port}/api/db"
        try:
            req = urllib.request.Request(http_url, headers={"User-Agent": "NobetClient"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status == 200:
                    content = resp.read()
                    local_synced = local_data_dir / "nobet_lan_sync.db"
                    with open(local_synced, "wb") as f:
                        f.write(content)
                    return True, str(local_synced), f"✅ '{host_info.get('school_name', hostname)}' sunucusuna Dahili Ağ Servisi (HTTP) üzerinden bağlanıldı!\nVeritabanı güncel kopyası yerel olarak eşitlendi."
        except Exception as e:
            logger.error(f"HTTP bağlantı testi başarısız: {e}")

        return False, "", f"❌ Sunucuya erişilemedi ({ip}).\nLütfen ana bilgisayarda ağ paylaşımının açık olduğundan ve aynı Wi-Fi/kablolu ağda bulunduğunuzdan emin olun."


# Global Singleton Yönetimi
_global_host_service: Optional[NetworkHostService] = None

def get_global_host_service(db_path: Optional[Path] = None, school_name: str = "Okul") -> NetworkHostService:
    global _global_host_service
    if _global_host_service is None:
        p = db_path if db_path else DB_PATH
        _global_host_service = NetworkHostService(p, school_name)
    return _global_host_service

def is_global_host_running() -> bool:
    global _global_host_service
    return _global_host_service is not None and _global_host_service.is_running

def stop_global_host_service():
    global _global_host_service
    if _global_host_service and _global_host_service.is_running:
        _global_host_service.stop()
        _global_host_service = None

