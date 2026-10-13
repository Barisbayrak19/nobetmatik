# 📖 NöbetMatik v2.0 — Kapsamlı Kullanım Kılavuzu

Hoş geldiniz! **NöbetMatik v2.0**, okul idarecilerinin haftalık nöbet çizelgelerini MEB yönetmeliklerine %100 uyumlu, adil, pratik ve hatasız şekilde hazırlamaları için tasarlanmış yeni nesil masaüstü uygulamasıdır.

---

## 📑 İçindekiler
1. [Hızlı Başlangıç ve İlk Kurulum](#1-hızlı-başlangıç-ve-ilk-kurulum)
2. [Ders Programı İçe Aktarma (e-Okul & aSc)](#2-ders-programı-içe-aktarma-e-okul--asc)
3. [Öğretmen ve Nöbet Yeri Yönetimi](#3-öğretmen-ve-nöbet-yeri-yönetimi)
4. [Haftalık Nöbet Çizelgesi ve Otomatik Dağıtım](#4-haftalık-nöbet-çizelgesi-ve-otomatik-dağıtım)
5. [İnteraktif Çizelge: Sürükle-Bırak, Takas ve Sabitleme](#5-interaktif-çizelge-sürükle-bırak-takas-ve-sabitleme)
6. [Hafta Rotasyonu ve İleriye Aktarım](#6-hafta-rotasyonu-ve-ileriye-aktarım)
7. [Boş Ders Doldurma ve İkame Görevlendirme](#7-boş-ders-doldurma-ve-ikame-görevlendirme)
8. [Raporlar ve Resmi Çıktı Merkezi](#8-raporlar-ve-resmi-çıktı-merkezi)
9. [Veri Güvenliği, Yedekleme ve Sistem Ayarları](#9-veri-güvenliği-yedekleme-ve-sistem-ayarları)
10. [Sıkça Sorulan Sorular (SSS)](#10-sıkça-sorulan-sorular-sss)

---

## 1. Hızlı Başlangıç ve İlk Kurulum

### 🚀 Kurulum Gerektirmez (Portable)
NöbetMatik bağımsız (portable) bir uygulamadır; bilgisayarınıza karmaşık kurulumlar yapmaz, sistem kayıt defterini kirletmez.

1. İndirdiğiniz **`NobetMatik_v2.0.2_Tasinabilir.zip`** arşivini masaüstünüze veya istediğiniz bir klasöre çıkartın.
2. Klasör içindeki **`NobetMatik.exe`** dosyasına çift tıklayın.
3. Program ilk kez açıldığında sizi **Kurulum Sihirbazı** karşılar:
   - **Okul Adı ve Müdür Bilgileri:** Çıktılarda görünecek resmi okul adı ve müdür adını girin.
   - **Eğitim Öğretim Yılı:** (Örn: `2026-2027`)
   - **Çalışma Modu:** Normal (Tam Gün), Sabahçı / Öğlenci ikili eğitim seçeneğini belirleyin.
   - **Başlangıç Seçeneği:** *"e-Okul'dan Kendi Okulumu İçe Aktar"*, *"Örnek Okul Verileriyle Başla"* veya *"Sıfırdan Başla"* seçeneklerinden birini tercih edin.
4. *"Kurulumu Tamamla"* butonuna bastığınızda ana çalışma ekranına ulaşırsınız.

> [!TIP]
> NöbetMatik klasörünü bir USB flash belleğe kopyalayarak evinizdeki veya okulunuzdaki herhangi bir Windows bilgisayarda doğrudan çalıştırabilirsiniz.

---

## 2. Ders Programı İçe Aktarma (e-Okul & aSc)

Öğretmenleri ve haftalık ders programlarını tek tek elle yazmanıza gerek yoktur!

### 📄 e-Okul PDF'inden İçe Aktarma:
1. **e-Okul** sistemine giriş yapın:  
   *Kurum İşlemleri ➔ Ders İşlemleri ➔ Haftalık Ders Programı* ekranından okulun haftalık ders programı PDF raporunu bilgisayarınıza indirin.
2. NöbetMatik sol menüsünden **📥 İçe Aktarma** sekmesine tıklayın.
3. *"e-Okul PDF Yükle"* butonuna basarak indirdiğiniz PDF dosyasını seçin.
4. **Granüler Seçim Ekranı:** Açılan listede e-Okul'daki tüm öğretmenler, branşları ve haftalık ders saatleri listelenir. İstediğiniz öğretmenleri seçebilir veya filtreleyebilirsiniz.
5. *"Seçilenleri Sisteme Aktar"* dediğinizde öğretmen listesi ve haftalık boş/dolu ders saatleri saniyeler içinde veritabanınıza işlenir.

### 📊 aSc Timetables Dosyasından Aktarma:
- aSc Timetables programından aldığınız `.xml` veya `.csv` dosyasını aynı ekrandan yükleyerek öğretmen ve ders dağılımını eksiksiz içeri alabilirsiniz.

---

## 3. Öğretmen ve Nöbet Yeri Yönetimi

### 👥 Öğretmenler Sekmesi:
- **Müsait Olmayan Günler:** Öğretmenin dersinin olmadığı veya izinli olduğu günleri işaretleyin; algoritma o günlere nöbet yazmaz.
- **Tercih Edilen Günler:** Öğretmenin nöbet tutmak istediği öncelikli günler.
- **Kıdem Yılı:** MEB yönetmeliği gereği kıdemli öğretmenlerin tercih günlerini öncelemek için kıdem yılını girin.
- **Nöbet Muafiyeti:** Hamilelik, analık izni, sağlık raporu veya engellilik muafiyeti olan öğretmenler için *"Muaf"* kutucuğunu işaretleyin (Gerekçesiyle birlikte arşivlenir).

### 📍 Nöbet Yerleri Sekmesi:
- Okulunuzdaki nöbet bölgelerini tanımlayın: (Örn: *Bahçe*, *Zemin Kat*, *1. Kat*, *Kantin*, *Spor Salonu*).
- **Kapasite:** Her nöbet bölgesinde kaç öğretmenin görev yapacağını belirleyin (Örn: Bahçe 2 kişi, 1. Kat 1 kişi).
- **Sıralama:** Bölgelerin çizelgede hangi sırada görüneceğini `▲` ve `▼` butonlarıyla ayarlayın.

---

## 4. Haftalık Nöbet Çizelgesi ve Otomatik Dağıtım

NöbetMatik'in kalbi olan **Akıllı Adalet Motoru**, saatler süren nöbet planlamasını saniyeler içinde tamamlar.

### ⚡ Otomatik Dağıtım Adımları:
1. Üst işlem çubuğundan **`⚡ Dağıt`** butonuna basın (veya sol menüden *Otomatik Dağıtım* sekmesine geçin).
2. **Dağıtım İlkeleri Paneli:** İhtiyacınıza göre dağıtım kurallarını seçin:
   - *Tüm Müsait Öğretmenlere Nöbet Ver:* Dersi az olan veya boş saati çok olan öğretmenleri dengeler.
   - *Kıdemli Öğretmenlere Öncelik Ver:* Kıdem yılı yüksek öğretmenlerin tercih ettiği günlere öncelik tanır.
   - *Yetersiz Kalırsa 2. Nöbet Günü Ver:* Öğretmen sayısı nöbet yuvasından azsa kimseye haksızlık olmadan 2. nöbetleri eşit paylaştırır.
3. **`⚡ Dağıtımı Hesapla`** butonuna tıklayın.
4. **Önizleme & Adalet Analizi:** Sistem dağıtım sonucunu, öğretmenlerin ders yükü dengesini ve varsa uyarıları ekranda gösterir.
5. *"Çizelgeye Uygula"* butonuna bastığınızda haftalık tablonuz hazır hale gelir!

---

## 5. İnteraktif Çizelge: Sürükle-Bırak, Takas ve Sabitleme

Oluşan çizelge üzerinde tam kontrole sahipsiniz:

* **Sürükle & Bırak (Drag & Drop):**  
  Bir öğretmeni farenin sol tuşuyla tutup başka bir güne veya nöbet yerine taşıyın. Eğer hedef yuva doluysa iki öğretmen otomatik olarak **karşılıklı takas (Swap)** edilir.
* **Sabitleme (🔒 Sabit Kilit):**  
  Belirli bir öğretmenin nöbet yerini sabitlemek istiyorsanız hücreye sağ tıklayıp **`📌 Sabitle`** seçeneğini işaretleyin. Otomatik dağıtım yeniden çalışsa bile kilitli nöbetçiler asla yerinden oynamaz.
* **Geri Al / İleri Al (Undo / Redo):**  
  Yanlışlıkla bir öğretmeni taşıdıysanız klavyeden **`Ctrl + Z`** tuşuna basarak veya üst bardaki **`↶`** simgesine tıklayarak sınırsız adım geri alabilirsiniz.
* **Öğretmen Bilgi Kartı (Popover):**  
  Öğretmen kartına **çift tıkladığınızda** o öğretmenin branşı, o günkü boş ders saatleri ve iletişim bilgileri mini pencerede açılır.

---

## 6. Hafta Rotasyonu ve İleriye Aktarım

Bir sonraki haftanın nöbet çizelgesini sıfırdan hazırlamak zorunda değilsiniz:

1. Üst çubuktan **`›`** butonuna basarak bir sonraki haftaya geçin.
2. Sistem size otomatik aktarma seçenekleri sunar (veya `••• ▾` menüsünden dilediğiniz modu seçebilirsiniz):
   - **Birebir Aynı Aktar:** Mevcut haftadaki dağılımı sonraki haftaya aynen kopyalar.
   - **1 Gün Kaydırarak Aktar (Rotasyon):** Pazartesi nöbetçileri Salı'ya, Salı nöbetçileri Çarşamba'ya kayar; böylece hiçbir öğretmen sürekli aynı gün nöbet tutmaz.
   - **Nöbet Yerlerini Kaydırarak Aktar:** Bahçe nöbetçisi kata, kat nöbetçisi kantine geçer; nöbet yerleri adilce döner.

---

## 7. Boş Ders Doldurma ve İkame Görevlendirme

Bir öğretmen raporlu veya sevkli olduğunda sınıfların boş kalmaması için:

1. Üst bardaki **`👥`** (İkame) butonuna tıklayın.
2. O gün izinli olan öğretmeni seçin (Öğretmenin o günkü dersleri listelenir).
3. Hangi ders saatlerinin doldurulacağını işaretleyin.
4. Sistem, **o ders saatinde nöbetçi olan ve boş dersi bulunan öğretmenleri** adalet puanına göre sıralar.
5. İlgili öğretmeni seçip *"Görevi Ata"* dediğinizde ikame işlemi kaydedilir.
6. **`🖨️ Resmi İkame Tutanağı Yazdır`** butonuna basarak MEB ek ders onayına uygun resmi görevlendirme belgesini anında yazdırabilirsiniz.

---

## 8. Raporlar ve Resmi Çıktı Merkezi

NöbetMatik, okul müdürlüğü onayına ve panolara asılmaya hazır profesyonel çıktılar üretir:

* **A4 Yatay Haftalık Nöbet Çizelgesi:** MEB yönetmelik formatında, okul başlıklı, nöbet talimatlı ve müdür onay imzalı resmi belge (PDF, Excel, Word, HTML).
* **Öğretmen El Programları:** Her öğretmenin sadece kendi ders ve nöbetini içeren kişisel el programları (İster tek tek, ister tüm öğretmenler tek bir PDF dosyasında).
* **Sınıf / Şube Haftalık Ders Programları:** Sınıf panolarına asılacak haftalık ders çizelgeleri.
* **Personel Devam Takip Çizelgeleri:** Günlük ve aylık öğretmen imza sirküleri.
* **Genel Çarşaf Program:** Tüm okulun tek bir Excel tablosunda büyük görünümü.

> [!NOTE]
> Yazdırmadan önce üst bardaki **`🖨️`** simgesine tıklayarak **Baskı Önizleme** penceresinde belgenin sayfa yerleşimini inceleyebilirsiniz.

---

## 9. Veri Güvenliği, Yedekleme ve Sistem Ayarları

* **Yönetici Şifresi:** Yetkisiz kişilerin nöbet çizelgesini veya öğretmen bilgilerini değiştirmesini engellemek için *Ayarlar* menüsünden yönetici PIN şifresi belirleyebilirsiniz.
* **Otomatik Güvenlik Yedeği:** Her önemli işlemden önce (sıfırlama, toplu dağıtım vb.) sistem otomatik olarak `backups/` klasörüne zaman damgalı `.db` yedeği alır.
* **Manuel Yedekleme:** Sol menüden *Veri Yedekleme* sekmesine giderek dilediğiniz an tek tıkla tam yedek alabilir veya eski bir yedeğe geri dönebilirsiniz.
* **Geliştirici Geri Bildirim Hattı:** Karşılaştığınız bir sorunu veya yeni özellik önerinizi üst bardaki **`💬`** butonuna tıklayarak doğrudan geliştiriciye iletebilirsiniz.

---

## 10. Sıkça Sorulan Sorular (SSS)

**S: NöbetMatik internet olmadan çalışır mı?**  
**C:** Evet, NöbetMatik %100 yerel ve çevrimdışı çalışacak şekilde tasarlanmıştır. İnternet bağlantısı sadece isteğe bağlı sürüm güncellemesi ve geri bildirim için kullanılır.

**S: Bilgisayarım bozulursa veya format atılırsa verilerim kaybolur mu?**  
**C:** NöbetMatik klasörünün içindeki `data/nobet.db` dosyasını flash belleğinize veya e-postanıza yedeklediğiniz sürece hiçbir veriniz kaybolmaz. Yeni bilgisayara klasörü kopyalamanız yeterlidir.

**S: Bir öğretmene haftada en fazla kaç gün nöbet verilebilir?**  
**C:** MEB mevzuatına göre standart kural haftada 1 gündür. Ancak okulunuzda öğretmen sayısı yetersizse *Otomatik Dağıtım* ekranındaki *"Yetersiz Kalırsa 2. Nöbet Günü Ver"* seçeneğini işaretleyerek 2. nöbetleri eşit dağıtabilirsiniz.

**S: Sürükle-bırak yaparken yanlışlıkla nöbetçiyi sildim, nasıl düzeltirim?**  
**C:** Hemen klavyenizden `Ctrl + Z` tuşuna basın veya üst bardaki `↶` (Geri Al) butonuna tıklayın.

---

*NöbetMatik v2.0 ile iyi çalışmalar ve başarılı eğitim öğretim yılları dileriz!* 🎓
