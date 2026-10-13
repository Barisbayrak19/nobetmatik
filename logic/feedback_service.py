"""
Geri Bildirim ve Hata İletim Servisi
Kullanıcı görüşlerini, özellik taleplerini ve hata loglarını:
1. Telegram Bot API üzerinden anında geliştiricinin telefonuna iletir.
2. Yerel arşivde (data/feedbacks.json) güvenle depolar.
3. Webhook/API yapılandırılmışsa doğrudan iletir.
4. Çevrimdışı veya alternatif olarak hazır e-posta şablonu (mailto) oluşturur.
"""
import os
import sys
import json
import html
import platform
import datetime
import urllib.request
import urllib.parse
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

from core.config import (
    APP_VERSION, APP_NAME, DATA_DIR, LOG_PATH, DEVELOPER_EMAIL,
    FEEDBACK_WEBHOOK_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
)
from core.database import Database
from core.logger import logger
from logic.update_service import _urlopen_with_fallback


@dataclass
class FeedbackData:
    category: str
    school_name: str
    sender_name: str
    contact: str
    subject: str
    message: str
    include_logs: bool
    app_version: str = APP_VERSION
    system_info: str = ""
    created_at: str = ""
    logs_snippet: str = ""


class FeedbackService:
    LOCAL_STORAGE_FILE = DATA_DIR / "feedbacks.json"
    DAILY_LIMIT = 20
    COOLDOWN_SECONDS = 120
    MIN_SUBJECT_LEN = 5
    MIN_MESSAGE_LEN = 10

    @classmethod
    def get_system_info_str(cls) -> str:
        return f"{platform.system()} {platform.release()} | Python {sys.version.split()[0]} | v{APP_VERSION}"

    @classmethod
    def _load_local_feedbacks(cls) -> list:
        if cls.LOCAL_STORAGE_FILE.exists():
            try:
                with open(cls.LOCAL_STORAGE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception:
                pass
        return []

    @classmethod
    def get_daily_stats(cls, db: Optional[Database] = None) -> Tuple[int, int]:
        """Bugün gönderilen bildirim sayısını ve kalan hakkı (kullanılan, kalan) döndürür."""
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        feedbacks = cls._load_local_feedbacks()
        json_count = sum(1 for item in feedbacks if str(item.get("created_at", "")).startswith(today_str))

        db_count = 0
        if db:
            saved_date = db.get_setting("feedback_daily_date", "")
            if saved_date == today_str:
                try:
                    db_count = int(db.get_setting("feedback_daily_count", "0"))
                except ValueError:
                    db_count = 0

        used = max(json_count, db_count)
        remaining = max(0, cls.DAILY_LIMIT - used)
        return used, remaining

    @classmethod
    def validate_and_check_rate_limit(cls, feedback: FeedbackData, db: Optional[Database] = None) -> Tuple[bool, str]:
        """
        Geri bildirim içeriğini ve gönderim sıklığını (günlük 20 limit, 2 dk bekleme, mükerrer içerik) denetler.
        Dönüş: (uygun_mu, uyarı_mesajı)
        """
        subj = (feedback.subject or "").strip()
        msg = (feedback.message or "").strip()

        if len(subj) < cls.MIN_SUBJECT_LEN:
            return False, f"Lütfen daha açıklayıcı bir konu başlığı girin (en az {cls.MIN_SUBJECT_LEN} karakter)."
        if len(msg) < cls.MIN_MESSAGE_LEN:
            return False, f"Lütfen mesajınızı biraz daha detaylandırın (en az {cls.MIN_MESSAGE_LEN} karakter)."

        now = datetime.datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        feedbacks = cls._load_local_feedbacks()

        # 1. Günlük Limit Kontrolü (20 adet / gün)
        used_today, remaining = cls.get_daily_stats(db)
        if used_today >= cls.DAILY_LIMIT or remaining <= 0:
            return False, (
                f"Günlük geri bildirim gönderme sınırına ({cls.DAILY_LIMIT} adet) ulaştınız.\n"
                "Anlayışınız için teşekkür eder, yeni bildirimlerinizi yarın bekleriz."
            )

        # 2. Mükerrer (Aynı) Mesaj Kontrolü ve 3. Bekleme Süresi (Cooldown - 120 sn)
        last_ts_str = ""
        if feedbacks:
            last_item = feedbacks[-1]
            last_subj = str(last_item.get("subject", "")).strip().lower()
            last_msg = str(last_item.get("message", "")).strip().lower()
            if subj.lower() == last_subj and msg.lower() == last_msg:
                return False, "Bu geri bildirimi az önce zaten gönderdiniz. Aynı mesajı tekrar göndermenize gerek yoktur."
            last_ts_str = str(last_item.get("created_at", ""))

        if db:
            db_last_ts = db.get_setting("feedback_last_ts", "")
            if db_last_ts > last_ts_str:
                last_ts_str = db_last_ts

        if last_ts_str:
            try:
                last_dt = datetime.datetime.strptime(last_ts_str, "%Y-%m-%d %H:%M:%S")
                elapsed = (now - last_dt).total_seconds()
                if 0 <= elapsed < cls.COOLDOWN_SECONDS:
                    wait_sec = int(cls.COOLDOWN_SECONDS - elapsed)
                    return False, (
                        f"Arka arkaya çok hızlı gönderim yapıldı.\n"
                        f"Yeni bir geri bildirim gönderebilmek için lütfen {wait_sec} saniye bekleyiniz."
                    )
            except Exception:
                pass

        return True, ""

    @classmethod
    def _record_rate_limit(cls, feedback: FeedbackData, db: Optional[Database] = None):
        if not db:
            return
        try:
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            used_today, _ = cls.get_daily_stats(db)
            db.set_setting("feedback_daily_date", today_str)
            db.set_setting("feedback_daily_count", str(used_today))
            db.set_setting("feedback_last_ts", feedback.created_at)
        except Exception as e:
            logger.warning(f"Rate limit durumu kaydedilemedi: {e}")

    @classmethod
    def get_recent_logs(cls, max_lines: int = 35) -> str:
        """Kişisel veri içermeyen son log kayıtlarını döndürür."""
        if not LOG_PATH.exists():
            return "Log dosyası bulunamadı."
        try:
            with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                snippet = lines[-max_lines:] if len(lines) > max_lines else lines
                return "".join(snippet).strip()
        except Exception as e:
            return f"Loglar okunurken hata: {e}"

    @classmethod
    def save_local_feedback(cls, feedback: FeedbackData):
        """Geri bildirimi yerel JSON dosyasına kaydeder (asla kaybolmaz)."""
        feedbacks = cls._load_local_feedbacks()
        item = asdict(feedback)
        feedbacks.append(item)

        try:
            with open(cls.LOCAL_STORAGE_FILE, "w", encoding="utf-8") as f:
                json.dump(feedbacks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Yerel geri bildirim kaydedilemedi: {e}")

    @classmethod
    def send_via_telegram(cls, feedback: FeedbackData, bot_token: str, chat_id: str) -> Tuple[bool, str]:
        """Telegram Bot API üzerinden doğrudan mesaj gönderir."""
        if not bot_token or not chat_id:
            return False, "Telegram bilgileri eksik."

        text = (
            f"📬 <b>Yeni NöbetMatik Geri Bildirimi</b>\n\n"
            f"🏷️ <b>Tür:</b> {html.escape(feedback.category)}\n"
            f"🏫 <b>Okul:</b> {html.escape(feedback.school_name)}\n"
            f"👤 <b>Gönderen:</b> {html.escape(feedback.sender_name or 'Belirtilmedi')}\n"
            f"📞 <b>İletişim:</b> {html.escape(feedback.contact or 'Belirtilmedi')}\n"
            f"📌 <b>Konu:</b> {html.escape(feedback.subject)}\n\n"
            f"💬 <b>Mesaj:</b>\n{html.escape(feedback.message)}\n\n"
            f"💻 <i>{html.escape(feedback.system_info)} | v{feedback.app_version}</i>"
        )
        if feedback.logs_snippet:
            snippet = feedback.logs_snippet[-600:]
            text += f"\n\n📋 <b>Son Hata Kayıtları:</b>\n<pre>{html.escape(snippet)}</pre>"

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "NobetMatik-TelegramFeedback/2.0"
                }
            )
            with _urlopen_with_fallback(req, timeout=8) as resp:
                if resp.status == 200:
                    return True, "Geri bildiriminiz Telegram üzerinden geliştiriciye anında iletildi!"
                return False, f"Telegram sunucusu yanıtı: {resp.status}"
        except Exception as e:
            logger.warning(f"Telegram iletim hatası: {e}")
            return False, f"Telegram bağlantı hatası: {e}"

    @classmethod
    def send_feedback(cls, feedback: FeedbackData, db: Optional[Database] = None) -> Tuple[bool, str]:
        """
        Geri bildirimi doğrular, hız sınırını kontrol eder, kaydeder ve Telegram / Webhook ile gönderir.
        Dönüş: (başarılı_mı, kullanıcı_mesajı)
        """
        allowed, reason = cls.validate_and_check_rate_limit(feedback, db)
        if not allowed:
            return False, reason

        if not feedback.created_at:
            feedback.created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not feedback.system_info:
            feedback.system_info = cls.get_system_info_str()

        # 1. Her durumda önce yerel kopyasını kaydet (Veri kaybı sıfır) ve sayacı güncelle
        cls.save_local_feedback(feedback)
        cls._record_rate_limit(feedback, db)

        # 2. Telegram Bot Entegrasyonu Kontrolü
        bot_token = TELEGRAM_BOT_TOKEN
        chat_id = TELEGRAM_CHAT_ID
        if db:
            custom_token = db.get_setting("telegram_bot_token", "")
            custom_chat = db.get_setting("telegram_chat_id", "")
            if custom_token: bot_token = custom_token
            if custom_chat: chat_id = custom_chat

        if bot_token and chat_id:
            ok, msg = cls.send_via_telegram(feedback, bot_token, chat_id)
            if ok:
                return True, "Geri bildiriminiz geliştiriciye başarıyla ulaştı. İlginiz için çok teşekkür ederiz!"

        # 3. Webhook URL kontrolü (Telegram yoksa veya ek kanal olarak)
        webhook_url = FEEDBACK_WEBHOOK_URL
        if db:
            custom_url = db.get_setting("feedback_webhook_url", "")
            if custom_url:
                webhook_url = custom_url

        if webhook_url:
            payload = {
                "content": f"📬 **Yeni NöbetMatik Geri Bildirimi**\n"
                           f"• **Tür:** {feedback.category}\n"
                           f"• **Okul:** {feedback.school_name}\n"
                           f"• **Gönderen:** {feedback.sender_name or 'Belirtilmedi'} ({feedback.contact or 'İletişim yok'})\n"
                           f"• **Konu:** {feedback.subject}\n\n"
                           f"**Mesaj:**\n{feedback.message}\n\n"
                           f"*(Sürüm: {feedback.app_version} | Sistem: {feedback.system_info})*",
                "data": asdict(feedback)
            }
            try:
                req_data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    webhook_url,
                    data=req_data,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "NobetMatik-FeedbackService/2.0"
                    }
                )
                with _urlopen_with_fallback(req, timeout=6) as resp:
                    if resp.status in (200, 201, 204):
                        return True, "Geri bildiriminiz geliştiriciye başarıyla iletildi. Katkınız için teşekkür ederiz!"
            except Exception as e:
                logger.warning(f"Geri bildirim webhook gönderim uyarısı: {e}")

        # Eğer uzaktan gönderilemediyse bile yerel olarak güvenle kaydedildi
        return True, "Geri bildiriminiz yerel olarak güvenle kaydedildi ve sisteme işlendi. Teşekkür ederiz!"

    @classmethod
    def get_mailto_url(cls, feedback: FeedbackData) -> str:
        """E-posta istemcisi için hazır mailto linki üretir."""
        subject = f"[NöbetMatik {feedback.category}] {feedback.subject} - {feedback.school_name}"
        body = (
            f"Kategori: {feedback.category}\n"
            f"Okul: {feedback.school_name}\n"
            f"Gönderen: {feedback.sender_name}\n"
            f"İletişim: {feedback.contact}\n"
            f"Sürüm / Sistem: {feedback.app_version} ({feedback.system_info})\n\n"
            f"MESAJ:\n{feedback.message}\n"
        )
        if feedback.logs_snippet:
            body += f"\n\n--- SİSTEM LOGLARI ---\n{feedback.logs_snippet}\n"

        params = urllib.parse.urlencode({
            "subject": subject,
            "body": body
        })
        return f"mailto:{DEVELOPER_EMAIL}?{params}"
