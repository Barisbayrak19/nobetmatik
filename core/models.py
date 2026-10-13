"""
Domain Veri Modelleri
ID tabanlı, tip güvenli dataclass yapıları.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import uuid
import datetime

def generate_id() -> str:
    return str(uuid.uuid4())

@dataclass
class SchoolInfo:
    id: str = field(default_factory=generate_id)
    name: str = ""
    city: str = ""
    district: str = ""
    academic_year: str = "2026-2027"
    principal_name: str = ""
    school_level: str = "Ortaokul"
    education_type: str = "Normal (Tekli)"
    daily_periods: int = 7
    duty_rules: str = (
        "1- Günlük vakit çizelgesini uygulamak.\n"
        "2- Öğretmenlerin derslere zamanında girip girmediğini izlemek ve öğretmeni gelmeyen sınıfları okul yönetimine bildirmek ve bu sınıflara nezaret etmek.\n"
        "3- Isıtma elektrik ve sıhhı tesislerin çalışıp çalışmadığını okul içi temizliğin yapılıp yapılmadığının okul bina ve tesislerinin yangından koruma önlemlerinin alınıp alınmadığının günlük kontrollerini yapmak giderilebildiği eksikleri gidermek gerekli olanları ilgililere duyurmak.\n"
        "4- Bahçedeki, koridorlardaki ve sınıflardaki öğrencileri gözetlemek.\n"
        "5- Beklenmedik olaylar karşısında gerekli tedbirleri almak ve bu durumu ilgililere bildirmek.\n"
        "6- Nöbet süresince okulun eğitim öğretim disiplin gibi çeşitli işlerini izlemek bu hususlarda günlük tedbirleri almak.\n"
        "7- Nöbet sonunda okul nöbet defterine nöbet süresi içerisinde önemli olayları ve aldığı tedbirleri belirten raporu yazmak."
    )
    installed: bool = False

@dataclass
class Teacher:
    id: str = field(default_factory=generate_id)
    name: str = ""
    branch: str = ""
    phone: str = ""
    shift_group: str = "Tümü"  # 'Tümü', 'Sabahçı', 'Öğlenci'
    is_active: bool = True
    unavailable_days: List[str] = field(default_factory=list)
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    # Gelişmiş Mevzuat, Muafiyet ve Tercih Alanları
    is_exempt: bool = False                    # Kesin mevzuat/sağlık muafiyeti
    exemption_reason: str = ""                 # 'İdareci', 'YEĞİTEK Okul Sorumlusu', 'Hamilelik / Süt İzni', 'Engellilik', 'Engelli Yakını', 'Yönetici İzni', 'Diğer'
    seniority_years: int = 0                   # Hizmet yılı (20/25 yıl kuralı)
    exemption_requested: bool = False          # 20/25 yıl veya istekli muafiyet talebi
    preferred_days: List[str] = field(default_factory=list)   # Tercih edilen günler (+puan)
    avoided_days: List[str] = field(default_factory=list)     # Tercih edilmeyen günler (-puan)
    is_primary_school: bool = True             # Kadrosunun bulunduğu okul mu?

@dataclass
class Location:
    id: str = field(default_factory=generate_id)
    name: str = ""
    order_num: int = 0
    capacity: int = 1
    shift_group: str = "Tümü"  # 'Tümü', 'Sabahçı', 'Öğlenci'
    is_active: bool = True

@dataclass
class Day:
    id: str = field(default_factory=generate_id)
    name: str = ""
    order_num: int = 0
    is_active: bool = True

@dataclass
class Assignment:
    id: str = field(default_factory=generate_id)
    week_start: str = "2026-09-28"  # Hafta başlangıç tarihi YYYY-MM-DD
    day_id: str = ""
    location_id: str = ""
    slot_index: int = 0  # 0 veya 1 (kapasitesi 2 olan yerler için)
    teacher_id: Optional[str] = None
    fixed: bool = False
    notes: str = ""

@dataclass
class DragState:
    source_assignment_id: str
    source_teacher_id: str
    source_day_id: str = ""
    source_location_id: str = ""
    source_slot_index: int = 0
    target_assignment_id: Optional[str] = None
    target_day_id: Optional[str] = None
    target_location_id: Optional[str] = None
    target_slot_index: int = 0

@dataclass
class DutyFairnessReport:
    teacher_counts: Dict[str, int] = field(default_factory=dict)
    teacher_names: Dict[str, str] = field(default_factory=dict)
    average_duties: float = 0.0
    min_duties: int = 0
    max_duties: int = 0
    fairness_score: float = 100.0
    warnings: List[str] = field(default_factory=list)
    excluded_teachers: Dict[str, str] = field(default_factory=dict)      # teacher_name -> elenme gerekçesi
    assignment_reasons: Dict[str, List[str]] = field(default_factory=dict) # assignment key -> gerekçe maddeleri
    unfilled_slots: List[Dict[str, Any]] = field(default_factory=list)   # doldurulamayan slotlar ve nedenleri
    stats: Dict[str, Any] = field(default_factory=dict)                  # özet istatistikler
    co_duty_proposals: List[Dict[str, Any]] = field(default_factory=list) # Boşta kalan öğretmenler için eşli/destek nöbet teklifleri
    co_duty_assignments: List[Assignment] = field(default_factory=list) # Atanan eşli nöbet nesneleri
    gini_index: float = 0.0                                              # Gini eşitlik katsayısı (0.0 = Tam eşitlik)
    fairness_details: Dict[str, Any] = field(default_factory=dict)       # Ayrıntılı adalet karnesi metrikleri

@dataclass
class TeacherLesson:
    id: str = field(default_factory=generate_id)
    teacher_id: str = ""
    day_name: str = ""
    period: int = 1
    class_name: str = ""
    subject_code: str = ""
    is_free: bool = True

@dataclass
class SubstitutionAssignment:
    id: str = field(default_factory=generate_id)
    date_str: str = ""
    period: int = 1
    absent_teacher_id: str = ""
    class_name: str = ""
    subject_code: str = ""
    duty_teacher_id: Optional[str] = None
    notes: str = ""
    is_ek_ders: bool = False

@dataclass
class AttendanceRecord:
    id: str = field(default_factory=generate_id)
    date_str: str = ""                # YYYY-MM-DD
    teacher_id: str = ""
    teacher_name: str = ""
    branch: str = ""
    status: str = "Raporlu"           # 'Raporlu', 'İzinli', 'Sevkli', 'Görevli', 'Mazeretli'
    periods_missed: str = "Tüm Gün"   # 'Tüm Gün' veya '1, 2, 3 (3 Saat)'
    lessons_missed: str = ""          # '5-A (MAT), 6-B (MAT)' (Girilmeyen sınıf ve dersler)
    slip_path: str = ""               # Saklanan görevlendirme fişi dosya yolu (.html veya .pdf)
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

@dataclass
class SubstitutionFairnessReport:
    teacher_counts: Dict[str, int] = field(default_factory=dict)         # teacher_id -> assigned substitution hours today
    teacher_names: Dict[str, str] = field(default_factory=dict)
    average_hours: float = 0.0
    min_hours: int = 0
    max_hours: int = 0
    fairness_score: float = 100.0
    gini_index: float = 0.0
    total_lessons_needed: int = 0
    total_assigned_slots: int = 0
    unassigned_lessons: int = 0
    tandem_assignments: List[Dict[str, Any]] = field(default_factory=list) # Başkasının yanına atananlar
    proposals: List[Dict[str, Any]] = field(default_factory=list)          # Boşta kalanlar için eşli teklifler
    idle_teachers_today: List[Dict[str, Any]] = field(default_factory=list)# O gün okulda/nöbetçi olup 0 saat alanlar
    stats: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
