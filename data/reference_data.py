"""
Referans ve Demo Kurulum Verileri
Tüm okul, öğretmen ve nöbet verileri genel dağıtıma uygun jenerik/örnek (fictional) verilerdir.
Gerçek kişisel veri (KVKK) içermez.
"""
from typing import Dict, List, Any

REFERENCE_SCHOOL = {
    "name": "Örnek Ortaokulu",
    "city": "Ankara",
    "district": "Çankaya",
    "academic_year": "2026-2027",
    "principal_name": "Ahmet ÖZTÜRK",
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

REFERENCE_LOCATIONS = [
    {"name": "1. KAT", "order_num": 1, "capacity": 1},
    {"name": "2. KAT", "order_num": 2, "capacity": 1},
    {"name": "3. KAT", "order_num": 3, "capacity": 1},
    {"name": "BAHÇE 1", "order_num": 4, "capacity": 1},
    {"name": "BAHÇE 2", "order_num": 5, "capacity": 1},
    {"name": "ZEMİN KAT", "order_num": 6, "capacity": 1}
]

# Örnek Haftalık Nöbet Çizelgesi
REFERENCE_DUTY_TABLE = {
    "Pazartesi": {
        "1. KAT": ["MEHMET DEMİR"],
        "2. KAT": ["İLKAY DEMİRTAŞ"],
        "3. KAT": ["ARZU DEMİR"],
        "BAHÇE 1": ["ADNAN YILMAZ"],
        "BAHÇE 2": ["ANIL YILDIRIM"],
        "ZEMİN KAT": ["ASLI ŞAHİN"]
    },
    "Salı": {
        "1. KAT": ["AYŞE ÖZTÜRK"],
        "2. KAT": ["DERYA ASLAN"],
        "3. KAT": ["BURAK GÜNEŞ"],
        "BAHÇE 1": ["FATMA POLAT"],
        "BAHÇE 2": ["ÇİĞDEM KOÇ"],
        "ZEMİN KAT": ["AYŞEGÜL AYDIN"]
    },
    "Çarşamba": {
        "1. KAT": ["CAN ERDOĞAN"],
        "2. KAT": ["GAMZE YAVUZ"],
        "3. KAT": ["HASAN ÇETİN"],
        "BAHÇE 1": ["AHMET KAYA"],
        "BAHÇE 2": ["İBRAHİM DOĞAN"],
        "ZEMİN KAT": ["GÜLAY KURT"]
    },
    "Perşembe": {
        "1. KAT": ["HÜLYA KESKİN"],
        "2. KAT": ["MURAT AVCI"],
        "3. KAT": ["MUSTAFA AKSOY"],
        "BAHÇE 1": ["NERMİN ÇAKIR"],
        "BAHÇE 2": ["OĞUZ TAŞ"],
        "ZEMİN KAT": ["ÖMER BOZKURT"]
    },
    "Cuma": {
        "1. KAT": ["ÖZLEM ÖZKAN"],
        "2. KAT": ["PINAR KARA"],
        "3. KAT": ["RECEP YALÇIN"],
        "BAHÇE 1": ["SEDA GÜLER"],
        "BAHÇE 2": ["DENİZ YILDIZ"],
        "ZEMİN KAT": ["FERİT BULUT"]
    }
}

DUTY_TEACHERS_SET = {
    t_name
    for day_dict in REFERENCE_DUTY_TABLE.values()
    for loc_list in day_dict.values()
    for t_name in loc_list
}

# Jenerik Örnek Öğretmen Listesi (İsim, Branş, Not)
RAW_TEACHERS_DATA = [
    ("ADNAN YILMAZ", "Sosyal Bilgiler", ""),
    ("AHMET KAYA", "Fen Bilimleri", ""),
    ("ALİ ÇELİK", "Özel Eğitim", "Özel Eğitim Öğretmeni (Nöbet Muaf)"),
    ("ANIL YILDIRIM", "Fen Bilimleri", ""),
    ("ARZU DEMİR", "İlköğretim Matematik", ""),
    ("ASLI ŞAHİN", "İngilizce", ""),
    ("AYŞE ÖZTÜRK", "Sosyal Bilgiler", ""),
    ("AYŞEGÜL AYDIN", "Din Kültürü ve Ahlâk Bilgisi", ""),
    ("BURAK GÜNEŞ", "Beden Eğitimi", ""),
    ("CAN ERDOĞAN", "Müzik", ""),
    ("ÇİĞDEM KOÇ", "Din Kültürü ve Ahlâk Bilgisi", ""),
    ("DENİZ YILDIZ", "Türkçe", ""),
    ("DERYA ASLAN", "Türkçe", ""),
    ("ELİF TEKİN", "Bilişim Teknolojileri", "Müdür Yardımcısı (Nöbet Muaf)"),
    ("EMİNE ŞEN", "Okul Öncesi", "Okul Öncesi Öğretmeni (Nöbet Muaf)"),
    ("FATMA POLAT", "Fen Bilimleri", ""),
    ("FERİT BULUT", "İlköğretim Matematik", ""),
    ("GAMZE YAVUZ", "Türkçe", ""),
    ("GÜLAY KURT", "İngilizce", ""),
    ("HAKAN KILIÇ", "Rehberlik", "Rehber Öğretmen (Nöbet Muaf)"),
    ("HASAN ÇETİN", "İlköğretim Matematik", ""),
    ("HÜLYA KESKİN", "Türkçe", ""),
    ("İBRAHİM DOĞAN", "Görsel Sanatlar", ""),
    ("İLKAY DEMİRTAŞ", "Türkçe", ""),
    ("MEHMET DEMİR", "Fen Bilimleri", ""),
    ("MURAT AVCI", "Beden Eğitimi", ""),
    ("MUSTAFA AKSOY", "Teknoloji ve Tasarım", ""),
    ("NERMİN ÇAKIR", "Sosyal Bilgiler", ""),
    ("OĞUZ TAŞ", "İlköğretim Matematik", ""),
    ("ÖMER BOZKURT", "Din Kültürü ve Ahlâk Bilgisi", ""),
    ("ÖZLEM ÖZKAN", "İngilizce", ""),
    ("PINAR KARA", "Fen Bilimleri", ""),
    ("RECEP YALÇIN", "Sosyal Bilgiler", ""),
    ("SEDA GÜLER", "Türkçe", ""),
    ("SELİN SARIOĞLU", "İngilizce", "Nöbet Listesi Dışı"),
    ("SERKAN YILMAZ", "İlköğretim Matematik", "Nöbet Listesi Dışı"),
    ("SEVİM KAYA", "Türkçe", "Okul Öncesi Öğretmeni (Nöbet Muaf)"),
    ("SİNAN ŞİMŞEK", "Beden Eğitimi", "Nöbet Listesi Dışı"),
    ("TOLGA AKTAŞ", "Fen Bilimleri", "Nöbet Listesi Dışı"),
    ("TÜLAY ÖZDEMİR", "Müzik", "Nöbet Listesi Dışı"),
    ("UFUK CEYLAN", "Sosyal Bilgiler", "Nöbet Listesi Dışı"),
    ("VEDAT ÖZCAN", "İngilizce", "Nöbet Listesi Dışı"),
    ("YASEMİN TUNÇ", "İlköğretim Matematik", "Nöbet Listesi Dışı"),
    ("ZEYNEP ÇAĞLAR", "Din Kültürü ve Ahlâk Bilgisi", "Nöbet Listesi Dışı")
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

# Örnek Kısaltma Eşleştirme Tablosu
NAME_ALIASES = {
    "M.DEMİR": "MEHMET DEMİR",
    "A.YILMAZ": "ADNAN YILMAZ",
    "A.KAYA": "AHMET KAYA",
    "A.DEMİR": "ARZU DEMİR",
    "A.ŞAHİN": "ASLI ŞAHİN",
    "A.ÖZTÜRK": "AYŞE ÖZTÜRK",
    "A.AYDIN": "AYŞEGÜL AYDIN",
    "B.GÜNEŞ": "BURAK GÜNEŞ",
    "C.ERDOĞAN": "CAN ERDOĞAN",
    "Ç.KOÇ": "ÇİĞDEM KOÇ",
    "D.YILDIZ": "DENİZ YILDIZ",
    "D.ASLAN": "DERYA ASLAN",
    "E.TEKİN": "ELİF TEKİN",
    "F.POLAT": "FATMA POLAT",
    "F.BULUT": "FERİT BULUT",
    "G.YAVUZ": "GAMZE YAVUZ",
    "G.KURT": "GÜLAY KURT",
    "H.ÇETİN": "HASAN ÇETİN",
    "H.KESKİN": "HÜLYA KESKİN",
    "İ.DOĞAN": "İBRAHİM DOĞAN",
    "İ.DEMİRTAŞ": "İLKAY DEMİRTAŞ",
    "M.AVCI": "MURAT AVCI",
    "M.AKSOY": "MUSTAFA AKSOY",
    "N.ÇAKIR": "NERMİN ÇAKIR",
    "O.TAŞ": "OĞUZ TAŞ",
    "Ö.BOZKURT": "ÖMER BOZKURT",
    "Ö.ÖZKAN": "ÖZLEM ÖZKAN",
    "P.KARA": "PINAR KARA",
    "R.YALÇIN": "RECEP YALÇIN",
    "S.GÜLER": "SEDA GÜLER"
}
