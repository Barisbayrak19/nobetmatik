import unittest
import tempfile
import os
import json
from pathlib import Path

from core.database import Database
from logic.announcement_service import AnnouncementService, Announcement
from logic.feedback_service import FeedbackService, FeedbackData


class TestAnnouncementAndFeedbackServices(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.db = Database(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_announcement_service_fallback(self):
        """Yerel duyuruların veya önbelleğin başarıyla çekildiğini doğrula."""
        announcements = AnnouncementService.fetch_announcements()
        self.assertIsInstance(announcements, list)
        self.assertGreater(len(announcements), 0, "En az bir duyuru yüklenmeli")

        first = announcements[0]
        self.assertTrue(first.title)
        self.assertTrue(first.content)

    def test_announcement_unread_tracking(self):
        """Okunmamış duyuru sayısının ve okundu işaretlemenin doğrulanması."""
        announcements = [
            Announcement(id="a1", title="D1", date="2026-10-08", badge="YENİ", badge_color="", summary="", content=""),
            Announcement(id="a2", title="D2", date="2026-10-07", badge="İPUCU", badge_color="", summary="", content=""),
        ]

        # Başlangıçta hepsi okunmamış
        unread = AnnouncementService.get_unread_count(self.db, announcements)
        self.assertEqual(unread, 2)

        # a1 okundu olarak işaretlenince kalan unread 0 olur (a1 en güncel duyuru)
        AnnouncementService.mark_as_read(self.db, "a1")
        unread_after = AnnouncementService.get_unread_count(self.db, announcements)
        self.assertEqual(unread_after, 0)

    def test_feedback_service_local_save(self):
        """Geri bildirimin yerel arşive başarıyla kaydedildiğini test et."""
        # Geçici depolama dosyası
        custom_file = Path(self.temp_dir.name) / "test_feedbacks.json"
        FeedbackService.LOCAL_STORAGE_FILE = custom_file

        feedback = FeedbackData(
            category="💡 Yeni Özellik / İyileştirme İsteği",
            school_name="Atatürk Ortaokulu",
            sender_name="Müdür Yardımcısı",
            contact="test@meb.k12.tr",
            subject="Excel Çıktı Tasarımı",
            message="Excel çizelgesinde hücre kenarlıkları biraz daha kalın olabilir mi?",
            include_logs=False
        )

        ok, msg = FeedbackService.send_feedback(feedback, self.db)
        self.assertTrue(ok)
        self.assertTrue(custom_file.exists())

        with open(custom_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["subject"], "Excel Çıktı Tasarımı")
            self.assertEqual(data[0]["school_name"], "Atatürk Ortaokulu")

    def test_feedback_mailto_generation(self):
        """E-posta mailto bağlantısının doğru formatta üretildiğini test et."""
        feedback = FeedbackData(
            category="🐛 Hata / Sorun Bildirimi",
            school_name="Cumhuriyet İlkokulu",
            sender_name="Ali Veli",
            contact="5551234567",
            subject="Nöbet Silme",
            message="Nöbeti silerken uyarı gelmiyor.",
            include_logs=True,
            logs_snippet="[INFO] Test log line"
        )
        url = FeedbackService.get_mailto_url(feedback)
        self.assertTrue(url.startswith("mailto:"))
        self.assertIn("barisbayrak19@gmail.com", url)
        self.assertIn("Cumhuriyet", url)


if __name__ == "__main__":
    unittest.main()
