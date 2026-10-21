# 📋 NöbetMatik Güncelleme ve Sürüm Kayıtları (Changelog)

Bu dosya, NöbetMatik projesinde yapılan tüm yenilikleri, geliştirmeleri ve hata düzeltmelerini gelecek sürümlerde unutulmamak ve release notlarına aktarılmak üzere kayıt altına alır.

---

## 🚀 [Gelecek Büyük Güncelleme - v2.2.0] - Hazırlık Aşamasında

### ✨ Yeni Özellikler & İyileştirmeler
- **🎨 Apple Human Interface Guidelines & macOS Sonoma / Sequoia Tasarım Yenilemesi:**
  - **Ferah Apple Canvas & Saf Beyaz Kartlar:** Çalışma alanı açık gri Apple Canvas zeminine (`#F5F5F7`), nöbet hücreleri ve pencereler saf beyaz squircle kartlara (`#FFFFFF`, `corner_radius=10-12`) dönüştürüldü.
  - **🌓 Özelleştirilebilir Sol Menü Teması (Açık / Koyu):** Sol menü artık kullanıcının tercihine göre tek tıkla (`☀️ / 🌙`) veya `Ayarlar ➔ Görünüm` sekmesinden **Koyu Antrasit (macOS Pro Dark)** ile **Saf Beyaz / Açık Gri (macOS Light)** arasında dinamik olarak değiştirilebilir.
  - **macOS Toolbar & Apple Segmented Control:** Üst araç çubuğu saf beyaz macOS Toolbar formuna, hafta geçişi Apple Segmented Control pill yapısına kavuşturuldu; hızlı eylem butonları Apple yumuşak pastel tonlarıyla (Soft Blue `#007AFF`, Soft Indigo `#5856D6`, Soft Emerald `#34C759`) revize edildi.
  - **Numbers / Calendar Çizelge Tipografisi & Izgara Uyumu:** Tablo başlıkları, boş slotlar, sürükle-bırak animasyonları ve rozetler Apple HIG tipografi standartlarıyla (antrasit `#1D1D1F`, ikincil `#86868B`, ince 1px `#E5E5EA` pürüzsüz sınırlar) harmonize edildi.

- **📖 Resmi MEB Günlük Nöbet Defteri ve Kontrol Raporu Modülü:**
  - **A4 Resmi Günlük Nöbet Sayfası:** MEB mevzuatına uygun olarak o günün görevli nöbetçi öğretmenleri, nöbet yerleri, nöbet görev saatleri ve imza teslim alanlarını içeren profesyonel sayfa çıktısı (`.pdf`).
  - **Devamsızlık ve İkame Senkronizasyonu:** O gün gelmeyen öğretmenler ve yerlerine görevlendirilen nöbetçiler (ek ders hak ediş durumlarıyla birlikte) defter sayfasına otomatik yansıtılır; gelmeyen yoksa *"Tüm dersler eksiksiz işlenmiştir"* onay rozeti eklenir.
  - **Günlük Denetim ve Olay Tutanağı:** Tesisat, hijyen, öğrenci güvenliği ve ders zillerine riayet kontrol maddeleri ile el yazısı veya dijital not girilebilen resmi olaylar alanı.
  - **5 Günlük Haftalık Kitapçık:** İdarecilerin haftalık nöbet klasörünü tek tıkla hazırlayabilmesi için Pazartesi'den Cuma'ya tüm günleri ardışık sayfalarda basan toplu kitapçık seçeneği.
  - **Erişim Kolaylığı:** Ana ekran araç çubuğundaki Dışa Aktar menüsünden ve Raporlar Yönetim Merkezi'nden tek tıkla erişilebilir.

- **⏰ Dinamik Ders Saati Yönetimi ve Çizelge Entegrasyonu:**
  - **Canlı Ders Saatleri Çizelgesi:** `Ayarlar ➔ ⏰ Saatler` sekmesine her dersin (1. Ders, 2. Ders... N. Ders) başlangıç ve bitiş saatlerinin doğrudan kutulardan görüntülenebildiği ve özelleştirilebildiği modern bir arayüz eklendi.
  - **⚡ Otomatik Saat Dağıtımı:** İlk ders başlama saati, ders süresi (varsayılan 40 dk) ve teneffüs süresine (varsayılan 10 dk) göre tüm günün ders ve teneffüs saatlerini tek tıkla hesaplayan akıllı motor eklendi.
  - **Rapor ve Çıktı Senkronizasyonu:** Belirlenen ders saatleri ve günlük ders sayısı;
    - Öğretmen El Programı (PDF & Excel),
    - Sınıf / Şube Haftalık Ders Programı (PDF & Excel),
    - Kurumsal Genel Çarşaf Ders Programı (Excel),
    - Öğretmen Boş Ders Analiz Çizelgesi (Excel),
    - Nöbetçi Öğretmen İkame Görevlendirme Fişleri ve Tutanakları (PDF & HTML),
    - Ana Ekran Canlı Önizleme ve Nöbet Izgarası popover pencerelerine
    tam entegre edildi.
  - Sabit (hardcoded) 7 ders ve eski saat şablonu kaldırıldı; okulun kademesine ve ihtiyacına göre dinamik ders sayısı (6, 7, 8, 9, 10) ve esnek saat desteği sağlandı.

---

## 📌 [v2.1.1] - Mevcut Kararlı Sürüm
- **e-Okul & aSc Granüler İçe Aktarım:** Seçici öğretmen ve ders saati aktarımı.
- **Ek Ders & MEB 44. Madde Uyumu:** Boş ders ikamelerinde branş eşleşmesi ve ek ders rozeti.
- **Personel Devam Takip Modülü:** Aylık devam takip ve resmi çizelgeler.
- **Veri Güvenliği ve Yedekleme:** Otomatik SQLite yedekleme motoru.
