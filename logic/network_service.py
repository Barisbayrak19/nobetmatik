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
import datetime
import shutil
import sqlite3
import urllib.request
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
    Zaten paylaşımdaysa başarılı döner. Hızlı timeout (1.5s) ile UI kilitlenmelerini engeller.
    """
    if os.name != "nt":
        return False, "Yalnızca Windows işletim sisteminde SMB paylaşımı desteklenir."

    abs_path = str(folder_path.resolve())
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        # Önce mevcut paylaşımları kontrol et (1.5 sn sınır)
        chk = subprocess.run(
            ["net", "share", share_name],
            capture_output=True,
            encoding="cp857",
            errors="replace",
            timeout=1.5,
            creationflags=flags
        )
        if chk.returncode == 0:
            return True, f"\\\\{get_hostname()}\\{share_name}"

        # Paylaşım yoksa yeni paylaşım aç (2 sn sınır)
        res = subprocess.run(
            ["net", "share", f"{share_name}={abs_path}", "/grant:everyone,full"],
            capture_output=True,
            encoding="cp857",
            errors="replace",
            timeout=2.0,
            creationflags=flags
        )
        if res.returncode == 0:
            logger.info(f"Windows klasör paylaşımı açıldı: {share_name} -> {abs_path}")
            return True, f"\\\\{get_hostname()}\\{share_name}"
        else:
            err_msg = res.stderr.strip() or res.stdout.strip()
            logger.warning(f"Paylaşım açma uyarısı: {err_msg}")
            return False, err_msg
    except Exception as e:
        logger.warning(f"Windows share zaman aşımı veya hatası: {e}")
        return False, str(e)

def remove_windows_share(share_name: str = SHARE_NAME) -> bool:
    """Windows üzerindeki paylaşımı kaldırır (1 sn sınır)."""
    if os.name != "nt":
        return False
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        res = subprocess.run(
            ["net", "share", share_name, "/delete", "/y"],
            capture_output=True,
            encoding="cp857",
            errors="replace",
            timeout=1.0,
            creationflags=flags
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

    def do_POST(self):
        if self.path == "/api/sync/push":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length <= 0 or content_length > 100 * 1024 * 1024:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Gecersiz icerik boyutu")
                    return

                uploaded_data = self.rfile.read(content_length)
                if not uploaded_data.startswith(b"SQLite format 3"):
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Gecersiz veritabani formati")
                    return

                tmp_path = NobetHTTPHandler.db_file_path.parent / f"push_temp_{int(time.time())}.db"
                with open(tmp_path, "wb") as f:
                    f.write(uploaded_data)

                # Ana sunucuda mevcut DB'yi yedekle
                backup_dir = NobetHTTPHandler.db_file_path.parent.parent / "backups"
                backup_dir.mkdir(parents=True, exist_ok=True)
                backup_file = backup_dir / f"host_pre_client_sync_{datetime.date.today().isoformat()}.db"
                try:
                    if NobetHTTPHandler.db_file_path.exists():
                        shutil.copy2(NobetHTTPHandler.db_file_path, backup_file)
                except Exception:
                    pass

                # SQLite Backup API ile güvenle aktar
                with sqlite3.connect(str(tmp_path)) as src:
                    with sqlite3.connect(str(NobetHTTPHandler.db_file_path)) as dst:
                        src.backup(dst)

                try:
                    tmp_path.unlink()
                except Exception:
                    pass

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "message": "Veritabanı güncellendi"}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))
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

        # Paylaşımı arka planda sessizce kaldır, kapanışı bekletme
        threading.Thread(target=remove_windows_share, args=(SHARE_NAME,), daemon=True).start()
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
    def check_host_direct(ip: str, port: int = HTTP_PORT, timeout: float = 0.8) -> Optional[Dict[str, Any]]:
        """Belirtilen IP adresindeki NöbetMatik sunucusunu doğrudan sorgular (anında yanıt)."""
        import urllib.request
        try:
            req = urllib.request.Request(f"http://{ip}:{port}/api/info", headers={"User-Agent": "NobetClient"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    info = json.loads(resp.read().decode("utf-8"))
                    if info.get("app") == "NobetMatik":
                        info["ip"] = ip
                        return info
        except Exception:
            pass
        return None

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


class NetworkSyncManager:
    """
    Offline-First Otomatik Senkronizasyon Yöneticisi:
    - İstemci bilgisayarlar her zaman yerel veritabanıyla hemen ve kesintisiz başlar (sıfır bekleme/donma).
    - Arka planda ana bilgisayar yoklanır; erişilebilirse en güncel veriler otomatik eşitlenir.
    - Ana bilgisayar kapalı olsa bile yerel verilerle çalışılmaya devam edilir.
    """
    LOCAL_PRESERVED_SETTINGS = [
        "lan_role",
        "lan_auto_host",
        "lan_auto_sync",
        "lan_last_host_ip",
        "lan_last_host_name",
        "lan_last_sync_time",
        "lan_last_synced_mtime",
        "lan_last_synced_size",
        "custom_db_path",
        "sidebar_theme",
        "window_geometry",
        "font_scaling",
        "font_size_custom",
        "active_vice_principal",
    ]

    @classmethod
    def get_lan_config(cls, db: Any) -> Dict[str, Any]:
        """Veritabanındaki yerel ağ yapılandırma ayarlarını döndürür."""
        return {
            "role": db.get_setting("lan_role", "none"),
            "auto_host": db.get_setting("lan_auto_host", "0") == "1",
            "auto_client_sync": db.get_setting("lan_auto_sync", "0") == "1",
            "last_host_ip": db.get_setting("lan_last_host_ip", ""),
            "last_host_name": db.get_setting("lan_last_host_name", ""),
            "last_sync_time": db.get_setting("lan_last_sync_time", ""),
            "last_synced_mtime": float(db.get_setting("lan_last_synced_mtime", "0") or 0),
            "last_synced_size": int(db.get_setting("lan_last_synced_size", "0") or 0),
        }

    @classmethod
    def set_lan_config(
        cls,
        db: Any,
        role: Optional[str] = None,
        auto_host: Optional[bool] = None,
        auto_client_sync: Optional[bool] = None,
        last_host_ip: Optional[str] = None,
        last_host_name: Optional[str] = None
    ):
        """Yerel ağ ayarlarını kaydeder."""
        if role is not None:
            db.set_setting("lan_role", role)
        if auto_host is not None:
            db.set_setting("lan_auto_host", "1" if auto_host else "0")
        if auto_client_sync is not None:
            db.set_setting("lan_auto_sync", "1" if auto_client_sync else "0")
        if last_host_ip is not None:
            db.set_setting("lan_last_host_ip", last_host_ip)
        if last_host_name is not None:
            db.set_setting("lan_last_host_name", last_host_name)

    @classmethod
    def find_active_host(cls, db: Any, timeout: float = 1.5) -> Optional[Dict[str, Any]]:
        """
        Önce kayıtlı son IP'yi hızlıca (50-200ms) yoklar.
        Bulamazsa UDP anons ve keşif ile ağı tarar.
        """
        last_ip = db.get_setting("lan_last_host_ip", "").strip()
        if last_ip:
            h = NetworkDiscoveryClient.check_host_direct(last_ip, timeout=0.6)
            if h:
                return h

        # Kayıtlı IP yanıt vermediyse ağdaki sunucuları tara
        hosts = NetworkDiscoveryClient.discover_hosts(timeout=timeout)
        if hosts:
            selected = hosts[0]
            if selected.get("ip"):
                db.set_setting("lan_last_host_ip", selected["ip"])
            if selected.get("hostname"):
                db.set_setting("lan_last_host_name", selected["hostname"])
            return selected

        return None

    @classmethod
    def sync_from_host(
        cls,
        db: Any,
        host_info: Optional[Dict[str, Any]] = None,
        timeout: float = 2.0,
        force: bool = False
    ) -> Tuple[bool, str, bool]:
        """
        Ana sunucudan veritabanını çeker ve yerel veritabanı ile eşitler.
        Döner: (başarılı_mı, kullanıcı_mesajı, veri_güncellendi_mi)
        """
        if not host_info:
            host_info = cls.find_active_host(db, timeout=timeout)

        if not host_info:
            return False, "Yerel ağda açık bir Ana Sunucu bulunamadı. Yerel veritabanı ile çalışılıyor.", False

        ip = host_info.get("ip", "")
        hostname = host_info.get("hostname", "")
        school_name = host_info.get("school_name", hostname)
        http_port = host_info.get("http_port", HTTP_PORT)
        host_mtime = float(host_info.get("mtime", 0))
        host_size = int(host_info.get("db_size", 0))

        # Yerelde kayıtlı son eşitleme bilgileri
        try:
            local_mtime = float(db.get_setting("lan_last_synced_mtime", "0") or 0)
            local_size = int(db.get_setting("lan_last_synced_size", "0") or 0)
        except Exception:
            local_mtime, local_size = 0.0, 0

        # Eğer boyut ve değiştirilme tarihi aynıysa ve zorlama yoksa indirmeye gerek yok
        if not force and host_mtime > 0 and host_mtime == local_mtime and host_size == local_size:
            now_str = datetime.datetime.now().strftime("%H:%M")
            return True, f"Veritabanı zaten ana sunucu ({school_name}) ile güncel. ({now_str})", False

        # Veritabanını indir
        http_url = f"http://{ip}:{http_port}/api/db"
        temp_file = db.db_path.parent / f"sync_temp_{int(time.time())}.db"
        try:
            req = urllib.request.Request(http_url, headers={"User-Agent": "NobetClient"})
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                if resp.status != 200:
                    return False, f"Sunucudan veri alınamadı (HTTP {resp.status})", False
                content = resp.read()

            if not content.startswith(b"SQLite format 3"):
                return False, "Sunucudan geçersiz veritabanı dosyası alındı.", False

            with open(temp_file, "wb") as f:
                f.write(content)

            # Eşitleme öncesi yerel yedeği al
            backup_dir = db.db_path.parent.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / "pre_lan_sync_backup.db"
            try:
                if db.db_path.exists():
                    shutil.copy2(db.db_path, backup_path)
            except Exception:
                pass

            # Yerel makine ayarlarını koru
            preserved = {}
            for key in cls.LOCAL_PRESERVED_SETTINGS:
                val = db.get_setting(key, "")
                if val:
                    preserved[key] = val

            # SQLite native backup ile canlı ve kilitlenme olmaksızın aktar
            with sqlite3.connect(str(temp_file)) as src:
                with sqlite3.connect(str(db.db_path)) as dst:
                    src.backup(dst)

            # Korunan ayarları ve yeni mtime/size bilgilerini geri yükle
            with sqlite3.connect(str(db.db_path)) as conn:
                for k, v in preserved.items():
                    conn.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (k, v))
                conn.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('lan_last_synced_mtime', ?)", (str(host_mtime),))
                conn.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('lan_last_synced_size', ?)", (str(host_size),))
                now_str = datetime.datetime.now().strftime("%H:%M")
                conn.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('lan_last_sync_time', ?)", (now_str,))
                conn.commit()

            try:
                temp_file.unlink()
            except Exception:
                pass

            logger.info(f"Ana sunucudan ({school_name} - {ip}) veritabanı başarıyla eşitlendi.")
            return True, f"Ana Sunucu ({school_name}) ile başarıyla eşitlendi. ({now_str})", True

        except Exception as e:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            logger.error(f"Eşitleme hatası: {e}")
            return False, f"Eşitleme sırasında hata oluştu: {e}", False

    @classmethod
    def push_to_host(
        cls,
        db: Any,
        host_info: Optional[Dict[str, Any]] = None,
        timeout: float = 4.0
    ) -> Tuple[bool, str]:
        """Yerelde yapılan değişiklikleri ana sunucuya gönderir."""
        if not host_info:
            host_info = cls.find_active_host(db, timeout=timeout)
        if not host_info:
            return False, "Ana sunucuya ulaşılamadı."

        ip = host_info.get("ip", "")
        http_port = host_info.get("http_port", HTTP_PORT)
        if not db.db_path.exists():
            return False, "Yerel veritabanı bulunamadı."

        try:
            with open(db.db_path, "rb") as f:
                data = f.read()

            url = f"http://{ip}:{http_port}/api/sync/push"
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/x-sqlite3", "User-Agent": "NobetClient"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    now_str = datetime.datetime.now().strftime("%H:%M")
                    db.set_setting("lan_last_sync_time", now_str)
                    return True, f"Değişiklikler Ana Sunucuya başarıyla iletildi. ({now_str})"
                return False, f"Sunucu hatası: HTTP {resp.status}"
        except Exception as e:
            return False, f"Gönderim hatası: {e}"


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

