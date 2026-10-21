# 📋 NöbetMatik Güncelleme ve Sürüm Kayıtları (Changelog)

Bu dosya, NöbetMatik projesinde yapılan tüm yenilikleri, geliştirmeleri ve hata düzeltmelerini gelecek sürümlerde unutulmamak ve release notlarına aktarılmak üzere kayıt altına alır.

---

## 🚀 [Gelecek Büyük Güncelleme - v2.2.0] - Hazırlık Aşamasında

### ✨ Yeni Özellikler & İyileştirmeler
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
