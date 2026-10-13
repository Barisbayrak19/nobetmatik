"""
Dinamik Geliştirici Mesajları ve Duyurular Servisi
Uzak GitHub / API kaynağından veya yerel önbellekten duyuruları çeker,
okunmamış duyuru sayısını yönetir ve güvenli önbellekleme sağlar.
"""
import os
import json
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.config import ANNOUNCEMENTS_URL, DATA_DIR
from core.database import Database
from core.logger import logger
from logic.update_service import _urlopen_with_fallback


@dataclass
class Announcement:
    id: str
    title: str
    date: str
    badge: str
    badge_color: str
    summary: str
    content: str
    important: bool = False
    link_text: str = ""
    link_url: str = ""


class AnnouncementService:
    CACHE_FILE = DATA_DIR / "announcements_cache.json"
    LOCAL_FALLBACK_FILE = DATA_DIR / "announcements.json"
    CACHE_TTL_SECONDS = 3600  # 1 saat

    @classmethod
    def fetch_announcements(cls, force_refresh: bool = False) -> List[Announcement]:
        """
        Duyuruları getirir:
        1. Önbellek geçerliyse önbellekten döner.
        2. Uzak kaynaktan (GitHub raw JSON) çekmeyi dener.
        3. Başarısız olursa yerel data/announcements.json yedeğini kullanır.
        """
        # 1. Önbellek kontrolü
        if not force_refresh and cls.CACHE_FILE.exists():
            try:
                mtime = os.path.getmtime(cls.CACHE_FILE)
                if (time.time() - mtime) < cls.CACHE_TTL_SECONDS:
                    with open(cls.CACHE_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return cls._parse_announcements(data)
            except Exception as e:
                logger.debug(f"Duyuru önbelleği okunurken uyarı: {e}")

        # 2. Uzak kaynaktan çek
        remote_data = cls._fetch_remote()
        if remote_data and "announcements" in remote_data:
            try:
                with open(cls.CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(remote_data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            return cls._parse_announcements(remote_data)

        # 3. Yerel dosya yedeği
        if cls.LOCAL_FALLBACK_FILE.exists():
            try:
                with open(cls.LOCAL_FALLBACK_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return cls._parse_announcements(data)
            except Exception as e:
                logger.debug(f"Yerel duyuru dosyası okunurken uyarı: {e}")

        return []

    @classmethod
    def _fetch_remote(cls) -> Optional[Dict[str, Any]]:
        if not ANNOUNCEMENTS_URL:
            return None
        try:
            req = urllib.request.Request(
                ANNOUNCEMENTS_URL,
                headers={"User-Agent": "NobetMatik-AnnouncementService/2.0"}
            )
            with _urlopen_with_fallback(req, timeout=4) as resp:
                if resp.status == 200:
                    raw = resp.read().decode("utf-8")
                    return json.loads(raw)
        except Exception as e:
            logger.debug(f"Uzak duyuru çekilemedi (çevrimdışı/engelli): {e}")
            return None

    @classmethod
    def _parse_announcements(cls, data: Dict[str, Any]) -> List[Announcement]:
        items = []
        raw_list = data.get("announcements", [])
        for r in raw_list:
            if isinstance(r, dict) and r.get("id"):
                items.append(Announcement(
                    id=str(r.get("id")),
                    title=str(r.get("title", "Duyuru")),
                    date=str(r.get("date", "")),
                    badge=str(r.get("badge", "Duyuru")),
                    badge_color=str(r.get("badge_color", "#2563EB")),
                    summary=str(r.get("summary", "")),
                    content=str(r.get("content", "")),
                    important=bool(r.get("important", False)),
                    link_text=str(r.get("link_text", "")),
                    link_url=str(r.get("link_url", ""))
                ))
        return items

    @classmethod
    def get_unread_announcements(cls, db: Database, announcements: Optional[List[Announcement]] = None) -> List[Announcement]:
        if announcements is None:
            announcements = cls.fetch_announcements()
        last_read_id = db.get_setting("last_read_announcement_id", "")
        if not last_read_id:
            return announcements

        unread = []
        found_last_read = False
        for a in announcements:
            if a.id == last_read_id:
                found_last_read = True
                break
            unread.append(a)

        return unread if found_last_read else announcements

    @classmethod
    def get_unread_count(cls, db: Database, announcements: Optional[List[Announcement]] = None) -> int:
        return len(cls.get_unread_announcements(db, announcements))

    @classmethod
    def mark_all_as_read(cls, db: Database, announcements: Optional[List[Announcement]] = None):
        if announcements is None:
            announcements = cls.fetch_announcements()
        if announcements:
            latest_id = announcements[0].id
            db.set_setting("last_read_announcement_id", latest_id)

    @classmethod
    def mark_as_read(cls, db: Database, announcement_id: str):
        db.set_setting("last_read_announcement_id", announcement_id)
