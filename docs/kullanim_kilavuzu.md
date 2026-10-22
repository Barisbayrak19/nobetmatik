# 🛡️ NöbetMatik v2.2 — Resimli ve Adım Adım Kullanma Kılavuzu
> *Milli Eğitim Bakanlığı mevzuatına tam uyumlu, akıllı, adil ve otomatik okul nöbet & boş ders ikame yönetim rehberi.*

---

## 📌 İçindekiler
1. [Hızlı Başlangıç & Sisteme Genel Bakış](#1-hızlı-başlangıç--sisteme-genel-bakış)
2. [Adım 1: Öğretmenler ve Branşların Yönetimi](#2-adım-1-öğretmenler-ve-branşların-yönetimi)
3. [Adım 2: Nöbet Yerleri ve Bölgelerin Belirlenmesi](#3-adım-2-nöbet-yerleri-ve-bölgelerin-belirlenmesi)
4. [Adım 3: Ders Programı & Veri İçe Aktarma (e-Okul / Excel / aSc)](#4-adım-3-ders-programı--veri-içe-aktarma-e-okul--excel--asc)
5. [Adım 4: Akıllı Otomatik Nöbet Dağıtımı](#5-adım-4-akıllı-otomatik-nöbet-dağıtımı)
6. [Adım 5: Haftalık Nöbet Çizelgesi & Canlı Takip Paneli](#6-adım-5-haftalık-nöbet-çizelgesi--canlı-takip-paneli)
7. [Adım 6: Günün Özeti & Canlı Nöbetçi Takip Panosu](#7-adım-6-günün-özeti--canlı-nöbetçi-takip-panosu)
8. [Adım 7: Boş Ders Doldurma & Nöbetçi İkame Asistanı](#8-adım-7-boş-ders-doldurma--nöbetçi-ikame-asistanı)
9. [Adım 8: Raporlar, Resmi Çıktılar & Nöbet Defterleri](#9-adım-8-raporlar-resmi-çıktılar--nöbet-defterleri)
10. [Adım 9: Sistem Ayarları, Güvenlik & Veri Yedekleme](#10-adım-9-sistem-ayarları-güvenlik--veri-yedekleme)
11. [Sıkça Sorulan Sorular (SSS) & Pratik İpuçları](#11-sıkça-sorulan-sorular-sss--pratik-ipuçları)

---

## 1. Hızlı Başlangıç & Sisteme Genel Bakış

NöbetMatik, okullarda nöbet çizelgelerinin hazırlanmasını, öğretmenlerin boş günlerini, kıdemlerini, gün tercihlerini ve son dakika gelmeyen öğretmenlerin boş kalan sınıflarını tek bir merkezden yöneten modern bir okul yönetim yazılımıdır.

### 🧭 Sol Gezinti Menüsü (Sidebar)
Ekranın sol tarafında yer alan menü, tüm işlemlere tek tıkla ulaşmanızı sağlar:
* **📅 Haftalık Nöbet:** Haftanın tüm günleri ve nöbet yerlerinin ana tablosu.
* **☀️ Günün Özeti:** Bugün görevli olan nöbetçiler, boş sınıflar ve canlı durum.
* **🔄 İkame Sistemi:** Gelmeyen öğretmenlerin yerine nöbetçi ve müsait öğretmen görevlendirme.
* **👥 Öğretmenler:** Öğretmen ekleme, branş tanımlama ve nöbet adalet istatistikleri.
* **📍 Nöbet Yerleri:** Bahçe, katlar, pansiyon gibi nöbet alanlarının kapasiteleri.
* **⚡ Otomatik Dağıtım:** Tek tuşla yapay zeka destekli adil nöbet dağıtımı.
* **📥 İçe Aktarma:** e-Okul, aSc Timetables veya Excel dosyalarından ders programı yükleme.
* **📊 Raporlar:** İmzalı nöbet defterleri, aylık puantajlar, öğretmen kartları ve çıktılar.
* **📖 Kullanım Kılavuzu:** Resimli kullanım kılavuzuna doğrudan uygulama içinden ulaşım.
* **⚙️ Ayarlar & Yedek:** Okul bilgileri, zil saatleri ve güvenli veritabanı yedekleri.

---

## 2. Adım 1: Öğretmenler ve Branşların Yönetimi

![Öğretmen Yönetim Paneli](screenshots/05_ogretmenler.png)

Nöbet dağıtımından önce okuldaki tüm öğretmenlerin sisteme tanımlanması gerekir.

### Nasıl Kullanılır?
1. Sol menüden **'👥 Öğretmenler'** seçeneğine tıklayın.
2. Sağ üstteki yeşil **'➕ Yeni Öğretmen Ekle'** butonuna basın.
3. Açılan formda öğretmenin:
   - Adı Soyadı
   - Branşı (Matematik, Türkçe, Beden Eğitimi vb.)
   - Telefon Numarası *(WhatsApp bilgilendirmesi için)*
   - Nöbete dahil olup olmadığı *(Nöbet tutar / Tutamaz)*
   - Kıdem yılı *(20-25 yıl üzeri muafiyet talepleri için)*
4. **'Kaydet'** butonuna basarak işlemi tamamlayın.

> 💡 **İpucu:** Öğretmenlerin haftalık ders programını elle tek tek girmek zorunda değilsiniz! **'📥 İçe Aktarma'** sekmesinden e-Okul veya Excel ders programını yüklediğinizde tüm öğretmenler ve ders saatleri **otomatik** olarak içeri aktarılır.

---

## 3. Adım 2: Nöbet Yerleri ve Bölgelerin Belirlenmesi

![Nöbet Yerleri Paneli](screenshots/06_nobet_yerleri.png)

Okul binasındaki görev yerleri (Bahçe, 1. Kat, 2. Kat, Zemin Kat vb.) bu ekrandan yönetilir.

### Nasıl Kullanılır?
1. Sol menüden **'📍 Nöbet Yerleri'** sekmesine tıklayın.
2. **'Yeni Nöbet Yeri Ekle'** butonuyla alan oluşturun.
3. Her alan için **Kapasite** belirleyin:
   - Örneğin okul bahçesi genişse *'Bahçe'* kapasitesini **2** yaparak aynı anda iki nöbetçi görevlendirebilirsiniz.
   - Sadece tek öğretmenin yeterli olduğu katlarda kapasiteyi **1** bırakın.
4. Sıralama oklarını kullanarak tablonun resmi evrakta hangi sırayla basılacağını belirleyin.

---

## 4. Adım 3: Ders Programı & Veri İçe Aktarma (e-Okul / Excel / aSc)

![İçe Aktarma Merkezi](screenshots/07_ice_aktarma.png)

NöbetMatik, okullarda en çok kullanılan tüm formatları tek tuşla tanır.

### Desteklenen Dosya Formatları:
* **e-Okul Haftalık Ders Programı (PDF):** e-Okul'dan aldığınız resmi çarşaf programı doğrudan seçebilirsiniz.
* **aSc Timetables (XML / Excel):** aSc programından dışa aktarılan ders çizelgeleri.
* **Excel / CSV Çizelgeleri:** Öğretmen listesi ve ders dağılımları.

### Yükleme Adımları:
1. **'📥 İçe Aktarma'** sekmesini açın.
2. Dosya türünü seçip **'Dosya Seç'** butonuna tıklayın.
3. Sistem verileri tarar, öğretmenleri ve ders programlarını tablo halinde önizler.
4. **'Veritabanına Aktar'** butonuna bastığınızda okulun tüm ders haritası hazırlanmış olur.

---

## 5. Adım 4: Akıllı Otomatik Nöbet Dağıtımı

![Otomatik Dağıtım Ekranı](screenshots/04_otomatik_dagitim.png)

MEB mevzuatına uygun şekilde öğretmenlerin boş günlerini, ders saatlerini ve adalet dengesini otomatik analiz eder.

### Dağıtım Kuralları (İsteğe Bağlı Seçenekler):
* **Dersi olmayan boş günlere nöbet yazma:** Öğretmenin okulda bulunmadığı güne nöbet yazılmasını engeller.
* **Ardışık günleri engelle:** Bir öğretmene peş peşe (örneğin Pazartesi ve Salı) nöbet verilmesini önler.
* **Önceki haftaya göre rotasyon:** Geçen hafta 3. Katta nöbet tutan öğretmeni bu hafta Bahçe veya Zemin Kata kaydırarak adalet sağlar.
* **Kıdem muafiyeti:** 20-25 yılını doldurmuş öğretmenlerin muafiyet taleplerini gözetir.
* **Sabit nöbetleri koru:** Önceden elle sabitlediğiniz (kilitlediğiniz) nöbetçilere dokunmaz.

> ⚠️ **Önemli:** **'Önizleme Hesapla'** butonuna bastığınızda sistem olası dağıtımı hesaplar ve bir adalet skoru sunar. Sonucu beğendiğinizde **'Dağıtımı Onayla ve Uygula'** demeniz yeterlidir!

---

## 6. Adım 5: Haftalık Nöbet Çizelgesi & Canlı Takip Paneli

![Haftalık Nöbet Ekranı](screenshots/01_haftalik_nobet.png)

Burası uygulamanın ana kumanda merkezidir. Haftanın tüm günleri sütunlar halinde, nöbet yerleri ise satırlar halinde listelenir.

### Önemli Özellikler:
* **Günün Belirginleştirilmesi (Neon Vurgusu):** İçinde bulunduğunuz gün, göz yormayan özel açık yeşil tonuyla otomatik olarak vurgulanır.
* **Sürükle - Bırak veya Tıkla - Değiştir:** Bir öğretmenin nöbet yerini değiştirmek için hücreye tıklayıp başka bir öğretmen seçebilir veya sağ tıklayarak sabitleyebilirsiniz.
* **Kilit Simgesi (🔒):** Özel bir nedenle belirli bir güne sabitlenen öğretmeni kilitlerseniz, otomatik dağıtım bu hücreyi asla değiştirmez.
* **Geri Al / İleri Al:** Yanlış bir işlem yaptığınızda üst çubuktaki **↶ Geri Al** butonuna basarak her an eski haline dönebilirsiniz.

---

## 7. Adım 6: Günün Özeti & Canlı Nöbetçi Takip Panosu

![Günün Özeti Ekranı](screenshots/02_gunun_ozeti.png)

Okul idarecileri ve nöbetçi müdür yardımcıları için günün canlı durumunu gösteren özel kontrol ekranıdır.

### Bu Ekranda Neler Var?
1. **Günün Nöbetçileri Listesi:** Bugün hangi öğretmenin hangi bölgede görevli olduğu, branşı ve boş ders saatleri.
2. **Boş Sınıflar ve İkame Merkezi:** Bugün izinli veya raporlu olan öğretmenlerin boş geçen sınıfları ve yerlerine atanan nöbetçiler.
3. **Müsait Öğretmenler Sekmesi:** Herhangi bir acil durumda o saatte dersi olmayan boş öğretmenlerin anlık listesi.
4. **📄 PDF Olarak Kaydet:** Günün özetini resmi A4 formatında tek tıkla imzaya hazır PDF olarak kaydeder.
5. **💬 WhatsApp Bildirimi:** Nöbetçi öğretmenlere görev yerlerini ve saatlerini WhatsApp üzerinden tek tek veya toplu olarak iletir.

---

## 8. Adım 7: Boş Ders Doldurma & Nöbetçi İkame Asistanı

![İkame Sistemi](screenshots/03_ikame_asistani.png)

Bir veya birden fazla öğretmen okula gelemediğinde, sınıfların boş kalmaması için geliştirilmiş akıllı görevlendirme modülüdür. Artık ana pencere içinde tam sayfa olarak çalışır.

### Adım Adım İkame Görevlendirme:
1. **Tarih Seçimi:** İkame yapılacak günü seçin.
2. **Gelmeyen Öğretmeni Seçin:** Açılır listeden okula gelmeyen öğretmeni ve nedenini (Raporlu, İzinli, Görevli vb.) seçip **'➕ Listeye Ekle'** butonuna basın.
3. **Derslerin Listelenmesi:** Öğretmenin o günkü tüm ders saatleri ve sınıfları ekrana gelir.
4. **Nöbetçi Önerisi:** Sistem o ders saatinde boşta olan o günün nöbetçi öğretmenlerini listeler.
5. **Tek Tıkla Atama:** İkame görevlisini seçin veya **'Akıllı Otomatik Doldur'** butonuna basarak tüm boş derslerin sıfır çakışmayla atanmasını sağlayın.
6. **💾 Kaydet & Yazdır:** **'TÜM GÖREVLENDİRMELERİ KAYDET'** butonuna bastığınızda:
   - İkameler sisteme işlenir,
   - İlgili öğretmenler için **Görevlendirme Fişi** ve **Toplu İkame Çizelgesi** hazırlanır.

---

## 9. Adım 8: Raporlar, Resmi Çıktılar & Nöbet Defterleri

![Raporlar ve Belgeler](screenshots/08_raporlar.png)

Okul müdürlüğü ve denetimler için gereken tüm resmi evraklar tek ekrandan üretilir:

* **Haftalık Nöbet Çizelgesi (A4 / A3 Çarşaf):** Öğretmenler odası panosu ve müdürlük onayı için imzalı format.
* **Resmi Nöbet Defteri Sayfaları:** İdareye teslim edilen günlük imza ve olay takip föyü.
* **Aylık KBS Ek Ders Puantajı (Excel):** Tutulan nöbetlerin ek ders modülüne hatasız aktarılması için resmi puantaj.
* **Öğretmen Bireysel Nöbet Kartları:** Her öğretmenin dönem boyunca tutacağı nöbet günlerini gösteren kartlar.

---

## 10. Adım 9: Sistem Ayarları, Güvenlik & Veri Yedekleme

![Sistem Ayarları](screenshots/09_ayarlar.png)

### Ayarlar Menüsünden Yapabilecekleriniz:
* **Okul Adı ve Müdürü:** Çıktılarda görünecek resmi okul adı, ilçe ve müdür adını düzenleyin.
* **Ders Saatleri (Zil Saatleri):** 1. Dersten 8. Derse kadar okulunuzun giriş-çıkış saatlerini tanımlayın.
* **Yönetici Şifresi:** Dağıtımın ve listelerin izinsiz değiştirilmesini önlemek için yönetici parolası koyun.
* **Otomatik Veri Yedekleme:** Her çıkışta veritabanınız ackups/ klasörüne tarih-saat etiketiyle yedeklenir. Bilgisayar değiştirseniz bile yedeği geri yükleyerek kaldığınız yerden devam edebilirsiniz.

---

## 11. Sıkça Sorulan Sorular (SSS) & Pratik İpuçları

### 💡 Sıkça Karşılaşılan Durumlar ve Çözümleri:

1. **Soru: Bir öğretmen belirli bir gün kesinlikle nöbet tutmak istemiyor, ne yapmalıyım?**
   - *Cevap:* Öğretmenler sekmesinden ilgili öğretmeni çift tıklayın, *'Nöbet Tutulmayacak Günler'* kısmından o günü işaretleyin. Otomatik dağıtım o güne asla nöbet yazmayacaktır.

2. **Soru: PDF çıktısı aldığımda Türkçe karakterler bozulur mu?**
   - *Cevap:* Hayır! NöbetMatik v2.2 dahili Unicode font motoru sayesinde Ş, İ, Ğ, Ç, Ö, Ü ve küçük harfler resmi yazışma kalitesinde pürüzsüz basılır.

3. **Soru: Yanlışlıkla otomatik dağıtım yaptım, eski tabloma dönebilir miyim?**
   - *Cevap:* Evet! Üstteki **↶ Geri Al** butonuna tıklayarak veya sol menüdeki **Veri Yedekleme** ekranından önceki günün yedeğine tek tıkla dönebilirsiniz.

4. **Soru: WhatsApp bildirimleri nasıl çalışıyor?**
   - *Cevap:* Öğretmenin telefon numarası kayıtlıysa, Günün Özeti ekranındaki WhatsApp butonuna bastığınızda varsayılan tarayıcınızda veya WhatsApp uygulamasında hazır mesaj şablonu açılır. Tek yapmanız gereken Gönder'e basmaktır.
