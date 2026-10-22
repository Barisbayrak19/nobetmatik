"""
NöbetMatik - Resimli Kullanım Kılavuzu Görünümü (Guide View)
Uygulama içinde etkileşimli, resimli ve adım adım kullanım rehberi sunar.
"""
import os
import webbrowser
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image

from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_PRIMARY, COLOR_PRIMARY_HOVER,
    COLOR_SECONDARY, COLOR_SUCCESS, COLOR_BORDER, COLOR_BORDER_STRONG,
    COLOR_TEXT_MAIN, COLOR_TEXT_MUTED, FONT_FAMILY
)
from core.config import BASE_DIR, BUNDLE_DIR
from core.logger import logger


class GuideView(ctk.CTkFrame):
    """
    Uygulama içi İnteraktif Kullanım Kılavuzu Paneli.
    Gerçek ekran görüntüleri, adım adım anlatım ve tek tıkla tarayıcıda açma/yazdırma desteği.
    """
    def __init__(self, parent: Any, on_finish: Optional[Callable[[], None]] = None):
        super().__init__(parent, fg_color="transparent")
        self.on_finish = on_finish
        self.current_topic_idx = 0

        # Kılavuz dizinleri
        self.docs_dir = BUNDLE_DIR / "docs"
        if not self.docs_dir.exists():
            self.docs_dir = BASE_DIR / "docs"
        self.screenshots_dir = self.docs_dir / "screenshots"

        self._init_topics_data()
        self._build_ui()
        self._show_topic(0)

    def _init_topics_data(self):
        self.topics = [
            {
                "id": "quickstart",
                "title": "1. Hızlı Başlangıç & Genel Bakış",
                "icon": "🚀",
                "badge": "Başlangıç",
                "image": "01_haftalik_nobet.png",
                "summary": "NöbetMatik, okullarda haftalık nöbet çizelgelerinin hazırlanmasını, öğretmenlerin ders yüklerini, gün tercihlerini ve son dakika gelmeyen öğretmenlerin boş sınıflarını tek merkezden yönetir.",
                "bullets": [
                    "🚀 Kurulum Gerektirmez (Portable): USB bellek veya herhangi bir klasörden doğrudan çalıştırılabilir.",
                    "🧭 Sol Gezinti Menüsü: Haftalık nöbet, Günün Özeti, İkame Asistanı ve Raporlar arasında tek tıkla geçiş yapın.",
                    "💡 Kilit (Sabitleme) Sistemi: İstediğiniz öğretmenleri belirli günlere sabitleyerek otomatik dağıtımda korunmasını sağlayın.",
                    "↶ Geri Al / İleri Al: Yapılan tüm değişiklikleri anında geri alabilir veya eski haline getirebilirsiniz."
                ]
            },
            {
                "id": "teachers",
                "title": "2. Öğretmenler ve Branş Yönetimi",
                "icon": "👥",
                "badge": "Kadro",
                "image": "05_ogretmenler.png",
                "summary": "Okuldaki öğretmenlerin branşları, telefon numaraları, kıdem yılları ve nöbet muafiyet durumları bu ekrandan yönetilir.",
                "bullets": [
                    "➕ Yeni Öğretmen Ekle: Öğretmenin branşını, iletişim numarasını ve kıdem bilgilerini kaydedin.",
                    "🚫 Müsait Olmayan Günler: Öğretmenin dersi olmayan boş günleri işaretleyin; algoritma o günlere asla nöbet yazmaz.",
                    "⭐ Tercih Edilen Günler: Öğretmenlerin nöbet tutmak istediği öncelikli günleri belirtin.",
                    "🛡️ Nöbet Muafiyeti: Sağlık raporu, süt izni veya yasal mazereti olan öğretmenleri nöbetten muaf tutun."
                ]
            },
            {
                "id": "locations",
                "title": "3. Nöbet Yerleri ve Alan Kapasiteleri",
                "icon": "📍",
                "badge": "Bölgeler",
                "image": "06_nobet_yerleri.png",
                "summary": "Okul bahçesi, bina katları, kantin ve pansiyon gibi nöbet alanları ile bu alanlarda kaç öğretmenin bulunacağı belirlenir.",
                "bullets": [
                    "🏢 Nöbet Yeri Tanımlama: 'Bahçe', '1. Kat', '2. Kat', 'Zemin Kat' gibi bölgeleri tanımlayın.",
                    "👥 Kapasite Ayarı: Geniş alanlar için (örneğin Bahçe) kapasiteyi 2 yaparak aynı anda 2 nöbetçi görevlendirin.",
                    "↕️ Sıralama: Resmi çizelge ve nöbet defteri basımında alanların hangi sırayla listeleneceğini yukarı/aşağı oklarla düzenleyin."
                ]
            },
            {
                "id": "import",
                "title": "4. e-Okul / aSc / Excel İçe Aktarma",
                "icon": "📥",
                "badge": "Veri Aktarımı",
                "image": "07_ice_aktarma.png",
                "summary": "e-Okul veya aSc programından aldığınız ders programı raporunu tek tıkla okuyarak öğretmen ve ders programlarını otomatik yükler.",
                "bullets": [
                    "📄 e-Okul Haftalık Ders Programı (PDF): e-Okul'dan aldığınız resmi PDF raporunu doğrudan içeri aktarın.",
                    "📊 aSc Timetables (XML / Excel): aSc ders dağıtım dosyasını yükleyin.",
                    "🔍 Önizleme ve Filtreleme: Aktarılacak öğretmenleri liste üzerinden kontrol edip eksik veya yeni personeli belirleyin.",
                    "⚡ Otomatik Harita: Tüm öğretmenlerin haftalık boş ve dolu ders saatleri saniyeler içinde veritabanına işlenir."
                ]
            },
            {
                "id": "distribution",
                "title": "5. Akıllı Otomatik Nöbet Dağıtımı",
                "icon": "⚡",
                "badge": "Yapay Zeka Dağıtım",
                "image": "04_otomatik_dagitim.png",
                "summary": "MEB yönetmeliğine uygun kural motoruyla öğretmenlerin ders saatlerini, kıdemlerini ve rotasyon dengesini gözeterek adil dağıtım yapar.",
                "bullets": [
                    "🚫 Boş Gün Koruması: Dersi olmayan öğretmene asla nöbet verilmez.",
                    "🔄 Haftalık Rotasyon: Geçen hafta 3. Katta nöbet tutan öğretmen bu hafta Bahçe veya Zemin Kata kaydırılarak adalet sağlanır.",
                    "🔒 Sabit Nöbetleri Koru: Önceden elle kilitlediğiniz nöbetçilere dokunulmaz.",
                    "⚖️ Adalet Skoru: 'Önizleme Hesapla' ile dağıtımı inceleyin; beğendiğinizde 'Dağıtımı Onayla ve Uygula' butonuna basın."
                ]
            },
            {
                "id": "weekly",
                "title": "6. Haftalık Nöbet Çizelgesi & Canlı Panel",
                "icon": "📅",
                "badge": "Ana Ekran",
                "image": "01_haftalik_nobet.png",
                "summary": "Uygulamanın ana çalışma masasıdır. Günler sütun, nöbet alanları satır olarak listelenir.",
                "bullets": [
                    "🌟 Aktif Gün Vurgusu: İçinde bulunduğunuz gün, göz yormayan açık neon yeşil tonuyla otomatik olarak belirginleşir.",
                    "🖱️ Tıkla - Değiştir / Sürükle - Bırak: Nöbetçiyi değiştirmek için hücreye tıklayıp yeni öğretmen seçin.",
                    "🔒 Hücre Kilitleme: Sağ tıklayarak öğretmeni sabitleyin; otomatik dağıtım bu hücreyi değiştirmez.",
                    "📊 Sayaçlar: O günkü toplam nöbetçi, boş bölge ve kilitli nöbet sayılarını anlık takip edin."
                ]
            },
            {
                "id": "daily_summary",
                "title": "7. Günün Özeti & Canlı Nöbetçi Takip Panosu",
                "icon": "☀️",
                "badge": "Canlı Takip",
                "image": "02_gunun_ozeti.png",
                "summary": "Nöbetçi müdür yardımcıları için günün nöbetçileri, boş sınıflar ve müsait öğretmenlerin anlık canlı takip merkezidir.",
                "bullets": [
                    "📋 Günün Nöbetçileri: Hangi öğretmenin nerede nöbetçi olduğunu, branşını ve boş ders saatlerini görün.",
                    "🚨 Boş Sınıf Takibi: Gelmeyen öğretmenlerin boş geçen sınıflarını ve atanan nöbetçileri izleyin.",
                    "📄 Günün Özetini PDF Kaydet: İmzaya hazır resmi A4 günlük takip formunu tek tıkla kaydedin.",
                    "💬 WhatsApp Bildirimi: Nöbetçilere görev yerlerini ve saatlerini WhatsApp üzerinden tek tek veya toplu iletin."
                ]
            },
            {
                "id": "substitution",
                "title": "8. Boş Ders Doldurma & İkame Asistanı",
                "icon": "🔄",
                "badge": "İkame Sistemi",
                "image": "03_ikame_asistani.png",
                "summary": "Okula gelemeyen öğretmenlerin derslerinin boş kalmaması için nöbetçi öğretmenleri sıfır çakışmayla görevlendirir.",
                "bullets": [
                    "➕ Gelmeyen Öğretmeni Ekle: Raporlu, izinli veya görevli öğretmeni seçip ekleyin.",
                    "📚 Derslerin Dökümü: Öğretmenin o günkü tüm ders saatleri ve sınıfları ekrana gelir.",
                    "🎯 Nöbetçi Eşleştirme: O saatte boş olan nöbetçi öğretmenler sistem tarafından otomatik önerilir.",
                    "💾 Kaydet & Fiş Üret: 'TÜM GÖREVLENDİRMELERİ KAYDET' dediğinizde görevlendirme fişleri ve toplu çizelge hazır hale gelir."
                ]
            },
            {
                "id": "reports",
                "title": "9. Resmi Çıktılar, Nöbet Defterleri & Puantaj",
                "icon": "📊",
                "badge": "Raporlar",
                "image": "08_raporlar.png",
                "summary": "Okul müdürlüğü ve denetimler için gereken tüm resmi evraklar tek ekrandan üretilir.",
                "bullets": [
                    "🖨️ Haftalık Çizelge (PDF / Excel / Word): Panolara asılacak resmi onaylı nöbet çizelgesi.",
                    "📖 Resmi Nöbet Defteri Sayfaları: İdareye teslim edilen günlük imza ve olay takip föyü.",
                    "💰 Aylık KBS Ek Ders Puantajı: Tutulan nöbetlerin ek ders modülüne hatasız aktarılması için Excel puantajı.",
                    "👤 Öğretmen Bireysel Nöbet Kartları: Her öğretmenin dönem boyunca tutacağı nöbet günlerinin dökümü."
                ]
            },
            {
                "id": "settings",
                "title": "10. Sistem Ayarları, Güvenlik & Yedekleme",
                "icon": "⚙️",
                "badge": "Yönetim",
                "image": "09_ayarlar.png",
                "summary": "Okul parametreleri, ders giriş-çıkış saatleri, yönetici parolası ve otomatik veritabanı yedekleri.",
                "bullets": [
                    "🏫 Okul Bilgileri: Belgelerde çıkacak okul adı, müdür adı ve öğretim yılını düzenleyin.",
                    "🔔 Ders Saatleri (Zil Saatleri): Okulunuzun günlük ders giriş ve çıkış saatlerini tanımlayın.",
                    "🔐 Yönetici Şifresi: Dağıtım ve öğretmen listesinin izinsiz değiştirilmesini önlemek için şifre koyun.",
                    "💾 Otomatik Yedekleme: Her işlemde veritabanınız otomatik yedeklenir; bilgisayar değişse bile tek tıkla geri yüklenir."
                ]
            },
            {
                "id": "faq",
                "title": "11. Sıkça Sorulan Sorular (SSS)",
                "icon": "❓",
                "badge": "Yardım",
                "image": "01_haftalik_nobet.png",
                "summary": "Kullanıcıların en sık karşılaştığı sorular ve pratik çözüm yolları.",
                "bullets": [
                    "❓ PDF çıktısında Türkçe karakter bozulur mu? Hayır! NöbetMatik v2.2 TrueType Unicode motoruyla Ş, İ, Ğ, Ç, Ö, Ü harflerini kusursuz basar.",
                    "❓ Yanlışlıkla dağıtım yaptım, eski tabloma nasıl dönerim? Üst çubuktaki '↶ Geri Al' butonuna basın veya '💾 Veri Yedekleme' sekmesinden dünkü yedeğe dönün.",
                    "❓ Bir öğretmene kesinlikle belirli bir gün nöbet vermek istemiyorum? '👥 Öğretmenler' sekmesinden o öğretmeni açıp o günü 'Müsait Olmayan Gün' olarak işaretleyin.",
                    "❓ WhatsApp bildirimleri nasıl çalışıyor? WhatsApp butonuna bastığınızda tarayıcınızda veya WhatsApp uygulamasında hazır mesaj şablonu açılır; doğrudan gönderebilirsiniz."
                ]
            }
        ]

    def _build_ui(self):
        # 1. Üst Başlık Kartı
        top_bar = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_BORDER)
        top_bar.pack(fill="x", padx=16, pady=(12, 8))

        f_left = ctk.CTkFrame(top_bar, fg_color="transparent")
        f_left.pack(side="left", padx=16, pady=12)

        ctk.CTkLabel(
            f_left,
            text="📖 NÖBETMATİK 2.2 KULLANIM KILAVUZU & YARDIM MERKEZİ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=COLOR_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            f_left,
            text="Adım adım resimli rehber, modül anlatımları, püf noktaları ve sıkça sorulan sorular.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w", pady=(2, 0))

        # Sağ Butonlar (Tarayıcıda Aç / Yazdır)
        f_actions = ctk.CTkFrame(top_bar, fg_color="transparent")
        f_actions.pack(side="right", padx=14, pady=10)

        btn_html = ctk.CTkButton(
            f_actions,
            text="🌐 Tarayıcıda Aç (HTML)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            height=32,
            corner_radius=6,
            command=self.open_in_browser
        )
        btn_html.pack(side="left", padx=(0, 8))

        btn_print = ctk.CTkButton(
            f_actions,
            text="🖨️ Yazdır / PDF Yap",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color="#F1F5F9",
            hover_color="#E2E8F0",
            text_color=COLOR_TEXT_MAIN,
            height=32,
            corner_radius=6,
            command=self.open_in_browser
        )
        btn_print.pack(side="left")

        # 2. İki Kolonlu Gövde Alanı
        body_container = ctk.CTkFrame(self, fg_color="transparent")
        body_container.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # Sol Kolon: Konu Listesi (Menü)
        self.toc_frame = ctk.CTkScrollableFrame(
            body_container,
            width=260,
            fg_color=COLOR_CARD,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDER
        )
        self.toc_frame.pack(side="left", fill="y", padx=(0, 8))

        ctk.CTkLabel(
            self.toc_frame,
            text="📌 KILAVUZ BÖLÜMLERİ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w", padx=10, pady=(6, 8))

        self.topic_buttons = []
        for idx, t in enumerate(self.topics):
            btn = ctk.CTkButton(
                self.toc_frame,
                text=f"{t['icon']} {t['title'].split('. ')[1] if '. ' in t['title'] else t['title']}",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                anchor="w",
                height=32,
                corner_radius=6,
                fg_color="transparent",
                text_color=COLOR_TEXT_MAIN,
                hover_color="#EFF6FF",
                command=lambda i=idx: self._show_topic(i)
            )
            btn.pack(fill="x", padx=4, pady=2)
            self.topic_buttons.append(btn)

        # Sağ Kolon: İçerik Kartı (Scrollable)
        self.content_scroll = ctk.CTkScrollableFrame(
            body_container,
            fg_color=COLOR_CARD,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDER
        )
        self.content_scroll.pack(side="left", fill="both", expand=True)

        self._build_content_area()

    def _build_content_area(self):
        # Başlık ve Rozet
        header_row = ctk.CTkFrame(self.content_scroll, fg_color="transparent")
        header_row.pack(fill="x", padx=20, pady=(16, 8))

        self.lbl_topic_title = ctk.CTkLabel(
            header_row,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=COLOR_PRIMARY
        )
        self.lbl_topic_title.pack(side="left")

        self.lbl_topic_badge = ctk.CTkLabel(
            header_row,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color="#1E40AF",
            fg_color="#DBEAFE",
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.lbl_topic_badge.pack(side="right")

        # Özet Paragrafı
        self.lbl_summary = ctk.CTkLabel(
            self.content_scroll,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLOR_TEXT_MAIN,
            justify="left",
            wraplength=800
        )
        self.lbl_summary.pack(anchor="w", padx=20, pady=(0, 12))

        # Ekran Görüntüsü Kutusu
        self.img_frame = ctk.CTkFrame(
            self.content_scroll,
            fg_color="#F1F5F9",
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER
        )
        self.img_frame.pack(fill="x", padx=20, pady=(0, 16))

        self.lbl_image = ctk.CTkLabel(self.img_frame, text="")
        self.lbl_image.pack(padx=8, pady=8)

        # Madde İşaretleri / Adımlar Alanı
        self.f_bullets = ctk.CTkFrame(self.content_scroll, fg_color="transparent")
        self.f_bullets.pack(fill="x", padx=20, pady=(0, 16))

        # Alt Navigasyon (Önceki - Sonraki Bölüm)
        nav_row = ctk.CTkFrame(self.content_scroll, fg_color="transparent")
        nav_row.pack(fill="x", padx=20, pady=(12, 20))

        self.btn_prev = ctk.CTkButton(
            nav_row,
            text="◀ Önceki Konu",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            width=110,
            height=30,
            fg_color="#F1F5F9",
            hover_color="#E2E8F0",
            text_color=COLOR_TEXT_MAIN,
            command=self._prev_topic
        )
        self.btn_prev.pack(side="left")

        self.btn_next = ctk.CTkButton(
            nav_row,
            text="Sonraki Konu ▶",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            width=110,
            height=30,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            command=self._next_topic
        )
        self.btn_next.pack(side="right")

    def _show_topic(self, idx: int):
        if not (0 <= idx < len(self.topics)):
            return
        self.current_topic_idx = idx
        data = self.topics[idx]

        # Menü vurgusu
        for i, btn in enumerate(self.topic_buttons):
            if i == idx:
                btn.configure(fg_color=COLOR_PRIMARY, text_color="#FFFFFF", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"))
            else:
                btn.configure(fg_color="transparent", text_color=COLOR_TEXT_MAIN, font=ctk.CTkFont(family=FONT_FAMILY, size=11))

        # Başlık ve Rozet
        self.lbl_topic_title.configure(text=f"{data['icon']} {data['title']}")
        self.lbl_topic_badge.configure(text=data['badge'])
        self.lbl_summary.configure(text=data['summary'])

        # Görseli Yükle
        img_name = data.get("image", "")
        img_path = self.screenshots_dir / img_name
        if img_path.exists():
            try:
                pil_img = Image.open(str(img_path))
                # En-boy oranını koruyarak 760 genişliğe ölçekle
                aspect = pil_img.height / pil_img.width
                target_w = 720
                target_h = int(target_w * aspect)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(target_w, target_h))
                self.lbl_image.configure(image=ctk_img, text="")
            except Exception as e:
                logger.warning(f"Görsel yüklenemedi: {e}")
                self.lbl_image.configure(image=None, text="[Ekran Görüntüsü Yüklenemedi]")
        else:
            self.lbl_image.configure(image=None, text="[Ekran Görüntüsü Bulunamadı]")

        # Maddeleri Temizle ve Yeniden Oluştur
        for child in self.f_bullets.winfo_children():
            child.destroy()

        ctk.CTkLabel(
            self.f_bullets,
            text="📌 Önemli Noktalar & Kullanım Adımları:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        ).pack(anchor="w", pady=(0, 6))

        for bullet in data.get("bullets", []):
            card = ctk.CTkFrame(self.f_bullets, fg_color="#F8FAFC", corner_radius=6, border_width=1, border_color="#E2E8F0")
            card.pack(fill="x", pady=3)
            ctk.CTkLabel(
                card,
                text=bullet,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color="#1E293B",
                justify="left",
                wraplength=720
            ).pack(anchor="w", padx=12, pady=6)

        # Navigasyon butonlarının durumları
        self.btn_prev.configure(state="normal" if idx > 0 else "disabled")
        self.btn_next.configure(state="normal" if idx < len(self.topics) - 1 else "disabled")

    def _prev_topic(self):
        if self.current_topic_idx > 0:
            self._show_topic(self.current_topic_idx - 1)

    def _next_topic(self):
        if self.current_topic_idx < len(self.topics) - 1:
            self._show_topic(self.current_topic_idx + 1)

    def open_in_browser(self):
        """Kullanım kılavuzunu varsayılan web tarayıcısında şık HTML olarak açar."""
        html_path = self.docs_dir / "kullanim_kilavuzu.html"
        if html_path.exists():
            webbrowser.open(str(html_path.resolve()))
        else:
            messagebox.showinfo("Bilgi", "Kılavuz HTML dosyası bulunamadı.", parent=self)
