import unittest
import tempfile
from pathlib import Path

from core.models import SchoolInfo, Teacher, Location
from core.database import Database

class TestSchoolAndSecurity(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "test.db"
        self.db = Database(self.db_path)

    def test_school_level_and_education_type(self):
        info = self.db.get_school_info()
        # Varsayılan değerler
        self.assertEqual(info.school_level, "Ortaokul")
        self.assertEqual(info.education_type, "Normal (Tekli)")
        self.assertEqual(info.daily_periods, 7)

        # Güncelleme
        info.school_level = "İlkokul"
        info.education_type = "İkili Eğitim (Sabahçı - Öğlenci)"
        info.daily_periods = 6
        self.db.save_school_info(info)

        loaded = self.db.get_school_info()
        self.assertEqual(loaded.school_level, "İlkokul")
        self.assertEqual(loaded.education_type, "İkili Eğitim (Sabahçı - Öğlenci)")
        self.assertEqual(loaded.daily_periods, 6)

    def test_teacher_phone_and_shift(self):
        t = Teacher(name="Ayşe Kaya", branch="Matematik", phone="05551234567", shift_group="Sabahçı")
        self.db.save_teacher(t)

        loaded = self.db.get_teacher_by_id(t.id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.phone, "05551234567")
        self.assertEqual(loaded.shift_group, "Sabahçı")

    def test_location_shift_group(self):
        loc = Location(name="Bahçe (Sabah)", order_num=1, capacity=2, shift_group="Sabahçı")
        self.db.save_location(loc)

        loaded = self.db.get_location_by_id(loc.id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.shift_group, "Sabahçı")

    def test_password_protection(self):
        # Başlangıçta şifre koruması kapalı
        self.assertFalse(self.db.is_password_protected())
        self.assertTrue(self.db.verify_admin_password(""))

        # Şifre belirle
        self.db.set_admin_password("Meb12345")
        self.assertTrue(self.db.is_password_protected())

        # Doğrulama testleri
        self.assertTrue(self.db.verify_admin_password("Meb12345"))
        self.assertFalse(self.db.verify_admin_password("yanlis"))
        self.assertFalse(self.db.verify_admin_password(""))

        # Şifreyi kaldır
        self.db.set_admin_password("")
        self.assertFalse(self.db.is_password_protected())

    def test_substitution_dialog_empty_absent_teachers(self):
        from unittest.mock import patch
        import customtkinter as ctk
        t1 = Teacher(name="Ahmet Yılmaz", branch="Türkçe")
        self.db.save_teacher(t1)

        root = ctk.CTk()
        root.withdraw()
        try:
            from ui.substitution_dialog import SubstitutionDialog
            dlg = SubstitutionDialog(parent=root, db=self.db, current_week_start="2026-10-05")
            dlg.withdraw()

            # İlk açılışta gelmeyen öğretmen listesi boş olmalı
            self.assertEqual(len(dlg.absent_teachers), 0)
            self.assertIsNone(dlg.active_teacher_id)

            # Bir öğretmen ekleyelim
            dlg.add_teacher_var.set(t1.name)
            dlg._on_add_absent_teacher()
            self.assertEqual(len(dlg.absent_teachers), 1)
            self.assertEqual(dlg.active_teacher_id, t1.id)

            # Listeden son öğretmeni çıkaralım (onay: Evet) - hata vermemeli, liste sıfırlanmalı
            with patch("tkinter.messagebox.askyesno", return_value=True):
                dlg._remove_absent_teacher(t1.id)

            self.assertEqual(len(dlg.absent_teachers), 0)
            self.assertIsNone(dlg.active_teacher_id)
            dlg.destroy()
        finally:
            root.destroy()

    def test_network_service_discovery(self):
        import time
        from logic.network_service import (
            NetworkHostService, NetworkDiscoveryClient,
            get_local_ip, get_hostname
        )
        ip = get_local_ip()
        hname = get_hostname()
        self.assertTrue(len(ip) > 0)
        self.assertTrue(len(hname) > 0)

        # Sunucuyu başlat
        srv = NetworkHostService(self.db_path, "Test Okulu")
        ok, msg = srv.start()
        self.assertTrue(ok)
        self.assertTrue(srv.is_running)

        try:
            time.sleep(0.5)
            # İstemci olarak ağı tara
            hosts = NetworkDiscoveryClient.discover_hosts(timeout=1.2)
            self.assertIsInstance(hosts, list)
            self.assertTrue(len(hosts) >= 1)
            found = next((h for h in hosts if h.get("school_name") == "Test Okulu"), None)
            self.assertIsNotNone(found)
            self.assertEqual(found.get("school_name"), "Test Okulu")
        finally:
            srv.stop()
            self.assertFalse(srv.is_running)

    def test_settings_dialog_lan_tab(self):
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        try:
            from ui.settings_dialog import SettingsDialog
            dlg = SettingsDialog(parent=root, db=self.db)
            dlg.withdraw()

            self.assertIsNotNone(dlg.btn_start_host)
            self.assertIsNotNone(dlg.btn_stop_host)
            self.assertIsNotNone(dlg.btn_scan_hosts)
            self.assertIsNotNone(dlg.lbl_host_status)
            self.assertIsNotNone(dlg.lbl_cur_db)

            # Tarama fonksiyonunun UI frame oluşturmasını test et
            fake_hosts = [{
                "hostname": "MUDUR-PC",
                "ip": "192.168.1.100",
                "school_name": "Atatürk Ortaokulu",
                "share_path": "\\\\MUDUR-PC\\NobetMatik_Ortak\\nobet.db",
                "http_port": 52520
            }]
            dlg._on_scan_completed(fake_hosts)
            # hosts listesinde çocuk widget'lar oluşmalı
            self.assertTrue(len(dlg.f_hosts_list.winfo_children()) > 0)

            dlg.destroy()
        finally:
            root.destroy()

if __name__ == "__main__":
    unittest.main()

