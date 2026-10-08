"""
Gerçek Kurulum Referans Verileri
Şehit Kadir Altuntaş Cumhuriyet Ortaokulu resmi verileri ve nöbet çizelgesi.
Nöbet listesinde yer almayan öğretmenler (idareciler, rehberlik, okul öncesi, özel eğitim vb.) varsayılan olarak pasif işaretlenmiştir.
"""
from typing import Dict, List, Any

REFERENCE_SCHOOL = {
    "name": "Şehit Kadir Altuntaş Cumhuriyet Ortaokulu",
    "city": "İzmir",
    "district": "Torbalı",
    "academic_year": "2026-2027",
    "principal_name": "Salahattin GÜNEK",
    "duty_rules": (
        "1- Günlük vakit çizelgesini uygulamak.\n"
        "2- Öğretmenlerin derslere zamanında girip girmediğini izlemek ve öğretmeni gelmeyen sınıfları okul yönetimine bildirmek ve bu sınıflara nezaret etmek.\n"
        "3- Isıtma elektrik ve sıhhı tesislerin çalışıp çalışmadığını okul içi temizliğin yapılıp yapılmadığının okul bina ve tesislerinin yangından koruma önlemlerinin alınıp alınmadığının günlük kontrollerini yapmak giderilebildiği eksikleri gidermek gerekli olanları ilgililere duyurmak.\n"
        "4- Bahçedeki, koridorlardaki ve sınıflardaki öğrencileri gözetlemek.\n"
        "5- Beklenmedik olaylar karşısında gerekli tedbirleri almak ve bu durumu ilgililere bildirmek.\n"
        "6- Nöbet süresince okulun eğitim öğretim disiplin gibi çeşitli işlerini izlemek bu hususlarda günlük tedbirleri almak.\n"
        "7- Nöbet sonunda okul nöbet defterine nöbet süresi içerisinde önemli olayları ve aldığı tedbirleri belirten raporu yazmak."
    )
}

REFERENCE_DAYS = [
    {"name": "Pazartesi", "order_num": 1},
    {"name": "Salı", "order_num": 2},
    {"name": "Çarşamba", "order_num": 3},
    {"name": "Perşembe", "order_num": 4},
    {"name": "Cuma", "order_num": 5}
]

# Nöbet Yerleri: Bahçe 1 ve Bahçe 2 ayrı nöbet yerleri olarak yapılandırılmıştır.
REFERENCE_LOCATIONS = [
    {"name": "1. KAT", "order_num": 1, "capacity": 1},
    {"name": "2. KAT", "order_num": 2, "capacity": 1},
    {"name": "3. KAT", "order_num": 3, "capacity": 1},
    {"name": "BAHÇE 1", "order_num": 4, "capacity": 1},
    {"name": "BAHÇE 2", "order_num": 5, "capacity": 1},
    {"name": "ZEMİN KAT", "order_num": 6, "capacity": 1}
]

# Gerçek Haftalık Nöbet Çizelgesi (Bahçe 1 ve Bahçe 2 ayrı yerler olarak atanmıştır)
REFERENCE_DUTY_TABLE = {
    "Pazartesi": {
        "1. KAT": ["MEHMET BEYDİLLİ"],
        "2. KAT": ["İLKNUR AKBAŞ UZUN"],
        "3. KAT": ["MELTEM ÖZEL"],
        "BAHÇE 1": ["ADNAN KIRLIOĞLU"],
        "BAHÇE 2": ["ANIL ÇATAK"],
        "ZEMİN KAT": ["ÖZNUR GÖKMEN ATASOY"]
    },
    "Salı": {
        "1. KAT": ["AYŞE EREN"],
        "2. KAT": ["DERYA YILDIZ SAVAŞ"],
        "3. KAT": ["MEHMET ÖZBEK"],
        "BAHÇE 1": ["FATMA ÇETİN"],
        "BAHÇE 2": ["NALAN NARİN SÖNMEZ"],
        "ZEMİN KAT": ["ÇİĞDEM YALÇINKAYA"]
    },
    "Çarşamba": {
        "1. KAT": ["BELGİN ÇAKIN"],
        "2. KAT": ["GÜLAY YILMAZ"],
        "3. KAT": ["LATİF CANDAN"],
        "BAHÇE 1": ["AHU ŞENOL ÇALIK"],
        "BAHÇE 2": ["VEYSİ ALTUN"],
        "ZEMİN KAT": ["YASEMİN GÖKOĞLU"]
    },
    "Perşembe": {
        "1. KAT": ["GÜLAY AYDIN SÖLPÜK"],
        "2. KAT": ["AYŞEGÜL KAYA"],
        "3. KAT": ["FUNDA VAROL DEMİR"],
        "BAHÇE 1": ["NEZAHAT SALMAN"],
        "BAHÇE 2": ["VİLDAN SATAN ERSOY"],
        "ZEMİN KAT": ["SILA ÖZGÜN AYDIN"]
    },
    "Cuma": {
        "1. KAT": ["ARZU KARAKÜLAH"],
        "2. KAT": ["ASLI ÖRGÜN AŞUTKALIOĞLU"],
        "3. KAT": ["SEHER AYDIN"],
        "BAHÇE 1": ["ŞENCAN YEŞİL"],
        "BAHÇE 2": ["ZEHRA ARAS"],
        "ZEMİN KAT": ["YASEMİN SAKA KILIÇ"]
    }
}

# Nöbet çizelgesinde fiilen yer alan öğretmenler (30 kişi)
DUTY_TEACHERS_SET = {
    t_name
    for day_dict in REFERENCE_DUTY_TABLE.values()
    for loc_list in day_dict.values()
    for t_name in loc_list
}

# Gerçek Öğretmen Listesi (İsim, Branş, Aktif/Pasif, Not)
# Nöbet listesindeki 30 öğretmen is_active=True, diğerleri is_active=False
RAW_TEACHERS_DATA = [
    ("ADNAN KIRLIOĞLU", "Sosyal Bilgiler", ""),
    ("AHU ŞENOL ÇALIK", "Fen Bilimleri", ""),
    ("ALİ EMRE KARAGÖZ", "Özel Eğitim", "Özel Eğitim Öğretmeni (Nöbet Muaf)"),
    ("ANIL ÇATAK", "Fen Bilimleri", ""),
    ("ARZU KARAKÜLAH", "İlköğretim Matematik", ""),
    ("ASLI ÖRGÜN AŞUTKALIOĞLU", "İngilizce", ""),
    ("AYŞE EREN", "Sosyal Bilgiler", ""),
    ("AYŞEGÜL KAYA", "Din Kültürü ve Ahlâk Bilgisi", ""),
    ("BARIŞ BAYRAK", "Din Kültürü ve Ahlâk Bilgisi", "Müdür Yardımcısı (Nöbet Muaf)"),
    ("BELGİN ÇAKIN", "Müzik", ""),
    ("BURCU UÇAR", "Beden Eğitimi", "Nöbet Listesi Dışı"),
    ("ÇİĞDEM YALÇINKAYA", "Din Kültürü ve Ahlâk Bilgisi", ""),
    ("DENİZ AKER", "Okul Öncesi", "Okul Öncesi Öğretmeni (Nöbet Muaf)"),
    ("DERYA YILDIZ SAVAŞ", "Türkçe", ""),
    ("ESRA LAÇİN YILMAZ", "Okul Öncesi", "Okul Öncesi Öğretmeni (Nöbet Muaf)"),
    ("FATMA ÇETİN", "Fen Bilimleri", ""),
    ("FATMA EMOL DAGALAN", "Özel Eğitim", "Özel Eğitim Öğretmeni (Nöbet Muaf)"),
    ("FERDİ CAN", "Bilişim Teknolojileri", "Bilişim Öğretmeni"),
    ("FETHİYE GÜNER UĞURLU", "Okul Öncesi", "Okul Öncesi Öğretmeni (Nöbet Muaf)"),
    ("FUNDA VAROL DEMİR", "Fen Bilimleri", ""),
    ("GÜL NARİN", "Özel Eğitim", "Özel Eğitim Öğretmeni (Nöbet Muaf)"),
    ("GÜLAY AYDIN SÖLPÜK", "İngilizce", ""),
    ("GÜLAY YILMAZ", "Türkçe", ""),
    ("HİLAL CENGİZ", "Okul Öncesi", "Okul Öncesi Öğretmeni (Nöbet Muaf)"),
    ("İLKNUR TEKİN SEZGİN", "Rehberlik", "Rehber Öğretmen (Nöbet Muaf)"),
    ("İLKNUR AKBAŞ UZUN", "Türkçe", "Belgede İ.AKBAŞ olarak geçmektedir"),
    ("LATİF CANDAN", "Sosyal Bilgiler", ""),
    ("MEHMET BEYDİLLİ", "Fen Bilimleri", ""),
    ("MEHMET ÖZBEK", "Beden Eğitimi", ""),
    ("MELTEM ÖZEL", "İngilizce", ""),
    ("MUNİSE İYİ", "İlköğretim Matematik", "Nöbet Listesi Dışı"),
    ("NALAN NARİN SÖNMEZ", "Teknoloji ve Tasarım", ""),
    ("NERMİN ZENGİN", "Okul Öncesi", "Okul Öncesi Öğretmeni (Nöbet Muaf)"),
    ("NEZAHAT SALMAN", "Beden Eğitimi", ""),
    ("ÖZNUR GÖKMEN ATASOY", "Türkçe", ""),
    ("SEHER AYDIN", "İlköğretim Matematik", ""),
    ("SILA ÖZGÜN AYDIN", "Türkçe", ""),
    ("ŞENCAN YEŞİL", "Görsel Sanatlar", ""),
    ("VEYSİ ALTUN", "İlköğretim Matematik", ""),
    ("VİLDAN SATAN ERSOY", "Türkçe", ""),
    ("YASEMİN GÖKOĞLU", "İngilizce", ""),
    ("YASEMİN SAKA KILIÇ", "İlköğretim Matematik", ""),
    ("ZEHRA ARAS", "Din Kültürü ve Ahlâk Bilgisi", ""),
    ("ZEYNEP AKKOYUN", "Okul Öncesi", "Okul Öncesi Öğretmeni (Nöbet Muaf)")
]

REFERENCE_TEACHERS = [
    {
        "name": name,
        "branch": branch,
        "is_active": (name in DUTY_TEACHERS_SET),
        "notes": notes
    }
    for name, branch, notes in RAW_TEACHERS_DATA
]

# PDF'teki kısaltmalar ile gerçek öğretmen isimleri arasındaki olası eşleşme tablosu
NAME_ALIASES = {
    "M.BEYDİLLİ": "MEHMET BEYDİLLİ",
    "İ.AKBAŞ": "İLKNUR AKBAŞ UZUN",
    "M.ÖZEL": "MELTEM ÖZEL",
    "A.KIRLIOĞLU": "ADNAN KIRLIOĞLU",
    "A.ÇATAK": "ANIL ÇATAK",
    "Ö.GÖKMEN ATASOY": "ÖZNUR GÖKMEN ATASOY",
    "A.EREN": "AYŞE EREN",
    "D.YILDIZ SAVAŞ": "DERYA YILDIZ SAVAŞ",
    "M.ÖZBEK": "MEHMET ÖZBEK",
    "F.ÇETİN": "FATMA ÇETİN",
    "N.NARİN SÖNMEZ": "NALAN NARİN SÖNMEZ",
    "Ç.YALÇINKAYA": "ÇİĞDEM YALÇINKAYA",
    "B.ÇAKIN": "BELGİN ÇAKIN",
    "G.YILMAZ": "GÜLAY YILMAZ",
    "L.CANDAN": "LATİF CANDAN",
    "A.ŞENOL ÇALIK": "AHU ŞENOL ÇALIK",
    "V.ALTUN": "VEYSİ ALTUN",
    "Y.GÖKOĞLU": "YASEMİN GÖKOĞLU",
    "G.AYDIN SÖLPÜK": "GÜLAY AYDIN SÖLPÜK",
    "A.KAYA": "AYŞEGÜL KAYA",
    "F.VAROL DEMİR": "FUNDA VAROL DEMİR",
    "N.SALMAN": "NEZAHAT SALMAN",
    "V.SATANERSOY": "VİLDAN SATAN ERSOY",
    "S.AYDIN (SILA)": "SILA ÖZGÜN AYDIN",
    "A.KARAKÜLAH": "ARZU KARAKÜLAH",
    "A.AŞUTKALIOĞLU": "ASLI ÖRGÜN AŞUTKALIOĞLU",
    "S.AYDIN (SEHER)": "SEHER AYDIN",
    "Ş.YEŞİL": "ŞENCAN YEŞİL",
    "Z.ARAS": "ZEHRA ARAS",
    "Y.SAKA KILIÇ": "YASEMİN SAKA KILIÇ"
}
