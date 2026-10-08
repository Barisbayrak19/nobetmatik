"""
aSc Timetables & Bilsa Ders Dağıtım İçe Aktarma Servisi
Türkiye'deki okullarda yaygın kullanılan aSc Timetables (XML ve Excel) ile 
Bilsa Haftalık Ders Dağıtım programlarının çıktılarını otomatik ayrıştırır.
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import openpyxl
import re

from core.models import Teacher, TeacherLesson
from core.logger import logger

TURKISH_DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]

class AscBilsaService:
    def __init__(self, db=None):
        self.db = db

    # =========================================================================
    # 1. aSc Timetables XML Ayrıştırıcı
    # =========================================================================
    def parse_asc_xml(self, xml_path: str) -> Dict[str, Any]:
        """
        aSc Timetables tarafından üretilen .xml dosyasını okur.
        Döndürür:
        {
            "teachers": [{"name": str, "short": str, "branch": str}],
            "classes": [{"name": str, "short": str}],
            "subjects": [{"name": str, "short": str}],
            "lessons": [TeacherLesson, ...]
        }
        """
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Gün Tanımları (daysdefs)
        days_map = {}
        daysdefs = root.find("daysdefs")
        if daysdefs is not None:
            for d in daysdefs.findall("daysdef"):
                d_id = d.attrib.get("id")
                d_name = d.attrib.get("name", "")
                d_days = d.attrib.get("days", "")
                days_map[d_id] = {"name": d_name, "days": d_days}

        # Öğretmenler
        teachers_dict = {}
        teachers_list = []
        teachers_el = root.find("teachers")
        if teachers_el is not None:
            for t in teachers_el.findall("teacher"):
                t_id = t.attrib.get("id")
                first = t.attrib.get("firstname", "").strip()
                last = t.attrib.get("lastname", "").strip()
                name = t.attrib.get("name", "").strip()
                if not name and (first or last):
                    name = f"{first} {last}".strip()
                short = t.attrib.get("short", "").strip()
                if name:
                    teachers_dict[t_id] = {"name": name, "short": short}
                    teachers_list.append({"name": name, "short": short, "branch": ""})

        # Sınıflar
        classes_dict = {}
        classes_list = []
        classes_el = root.find("classes")
        if classes_el is not None:
            for c in classes_el.findall("class"):
                c_id = c.attrib.get("id")
                name = c.attrib.get("name", "").strip()
                short = c.attrib.get("short", "").strip()
                classes_dict[c_id] = name or short
                classes_list.append({"name": name or short, "short": short})

        # Dersler (Subjects)
        subjects_dict = {}
        subjects_list = []
        subjects_el = root.find("subjects")
        if subjects_el is not None:
            for s in subjects_el.findall("subject"):
                s_id = s.attrib.get("id")
                name = s.attrib.get("name", "").strip()
                short = s.attrib.get("short", "").strip()
                subjects_dict[s_id] = name or short
                subjects_list.append({"name": name or short, "short": short})

        # Öğretmenlerin branşlarını derslerden tahmin et (en çok girdiği ders branşıdır)
        teacher_subject_counts: Dict[str, Dict[str, int]] = {}

        # Ders Atamaları (Lessons)
        lessons_dict = {}
        lessons_el = root.find("lessons")
        if lessons_el is not None:
            for les in lessons_el.findall("lesson"):
                les_id = les.attrib.get("id")
                t_ids = [tid.strip() for tid in les.attrib.get("teacherids", "").split(",") if tid.strip()]
                c_ids = [cid.strip() for cid in les.attrib.get("classids", "").split(",") if cid.strip()]
                s_id = les.attrib.get("subjectid", "").strip()

                s_name = subjects_dict.get(s_id, "")
                for tid in t_ids:
                    if tid not in teacher_subject_counts:
                        teacher_subject_counts[tid] = {}
                    teacher_subject_counts[tid][s_name] = teacher_subject_counts[tid].get(s_name, 0) + 1

                class_names = [classes_dict.get(cid, cid) for cid in c_ids]
                class_str = ", ".join(class_names)

                lessons_dict[les_id] = {
                    "teacher_ids": t_ids,
                    "class_name": class_str,
                    "subject": s_name
                }

        # Öğretmen branşını güncelle
        for t in teachers_list:
            matched_id = None
            for tid, tinfo in teachers_dict.items():
                if tinfo["name"] == t["name"]:
                    matched_id = tid
                    break
            if matched_id and matched_id in teacher_subject_counts:
                counts = teacher_subject_counts[matched_id]
                if counts:
                    top_subject = max(counts.items(), key=lambda x: x[1])[0]
                    t["branch"] = top_subject

        # Ders Kartları (Cards) -> Haftalık programa dönüştür
        parsed_lessons: List[TeacherLesson] = []
        cards_el = root.find("cards")
        if cards_el is not None:
            for card in cards_el.findall("card"):
                les_id = card.attrib.get("lessonid")
                if les_id not in lessons_dict:
                    continue

                les_info = lessons_dict[les_id]
                period_str = card.attrib.get("period", "")
                try:
                    period = int(period_str)
                except ValueError:
                    continue

                day_attr = card.attrib.get("day", "")
                days_attr = card.attrib.get("days", "")
                day_name = self._resolve_asc_day(day_attr or days_attr, days_map)
                if not day_name or day_name not in TURKISH_DAYS:
                    continue

                for tid in les_info["teacher_ids"]:
                    tinfo = teachers_dict.get(tid)
                    if not tinfo:
                        continue
                    t_name = tinfo["name"]

                    lesson_obj = TeacherLesson(
                        teacher_id="",
                        day_name=day_name,
                        period=period,
                        class_name=les_info["class_name"] or "Belirtilmemiş",
                        subject_code=les_info["subject"] or "Ders",
                        is_free=False
                    )
                    lesson_obj.temp_teacher_name = t_name
                    parsed_lessons.append(lesson_obj)

        logger.info(f"aSc XML Ayrıştırıldı: {len(teachers_list)} öğretmen, {len(parsed_lessons)} ders saati.")
        return {
            "teachers": teachers_list,
            "classes": classes_list,
            "subjects": subjects_list,
            "lessons": parsed_lessons
        }

    def _resolve_asc_day(self, day_code: str, days_map: Dict[str, Dict[str, str]]) -> Optional[str]:
        """
        aSc gün kodunu ('10000', '1', 'Salı' vb.) Türkçe gün adına dönüştürür.
        """
        if not day_code:
            return None

        for td in TURKISH_DAYS:
            if td.lower() in day_code.lower():
                return td

        if len(day_code) >= 5 and all(c in "01" for c in day_code[:5]):
            idx = day_code.find("1")
            if 0 <= idx < 5:
                return TURKISH_DAYS[idx]

        try:
            val = int(day_code)
            if 1 <= val <= 5:
                return TURKISH_DAYS[val - 1]
            if 0 <= val <= 4:
                return TURKISH_DAYS[val]
        except ValueError:
            pass

        if day_code in days_map:
            d_info = days_map[day_code]
            return self._resolve_asc_day(d_info.get("days") or d_info.get("name"), {})

        return None

    # =========================================================================
    # 2. aSc / Bilsa Çarşaf Excel Ayrıştırıcı
    # =========================================================================
    def parse_asc_bilsa_excel(self, excel_path: str) -> Dict[str, Any]:
        """
        aSc Timetables veya Bilsa tarafından dışa aktarılan Excel çarşaf veya liste çizelgesini okur.
        Döndürür:
        {
            "teachers": [{"name": str, "branch": str}],
            "lessons": [TeacherLesson, ...]
        }
        """
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))

        if not rows:
            return {"teachers": [], "lessons": []}

        header_candidate = [str(c).strip().lower() if c else "" for c in rows[0]]
        if any("öğretmen" in c or "ogretmen" in c for c in header_candidate) and \
           any("gün" in c or "gun" in c for c in header_candidate):
            return self._parse_tabular_excel(rows)
        else:
            return self._parse_matrix_excel(rows)

    def _parse_tabular_excel(self, rows: List[Tuple]) -> Dict[str, Any]:
        header = [str(c).strip().lower() if c else "" for c in rows[0]]
        t_idx = next((i for i, c in enumerate(header) if "öğretmen" in c or "ogretmen" in c), 0)
        d_idx = next((i for i, c in enumerate(header) if "gün" in c or "gun" in c), 1)
        p_idx = next((i for i, c in enumerate(header) if "saat" in c or "ders" in c), 2)
        c_idx = next((i for i, c in enumerate(header) if "sınıf" in c or "sinif" or "şube" in c), 3)
        s_idx = next((i for i, c in enumerate(header) if "branş" in c or "ders adı" in c), 4)

        teachers_set = set()
        parsed_lessons: List[TeacherLesson] = []

        for r in rows[1:]:
            if not any(r):
                continue
            t_name = str(r[t_idx]).strip() if t_idx < len(r) and r[t_idx] else ""
            if not t_name:
                continue
            day_str = str(r[d_idx]).strip() if d_idx < len(r) and r[d_idx] else ""
            resolved_day = self._resolve_turkish_day_name(day_str)
            if not resolved_day:
                continue

            try:
                p_val = int(re.search(r'\d+', str(r[p_idx])).group()) if p_idx < len(r) and r[p_idx] else 1
            except Exception:
                p_val = 1

            cls_name = str(r[c_idx]).strip() if c_idx < len(r) and r[c_idx] else "Belirtilmemiş"
            sbj_name = str(r[s_idx]).strip() if s_idx < len(r) and r[s_idx] else "Ders"

            teachers_set.add(t_name)
            les = TeacherLesson(
                teacher_id="",
                day_name=resolved_day,
                period=p_val,
                class_name=cls_name,
                subject_code=sbj_name,
                is_free=False
            )
            les.temp_teacher_name = t_name
            parsed_lessons.append(les)

        teachers_list = [{"name": name, "branch": ""} for name in sorted(teachers_set)]
        return {"teachers": teachers_list, "lessons": parsed_lessons}

    def _parse_matrix_excel(self, rows: List[Tuple]) -> Dict[str, Any]:
        """
        Çarşaf / Matris formatındaki Excel'i (Satırlarda Öğretmen, Sütunlarda Gün/Saat) ayrıştırır.
        """
        day_cols: List[Tuple[int, str, int]] = []
        current_day = None

        day_row_idx = 0
        hour_row_idx = 1
        for r_idx in range(min(5, len(rows))):
            row_str = " ".join([str(c) for c in rows[r_idx] if c])
            if any(d in row_str for d in TURKISH_DAYS):
                day_row_idx = r_idx
                hour_row_idx = r_idx + 1
                break

        row_days = rows[day_row_idx]
        row_hours = rows[hour_row_idx] if hour_row_idx < len(rows) else []

        for c_idx in range(1, len(row_days)):
            val_day = str(row_days[c_idx]).strip() if row_days[c_idx] else ""
            res_d = self._resolve_turkish_day_name(val_day)
            if res_d:
                current_day = res_d

            val_h = str(row_hours[c_idx]).strip() if c_idx < len(row_hours) and row_hours[c_idx] else ""
            m_h = re.search(r'\d+', val_h)
            period = int(m_h.group()) if m_h else ((c_idx - 1) % 8 + 1)

            if current_day:
                day_cols.append((c_idx, current_day, period))

        teachers_set = set()
        parsed_lessons: List[TeacherLesson] = []

        start_row = hour_row_idx + 1
        for r_idx in range(start_row, len(rows)):
            row = rows[r_idx]
            if not row or not any(row):
                continue
            teacher_name = str(row[0]).strip() if row[0] else ""
            if not teacher_name or any(w in teacher_name.lower() for w in ["toplam", "saat", "gün", "öğretmen"]):
                continue

            teachers_set.add(teacher_name)

            for col_idx, d_name, p_num in day_cols:
                if col_idx < len(row) and row[col_idx]:
                    cell_val = str(row[col_idx]).strip()
                    if not cell_val or cell_val in ["-", ".", ""]:
                        continue

                    parts = cell_val.replace("/", " ").replace("-", " ").split()
                    c_name = cell_val
                    s_name = "Ders"
                    if len(parts) >= 2:
                        c_name = parts[0]
                        s_name = " ".join(parts[1:])

                    les = TeacherLesson(
                        teacher_id="",
                        day_name=d_name,
                        period=p_num,
                        class_name=c_name,
                        subject_code=s_name,
                        is_free=False
                    )
                    les.temp_teacher_name = teacher_name
                    parsed_lessons.append(les)

        teachers_list = [{"name": name, "branch": ""} for name in sorted(teachers_set)]
        return {"teachers": teachers_list, "lessons": parsed_lessons}

    def _resolve_turkish_day_name(self, text: str) -> Optional[str]:
        if not text:
            return None
        text_lower = text.lower()
        if "pazartesi" in text_lower or text_lower.startswith("pzt"):
            return "Pazartesi"
        if "salı" in text_lower or text_lower.startswith("sal"):
            return "Salı"
        if "çarşamba" in text_lower or text_lower.startswith("çar"):
            return "Çarşamba"
        if "perşembe" in text_lower or text_lower.startswith("per"):
            return "Perşembe"
        if "cuma" in text_lower or text_lower.startswith("cum"):
            return "Cuma"
        return None
