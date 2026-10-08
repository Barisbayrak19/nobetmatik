"""
Güncelleme Servisi Birim Testleri (Unit Tests for UpdateService)
"""
import unittest
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path

from logic.update_service import parse_version, UpdateService

class TestUpdateService(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(parse_version("2.0.0"), (2, 0, 0))
        self.assertEqual(parse_version("v2.1.0"), (2, 1, 0))
        self.assertEqual(parse_version("V3.0"), (3, 0, 0))
        self.assertEqual(parse_version("v1.5.2-beta"), (1, 5, 2))
        self.assertEqual(parse_version(""), (0, 0, 0))
        self.assertTrue(parse_version("v2.1.0") > parse_version("2.0.0"))
        self.assertTrue(parse_version("v2.0.1") > parse_version("2.0.0"))
        self.assertFalse(parse_version("v1.9.9") > parse_version("2.0.0"))
        self.assertFalse(parse_version("v2.0.0") > parse_version("2.0.0"))

    @patch("urllib.request.urlopen")
    def test_check_for_updates_available(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'''{
            "tag_name": "v2.5.0",
            "name": "NobetMatik v2.5.0 Yenilikler",
            "body": "Yeni ozellikler eklendi.",
            "html_url": "https://github.com/test/repo/releases/tag/v2.5.0",
            "published_at": "2026-10-10T12:00:00Z",
            "assets": [
                {
                    "name": "NobetMatik_Kurulum_v2.5.0.exe",
                    "browser_download_url": "https://github.com/test/repo/releases/download/v2.5.0/NobetMatik_Kurulum_v2.5.0.exe",
                    "size": 15000000
                }
            ]
        }'''
        mock_urlopen.return_value.__enter__.return_value = mock_response

        svc = UpdateService("test/repo")
        result = svc.check_for_updates()

        self.assertTrue(result["success"])
        self.assertTrue(result["has_update"])
        self.assertEqual(result["latest_version"], "v2.5.0")
        self.assertEqual(result["asset_name"], "NobetMatik_Kurulum_v2.5.0.exe")
        self.assertTrue(result["download_url"].endswith(".exe"))

    @patch("urllib.request.urlopen")
    def test_check_for_updates_up_to_date(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'''{
            "tag_name": "v1.0.0",
            "name": "Eski Surum",
            "body": "Notlar",
            "assets": []
        }'''
        mock_urlopen.return_value.__enter__.return_value = mock_response

        svc = UpdateService("test/repo")
        result = svc.check_for_updates()

        self.assertTrue(result["success"])
        self.assertFalse(result["has_update"])

    @patch("urllib.request.urlopen")
    def test_download_installer(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.headers.get.return_value = "100"
        mock_response.read.side_effect = [b"chunk1", b"chunk2", b""]
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "test_installer.exe"
            svc = UpdateService("test/repo")
            progress_calls = []

            def progress(d, t):
                progress_calls.append((d, t))

            success = svc.download_installer("http://dummy/test.exe", target, progress_callback=progress)
            self.assertTrue(success)
            self.assertTrue(target.exists())
            self.assertEqual(target.read_bytes(), b"chunk1chunk2")
            self.assertTrue(len(progress_calls) >= 2)

    @patch("urllib.request.urlopen")
    def test_check_for_updates_404_handled_gracefully(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://dummy", code=404, msg="Not Found", hdrs=None, fp=None
        )
        svc = UpdateService("test/repo")
        result = svc.check_for_updates()

        self.assertTrue(result["success"])
        self.assertFalse(result["has_update"])
        self.assertEqual(result["title"], "Sürüm Güncel")

if __name__ == "__main__":
    unittest.main()
