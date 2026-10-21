"""
Boş Ders Doldurma ve Nöbetçi İkame Servisi (Substitution Service)
İzinli/raporlu öğretmenin derslerini tespit eder, nöbetçi öğretmenlerin boş dersleri ile
eşleştirir, iş yükünü adil dağıtır ve resmi görevlendirme fişi / çıktısı üretir.
"""
import os
import json
import datetime
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pymupdf

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from core.models import (
    Teacher, Location, Day, TeacherLesson, SubstitutionAssignment, SubstitutionFairnessReport
)
from core.database import Database
from core.logger import logger
from data.reference_data import NAME_ALIASES

PERIOD_TIMES = {
    1: "07:40 - 08:20",
    2: "08:30 - 09:10",
    3: "09:20 - 10:00",
    4: "10:10 - 10:50",
    5: "11:00 - 11:40",
    6: "11:50 - 12:30",
    7: "12:40 - 13:20"
}

_FONT_REGISTERED = False
def _register_pdf_fonts():
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return
    font_path = Path("C:/Windows/Fonts/arial.ttf")
    font_bold_path = Path("C:/Windows/Fonts/arialbd.ttf")
    if font_path.exists():
        try:
            pdfmetrics.registerFont(TTFont("CustomArial", str(font_path)))
            if font_bold_path.exists():
                pdfmetrics.registerFont(TTFont("CustomArial-Bold", str(font_bold_path)))
            else:
                pdfmetrics.registerFont(TTFont("CustomArial-Bold", str(font_path)))
            _FONT_REGISTERED = True
        except Exception as e:
            logger.warning(f"Arial font yüklenirken hata: {e}")


def is_same_branch(b1: str, b2: str) -> bool:
    """
    İki branşın eşleşip eşleşmediğini kontrol eder (Örn: İlköğretim Matematik == Matematik).
    """
    if not b1 or not b2:
        return False
    b1_norm = b1.lower().replace("öğretmenliği", "").replace("öğretmeni", "").strip()
    b2_norm = b2.lower().replace("öğretmenliği", "").replace("öğretmeni", "").strip()
    aliases = {
        "ilköğretim matematik": "matematik",
        "din kültürü ve ahlâk bilgisi": "din kültürü",
        "din kültürü ve ahlak bilgisi": "din kültürü",
        "fen bilimleri": "fen",
        "fen ve teknoloji": "fen",
        "türkçe": "türkçe",
        "ingilizce": "ingilizce",
        "sosyal bilgiler": "sosyal",
        "beden eğitimi": "beden",
        "görsel sanatlar": "resim",
        "müzik": "müzik",
        "teknoloji ve tasarım": "teknoloji tasarım",
        "bilişim teknolojileri": "bilişim"
    }
    b1_mapped = aliases.get(b1_norm, b1_norm)
    b2_mapped = aliases.get(b2_norm, b2_norm)
    return b1_mapped == b2_mapped or b1_mapped in b2_mapped or b2_mapped in b1_mapped


SUBJECT_TO_BRANCH = {
    "MATEMATİK": "İlköğretim Matematik",
    "FEN BİLİMLERİ": "Fen Bilimleri",
    "TÜRKÇE": "Türkçe",
    "SOSYAL BİLGİLER": "Sosyal Bilgiler",
    "YABANCI DİL": "İngilizce",
    "DİN KÜLTÜRÜ VE AHLAK BİLGİSİ": "Din Kültürü ve Ahlâk Bilgisi",
    "BEDEN EĞİTİMİ VE SPOR": "Beden Eğitimi",
    "GÖRSEL SANATLAR": "Görsel Sanatlar",
    "MÜZİK": "Müzik",
    "BİLİŞİM TEKNOLOJİLERİ VE YAZILIM": "Bilişim Teknolojileri",
    "TEKNOLOJİ VE TASARIM": "Teknoloji ve Tasarım",
    "T.C. İNKILAP TARİHİ VE ATATÜRKÇÜLÜK": "Sosyal Bilgiler",
    "REHBERLİK VE YÖNLENDİRME": "Rehberlik"
}

def clean_unicode_text(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFC", str(s))
    return " ".join(s.split()).strip()

def normalize_class_name(raw_class: str) -> str:
    cleaned = clean_unicode_text(raw_class)
    m = re.search(r'(\d+)\.\s*S[ıi]n[ıi]f\s*\/\s*([A-Za-zÇĞİÖŞÜçğıöşü])', cleaned, re.IGNORECASE)
    if m:
        return f"{m.group(1)}-{clean_unicode_text(m.group(2)).upper()}"
    m2 = re.search(r'Ana\s*S[ıi]n[ıi]f[ıi]\s*\/\s*([A-Za-zÇĞİÖŞÜçğıöşü])', cleaned, re.IGNORECASE)
    if m2:
        return f"Ana-{clean_unicode_text(m2.group(1)).upper()}"
    m3 = re.search(r'Özel\s*Eğitim[^\/]*\/\s*([A-Za-zÇĞİÖŞÜçğıöşü])', cleaned, re.IGNORECASE)
    if m3:
        return f"Özel-{clean_unicode_text(m3.group(1)).upper()}"
    return cleaned

def determine_teacher_branch(subjects_count: Dict[str, int]) -> str:
    if not subjects_count:
        return "Genel"
    sorted_s = sorted(subjects_count.items(), key=lambda x: x[1], reverse=True)
    for s, _ in sorted_s:
        for k, v in SUBJECT_TO_BRANCH.items():
            if k in s:
                return v
    top = sorted_s[0][0]
    if "SPOR" in top or "OYUN" in top: return "Beden Eğitimi"
    if "YAZARLIK" in top or "MASAL" in top: return "Türkçe"
    if "DİNİ" in top: return "Din Kültürü ve Ahlâk Bilgisi"
    if "İKLİM" in top or "ÇEVRE" in top or "BİLİM" in top: return "Fen Bilimleri"
    if "MATEMATİK" in top: return "İlköğretim Matematik"
    if "YABANCI" in top: return "İngilizce"
    if "AHLAK" in top or "KÜLTÜR" in top or "TARİH" in top: return "Sosyal Bilgiler"
    return "Branş Öğretmeni"


class SubstitutionService:
    def __init__(self, db: Database):
        self.db = db

    def get_period_times(self) -> Dict[int, str]:
        """Kayıtlı veya hesaplanmış ders saatlerini döndürür."""
        if hasattr(self.db, "get_period_times"):
            return self.db.get_period_times()
        return PERIOD_TIMES

    @staticmethod
    def parse_eokul_timetable_pdf(pdf_path: str) -> Dict[str, Any]:
        """
        e-Okul'dan alınan haftalık ders programı PDF çizelgesini ayrıştırır.
        Sınıfları, ders saatlerini, öğretmenleri ve girdikleri dersleri çıkarır.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF dosyası bulunamadı: {pdf_path}")

        doc = pymupdf.open(pdf_path)
        days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]

        teacher_schedules: Dict[str, Dict[str, Dict[int, Tuple[str, str]]]] = defaultdict(lambda: defaultdict(dict))
        teacher_subjects: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        classes_found = set()
        total_non_empty_cells = 0

        for page in doc:
            lines = [clean_unicode_text(l) for l in page.get_text("text").split("\n") if clean_unicode_text(l)]
            if len(lines) < 4:
                continue

            header_line = lines[3]
            class_raw = header_line.split("2026-2027")[0].strip() if "2026-2027" in header_line else header_line
            class_name = normalize_class_name(class_raw)
            classes_found.add(class_name)

            tabs = page.find_tables()
            if not tabs.tables:
                continue

            table = tabs.tables[0].extract()
            for row in table[1:]:
                try:
                    p_str = clean_unicode_text(row[0])
                    period_num = int(p_str)
                except Exception:
                    continue

                for col_idx in range(2, 7):
                    day_name = days[col_idx - 2]
                    cell = row[col_idx]
                    if not cell or not clean_unicode_text(cell):
                        continue

                    c_lines = [clean_unicode_text(l) for l in cell.strip().split("\n") if clean_unicode_text(l)]
                    if not c_lines:
                        continue

                    # Seçmeli Ders ve Normal Ders format ayrımı
                    if "SEÇMELİ" in c_lines[0].upper() and len(c_lines) > 1 and "-" in c_lines[1]:
                        parts = c_lines[1].split("-", 1)
                        t_name = clean_unicode_text(parts[0])
                        s_name = clean_unicode_text(parts[1])
                        if len(c_lines) > 2:
                            s_name += " " + " ".join(c_lines[2:])
                    elif "-" in c_lines[0]:
                        parts = c_lines[0].split("-", 1)
                        t_name = clean_unicode_text(parts[0])
                        s_name = clean_unicode_text(parts[1])
                        if len(c_lines) > 1:
                            s_name += " " + " ".join(c_lines[1:])
                    else:
                        t_name = clean_unicode_text(c_lines[-1])
                        s_name = clean_unicode_text(" ".join(c_lines[:-1]))

                    t_name = t_name.upper()
                    s_name = s_name.upper()

                    # Aliases kontrolü (Örn: İLKNUR AKBAŞ UZUN <-> İLKNUR UZUN)
                    t_name = NAME_ALIASES.get(t_name, t_name)

                    teacher_schedules[t_name][day_name][period_num] = (class_name, s_name)
                    teacher_subjects[t_name][s_name] += 1
                    total_non_empty_cells += 1

        teacher_info: Dict[str, Dict[str, Any]] = {}
        for t_name, schedule_dict in teacher_schedules.items():
            branch = determine_teacher_branch(teacher_subjects[t_name])
            total_lessons = sum(len(p) for p in schedule_dict.values())
            teacher_info[t_name] = {
                "branch": branch,
                "schedule": schedule_dict,
                "total_lessons": total_lessons,
                "subjects": dict(teacher_subjects[t_name])
            }

        return {
            "teachers": teacher_info,
            "classes": sorted(list(classes_found)),
            "total_lessons": total_non_empty_cells
        }

    def import_timetables_from_pdf(
        self,
        pdf_path: str,
        auto_create_missing_teachers: bool = True,
        clear_existing: bool = True
    ) -> Dict[str, int]:
        """
        e-Okul PDF'inden haftalık ders programlarını ve öğretmenleri veritabanına aktarır.
        """
        parsed = self.parse_eokul_timetable_pdf(pdf_path)
        teachers_data = parsed["teachers"]
        days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]

        existing_teachers = self.db.get_teachers()
        teacher_by_name = {t.name.upper(): t for t in existing_teachers}

        new_teachers_count = 0
        if auto_create_missing_teachers:
            for t_name, t_info in teachers_data.items():
                if t_name not in teacher_by_name:
                    # Kısmi eşleşme var mı kontrol et
                    matched = None
                    for ex_t in existing_teachers:
                        if ex_t.name.upper() in t_name or t_name in ex_t.name.upper():
                            matched = ex_t
                            break
                    if matched:
                        teacher_by_name[t_name] = matched
                    else:
                        new_t = Teacher(
                            name=t_name,
                            branch=t_info["branch"],
                            is_active=True,
                            notes="e-Okul PDF İçe Aktarım"
                        )
                        self.db.save_teacher(new_t)
                        teacher_by_name[t_name] = new_t
                        existing_teachers.append(new_t)
                        new_teachers_count += 1

        if clear_existing:
            self.db.clear_teacher_lessons()

        lessons_to_save: List[TeacherLesson] = []
        for t_name, t_info in teachers_data.items():
            teacher = teacher_by_name.get(t_name)
            if not teacher:
                # Kısmi eşleşme kontrol et
                for ex_t in existing_teachers:
                    if ex_t.name.upper() in t_name or t_name in ex_t.name.upper():
                        teacher = ex_t
                        break
            if not teacher:
                continue

            sched = t_info["schedule"]
            # 5 gün x 7 saat = 35 saatlik tam çizelgeyi oluştur
            for day_name in days:
                day_lessons = sched.get(day_name, {})
                for p_num in range(1, 8):
                    if p_num in day_lessons:
                        c_name, s_name = day_lessons[p_num]
                        l = TeacherLesson(
                            teacher_id=teacher.id,
                            day_name=day_name,
                            period=p_num,
                            class_name=c_name,
                            subject_code=s_name,
                            is_free=False
                        )
                    else:
                        l = TeacherLesson(
                            teacher_id=teacher.id,
                            day_name=day_name,
                            period=p_num,
                            class_name="",
                            subject_code="",
                            is_free=True
                        )
                    lessons_to_save.append(l)

        if lessons_to_save:
            self.db.save_teacher_lessons_batch(lessons_to_save)

        logger.info(f"e-Okul PDF'ten {len(lessons_to_save)} adet ders programı kaydı aktarıldı. Yeni öğretmen: {new_teachers_count}")
        return {
            "teachers_count": len(teachers_data),
            "lessons_count": len(lessons_to_save),
            "new_teachers_count": new_teachers_count,
            "classes_count": len(parsed["classes"])
        }


    def import_timetables_from_json(self, json_path: Optional[str] = None) -> int:
        """
        JSON dosyasındaki ders programlarını veritabanına aktarır.
        """
        if not json_path:
            json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "timetables.json")

        if not os.path.exists(json_path):
            logger.warning(f"Ders programı dosyası bulunamadı: {json_path}")
            return 0

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        teachers = self.db.get_teachers()
        teacher_by_name = {t.name.upper(): t for t in teachers}

        lessons_to_save: List[TeacherLesson] = []
        for teacher_raw_name, days_data in data.items():
            canonical_name = NAME_ALIASES.get(teacher_raw_name, teacher_raw_name).upper()
            teacher = teacher_by_name.get(canonical_name)
            if not teacher:
                # Kısmi eşleşme dene
                for t in teachers:
                    if t.name.upper() in canonical_name or canonical_name in t.name.upper():
                        teacher = t
                        break

            if not teacher:
                continue

            for day_name, periods_data in days_data.items():
                for period_str, info in periods_data.items():
                    try:
                        p_num = int(period_str)
                    except ValueError:
                        continue

                    lesson = TeacherLesson(
                        teacher_id=teacher.id,
                        day_name=day_name,
                        period=p_num,
                        class_name=info.get("class", ""),
                        subject_code=info.get("subject", ""),
                        is_free=bool(info.get("is_free", True))
                    )
                    lessons_to_save.append(lesson)

        if lessons_to_save:
            self.db.save_teacher_lessons_batch(lessons_to_save)
        saved_count = len(lessons_to_save)

        logger.info(f"{saved_count} adet ders programı kaydı veritabanına aktarıldı.")
        return saved_count

    def get_teacher_free_periods(self, teacher_id: str, day_name: str, is_duty: bool = True) -> List[int]:
        """
        Bir öğretmenin belirli bir gündeki boş ders saatlerini (1..7) döner.
        - Eğer öğretmen o gün NÖBETÇİ ise (is_duty=True): Okulda tam gün nöbetçi olduğundan dolu dersi
          olmayan tüm saatler (1..7) boş kabul edilir.
        - Eğer öğretmen o gün NÖBETÇİ DEĞİL ise (is_duty=False): Öğretmenin o günkü İLK DERSİNDEN ÖNCE
          ve SON DERSİNDEN SONRA öğretmen okulda kabul edilmez.
          Yalnızca ilk ve son dersi arasındaki boşluk (pencere) saatleri 'okulda boş' sayılır.
          Eğer öğretmenin o gün hiç dersi yoksa (boş gün), o gün hiçbir saatte okulda kabul edilmez.
        """
        lessons = self.db.get_teacher_lessons(teacher_id, day_name)
        busy_periods = sorted([l.period for l in lessons if not l.is_free])
        busy_set = set(busy_periods)

        if is_duty:
            return [p for p in range(1, 8) if p not in busy_set]

        if not busy_periods:
            return []

        first_p = busy_periods[0]
        last_p = busy_periods[-1]
        return [p for p in range(first_p, last_p + 1) if p not in busy_set]

    def _ensure_week_start(self, date_or_week: str) -> str:
        """Herhangi bir tarih veya hafta başlangıç dizesini o haftanın Pazartesi gününün ISO tarihine çevirir."""
        try:
            dt = datetime.date.fromisoformat(date_or_week)
            monday = dt - datetime.timedelta(days=dt.weekday())
            return monday.isoformat()
        except Exception:
            return date_or_week

    def get_teacher_schedule(self, teacher_id: str, day_name: str) -> List[TeacherLesson]:
        """
        Bir öğretmenin belirli bir gündeki 7 saatlik ders programını döner.
        """
        return self.db.get_teacher_lessons(teacher_id, day_name)

    def get_day_duty_teachers(self, week_start: str, day_name: str) -> List[Dict[str, Any]]:
        """
        Haftanın belirli bir gününde nöbetçi olan öğretmenleri ve nöbet yerlerini döner.
        Tarih veya hafta başlangıcı ne verilirse verilsin otomatik olarak o haftanın Pazartesi gününe eşler.
        """
        days = self.db.get_days()
        target_day = next((d for d in days if d.name.lower() == day_name.lower()), None)
        if not target_day:
            return []

        resolved_week = self._ensure_week_start(week_start)
        assignments = self.db.get_assignments_for_week(resolved_week)
        day_assignments = [a for a in assignments if a.day_id == target_day.id and a.teacher_id]

        teachers = {t.id: t for t in self.db.get_teachers()}
        locations = {loc.id: loc for loc in self.db.get_locations()}

        results = []
        for a in day_assignments:
            teacher = teachers.get(a.teacher_id)
            location = locations.get(a.location_id)
            if teacher:
                free_periods = self.get_teacher_free_periods(teacher.id, day_name)
                results.append({
                    "teacher": teacher,
                    "location": location,
                    "free_periods": free_periods,
                    "assignment": a
                })
        return results

    def find_candidates_for_period(
        self,
        week_start: str,
        day_name: str,
        period: int,
        absent_teacher_id: str,
        absent_teacher_branch: str = "",
        date_str: Optional[str] = None,
        exclude_teacher_ids: Optional[List[str]] = None,
        active_substitutions: Optional[List[SubstitutionAssignment]] = None
    ) -> List[Dict[str, Any]]:
        """
        Belirli bir ders saati için görevlendirilebilecek nöbetçi öğretmenleri listeler.
        Birden fazla gelmeyen öğretmen durumunda:
        1. Kendisi de bugün gelmeyen/izinli olan nöbetçileri tespit eder ve havuzdan çıkarır.
        2. Aynı ders saatinde başka bir sınıfa atanmış nöbetçileri 'Çakışma Var' olarak işaretler.
        """
        duty_info_list = self.get_day_duty_teachers(week_start, day_name)
        candidates = []

        # Tüm gelmeyen öğretmenleri topla (kendisi gelmeyen nöbetçiler ikame yapamaz)
        all_absent_ids = set()
        if absent_teacher_id:
            all_absent_ids.add(absent_teacher_id)
        if exclude_teacher_ids:
            all_absent_ids.update(exclude_teacher_ids)
        if date_str:
            for s in self.db.get_substitutions_for_date(date_str):
                all_absent_ids.add(s.absent_teacher_id)
            for r in self.db.get_attendance_records(date_str=date_str):
                all_absent_ids.add(r.teacher_id)
        if active_substitutions:
            for s in active_substitutions:
                all_absent_ids.add(s.absent_teacher_id)

        # Bu ders saatinde başka bir sınıfa atanmış olan nöbetçileri haritala
        assigned_elsewhere: Dict[str, str] = {}
        if active_substitutions:
            for s in active_substitutions:
                if s.period == period and s.duty_teacher_id and s.absent_teacher_id != absent_teacher_id:
                    assigned_elsewhere[s.duty_teacher_id] = f"{s.class_name} ({s.subject_code})"
        if date_str:
            for s in self.db.get_substitutions_for_date(date_str):
                if s.period == period and s.duty_teacher_id and s.absent_teacher_id != absent_teacher_id:
                    if s.duty_teacher_id not in assigned_elsewhere:
                        assigned_elsewhere[s.duty_teacher_id] = f"{s.class_name} ({s.subject_code})"

        if not absent_teacher_branch and absent_teacher_id:
            t_obj = next((t for t in self.db.get_teachers() if t.id == absent_teacher_id), None)
            if t_obj:
                absent_teacher_branch = t_obj.branch

        duty_teacher_ids = set()
        for item in duty_info_list:
            teacher = item["teacher"]
            duty_teacher_ids.add(teacher.id)
            if teacher.id == absent_teacher_id:
                continue

            is_self_absent = teacher.id in all_absent_ids
            has_period_conflict = teacher.id in assigned_elsewhere

            lessons = self.get_teacher_schedule(teacher.id, day_name)
            lesson_at_period = next((l for l in lessons if l.period == period), None)
            timetable_free = lesson_at_period.is_free if lesson_at_period is not None else True

            if is_self_absent:
                is_free = False
                lesson_desc = "⛔ [BUGÜN GELMEDİ (İzinli/Raporlu)]"
            elif has_period_conflict:
                is_free = False
                lesson_desc = f"⚠️ [Başka Derse Atandı: {assigned_elsewhere[teacher.id]}]"
            elif not timetable_free:
                is_free = False
                lesson_desc = f"Dolu: {lesson_at_period.class_name} ({lesson_at_period.subject_code})"
            else:
                is_free = True
                loc_name = item["location"].name if item["location"] else "Nöbetçi"
                lesson_desc = f"BOŞ (Nöbetçi - {loc_name})"

            is_branch_match = is_same_branch(teacher.branch, absent_teacher_branch) if absent_teacher_branch else False

            candidates.append({
                "teacher": teacher,
                "location": item["location"],
                "is_duty": True,
                "is_free": is_free,
                "is_branch_match": is_branch_match,
                "lesson_desc": lesson_desc,
                "free_periods": item["free_periods"],
                "is_absent": is_self_absent,
                "has_conflict": has_period_conflict
            })

        # Nöbetçi olmayan öğretmenlerden SADECE gelmeyen öğretmenle aynı branşta olanlar eklenir (ek ders teklifi için).
        # MEB mevzuatına göre farklı branştan nöbetçi olmayan öğretmen zorunlu derse sokulamaz.
        all_teachers = self.db.get_teachers(active_only=True)
        other_teachers = [
            t for t in all_teachers
            if t.id not in duty_teacher_ids and t.id != absent_teacher_id
            and (is_same_branch(t.branch, absent_teacher_branch) if absent_teacher_branch else False)
        ]

        for teacher in other_teachers:
            is_self_absent = teacher.id in all_absent_ids
            has_period_conflict = teacher.id in assigned_elsewhere

            lessons = self.get_teacher_schedule(teacher.id, day_name)
            busy_periods = sorted([l.period for l in lessons if not l.is_free])
            free_periods = self.get_teacher_free_periods(teacher.id, day_name, is_duty=False)

            if is_self_absent:
                is_free = False
                lesson_desc = "⛔ [BUGÜN GELMEDİ (İzinli/Raporlu)]"
            elif has_period_conflict:
                is_free = False
                lesson_desc = f"⚠️ [Başka Derse Atandı: {assigned_elsewhere[teacher.id]}]"
            elif not busy_periods:
                is_free = False
                lesson_desc = "⚪ [Bugün Okulda Dersi Yok (Okulda Değil)]"
            elif period < busy_periods[0]:
                is_free = False
                lesson_desc = f"⚪ [Dersi {busy_periods[0]}. Saatte Başlıyor (Henüz Gelmedi)]"
            elif period > busy_periods[-1]:
                is_free = False
                lesson_desc = f"⚪ [Dersi {busy_periods[-1]}. Saatte Bitti (Okuldan Ayrıldı)]"
            elif period in busy_periods:
                lesson_at_period = next((l for l in lessons if l.period == period), None)
                c_name = lesson_at_period.class_name if lesson_at_period else ""
                s_name = lesson_at_period.subject_code if lesson_at_period else ""
                is_free = False
                lesson_desc = f"Dolu: {c_name} ({s_name})"
            else:
                is_free = True
                lesson_desc = "BOŞ (⭐ Kendi Branşı - Okulda/Pencere Saati)"

            is_branch_match = True

            candidates.append({
                "teacher": teacher,
                "location": None,
                "is_duty": False,
                "is_free": is_free,
                "is_branch_match": is_branch_match,
                "lesson_desc": lesson_desc,
                "free_periods": free_periods,
                "is_absent": is_self_absent,
                "has_conflict": has_period_conflict
            })

        # Öncelik Sıralaması:
        # 1. Gelmeyenler en altta (x["is_absent"])
        # 2. Boş ve Aynı Branş Nöbetçi (Ek ders - Tier 1a)
        # 3. Boş Nöbetçi (Tier 1b)
        # 4. Boş ve Aynı Branş Okul Öğretmeni (Ek ders teklifi - Tier 2)
        # 5. Dolu Nöbetçi (Tier 3)
        # 6. Dolu Okul Öğretmeni (Tier 4)
        def candidate_sort_rank(x):
            if x["is_absent"]:
                return 99
            is_duty = x.get("is_duty", True)
            is_free = x["is_free"]
            is_match = x["is_branch_match"]

            if is_duty and is_free and is_match:
                return 1
            elif is_duty and is_free:
                return 2
            elif not is_duty and is_free and is_match:
                return 3
            elif is_duty and not is_free:
                return 4
            else:
                return 5

        candidates.sort(key=lambda x: (candidate_sort_rank(x), x["teacher"].name))
        return candidates

    def auto_assign_substitutions(
        self,
        date_str: str,
        day_name: str,
        absent_teacher_id: str,
        week_start: str,
        teachers_per_lesson: int = 1,
        exclude_teacher_ids: Optional[List[str]] = None,
        active_substitutions: Optional[List[SubstitutionAssignment]] = None,
        allow_branch_peers_ek_ders: bool = True,
        assign_tandem_for_unassigned: bool = False
    ) -> List[SubstitutionAssignment]:
        """
        Gelmeyen öğretmenin dolu derslerini boş nöbetçiler ve okuldaki boş branşdaş öğretmenlerle eşleştirir:
        1. Katman 1 (Boş Nöbetçiler): O gün nöbetçi olup o saatte boş olan öğretmenler (varsa aynı branş öncelikli).
        2. Katman 2 (Ek Ders Fırsatı): Nöbetçiler o saatte doluysa ve izin verildiyse, SADECE okulda o an boş olan AYNI BRANŞTAKİ öğretmenler ek ders karşılığı atanır.
        3. Katman 3 (Kat Nöbetçisi): Başka branştan nöbetçi olmayan öğretmen derse sokulamaz; nöbetçi kat sorumlusu gözetmen atanır.
        """
        resolved_week = self._ensure_week_start(date_str if date_str else week_start)
        absent_teacher = next((t for t in self.db.get_teachers() if t.id == absent_teacher_id), None)
        absent_branch = absent_teacher.branch if absent_teacher else ""

        absent_lessons = self.get_teacher_schedule(absent_teacher_id, day_name)
        busy_lessons = [l for l in absent_lessons if not l.is_free]
        if not busy_lessons:
            return []

        # Bugün gelmeyen TÜM öğretmenleri belirle
        all_absent_ids = {absent_teacher_id}
        if exclude_teacher_ids:
            all_absent_ids.update(exclude_teacher_ids)
        if active_substitutions:
            all_absent_ids.update(s.absent_teacher_id for s in active_substitutions)
        for s in self.db.get_substitutions_for_date(date_str):
            all_absent_ids.add(s.absent_teacher_id)
        for r in self.db.get_attendance_records(date_str=date_str):
            all_absent_ids.add(r.teacher_id)

        duty_info_list = self.get_day_duty_teachers(resolved_week, day_name)
        # Nöbetçi havuzundan kendisi de gelmeyen öğretmenleri tamamen çıkar!
        duty_candidates = [d for d in duty_info_list if d["teacher"].id not in all_absent_ids]
        duty_teacher_ids = {d["teacher"].id for d in duty_info_list}

        # Okuldaki diğer aktif öğretmenler (nöbetçi olmayanlar ve gelmeyenler hariç)
        all_teachers = self.db.get_teachers(active_only=True)
        school_candidates = [
            t for t in all_teachers
            if t.id not in duty_teacher_ids and t.id not in all_absent_ids
        ]
        school_free_periods: Dict[str, List[int]] = {
            t.id: self.get_teacher_free_periods(t.id, day_name, is_duty=False)
            for t in school_candidates
        }

        # Diğer gelmeyen öğretmenler için o gün yapılan görevlendirmeleri topla (saat çakışması ve iş yükü için)
        duty_assigned_at_period: Dict[int, Set[str]] = defaultdict(set)
        teacher_assigned_today: Dict[str, int] = defaultdict(int)

        counted_sub_ids = set()
        if active_substitutions:
            for s in active_substitutions:
                if s.duty_teacher_id and s.absent_teacher_id != absent_teacher_id:
                    duty_assigned_at_period[s.period].add(s.duty_teacher_id)
                    teacher_assigned_today[s.duty_teacher_id] += 1
                    counted_sub_ids.add(s.id)

        for s in self.db.get_substitutions_for_date(date_str):
            if s.id not in counted_sub_ids and s.duty_teacher_id and s.absent_teacher_id != absent_teacher_id:
                duty_assigned_at_period[s.period].add(s.duty_teacher_id)
                teacher_assigned_today[s.duty_teacher_id] += 1

        # Her ders saati için uygun nöbetçi ve branşdaş okul öğretmenleri listesi
        period_duty_candidates: Dict[int, List[Teacher]] = {}
        period_same_branch_school: Dict[int, List[Teacher]] = {}
        for lesson in busy_lessons:
            p = lesson.period
            period_duty_candidates[p] = [
                d["teacher"] for d in duty_candidates
                if p in d["free_periods"] and d["teacher"].id not in duty_assigned_at_period[p]
            ]
            period_same_branch_school[p] = [
                t for t in school_candidates
                if p in school_free_periods.get(t.id, [])
                and t.id not in duty_assigned_at_period[p]
                and is_same_branch(t.branch, absent_branch)
            ]

        # MRV: En az alternatifi olan ders saatlerini önce planla
        sorted_lessons = sorted(
            busy_lessons,
            key=lambda l: (
                len(period_duty_candidates.get(l.period, [])) + len(period_same_branch_school.get(l.period, [])),
                l.period
            )
        )

        # Ders atamaları sözlüğü: period -> list of (Teacher, is_ek_ders, notes)
        period_assignments: Dict[int, List[Tuple[Teacher, bool, str]]] = {l.period: [] for l in busy_lessons}

        for lesson in sorted_lessons:
            p = lesson.period
            available_duty = period_duty_candidates.get(p, [])
            available_school = period_same_branch_school.get(p, [])

            for _ in range(teachers_per_lesson):
                already_assigned_here = {item[0].id for item in period_assignments[p]}

                # 1. Aşama: Boş Nöbetçi Öğretmen Ara (varsa aynı branş öncelikli)
                eligible_duty = [
                    t for t in available_duty
                    if t.id not in already_assigned_here and t.id not in duty_assigned_at_period[p]
                ]

                chosen = None
                assignment_tier = 1

                if eligible_duty:
                    def duty_fairness_key(t: Teacher):
                        t_info = next((d for d in duty_candidates if d["teacher"].id == t.id), None)
                        free_count = len(t_info["free_periods"]) if t_info else 0
                        same_b = 0 if is_same_branch(t.branch, absent_branch) else 1
                        return (same_b, teacher_assigned_today.get(t.id, 0), free_count, t.name)

                    eligible_duty.sort(key=duty_fairness_key)
                    chosen = eligible_duty[0]
                    assignment_tier = 1
                elif allow_branch_peers_ek_ders and available_school:
                    # 2. Aşama: Nöbetçiler o saatte doluysa, SADECE okulda o saatte boş olan kendi branşındaki öğretmene ek ders öner
                    eligible_school = [
                        t for t in available_school
                        if t.id not in already_assigned_here and t.id not in duty_assigned_at_period[p]
                    ]
                    if eligible_school:
                        def school_fairness_key(t: Teacher):
                            free_count = len(school_free_periods.get(t.id, []))
                            return (teacher_assigned_today.get(t.id, 0), free_count, t.name)

                        eligible_school.sort(key=school_fairness_key)
                        chosen = eligible_school[0]
                        assignment_tier = 2

                # 3. Aşama: Ne boş nöbetçi ne de kendi branşından boş öğretmen yoksa -> Kat Nöbetçisi gözetimi (farklı branştan nöbetçi olmayan derse sokulamaz)
                if not chosen:
                    fallback_duty = [
                        d["teacher"] for d in duty_candidates
                        if d["teacher"].id not in already_assigned_here and d["teacher"].id not in duty_assigned_at_period[p]
                    ]
                    if fallback_duty:
                        fallback_duty.sort(key=lambda t: (teacher_assigned_today.get(t.id, 0), t.name))
                        chosen = fallback_duty[0]
                        assignment_tier = 3

                if not chosen:
                    break

                if assignment_tier == 1:
                    is_ek = is_same_branch(chosen.branch, absent_branch)
                    note = "⭐ Ek Ders Yazılacak (Branş Nöbetçisi)" if is_ek else "Nöbet Görevi (İkame Doldurma)"
                elif assignment_tier == 2:
                    is_ek = True
                    note = "⭐ Ek Ders Teklifi (Branşdaş Öğretmen)"
                else: # tier 3
                    is_ek = False
                    note = "Kat Nöbetçisi Gözetiminde (Ders İçi/Koridor)"

                period_assignments[p].append((chosen, is_ek, note))
                duty_assigned_at_period[p].add(chosen.id)
                teacher_assigned_today[chosen.id] = teacher_assigned_today.get(chosen.id, 0) + 1

        # O gün henüz 0 görev almış nöbetçileri boş derslerine başkasının yanına eşli/ortak görevlendir
        if assign_tandem_for_unassigned:
            unassigned_duty = [
                d for d in duty_candidates
                if teacher_assigned_today.get(d["teacher"].id, 0) == 0
            ]
            for d_info in unassigned_duty:
                u_teach = d_info["teacher"]
                free_pers = d_info["free_periods"]
                for lesson in sorted(busy_lessons, key=lambda l: l.period):
                    p = lesson.period
                    if p in free_pers and u_teach.id not in duty_assigned_at_period[p]:
                        current_items = period_assignments.get(p, [])
                        if current_items and len(current_items) == 1 and current_items[0][0].id != u_teach.id:
                            prim_t = current_items[0][0]
                            is_ek = is_same_branch(u_teach.branch, absent_branch)
                            note = f"👥 Ortak/Eşli İkame: {prim_t.name} ile birlikte ({lesson.class_name})\n✓ Boş saatinde adil iş yükü paylaşımı"
                            period_assignments[p].append((u_teach, is_ek, note))
                            duty_assigned_at_period[p].add(u_teach.id)
                            teacher_assigned_today[u_teach.id] = teacher_assigned_today.get(u_teach.id, 0) + 1
                            break

        # Sonuç SubstitutionAssignment listesini oluştur
        results: List[SubstitutionAssignment] = []
        for lesson in sorted(busy_lessons, key=lambda l: l.period):
            assigned_items = period_assignments.get(lesson.period, [])
            if assigned_items:
                for t, is_ek_ders, note in assigned_items:
                    sub = SubstitutionAssignment(
                        date_str=date_str,
                        period=lesson.period,
                        absent_teacher_id=absent_teacher_id,
                        class_name=lesson.class_name,
                        subject_code=lesson.subject_code,
                        duty_teacher_id=t.id,
                        notes=note,
                        is_ek_ders=is_ek_ders
                    )
                    results.append(sub)
            else:
                sub = SubstitutionAssignment(
                    date_str=date_str,
                    period=lesson.period,
                    absent_teacher_id=absent_teacher_id,
                    class_name=lesson.class_name,
                    subject_code=lesson.subject_code,
                    duty_teacher_id=None,
                    notes="Uygun Boş Nöbetçi Yok",
                    is_ek_ders=False
                )
                results.append(sub)

        return results

    def auto_assign_multi_substitutions(
        self,
        date_str: str,
        day_name: str,
        absent_teacher_ids: List[str],
        week_start: str,
        teachers_per_lesson: int = 1,
        allow_branch_peers_ek_ders: bool = True,
        assign_tandem_for_unassigned: bool = False
    ) -> Dict[str, List[SubstitutionAssignment]]:
        """
        Birden fazla gelmeyen öğretmenin derslerini tek bir küresel adalet optimizasyonuyla dağıtır.
        - Tüm gelmeyen öğretmenleri nöbetçi havuzundan muaf tutar.
        - Hiçbir nöbetçiyi aynı saatte iki farklı sınıfa çakıştırmaz.
        - 1. Katman: O günün boş nöbetçileri (aynı branş öncelikli).
        - 2. Katman: Nöbetçiler o saatte doluysa, SADECE o saatte boş olan AYNI BRANŞTAKİ okul öğretmenleri ek ders teklifi olarak atanır.
        - 3. Katman: Kat nöbetçisi gözetimi (farklı branştan nöbetçi olmayan öğretmen derse sokulmaz).
        """
        resolved_week = self._ensure_week_start(date_str if date_str else week_start)
        teachers = {t.id: t for t in self.db.get_teachers()}
        all_absent_ids = set(absent_teacher_ids)
        # Attendance kayıtlarındaki diğer gelmeyenleri de ekle
        for r in self.db.get_attendance_records(date_str=date_str):
            all_absent_ids.add(r.teacher_id)

        duty_info_list = self.get_day_duty_teachers(resolved_week, day_name)
        # Nöbetçi havuzundan gelmeyen öğretmenleri tamamen ayıkla!
        duty_candidates = [d for d in duty_info_list if d["teacher"].id not in all_absent_ids]
        duty_teacher_ids = {d["teacher"].id for d in duty_info_list}

        # Okuldaki diğer aktif öğretmenler (nöbetçi olmayanlar ve gelmeyenler hariç)
        all_teachers = self.db.get_teachers(active_only=True)
        school_candidates = [
            t for t in all_teachers
            if t.id not in duty_teacher_ids and t.id not in all_absent_ids
        ]
        school_free_periods: Dict[str, List[int]] = {
            t.id: self.get_teacher_free_periods(t.id, day_name, is_duty=False)
            for t in school_candidates
        }

        teacher_assigned_today: Dict[str, int] = defaultdict(int)
        duty_assigned_at_period: Dict[int, Set[str]] = defaultdict(set)

        # Tüm gelmeyen öğretmenlerin dolu derslerini topla
        all_tasks: List[Dict[str, Any]] = []
        for a_id in absent_teacher_ids:
            a_teacher = teachers.get(a_id)
            if not a_teacher:
                continue
            lessons = self.get_teacher_schedule(a_id, day_name)
            busy_lessons = [l for l in lessons if not l.is_free]
            for l in busy_lessons:
                all_tasks.append({
                    "absent_id": a_id,
                    "absent_teacher": a_teacher,
                    "lesson": l,
                    "period": l.period
                })

        # Her ders saati için o saatte boş olan aday sayısını hesapla (MRV)
        for task in all_tasks:
            p = task["period"]
            a_teach = task["absent_teacher"]
            free_duty_count = sum(1 for d in duty_candidates if p in d["free_periods"])
            free_same_branch_school = sum(
                1 for t in school_candidates
                if p in school_free_periods.get(t.id, []) and is_same_branch(t.branch, a_teach.branch)
            ) if allow_branch_peers_ek_ders else 0
            task["free_count"] = free_duty_count + free_same_branch_school

        # Sıralama: En kısıtlı ders saatlerini ve branş eşleşmesi olanları önce ele al
        all_tasks.sort(key=lambda x: (x["free_count"], x["period"]))

        results_by_teacher: Dict[str, List[SubstitutionAssignment]] = {a_id: [] for a_id in absent_teacher_ids}

        for task in all_tasks:
            p = task["period"]
            a_teacher = task["absent_teacher"]
            lesson = task["lesson"]

            # Bu saatte boşta olan VE bu saatte başka bir göreve verilmemiş nöbetçiler
            eligible_duty = [
                d["teacher"] for d in duty_candidates
                if p in d["free_periods"] and d["teacher"].id not in duty_assigned_at_period[p]
            ]

            assigned_teachers: List[Tuple[Teacher, int]] = []

            # 1. Aşama: Boş Nöbetçilerden Ata (önce aynı branş nöbetçi)
            for _ in range(teachers_per_lesson):
                if not eligible_duty:
                    break

                def sort_key(t: Teacher):
                    t_info = next((d for d in duty_candidates if d["teacher"].id == t.id), None)
                    free_count = len(t_info["free_periods"]) if t_info else 0
                    same_b = 0 if is_same_branch(t.branch, a_teacher.branch) else 1
                    return (same_b, teacher_assigned_today.get(t.id, 0), free_count, t.name)

                eligible_duty.sort(key=sort_key)
                chosen = eligible_duty.pop(0)

                duty_assigned_at_period[p].add(chosen.id)
                teacher_assigned_today[chosen.id] = teacher_assigned_today.get(chosen.id, 0) + 1
                assigned_teachers.append((chosen, 1))

            # 2. Aşama: Nöbetçi yetersiz/yoksa ve izin verildiyse SADECE kendi branşındaki boş öğretmenlere ek ders öner
            if allow_branch_peers_ek_ders and len(assigned_teachers) < teachers_per_lesson:
                school_eligible = [
                    t for t in school_candidates
                    if p in school_free_periods.get(t.id, [])
                    and t.id not in duty_assigned_at_period[p]
                    and t.id not in [at[0].id for at in assigned_teachers]
                    and is_same_branch(t.branch, a_teacher.branch)
                ]
                while len(assigned_teachers) < teachers_per_lesson and school_eligible:
                    def school_sort_key(t: Teacher):
                        free_count = len(school_free_periods.get(t.id, []))
                        return (teacher_assigned_today.get(t.id, 0), free_count, t.name)

                    school_eligible.sort(key=school_sort_key)
                    chosen = school_eligible.pop(0)
                    duty_assigned_at_period[p].add(chosen.id)
                    teacher_assigned_today[chosen.id] = teacher_assigned_today.get(chosen.id, 0) + 1
                    assigned_teachers.append((chosen, 2))

            # 3. Aşama: Ekstrem durumda boşta nöbetçi ve branşdaş kalmadıysa, o günkü nöbetçilerden en az dersi olanı kat gözetmeni ata
            if len(assigned_teachers) < teachers_per_lesson:
                fallback_duty = [
                    d["teacher"] for d in duty_candidates
                    if d["teacher"].id not in duty_assigned_at_period[p]
                    and d["teacher"].id not in [at[0].id for at in assigned_teachers]
                ]
                while len(assigned_teachers) < teachers_per_lesson and fallback_duty:
                    fallback_duty.sort(key=lambda t: (teacher_assigned_today.get(t.id, 0), t.name))
                    chosen = fallback_duty.pop(0)
                    duty_assigned_at_period[p].add(chosen.id)
                    teacher_assigned_today[chosen.id] = teacher_assigned_today.get(chosen.id, 0) + 1
                    assigned_teachers.append((chosen, 3))

            if assigned_teachers:
                for t, tier in assigned_teachers:
                    if tier == 1:
                        is_ek = is_same_branch(t.branch, a_teacher.branch)
                        note = "⭐ Ek Ders Yazılacak (Branş Nöbetçisi)" if is_ek else "Nöbet Görevi (İkame Doldurma)"
                    elif tier == 2:
                        is_ek = True
                        note = "⭐ Ek Ders Teklifi (Branşdaş Öğretmen)"
                    else: # tier 3
                        is_ek = False
                        note = "🛡️ Kat Nöbetçisi Gözetiminde (Ders İçi/Koridor)"

                    sub = SubstitutionAssignment(
                        date_str=date_str,
                        period=lesson.period,
                        absent_teacher_id=a_teacher.id,
                        class_name=lesson.class_name,
                        subject_code=lesson.subject_code,
                        duty_teacher_id=t.id,
                        notes=note,
                        is_ek_ders=is_ek
                    )
                    results_by_teacher[a_teacher.id].append(sub)
            else:
                sub = SubstitutionAssignment(
                    date_str=date_str,
                    period=lesson.period,
                    absent_teacher_id=a_teacher.id,
                    class_name=lesson.class_name,
                    subject_code=lesson.subject_code,
                    duty_teacher_id=None,
                    notes="Uygun Boş Nöbetçi Yok",
                    is_ek_ders=False
                )
                results_by_teacher[a_teacher.id].append(sub)

        # 4. Aşama: O gün henüz 0 görev almış nöbetçileri boş derslerine başkasının yanına eşli/ortak görevlendir (Tandem)
        if assign_tandem_for_unassigned:
            unassigned_duty = [
                d for d in duty_candidates
                if teacher_assigned_today.get(d["teacher"].id, 0) == 0
            ]
            for d_info in unassigned_duty:
                u_teach = d_info["teacher"]
                free_pers = d_info["free_periods"]
                for a_id in absent_teacher_ids:
                    if teacher_assigned_today.get(u_teach.id, 0) > 0:
                        break
                    sub_list = results_by_teacher.get(a_id, [])
                    for p in free_pers:
                        if u_teach.id in duty_assigned_at_period[p]:
                            continue
                        current_p_subs = [s for s in sub_list if s.period == p and s.duty_teacher_id]
                        if len(current_p_subs) == 1 and current_p_subs[0].duty_teacher_id != u_teach.id:
                            prim_sub = current_p_subs[0]
                            prim_t = teachers.get(prim_sub.duty_teacher_id)
                            prim_name = prim_t.name if prim_t else "Nöbetçi Öğretmen"
                            a_teach_obj = teachers.get(a_id)
                            a_branch = a_teach_obj.branch if a_teach_obj else ""
                            is_ek = is_same_branch(u_teach.branch, a_branch)

                            tandem_sub = SubstitutionAssignment(
                                date_str=date_str,
                                period=p,
                                absent_teacher_id=a_id,
                                class_name=prim_sub.class_name,
                                subject_code=prim_sub.subject_code,
                                duty_teacher_id=u_teach.id,
                                notes=f"👥 Ortak/Eşli İkame: {prim_name} ile birlikte ({prim_sub.class_name})\n✓ Adil iş yükü dengelemesi (Boş Saat)",
                                is_ek_ders=is_ek
                            )
                            sub_list.append(tandem_sub)
                            duty_assigned_at_period[p].add(u_teach.id)
                            teacher_assigned_today[u_teach.id] = teacher_assigned_today.get(u_teach.id, 0) + 1
                            break

        return results_by_teacher

    def get_fairness_report(
        self,
        date_str: str,
        day_name: str,
        assignments: List[SubstitutionAssignment],
        week_start: str,
        absent_teacher_ids: Optional[List[str]] = None
    ) -> SubstitutionFairnessReport:
        """
        Günün ikame görevlendirmelerinin adalet, denge ve kural uyum karnesini hesaplar.
        Gini katsayısı, boşta kalan öğretmenler ve eşli teklifleri içerir.
        """
        resolved_week = self._ensure_week_start(date_str if date_str else week_start)
        teachers = {t.id: t for t in self.db.get_teachers()}
        all_absent_ids = set(absent_teacher_ids or [])
        for r in self.db.get_attendance_records(date_str=date_str):
            all_absent_ids.add(r.teacher_id)
        for s in assignments:
            if s.absent_teacher_id:
                all_absent_ids.add(s.absent_teacher_id)

        duty_info_list = self.get_day_duty_teachers(resolved_week, day_name)
        duty_candidates = [d for d in duty_info_list if d["teacher"].id not in all_absent_ids]

        teacher_counts: Dict[str, int] = {d["teacher"].id: 0 for d in duty_candidates}
        for s in assignments:
            if s.duty_teacher_id:
                teacher_counts[s.duty_teacher_id] = teacher_counts.get(s.duty_teacher_id, 0) + 1

        active_counts = list(teacher_counts.values()) if teacher_counts else [0]
        total_assigned_slots = sum(active_counts)

        # Gini Katsayısı Hesaplama (0.0 = Kusursuz Eşitlik)
        def _calc_gini(counts: List[int]) -> float:
            if not counts or len(counts) <= 1:
                return 0.0
            s = sorted(counts)
            n = len(s)
            tot = sum(s)
            if tot == 0:
                return 0.0
            gini_sum = sum((2 * i - n - 1) * c for i, c in enumerate(s, 1))
            return max(0.0, min(1.0, round(gini_sum / (n * tot), 4)))

        gini_val = _calc_gini(active_counts)
        min_h = min(active_counts) if active_counts else 0
        max_h = max(active_counts) if active_counts else 0
        spread = max_h - min_h
        avg_h = round(sum(active_counts) / len(active_counts), 2) if active_counts else 0.0

        # Adalet Skoru (100 üzerinden)
        fairness_score = max(0.0, min(100.0, round(100.0 - (gini_val * 100.0 * 0.75) - (spread * 5.0), 1)))

        # Tandem / Eşli İkame Atamaları
        lessons_grouped: Dict[Tuple[str, int], List[SubstitutionAssignment]] = defaultdict(list)
        for s in assignments:
            if s.duty_teacher_id:
                lessons_grouped[(s.absent_teacher_id, s.period)].append(s)

        tandem_assignments = []
        for (a_id, p), sub_items in lessons_grouped.items():
            if len(sub_items) > 1:
                t_names = [teachers[s.duty_teacher_id].name for s in sub_items if s.duty_teacher_id in teachers]
                tandem_assignments.append({
                    "period": p,
                    "class_name": sub_items[0].class_name,
                    "subject_code": sub_items[0].subject_code,
                    "absent_teacher_name": teachers[a_id].name if a_id in teachers else "",
                    "assigned_teachers": t_names,
                    "notes": sub_items[-1].notes
                })

        # O gün boşta kalan (0 görevli) nöbetçi öğretmenler
        idle_teachers_today = []
        for d in duty_candidates:
            t = d["teacher"]
            cnt = teacher_counts.get(t.id, 0)
            if cnt == 0:
                idle_teachers_today.append({
                    "teacher_id": t.id,
                    "teacher_name": t.name,
                    "branch": t.branch,
                    "location": d["location"].name if d["location"] else "Nöbetçi",
                    "free_periods": d["free_periods"],
                    "free_periods_str": ", ".join(map(str, d["free_periods"])) if d["free_periods"] else "Yok"
                })

        # Eşli İkame Teklifleri (Boşta kalanlar için başkasının yanına görevlendirme teklifi)
        proposals = []
        assigned_periods_taken: Dict[int, Set[str]] = defaultdict(set)
        for s in assignments:
            if s.duty_teacher_id:
                assigned_periods_taken[s.period].add(s.duty_teacher_id)

        for idle_info in idle_teachers_today:
            t_id = idle_info["teacher_id"]
            for s in assignments:
                p = s.period
                if p in idle_info["free_periods"] and s.duty_teacher_id and s.duty_teacher_id != t_id:
                    if t_id not in assigned_periods_taken[p]:
                        prim_t = teachers.get(s.duty_teacher_id)
                        prim_name = prim_t.name if prim_t else "Nöbetçi"
                        a_name = teachers[s.absent_teacher_id].name if s.absent_teacher_id in teachers else ""
                        proposals.append({
                            "absent_teacher_id": s.absent_teacher_id,
                            "absent_teacher_name": a_name,
                            "period": p,
                            "class_name": s.class_name,
                            "subject_code": s.subject_code,
                            "primary_teacher_id": s.duty_teacher_id,
                            "primary_teacher_name": prim_name,
                            "co_teacher_id": t_id,
                            "co_teacher_name": idle_info["teacher_name"],
                            "co_teacher_branch": idle_info["branch"],
                            "reason": f"{idle_info['teacher_name']} bugün nöbetçi olup henüz hiç ikame almamıştır. {p}. saatteki boş dersinde {s.class_name} sınıfında {prim_name} yanına eşli gözetmen olarak atanabilir."
                        })
                        break

        total_lessons_needed = len(set((s.absent_teacher_id, s.period) for s in assignments))
        unassigned_cnt = sum(1 for s in assignments if not s.duty_teacher_id)

        details = {
            "fairness_level": "🏆 A+ Mükemmel Eşitlik" if fairness_score >= 95 else ("A Çok Yüksek Adalet" if fairness_score >= 85 else "B Dengeli Dağılım"),
            "zero_duty_teachers": len(idle_teachers_today),
            "spread": spread,
            "average_hours": avg_h,
            "tandem_count": len(tandem_assignments),
            "proposals_count": len(proposals),
            "active_duty_teachers_count": len(duty_candidates)
        }

        stats = {
            "total_duty_teachers": len(duty_candidates),
            "assigned_teachers_count": sum(1 for c in active_counts if c > 0),
            "zero_assigned_count": len(idle_teachers_today),
            "total_slots": total_assigned_slots,
            "gini_index": gini_val,
            "fairness_score": fairness_score
        }

        return SubstitutionFairnessReport(
            teacher_counts=teacher_counts,
            teacher_names={t_id: teachers[t_id].name for t_id in teacher_counts if t_id in teachers},
            average_hours=avg_h,
            min_hours=min_h,
            max_hours=max_h,
            fairness_score=fairness_score,
            gini_index=gini_val,
            total_lessons_needed=total_lessons_needed,
            total_assigned_slots=total_assigned_slots,
            unassigned_lessons=unassigned_cnt,
            tandem_assignments=tandem_assignments,
            proposals=proposals,
            idle_teachers_today=idle_teachers_today,
            stats=stats,
            details=details
        )

    def export_substitution_pdf(
        self,
        output_path: str,
        date_str: str,
        day_name: str,
        absent_teacher: Teacher,
        assignments: List[SubstitutionAssignment]
    ) -> str:
        """
        Resmi Boş Ders Doldurma ve Nöbetçi Görevlendirme Fişini PDF olarak üretir.
        """
        _register_pdf_fonts()
        font_name = "CustomArial" if _FONT_REGISTERED else "Helvetica"
        font_bold = "CustomArial-Bold" if _FONT_REGISTERED else "Helvetica-Bold"

        school = self.db.get_school_info()
        teachers = {t.id: t for t in self.db.get_teachers()}
        locations = {loc.id: loc for loc in self.db.get_locations()}

        # Duty assignments for location mapping
        duty_day_teachers = self.get_day_duty_teachers(date_str, day_name)
        teacher_loc_map = {d["teacher"].id: (d["location"].name if d["location"] else "-") for d in duty_day_teachers}

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "TitleStyle",
            parent=styles["Normal"],
            fontName=font_bold,
            fontSize=12,
            leading=16,
            alignment=1,
            textColor=colors.HexColor("#0F172A")
        )
        subtitle_style = ParagraphStyle(
            "SubTitleStyle",
            parent=styles["Normal"],
            fontName=font_bold,
            fontSize=10,
            leading=14,
            alignment=1,
            textColor=colors.HexColor("#2563EB")
        )
        meta_style = ParagraphStyle(
            "MetaStyle",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=9,
            leading=13,
            alignment=0,
            textColor=colors.HexColor("#334155")
        )
        cell_style = ParagraphStyle(
            "CellStyle",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=8,
            leading=11,
            alignment=1
        )
        cell_bold = ParagraphStyle(
            "CellBold",
            parent=styles["Normal"],
            fontName=font_bold,
            fontSize=8,
            leading=11,
            alignment=1,
            textColor=colors.white
        )

        elements = []

        # Başlık Bloğu
        elements.append(Paragraph(f"T.C.<br/>{school.city.upper()} / {school.district.upper()}<br/>{school.name.upper()} MÜDÜRLÜĞÜ", title_style))
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("BOŞ DERS DOLDURMA / NÖBETÇİ ÖĞRETMEN GÖREVLENDİRME ÇİZELGESİ", subtitle_style))
        elements.append(Spacer(1, 14))

        # Bilgi Satırı
        today_date = datetime.date.today().strftime("%d.%m.%Y")
        meta_text = (
            f"<b>Tarih / Gün:</b> {date_str} ({day_name}) &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>İzinli/Raporlu Öğretmen:</b> {absent_teacher.name} ({absent_teacher.branch})<br/>"
            f"<b>Düzenleme Tarihi:</b> {today_date}"
        )
        elements.append(Paragraph(meta_text, meta_style))
        elements.append(Spacer(1, 12))

        # Tablo
        headers = ["Ders", "Saat Aralığı", "Sınıf", "Ders Adı", "Görevlendirilen Nöbetçi Öğretmen", "Nöbet Yeri", "Öğretmen İmzası"]
        table_data = [[Paragraph(h, cell_bold) for h in headers]]

        # Ders saatlerine göre grupla (bir derste birden fazla nöbetçi olabilir)
        period_times = self.get_period_times()
        period_groups: Dict[int, List[SubstitutionAssignment]] = {}
        for a in assignments:
            if a.period not in period_groups:
                period_groups[a.period] = []
            period_groups[a.period].append(a)

        for period in sorted(period_groups.keys()):
            subs = period_groups[period]
            first_sub = subs[0]
            time_interval = period_times.get(period, "")

            duty_lines = []
            loc_lines = []
            sig_lines = []

            for s in subs:
                duty_t = teachers.get(s.duty_teacher_id) if s.duty_teacher_id else None
                if duty_t:
                    is_ek = s.is_ek_ders or is_same_branch(duty_t.branch, absent_teacher.branch)
                    ek_tag = "<br/>&nbsp;&nbsp;<font color='#1D4ED8'><b>[⭐ Ek Ders Hak Eder - Branş Öğretmeni]</b></font>" if is_ek else ""
                    t_str = f"• <b>{duty_t.name}</b>{ek_tag}" if len(subs) > 1 else f"<b>{duty_t.name}</b>{ek_tag}"
                    l_str = teacher_loc_map.get(duty_t.id, "—")
                else:
                    t_str = "—"
                    l_str = "—"
                duty_lines.append(t_str)
                loc_lines.append(l_str)
                sig_lines.append("...............")

            duty_html = "<br/>".join(duty_lines)
            loc_html = "<br/>".join(loc_lines)
            sig_html = "<br/>".join(sig_lines)

            row = [
                Paragraph(f"<b>{period}. Ders</b>", cell_style),
                Paragraph(time_interval, cell_style),
                Paragraph(f"<b>{first_sub.class_name}</b>", cell_style),
                Paragraph(first_sub.subject_code, cell_style),
                Paragraph(duty_html, cell_style),
                Paragraph(loc_html, cell_style),
                Paragraph(sig_html, cell_style)
            ]
            table_data.append(row)

        col_widths = [45, 75, 45, 55, 170, 65, 65]
        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))

        # Yönerge Notu
        note_text = (
            "<i>* Nöbetçi öğretmenler boş ders saatlerinde yukarıda belirtilen sınıflara nezaret etmekle yükümlüdür. "
            "(MEB Okul Öncesi ve İlköğretim Kurumları Yönetmeliği Madde 44)<br/>"
            "* Gelmeyen öğretmenle aynı branşta olup derse giren nöbetçi öğretmenlere ilgili mevzuat uyarınca ek ders ücreti tahakkuk ettirilir.</i>"
        )
        elements.append(Paragraph(note_text, meta_style))
        elements.append(Spacer(1, 30))

        # İmza Bloğu
        sig_data = [
            ["", f"{today_date}\n{school.principal_name}\nOkul Müdürü"]
        ]
        sig_table = Table(sig_data, colWidths=[320, 200])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(sig_table)

        doc.build(elements)
        logger.info(f"İkame görevlendirme PDF belgesi oluşturuldu: {output_path}")
        return output_path

    def export_substitution_html(
        self,
        output_path: str,
        date_str: str,
        day_name: str,
        absent_teacher: Teacher,
        assignments: List[SubstitutionAssignment]
    ) -> str:
        """
        Yazdırılabilir resmi HTML görevlendirme fişi üretir.
        """
        school = self.db.get_school_info()
        teachers = {t.id: t for t in self.db.get_teachers()}
        duty_day_teachers = self.get_day_duty_teachers(date_str, day_name)
        teacher_loc_map = {d["teacher"].id: (d["location"].name if d["location"] else "-") for d in duty_day_teachers}

        today_date = datetime.date.today().strftime("%d.%m.%Y")

        rows_html = ""
        period_times = self.get_period_times()
        period_groups: Dict[int, List[SubstitutionAssignment]] = {}
        for a in assignments:
            if a.period not in period_groups:
                period_groups[a.period] = []
            period_groups[a.period].append(a)

        for period in sorted(period_groups.keys()):
            subs = period_groups[period]
            first_sub = subs[0]
            time_interval = period_times.get(period, "")

            duty_lines = []
            loc_lines = []
            sig_lines = []

            for s in subs:
                duty_t = teachers.get(s.duty_teacher_id) if s.duty_teacher_id else None
                if duty_t:
                    is_ek = s.is_ek_ders or is_same_branch(duty_t.branch, absent_teacher.branch)
                    ek_badge = " <span style='background:#dbeafe; color:#1e40af; font-size:10px; padding:2px 6px; border-radius:3px; font-weight:bold;'>⭐ Ek Ders Hak Eder (Branş)</span>" if is_ek else ""
                    t_str = f"• {duty_t.name}{ek_badge}" if len(subs) > 1 else f"{duty_t.name}{ek_badge}"
                    l_str = teacher_loc_map.get(duty_t.id, "—")
                else:
                    t_str = "—"
                    l_str = "—"
                duty_lines.append(t_str)
                loc_lines.append(l_str)
                sig_lines.append("<span style='color:#94a3b8;'>....................</span>")

            duty_html = "<br/>".join(duty_lines)
            loc_html = "<br/>".join(loc_lines)
            sig_html = "<br/>".join(sig_lines)

            rows_html += f"""
            <tr>
                <td style="text-align:center; font-weight:bold;">{period}. Ders</td>
                <td style="text-align:center;">{time_interval}</td>
                <td style="text-align:center; font-weight:bold;">{first_sub.class_name}</td>
                <td style="text-align:center;">{first_sub.subject_code}</td>
                <td style="font-weight:bold; line-height:1.6;">{duty_html}</td>
                <td style="text-align:center; line-height:1.6;">{loc_html}</td>
                <td style="text-align:center; width: 120px; line-height:1.6;">{sig_html}</td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Boş Ders Doldurma Çizelgesi - {date_str}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            color: #1e293b;
        }}
        .header {{
            text-align: center;
            line-height: 1.4;
            margin-bottom: 20px;
        }}
        .title {{
            font-size: 16px;
            font-weight: bold;
        }}
        .subtitle {{
            font-size: 14px;
            font-weight: bold;
            color: #2563eb;
            margin-top: 5px;
        }}
        .meta-box {{
            background: #f8fafc;
            border: 1px solid #cbd5e1;
            padding: 10px 15px;
            border-radius: 6px;
            margin-bottom: 15px;
            font-size: 13px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        th, td {{
            border: 1px solid #94a3b8;
            padding: 8px 10px;
            font-size: 12px;
        }}
        th {{
            background-color: #1e293b;
            color: #ffffff;
            font-weight: bold;
            text-align: center;
        }}
        .signature-block {{
            float: right;
            text-align: center;
            width: 220px;
            margin-top: 30px;
            font-size: 13px;
            line-height: 1.5;
        }}
        .no-print {{
            margin-bottom: 15px;
        }}
        @media print {{
            .no-print {{ display: none; }}
            body {{ margin: 0; }}
        }}
    </style>
</head>
<body>
    <div class="no-print">
        <button onclick="window.print()" style="padding: 8px 16px; background:#2563eb; color:#fff; border:none; border-radius:4px; cursor:pointer; font-weight:bold;">
            🖨️ Sayfayı Yazdır
        </button>
    </div>

    <div class="header">
        <div class="title">
            T.C.<br/>
            {school.city.upper()} / {school.district.upper()}<br/>
            {school.name.upper()} MÜDÜRLÜĞÜ
        </div>
        <div class="subtitle">BOŞ DERS DOLDURMA / NÖBETÇİ ÖĞRETMEN GÖREVLENDİRME ÇİZELGESİ</div>
    </div>

    <div class="meta-box">
        <strong>Tarih / Gün:</strong> {date_str} ({day_name}) &nbsp;|&nbsp;
        <strong>İzinli/Raporlu Öğretmen:</strong> {absent_teacher.name} ({absent_teacher.branch}) &nbsp;|&nbsp;
        <strong>Düzenleme Tarihi:</strong> {today_date}
    </div>

    <table>
        <thead>
            <tr>
                <th>Ders</th>
                <th>Saat Aralığı</th>
                <th>Sınıf</th>
                <th>Ders Adı</th>
                <th>Görevlendirilen Nöbetçi Öğretmen</th>
                <th>Nöbet Yeri</th>
                <th>Öğretmen İmzası</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>

    <div style="font-size:11px; font-style:italic; color:#64748b; line-height:1.5;">
        * Nöbetçi öğretmenler boş ders saatlerinde yukarıda belirtilen sınıflara nezaret etmekle yükümlüdür. (MEB Yönetmeliği Md. 44)<br/>
        * Gelmeyen öğretmenle aynı branşta olup derse giren nöbetçi öğretmenlere ilgili mevzuat uyarınca ek ders ücreti tahakkuk ettirilir.
    </div>

    <div class="signature-block">
        <div>{today_date}</div>
        <br/><br/>
        <div style="font-weight:bold;">{school.principal_name}</div>
        <div>Okul Müdürü</div>
    </div>
</body>
</html>
"""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"İkame görevlendirme HTML belgesi oluşturuldu: {output_path}")
        return output_path

    def export_daily_substitutions_pdf(
        self,
        output_path: str,
        date_str: str,
        day_name: str,
        assignments: List[SubstitutionAssignment]
    ) -> str:
        """
        O güne ait TÜM gelmeyen öğretmenlerin ikamelerini tek bir resmi günlük çarşaf PDF belgesinde toplar.
        """
        _register_pdf_fonts()
        font_name = "CustomArial" if _FONT_REGISTERED else "Helvetica"
        font_bold = "CustomArial-Bold" if _FONT_REGISTERED else "Helvetica-Bold"

        school = self.db.get_school_info()
        teachers = {t.id: t for t in self.db.get_teachers()}
        locations = {loc.id: loc for loc in self.db.get_locations()}

        duty_day_teachers = self.get_day_duty_teachers(date_str, day_name)
        teacher_loc_map = {d["teacher"].id: (d["location"].name if d["location"] else "-") for d in duty_day_teachers}

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=30,
            rightMargin=30,
            topMargin=30,
            bottomMargin=30
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DailyTitleStyle",
            parent=styles["Normal"],
            fontName=font_bold,
            fontSize=11,
            leading=15,
            alignment=1,
            textColor=colors.HexColor("#0F172A")
        )
        subtitle_style = ParagraphStyle(
            "DailySubTitleStyle",
            parent=styles["Normal"],
            fontName=font_bold,
            fontSize=10,
            leading=13,
            alignment=1,
            textColor=colors.HexColor("#2563EB")
        )
        meta_style = ParagraphStyle(
            "DailyMetaStyle",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=8,
            leading=12,
            alignment=0,
            textColor=colors.HexColor("#334155")
        )
        cell_style = ParagraphStyle(
            "DailyCellStyle",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=8,
            leading=11,
            alignment=1
        )
        cell_bold = ParagraphStyle(
            "DailyCellBold",
            parent=styles["Normal"],
            fontName=font_bold,
            fontSize=8,
            leading=11,
            alignment=1,
            textColor=colors.white
        )

        elements = []
        elements.append(Paragraph(f"T.C.<br/>{school.city.upper()} / {school.district.upper()}<br/>{school.name.upper()} MÜDÜRLÜĞÜ", title_style))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("GÜNLÜK BOŞ DERS DOLDURMA VE NÖBETÇİ ÖĞRETMEN GÖREVLENDİRME ÇİZELGESİ", subtitle_style))
        elements.append(Spacer(1, 10))

        today_date = datetime.date.today().strftime("%d.%m.%Y")
        absent_ids = list({a.absent_teacher_id for a in assignments if a.absent_teacher_id})
        absent_names = [teachers[aid].name for aid in absent_ids if aid in teachers]
        absent_summary = ", ".join(absent_names) if absent_names else "Belirtilmemiş"

        meta_text = (
            f"<b>Tarih / Gün:</b> {date_str} ({day_name}) &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Gelmeyen Öğretmenler ({len(absent_names)}):</b> {absent_summary}<br/>"
            f"<b>Düzenleme Tarihi:</b> {today_date} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Toplam Görevlendirme:</b> {len(assignments)} ders saati"
        )
        elements.append(Paragraph(meta_text, meta_style))
        elements.append(Spacer(1, 10))

        headers = ["Ders", "Saat", "Gelmeyen Öğretmen", "Sınıf", "Ders Adı", "Görevli Nöbetçi", "Nöbet Yeri", "İmza"]
        table_data = [[Paragraph(h, cell_bold) for h in headers]]

        sorted_assignments = sorted(
            assignments,
            key=lambda x: (x.period, teachers.get(x.absent_teacher_id).name if teachers.get(x.absent_teacher_id) else "")
        )

        period_times = self.get_period_times()
        for a in sorted_assignments:
            time_interval = period_times.get(a.period, "")
            absent_t = teachers.get(a.absent_teacher_id)
            absent_str = f"<b>{absent_t.name}</b>" if absent_t else "—"
            if absent_t and absent_t.branch:
                absent_str += f"<br/><font size='7' color='#64748B'>({absent_t.branch})</font>"

            duty_t = teachers.get(a.duty_teacher_id) if a.duty_teacher_id else None
            if duty_t:
                is_ek = a.is_ek_ders or (absent_t and is_same_branch(duty_t.branch, absent_t.branch))
                ek_tag = "<br/><font size='7' color='#1D4ED8'><b>[⭐ Ek Ders (Branş)]</b></font>" if is_ek else ""
                duty_str = f"<b>{duty_t.name}</b>{ek_tag}"
                loc_str = teacher_loc_map.get(duty_t.id, "—")
            else:
                duty_str = "<font color='#DC2626'><i>Boş / Atanmadı</i></font>"
                loc_str = "—"

            row = [
                Paragraph(f"<b>{a.period}. Ders</b>", cell_style),
                Paragraph(time_interval, cell_style),
                Paragraph(absent_str, cell_style),
                Paragraph(f"<b>{a.class_name}</b>", cell_style),
                Paragraph(a.subject_code, cell_style),
                Paragraph(duty_str, cell_style),
                Paragraph(loc_str, cell_style),
                Paragraph("...............", cell_style)
            ]
            table_data.append(row)

        col_widths = [45, 65, 95, 45, 55, 125, 55, 50]
        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 14))

        note_text = (
            "<i>* Nöbetçi öğretmenler boş ders saatlerinde yukarıda belirtilen sınıflara nezaret etmekle yükümlüdür. (MEB Yönetmeliği Md. 44)<br/>"
            "* Gelmeyen öğretmenle aynı branşta olup derse giren nöbetçi öğretmenlere ilgili mevzuat uyarınca ek ders tahakkuk ettirilir.</i>"
        )
        elements.append(Paragraph(note_text, meta_style))
        elements.append(Spacer(1, 20))

        sig_data = [["", f"{today_date}\n{school.principal_name}\nOkul Müdürü"]]
        sig_table = Table(sig_data, colWidths=[335, 200])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        elements.append(sig_table)

        doc.build(elements)
        logger.info(f"Toplu ikame görevlendirme PDF belgesi oluşturuldu: {output_path}")
        return output_path

    def export_daily_substitutions_html(
        self,
        output_path: str,
        date_str: str,
        day_name: str,
        assignments: List[SubstitutionAssignment]
    ) -> str:
        """
        O güne ait TÜM gelmeyen öğretmenlerin ikamelerini tek bir HTML sayfasında yazdırılabilir formatta üretir.
        """
        school = self.db.get_school_info()
        teachers = {t.id: t for t in self.db.get_teachers()}
        duty_day_teachers = self.get_day_duty_teachers(date_str, day_name)
        teacher_loc_map = {d["teacher"].id: (d["location"].name if d["location"] else "-") for d in duty_day_teachers}
        today_date = datetime.date.today().strftime("%d.%m.%Y")

        absent_ids = list({a.absent_teacher_id for a in assignments if a.absent_teacher_id})
        absent_names = [teachers[aid].name for aid in absent_ids if aid in teachers]
        absent_summary = ", ".join(absent_names) if absent_names else "Belirtilmemiş"

        sorted_assignments = sorted(
            assignments,
            key=lambda x: (x.period, teachers.get(x.absent_teacher_id).name if teachers.get(x.absent_teacher_id) else "")
        )

        rows_html = ""
        period_times = self.get_period_times()
        for a in sorted_assignments:
            time_interval = period_times.get(a.period, "")
            absent_t = teachers.get(a.absent_teacher_id)
            absent_str = absent_t.name if absent_t else "—"
            if absent_t and absent_t.branch:
                absent_str += f"<br/><small style='color:#64748B;'>({absent_t.branch})</small>"

            duty_t = teachers.get(a.duty_teacher_id) if a.duty_teacher_id else None
            if duty_t:
                is_ek = a.is_ek_ders or (absent_t and is_same_branch(duty_t.branch, absent_t.branch))
                ek_badge = " <span style='background:#dbeafe; color:#1e40af; font-size:10px; padding:2px 5px; border-radius:3px; font-weight:bold;'>⭐ Ek Ders</span>" if is_ek else ""
                duty_str = f"<b>{duty_t.name}</b>{ek_badge}"
                loc_str = teacher_loc_map.get(duty_t.id, "—")
            else:
                duty_str = "<span style='color:#dc2626;'><i>Boş / Atanmadı</i></span>"
                loc_str = "—"

            rows_html += f"""
            <tr>
                <td style="text-align:center; font-weight:bold;">{a.period}. Ders</td>
                <td style="text-align:center;">{time_interval}</td>
                <td>{absent_str}</td>
                <td style="text-align:center; font-weight:bold;">{a.class_name}</td>
                <td style="text-align:center;">{a.subject_code}</td>
                <td>{duty_str}</td>
                <td style="text-align:center;">{loc_str}</td>
                <td style="text-align:center; color:#94a3b8;">....................</td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Toplu Boş Ders Doldurma Çizelgesi - {date_str}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; color: #1e293b; }}
        .header {{ text-align: center; line-height: 1.4; margin-bottom: 15px; }}
        .title {{ font-size: 15px; font-weight: bold; }}
        .subtitle {{ font-size: 13px; font-weight: bold; color: #2563eb; margin-top: 5px; }}
        .meta-box {{ background: #f8fafc; border: 1px solid #cbd5e1; padding: 10px 14px; border-radius: 6px; margin-bottom: 15px; font-size: 12px; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; }}
        th, td {{ border: 1px solid #94a3b8; padding: 6px 8px; font-size: 11px; }}
        th {{ background-color: #1e293b; color: #ffffff; font-weight: bold; text-align: center; }}
        .signature-block {{ float: right; text-align: center; width: 220px; margin-top: 25px; font-size: 12px; line-height: 1.5; }}
        @media print {{ .no-print {{ display: none; }} body {{ margin: 0; }} }}
    </style>
</head>
<body>
    <div class="no-print" style="margin-bottom: 12px;">
        <button onclick="window.print()" style="padding: 8px 16px; background:#2563eb; color:#fff; border:none; border-radius:4px; cursor:pointer; font-weight:bold;">
            🖨️ Sayfayı Yazdır
        </button>
    </div>
    <div class="header">
        <div class="title">T.C.<br/>{school.city.upper()} / {school.district.upper()}<br/>{school.name.upper()} MÜDÜRLÜĞÜ</div>
        <div class="subtitle">GÜNLÜK BOŞ DERS DOLDURMA VE NÖBETÇİ ÖĞRETMEN GÖREVLENDİRME ÇİZELGESİ</div>
    </div>
    <div class="meta-box">
        <strong>Tarih / Gün:</strong> {date_str} ({day_name}) &nbsp;|&nbsp;
        <strong>Gelmeyen Öğretmenler ({len(absent_names)}):</strong> {absent_summary} &nbsp;|&nbsp;
        <strong>Toplam Ders Saati:</strong> {len(assignments)} &nbsp;|&nbsp;
        <strong>Düzenleme Tarihi:</strong> {today_date}
    </div>
    <table>
        <thead>
            <tr>
                <th>Ders</th><th>Saat Aralığı</th><th>Gelmeyen Öğretmen</th><th>Sınıf</th><th>Ders Adı</th><th>Görevli Nöbetçi</th><th>Nöbet Yeri</th><th>İmza</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    <div style="font-size:10px; font-style:italic; color:#64748b; line-height:1.4;">
        * Nöbetçi öğretmenler boş ders saatlerinde yukarıda belirtilen sınıflara nezaret etmekle yükümlüdür. (MEB Yönetmeliği Md. 44)<br/>
        * Gelmeyen öğretmenle aynı branşta olup derse giren nöbetçi öğretmenlere ilgili mevzuat uyarınca ek ders tahakkuk ettirilir.
    </div>
    <div class="signature-block">
        <div>{today_date}</div><br/><br/>
        <div style="font-weight:bold;">{school.principal_name}</div>
        <div>Okul Müdürü</div>
    </div>
</body>
</html>
"""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"Toplu ikame görevlendirme HTML belgesi oluşturuldu: {output_path}")
        return output_path


def get_monthly_ek_ders_summary(db: Database, month_str: str) -> Dict[str, Any]:
    """
    Belirli bir ay için (YYYY-MM) ikameye giren tüm öğretmenlerin
    ek ders hak edişlerini ve nöbet nezareti saatlerini hesaplar.
    """
    teachers_list = db.get_teachers(active_only=False)
    teachers_map = {t.id: t for t in teachers_list}
    subs = db.get_substitutions(month_str=month_str)

    teacher_stats: Dict[str, Dict[str, Any]] = {}
    total_hours = 0
    total_ek_ders_hours = 0
    total_supervision_hours = 0

    for s in subs:
        if not s.duty_teacher_id:
            continue
        total_hours += 1
        duty_t = teachers_map.get(s.duty_teacher_id)
        absent_t = teachers_map.get(s.absent_teacher_id) if s.absent_teacher_id else None

        duty_name = duty_t.name if duty_t else "Bilinmeyen Öğretmen"
        duty_branch = duty_t.branch if duty_t else ""

        is_branch_match = is_same_branch(duty_branch, absent_t.branch) if (duty_t and absent_t) else False
        is_ek = bool(s.is_ek_ders or is_branch_match)

        if is_ek:
            total_ek_ders_hours += 1
            reason = "Branş Uyumu (+1)" if is_branch_match else "İdare Görevlendirmesi (+1)"
        else:
            total_supervision_hours += 1
            reason = "Nöbet Nezareti (Ücretsiz)"

        t_id = s.duty_teacher_id
        if t_id not in teacher_stats:
            teacher_stats[t_id] = {
                "teacher": duty_t,
                "teacher_id": t_id,
                "teacher_name": duty_name,
                "branch": duty_branch,
                "total_substitutions": 0,
                "ek_ders_hours": 0,
                "supervision_hours": 0,
                "classes_set": set(),
                "details": []
            }

        st = teacher_stats[t_id]
        st["total_substitutions"] += 1
        if is_ek:
            st["ek_ders_hours"] += 1
        else:
            st["supervision_hours"] += 1

        if s.class_name:
            st["classes_set"].add(s.class_name)

        st["details"].append({
            "id": s.id,
            "date_str": s.date_str,
            "period": s.period,
            "class_name": s.class_name,
            "subject_code": s.subject_code,
            "absent_teacher_name": absent_t.name if absent_t else "-",
            "absent_teacher_branch": absent_t.branch if absent_t else "-",
            "is_ek_ders": is_ek,
            "reason": reason,
            "notes": s.notes or ""
        })

    for st in teacher_stats.values():
        st["classes_str"] = ", ".join(sorted(list(st["classes_set"]))) if st["classes_set"] else "-"
        st["details"].sort(key=lambda x: (x["date_str"], x["period"]))

    sorted_teachers = sorted(teacher_stats.values(), key=lambda x: x["teacher_name"].lower())

    return {
        "month_str": month_str,
        "total_hours": total_hours,
        "total_ek_ders_hours": total_ek_ders_hours,
        "total_supervision_hours": total_supervision_hours,
        "teachers": sorted_teachers,
        "eligible_teacher_count": sum(1 for st in sorted_teachers if st["ek_ders_hours"] > 0)
    }


def get_teacher_substitutions_summary(db: Database, teacher_id: str, month_str: Optional[str] = None) -> Dict[str, Any]:
    """
    Belirli bir öğretmenin girdiği tüm ikameleri veya seçili aydaki ikamelerini döner.
    """
    teachers_list = db.get_teachers(active_only=False)
    teachers_map = {t.id: t for t in teachers_list}
    duty_t = teachers_map.get(teacher_id)

    subs = db.get_substitutions(month_str=month_str, duty_teacher_id=teacher_id)

    total_substitutions = 0
    ek_ders_hours = 0
    supervision_hours = 0
    details = []

    for s in subs:
        total_substitutions += 1
        absent_t = teachers_map.get(s.absent_teacher_id) if s.absent_teacher_id else None
        is_branch_match = is_same_branch(duty_t.branch if duty_t else "", absent_t.branch if absent_t else "")
        is_ek = bool(s.is_ek_ders or is_branch_match)

        if is_ek:
            ek_ders_hours += 1
            reason = "Branş Uyumu (+1)" if is_branch_match else "İdare Görevlendirmesi (+1)"
        else:
            supervision_hours += 1
            reason = "Nöbet Nezareti (Ücretsiz)"

        details.append({
            "id": s.id,
            "date_str": s.date_str,
            "period": s.period,
            "class_name": s.class_name,
            "subject_code": s.subject_code,
            "absent_teacher_name": absent_t.name if absent_t else "-",
            "absent_teacher_branch": absent_t.branch if absent_t else "-",
            "is_ek_ders": is_ek,
            "reason": reason,
            "notes": s.notes or ""
        })

    details.sort(key=lambda x: (x["date_str"], x["period"]))

    return {
        "teacher": duty_t,
        "teacher_id": teacher_id,
        "month_str": month_str,
        "total_substitutions": total_substitutions,
        "ek_ders_hours": ek_ders_hours,
        "supervision_hours": supervision_hours,
        "details": details
    }

